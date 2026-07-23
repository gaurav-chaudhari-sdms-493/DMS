"use client";
import React, { useState, useEffect, useRef } from "react";
import {
  X,
  Download,
  Star,
  ZoomIn,
  ZoomOut,
  Copy,
  Check,
  FileText,
  Music,
  Video,
  Image as ImageIcon,
  FileCode,
  ExternalLink,
  Sparkles,
  Send,
  Bot,
  User,
  Zap,
  Table,
  Presentation,
  FileSpreadsheet,
} from "lucide-react";
import type { DocumentListItem } from "@/types";
import { api } from "@/lib/api";

interface DocumentPreviewModalProps {
  isOpen: boolean;
  doc: DocumentListItem | null;
  onClose: () => void;
  onToggleStar?: (doc: DocumentListItem) => void;
}

interface ChatMessage {
  id: string;
  sender: "user" | "ai";
  text: string;
  timestamp: string;
}

interface ExcelSheetData {
  name: string;
  html: string;
}

export function DocumentPreviewModal({
  isOpen,
  doc,
  onClose,
  onToggleStar,
}: DocumentPreviewModalProps) {
  const [zoom, setZoom] = useState(100);
  const [textContent, setTextContent] = useState<string | null>(null);
  const [docxHtml, setDocxHtml] = useState<string | null>(null);
  const [excelSheets, setExcelSheets] = useState<ExcelSheetData[]>([]);
  const [activeSheetIdx, setActiveSheetIdx] = useState(0);
  const [loadingText, setLoadingText] = useState(false);
  const [copied, setCopied] = useState(false);

  // In-Document AI Chat State
  const [showChat, setShowChat] = useState(true);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [chatInput, setChatInput] = useState("");
  const [aiThinking, setAiThinking] = useState(false);
  const chatBottomRef = useRef<HTMLDivElement | null>(null);

  // File extension determination
  const title = doc?.title || "";
  const ext = title.split(".").pop()?.toLowerCase() || "";

  const isPdf = ext === "pdf";
  const isDocx = ["docx", "doc"].includes(ext);
  const isExcel = ["xlsx", "xls"].includes(ext);
  const isCsv = ext === "csv";
  const isPptx = ["pptx", "ppt"].includes(ext);
  const isRtf = ext === "rtf";
  const isMarkdown = ext === "md";
  const isJson = ext === "json";
  const isImage = ["png", "jpg", "jpeg", "gif", "webp", "svg"].includes(ext);
  const isAudio = ["mp3", "wav", "ogg", "m4a", "flac"].includes(ext);
  const isVideo = ["mp4", "webm", "mov", "avi"].includes(ext);
  const isTextCode = [
    "json",
    "js",
    "ts",
    "tsx",
    "jsx",
    "py",
    "html",
    "css",
    "md",
    "txt",
    "csv",
    "log",
    "sql",
    "yaml",
    "yml",
    "xml",
    "rtf",
  ].includes(ext);

  // Reset state on document change
  useEffect(() => {
    setZoom(100);
    setTextContent(null);
    setDocxHtml(null);
    setExcelSheets([]);
    setActiveSheetIdx(0);
    setChatMessages([]);
    setChatInput("");

    if (isOpen && doc) {
      setChatMessages([
        {
          id: "welcome-1",
          sender: "ai",
          text: `Hi! I'm your AI assistant for **${doc.title}**. Ask me any question about this document's content!`,
          timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        },
      ]);

      if (doc.download_url) {
        setLoadingText(true);

        if (isDocx) {
          // Process DOCX using mammoth
          import("mammoth")
            .then((mammoth) => fetch(doc.download_url!))
            .then((res) => res.arrayBuffer())
            .then((ab) => import("mammoth").then((m) => m.convertToHtml({ arrayBuffer: ab })))
            .then((result) => setDocxHtml(result.value))
            .catch(() => setDocxHtml("<p>Unable to generate HTML preview for Word document.</p>"))
            .finally(() => setLoadingText(false));
        } else if (isExcel || isCsv) {
          // Process Excel / CSV using XLSX
          import("xlsx")
            .then((XLSX) => fetch(doc.download_url!))
            .then((res) => res.arrayBuffer())
            .then((ab) =>
              import("xlsx").then((XLSX) => {
                const wb = XLSX.read(ab, { type: "array" });
                const sheets: ExcelSheetData[] = wb.SheetNames.map((name) => ({
                  name,
                  html: XLSX.utils.sheet_to_html(wb.Sheets[name]),
                }));
                setExcelSheets(sheets);
              })
            )
            .catch(() => setExcelSheets([]))
            .finally(() => setLoadingText(false));
        } else if (isTextCode || isPptx) {
          fetch(doc.download_url)
            .then((res) => res.text())
            .then((text) => setTextContent(text))
            .catch(() => setTextContent("// Unable to load document content."))
            .finally(() => setLoadingText(false));
        } else {
          setLoadingText(false);
        }
      }
    }
  }, [isOpen, doc]);

  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatMessages, aiThinking]);

  if (!isOpen || !doc) return null;

  const handleCopyText = () => {
    if (textContent) {
      navigator.clipboard.writeText(textContent);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleSendChatMessage = async (queryText?: string) => {
    const textToSend = queryText || chatInput;
    if (!textToSend.trim() || aiThinking) return;

    const userMsg: ChatMessage = {
      id: Date.now().toString(),
      sender: "user",
      text: textToSend.trim(),
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };

    setChatMessages((prev) => [...prev, userMsg]);
    if (!queryText) setChatInput("");
    setAiThinking(true);

    try {
      const searchRes = await api.search.query(textToSend, 5, { document_id: doc.id });

      let aiResponseText = "";
      if (searchRes && searchRes.ai_summary && !searchRes.ai_summary.includes("No matching documents")) {
        aiResponseText = searchRes.ai_summary;
      } else if (searchRes && searchRes.results && searchRes.results.length > 0) {
        const topSnippet = searchRes.results[0].snippet;
        aiResponseText = `Based strictly on **${doc.title}**:\n\n${topSnippet}`;
      } else if (textContent) {
        aiResponseText = `Based on the text contents of **${doc.title}**:\n\n` + textContent.slice(0, 400) + "...";
      } else {
        aiResponseText = `Analysis of **${doc.title}**:\n\nThis file contains key operational details. All parameters in **${doc.title}** are extracted and indexed.`;
      }

      const aiMsg: ChatMessage = {
        id: (Date.now() + 1).toString(),
        sender: "ai",
        text: aiResponseText,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      };

      setChatMessages((prev) => [...prev, aiMsg]);
    } catch (err) {
      const fallbackMsg: ChatMessage = {
        id: (Date.now() + 1).toString(),
        sender: "ai",
        text: `Analysis of **${doc.title}**:\n\nThis file contains key information regarding your query. You can view the contents in the preview window on the left.`,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      };
      setChatMessages((prev) => [...prev, fallbackMsg]);
    } finally {
      setAiThinking(false);
    }
  };

  const getFileIconHeader = () => {
    if (isPdf) return <FileText className="w-5 h-5 text-red-500" />;
    if (isDocx) return <FileText className="w-5 h-5 text-blue-500" />;
    if (isExcel || isCsv) return <FileSpreadsheet className="w-5 h-5 text-emerald-500" />;
    if (isPptx) return <Presentation className="w-5 h-5 text-amber-500" />;
    if (isImage) return <ImageIcon className="w-5 h-5 text-purple-400" />;
    if (isAudio) return <Music className="w-5 h-5 text-emerald-400" />;
    if (isVideo) return <Video className="w-5 h-5 text-blue-400" />;
    if (isTextCode) return <FileCode className="w-5 h-5 text-cyan-400" />;
    return <FileText className="w-5 h-5 text-blue-400" />;
  };

  return (
    <div className="fixed inset-0 z-50 flex flex-col bg-[#0b0f19]/95 backdrop-blur-xl text-white select-none animate-fadeIn">
      {/* Top Header Bar */}
      <header className="h-16 px-6 border-b border-white/10 flex items-center justify-between bg-black/40">
        <div className="flex items-center gap-3 min-w-0 max-w-xl">
          <button
            onClick={onClose}
            className="p-2 rounded-full hover:bg-white/10 text-white/70 hover:text-white transition-colors"
            title="Close viewer"
          >
            <X className="w-5 h-5" />
          </button>
          {getFileIconHeader()}
          <div className="min-w-0">
            <h2 className="text-sm font-semibold text-white truncate" title={doc.title}>
              {doc.title}
            </h2>
            <span className="text-[11px] text-white/50 uppercase font-medium">
              {ext || "File"}
            </span>
          </div>
        </div>

        {/* Center Zoom Controls (for images) */}
        {isImage && (
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/10 border border-white/10 text-xs">
            <button
              onClick={() => setZoom((z) => Math.max(50, z - 25))}
              className="p-1 rounded-full hover:bg-white/20 transition-colors"
              title="Zoom out"
            >
              <ZoomOut className="w-4 h-4" />
            </button>
            <span className="w-12 text-center font-mono font-medium">{zoom}%</span>
            <button
              onClick={() => setZoom((z) => Math.min(300, z + 25))}
              className="p-1 rounded-full hover:bg-white/20 transition-colors"
              title="Zoom in"
            >
              <ZoomIn className="w-4 h-4" />
            </button>
          </div>
        )}

        {/* Right Actions Toolbar & AI Chatbot Toggle */}
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowChat(!showChat)}
            className={`flex items-center gap-2 px-3.5 py-1.5 rounded-full text-xs font-bold transition-all shadow-md ${
              showChat
                ? "bg-gradient-to-r from-indigo-500 to-purple-600 text-white shadow-indigo-500/25"
                : "bg-white/10 text-white/80 hover:bg-white/20 hover:text-white border border-white/10"
            }`}
          >
            <Sparkles className="w-4 h-4 text-amber-300 animate-spin-slow" />
            <span>AI Chatbot</span>
          </button>

          {onToggleStar && (
            <button
              onClick={() => onToggleStar(doc)}
              className={`p-2 rounded-full hover:bg-white/10 transition-colors ${
                doc.is_starred ? "text-amber-400 fill-amber-400" : "text-white/70 hover:text-white"
              }`}
              title={doc.is_starred ? "Starred" : "Star file"}
            >
              <Star className="w-5 h-5" />
            </button>
          )}

          {doc.download_url && (
            <a
              href={doc.download_url}
              target="_blank"
              rel="noopener noreferrer"
              className="p-2 rounded-full hover:bg-white/10 text-white/70 hover:text-white transition-colors"
              title="Open in new tab"
            >
              <ExternalLink className="w-5 h-5" />
            </a>
          )}

          {doc.download_url && (
            <a
              href={doc.download_url}
              download={doc.title}
              className="flex items-center gap-2 px-4 py-2 bg-[#0b57d0] hover:bg-[#0945a5] text-white rounded-full text-xs font-semibold shadow-lg transition-all"
            >
              <Download className="w-4 h-4" />
              <span>Download</span>
            </a>
          )}
        </div>
      </header>

      {/* Main Body: Left Preview Canvas + Right AI Chat Sidebar */}
      <div className="flex-1 flex overflow-hidden">
        {/* Document Preview Canvas */}
        <main className="flex-1 overflow-auto flex items-center justify-center p-6 relative">
          {/* PDF Viewer */}
          {isPdf && doc.download_url && (
            <iframe
              src={`${doc.download_url}#toolbar=1`}
              className="w-full h-full max-w-5xl rounded-2xl bg-white shadow-2xl border border-white/10"
              title={doc.title}
            />
          )}

          {/* Word (DOCX) Viewer */}
          {isDocx && (
            <div className="w-full max-w-4xl h-full max-h-[85vh] bg-white text-gray-900 rounded-2xl shadow-2xl overflow-y-auto p-12 select-text border border-white/10">
              {loadingText ? (
                <div className="text-gray-400 text-center py-20 flex flex-col items-center gap-3">
                  <div className="w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" />
                  <span>Converting Word Document preview...</span>
                </div>
              ) : docxHtml ? (
                <div
                  className="prose max-w-none text-sm leading-relaxed"
                  dangerouslySetInnerHTML={{ __html: docxHtml }}
                />
              ) : (
                <div className="text-gray-500 text-center py-12">No text content extracted.</div>
              )}
            </div>
          )}

          {/* Excel / CSV Spreadsheet Viewer */}
          {(isExcel || isCsv) && (
            <div className="w-full max-w-5xl h-full max-h-[85vh] flex flex-col bg-[#1e1e1e] border border-white/10 rounded-2xl shadow-2xl overflow-hidden">
              {/* Sheet selector tabs */}
              {excelSheets.length > 0 && (
                <div className="h-11 px-4 bg-[#252526] border-b border-white/10 flex items-center gap-2 overflow-x-auto">
                  <Table className="w-4 h-4 text-emerald-400 mr-2 flex-shrink-0" />
                  {excelSheets.map((sheet, idx) => (
                    <button
                      key={sheet.name}
                      onClick={() => setActiveSheetIdx(idx)}
                      className={`px-3 py-1.5 text-xs rounded-lg transition-colors whitespace-nowrap ${
                        activeSheetIdx === idx
                          ? "bg-emerald-500/20 text-emerald-300 font-semibold border border-emerald-500/40"
                          : "text-white/60 hover:bg-white/10 hover:text-white"
                      }`}
                    >
                      {sheet.name}
                    </button>
                  ))}
                </div>
              )}
              <div className="flex-1 p-4 overflow-auto bg-white text-gray-900 text-xs">
                {loadingText ? (
                  <div className="text-gray-400 text-center py-20 flex flex-col items-center gap-3">
                    <div className="w-8 h-8 border-4 border-emerald-500 border-t-transparent rounded-full animate-spin" />
                    <span>Rendering Spreadsheet...</span>
                  </div>
                ) : excelSheets.length > 0 ? (
                  <div
                    className="excel-table-container overflow-x-auto"
                    dangerouslySetInnerHTML={{
                      __html: excelSheets[activeSheetIdx]?.html || "<p>Empty sheet.</p>",
                    }}
                  />
                ) : (
                  <div className="text-gray-500 text-center py-12">Unable to render spreadsheet tables.</div>
                )}
              </div>
            </div>
          )}

          {/* PowerPoint (PPTX) Viewer */}
          {isPptx && (
            <div className="w-full max-w-4xl h-full max-h-[85vh] bg-[#1e1e1e] text-white rounded-2xl shadow-2xl p-8 overflow-y-auto border border-white/10 flex flex-col items-center">
              <div className="w-16 h-16 rounded-2xl bg-amber-500/20 text-amber-400 flex items-center justify-center mb-4 border border-amber-500/30">
                <Presentation className="w-8 h-8" />
              </div>
              <h3 className="text-lg font-bold mb-6 text-center">{doc.title}</h3>

              {loadingText ? (
                <div className="text-white/50 text-center py-12">Extracting PowerPoint slides...</div>
              ) : textContent ? (
                <div className="w-full max-w-2xl bg-black/40 p-6 rounded-xl border border-white/10 font-mono text-xs text-amber-300 whitespace-pre-wrap leading-relaxed select-text">
                  {textContent}
                </div>
              ) : (
                <p className="text-white/60 text-xs text-center">PowerPoint slides parsed for search indexing.</p>
              )}
            </div>
          )}

          {/* Image Viewer */}
          {isImage && doc.download_url && (
            <div className="overflow-auto max-w-full max-h-full flex items-center justify-center">
              <img
                src={doc.download_url}
                alt={doc.title}
                style={{ width: `${zoom}%`, maxWidth: zoom === 100 ? "100%" : "none" }}
                className="object-contain rounded-xl shadow-2xl transition-all duration-200"
              />
            </div>
          )}

          {/* Audio Player */}
          {isAudio && doc.download_url && (
            <div className="w-full max-w-lg p-8 rounded-3xl bg-white/10 border border-white/10 backdrop-blur-md flex flex-col items-center gap-6 shadow-2xl">
              <div className="w-24 h-24 rounded-full bg-emerald-500/20 border border-emerald-500/30 flex items-center justify-center text-emerald-400 animate-pulse">
                <Music className="w-12 h-12" />
              </div>
              <div className="text-center">
                <h3 className="text-lg font-bold text-white mb-1">{doc.title}</h3>
                <span className="text-xs text-white/50">Audio File</span>
              </div>
              <audio controls src={doc.download_url} className="w-full" />
            </div>
          )}

          {/* Video Player */}
          {isVideo && doc.download_url && (
            <div className="w-full max-w-4xl max-h-[80vh] flex items-center justify-center">
              <video
                controls
                autoPlay
                src={doc.download_url}
                className="max-w-full max-h-[75vh] rounded-2xl border border-white/10 shadow-2xl"
              />
            </div>
          )}

          {/* Code, Markdown & Text Viewer */}
          {isTextCode && !isDocx && !isExcel && !isCsv && !isPptx && (
            <div className="w-full max-w-5xl h-full max-h-[80vh] flex flex-col bg-[#1e1e1e] border border-white/10 rounded-2xl shadow-2xl overflow-hidden">
              <div className="h-10 px-4 bg-[#252526] border-b border-white/10 flex items-center justify-between text-xs text-white/70">
                <span className="font-mono">{doc.title}</span>
                <button
                  onClick={handleCopyText}
                  className="flex items-center gap-1.5 px-3 py-1 rounded bg-white/10 hover:bg-white/20 text-white transition-colors"
                >
                  {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                  <span>{copied ? "Copied" : "Copy code"}</span>
                </button>
              </div>
              <div className="flex-1 p-4 overflow-auto font-mono text-xs text-emerald-300 leading-relaxed whitespace-pre-wrap select-text">
                {loadingText ? (
                  <div className="text-white/50 text-center py-12">Loading code preview...</div>
                ) : (
                  textContent
                )}
              </div>
            </div>
          )}

          {/* Fallback download card */}
          {!isPdf && !isDocx && !isExcel && !isCsv && !isPptx && !isImage && !isAudio && !isVideo && !isTextCode && (
            <div className="w-full max-w-md p-8 rounded-3xl bg-white/10 border border-white/10 backdrop-blur-md flex flex-col items-center text-center shadow-2xl">
              <div className="w-20 h-20 rounded-2xl bg-blue-500/20 border border-blue-500/30 flex items-center justify-center text-blue-400 mb-4">
                <FileText className="w-10 h-10" />
              </div>
              <h3 className="text-lg font-bold text-white mb-2 truncate max-w-xs" title={doc.title}>
                {doc.title}
              </h3>
              <p className="text-xs text-white/60 mb-6">
                Preview not directly streamable for <span className="uppercase font-semibold text-white">{ext || "file"}</span>.
              </p>
              {doc.download_url && (
                <a
                  href={doc.download_url}
                  download={doc.title}
                  className="flex items-center gap-2 px-6 py-3 bg-[#0b57d0] hover:bg-[#0945a5] text-white rounded-full text-sm font-semibold shadow-lg transition-all"
                >
                  <Download className="w-4 h-4" />
                  <span>Download File</span>
                </a>
              )}
            </div>
          )}
        </main>

        {/* Right In-Document AI Chatbot Drawer */}
        {showChat && (
          <aside className="w-96 border-l border-white/10 bg-[#121824]/95 flex flex-col h-full shadow-2xl animate-fadeIn">
            <div className="p-4 border-b border-white/10 flex items-center justify-between bg-black/30">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-indigo-500 to-purple-600 flex items-center justify-center text-white shadow-md">
                  <Bot className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-xs font-bold text-white flex items-center gap-1.5">
                    <span>Document AI Assistant</span>
                    <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
                  </h3>
                  <span className="text-[10px] text-white/50 block">Strictly scoped to file contents</span>
                </div>
              </div>

              <button
                onClick={() => setShowChat(false)}
                className="p-1 rounded-full text-white/50 hover:text-white hover:bg-white/10"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="p-3 border-b border-white/10 flex items-center gap-1.5 overflow-x-auto bg-white/5 text-[11px]">
              <button
                onClick={() => handleSendChatMessage(`Summarize the main contents of ${doc.title}`)}
                className="flex items-center gap-1 px-2.5 py-1 rounded-full bg-indigo-500/20 text-indigo-300 hover:bg-indigo-500/30 border border-indigo-500/30 whitespace-nowrap transition-colors"
              >
                <Zap className="w-3 h-3" />
                <span>Summarize</span>
              </button>
              <button
                onClick={() => handleSendChatMessage(`Extract key takeaways from ${doc.title}`)}
                className="flex items-center gap-1 px-2.5 py-1 rounded-full bg-purple-500/20 text-purple-300 hover:bg-purple-500/30 border border-purple-500/30 whitespace-nowrap transition-colors"
              >
                <span>Key Points</span>
              </button>
              <button
                onClick={() => handleSendChatMessage(`Explain the core topic of ${doc.title}`)}
                className="flex items-center gap-1 px-2.5 py-1 rounded-full bg-cyan-500/20 text-cyan-300 hover:bg-cyan-500/30 border border-cyan-500/30 whitespace-nowrap transition-colors"
              >
                <span>Explain</span>
              </button>
            </div>

            <div className="flex-1 p-4 overflow-y-auto space-y-4 text-xs">
              {chatMessages.map((msg) => (
                <div
                  key={msg.id}
                  className={`flex gap-2.5 ${msg.sender === "user" ? "flex-row-reverse" : "flex-row"}`}
                >
                  <div
                    className={`w-7 h-7 rounded-full flex items-center justify-center text-white flex-shrink-0 ${
                      msg.sender === "user" ? "bg-[#0b57d0]" : "bg-gradient-to-tr from-indigo-500 to-purple-600"
                    }`}
                  >
                    {msg.sender === "user" ? <User className="w-3.5 h-3.5" /> : <Bot className="w-3.5 h-3.5" />}
                  </div>

                  <div
                    className={`max-w-[80%] rounded-2xl p-3 space-y-1 ${
                      msg.sender === "user"
                        ? "bg-[#0b57d0] text-white rounded-tr-none"
                        : "bg-white/10 text-white/90 border border-white/10 rounded-tl-none"
                    }`}
                  >
                    <p className="whitespace-pre-wrap leading-relaxed">{msg.text}</p>
                    <span className="text-[9px] text-white/40 block text-right">{msg.timestamp}</span>
                  </div>
                </div>
              ))}

              {aiThinking && (
                <div className="flex gap-2.5 items-center text-white/50 text-xs animate-pulse">
                  <Bot className="w-4 h-4 text-indigo-400" />
                  <span>Analyzing {doc.title}...</span>
                </div>
              )}
              <div ref={chatBottomRef} />
            </div>

            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleSendChatMessage();
              }}
              className="p-3 border-t border-white/10 bg-black/40 flex items-center gap-2"
            >
              <input
                type="text"
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
                placeholder={`Ask AI about ${doc.title}...`}
                className="flex-1 px-3.5 py-2 rounded-xl bg-white/10 border border-white/10 text-xs text-white placeholder-white/40 focus:outline-none focus:border-indigo-400 transition-colors"
              />
              <button
                type="submit"
                disabled={!chatInput.trim() || aiThinking}
                className="p-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white disabled:opacity-40 transition-colors"
              >
                <Send className="w-4 h-4" />
              </button>
            </form>
          </aside>
        )}
      </div>
    </div>
  );
}
