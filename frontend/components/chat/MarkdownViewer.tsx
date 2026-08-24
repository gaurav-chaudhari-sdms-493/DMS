"use client";
import React from "react";

interface MarkdownViewerProps {
  content: string;
  className?: string;
  /** T71: when provided, [1] [2] style markers become clickable citation
   * buttons instead of plain text. Opt-in only — callers that don't pass
   * this (chat, etc.) render literal "[1]" text unchanged, same as before. */
  onCitationClick?: (n: number) => void;
}

export function MarkdownViewer({ content, className = "", onCitationClick }: MarkdownViewerProps) {
  if (!content) return null;

  // Simple, safe, robust Markdown parser for LLM responses
  const renderMarkdown = (rawText: string) => {
    const lines = rawText.split("\n");
    const elements: React.ReactNode[] = [];
    let inCodeBlock = false;
    let codeBuffer: string[] = [];
    let listBuffer: { type: "ul" | "ol"; items: string[] } | null = null;

    const flushList = () => {
      if (listBuffer) {
        const ListTag = listBuffer.type;
        elements.push(
          <ListTag
            key={`list-${elements.length}`}
            className={`my-3 space-y-1.5 pl-6 ${
              listBuffer.type === "ul" ? "list-disc" : "list-decimal"
            } text-sm text-[#1f1f1f]`}
          >
            {listBuffer.items.map((item, idx) => (
              <li key={idx} className="leading-relaxed">
                {parseInline(item)}
              </li>
            ))}
          </ListTag>
        );
        listBuffer = null;
      }
    };

    const flushCode = () => {
      if (codeBuffer.length > 0) {
        elements.push(
          <div
            key={`code-${elements.length}`}
            className="my-3 p-3.5 bg-[#1e1e1e] text-[#d4d4d4] rounded-xl font-mono text-xs overflow-x-auto border border-gray-700 shadow-inner"
          >
            <pre>{codeBuffer.join("\n")}</pre>
          </div>
        );
        codeBuffer = [];
      }
    };

    const parseInline = (text: string): React.ReactNode => {
      // Bold text **text**, plus [N] citation markers when onCitationClick is set
      const splitPattern = onCitationClick
        ? /(\*\*.*?\*\*|\*.*?\*|`.*?`|\[\d+\])/g
        : /(\*\*.*?\*\*|\*.*?\*|`.*?`)/g;
      const parts = text.split(splitPattern);
      return parts.map((part, i) => {
        if (part.startsWith("**") && part.endsWith("**")) {
          return (
            <strong key={i} className="font-bold text-[#001d35]">
              {part.slice(2, -2)}
            </strong>
          );
        }
        if (part.startsWith("*") && part.endsWith("*")) {
          return (
            <em key={i} className="italic text-[#444746]">
              {part.slice(1, -1)}
            </em>
          );
        }
        if (part.startsWith("`") && part.endsWith("`")) {
          return (
            <code
              key={i}
              className="px-1.5 py-0.5 bg-[#f0f4f9] text-[#0b57d0] rounded font-mono text-xs border border-[#d3d7dc]"
            >
              {part.slice(1, -1)}
            </code>
          );
        }
        if (onCitationClick && /^\[\d+\]$/.test(part)) {
          const n = parseInt(part.slice(1, -1), 10);
          return (
            <button
              key={i}
              type="button"
              onClick={() => onCitationClick(n)}
              className="inline-flex items-center justify-center align-super ml-0.5 w-4 h-4 text-[10px] font-bold rounded-full bg-[#e8f0fe] hover:bg-[#c2e7ff] text-[#0b57d0] border border-[#c2d5f5] cursor-pointer leading-none"
              title={`Open source ${n}`}
            >
              {n}
            </button>
          );
        }
        return part;
      });
    };

    lines.forEach((line, lineIdx) => {
      const trimmed = line.trim();

      // Code Block Start/End ```
      if (trimmed.startsWith("```")) {
        if (inCodeBlock) {
          flushCode();
          inCodeBlock = false;
        } else {
          flushList();
          inCodeBlock = true;
        }
        return;
      }

      if (inCodeBlock) {
        codeBuffer.push(line);
        return;
      }

      // Headers ###, ##, #
      if (trimmed.startsWith("### ")) {
        flushList();
        elements.push(
          <h3
            key={`h3-${lineIdx}`}
            className="text-base font-bold text-[#001d35] mt-4 mb-2 pb-1 border-b border-[#e1e3e1]/60 flex items-center gap-1.5"
          >
            {parseInline(trimmed.slice(4))}
          </h3>
        );
        return;
      }
      if (trimmed.startsWith("## ")) {
        flushList();
        elements.push(
          <h2
            key={`h2-${lineIdx}`}
            className="text-lg font-extrabold text-[#001d35] mt-5 mb-2.5 pb-1 border-b border-[#0b57d0]/20"
          >
            {parseInline(trimmed.slice(3))}
          </h2>
        );
        return;
      }
      if (trimmed.startsWith("# ")) {
        flushList();
        elements.push(
          <h1
            key={`h1-${lineIdx}`}
            className="text-xl font-black text-[#0b57d0] mt-5 mb-3 pb-1 border-b-2 border-[#0b57d0]"
          >
            {parseInline(trimmed.slice(2))}
          </h1>
        );
        return;
      }

      // Unordered list items (* or -)
      if (trimmed.startsWith("* ") || trimmed.startsWith("- ")) {
        const itemText = trimmed.slice(2);
        if (!listBuffer || listBuffer.type !== "ul") {
          flushList();
          listBuffer = { type: "ul", items: [itemText] };
        } else {
          listBuffer.items.push(itemText);
        }
        return;
      }

      // Ordered list items (1. 2. etc)
      const olMatch = trimmed.match(/^(\d+)\.\s+(.*)/);
      if (olMatch) {
        const itemText = olMatch[2];
        if (!listBuffer || listBuffer.type !== "ol") {
          flushList();
          listBuffer = { type: "ol", items: [itemText] };
        } else {
          listBuffer.items.push(itemText);
        }
        return;
      }

      // Blockquotes (> quote)
      if (trimmed.startsWith("> ")) {
        flushList();
        elements.push(
          <blockquote
            key={`quote-${lineIdx}`}
            className="my-3 p-3 border-l-4 border-[#0b57d0] bg-[#f0f4f9] rounded-r-xl text-sm text-[#444746] italic"
          >
            {parseInline(trimmed.slice(2))}
          </blockquote>
        );
        return;
      }

      // Horizontal Rule ---
      if (trimmed === "---" || trimmed === "***") {
        flushList();
        elements.push(
          <hr key={`hr-${lineIdx}`} className="my-4 border-t border-[#e1e3e1]" />
        );
        return;
      }

      // Standard paragraph
      if (trimmed.length > 0) {
        flushList();
        elements.push(
          <p key={`p-${lineIdx}`} className="my-2 leading-relaxed text-sm text-[#1f1f1f]">
            {parseInline(line)}
          </p>
        );
      }
    });

    flushList();
    flushCode();

    return elements;
  };

  return <div className={`markdown-viewer space-y-1.5 ${className}`}>{renderMarkdown(content)}</div>;
}
