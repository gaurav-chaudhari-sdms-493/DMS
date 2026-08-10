"use client";
import React, { useState } from "react";
import { ChevronDown, ChevronUp, X, CheckCircle, AlertCircle, Loader2, Sparkles } from "lucide-react";

export interface UploadItem {
  id: string;
  documentId?: string;
  name: string;
  progress: number;
  status: "uploading" | "indexing" | "completed" | "error";
  errorMsg?: string;
}

interface UploadWidgetProps {
  uploads: UploadItem[];
  onDismiss: () => void;
}

export function UploadWidget({ uploads, onDismiss }: UploadWidgetProps) {
  const [minimized, setMinimized] = useState(false);

  if (!uploads || uploads.length === 0) return null;

  const uploadingCount = uploads.filter((u) => u.status === "uploading").length;
  const indexingCount = uploads.filter((u) => u.status === "indexing").length;
  const completedCount = uploads.filter((u) => u.status === "completed").length;

  const getHeaderText = () => {
    if (uploadingCount > 0) {
      return uploadingCount > 1 ? `Uploading ${uploadingCount} files...` : "Uploading 1 file...";
    }
    if (indexingCount > 0) {
      return indexingCount > 1 ? `Indexing ${indexingCount} files (Generating embeddings)...` : "Indexing 1 file (Generating embeddings)...";
    }
    return completedCount > 1 ? `${completedCount} files indexed & ready` : "1 file indexed & ready";
  };

  return (
    <div className="fixed bottom-6 right-6 z-50 w-84 glass rounded-2xl border border-borderDark/80 shadow-2xl overflow-hidden animate-fadeIn select-none">
      {/* Widget Header */}
      <div className="flex items-center justify-between px-4 py-3 bg-surface/90 border-b border-borderDark/60">
        <span className="text-xs font-bold text-textMain flex items-center gap-1.5">
          {indexingCount > 0 && <Sparkles className="w-3.5 h-3.5 text-amber-400 animate-spin" />}
          <span>{getHeaderText()}</span>
        </span>

        <div className="flex items-center gap-1">
          <button
            onClick={() => setMinimized(!minimized)}
            className="p-1 rounded-lg text-textMuted hover:text-textMain hover:bg-surface transition-colors"
          >
            {minimized ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </button>
          <button
            onClick={onDismiss}
            className="p-1 rounded-lg text-textMuted hover:text-textMain hover:bg-surface transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Upload Items List */}
      {!minimized && (
        <div className="max-h-60 overflow-y-auto p-3 space-y-3">
          {uploads.map((item) => (
            <div key={item.id} className="space-y-1.5 text-xs bg-surface/40 p-2.5 rounded-xl border border-borderDark/40">
              <div className="flex items-center justify-between text-textMain">
                <span className="truncate max-w-[170px] font-medium" title={item.name}>
                  {item.name}
                </span>

                {item.status === "uploading" && (
                  <div className="flex items-center gap-1 text-[10px] text-primary font-semibold">
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    <span>Uploading</span>
                  </div>
                )}
                {item.status === "indexing" && (
                  <div className="flex items-center gap-1 text-[10px] text-amber-400 font-semibold">
                    <Sparkles className="w-3.5 h-3.5 text-amber-400 animate-spin" />
                    <span>Indexing AI</span>
                  </div>
                )}
                {item.status === "completed" && (
                  <div className="flex items-center gap-1 text-[10px] text-emerald-400 font-semibold">
                    <CheckCircle className="w-3.5 h-3.5" />
                    <span>Ready</span>
                  </div>
                )}
                {item.status === "error" && (
                  <div className="flex items-center gap-1 text-[10px] text-red-400 font-semibold">
                    <AlertCircle className="w-3.5 h-3.5" />
                    <span>Error</span>
                  </div>
                )}
              </div>

              {item.status === "uploading" && (
                <div className="w-full h-1.5 bg-surface rounded-full overflow-hidden border border-borderDark/40">
                  <div
                    className="h-full bg-gradient-to-r from-primary to-secondary transition-all duration-300"
                    style={{ width: `${item.progress}%` }}
                  />
                </div>
              )}

              {item.status === "indexing" && (
                <p className="text-[10px] text-amber-300/90 font-mono animate-pulse">
                  Generating OCR, chunks & 1024d embeddings...
                </p>
              )}

              {item.status === "error" && item.errorMsg && (
                <p className="text-[10px] text-red-400">{item.errorMsg}</p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
