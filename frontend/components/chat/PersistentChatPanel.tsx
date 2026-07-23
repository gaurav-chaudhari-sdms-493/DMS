"use client";
import React, { useState, useEffect, useRef } from "react";
import {
  MessageSquare,
  Plus,
  Trash2,
  Send,
  Sparkles,
  FileText,
  Eye,
  Download,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Paperclip,
  X,
  Lightbulb,
  Search,
  Compass,
  FileUp,
  Bot
} from "lucide-react";
import { api } from "@/lib/api";
import type { ChatSession, ChatSessionListItem, ChatMessage, SearchResult, DocumentListItem } from "@/types";
import { MarkdownViewer } from "./MarkdownViewer";
import { ConfirmModal } from "@/components/ui/ConfirmModal";


interface PersistentChatPanelProps {
  onPreviewDocument: (doc: DocumentListItem) => void;
  initialQuery?: string;
}

export function PersistentChatPanel({ onPreviewDocument, initialQuery }: PersistentChatPanelProps) {
  const [sessions, setSessions] = useState<ChatSessionListItem[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [activeSession, setActiveSession] = useState<ChatSession | null>(null);

  const [query, setQuery] = useState("");
  const [sending, setSending] = useState(false);
  const [loadingSessions, setLoadingSessions] = useState(true);
  const [isDocsExpanded, setIsDocsExpanded] = useState(true);

  // File Attachments for Chat State
  const [attachedFiles, setAttachedFiles] = useState<File[]>([]);
  const [uploadingAttached, setUploadingAttached] = useState(false);
  const chatFileInputRef = useRef<HTMLInputElement | null>(null);

  // Custom Modal Dialog State
  const [modalConfig, setModalConfig] = useState<{
    isOpen: boolean;
    title?: string;
    message: string;
    type?: "danger" | "warning" | "info" | "success";
    confirmText?: string;
    showCancel?: boolean;
    onConfirm: () => void;
  }>({
    isOpen: false,
    message: "",
    onConfirm: () => {},
  });


  const messagesEndRef = useRef<HTMLDivElement | null>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [activeSession?.messages, sending]);

  // Load user sessions list on mount
  const loadSessionsList = async (selectSessionId?: string) => {
    try {
      setLoadingSessions(true);
      const list = await api.chat.listSessions();
      setSessions(list);

      if (selectSessionId) {
        loadSessionDetails(selectSessionId);
      } else if (list.length > 0 && !activeSessionId) {
        loadSessionDetails(list[0].id);
      } else if (list.length === 0) {
        handleCreateNewSession();
      }
    } catch (err) {
      console.error("Failed to load chat sessions:", err);
    } finally {
      setLoadingSessions(false);
    }
  };

  const loadSessionDetails = async (sessionId: string) => {
    try {
      setActiveSessionId(sessionId);
      const full = await api.chat.getSession(sessionId);
      setActiveSession(full);
    } catch (err) {
      console.error("Failed to load session details:", err);
    }
  };

  useEffect(() => {
    loadSessionsList();
  }, []);

  // Handle initial search query if passed from search bar
  useEffect(() => {
    if (initialQuery && initialQuery.trim()) {
      handleCreateNewSession(initialQuery);
    }
  }, [initialQuery]);

  const handleCreateNewSession = async (customInitialQuery?: string) => {
    try {
      const title = customInitialQuery ? customInitialQuery.slice(0, 30) : "New Chat";
      const newSession = await api.chat.createSession(title, customInitialQuery);
      setSessions((prev) => [
        {
          id: newSession.id,
          title: newSession.title,
          created_at: newSession.created_at,
          updated_at: newSession.updated_at,
          message_count: 0
        },
        ...prev
      ]);
      setActiveSessionId(newSession.id);
      setActiveSession(newSession);

      if (customInitialQuery) {
        handleSendMessage(customInitialQuery, newSession.id);
      }
    } catch (err) {
      console.error("Failed to create new chat session:", err);
    }
  };

  const handleDeleteSession = async (sessionId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setModalConfig({
      isOpen: true,
      title: "Delete Chat Thread",
      message: "Are you sure you want to delete this chat thread? This action cannot be undone.",
      type: "danger",
      confirmText: "Delete",
      showCancel: true,
      onConfirm: async () => {
        try {
          await api.chat.deleteSession(sessionId);
          const updatedList = sessions.filter((s) => s.id !== sessionId);
          setSessions(updatedList);

          if (activeSessionId === sessionId) {
            if (updatedList.length > 0) {
              loadSessionDetails(updatedList[0].id);
            } else {
              setActiveSession(null);
              setActiveSessionId(null);
              handleCreateNewSession();
            }
          }
        } catch (err) {
          console.error("Failed to delete session:", err);
        }
      },
    });
  };

  // Helper: Ensure "Chat Uploads" folder exists in Drive
  const ensureChatUploadsFolder = async (): Promise<string | null> => {
    try {
      const existing = await api.folders.list({ is_trashed: false });
      const found = existing.find((f) => f.name === "Chat Uploads");
      if (found) return found.id;

      const created = await api.folders.create("Chat Uploads", null, "#0b57d0");
      return created.id;
    } catch (err) {
      console.warn("Could not resolve Chat Uploads folder:", err);
      return null;
    }
  };

  const handleChatFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    if (files.length > 0) {
      setAttachedFiles((prev) => [...prev, ...files]);
    }
    if (chatFileInputRef.current) chatFileInputRef.current.value = "";
  };

  const removeAttachedFile = (index: number) => {
    setAttachedFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const handleSendMessage = async (customQuery?: string, targetSessionId?: string) => {
    let textToSend = customQuery || query;
    const sId = targetSessionId || activeSessionId;

    if ((!textToSend.trim() && attachedFiles.length === 0) || !sId || sending) return;

    if (!textToSend.trim() && attachedFiles.length > 0) {
      textToSend = "Please analyze and summarize the attached documents.";
    }

    if (!customQuery) {
      setQuery("");
    }
    setSending(true);

    // If files are attached, upload them into "Chat Uploads" folder first
    let attachedFileNames = "";
    if (attachedFiles.length > 0) {
      setUploadingAttached(true);
      try {
        const folderId = await ensureChatUploadsFolder();
        if (attachedFiles.length === 1) {
          await api.documents.upload(attachedFiles[0], folderId);
        } else {
          await api.documents.uploadBulk(attachedFiles, folderId);
        }
        attachedFileNames = attachedFiles.map((f) => f.name).join(", ");
        textToSend = `${textToSend}\n\n[Attached Context Files: ${attachedFileNames}]`;
        setAttachedFiles([]);
      } catch (err: any) {
        console.error("Failed to upload chat files:", err);
        setModalConfig({
          isOpen: true,
          title: "Upload Failed",
          message: err.message || "Failed to upload attached files.",
          type: "danger",
          showCancel: false,
          confirmText: "OK",
          onConfirm: () => {},
        });
        setSending(false);
        setUploadingAttached(false);
        return;
      } finally {
        setUploadingAttached(false);
      }
    }

    const tempUserMsg: ChatMessage = {
      id: `temp-${Date.now()}`,
      session_id: sId,
      role: "user",
      content: textToSend,
      created_at: new Date().toISOString()
    };

    setActiveSession((prev) => {
      if (!prev) return null;
      return {
        ...prev,
        messages: [...prev.messages, tempUserMsg]
      };
    });

    try {
      const reply = await api.chat.sendMessage(sId, textToSend);

      setActiveSession((prev) => {
        if (!prev) return null;
        const existingMsgs = prev.messages.filter((m) => !m.id.startsWith("temp-"));
        return {
          ...prev,
          messages: [...existingMsgs, tempUserMsg, reply]
        };
      });

      const updatedList = await api.chat.listSessions();
      setSessions(updatedList);
    } catch (err: any) {
      console.error("Failed to send chat message:", err);
      setModalConfig({
        isOpen: true,
        title: "Message Error",
        message: err.message || "Failed to send message.",
        type: "danger",
        showCancel: false,
        confirmText: "OK",
        onConfirm: () => {},
      });
    } finally {
      setSending(false);
    }
  };


  // Get active listed results from the latest assistant message with results
  const getActiveLoadedDocs = (): SearchResult[] => {
    if (!activeSession?.messages) return [];
    for (let i = activeSession.messages.length - 1; i >= 0; i--) {
      const m = activeSession.messages[i];
      if (m.role === "assistant" && m.results && m.results.length > 0) {
        return m.results;
      }
    }
    return [];
  };

  const activeLoadedDocs = getActiveLoadedDocs();

  const handlePreviewCard = (res: SearchResult) => {
    const docItem: DocumentListItem = {
      id: res.document_id,
      title: res.document_name,
      status: "indexed",
      created_at: new Date().toISOString(),
      file_size_bytes: 1024,
      is_starred: false,
      is_trashed: false,
      download_url: res.download_url
    };
    onPreviewDocument(docItem);
  };

  // ChatGPT FAQ Dynamic Prompt Suggestions
  const faqSuggestions = [
    {
      icon: Lightbulb,
      title: "Summarize Insights",
      prompt: "Summarize key findings, main decisions, and action items from my uploaded files.",
      bg: "bg-amber-50 hover:bg-amber-100/70 border-amber-200/60 text-amber-900"
    },
    {
      icon: Search,
      title: "Financial & Invoices",
      prompt: "Find all financial metrics, total costs, invoices, and pricing details in my documents.",
      bg: "bg-emerald-50 hover:bg-emerald-100/70 border-emerald-200/60 text-emerald-900"
    },
    {
      icon: FileText,
      title: "Policy & Agreement Compare",
      prompt: "Compare terms, rules, conditions, and compliance requirements across policy documents.",
      bg: "bg-blue-50 hover:bg-blue-100/70 border-blue-200/60 text-blue-900"
    },
    {
      icon: Compass,
      title: "Topic Discovery",
      prompt: "What are the primary topics, project updates, and metadata stored in my repository?",
      bg: "bg-purple-50 hover:bg-purple-100/70 border-purple-200/60 text-purple-900"
    }
  ];

  return (
    <div className="flex-1 flex h-full bg-[#f8fafd] rounded-3xl border border-[#e1e3e1] shadow-sm overflow-hidden select-none">
      {/* Hidden File Input for Chat Attachments */}
      <input
        type="file"
        multiple
        ref={chatFileInputRef}
        onChange={handleChatFileSelect}
        className="hidden"
      />

      {/* Chat Threads Sidebar */}
      <div className="w-64 border-r border-[#e1e3e1] bg-white flex flex-col justify-between">
        <div className="p-4 border-b border-[#e1e3e1]">
          <button
            onClick={() => handleCreateNewSession()}
            className="w-full flex items-center justify-center gap-2 py-2.5 px-4 bg-[#0b57d0] hover:bg-[#0945a5] text-white font-semibold rounded-2xl shadow-sm transition-all text-sm"
          >
            <Plus className="w-4 h-4 stroke-[2.5]" />
            <span>New Chat</span>
          </button>
        </div>

        {/* Sessions list */}
        <div className="flex-1 overflow-y-auto p-2 space-y-1">
          <div className="px-3 py-2 text-xs font-semibold text-[#444746] uppercase tracking-wider">
            Chat History
          </div>

          {loadingSessions ? (
            <div className="px-4 py-8 text-center text-xs text-[#444746] animate-pulse">
              Loading chat history...
            </div>
          ) : sessions.length === 0 ? (
            <div className="px-4 py-6 text-center text-xs text-[#747775]">
              No chats yet. Start a new one!
            </div>
          ) : (
            sessions.map((s) => (
              <div
                key={s.id}
                onClick={() => loadSessionDetails(s.id)}
                className={`group flex items-center justify-between px-3 py-2.5 rounded-xl cursor-pointer text-sm font-medium transition-all ${
                  activeSessionId === s.id
                    ? "bg-[#c2e7ff] text-[#001d35] font-bold"
                    : "text-[#444746] hover:bg-[#edf2fc] hover:text-[#1f1f1f]"
                }`}
              >
                <div className="flex items-center gap-2.5 truncate">
                  <MessageSquare className="w-4 h-4 flex-shrink-0 text-[#0b57d0]" />
                  <span className="truncate">{s.title}</span>
                </div>

                <button
                  onClick={(e) => handleDeleteSession(s.id, e)}
                  className="opacity-0 group-hover:opacity-100 p-1 text-[#747775] hover:text-red-600 rounded-lg hover:bg-white/60 transition-all"
                  title="Delete chat thread"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            ))
          )}
        </div>

        {/* Footer info */}
        <div className="p-3 border-t border-[#e1e3e1] bg-[#f8fafd] text-[11px] text-[#747775] flex items-center gap-2">
          <Sparkles className="w-3.5 h-3.5 text-[#0b57d0]" />
          <span>Powered by Stark AI Engine</span>
        </div>
      </div>

      {/* Main Conversation Canvas */}
      <div className="flex-1 flex flex-col bg-white overflow-hidden">
        {/* Header */}
        <div className="px-6 py-4 border-b border-[#e1e3e1] flex items-center justify-between bg-white shadow-xs">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-[#0b57d0] text-white flex items-center justify-center shadow-md">
              <Bot className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-[#1f1f1f]">
                {activeSession?.title === "New Persistent Chat" ? "Stark AI Assistant" : activeSession?.title || "Stark AI Assistant"}
              </h2>
              <div className="flex items-center gap-2 text-xs text-[#444746] mt-0.5">
                <span className="flex items-center gap-1 font-medium text-[#0b57d0]">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  Grounded in My Drive
                </span>
                {activeLoadedDocs.length > 0 && (
                  <>
                    <span>•</span>
                    <span>{activeLoadedDocs.length} documents loaded</span>
                  </>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* LOADED DOCUMENTS SHOWN ONLY ONCE AT THE TOP */}
        {activeLoadedDocs.length > 0 && (
          <div className="bg-[#f8fafd] border-b border-[#e1e3e1] transition-all">
            <button
              onClick={() => setIsDocsExpanded(!isDocsExpanded)}
              className="w-full px-6 py-2.5 flex items-center justify-between hover:bg-[#f0f4f9] transition-colors text-left"
            >
              <div className="flex items-center gap-2">
                <FileText className="w-4 h-4 text-[#0b57d0]" />
                <span className="text-xs font-bold text-[#1f1f1f]">
                  Loaded Context Documents ({activeLoadedDocs.length})
                </span>
              </div>
              <div className="flex items-center gap-1 text-xs text-[#0b57d0] font-semibold">
                <span>{isDocsExpanded ? "Hide Documents" : "Show Documents"}</span>
                {isDocsExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
              </div>
            </button>

            {isDocsExpanded && (
              <div className="p-4 pt-0 max-h-[220px] overflow-y-auto grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 border-t border-[#e1e3e1]/50">
                {activeLoadedDocs.map((res, idx) => {
                  const scorePct = Math.round((res.score || 0) * 100);
                  const isHigh = scorePct >= 85;

                  return (
                    <div
                      key={`${res.document_id}-${idx}`}
                      className="p-3 rounded-2xl bg-white border border-[#e1e3e1] hover:border-[#0b57d0]/40 transition-all space-y-2 shadow-2xs"
                    >
                      <div className="flex items-center justify-between gap-2">
                        <div className="flex items-center gap-2 min-w-0">
                          <FileText className="w-4 h-4 text-[#0b57d0] flex-shrink-0" />
                          <span className="font-semibold text-xs text-[#1f1f1f] truncate">
                            {res.document_name}
                          </span>
                        </div>

                        <span
                          className={`px-2 py-0.5 rounded-full text-[10px] font-bold border ${
                            isHigh
                              ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                              : "bg-blue-50 text-blue-700 border-blue-200"
                          }`}
                        >
                          {scorePct}% Match
                        </span>
                      </div>

                      <p className="text-[11px] text-[#444746] line-clamp-2 italic bg-[#f8fafd] p-2 rounded-xl border border-[#e1e3e1]/40">
                        "{res.snippet}"
                      </p>

                      <div className="flex items-center justify-between pt-1">
                        <button
                          onClick={() => handlePreviewCard(res)}
                          className="flex items-center gap-1 text-xs font-semibold text-[#0b57d0] hover:underline"
                        >
                          <Eye className="w-3.5 h-3.5" />
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
                            <Download className="w-3.5 h-3.5" />
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

        {/* Message Stream */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6 bg-[#fcfdfe]">
          {activeSession?.messages && activeSession.messages.length > 0 ? (
            activeSession.messages.map((m) => (
              <div
                key={m.id}
                className={`flex flex-col ${m.role === "user" ? "items-end" : "items-start"} space-y-2`}
              >
                <div className="flex items-center gap-2 px-1 text-xs text-[#747775]">
                  <span className="font-semibold">
                    {m.role === "user" ? "You" : "Stark AI Assistant"}
                  </span>
                  <span>•</span>
                  <span>{new Date(m.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</span>
                </div>

                {/* Message Bubble */}
                <div
                  className={`max-w-[85%] rounded-3xl p-5 shadow-xs ${
                    m.role === "user"
                      ? "bg-[#0b57d0] text-white rounded-tr-xs font-medium shadow-md"
                      : "bg-white border border-[#e1e3e1] text-[#1f1f1f] rounded-tl-xs shadow-xs"
                  }`}
                >
                  {/* Markdown Answer Text */}
                  {m.role === "user" ? (
                    <div className="text-sm leading-relaxed whitespace-pre-wrap font-normal">
                      {m.content}
                    </div>
                  ) : (
                    <MarkdownViewer content={m.content} />
                  )}
                </div>
              </div>
            ))
          ) : (
            /* ChatGPT Empty State with Dynamic Prompt Cards */
            <div className="h-full flex flex-col items-center justify-center text-center py-8 px-4 max-w-3xl mx-auto">
              <div className="w-16 h-16 rounded-3xl bg-[#0b57d0] text-white flex items-center justify-center mb-4 shadow-xl shadow-[#0b57d0]/20">
                <Sparkles className="w-8 h-8" />
              </div>
              <h3 className="text-2xl font-bold text-[#1f1f1f] mb-1">Stark AI Assistant</h3>
              <p className="text-sm text-[#444746] max-w-md mb-8">
                Ask questions across your entire Drive repository or upload files below to chat directly with specific documents.
              </p>

              {/* Dynamic ChatGPT FAQ Prompt Cards */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 w-full text-left">
                {faqSuggestions.map((card, idx) => {
                  const CardIcon = card.icon;
                  return (
                    <button
                      key={idx}
                      onClick={() => handleSendMessage(card.prompt)}
                      className={`p-4 rounded-2xl border transition-all duration-200 group flex flex-col justify-between ${card.bg} shadow-2xs hover:shadow-md cursor-pointer`}
                    >
                      <div className="flex items-center gap-2 font-bold text-sm mb-1">
                        <CardIcon className="w-4 h-4 flex-shrink-0" />
                        <span>{card.title}</span>
                      </div>
                      <p className="text-xs opacity-80 leading-relaxed font-normal">
                        "{card.prompt}"
                      </p>
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {sending && (
            <div className="flex items-center gap-3 p-4 bg-white border border-[#e1e3e1] rounded-2xl max-w-xs animate-pulse shadow-sm">
              <Sparkles className="w-4 h-4 text-[#0b57d0] animate-spin" />
              <span className="text-xs font-semibold text-[#444746]">
                {uploadingAttached ? "Uploading attached documents..." : "Stark AI is searching & thinking..."}
              </span>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* ChatGPT Style Input Controls Bar */}
        <div className="p-4 bg-white border-t border-[#e1e3e1]">
          {/* Attached Files Badges Pill */}
          {attachedFiles.length > 0 && (
            <div className="flex items-center gap-2 mb-2 overflow-x-auto pb-1">
              <span className="text-xs font-semibold text-[#444746] flex items-center gap-1">
                <FileUp className="w-3.5 h-3.5 text-[#0b57d0]" />
                Attached:
              </span>
              {attachedFiles.map((file, idx) => (
                <div
                  key={idx}
                  className="flex items-center gap-1.5 px-3 py-1 bg-blue-50 border border-blue-200 text-[#0b57d0] rounded-full text-xs font-medium"
                >
                  <FileText className="w-3.5 h-3.5" />
                  <span className="truncate max-w-[140px]">{file.name}</span>
                  <button
                    onClick={() => removeAttachedFile(idx)}
                    className="p-0.5 hover:bg-blue-100 rounded-full transition-colors"
                  >
                    <X className="w-3 h-3 text-[#0b57d0]" />
                  </button>
                </div>
              ))}
            </div>
          )}

          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSendMessage();
            }}
            className="flex items-center gap-2 bg-[#f0f4f9] rounded-3xl p-2 pl-4 border border-[#d3d7dc] focus-within:border-[#0b57d0] focus-within:bg-white transition-all shadow-xs"
          >
            {/* Paperclip Button for Chat File Attachments */}
            <button
              type="button"
              onClick={() => chatFileInputRef.current?.click()}
              className="p-2 text-[#444746] hover:text-[#0b57d0] hover:bg-[#e1e5ea] rounded-full transition-all"
              title="Attach document(s) to chat"
            >
              <Paperclip className="w-5 h-5" />
            </button>

            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Ask anything or attach file(s) to chat with documents..."
              className="flex-1 bg-transparent text-sm text-[#1f1f1f] focus:outline-none placeholder-[#747775]"
            />

            <button
              type="submit"
              disabled={(!query.trim() && attachedFiles.length === 0) || sending}
              className="p-2.5 bg-[#0b57d0] hover:bg-[#0945a5] disabled:opacity-40 text-white rounded-full shadow-xs transition-all flex items-center justify-center"
            >
              <Send className="w-4 h-4 stroke-[2.5]" />
            </button>
          </form>
        </div>
      </div>

      {/* Custom Stark AI Confirm & Alert Modal */}
      <ConfirmModal
        isOpen={modalConfig.isOpen}
        title={modalConfig.title}
        message={modalConfig.message}
        type={modalConfig.type}
        confirmText={modalConfig.confirmText}
        showCancel={modalConfig.showCancel}
        onConfirm={modalConfig.onConfirm}
        onClose={() => setModalConfig((prev) => ({ ...prev, isOpen: false }))}
      />
    </div>
  );
}


