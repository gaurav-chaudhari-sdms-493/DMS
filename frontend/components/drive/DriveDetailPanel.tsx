"use client";
import React, { useEffect, useState } from "react";
import { X, FileText, Folder as FolderIcon, Download, Sparkles, HardDrive, Info } from "lucide-react";
import type { Folder, DocumentListItem, DocumentDetailResponse } from "@/types";
import { api } from "@/lib/api";

interface DriveDetailPanelProps {
  selectedFolder: Folder | null;
  selectedDoc: DocumentListItem | null;
  onClose: () => void;
}

export function DriveDetailPanel({
  selectedFolder,
  selectedDoc,
  onClose,
}: DriveDetailPanelProps) {
  const [docDetail, setDocDetail] = useState<DocumentDetailResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<"details" | "versions" | "metadata">("details");

  useEffect(() => {
    if (selectedDoc) {
      setLoading(true);
      api.documents
        .get(selectedDoc.id)
        .then((res) => {
          setDocDetail(res);
        })
        .catch((err) => {
          console.error("Failed to load doc detail:", err);
        })
        .finally(() => setLoading(false));
    } else {
      setDocDetail(null);
    }
  }, [selectedDoc]);

  if (!selectedFolder && !selectedDoc) {
    return null;
  }

  const formatSize = (bytes: number) => {
    if (!bytes) return "0 B";
    const k = 1024;
    const sizes = ["B", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i];
  };

  return (
    <aside className="w-80 flex-shrink-0 bg-white border-l border-[#e1e3e1] flex flex-col h-full overflow-y-auto select-none animate-fadeIn">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-[#e1e3e1]">
        <h3 className="font-semibold text-sm text-[#1f1f1f] truncate">
          {selectedFolder ? selectedFolder.name : selectedDoc?.title}
        </h3>
        <button
          onClick={onClose}
          className="p-1 rounded-full text-[#444746] hover:bg-[#f0f4f9]"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Item Icon Box */}
      <div className="p-6 flex flex-col items-center justify-center border-b border-[#e1e3e1] bg-[#f8f9fa]">
        {selectedFolder ? (
          <div className="w-20 h-20 rounded-2xl bg-[#f0f4f9] flex items-center justify-center mb-3 shadow-xs border border-[#e1e3e1]">
            <FolderIcon className="w-10 h-10 text-[#5f6368] fill-[#fbbc04]" />
          </div>
        ) : selectedDoc && selectedDoc.title.match(/\.(jpg|jpeg|png|webp|gif|svg|bmp)$/i) && selectedDoc.download_url ? (
          <div className="relative w-full max-w-[200px] h-40 bg-white rounded-2xl border border-[#e1e3e1] p-1.5 flex items-center justify-center shadow-md overflow-hidden mb-3">
            <img
              src={selectedDoc.download_url}
              alt={selectedDoc.title}
              className="max-w-full max-h-full object-contain rounded-xl"
            />
          </div>
        ) : selectedDoc && selectedDoc.title.toLowerCase().endsWith(".pdf") ? (
          <div className="w-24 h-32 bg-white rounded-xl shadow-md border border-[#e1e3e1] flex flex-col overflow-hidden mb-3">
            <div className="h-7 bg-[#ea4335] flex items-center px-2.5 text-xs font-bold text-white tracking-wider">
              PDF
            </div>
            <div className="p-2.5 space-y-2 flex-1 bg-white">
              <div className="h-2 bg-[#f1f3f4] rounded w-full" />
              <div className="h-2 bg-[#f1f3f4] rounded w-4/5" />
              <div className="h-2 bg-[#f1f3f4] rounded w-3/5" />
              <div className="h-2 bg-[#f1f3f4] rounded w-full mt-3" />
              <div className="h-2 bg-[#f1f3f4] rounded w-2/3" />
            </div>
          </div>
        ) : (
          <div className="w-24 h-32 bg-white rounded-xl shadow-md border border-[#e1e3e1] flex flex-col overflow-hidden mb-3">
            <div className="h-7 bg-[#0d2e5c] flex items-center px-2.5 text-xs font-bold text-white tracking-wider">
              DOC
            </div>
            <div className="p-2.5 space-y-2 flex-1 bg-white">
              <div className="h-2 bg-[#edf2fc] rounded w-full" />
              <div className="h-2 bg-[#edf2fc] rounded w-3/4" />
              <div className="h-2 bg-[#edf2fc] rounded w-5/6" />
              <div className="h-2 bg-[#edf2fc] rounded w-1/2" />
            </div>
          </div>
        )}

        <span className="font-bold text-sm text-[#1f1f1f] text-center line-clamp-2">
          {selectedFolder ? selectedFolder.name : selectedDoc?.title}
        </span>

        {selectedDoc?.download_url && (
          <a
            href={selectedDoc.download_url}
            download={selectedDoc.title}
            className="mt-4 flex items-center gap-2 px-4 py-2 bg-[#0d2e5c] text-white hover:bg-[#0945a5] rounded-full text-xs font-semibold shadow-md transition-all"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Download file</span>
          </a>
        )}
      </div>

      {/* Tabs */}
      {selectedDoc && (
        <div className="flex border-b border-[#e1e3e1] text-xs font-medium text-[#444746] bg-white">
          <button
            onClick={() => setActiveTab("details")}
            className={`flex-1 py-2.5 text-center transition-colors border-b-2 ${
              activeTab === "details" ? "border-[#0d2e5c] text-[#0d2e5c] font-bold" : "border-transparent hover:text-[#1f1f1f]"
            }`}
          >
            Details
          </button>
          <button
            onClick={() => setActiveTab("metadata")}
            className={`flex-1 py-2.5 text-center transition-colors border-b-2 ${
              activeTab === "metadata" ? "border-[#0d2e5c] text-[#0d2e5c] font-bold" : "border-transparent hover:text-[#1f1f1f]"
            }`}
          >
            AI Metadata ({docDetail?.metadata?.length || 0})
          </button>
          <button
            onClick={() => setActiveTab("versions")}
            className={`flex-1 py-2.5 text-center transition-colors border-b-2 ${
              activeTab === "versions" ? "border-[#0d2e5c] text-[#0d2e5c] font-bold" : "border-transparent hover:text-[#1f1f1f]"
            }`}
          >
            Versions ({docDetail?.versions?.length || 1})
          </button>
        </div>
      )}

      {/* Details Body */}
      <div className="p-4 flex-1 space-y-4 text-xs">
        {selectedFolder && (
          <div className="space-y-3">
            <div>
              <span className="text-[#444746] block mb-1">Type</span>
              <span className="font-semibold text-[#1f1f1f]">Folder</span>
            </div>
            <div>
              <span className="text-[#444746] block mb-1">Created</span>
              <span className="font-medium text-[#1f1f1f]">{new Date(selectedFolder.created_at).toLocaleString()}</span>
            </div>
            <div>
              <span className="text-[#444746] block mb-1">Storage Location</span>
              <span className="font-medium text-[#1f1f1f]">MinIO Object Storage</span>
            </div>
          </div>
        )}

        {selectedDoc && activeTab === "details" && (
          <div className="space-y-3">
            <div>
              <span className="text-[#444746] block mb-1">Type</span>
              <span className="font-semibold text-[#1f1f1f] uppercase">{selectedDoc.title.split(".").pop() || "Document"}</span>
            </div>
            <div>
              <span className="text-[#444746] block mb-1">Size</span>
              <span className="font-medium text-[#1f1f1f]">{formatSize(selectedDoc.file_size_bytes)}</span>
            </div>
            <div>
              <span className="text-[#444746] block mb-1">Indexing Status</span>
              <span className="inline-block px-2.5 py-1 rounded-full text-[10px] font-semibold bg-[#e6f4ea] text-[#137333]">
                {selectedDoc.status}
              </span>
            </div>
            <div>
              <span className="text-[#444746] block mb-1">Created Date</span>
              <span className="font-medium text-[#1f1f1f]">{new Date(selectedDoc.created_at).toLocaleString()}</span>
            </div>
          </div>
        )}

        {selectedDoc && activeTab === "metadata" && (
          <div className="space-y-2">
            {loading ? (
              <div className="text-[#444746] text-center py-6">Loading AI metadata...</div>
            ) : docDetail?.metadata && Array.isArray(docDetail.metadata) && docDetail.metadata.length > 0 ? (
              docDetail.metadata.map((item: any, idx: number) => {
                const keyStr = typeof item === "string" ? "Metadata" : String(item?.key || item?.name || "Key");
                const rawVal = typeof item === "string" ? item : (item?.value ?? item?.content ?? "");
                const valStr = typeof rawVal === "object" ? JSON.stringify(rawVal) : String(rawVal);
                const score = typeof item?.confidence_score === "number" ? Math.round(item.confidence_score * 100) : 95;

                return (
                  <div key={idx} className="p-3 bg-[#f8f9fa] rounded-xl border border-[#e1e3e1] space-y-1 select-text">
                    <div className="flex items-center justify-between text-[#444746]">
                      <span className="font-semibold text-[#1f1f1f] capitalize">{keyStr}</span>
                      <span className="flex items-center gap-1 text-[10px] text-[#0d2e5c] font-semibold">
                        <Sparkles className="w-3 h-3 text-[#0d2e5c]" />
                        {score}%
                      </span>
                    </div>
                    <p className="text-[#1f1f1f] font-medium break-words text-xs">{valStr}</p>
                  </div>
                );
              })
            ) : (
              <div className="text-center py-6 text-[#444746]">
                <Sparkles className="w-8 h-8 text-[#444746] mx-auto mb-2 opacity-50" />
                <p>No AI metadata extracted yet.</p>
              </div>
            )}
          </div>
        )}

        {selectedDoc && activeTab === "versions" && (
          <div className="space-y-2">
            {loading ? (
              <div className="text-[#444746] text-center py-6">Loading versions...</div>
            ) : docDetail?.versions && docDetail.versions.length > 0 ? (
              docDetail.versions.map((ver) => (
                <div key={ver.id} className="p-3 bg-[#f8f9fa] rounded-xl border border-[#e1e3e1] flex items-center justify-between">
                  <div>
                    <span className="font-bold text-[#1f1f1f] block">Version {ver.version}</span>
                    <span className="text-[10px] text-[#444746]">{new Date(ver.created_at).toLocaleDateString()}</span>
                  </div>

                  {ver.download_url && (
                    <a
                      href={ver.download_url}
                      download
                      className="p-1.5 rounded-lg bg-white text-[#444746] hover:text-[#0d2e5c] border border-[#e1e3e1]"
                    >
                      <Download className="w-3.5 h-3.5" />
                    </a>
                  )}
                </div>
              ))
            ) : (
              <div className="text-center py-6 text-[#444746]">Single version available</div>
            )}
          </div>
        )}
      </div>
    </aside>
  );
}
