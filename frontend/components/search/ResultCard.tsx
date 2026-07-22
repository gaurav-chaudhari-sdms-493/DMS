import React from "react";
import { FileText, Download } from "lucide-react";
import { Card } from "../ui/Card";
import type { SearchResult } from "@/types";
import { Badge } from "../ui/Badge";

interface ResultCardProps {
  result: SearchResult;
}

export const ResultCard: React.FC<ResultCardProps> = ({ result }) => {
  // Safely render backend-highlighted HTML (bold match terms)
  const createMarkup = (html: string) => {
    return { __html: html };
  };

  const getFileExtension = (filename: string): string => {
    const parts = filename.split(".");
    return parts.length > 1 ? parts[parts.length - 1].toLowerCase() : "";
  };

  const ext = getFileExtension(result.document_name);

  const getIconColor = (extension: string) => {
    if (extension === "pdf") return "text-red-500 bg-red-500/10 border-red-500/20";
    if (extension === "txt") return "text-blue-500 bg-blue-500/10 border-blue-500/20";
    if (extension === "docx" || extension === "doc") return "text-success bg-success/10 border-success/20";
    return "text-primary bg-primary/10 border-primary/20";
  };

  const getMatchGlow = (score: number) => {
    const pct = Math.round(score * 100);
    if (pct > 80) return "text-success bg-success/10 border-success/20 shadow-[0_0_15px_rgba(16,185,129,0.15)]";
    if (pct > 50) return "text-yellow-500 bg-yellow-500/10 border-yellow-500/20";
    if (pct > 20) return "text-primary bg-primary/10 border-primary/20";
    return "text-textMuted bg-surface border-borderDark";
  };

  const getProgressBarColor = (score: number) => {
    const pct = Math.round(score * 100);
    if (pct > 80) return "bg-success";
    if (pct > 50) return "bg-yellow-500";
    if (pct > 20) return "bg-primary";
    return "bg-textMuted";
  };

  const matchPct = Math.round(result.score * 100);

  // Extract custom metadata items
  const metadata = (result.metadata || {}) as Record<string, any>;
  const author = metadata.author as string | undefined;
  const date = metadata.date as string | undefined;
  const keyTopics = metadata.key_topics;

  const topicsList = Array.isArray(keyTopics) 
    ? keyTopics 
    : typeof keyTopics === "string" 
      ? JSON.parse(keyTopics) as string[]
      : [] as string[];

  return (
    <Card glow className="hover:border-primary/50 group animate-fadeIn flex flex-col gap-4">
      {/* File Title and Page */}
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3 overflow-hidden">
          <div className={`p-2.5 rounded-lg border transition-colors ${getIconColor(ext)}`}>
            <FileText className="w-5 h-5" />
          </div>
          <div className="flex flex-col min-w-0">
            <h4 className="font-bold text-textMain text-base truncate group-hover:text-primary transition-colors" title={result.document_name}>
              {result.document_name}
            </h4>
            
            {/* Author and Date if present */}
            {(author || date) && (
              <div className="flex items-center gap-3 mt-1 text-xs text-textMuted flex-wrap">
                {author && (
                  <span className="flex items-center gap-1">
                    <User className="w-3.5 h-3.5" />
                    {author}
                  </span>
                )}
                {date && (
                  <span className="flex items-center gap-1">
                    <Calendar className="w-3.5 h-3.5" />
                    {date}
                  </span>
                )}
              </div>
            )}
          </div>
        </div>
        
        {result.page_number && (
          <Badge status="default" className="shrink-0 ml-2">
            Page {result.page_number}
          </Badge>
        )}
      </div>

      {/* Snippet preview — dark navy background, light gray text, indigo bold highlights */}
      <div
        className="text-sm leading-relaxed p-3 rounded-lg border border-indigo-900/40 not-italic"
        style={{
          backgroundColor: "#0f1420",
          color: "#e2e8f0",
          fontStyle: "normal",
        }}
        dangerouslySetInnerHTML={createMarkup(result.snippet)}
      />

      <div className="flex items-center justify-between mt-auto pt-2 border-t border-borderDark">
        <div className="flex items-center gap-2">
          <div className="w-16 h-1.5 bg-surface rounded-full overflow-hidden" title={`Relevance: ${Math.round(result.score * 100)}%`}>
            <div
              className={`h-full rounded-full ${getScoreColor(result.score)}`}
              style={{ width: `${Math.max(10, result.score * 100)}%` }}
            />
          </div>
          <span className={`text-xs font-semibold px-2.5 py-0.5 rounded-full border transition-all duration-300 ${getMatchGlow(result.score)}`}>
            {matchPct}% Match
          </span>
        </div>

        <a
          href={result.download_url}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-1.5 text-xs font-medium text-primary hover:text-indigo-400 transition-colors"
        >
          <Download className="w-3.5 h-3.5" />
          Download
        </a>
      </div>
    </Card>
  );
};
