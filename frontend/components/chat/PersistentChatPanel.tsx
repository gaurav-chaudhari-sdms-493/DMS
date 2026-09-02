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
  Bot,
  PanelLeftClose,
  PanelLeft
} from "lucide-react";
import { api } from "@/lib/api";
import { onKeyActivate } from "@/lib/a11y";
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
  const [isDocsExpanded, setIsDocsExpanded] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);

  // File Attachments for Chat State
  const [attachedFiles, setAttachedFiles] = useState<File[]>([]);
  const [attachmentPreviews, setAttachmentPreviews] = useState<Record<string, string>>({});
  const [uploadingAttached, setUploadingAttached] = useState(false);
  const [processingStatus, setProcessingStatus] = useState<string>("Stark AI is thinking...");
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
      setAttachmentPreviews((prev) => {
        const updated = { ...prev };
        files.forEach((file) => {
          if (file.type.startsWith("image/") || /\.(jpg|jpeg|png|webp|gif|svg)$/i.test(file.name)) {
            updated[file.name] = URL.createObjectURL(file);
          }
        });
        return updated;
      });
    }
    if (chatFileInputRef.current) chatFileInputRef.current.value = "";
  };

  const removeAttachedFile = (index: number) => {
    setAttachedFiles((prev) => prev.filter((_, i) => i !== index));
  };

  // Helper: Poll document status dynamically until Celery worker OCR & vector embedding completes
  const waitForDocumentsIndexing = async (docIds: string[], onProgress?: (msg: string) => void): Promise<boolean> => {
    if (docIds.length === 0) return true;

    const pollInterval = 1000; // poll every 1s

    while (true) {
      try {
        const docs = await Promise.all(
          docIds.map((id) => api.documents.get(id).catch(() => null))
        );

        const allFinished = docs.every((d) => d && (d.status === "indexed" || d.status === "failed"));
        const indexedCount = docs.filter((d) => d && d.status === "indexed").length;

        if (onProgress) {
          onProgress(`Extracting OCR text & AI embeddings... (${indexedCount}/${docIds.length} ready)`);
        }

        if (allFinished) {
          return indexedCount > 0;
        }
      } catch (err) {
        console.warn("Polling document status notice:", err);
      }
      await new Promise((res) => setTimeout(res, pollInterval));
    }
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
    setProcessingStatus("Preparing request...");

    // If files are attached, upload them into "Chat Uploads" folder first & wait for OCR/indexing
    let attachedFileNames = "";
    if (attachedFiles.length > 0) {
      setUploadingAttached(true);
      setProcessingStatus("Uploading attached document(s) to DMS...");
      try {
        const folderId = await ensureChatUploadsFolder();
        const uploadedDocIds: string[] = [];

        if (attachedFiles.length === 1) {
          const res = await api.documents.upload(attachedFiles[0], folderId);
          if (res?.document_id) uploadedDocIds.push(res.document_id);
        } else {
          const res = await api.documents.uploadBulk(attachedFiles, folderId);
          if (res?.documents) {
            res.documents.forEach((d: any) => {
              if (d.document_id) uploadedDocIds.push(d.document_id);
            });
          }
        }

        attachedFileNames = attachedFiles.map((f) => f.name).join(", ");
        textToSend = `${textToSend}\n\n[Attached Context Files: ${attachedFileNames}]`;
        setAttachedFiles([]);

        // Wait for Celery worker OCR & Qdrant vector indexing to complete!
        if (uploadedDocIds.length > 0) {
          setProcessingStatus("Extracting OCR text & indexing attached file(s) for AI RAG...");
          const isReady = await waitForDocumentsIndexing(uploadedDocIds, (msg) => setProcessingStatus(msg));
          if (!isReady) {
            throw new Error("Document text extraction & AI indexing is still processing in background. Please wait a moment and send your prompt again.");
          }
        }

      } catch (err: any) {
        console.error("Failed to upload/process chat files:", err);
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

    setProcessingStatus("Stark AI is analyzing context & generating response...");

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
      await api.chat.sendMessage(sId, textToSend);

      const refreshed = await api.chat.getSession(sId);
      if (refreshed) {
        setActiveSession(refreshed);
      }

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

  const parseUserMessage = (content: string) => {
    const match = content.match(/\n\n\[Attached Context Files: (.*?)\]$/) || content.match(/\[Attached Context Files: (.*?)\]$/);
    const attachedNamesStr = match ? match[1] : null;
    const cleanText = match ? content.replace(match[0], "").trim() : content;
    const attachedFileNames = attachedNamesStr ? attachedNamesStr.split(",").map((s) => s.trim()).filter(Boolean) : [];

    return { cleanText, attachedFileNames };
  };

  const handlePreviewCardByFileName = (fileName: string) => {
    const matchedDoc = activeLoadedDocs.find((d) => d.document_name === fileName);
    if (matchedDoc) {
      handlePreviewCard(matchedDoc);
    } else {
      onPreviewDocument({
        id: `preview-${fileName}`,
        title: fileName,
        status: "indexed",
        created_at: new Date().toISOString(),
        file_size_bytes: 1024,
        is_starred: false,
        is_trashed: false,
        download_url: attachmentPreviews[fileName] || undefined,
      });
    }
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
      <div
        className={`transition-all duration-300 border-r border-[#e1e3e1] bg-white flex flex-col justify-between overflow-hidden flex-shrink-0 ${
          isSidebarOpen ? "w-64" : "w-0 border-r-0 opacity-0 pointer-events-none"
        }`}
      >
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
                role="button"
                tabIndex={0}
                onClick={() => loadSessionDetails(s.id)}
                onKeyDown={onKeyActivate(() => loadSessionDetails(s.id))}
                aria-label={s.title}
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
        <div className="px-6 py-3.5 border-b border-[#e1e3e1] flex items-center justify-between bg-white shadow-2xs">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setIsSidebarOpen(!isSidebarOpen)}
              className="p-1.5 text-[#444746] hover:bg-[#f0f4f9] rounded-xl transition-all mr-0.5"
              title={isSidebarOpen ? "Collapse history sidebar" : "Expand history sidebar"}
            >
              {isSidebarOpen ? (
                <PanelLeftClose className="w-5 h-5" />
              ) : (
                <PanelLeft className="w-5 h-5 text-[#0b57d0]" />
              )}
            </button>

            <div className="w-9 h-9 rounded-xl bg-[#0b57d0] text-white flex items-center justify-center shadow-sm flex-shrink-0">
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

        {/* LOADED DOCUMENTS SHOWN COLLAPSED BY DEFAULT */}
        {activeLoadedDocs.length > 0 && (
          <div className="bg-[#f0f4f9] border-b border-[#e1e3e1] transition-all">
            <button
              onClick={() => setIsDocsExpanded(!isDocsExpanded)}
              className="w-full px-6 py-2 flex items-center justify-between hover:bg-[#e4e9f0] transition-colors text-left"
            >
              <div className="flex items-center gap-2">
                <FileText className="w-4 h-4 text-[#0b57d0]" />
                <span className="text-xs font-semibold text-[#1f1f1f]">
                  Loaded Context ({activeLoadedDocs.length} {activeLoadedDocs.length === 1 ? "document" : "documents"})
                </span>
              </div>
              <div className="flex items-center gap-1 text-xs text-[#0b57d0] font-semibold">
                <span>{isDocsExpanded ? "Hide Details" : "Show Details"}</span>
                {isDocsExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
              </div>
            </button>

            {isDocsExpanded && (
              <div className="p-3 max-h-[160px] overflow-y-auto grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2.5 bg-white border-t border-[#e1e3e1]">
                {activeLoadedDocs.map((res, idx) => {
                  const scorePct = Math.round((res.score || 0) * 100);
                  const isHigh = scorePct >= 85;

                  return (
                    <div
                      key={`${res.document_id}-${idx}`}
                      className="p-2.5 rounded-xl bg-[#f8fafd] border border-[#e1e3e1] hover:border-[#0b57d0]/40 transition-all space-y-1.5 shadow-2xs"
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

                      <p className="text-[11px] text-[#444746] line-clamp-2 italic bg-white p-1.5 rounded-lg border border-[#e1e3e1]/50">
                        &quot;{res.snippet}&quot;
                      </p>

                      <div className="flex items-center justify-between pt-0.5">
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

                {/* Small technology message at the bottom of loaded docs if activeLoadedDocs > 1 */}
                {activeLoadedDocs.length > 1 && (
                  <div className="col-span-full p-2.5 bg-[#edf2fc]/60 border border-[#c4c7c5]/50 rounded-xl flex items-center justify-between text-[11px] text-[#444746] mt-1">
                    <div className="flex items-center gap-1.5 font-medium">
                      <Sparkles className="w-3.5 h-3.5 text-[#0b57d0]" />
                      <span>Search Technology:</span>
                      <span className="font-bold text-[#0b57d0] px-1.5 py-0.5 rounded-md bg-white border border-[#0b57d0]/20 shadow-2xs">
                        {activeSession?.messages?.find((m) => m.role === "assistant" && m.search_mode)?.search_mode === "HyDE"
                          ? "HyDE"
                          : activeSession?.messages?.find((m) => m.role === "assistant" && m.search_mode)?.search_mode || "vector+keyword"}
                      </span>
                    </div>
                    <span className="text-[10px] text-[#747775]">RAG Grounded</span>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* Message Stream */}
        <div className="flex-1 overflow-y-auto p-6 bg-[#fcfdfe]">
          <div className="max-w-4xl mx-auto space-y-6 w-full">
            {activeSession?.messages && activeSession.messages.length > 0 ? (
              activeSession.messages.map((m) => (
                <div
                  key={m.id}
                  className={`flex flex-col ${m.role === "user" ? "items-end" : "items-start"} space-y-1.5`}
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
                    className={`rounded-2xl shadow-2xs ${
                      m.role === "user"
                        ? "bg-[#0b57d0] text-white p-4 max-w-[85%] rounded-tr-xs font-medium shadow-sm"
                        : "bg-white border border-[#e1e3e1] text-[#1f1f1f] p-5 w-full max-w-[92%] md:max-w-[88%] rounded-tl-xs shadow-xs"
                    }`}
                  >
                    {/* Markdown Answer Text */}
                    {m.role === "user" ? (
                      (() => {
                        const parsedUserMsg = parseUserMessage(m.content);
                        return (
                          <div className="space-y-3">
                            {/* Attached Files Thumbnail Cards */}
                            {parsedUserMsg.attachedFileNames.length > 0 && (
                              <div className="flex flex-wrap gap-2.5 justify-end mb-1">
                                {parsedUserMsg.attachedFileNames.map((fileName, idx) => {
                                  const isImage = /\.(jpg|jpeg|png|webp|gif|svg)$/i.test(fileName);
                                  const previewSrc = attachmentPreviews[fileName] || activeLoadedDocs.find((d) => d.document_name === fileName)?.download_url;

                                  if (isImage) {
                                    return (
                                      <div
                                        key={idx}
                                        className="group relative rounded-2xl overflow-hidden bg-black/20 border border-white/20 shadow-md transition-all max-w-[240px]"
                                      >
                                        {previewSrc ? (
                                          <div className="relative w-48 h-36 bg-black/40 overflow-hidden">
                                            <img
                                              src={previewSrc}
                                              alt={fileName}
                                              className="w-full h-full object-cover rounded-t-2xl transition-transform duration-300 group-hover:scale-105"
                                            />
                                            <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-transparent to-black/10" />
                                          </div>
                                        ) : (
                                          <div className="w-48 h-28 bg-white/10 backdrop-blur-md flex flex-col items-center justify-center p-3 text-center">
                                            <FileText className="w-8 h-8 text-white/90 mb-1" />
                                            <span className="text-xs font-semibold text-white/90 truncate max-w-full">{fileName}</span>
                                          </div>
                                        )}

                                        {/* Badge Overlay */}
                                        <div className="p-2 bg-black/60 backdrop-blur-md flex items-center justify-between gap-2 border-t border-white/10">
                                          <div className="flex items-center gap-1.5 min-w-0">
                                            <Sparkles className="w-3.5 h-3.5 text-blue-300 flex-shrink-0" />
                                            <span className="text-xs font-medium text-white truncate">{fileName}</span>
                                          </div>
                                          <button
                                            onClick={() => handlePreviewCardByFileName(fileName)}
                                            className="p-1 hover:bg-white/20 rounded-lg text-white transition-colors"
                                            title="Preview Image"
                                          >
                                            <Eye className="w-3.5 h-3.5" />
                                          </button>
                                        </div>
                                      </div>
                                    );
                                  }

                                  return (
                                    <div
                                      key={idx}
                                      className="flex items-center gap-2.5 px-3.5 py-2.5 bg-white/15 border border-white/25 backdrop-blur-md rounded-2xl text-white shadow-xs max-w-xs"
                                    >
                                      <div className="w-8 h-8 rounded-xl bg-white/20 flex items-center justify-center flex-shrink-0">
                                        <FileText className="w-4 h-4 text-white" />
                                      </div>
                                      <div className="min-w-0 flex-1">
                                        <p className="text-xs font-semibold truncate leading-tight">{fileName}</p>
                                        <span className="text-[10px] text-blue-100 font-medium">Uploaded Document</span>
                                      </div>
                                      <button
                                        onClick={() => handlePreviewCardByFileName(fileName)}
                                        className="p-1.5 hover:bg-white/20 rounded-lg text-white/90 transition-colors"
                                        title="Preview document"
                                      >
                                        <Eye className="w-3.5 h-3.5" />
                                      </button>
                                    </div>
                                  );
                                })}
                              </div>
                            )}

                            {/* Text Prompt */}
                            {parsedUserMsg.cleanText && (
                              <div className="text-sm leading-relaxed whitespace-pre-wrap font-normal">
                                {parsedUserMsg.cleanText}
                              </div>
                            )}
                          </div>
                        );
                      })()
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
                          &quot;{card.prompt}&quot;
                        </p>
                      </button>
                    );
                  })}
                </div>
              </div>
            )}

            {sending && (
              <div className="flex items-center gap-3 p-4 bg-white border border-[#e1e3e1] rounded-2xl max-w-md animate-pulse shadow-sm">
                <Sparkles className="w-4.5 h-4.5 text-[#0b57d0] animate-spin flex-shrink-0" />
                <div className="flex flex-col min-w-0">
                  <span className="text-xs font-bold text-[#1f1f1f] truncate">
                    {processingStatus}
                  </span>
                  <span className="text-[11px] text-[#747775]">
                    Waiting for OCR & document indexing before answering
                  </span>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>
        </div>

        {/* ChatGPT Style Input Controls Bar */}
        <div className="p-4 bg-white border-t border-[#e1e3e1]">
          <div className="max-w-4xl mx-auto w-full">
            {/* ChatGPT Style Attached Files Thumbnail Cards Grid */}
            {attachedFiles.length > 0 && (
              <div className="flex items-center gap-3 mb-3 overflow-x-auto pb-2 pt-1 px-1">
                {attachedFiles.map((file, idx) => {
                  const isImage = file.type.startsWith("image/") || /\.(jpg|jpeg|png|webp|gif|svg)$/i.test(file.name);
                  const objectUrl = isImage ? (attachmentPreviews[file.name] || URL.createObjectURL(file)) : null;

                  if (isImage && objectUrl) {
                    return (
                      <div
                        key={idx}
                        className="group relative w-20 h-20 rounded-2xl border border-[#d3d7dc] bg-gray-100 overflow-hidden flex-shrink-0 shadow-xs transition-all hover:shadow-sm"
                      >
                        <img
                          src={objectUrl}
                          alt={file.name}
                          className="w-full h-full object-cover rounded-2xl"
                        />
                        <div className="absolute inset-0 bg-black/20 group-hover:bg-black/30 transition-all" />
                        <button
                          type="button"
                          onClick={() => removeAttachedFile(idx)}
                          className="absolute top-1 right-1 p-1 bg-black/60 hover:bg-black text-white rounded-full transition-colors shadow-sm"
                          title="Remove image"
                        >
                          <X className="w-3 h-3" />
                        </button>
                        <div className="absolute bottom-0 inset-x-0 p-1 bg-gradient-to-t from-black/80 to-transparent text-[9px] font-medium text-white truncate px-1.5">
                          {file.name}
                        </div>
                      </div>
                    );
                  }

                  return (
                    <div
                      key={idx}
                      className="relative group flex items-center gap-2.5 px-3 py-2 bg-[#f0f4f9] border border-[#d3d7dc] rounded-2xl shadow-2xs max-w-[200px] flex-shrink-0"
                    >
                      <div className="w-8 h-8 rounded-xl bg-blue-100 text-[#0b57d0] flex items-center justify-center flex-shrink-0">
                        <FileText className="w-4 h-4" />
                      </div>
                      <div className="min-w-0 flex-1">
                        <p className="text-xs font-semibold text-[#1f1f1f] truncate leading-tight">{file.name}</p>
                        <span className="text-[10px] text-[#747775] font-medium">
                          {(file.size / 1024).toFixed(0)} KB
                        </span>
                      </div>
                      <button
                        type="button"
                        onClick={() => removeAttachedFile(idx)}
                        className="p-1 hover:bg-[#d3d7dc] text-[#747775] hover:text-red-600 rounded-full transition-colors"
                        title="Remove file"
                      >
                        <X className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  );
                })}
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
                aria-label="Ask anything or attach files to chat with documents"
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

            <p className="text-[11px] text-[#747775] text-center mt-2 font-medium tracking-tight">
              Stark AI can make mistakes. Verify important info.
            </p>
          </div>
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


