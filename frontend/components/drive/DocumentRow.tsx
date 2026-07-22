"use client";
import React, { useState } from "react";
import { FileText, FileSpreadsheet, FileCode, Image, File, Download, ExternalLink, Star, Trash2, Edit2, FolderInput, RotateCcw, MoreVertical } from "lucide-react";
import type { DocumentListItem } from "@/types";

interface DocumentRowProps {
  doc: DocumentListItem;
  onSelect: (doc: DocumentListItem) => void;
  isSelected: boolean;
  onToggleStar: (doc: DocumentListItem) => void;
  onToggleTrash: (doc: DocumentListItem) => void;
  onRename: (doc: DocumentListItem) => void;
  onMove: (doc: DocumentListItem) => void;
  onDeletePermanent?: (doc: DocumentListItem) => void;
  onPreview: (doc: DocumentListItem) => void;
}

export function DocumentRow({
  doc,
  onSelect,
  isSelected,
  onToggleStar,
  onToggleTrash,
  onRename,
  onMove,
  onDeletePermanent,
  onPreview,
}: DocumentRowProps) {
  const [showMenu, setShowMenu] = useState(false);

  const getFileIcon = (title: string) => {
    const ext = title.split(".").pop()?.toLowerCase() || "";
    if (["pdf", "doc", "docx", "txt"].includes(ext)) {
      return <FileText className="w-5 h-5 text-blue-400" />;
    }
    if (["csv", "xlsx", "xls"].includes(ext)) {
      return <FileSpreadsheet className="w-5 h-5 text-emerald-400" />;
    }
    if (["png", "jpg", "jpeg", "svg", "webp"].includes(ext)) {
      return <Image className="w-5 h-5 text-purple-400" />;
    }
    if (["json", "py", "js", "ts", "html"].includes(ext)) {
      return <FileCode className="w-5 h-5 text-amber-400" />;
    }
    return <File className="w-5 h-5 text-secondary" />;
  };

  const formatSize = (bytes: number) => {
    if (!bytes) return "0 B";
    const k = 1024;
    const sizes = ["B", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i];
  };

  return (
    <div
      onClick={() => onSelect(doc)}
      onDoubleClick={() => onPreview(doc)}
      className={`group flex items-center justify-between px-4 py-3 border-b border-borderDark/40 transition-colors cursor-pointer select-none ${
        isSelected
          ? "bg-primary/15 text-textMain"
          : "hover:bg-surface/70 text-textMuted hover:text-textMain"
      }`}
    >
      <div className="flex items-center gap-3 min-w-0 flex-1">
        {getFileIcon(doc.title)}
        <span className="text-sm font-medium text-textMain truncate">
          {doc.title}
        </span>
      </div>

      <div className="w-36 text-xs text-textMuted hidden sm:block">
        {formatSize(doc.file_size_bytes)}
      </div>

      <div className="w-36 text-xs text-textMuted hidden md:block">
        {new Date(doc.created_at).toLocaleDateString()}
      </div>

      <div className="flex items-center gap-2 relative">
        <span className={`px-2 py-0.5 rounded-full text-[10px] font-medium capitalize hidden lg:inline-block ${
          doc.status === "indexed" ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20" : "bg-amber-500/10 text-amber-400 border border-amber-500/20"
        }`}>
          {doc.status}
        </span>

        {doc.is_starred && (
          <Star className="w-4 h-4 text-amber-400 fill-amber-400 flex-shrink-0" />
        )}

        <button
          onClick={(e) => {
            e.stopPropagation();
            setShowMenu(!showMenu);
          }}
          className="opacity-0 group-hover:opacity-100 p-1.5 rounded-lg text-textMuted hover:text-textMain hover:bg-surface transition-all"
        >
          <MoreVertical className="w-4 h-4" />
        </button>

        {showMenu && (
          <>
            <div className="fixed inset-0 z-40" onClick={() => setShowMenu(false)} />
            <div className="absolute right-0 top-8 z-50 w-48 glass rounded-2xl shadow-2xl border border-borderDark p-1.5 animate-fadeIn text-sm">
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  setShowMenu(false);
                  onPreview(doc);
                }}
                className="flex items-center gap-2.5 w-full px-3 py-2 rounded-xl hover:bg-surface text-textMain font-medium"
              >
                <ExternalLink className="w-4 h-4 text-primary" />
                <span>Preview / Details</span>
              </button>

              {doc.download_url && (
                <a
                  href={doc.download_url}
                  download={doc.title}
                  onClick={(e) => e.stopPropagation()}
                  className="flex items-center gap-2.5 w-full px-3 py-2 rounded-xl hover:bg-surface text-textMain font-medium"
                >
                  <Download className="w-4 h-4 text-secondary" />
                  <span>Download</span>
                </a>
              )}

              <button
                onClick={(e) => {
                  e.stopPropagation();
                  setShowMenu(false);
                  onToggleStar(doc);
                }}
                className="flex items-center gap-2.5 w-full px-3 py-2 rounded-xl hover:bg-surface text-textMain font-medium"
              >
                <Star className={`w-4 h-4 ${doc.is_starred ? "text-amber-400 fill-amber-400" : "text-textMuted"}`} />
                <span>{doc.is_starred ? "Remove star" : "Add star"}</span>
              </button>

              <button
                onClick={(e) => {
                  e.stopPropagation();
                  setShowMenu(false);
                  onRename(doc);
                }}
                className="flex items-center gap-2.5 w-full px-3 py-2 rounded-xl hover:bg-surface text-textMain font-medium"
              >
                <Edit2 className="w-4 h-4 text-textMuted" />
                <span>Rename</span>
              </button>

              <button
                onClick={(e) => {
                  e.stopPropagation();
                  setShowMenu(false);
                  onMove(doc);
                }}
                className="flex items-center gap-2.5 w-full px-3 py-2 rounded-xl hover:bg-surface text-textMain font-medium"
              >
                <FolderInput className="w-4 h-4 text-textMuted" />
                <span>Move to...</span>
              </button>

              <div className="h-px bg-borderDark/50 my-1" />

              <button
                onClick={(e) => {
                  e.stopPropagation();
                  setShowMenu(false);
                  onToggleTrash(doc);
                }}
                className="flex items-center gap-2.5 w-full px-3 py-2 rounded-xl hover:bg-red-500/10 text-red-400 font-medium"
              >
                {doc.is_trashed ? (
                  <>
                    <RotateCcw className="w-4 h-4" />
                    <span>Restore</span>
                  </>
                ) : (
                  <>
                    <Trash2 className="w-4 h-4" />
                    <span>Move to trash</span>
                  </>
                )}
              </button>

              {doc.is_trashed && onDeletePermanent && (
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    setShowMenu(false);
                    onDeletePermanent(doc);
                  }}
                  className="flex items-center gap-2.5 w-full px-3 py-2 rounded-xl hover:bg-red-500/20 text-red-500 font-medium"
                >
                  <Trash2 className="w-4 h-4" />
                  <span>Delete forever</span>
                </button>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
