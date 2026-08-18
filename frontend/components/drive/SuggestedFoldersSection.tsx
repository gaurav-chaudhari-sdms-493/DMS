"use client";
import React, { useState } from "react";
import { ChevronDown, Folder as FolderIcon, MoreVertical, Star, Edit2, FolderInput, Trash2 } from "lucide-react";
import type { Folder } from "@/types";

interface SuggestedFoldersProps {
  folders: Folder[];
  onOpenFolder: (folder: Folder) => void;
  onSelectFolder?: (folder: Folder, isMulti: boolean) => void;
  onContextMenu?: (e: React.MouseEvent, folder: Folder) => void;
  selectedFolderIds?: Set<string>;
  onToggleStar: (folder: Folder) => void;
  onRename: (folder: Folder) => void;
  onMove: (folder: Folder) => void;
  onTrash: (folder: Folder) => void;
}

export function SuggestedFoldersSection({
  folders,
  onOpenFolder,
  onSelectFolder,
  onContextMenu,
  selectedFolderIds = new Set(),
  onToggleStar,
  onRename,
  onMove,
  onTrash,
}: SuggestedFoldersProps) {
  const [collapsed, setCollapsed] = useState(false);
  const [activeMenuId, setActiveMenuId] = useState<string | null>(null);

  if (folders.length === 0) {
    return null;
  }

  const displayFolders = folders.map((f) => ({
    id: f.id,
    name: f.name,
    location: f.parent_id ? "in Subfolder" : "in My Drive",
    color: f.color || "#fbbc04",
    raw: f,
  }));

  return (
    <div className="mb-6 select-none">
      {/* Header */}
      <button
        onClick={() => setCollapsed(!collapsed)}
        className="flex items-center gap-2 text-sm font-medium text-[#1f1f1f] hover:text-[#0b57d0] transition-colors mb-3"
      >
        <ChevronDown className={`w-4 h-4 transition-transform ${collapsed ? "-rotate-90" : ""}`} />
        <span>Folders ({folders.length})</span>
      </button>

      {!collapsed && (
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
          {displayFolders.map((item) => {
            const isSelected = selectedFolderIds.has(item.id);
            return (
              <div
                key={item.id}
                onClick={(e) => {
                  if (onSelectFolder) onSelectFolder(item.raw, e.ctrlKey || e.metaKey || e.shiftKey);
                }}
                onDoubleClick={() => onOpenFolder(item.raw)}
                onContextMenu={(e) => {
                  if (onContextMenu) onContextMenu(e, item.raw);
                }}
                className={`group relative flex items-center justify-between p-3 rounded-2xl transition-all cursor-pointer shadow-xs select-none border ${
                  isSelected
                    ? "bg-[#c2e7ff] border-[#0b57d0] shadow-sm font-semibold"
                    : "bg-[#f0f4f9] hover:bg-[#e1e5ea] border-transparent hover:border-[#c4c7c5]"
                }`}
              >
                <div className="flex items-center gap-2.5 min-w-0 pr-1">
                  <div className="w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0">
                    <FolderIcon className="w-5 h-5 text-[#5f6368] fill-[#fbbc04]" />
                  </div>
                  <div className="min-w-0">
                    <h4 className="text-xs font-semibold text-[#1f1f1f] truncate" title={item.name}>
                      {item.name}
                    </h4>
                    <span className="text-[10px] text-[#444746] truncate block">{item.location}</span>
                  </div>
                </div>

                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    setActiveMenuId(activeMenuId === item.id ? null : item.id);
                  }}
                  className="opacity-0 group-hover:opacity-100 p-1.5 rounded-full text-[#444746] hover:bg-[#d3d7dc] transition-all"
                >
                  <MoreVertical className="w-4 h-4" />
                </button>

                {activeMenuId === item.id && (
                  <>
                    <div className="fixed inset-0 z-40" onClick={() => setActiveMenuId(null)} />
                    <div className="absolute right-2 top-10 z-50 w-44 bg-white rounded-xl shadow-xl border border-[#e1e3e1] p-1.5 text-xs text-[#1f1f1f]">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setActiveMenuId(null);
                          onOpenFolder(item.raw);
                        }}
                        className="flex items-center gap-2 w-full px-3 py-2 rounded-lg hover:bg-[#f0f4f9]"
                      >
                        <FolderIcon className="w-4 h-4 text-[#0b57d0]" />
                        <span>Open</span>
                      </button>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setActiveMenuId(null);
                          onToggleStar(item.raw);
                        }}
                        className="flex items-center gap-2 w-full px-3 py-2 rounded-lg hover:bg-[#f0f4f9]"
                      >
                        <Star className="w-4 h-4 text-amber-500" />
                        <span>{item.raw.is_starred ? "Unstar" : "Star"}</span>
                      </button>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setActiveMenuId(null);
                          onRename(item.raw);
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
                          onMove(item.raw);
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
                          onTrash(item.raw);
                        }}
                        className="flex items-center gap-2 w-full px-3 py-2 rounded-lg hover:bg-red-50 text-red-600"
                      >
                        <Trash2 className="w-4 h-4" />
                        <span>Trash</span>
                      </button>
                    </div>
                  </>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
