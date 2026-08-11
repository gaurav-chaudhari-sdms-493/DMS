"use client";
import React, { useState } from "react";
import {
  ChevronDown,
  FileText,
  FileCode,
  Image as ImageIcon,
  MoreVertical,
  List,
  LayoutGrid,
  Star,
  Download,
  Edit2,
  FolderInput,
  Trash2,
  UploadCloud,
  Eye,
} from "lucide-react";
import type { DocumentListItem } from "@/types";

interface SuggestedFilesTableProps {
  documents: DocumentListItem[];
  onSelectDoc: (doc: DocumentListItem, isMulti: boolean) => void;
  onPreviewDoc?: (doc: DocumentListItem) => void;
  onContextMenu?: (e: React.MouseEvent, doc: DocumentListItem) => void;
  selectedDocId?: string | null;
  selectedDocIds?: Set<string>;
  onToggleSelectAll?: () => void;
  isAllSelected?: boolean;
  onToggleStar: (doc: DocumentListItem) => void;
  onRename: (doc: DocumentListItem) => void;
  onMove: (doc: DocumentListItem) => void;
  onTrash: (doc: DocumentListItem) => void;
}

export function SuggestedFilesTable({
  documents,
  onSelectDoc,
  onPreviewDoc,
  onContextMenu,
  selectedDocId,
  selectedDocIds = new Set(),
  onToggleSelectAll,
  isAllSelected = false,
  onToggleStar,
  onRename,
  onMove,
  onTrash,
}: SuggestedFilesTableProps) {
  const [collapsed, setCollapsed] = useState(false);
  const [viewMode, setViewMode] = useState<"list" | "grid">("list");
  const [activeMenuId, setActiveMenuId] = useState<string | null>(null);

  const isImageFile = (filename: string) => {
    const ext = filename.split(".").pop()?.toLowerCase() || "";
    return ["jpg", "jpeg", "png", "webp", "gif", "svg", "bmp"].includes(ext);
  };

  const getFileIcon = (title: string, downloadUrl?: string | null) => {
    const ext = title.split(".").pop()?.toLowerCase() || "";
    if (["png", "jpg", "jpeg", "webp", "gif", "svg"].includes(ext) && downloadUrl) {
      return (
        <img
          src={downloadUrl}
          alt={title}
          className="w-5 h-5 object-cover rounded shadow-xs border border-[#e1e3e1] flex-shrink-0"
          onError={(e) => {
            (e.target as HTMLElement).style.display = "none";
          }}
        />
      );
    }
    if (["xlsx", "xls", "csv", "excel"].includes(ext)) {
      return (
        <div className="w-5 h-5 bg-[#107c41] rounded text-white flex items-center justify-center font-bold text-[10px]">
          X
        </div>
      );
    }
    if (["pdf"].includes(ext)) {
      return (
        <div className="w-5 h-5 bg-[#ea4335] rounded text-white flex items-center justify-center font-bold text-[9px]">
          PDF
        </div>
      );
    }
    if (["ipynb"].includes(ext)) {
      return (
        <div className="w-5 h-5 bg-[#ff6d00] rounded text-white flex items-center justify-center font-bold text-[9px]">
          co
        </div>
      );
    }
    if (["json", "js", "ts", "py"].includes(ext)) {
      return <FileCode className="w-5 h-5 text-[#0b57d0]" />;
    }
    if (["png", "jpg", "jpeg", "svg"].includes(ext)) {
      return <ImageIcon className="w-5 h-5 text-[#a142f4]" />;
    }
    return <FileText className="w-5 h-5 text-[#0b57d0]" />;
  };

  const renderGridThumbnail = (row: { title: string; downloadUrl?: string | null }) => {
    const isImg = isImageFile(row.title);
    const ext = row.title.split(".").pop()?.toLowerCase() || "";

    if (isImg && row.downloadUrl) {
      return (
        <div className="relative w-full h-32 bg-[#f8f9fa] rounded-t-2xl border-b border-[#e1e3e1] overflow-hidden flex items-center justify-center">
          <img
            src={row.downloadUrl}
            alt={row.title}
            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
            onError={(e) => {
              (e.target as HTMLElement).style.display = "none";
            }}
          />
        </div>
      );
    }

    if (ext === "pdf" && row.downloadUrl) {
      return (
        <div className="relative w-full h-36 bg-[#f8f9fa] rounded-t-2xl border-b border-[#e1e3e1] overflow-hidden flex items-center justify-center pointer-events-none">
          <iframe
            src={`${row.downloadUrl}#page=1&toolbar=0&navpanes=0&scrollbar=0`}
            className="w-full h-[180%] border-0 bg-white scale-100 transform origin-top pointer-events-none select-none"
            title={row.title}
          />
        </div>
      );
    }

    if (["doc", "docx"].includes(ext)) {
      return (
        <div className="relative w-full h-36 bg-[#f8f9fa] rounded-t-2xl border-b border-[#e1e3e1] flex items-center justify-center p-3 overflow-hidden">
          <div className="w-20 h-28 bg-white rounded-md shadow-md border border-[#e1e3e1] flex flex-col p-2 overflow-hidden group-hover:scale-105 transition-transform">
            <div className="flex items-center gap-1 border-b border-[#e1e3e1] pb-1 mb-1.5">
              <div className="w-2.5 h-2.5 bg-[#0b57d0] rounded-xs flex-shrink-0" />
              <span className="text-[7px] font-bold text-[#1f1f1f] truncate leading-none" title={row.title}>
                {row.title.replace(/\.[^/.]+$/, "")}
              </span>
            </div>
            <div className="space-y-1 text-[5px] text-[#444746] leading-tight flex-1 font-serif select-none overflow-hidden opacity-80">
              <p className="font-bold text-[6px] text-[#1f1f1f]">{row.title.split(".")[0]}</p>
              <p className="line-clamp-2">This document contains indexed text and metadata extracted for search & retrieval.</p>
              <div className="h-0.5 bg-[#edf2fc] rounded w-full my-0.5" />
              <div className="h-0.5 bg-[#edf2fc] rounded w-5/6" />
              <div className="h-0.5 bg-[#edf2fc] rounded w-3/4" />
            </div>
          </div>
        </div>
      );
    }

    if (["xlsx", "xls", "csv"].includes(ext)) {
      return (
        <div className="relative w-full h-36 bg-[#f8f9fa] rounded-t-2xl border-b border-[#e1e3e1] flex items-center justify-center p-3 overflow-hidden">
          <div className="w-20 h-28 bg-white rounded-md shadow-md border border-[#e1e3e1] flex flex-col p-1.5 overflow-hidden group-hover:scale-105 transition-transform">
            <div className="flex items-center gap-1 border-b border-emerald-200 pb-1 mb-1">
              <div className="w-2.5 h-2.5 bg-[#107c41] rounded-xs text-white text-[5px] font-bold flex items-center justify-center">X</div>
              <span className="text-[7px] font-bold text-emerald-800 truncate leading-none">Sheet 1</span>
            </div>
            <div className="grid grid-cols-3 gap-0.5 border border-[#e1e3e1] rounded-xs p-0.5 bg-[#f8fafd] flex-1">
              <div className="bg-emerald-100 h-2 text-[5px] font-bold text-center">A</div>
              <div className="bg-emerald-100 h-2 text-[5px] font-bold text-center">B</div>
              <div className="bg-emerald-100 h-2 text-[5px] font-bold text-center">C</div>
              {Array.from({ length: 9 }).map((_, i) => (
                <div key={i} className="bg-white border border-[#e1e3e1]/60 h-2" />
              ))}
            </div>
          </div>
        </div>
      );
    }

    // Default Document / Code / Text
    return (
      <div className="relative w-full h-36 bg-[#f8f9fa] rounded-t-2xl border-b border-[#e1e3e1] flex items-center justify-center p-3 overflow-hidden">
        <div className="w-20 h-28 bg-[#1e1e1e] rounded-md shadow-md border border-[#333333] flex flex-col p-2 overflow-hidden group-hover:scale-105 transition-transform font-mono text-[5.5px] text-emerald-400">
          <div className="text-gray-400 border-b border-gray-700 pb-1 mb-1 font-sans text-[6px]">code.py</div>
          <p><span className="text-blue-400">import</span> os, sys</p>
          <p><span className="text-purple-400">def</span> main():</p>
          <p className="pl-1 text-gray-300">print(<span className="text-amber-300">"DMS AI"</span>)</p>
        </div>
      </div>
    );
  };

  if (documents.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center p-12 bg-[#f0f4f9] rounded-3xl border border-dashed border-[#c4c7c5] text-center my-6 select-none">
        <div className="w-14 h-14 rounded-full bg-[#c2e7ff] flex items-center justify-center text-[#0b57d0] mb-3">
          <UploadCloud className="w-7 h-7" />
        </div>
        <h3 className="text-sm font-semibold text-[#1f1f1f] mb-1">A place for all your files</h3>
        <p className="text-xs text-[#444746] max-w-xs">
          Use the "+ New" button to upload documents or create folders.
        </p>
      </div>
    );
  }

  const fileRows = documents.map((d) => ({
    id: d.id,
    title: d.title,
    reason: `Created • ${new Date(d.created_at).toLocaleDateString("en-US", { month: "short", day: "numeric" })}`,
    owner: "me",
    ownerInitial: "me",
    ownerBg: "#ff6d00",
    location: d.folder_id ? "in Subfolder" : "My Drive",
    downloadUrl: d.download_url,
    raw: d,
  }));

  return (
    <div className="select-none">
      <div className="flex items-center justify-between mb-3">
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="flex items-center gap-2 text-sm font-medium text-[#1f1f1f] hover:text-[#0b57d0] transition-colors"
        >
          <ChevronDown className={`w-4 h-4 transition-transform ${collapsed ? "-rotate-90" : ""}`} />
          <span>Files ({documents.length})</span>
        </button>

        <div className="flex items-center gap-1 bg-[#edf2fc] p-1 rounded-full border border-[#e1e3e1]">
          <button
            onClick={() => setViewMode("list")}
            className={`p-1.5 rounded-full transition-all ${
              viewMode === "list" ? "bg-white text-[#0b57d0] shadow-sm font-bold" : "text-[#444746] hover:bg-white"
            }`}
            title="List view"
          >
            <List className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={() => setViewMode("grid")}
            className={`p-1.5 rounded-full transition-all ${
              viewMode === "grid" ? "bg-white text-[#0b57d0] shadow-sm font-bold" : "text-[#444746] hover:bg-white"
            }`}
            title="Grid view"
          >
            <LayoutGrid className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {!collapsed && (
        <div>
          {viewMode === "list" ? (
            <div className="w-full overflow-x-auto">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="border-b border-[#e1e3e1] text-[#444746] font-medium">
                    <th className="py-2.5 px-3 font-medium">Name</th>
                    <th className="py-2.5 px-3 font-medium">Date added</th>
                    <th className="py-2.5 px-3 font-medium">Owner</th>
                    <th className="py-2.5 px-3 font-medium">Location</th>
                    <th className="py-2.5 px-3 text-right font-medium">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#f0f4f9]">
                  {fileRows.map((row) => {
                    const isSelected = selectedDocIds.has(row.id) || selectedDocId === row.id;
                    return (
                      <tr
                        key={row.id}
                        onClick={(e) => onSelectDoc(row.raw, e.ctrlKey || e.metaKey || e.shiftKey)}
                        onDoubleClick={() => {
                          if (onPreviewDoc) onPreviewDoc(row.raw);
                        }}
                        onContextMenu={(e) => {
                          if (onContextMenu) onContextMenu(e, row.raw);
                        }}
                        className={`group transition-colors cursor-pointer select-none ${
                          isSelected ? "bg-[#c2e7ff] text-[#001d35] font-semibold" : "hover:bg-[#edf2fc]"
                        }`}
                      >
                        <td className="py-3 px-3">
                          <div className="flex items-center gap-3 min-w-[240px]">
                            {getFileIcon(row.title, row.downloadUrl)}
                            <span className="font-semibold text-[#1f1f1f] truncate max-w-xs" title={row.title}>
                              {row.title}
                            </span>
                          </div>
                        </td>
                        <td className="py-3 px-3 text-[#444746] whitespace-nowrap">{row.reason}</td>
                        <td className="py-3 px-3 whitespace-nowrap">
                          <span className="text-[#444746] font-medium">me</span>
                        </td>
                        <td className="py-3 px-3 text-[#444746] whitespace-nowrap">
                          <div className="flex items-center gap-1.5">
                            <span className="text-[#5f6368]">📁</span>
                            <span>{row.location}</span>
                          </div>
                        </td>
                        <td className="py-3 px-3 text-right relative">
                          <div className="flex items-center justify-end gap-1">
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                onToggleStar(row.raw);
                              }}
                              className="p-1.5 rounded-full text-[#444746] hover:bg-[#d3d7dc] transition-colors"
                              title={row.raw.is_starred ? "Unstar" : "Star"}
                            >
                              <Star
                                className={`w-4 h-4 ${
                                  row.raw.is_starred ? "text-amber-500 fill-amber-500" : "text-[#444746]"
                                }`}
                              />
                            </button>
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                setActiveMenuId(activeMenuId === row.id ? null : row.id);
                              }}
                              className="p-1.5 rounded-full text-[#444746] hover:bg-[#d3d7dc] transition-colors"
                              title="More options"
                            >
                              <MoreVertical className="w-4 h-4" />
                            </button>
                          </div>
                          {activeMenuId === row.id && (
                            <>
                              <div
                                className="fixed inset-0 z-10"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  setActiveMenuId(null);
                                }}
                              />
                              <div className="absolute right-3 top-10 w-44 bg-white border border-[#e1e3e1] rounded-2xl shadow-xl z-20 py-1.5 text-left animate-fadeIn">
                                {onPreviewDoc && (
                                  <button
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      setActiveMenuId(null);
                                      onPreviewDoc(row.raw);
                                    }}
                                    className="w-full flex items-center gap-2.5 px-3 py-2 text-xs text-[#1f1f1f] hover:bg-[#f0f4f9] font-medium"
                                  >
                                    <Eye className="w-3.5 h-3.5 text-[#0b57d0]" />
                                    <span>Preview</span>
                                  </button>
                                )}
                                {row.downloadUrl && (
                                  <a
                                    href={row.downloadUrl}
                                    download
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      setActiveMenuId(null);
                                    }}
                                    className="w-full flex items-center gap-2.5 px-3 py-2 text-xs text-[#1f1f1f] hover:bg-[#f0f4f9] font-medium"
                                  >
                                    <Download className="w-3.5 h-3.5 text-[#00639b]" />
                                    <span>Download</span>
                                  </a>
                                )}
                                <button
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    setActiveMenuId(null);
                                    onRename(row.raw);
                                  }}
                                  className="w-full flex items-center gap-2.5 px-3 py-2 text-xs text-[#1f1f1f] hover:bg-[#f0f4f9] font-medium"
                                >
                                  <Edit2 className="w-3.5 h-3.5 text-[#444746]" />
                                  <span>Rename</span>
                                </button>
                                <button
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    setActiveMenuId(null);
                                    onMove(row.raw);
                                  }}
                                  className="w-full flex items-center gap-2.5 px-3 py-2 text-xs text-[#1f1f1f] hover:bg-[#f0f4f9] font-medium"
                                >
                                  <FolderInput className="w-3.5 h-3.5 text-[#444746]" />
                                  <span>Move</span>
                                </button>
                                <button
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    setActiveMenuId(null);
                                    onToggleStar(row.raw);
                                  }}
                                  className="w-full flex items-center gap-2.5 px-3 py-2 text-xs text-[#1f1f1f] hover:bg-[#f0f4f9] font-medium"
                                >
                                  <Star className="w-3.5 h-3.5 text-amber-500" />
                                  <span>{row.raw.is_starred ? "Unstar" : "Star"}</span>
                                </button>
                                <div className="h-px bg-[#e1e3e1] my-1" />
                                <button
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    setActiveMenuId(null);
                                    onTrash(row.raw);
                                  }}
                                  className="w-full flex items-center gap-2.5 px-3 py-2 text-xs text-red-600 hover:bg-red-50 font-medium"
                                >
                                  <Trash2 className="w-3.5 h-3.5" />
                                  <span>Move to Bin</span>
                                </button>
                              </div>
                            </>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
              {fileRows.map((row) => {
                const isSelected = selectedDocIds.has(row.id) || selectedDocId === row.id;
                return (
                  <div
                    key={row.id}
                    onClick={(e) => onSelectDoc(row.raw, e.ctrlKey || e.metaKey || e.shiftKey)}
                    onDoubleClick={() => {
                      if (onPreviewDoc) onPreviewDoc(row.raw);
                    }}
                    onContextMenu={(e) => {
                      if (onContextMenu) onContextMenu(e, row.raw);
                    }}
                    className={`group rounded-2xl border transition-all cursor-pointer flex flex-col overflow-hidden select-none ${
                      isSelected
                        ? "bg-[#c2e7ff]/40 border-[#0b57d0] shadow-md font-semibold ring-1 ring-[#0b57d0]"
                        : "bg-white border-[#e1e3e1] hover:shadow-md"
                    }`}
                  >
                    <div className="relative">
                      {renderGridThumbnail(row)}
                      <div className="absolute top-2 right-2 flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity bg-white/90 backdrop-blur-md rounded-full p-1 shadow-xs border border-[#e1e3e1]">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            if (onPreviewDoc) onPreviewDoc(row.raw);
                          }}
                          className="p-1 rounded-full text-[#444746] hover:text-[#0b57d0] hover:bg-[#edf2fc] transition-all"
                          title="Preview"
                        >
                          <Eye className="w-3.5 h-3.5" />
                        </button>
                        {row.downloadUrl && (
                          <a
                            href={row.downloadUrl}
                            download
                            onClick={(e) => e.stopPropagation()}
                            className="p-1 rounded-full text-[#444746] hover:text-[#00639b] hover:bg-[#edf2fc] transition-all"
                            title="Download"
                          >
                            <Download className="w-3.5 h-3.5" />
                          </a>
                        )}
                      </div>
                    </div>
                    <div className="p-3.5 flex items-start gap-3 bg-white">
                      <div className="flex-shrink-0 mt-0.5">{getFileIcon(row.title, row.downloadUrl)}</div>
                      <div className="min-w-0 flex-1">
                        <h4 className="text-xs font-semibold text-[#1f1f1f] truncate mb-0.5" title={row.title}>
                          {row.title}
                        </h4>
                        <div className="flex items-center justify-between text-[11px] text-[#444746]">
                          <span>{row.reason}</span>
                          <span className="text-[10px] text-[#5f6368] font-medium">{row.location}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
