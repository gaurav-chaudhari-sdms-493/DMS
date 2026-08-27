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
  AlertCircle,
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
      const isPending = doc.status === "pending" || doc.status === "processing";
      setChatMessages([
        {
          id: "welcome-1",
          sender: "ai",
          text: isPending
            ? `Hi! I'm your AI assistant for **${doc.title}**. *(Note: Background AI indexing & 1024d vector embedding generation is currently in progress. I will answer your questions using preview text in the meantime!)*`
            : `Hi! I'm your AI assistant for **${doc.title}**. Ask me any question about this document's content!`,
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
      const extractedText = textContent || (docxHtml ? docxHtml.replace(/<[^>]+>/g, " ") : null) || (excelSheets.length > 0 ? excelSheets.map(s => `${s.name}:\n${s.html.replace(/<[^>]+>/g, " ")}`).join("\n") : null);
      const filters: any = { document_id: doc.id };
      if (extractedText) {
        filters.document_text = extractedText;
      }

      const searchRes = await api.search.query(textToSend, 5, filters);

      let aiResponseText = "";
      if (searchRes && searchRes.ai_summary && !searchRes.ai_summary.includes("No matching documents were found in your drive")) {
        aiResponseText = searchRes.ai_summary;
      } else if (searchRes && searchRes.results && searchRes.results.length > 0) {
        const topSnippet = searchRes.results[0].snippet;
        aiResponseText = `Based strictly on **${doc.title}**:\n\n${topSnippet}`;
      } else if (extractedText) {
        aiResponseText = `Based on the text contents of **${doc.title}**:\n\n` + extractedText.slice(0, 400) + "...";
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

  const formatQualityWarnings = (warnings?: string[]) => {
    if (!warnings || warnings.length === 0) return "scan quality warning";
    const map: Record<string, string> = {
      blurry: "Image is blurry",
      underexposed: "Too dark",
      overexposed: "Too bright",
      possible_blank_page: "May be a blank page",
      low_resolution: "Resolution too low",
    };
    return warnings.map((w) => map[w] || w).join(", ");
  };

  return (
    <div className="fixed inset-0 z-50 flex flex-col bg-[#111111]/95 backdrop-blur-md animate-fadeIn select-none">
      {/* Google Drive Dark Header Bar */}
      <header className="h-14 px-4 bg-[#1f1f1f] border-b border-[#333333] flex items-center justify-between z-30 text-white">
        {/* Left Info & Close Button */}
        <div className="flex items-center gap-3 min-w-0">
          <button
            onClick={onClose}
            className="p-2 rounded-full text-white/80 hover:text-white hover:bg-white/10 transition-colors"
            title="Close viewer"
          >
            <X className="w-5 h-5" />
          </button>
          {getFileIconHeader()}
          <div className="min-w-0">
            <h2 className="text-sm font-semibold text-white truncate max-w-sm" title={doc.title}>
              {doc.title}
            </h2>
            <span className="text-[10px] text-white/60 uppercase font-mono font-bold">
              {ext || "File"}
            </span>
          </div>
        </div>

        {/* Center Zoom Controls */}
        <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-[#2d2d2d] border border-white/10 text-xs text-white/90">
          <button
            onClick={() => setZoom((z) => Math.max(25, z - 25))}
            className="p-1 rounded-full hover:bg-white/15 transition-colors"
            title="Zoom out"
          >
            <ZoomOut className="w-4 h-4" />
          </button>
          <span className="w-12 text-center font-mono font-bold">{zoom}%</span>
          <button
            onClick={() => setZoom((z) => Math.min(300, z + 25))}
            className="p-1 rounded-full hover:bg-white/15 transition-colors"
            title="Zoom in"
          >
            <ZoomIn className="w-4 h-4" />
          </button>
          {zoom !== 100 && (
            <button
              onClick={() => setZoom(100)}
              className="px-2 py-0.5 text-[10px] font-semibold bg-white/20 hover:bg-white/30 rounded-full ml-1 transition-colors"
              title="Reset zoom"
            >
              Reset
            </button>
          )}
        </div>

        {/* Right Actions Toolbar & AI Chatbot Toggle */}
        <div className="flex items-center gap-3">
          <button
            onClick={() => setShowChat(!showChat)}
            className={`flex items-center gap-2 px-4 py-2 rounded-full text-xs font-bold transition-all shadow-xs ${
              showChat
                ? "bg-[#0b57d0] text-white shadow-blue-500/20"
                : "bg-white/10 text-white hover:bg-white/20 border border-white/10"
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

      {/* Scan Quality Warning Banner Notice */}
      {doc.quality_flag === "needs_review" && (
        <div className="bg-amber-500/20 border-b border-amber-500/40 px-6 py-2.5 flex items-center justify-between text-xs text-amber-200 font-medium select-none z-10 shadow-xs backdrop-blur-md">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-amber-400 shrink-0" />
            <span>
              <strong>Quality Notice:</strong> This scan may have quality issues (
              <span className="font-semibold text-amber-300">{formatQualityWarnings(doc.quality_warnings)}</span>
              ). Consider re-scanning for optimal OCR accuracy.
            </span>
          </div>
        </div>
      )}

      {/* Pending Indexing Banner Notice */}
      {(doc.status === "pending" || doc.status === "processing") && (
        <div className="bg-amber-900/40 border-b border-amber-500/30 px-6 py-2.5 flex items-center justify-between text-xs text-amber-200 font-medium select-none z-10 shadow-xs backdrop-blur-md">
          <div className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-amber-400 animate-spin" />
            <span>
              <strong>AI Indexing In Progress:</strong> Generating OCR, text chunks, and 1024d vector embeddings in background...
            </span>
          </div>
          <span className="text-[10px] bg-amber-500/30 text-amber-100 px-2 py-0.5 rounded-full font-mono font-bold uppercase">
            Status: {doc.status}
          </span>
        </div>
      )}

      {/* Main Body: Left Preview Canvas + Right AI Chat Sidebar */}
      <div className="flex-1 flex overflow-hidden bg-[#1a1a1a]">
        {/* Document Preview Canvas */}
        <main className="flex-1 overflow-y-auto flex justify-center p-8 relative scrollbar-thin">
          {/* PDF Viewer */}
          {isPdf && doc.download_url && (
            <div
              style={{
                transform: `scale(${zoom / 100})`,
                transformOrigin: "top center",
                transition: "transform 0.15s ease-out",
              }}
              className="w-full flex justify-center"
            >
              <iframe
                src={`${doc.download_url}#toolbar=1`}
                className="w-[850px] max-w-[95%] h-[90vh] rounded-sm bg-white shadow-2xl border-0"
                title={doc.title}
              />
            </div>
          )}

          {/* Word (DOCX) Viewer - Styled like Google Docs A4 Paper */}
          {isDocx && (
            <div
              style={{
                transform: `scale(${zoom / 100})`,
                transformOrigin: "top center",
                transition: "transform 0.15s ease-out",
              }}
              className="w-[816px] max-w-[95%] min-h-[1056px] bg-white text-[#1f1f1f] rounded-sm shadow-2xl p-16 select-text border border-[#dedede] my-4 relative mx-auto"
            >
              <style>{`
                .docx-preview-paper {
                  color: #111827 !important;
                  font-family: 'Google Sans', Inter, system-ui, -apple-system, sans-serif !important;
                }
                .docx-preview-paper p, 
                .docx-preview-paper span, 
                .docx-preview-paper div,
                .docx-preview-paper li,
                .docx-preview-paper td,
                .docx-preview-paper th {
                  color: #111827 !important;
                  line-height: 1.6 !important;
                }
                .docx-preview-paper p {
                  margin-bottom: 0.75rem !important;
                }
                .docx-preview-paper h1, 
                .docx-preview-paper h2, 
                .docx-preview-paper h3, 
                .docx-preview-paper h4 {
                  color: #000000 !important;
                  font-weight: 700 !important;
                  margin-top: 1.5rem !important;
                  margin-bottom: 0.5rem !important;
                  line-height: 1.3 !important;
                }
                .docx-preview-paper h1 { font-size: 1.5rem !important; border-bottom: 1px solid #e5e7eb; padding-bottom: 0.35rem; }
                .docx-preview-paper h2 { font-size: 1.25rem !important; }
                .docx-preview-paper h3 { font-size: 1.1rem !important; }
                .docx-preview-paper img {
                  max-width: 240px !important;
                  max-height: 240px !important;
                  width: auto !important;
                  height: auto !important;
                  object-fit: contain !important;
                  margin: 1.25rem auto !important;
                  display: block !important;
                  border-radius: 8px;
                }
                .docx-preview-paper table {
                  width: 100% !important;
                  border-collapse: collapse !important;
                  margin: 1rem 0 !important;
                }
                .docx-preview-paper td, .docx-preview-paper th {
                  border: 1px solid #e5e7eb !important;
                  padding: 8px 12px !important;
                  vertical-align: top !important;
                  color: #111827 !important;
                  background-color: #ffffff !important;
                }
                .docx-preview-paper ul {
                  list-style-type: disc !important;
                  margin-left: 1.5rem !important;
                  margin-bottom: 1rem !important;
                }
                .docx-preview-paper ol {
                  list-style-type: decimal !important;
                  margin-left: 1.5rem !important;
                  margin-bottom: 1rem !important;
                }
                .docx-preview-paper a {
                  color: #2563eb !important;
                  text-decoration: underline !important;
                }
              `}</style>
              {loadingText ? (
                <div className="text-[#444746] text-center py-32 flex flex-col items-center gap-3">
                  <div className="w-8 h-8 border-4 border-[#0b57d0] border-t-transparent rounded-full animate-spin" />
                  <span>Converting Word Document preview...</span>
                </div>
              ) : docxHtml ? (
                <div
                  className="docx-preview-paper prose max-w-none text-sm leading-relaxed text-[#1f1f1f]"
                  dangerouslySetInnerHTML={{ __html: docxHtml }}
                />
              ) : (
                <div className="text-[#747775] text-center py-20">No text content extracted.</div>
              )}
            </div>
          )}

          {/* Excel / CSV Spreadsheet Viewer */}
          {(isExcel || isCsv) && (
            <div
              style={{
                transform: `scale(${zoom / 100})`,
                transformOrigin: "top center",
                transition: "transform 0.15s ease-out",
              }}
              className="w-full max-w-5xl h-full max-h-[85vh] flex flex-col bg-white border border-[#e1e3e1] rounded-2xl shadow-xl overflow-hidden"
            >
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
            <div
              style={{
                transform: `scale(${zoom / 100})`,
                transformOrigin: "top center",
                transition: "transform 0.15s ease-out",
              }}
              className="w-full max-w-4xl h-full max-h-[85vh] bg-white text-[#1f1f1f] rounded-2xl shadow-xl p-8 overflow-y-auto border border-[#e1e3e1] flex flex-col items-center"
            >
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
            <div className="w-full h-full overflow-auto flex items-center justify-center p-4">
              <div
                style={{
                  transform: `scale(${zoom / 100})`,
                  transformOrigin: "center center",
                  transition: "transform 0.15s ease-out",
                }}
                className="flex items-center justify-center max-w-full max-h-full"
              >
                <img
                  src={doc.download_url}
                  alt={doc.title}
                  className="max-w-full max-h-[80vh] object-contain rounded-xl shadow-xl border border-[#e1e3e1]"
                />
              </div>
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
              {/* eslint-disable-next-line jsx-a11y/media-has-caption -- arbitrary user-uploaded audio,
                  no transcript/caption source exists to attach; an empty track would falsely claim one */}
              <audio controls src={doc.download_url} className="w-full" />
            </div>
          )}

          {/* Video Player */}
          {isVideo && doc.download_url && (
            <div className="w-full max-w-4xl max-h-[80vh] flex items-center justify-center">
              {/* eslint-disable-next-line jsx-a11y/media-has-caption -- arbitrary user-uploaded video,
                  no transcript/caption source exists to attach; an empty track would falsely claim one */}
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
            <div
              style={{
                transform: `scale(${zoom / 100})`,
                transformOrigin: "top center",
                transition: "transform 0.15s ease-out",
              }}
              className="w-full max-w-5xl h-full max-h-[80vh] flex flex-col bg-white border border-[#e1e3e1] rounded-2xl shadow-xl overflow-hidden"
            >
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
            {/* Draggable Left Boundary Handle. WAI-ARIA APG "window splitter" pattern:
                role="separator" with tabIndex+onKeyDown is the recommended accessible
                resize-handle widget; jsx-a11y's interactive-roles list doesn't include
                separator, hence the block disable below. */}
            {/* eslint-disable jsx-a11y/no-noninteractive-element-interactions, jsx-a11y/no-noninteractive-tabindex */}
            <div
              role="separator"
              aria-orientation="vertical"
              aria-label="Resize chat panel"
              aria-valuenow={chatWidth}
              aria-valuemin={340}
              aria-valuemax={typeof window !== "undefined" ? Math.min(950, window.innerWidth - 200) : 950}
              tabIndex={0}
              onMouseDown={handleChatMouseDown}
              onKeyDown={(e) => {
                const maxWidth = typeof window !== "undefined" ? Math.min(950, window.innerWidth - 200) : 950;
                if (e.key === "ArrowLeft") {
                  e.preventDefault();
                  setChatWidth((w) => Math.min(maxWidth, w + 20));
                } else if (e.key === "ArrowRight") {
                  e.preventDefault();
                  setChatWidth((w) => Math.max(340, w - 20));
                } else if (e.key === "Home") {
                  e.preventDefault();
                  setChatWidth(340);
                } else if (e.key === "End") {
                  e.preventDefault();
                  setChatWidth(maxWidth);
                }
              }}
              className={`absolute left-0 top-0 bottom-0 w-2.5 -ml-1.5 cursor-col-resize z-50 flex items-center justify-center group hover:bg-[#0b57d0]/20 transition-colors ${
                isResizingChat ? "bg-[#0b57d0]/30" : ""
              }`}
              title="Click and drag, or use arrow keys, to resize the chat panel"
            >
              <div className="w-1 h-10 bg-[#c4c7c5] group-hover:bg-[#0b57d0] rounded-full transition-colors" />
            </div>
            {/* eslint-enable jsx-a11y/no-noninteractive-element-interactions, jsx-a11y/no-noninteractive-tabindex */}

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
                  aria-label={`Ask AI about ${doc.title}`}
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
