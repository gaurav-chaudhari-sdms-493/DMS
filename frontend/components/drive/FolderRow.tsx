"use client";
import React, { useState } from "react";
import { Folder as FolderIcon, MoreVertical, Star, Trash2, Edit2, FolderInput, RotateCcw } from "lucide-react";
import type { Folder } from "@/types";

interface FolderRowProps {
  folder: Folder;
  onOpen: (folder: Folder) => void;
  onSelect: (folder: Folder) => void;
  isSelected: boolean;
  onToggleStar: (folder: Folder) => void;
  onToggleTrash: (folder: Folder) => void;
  onRename: (folder: Folder) => void;
  onMove: (folder: Folder) => void;
  onDeletePermanent?: (folder: Folder) => void;
}

export function FolderRow({
  folder,
  onOpen,
  onSelect,
  isSelected,
  onToggleStar,
  onToggleTrash,
  onRename,
  onMove,
  onDeletePermanent,
}: FolderRowProps) {
  const [showMenu, setShowMenu] = useState(false);

  return (
    <div
      onClick={() => onSelect(folder)}
      onDoubleClick={() => onOpen(folder)}
      className={`group flex items-center justify-between px-4 py-3 border-b border-borderDark/40 transition-colors cursor-pointer select-none ${
        isSelected
          ? "bg-primary/15 text-textMain"
          : "hover:bg-surface/70 text-textMuted hover:text-textMain"
      }`}
    >
      <div className="flex items-center gap-3 min-w-0 flex-1">
        <FolderIcon
          className="w-5 h-5 flex-shrink-0"
          style={{ color: folder.color || "#1a73e8", fill: `${folder.color || "#1a73e8"}30` }}
        />
        <span className="text-sm font-medium text-textMain truncate">
          {folder.name}
        </span>
      </div>

      <div className="w-36 text-xs text-textMuted hidden sm:block">Folder</div>

      <div className="w-36 text-xs text-textMuted hidden md:block">
        {new Date(folder.created_at).toLocaleDateString()}
      </div>

      <div className="flex items-center gap-2 relative">
        {folder.is_starred && (
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
                  onOpen(folder);
                }}
                className="flex items-center gap-2.5 w-full px-3 py-2 rounded-xl hover:bg-surface text-textMain font-medium"
              >
                <FolderIcon className="w-4 h-4 text-primary" />
                <span>Open</span>
              </button>

              <button
                onClick={(e) => {
                  e.stopPropagation();
                  setShowMenu(false);
                  onToggleStar(folder);
                }}
                className="flex items-center gap-2.5 w-full px-3 py-2 rounded-xl hover:bg-surface text-textMain font-medium"
              >
                <Star className={`w-4 h-4 ${folder.is_starred ? "text-amber-400 fill-amber-400" : "text-textMuted"}`} />
                <span>{folder.is_starred ? "Remove star" : "Add star"}</span>
              </button>

              <button
                onClick={(e) => {
                  e.stopPropagation();
                  setShowMenu(false);
                  onRename(folder);
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
                  onMove(folder);
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
                  onToggleTrash(folder);
                }}
                className="flex items-center gap-2.5 w-full px-3 py-2 rounded-xl hover:bg-red-500/10 text-red-400 font-medium"
              >
                {folder.is_trashed ? (
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

              {folder.is_trashed && onDeletePermanent && (
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    setShowMenu(false);
                    onDeletePermanent(folder);
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
