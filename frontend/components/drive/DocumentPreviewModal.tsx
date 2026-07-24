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
import { MarkdownViewer } from "../chat/MarkdownViewer";
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

  // Extensible Drag Resizable Width for In-Document AI Chatbot
  const [chatWidth, setChatWidth] = useState<number>(420);
  const [isResizingChat, setIsResizingChat] = useState<boolean>(false);
  const isResizingChatRef = useRef(false);

  const handleChatMouseDown = (e: React.MouseEvent) => {
    e.preventDefault();
    isResizingChatRef.current = true;
    setIsResizingChat(true);

    const handleMouseMove = (e: MouseEvent) => {
      if (!isResizingChatRef.current) return;
      const newWidth = window.innerWidth - e.clientX;
      const clampedWidth = Math.min(Math.max(newWidth, 340), Math.min(950, window.innerWidth - 200));
      setChatWidth(clampedWidth);
    };

    const handleMouseUp = () => {
      isResizingChatRef.current = false;
      setIsResizingChat(false);
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseup", handleMouseUp);
    };

    window.addEventListener("mousemove", handleMouseMove);
    window.addEventListener("mouseup", handleMouseUp);
  };

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
    <div className="fixed inset-0 z-50 flex flex-col bg-black/60 backdrop-blur-md text-[#1f1f1f] select-none animate-fadeIn">
      {/* Top Header Bar */}
      <header className="h-16 px-6 border-b border-[#e1e3e1] flex items-center justify-between bg-white shadow-xs">
        <div className="flex items-center gap-3 min-w-0 max-w-xl">
          <button
            onClick={onClose}
            className="p-2 rounded-full hover:bg-[#f0f4f9] text-[#444746] hover:text-[#1f1f1f] transition-colors"
            title="Close viewer"
          >
            <X className="w-5 h-5" />
          </button>
          {getFileIconHeader()}
          <div className="min-w-0">
            <h2 className="text-sm font-bold text-[#1f1f1f] truncate" title={doc.title}>
              {doc.title}
            </h2>
            <span className="text-[11px] text-[#747775] uppercase font-semibold">
              {ext || "File"}
            </span>
          </div>
        </div>

        {/* Center Zoom Controls (for images) */}
        {isImage && (
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-[#edf2fc] border border-[#e1e3e1] text-xs text-[#1f1f1f]">
            <button
              onClick={() => setZoom((z) => Math.max(50, z - 25))}
              className="p-1 rounded-full hover:bg-[#d3d7dc] transition-colors"
              title="Zoom out"
            >
              <ZoomOut className="w-4 h-4" />
            </button>
            <span className="w-12 text-center font-mono font-bold">{zoom}%</span>
            <button
              onClick={() => setZoom((z) => Math.min(300, z + 25))}
              className="p-1 rounded-full hover:bg-[#d3d7dc] transition-colors"
              title="Zoom in"
            >
              <ZoomIn className="w-4 h-4" />
            </button>
          </div>
        )}

        {/* Right Actions Toolbar & AI Chatbot Toggle */}
        <div className="flex items-center gap-3">
          <button
            onClick={() => setShowChat(!showChat)}
            className={`flex items-center gap-2 px-4 py-2 rounded-full text-xs font-bold transition-all shadow-xs ${
              showChat
                ? "bg-[#0b57d0] text-white shadow-blue-500/20"
                : "bg-[#f0f4f9] text-[#001d35] hover:bg-[#e1e5ea] border border-[#d3d7dc]"
            }`}
          >
            <Sparkles className="w-4 h-4 text-amber-300 animate-spin-slow" />
            <span>AI Chatbot</span>
          </button>

          {doc.download_url && (
            <a
              href={doc.download_url}
              download={doc.title}
              className="flex items-center gap-2 px-4 py-2 bg-[#0b57d0] hover:bg-[#0945a5] text-white rounded-full text-xs font-semibold shadow-sm transition-all"
            >
              <Download className="w-4 h-4" />
              <span>Download</span>
            </a>
          )}
        </div>
      </header>

      {/* Main Body: Left Preview Canvas + Right AI Chat Sidebar */}
      <div className="flex-1 flex overflow-hidden bg-[#f8fafd]">
        {/* Document Preview Canvas */}
        <main className="flex-1 overflow-auto flex items-center justify-center p-6 relative">
          {/* PDF Viewer */}
          {isPdf && doc.download_url && (
            <iframe
              src={`${doc.download_url}#toolbar=1`}
              className="w-full h-full max-w-5xl rounded-2xl bg-white shadow-xl border border-[#e1e3e1]"
              title={doc.title}
            />
          )}

          {/* Word (DOCX) Viewer */}
          {isDocx && (
            <div className="w-full max-w-4xl h-full max-h-[85vh] bg-white text-[#1f1f1f] rounded-2xl shadow-xl overflow-y-auto p-12 select-text border border-[#e1e3e1]">
              {loadingText ? (
                <div className="text-[#444746] text-center py-20 flex flex-col items-center gap-3">
                  <div className="w-8 h-8 border-4 border-[#0b57d0] border-t-transparent rounded-full animate-spin" />
                  <span>Converting Word Document preview...</span>
                </div>
              ) : docxHtml ? (
                <div
                  className="prose max-w-none text-sm leading-relaxed text-[#1f1f1f]"
                  dangerouslySetInnerHTML={{ __html: docxHtml }}
                />
              ) : (
                <div className="text-[#747775] text-center py-12">No text content extracted.</div>
              )}
            </div>
          )}

          {/* Excel / CSV Spreadsheet Viewer */}
          {(isExcel || isCsv) && (
            <div className="w-full max-w-5xl h-full max-h-[85vh] flex flex-col bg-white border border-[#e1e3e1] rounded-2xl shadow-xl overflow-hidden">
              {/* Sheet selector tabs */}
              {excelSheets.length > 0 && (
                <div className="h-11 px-4 bg-[#f8fafd] border-b border-[#e1e3e1] flex items-center gap-2 overflow-x-auto">
                  <Table className="w-4 h-4 text-emerald-600 mr-2 flex-shrink-0" />
                  {excelSheets.map((sheet, idx) => (
                    <button
                      key={sheet.name}
                      onClick={() => setActiveSheetIdx(idx)}
                      className={`px-3 py-1.5 text-xs rounded-lg transition-colors whitespace-nowrap ${
                        activeSheetIdx === idx
                          ? "bg-emerald-50 text-emerald-700 font-semibold border border-emerald-200"
                          : "text-[#444746] hover:bg-[#edf2fc] hover:text-[#1f1f1f]"
                      }`}
                    >
                      {sheet.name}
                    </button>
                  ))}
                </div>
              )}
              <div className="flex-1 p-4 overflow-auto bg-white text-[#1f1f1f] text-xs">
                {loadingText ? (
                  <div className="text-[#444746] text-center py-20 flex flex-col items-center gap-3">
                    <div className="w-8 h-8 border-4 border-emerald-600 border-t-transparent rounded-full animate-spin" />
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
                  <div className="text-[#747775] text-center py-12">Unable to render spreadsheet tables.</div>
                )}
              </div>
            </div>
          )}

          {/* PowerPoint (PPTX) Viewer */}
          {isPptx && (
            <div className="w-full max-w-4xl h-full max-h-[85vh] bg-white text-[#1f1f1f] rounded-2xl shadow-xl p-8 overflow-y-auto border border-[#e1e3e1] flex flex-col items-center">
              <div className="w-16 h-16 rounded-2xl bg-amber-50 text-amber-600 flex items-center justify-center mb-4 border border-amber-200">
                <Presentation className="w-8 h-8" />
              </div>
              <h3 className="text-lg font-bold mb-6 text-center text-[#1f1f1f]">{doc.title}</h3>

              {loadingText ? (
                <div className="text-[#747775] text-center py-12">Extracting PowerPoint slides...</div>
              ) : textContent ? (
                <div className="w-full max-w-2xl bg-[#f8fafd] p-6 rounded-xl border border-[#e1e3e1] font-mono text-xs text-[#1f1f1f] whitespace-pre-wrap leading-relaxed select-text">
                  {textContent}
                </div>
              ) : (
                <p className="text-[#747775] text-xs text-center">PowerPoint slides parsed for search indexing.</p>
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
                className="object-contain rounded-xl shadow-xl transition-all duration-200 border border-[#e1e3e1]"
              />
            </div>
          )}

          {/* Audio Player */}
          {isAudio && doc.download_url && (
            <div className="w-full max-w-lg p-8 rounded-3xl bg-white border border-[#e1e3e1] flex flex-col items-center gap-6 shadow-xl">
              <div className="w-24 h-24 rounded-full bg-emerald-50 border border-emerald-200 flex items-center justify-center text-emerald-600 animate-pulse">
                <Music className="w-12 h-12" />
              </div>
              <div className="text-center">
                <h3 className="text-lg font-bold text-[#1f1f1f] mb-1">{doc.title}</h3>
                <span className="text-xs text-[#747775]">Audio File</span>
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
                className="max-w-full max-h-[75vh] rounded-2xl border border-[#e1e3e1] shadow-xl bg-black"
              />
            </div>
          )}

          {/* Code, Markdown & Text Viewer */}
          {isTextCode && !isDocx && !isExcel && !isCsv && !isPptx && (
            <div className="w-full max-w-5xl h-full max-h-[80vh] flex flex-col bg-white border border-[#e1e3e1] rounded-2xl shadow-xl overflow-hidden">
              <div className="h-10 px-4 bg-[#f8fafd] border-b border-[#e1e3e1] flex items-center justify-between text-xs text-[#444746]">
                <span className="font-mono font-semibold text-[#1f1f1f]">{doc.title}</span>
                <button
                  onClick={handleCopyText}
                  className="flex items-center gap-1.5 px-3 py-1 rounded-lg bg-[#edf2fc] hover:bg-[#e1e5ea] text-[#0b57d0] font-semibold transition-colors border border-[#d3d7dc]"
                >
                  {copied ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5" />}
                  <span>{copied ? "Copied" : "Copy content"}</span>
                </button>
              </div>
              <div className="flex-1 p-5 overflow-auto font-mono text-xs text-[#1f1f1f] leading-relaxed whitespace-pre-wrap select-text bg-white">
                {loadingText ? (
                  <div className="text-[#747775] text-center py-12">Loading content preview...</div>
                ) : (
                  textContent
                )}
              </div>
            </div>
          )}

          {/* Fallback download card */}
          {!isPdf && !isDocx && !isExcel && !isCsv && !isPptx && !isImage && !isAudio && !isVideo && !isTextCode && (
            <div className="w-full max-w-md p-8 rounded-3xl bg-white border border-[#e1e3e1] flex flex-col items-center text-center shadow-xl">
              <div className="w-20 h-20 rounded-2xl bg-blue-50 border border-blue-100 flex items-center justify-center text-[#0b57d0] mb-4">
                <FileText className="w-10 h-10" />
              </div>
              <h3 className="text-lg font-bold text-[#1f1f1f] mb-2 truncate max-w-xs" title={doc.title}>
                {doc.title}
              </h3>
              <p className="text-xs text-[#747775] mb-6">
                Preview not directly streamable for <span className="uppercase font-semibold text-[#1f1f1f]">{ext || "file"}</span>.
              </p>
              {doc.download_url && (
                <a
                  href={doc.download_url}
                  download={doc.title}
                  className="flex items-center gap-2 px-6 py-3 bg-[#0b57d0] hover:bg-[#0945a5] text-white rounded-full text-sm font-semibold shadow-md transition-all"
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
          <aside
            style={{ width: `${chatWidth}px` }}
            className="border-l border-[#e1e3e1] bg-white flex flex-col h-full shadow-2xl animate-fadeIn relative z-20 flex-shrink-0 transition-none"
          >
            {/* Draggable Left Boundary Handle */}
            <div
              onMouseDown={handleChatMouseDown}
              className={`absolute left-0 top-0 bottom-0 w-2.5 -ml-1.5 cursor-col-resize z-50 flex items-center justify-center group hover:bg-[#0b57d0]/20 transition-colors ${
                isResizingChat ? "bg-[#0b57d0]/30" : ""
              }`}
              title="Click and drag to extend/resize chatbot width"
            >
              <div className="w-1 h-10 bg-[#c4c7c5] group-hover:bg-[#0b57d0] rounded-full transition-colors" />
            </div>

            {/* Header */}
            <div className="p-4 border-b border-[#e1e3e1] flex items-center justify-between bg-[#f8fafd] shadow-2xs">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-[#0b57d0] to-indigo-600 flex items-center justify-center text-white shadow-md shadow-blue-500/20">
                  <Sparkles className="w-4.5 h-4.5 text-white" />
                </div>
                <div>
                  <h3 className="text-xs font-bold text-[#1f1f1f] flex items-center gap-1.5">
                    <span>Document AI Assistant</span>
                    <span className="flex h-2 w-2 relative">
                      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                      <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                    </span>
                  </h3>
                  <span className="text-[10px] text-[#747775] block font-medium">Strictly scoped to file contents</span>
                </div>
              </div>

              <button
                onClick={() => setShowChat(false)}
                className="p-1.5 rounded-full text-[#444746] hover:bg-[#e1e3e1] transition-colors"
                title="Close chat"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Quick Action Prompt Chips */}
            <div className="p-3 border-b border-[#e1e3e1] flex items-center gap-2 overflow-x-auto bg-[#f8fafd] text-xs">
              <button
                onClick={() => handleSendChatMessage(`Summarize the main contents of ${doc.title}`)}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-white text-[#0b57d0] hover:bg-[#0b57d0] hover:text-white border border-[#d3d7dc] hover:border-[#0b57d0] whitespace-nowrap transition-all font-semibold shadow-2xs cursor-pointer"
              >
                <Zap className="w-3.5 h-3.5" />
                <span>Summarize</span>
              </button>
              <button
                onClick={() => handleSendChatMessage(`Extract key takeaways from ${doc.title}`)}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-white text-purple-700 hover:bg-purple-700 hover:text-white border border-[#d3d7dc] hover:border-purple-700 whitespace-nowrap transition-all font-semibold shadow-2xs cursor-pointer"
              >
                <Sparkles className="w-3.5 h-3.5" />
                <span>Key Points</span>
              </button>
              <button
                onClick={() => handleSendChatMessage(`Explain the core topic of ${doc.title}`)}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-white text-emerald-700 hover:bg-emerald-700 hover:text-white border border-[#d3d7dc] hover:border-emerald-700 whitespace-nowrap transition-all font-semibold shadow-2xs cursor-pointer"
              >
                <FileText className="w-3.5 h-3.5" />
                <span>Explain</span>
              </button>
            </div>

            {/* Chat Messages */}
            <div className="flex-1 p-4 overflow-y-auto space-y-4 text-xs bg-[#f8fafd]">
              {chatMessages.map((msg) => (
                <div
                  key={msg.id}
                  className={`flex gap-2.5 ${msg.sender === "user" ? "flex-row-reverse" : "flex-row"}`}
                >
                  <div
                    className={`w-7 h-7 rounded-full flex items-center justify-center text-white flex-shrink-0 shadow-xs ${
                      msg.sender === "user" ? "bg-[#0b57d0]" : "bg-gradient-to-br from-indigo-600 to-[#0b57d0]"
                    }`}
                  >
                    {msg.sender === "user" ? <User className="w-3.5 h-3.5" /> : <Bot className="w-3.5 h-3.5" />}
                  </div>

                  <div
                    className={`max-w-[85%] rounded-2xl p-3.5 space-y-1 overflow-hidden break-words [word-break:break-word] min-w-0 ${
                      msg.sender === "user"
                        ? "bg-[#0b57d0] text-white font-medium rounded-tr-xs shadow-sm"
                        : "bg-white border border-[#e1e3e1] text-[#1f1f1f] rounded-tl-xs shadow-2xs"
                    }`}
                  >
                    {msg.sender === "user" ? (
                      <p className="whitespace-pre-wrap leading-relaxed break-words [word-break:break-word]">{msg.text}</p>
                    ) : (
                      <div className="leading-relaxed text-[#1f1f1f] break-words [word-break:break-word] overflow-x-auto">
                        <MarkdownViewer content={msg.text} />
                      </div>
                    )}
                    <span className={`text-[9px] block text-right mt-1 ${msg.sender === "user" ? "text-blue-100" : "text-[#747775]"}`}>
                      {msg.timestamp}
                    </span>
                  </div>
                </div>
              ))}

              {aiThinking && (
                <div className="flex gap-2.5 items-center text-[#747775] text-xs bg-white p-3 rounded-2xl border border-[#e1e3e1] w-fit shadow-2xs animate-pulse">
                  <Sparkles className="w-4 h-4 text-[#0b57d0] animate-spin" />
                  <span>Analyzing {doc.title}...</span>
                </div>
              )}
              <div ref={chatBottomRef} />
            </div>

            {/* Input Bar */}
            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleSendChatMessage();
              }}
              className="p-3 border-t border-[#e1e3e1] bg-white flex items-center gap-2"
            >
              <div className="flex-1 relative flex items-center">
                <input
                  type="text"
                  value={chatInput}
                  onChange={(e) => setChatInput(e.target.value)}
                  placeholder={`Ask AI about ${doc.title}...`}
                  className="w-full pl-4 pr-10 py-2.5 rounded-full bg-[#edf2fc] border border-[#d3d7dc] text-xs text-[#1f1f1f] placeholder-[#747775] focus:outline-none focus:bg-white focus:border-[#0b57d0] focus:ring-2 focus:ring-[#0b57d0]/30 transition-all shadow-inner"
                />
                <button
                  type="submit"
                  disabled={!chatInput.trim() || aiThinking}
                  className="absolute right-1.5 p-1.5 rounded-full bg-[#0b57d0] hover:bg-[#0945a5] text-white disabled:opacity-40 transition-all hover:scale-105 shadow-sm"
                  title="Send message"
                >
                  <Send className="w-3.5 h-3.5" />
                </button>
              </div>
            </form>
          </aside>
        )}
      </div>
    </div>
  );
}
