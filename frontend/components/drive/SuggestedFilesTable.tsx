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
  onSelectDoc: (doc: DocumentListItem) => void;
  onPreviewDoc?: (doc: DocumentListItem) => void;
  selectedDocId?: string | null;
  onToggleStar: (doc: DocumentListItem) => void;
  onRename: (doc: DocumentListItem) => void;
  onMove: (doc: DocumentListItem) => void;
  onTrash: (doc: DocumentListItem) => void;
}

export function SuggestedFilesTable({
  documents,
  onSelectDoc,
  onPreviewDoc,
  selectedDocId,
  onToggleStar,
  onRename,
  onMove,
  onTrash,
}: SuggestedFilesTableProps) {
  const [collapsed, setCollapsed] = useState(false);
  const [viewMode, setViewMode] = useState<"list" | "grid">("list");
  const [activeMenuId, setActiveMenuId] = useState<string | null>(null);

  const getFileIcon = (title: string, type?: string) => {
    const ext = title.split(".").pop()?.toLowerCase() || type || "";
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
      {/* Header Controls */}
      <div className="flex items-center justify-between mb-3">
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="flex items-center gap-2 text-sm font-medium text-[#1f1f1f] hover:text-[#0b57d0] transition-colors"
        >
          <ChevronDown className={`w-4 h-4 transition-transform ${collapsed ? "-rotate-90" : ""}`} />
          <span>Files ({documents.length})</span>
        </button>

        {/* View Mode Switcher Pills */}
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
        <div className="w-full">
          {viewMode === "list" ? (
            /* Table View */
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
                  {fileRows.map((row) => (
                    <tr
                      key={row.id}
                      onClick={() => onSelectDoc(row.raw)}
                      className={`group hover:bg-[#edf2fc] transition-colors cursor-pointer ${
                        selectedDocId === row.id ? "bg-[#c2e7ff]/40 font-semibold" : ""
                      }`}
                    >
                      {/* Name Column */}
                      <td className="py-3 px-3">
                        <div className="flex items-center gap-3 min-w-[240px]">
                          {getFileIcon(row.title)}
                          <span className="font-semibold text-[#1f1f1f] truncate max-w-xs" title={row.title}>
                            {row.title}
                          </span>
                        </div>
                      </td>

                      {/* Reason / Date Column */}
                      <td className="py-3 px-3 text-[#444746] whitespace-nowrap">{row.reason}</td>

                      {/* Owner Column */}
                      <td className="py-3 px-3 whitespace-nowrap">
                        <span className="text-[#444746] font-medium">me</span>
                      </td>

                      {/* Location Column */}
                      <td className="py-3 px-3 text-[#444746] whitespace-nowrap">
                        <div className="flex items-center gap-1.5">
                          <span className="text-[#5f6368]">📁</span>
                          <span>{row.location}</span>
                        </div>
                      </td>

                      {/* Actions: Preview button to the left side of Download button on hover */}
                      <td className="py-3 px-3 text-right relative">
                        <div className="flex items-center justify-end gap-1">
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              if (onPreviewDoc) onPreviewDoc(row.raw);
                              else onSelectDoc(row.raw);
                            }}
                            className="opacity-0 group-hover:opacity-100 p-1.5 rounded-full text-[#444746] hover:text-[#0b57d0] hover:bg-[#d3d7dc] transition-all"
                            title="Preview"
                          >
                            <Eye className="w-4 h-4" />
                          </button>

                          {row.downloadUrl && (
                            <a
                              href={row.downloadUrl}
                              download
                              onClick={(e) => e.stopPropagation()}
                              className="opacity-0 group-hover:opacity-100 p-1.5 rounded-full text-[#444746] hover:text-[#00639b] hover:bg-[#d3d7dc] transition-all"
                              title="Download"
                            >
                              <Download className="w-4 h-4" />
                            </a>
                          )}

                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              setActiveMenuId(activeMenuId === row.id ? null : row.id);
                            }}
                            className="opacity-0 group-hover:opacity-100 p-1.5 rounded-full text-[#444746] hover:bg-[#d3d7dc] transition-all"
                            title="More options"
                          >
                            <MoreVertical className="w-4 h-4" />
                          </button>
                        </div>

                        {activeMenuId === row.id && (
                          <>
                            <div className="fixed inset-0 z-40" onClick={() => setActiveMenuId(null)} />
                            <div className="absolute right-2 top-8 z-50 w-44 bg-white rounded-xl shadow-xl border border-[#e1e3e1] p-1.5 text-xs text-[#1f1f1f]">
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  setActiveMenuId(null);
                                  if (onPreviewDoc) onPreviewDoc(row.raw);
                                  else onSelectDoc(row.raw);
                                }}
                                className="flex items-center gap-2 w-full px-3 py-2 rounded-lg hover:bg-[#f0f4f9]"
                              >
                                <Eye className="w-4 h-4 text-[#0b57d0]" />
                                <span>Preview</span>
                              </button>

                              {row.downloadUrl && (
                                <a
                                  href={row.downloadUrl}
                                  download
                                  onClick={(e) => e.stopPropagation()}
                                  className="flex items-center gap-2 w-full px-3 py-2 rounded-lg hover:bg-[#f0f4f9]"
                                >
                                  <Download className="w-4 h-4 text-[#00639b]" />
                                  <span>Download</span>
                                </a>
                              )}

                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  setActiveMenuId(null);
                                  onToggleStar(row.raw);
                                }}
                                className="flex items-center gap-2 w-full px-3 py-2 rounded-lg hover:bg-[#f0f4f9]"
                              >
                                <Star className="w-4 h-4 text-amber-500" />
                                <span>Star</span>
                              </button>

                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  setActiveMenuId(null);
                                  onRename(row.raw);
                                }}
                                className="flex items-center gap-2 w-full px-3 py-2 rounded-lg hover:bg-[#f0f4f9]"
                              >
                                <Edit2 className="w-4 h-4" />
                                <span>Rename</span>
                              </button>

                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  setActiveMenuId(null);
                                  onMove(row.raw);
                                }}
                                className="flex items-center gap-2 w-full px-3 py-2 rounded-lg hover:bg-[#f0f4f9]"
                              >
                                <FolderInput className="w-4 h-4" />
                                <span>Move</span>
                              </button>

                              <div className="h-px bg-[#e1e3e1] my-1" />

                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  setActiveMenuId(null);
                                  onTrash(row.raw);
                                }}
                                className="flex items-center gap-2 w-full px-3 py-2 rounded-lg hover:bg-red-50 text-red-600"
                              >
                                <Trash2 className="w-4 h-4" />
                                <span>Trash</span>
                              </button>
                            </div>
                          </>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            /* Grid View */
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
              {fileRows.map((row) => (
                <div
                  key={row.id}
                  onClick={() => onSelectDoc(row.raw)}
                  className="group p-4 rounded-2xl bg-white border border-[#e1e3e1] hover:shadow-md transition-all cursor-pointer flex flex-col justify-between"
                >
                  <div className="flex items-start justify-between mb-3">
                    {getFileIcon(row.title)}
                    <div className="flex items-center gap-1">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          if (onPreviewDoc) onPreviewDoc(row.raw);
                          else onSelectDoc(row.raw);
                        }}
                        className="opacity-0 group-hover:opacity-100 p-1 rounded-full text-[#444746] hover:text-[#0b57d0] hover:bg-[#edf2fc] transition-all"
                        title="Preview"
                      >
                        <Eye className="w-4 h-4" />
                      </button>
                      {row.downloadUrl && (
                        <a
                          href={row.downloadUrl}
                          download
                          onClick={(e) => e.stopPropagation()}
                          className="opacity-0 group-hover:opacity-100 p-1 rounded-full text-[#444746] hover:text-[#00639b] hover:bg-[#edf2fc] transition-all"
                          title="Download"
                        >
                          <Download className="w-4 h-4" />
                        </a>
                      )}
                      <span className="text-[10px] text-[#444746] font-medium">{row.location}</span>
                    </div>
                  </div>
                  <div>
                    <h4 className="text-xs font-semibold text-[#1f1f1f] truncate mb-1" title={row.title}>
                      {row.title}
                    </h4>
                    <span className="text-[11px] text-[#444746] block">{row.reason}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
