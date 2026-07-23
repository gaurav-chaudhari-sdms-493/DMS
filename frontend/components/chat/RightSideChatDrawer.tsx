"use client";
import React, { useState, useEffect, useRef, useMemo } from "react";
import {
  Sparkles,
  X,
  Send,
  FileText,
  Eye,
  Download,
  Filter,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Tag,
  Layers,
  ArrowUpDown
} from "lucide-react";
import { api } from "@/lib/api";
import type { ChatSession, ChatMessage, SearchResult, DocumentListItem } from "@/types";
import { MarkdownViewer } from "./MarkdownViewer";

interface RightSideChatDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  initialQuery?: string;
  initialResults?: SearchResult[];
  onPreviewDocument: (doc: DocumentListItem) => void;
}

export function RightSideChatDrawer({
  isOpen,
  onClose,
  initialQuery,
  initialResults,
  onPreviewDocument,
}: RightSideChatDrawerProps) {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputQuery, setInputQuery] = useState("");
  const [sending, setSending] = useState(false);
  const [sessionTitle, setSessionTitle] = useState("Persistent Chat");
  const [loadedDocs, setLoadedDocs] = useState<SearchResult[]>([]);
  const [isDocsExpanded, setIsDocsExpanded] = useState(true);

  const messagesEndRef = useRef<HTMLDivElement | null>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, sending]);

  // Keep loaded docs state synced with initialResults or latest assistant results
  useEffect(() => {
    if (initialResults && initialResults.length > 0) {
      setLoadedDocs(initialResults);
    }
  }, [initialResults]);

  // When opened with a new search query, initialize/fetch session
  useEffect(() => {
    if (isOpen && initialQuery) {
      initSessionWithQuery(initialQuery);
    }
  }, [isOpen, initialQuery]);

  const initSessionWithQuery = async (queryText: string) => {
    try {
      setSending(true);
      const newSession = await api.chat.createSession(queryText.slice(0, 35));
      setSessionId(newSession.id);
      setSessionTitle(newSession.title);

      const reply = await api.chat.sendMessage(newSession.id, queryText);
      if (reply.results && reply.results.length > 0) {
        setLoadedDocs(reply.results);
      }

      setMessages([
        {
          id: `user-init-${Date.now()}`,
          session_id: newSession.id,
          role: "user",
          content: queryText,
          created_at: new Date().toISOString()
        },
        reply
      ]);
    } catch (err) {
      console.error("Failed to initialize right chat session:", err);
      if (initialResults) {
        setLoadedDocs(initialResults);
        setMessages([
          {
            id: `init-user`,
            session_id: "local",
            role: "user",
            content: queryText,
            created_at: new Date().toISOString()
          },
          {
            id: `init-assistant`,
            session_id: "local",
            role: "assistant",
            content: `I have loaded ${initialResults.length} documents for "${queryText}". You can search, filter (e.g., score >= 85), list, or ask any question related to these loaded files.`,
            results: initialResults,
            created_at: new Date().toISOString()
          }
        ]);
      }
    } finally {
      setSending(false);
    }
  };

  const handleSendMessage = async (textToSend?: string) => {
    const q = textToSend || inputQuery;
    if (!q.trim() || sending) return;

    if (!textToSend) setInputQuery("");
    setSending(true);

    const tempMsg: ChatMessage = {
      id: `temp-${Date.now()}`,
      session_id: sessionId || "temp",
      role: "user",
      content: q,
      created_at: new Date().toISOString()
    };

    setMessages((prev) => [...prev, tempMsg]);

    try {
      let targetSessionId = sessionId;
      if (!targetSessionId) {
        const created = await api.chat.createSession(q.slice(0, 30));
        targetSessionId = created.id;
        setSessionId(created.id);
      }

      const reply = await api.chat.sendMessage(targetSessionId, q);
      if (reply.results && reply.results.length > 0) {
        setLoadedDocs(reply.results);
      }
      setMessages((prev) => [...prev.filter((m) => !m.id.startsWith("temp-")), tempMsg, reply]);
    } catch (err: any) {
      console.error("Failed to send message in right drawer:", err);
    } finally {
      setSending(false);
    }
  };

  // DYNAMIC CONTEXT-BASED QUICK FILTERS
  const dynamicFilters = useMemo(() => {
    const chips: { label: string; actionQuery: string; icon: "tag" | "score" | "list" | "sort" }[] = [];

    // 1. Extract dynamic tags from loaded docs
    const tagCounts: Record<string, number> = {};
    loadedDocs.forEach((doc) => {
      if (doc.tags && Array.isArray(doc.tags)) {
        doc.tags.forEach((t) => {
          if (t && t.trim()) {
            const tagClean = t.trim();
            tagCounts[tagClean] = (tagCounts[tagClean] || 0) + 1;
          }
        });
      }
    });

    const sortedTags = Object.entries(tagCounts)
      .sort((a, b) => b[1] - a[1])
      .map(([tag]) => tag);

    sortedTags.slice(0, 4).forEach((tag) => {
      chips.push({
        label: tag,
        actionQuery: `filter documents related to ${tag}`,
        icon: "tag"
      });
    });

    // 2. Score threshold chip if high score docs exist
    const hasHighScore = loadedDocs.some((d) => (d.score || 0) >= 0.85);
    if (hasHighScore) {
      chips.push({
        label: "Score >= 85",
        actionQuery: "filter documents which have score >= 85",
        icon: "score"
      });
    }

    // 3. Fallback context chips if tags are scarce
    if (chips.length < 3) {
      chips.push({
        label: "List Loaded Docs",
        actionQuery: "list all loaded documents with details",
        icon: "list"
      });
      chips.push({
        label: "Sort by Score",
        actionQuery: "sort documents by highest match score",
        icon: "sort"
      });
    }

    return chips;
  }, [loadedDocs]);

  if (!isOpen) return null;

  return (
    <aside className="w-[420px] flex-shrink-0 bg-white border-l border-[#e1e3e1] flex flex-col h-full select-none z-30 shadow-lg animate-fadeIn">
      {/* Drawer Header */}
      <div className="p-3.5 border-b border-[#e1e3e1] flex items-center justify-between bg-[#f8fafd]">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-lg bg-blue-50 text-[#0b57d0] flex items-center justify-center border border-blue-100 shadow-xs">
            <Sparkles className="w-3.5 h-3.5" />
          </div>
          <div>
            <h3 className="text-xs font-bold text-[#1f1f1f] truncate max-w-[220px]">
              {sessionTitle}
            </h3>
            <div className="flex items-center gap-1 text-[10px] text-[#0b57d0] font-semibold">
              <CheckCircle2 className="w-3 h-3" />
              <span>Grounded in Loaded Files</span>
            </div>
          </div>
        </div>

        <button
          onClick={onClose}
          className="p-1 rounded-full text-[#444746] hover:bg-[#e1e3e1] transition-colors"
          title="Close persistent chat"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* DYNAMIC CONTEXT-BASED QUICK FILTER BAR */}
      <div className="px-3 py-2 bg-white border-b border-[#e1e3e1]/60 flex items-center gap-1.5 overflow-x-auto text-xs scrollbar-none">
        <span className="text-[10px] font-bold text-[#747775] uppercase tracking-wider flex-shrink-0 mr-1">
          Context Filters:
        </span>

        {dynamicFilters.map((chip, idx) => (
          <button
            key={`${chip.label}-${idx}`}
            onClick={() => handleSendMessage(chip.actionQuery)}
            className="flex items-center gap-1 px-2.5 py-1 bg-[#f0f4f9] hover:bg-[#e1e5ea] text-[#001d35] rounded-full text-[11px] font-semibold border border-[#d3d7dc] flex-shrink-0 transition-all hover:scale-105"
          >
            {chip.icon === "tag" && <Tag className="w-3 h-3 text-[#0b57d0]" />}
            {chip.icon === "score" && <Filter className="w-3 h-3 text-[#108554]" />}
            {chip.icon === "list" && <Layers className="w-3 h-3 text-[#00639b]" />}
            {chip.icon === "sort" && <ArrowUpDown className="w-3 h-3 text-[#b45309]" />}
            <span>{chip.label}</span>
          </button>
        ))}
      </div>

      {/* LOADED DOCUMENTS SHOWN ONLY ONCE AT THE TOP */}
      {loadedDocs.length > 0 && (
        <div className="bg-[#f8fafd] border-b border-[#e1e3e1] overflow-hidden transition-all">
          <button
            onClick={() => setIsDocsExpanded(!isDocsExpanded)}
            className="w-full px-3.5 py-2 flex items-center justify-between hover:bg-[#f0f4f9] transition-colors text-left"
          >
            <div className="flex items-center gap-2">
              <FileText className="w-3.5 h-3.5 text-[#0b57d0]" />
              <span className="text-xs font-bold text-[#1f1f1f]">
                Loaded Context Documents ({loadedDocs.length})
              </span>
            </div>
            <div className="flex items-center gap-1 text-[11px] text-[#0b57d0] font-semibold">
              <span>{isDocsExpanded ? "Hide" : "Show"}</span>
              {isDocsExpanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
            </div>
          </button>

          {isDocsExpanded && (
            <div className="p-3 pt-0 max-h-[190px] overflow-y-auto space-y-2 border-t border-[#e1e3e1]/50">
              {loadedDocs.map((res, idx) => {
                const scorePct = Math.round((res.score || 0) * 100);
                const isHigh = scorePct >= 85;

                return (
                  <div
                    key={`${res.document_id}-${idx}`}
                    className="p-2 rounded-xl bg-white border border-[#e1e3e1] hover:border-[#0b57d0]/40 transition-all space-y-1.5 shadow-2xs"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex items-center gap-1.5 min-w-0">
                        <FileText className="w-3.5 h-3.5 text-[#0b57d0] flex-shrink-0" />
                        <span className="font-semibold text-xs text-[#1f1f1f] truncate">
                          {res.document_name}
                        </span>
                      </div>

                      <span
                        className={`px-1.5 py-0.5 rounded-full text-[10px] font-bold border ${
                          isHigh
                            ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                            : "bg-blue-50 text-blue-700 border-blue-200"
                        }`}
                      >
                        {scorePct}% Match
                      </span>
                    </div>

                    <p className="text-[11px] text-[#444746] line-clamp-2 italic bg-[#f8fafd] p-1.5 rounded-lg border border-[#e1e3e1]/40">
                      "{res.snippet}"
                    </p>

                    <div className="flex items-center justify-between pt-0.5">
                      <button
                        onClick={() =>
                          onPreviewDocument({
                            id: res.document_id,
                            title: res.document_name,
                            status: "indexed",
                            created_at: new Date().toISOString(),
                            file_size_bytes: 1024,
                            is_starred: false,
                            is_trashed: false,
                            download_url: res.download_url
                          })
                        }
                        className="flex items-center gap-1 text-[11px] font-semibold text-[#0b57d0] hover:underline"
                      >
                        <Eye className="w-3 h-3" />
                        <span>Preview</span>
                      </button>

                      {res.download_url && (
                        <a
                          href={res.download_url}
                          target="_blank"
                          rel="noreferrer"
                          className="p-1 text-[#747775] hover:text-[#0b57d0]"
                          title="Download document"
                        >
                          <Download className="w-3 h-3" />
                        </a>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* CONVERSATION MESSAGE STREAM WITH MARKDOWN VIEWER */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-[#fcfdfe]">
        {messages.map((m) => (
          <div
            key={m.id}
            className={`flex flex-col ${m.role === "user" ? "items-end" : "items-start"} space-y-1`}
          >
            <div className="text-[10px] text-[#747775] px-1 font-semibold">
              {m.role === "user" ? "You" : "AI Assistant"}
            </div>

            <div
              className={`max-w-[94%] rounded-2xl p-3.5 shadow-2xs text-xs leading-relaxed ${
                m.role === "user"
                  ? "bg-[#c2e7ff] text-[#001d35] rounded-tr-xs font-medium"
                  : "bg-white border border-[#e1e3e1] text-[#1f1f1f] rounded-tl-xs"
              }`}
            >
              {m.role === "user" ? (
                <div className="whitespace-pre-wrap">{m.content}</div>
              ) : (
                <MarkdownViewer content={m.content} />
              )}
            </div>
          </div>
        ))}

        {sending && (
          <div className="flex items-center gap-2 p-3 bg-white border border-[#e1e3e1] rounded-xl text-xs text-[#444746] animate-pulse">
            <Sparkles className="w-3.5 h-3.5 text-[#0b57d0] animate-spin" />
            <span>Evaluating prompt against loaded context...</span>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Form */}
      <div className="p-3 bg-white border-t border-[#e1e3e1]">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSendMessage();
          }}
          className="flex items-center gap-2 bg-[#f0f4f9] rounded-xl p-1.5 pl-3 border border-[#d3d7dc] focus-within:border-[#0b57d0] focus-within:bg-white transition-all"
        >
          <input
            type="text"
            value={inputQuery}
            onChange={(e) => setInputQuery(e.target.value)}
            placeholder="Ask anything or filter loaded docs..."
            className="flex-1 bg-transparent text-xs text-[#1f1f1f] focus:outline-none placeholder-[#747775]"
          />

          <button
            type="submit"
            disabled={!inputQuery.trim() || sending}
            className="p-2 bg-[#0b57d0] hover:bg-[#0945a5] disabled:opacity-40 text-white rounded-lg transition-all"
          >
            <Send className="w-3.5 h-3.5" />
          </button>
        </form>
      </div>
    </aside>
  );
}
