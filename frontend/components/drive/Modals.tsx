"use client";
import React, { useState, useEffect } from "react";
import { X, Folder, Check } from "lucide-react";
import type { FolderTreeNode } from "@/types";
import { api } from "@/lib/api";

interface NewFolderModalProps {
  isOpen: boolean;
  onClose: () => void;
  onCreate: (name: string, color: string) => void;
}

const FOLDER_COLORS = [
  "#1a73e8", // Blue (Google Drive default)
  "#ea4335", // Red
  "#fbbc04", // Yellow
  "#34a853", // Green
  "#a142f4", // Purple
  "#24c1e0", // Cyan
  "#ff6d01", // Orange
  "#5f6368", // Gray
];

export function NewFolderModal({ isOpen, onClose, onCreate }: NewFolderModalProps) {
  const [name, setName] = useState("Untitled folder");
  const [selectedColor, setSelectedColor] = useState("#1a73e8");

  if (!isOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (name.trim()) {
      onCreate(name.trim(), selectedColor);
      setName("Untitled folder");
      onClose();
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-fadeIn">
      <div className="w-full max-w-md glass rounded-2xl border border-borderDark p-6 shadow-2xl space-y-6">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-bold text-textMain">New folder</h3>
          <button onClick={onClose} className="p-1 text-textMuted hover:text-textMain">
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="new-folder-name" className="block text-xs font-semibold text-textMuted mb-2">Folder Name</label>
            <input
              id="new-folder-name"
              type="text"
              // eslint-disable-next-line jsx-a11y/no-autofocus -- WAI-ARIA APG dialog pattern: move focus into a freshly opened dialog's first field, unlike page-load autofocus
              autoFocus
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full px-4 py-2.5 bg-surface rounded-xl border border-borderDark text-textMain text-sm focus:border-primary focus:outline-none"
            />
          </div>

          <div>
            <span id="folder-color-label" className="block text-xs font-semibold text-textMuted mb-2">Folder Color</span>
            <div role="group" aria-labelledby="folder-color-label" className="flex items-center gap-3">
              {FOLDER_COLORS.map((color) => (
                <button
                  key={color}
                  type="button"
                  onClick={() => setSelectedColor(color)}
                  aria-label={`Folder color ${color}`}
                  aria-pressed={selectedColor === color}
                  className="w-7 h-7 rounded-full flex items-center justify-center transition-transform hover:scale-110 shadow-sm"
                  style={{ backgroundColor: color }}
                >
                  {selectedColor === color && <Check className="w-4 h-4 text-white stroke-[3]" />}
                </button>
              ))}
            </div>
          </div>

          <div className="flex items-center justify-end gap-3 pt-4 border-t border-borderDark/40">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm font-semibold text-textMuted hover:text-textMain hover:bg-surface rounded-xl transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-5 py-2 bg-primary hover:bg-primary/90 text-white text-sm font-semibold rounded-xl shadow-md transition-all"
            >
              Create
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

interface RenameModalProps {
  isOpen: boolean;
  currentName: string;
  onClose: () => void;
  onRename: (newName: string) => void;
}

export function RenameModal({ isOpen, currentName, onClose, onRename }: RenameModalProps) {
  const [name, setName] = useState(currentName);

  useEffect(() => {
    setName(currentName);
  }, [currentName]);

  if (!isOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (name.trim()) {
      onRename(name.trim());
      onClose();
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-fadeIn">
      <div className="w-full max-w-md glass rounded-2xl border border-borderDark p-6 shadow-2xl space-y-6">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-bold text-textMain">Rename</h3>
          <button onClick={onClose} className="p-1 text-textMuted hover:text-textMain">
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <input
            type="text"
            aria-label="New name"
            // eslint-disable-next-line jsx-a11y/no-autofocus -- WAI-ARIA APG dialog pattern: move focus into a freshly opened dialog's first field, unlike page-load autofocus
            autoFocus
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-full px-4 py-2.5 bg-surface rounded-xl border border-borderDark text-textMain text-sm focus:border-primary focus:outline-none"
          />

          <div className="flex items-center justify-end gap-3 pt-4 border-t border-borderDark/40">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm font-semibold text-textMuted hover:text-textMain hover:bg-surface rounded-xl transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-5 py-2 bg-primary hover:bg-primary/90 text-white text-sm font-semibold rounded-xl shadow-md transition-all"
            >
              OK
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

interface MoveModalProps {
  isOpen: boolean;
  onClose: () => void;
  onMove: (targetFolderId: string | null) => void;
}

export function MoveModal({ isOpen, onClose, onMove }: MoveModalProps) {
  const [tree, setTree] = useState<FolderTreeNode[]>([]);
  const [selectedTargetId, setSelectedTargetId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (isOpen) {
      setLoading(true);
      api.folders
        .getTree()
        .then((res) => setTree(res))
        .catch((err) => console.error("Failed to fetch folder tree:", err))
        .finally(() => setLoading(false));
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const renderTreeNodes = (nodes: FolderTreeNode[]) => {
    return nodes.map((node) => {
      const childNodes = node.children || node.subfolders || [];
      return (
        <div key={node.id} className="ml-4 space-y-1">
          <button
            onClick={() => setSelectedTargetId(node.id)}
            className={`flex items-center gap-2.5 w-full px-3 py-2 rounded-xl text-xs font-semibold transition-colors ${
              selectedTargetId === node.id ? "bg-primary/20 text-primary border border-primary/40" : "hover:bg-surface text-textMain"
            }`}
          >
            <Folder className="w-4 h-4" style={{ color: node.color || "#1a73e8" }} />
            <span>{node.name}</span>
          </button>
          {childNodes.length > 0 && renderTreeNodes(childNodes)}
        </div>
      );
    });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-fadeIn">
      <div className="w-full max-w-md glass rounded-2xl border border-borderDark p-6 shadow-2xl space-y-6">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-bold text-textMain">Move to...</h3>
          <button onClick={onClose} className="p-1 text-textMuted hover:text-textMain">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="max-h-60 overflow-y-auto space-y-1 pr-1 border border-borderDark/40 rounded-xl p-2 bg-surface/40">
          <button
            onClick={() => setSelectedTargetId(null)}
            className={`flex items-center gap-2.5 w-full px-3 py-2 rounded-xl text-xs font-semibold transition-colors ${
              selectedTargetId === null ? "bg-primary/20 text-primary border border-primary/40" : "hover:bg-surface text-textMain"
            }`}
          >
            <Folder className="w-4 h-4 text-primary" />
            <span>My Drive (Root)</span>
          </button>

          {loading ? (
            <div className="text-center py-4 text-xs text-textMuted">Loading folders...</div>
          ) : (
            renderTreeNodes(tree)
          )}
        </div>

        <div className="flex items-center justify-end gap-3 pt-4 border-t border-borderDark/40">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-sm font-semibold text-textMuted hover:text-textMain hover:bg-surface rounded-xl transition-colors"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={() => {
              onMove(selectedTargetId);
              onClose();
            }}
            className="px-5 py-2 bg-primary hover:bg-primary/90 text-white text-sm font-semibold rounded-xl shadow-md transition-all"
          >
            Move here
          </button>
        </div>
      </div>
    </div>
  );
}
