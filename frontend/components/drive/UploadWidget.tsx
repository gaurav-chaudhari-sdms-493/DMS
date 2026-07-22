"use client";
import React, { useState } from "react";
import { ChevronDown, ChevronUp, X, CheckCircle, AlertCircle, Loader2 } from "lucide-react";

export interface UploadItem {
  id: string;
  name: string;
  progress: number;
  status: "uploading" | "completed" | "error";
  errorMsg?: string;
}

interface UploadWidgetProps {
  uploads: UploadItem[];
  onDismiss: () => void;
}

export function UploadWidget({ uploads, onDismiss }: UploadWidgetProps) {
  const [minimized, setMinimized] = useState(false);

  if (!uploads || uploads.length === 0) return null;

  const activeCount = uploads.filter((u) => u.status === "uploading").length;
  const completedCount = uploads.filter((u) => u.status === "completed").length;

  return (
    <div className="fixed bottom-6 right-6 z-50 w-80 glass rounded-2xl border border-borderDark/80 shadow-2xl overflow-hidden animate-fadeIn select-none">
      {/* Widget Header */}
      <div className="flex items-center justify-between px-4 py-3 bg-surface/90 border-b border-borderDark/60">
        <span className="text-xs font-bold text-textMain">
          {activeCount > 0
            ? `Uploading ${activeCount} item${activeCount > 1 ? "s" : ""}`
            : `${completedCount} upload${completedCount > 1 ? "s" : ""} complete`}
        </span>

        <div className="flex items-center gap-1">
          <button
            onClick={() => setMinimized(!minimized)}
            className="p-1 rounded-lg text-textMuted hover:text-textMain hover:bg-surface"
          >
            {minimized ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </button>
          <button
            onClick={onDismiss}
            className="p-1 rounded-lg text-textMuted hover:text-textMain hover:bg-surface"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Upload Items List */}
      {!minimized && (
        <div className="max-h-56 overflow-y-auto p-3 space-y-3">
          {uploads.map((item) => (
            <div key={item.id} className="space-y-1 text-xs">
              <div className="flex items-center justify-between text-textMain">
                <span className="truncate max-w-[180px] font-medium" title={item.name}>
                  {item.name}
                </span>

                {item.status === "uploading" && (
                  <Loader2 className="w-3.5 h-3.5 text-primary animate-spin" />
                )}
                {item.status === "completed" && (
                  <CheckCircle className="w-3.5 h-3.5 text-emerald-400" />
                )}
                {item.status === "error" && (
                  <AlertCircle className="w-3.5 h-3.5 text-red-400" />
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
