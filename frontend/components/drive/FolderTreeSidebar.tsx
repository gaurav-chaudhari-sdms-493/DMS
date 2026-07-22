"use client";
import React, { useState } from "react";
import { ChevronRight, ChevronDown, Folder as FolderIcon } from "lucide-react";
import type { FolderTreeNode } from "@/types";

interface FolderTreeItemProps {
  node: FolderTreeNode;
  activeFolderId: string | null;
  onSelectFolder: (folderId: string) => void;
  depth?: number;
}

function FolderTreeItem({
  node,
  activeFolderId,
  onSelectFolder,
  depth = 0,
}: FolderTreeItemProps) {
  const [expanded, setExpanded] = useState(false);
  const childrenNodes = node.children || node.subfolders || [];
  const hasChildren = childrenNodes.length > 0;
  const isSelected = activeFolderId === node.id;

  return (
    <div className="select-none">
      <div
        className={`flex items-center gap-1 py-1 px-2 rounded-xl cursor-pointer transition-colors ${
          isSelected
            ? "bg-[#c2e7ff] text-[#001d35] font-bold"
            : "hover:bg-[#edf2fc] text-[#444746] hover:text-[#1f1f1f]"
        }`}
        style={{ paddingLeft: `${depth * 14 + 8}px` }}
        onClick={(e) => {
          e.stopPropagation();
          onSelectFolder(node.id);
        }}
      >
        {hasChildren ? (
          <button
            onClick={(e) => {
              e.stopPropagation();
              setExpanded(!expanded);
            }}
            className="p-1 rounded-full hover:bg-black/10 transition-transform"
          >
            <ChevronRight
              className={`w-3.5 h-3.5 transition-transform ${expanded ? "rotate-90" : ""}`}
            />
          </button>
        ) : (
          <span className="w-5" />
        )}

        <FolderIcon className="w-4 h-4 text-[#5f6368] fill-[#fbbc04] flex-shrink-0" />
        <span className="text-xs truncate">{node.name}</span>
      </div>

      {expanded && hasChildren && (
        <div className="flex flex-col">
          {childrenNodes.map((child) => (
            <FolderTreeItem
              key={child.id}
              node={child}
              activeFolderId={activeFolderId}
              onSelectFolder={onSelectFolder}
              depth={depth + 1}
            />
          ))}
        </div>
      )}
    </div>
  );
}

interface FolderTreeSidebarProps {
  tree: FolderTreeNode[];
  activeFolderId: string | null;
  onSelectFolder: (folderId: string) => void;
}

export function FolderTreeSidebar({
  tree,
  activeFolderId,
  onSelectFolder,
}: FolderTreeSidebarProps) {
  if (!tree || tree.length === 0) return null;

  return (
    <div className="flex flex-col gap-0.5 mt-1 ml-4 border-l border-[#e1e3e1] pl-1">
      {tree.map((node) => (
        <FolderTreeItem
          key={node.id}
          node={node}
          activeFolderId={activeFolderId}
          onSelectFolder={onSelectFolder}
        />
      ))}
    </div>
  );
}
