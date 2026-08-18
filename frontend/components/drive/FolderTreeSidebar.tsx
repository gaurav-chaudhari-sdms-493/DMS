"use client";
import React, { useState, useEffect } from "react";
import { ChevronRight, ChevronDown, Folder as FolderIcon, FileText, FileSpreadsheet, Presentation, Image as ImageIcon, FileCode, Music, Video } from "lucide-react";
import type { FolderTreeNode, DocumentListItem } from "@/types";
import { api } from "@/lib/api";

const getTreeFileIcon = (title: string) => {
  const ext = title.split(".").pop()?.toLowerCase() || "";
  if (["pdf"].includes(ext)) return <FileText className="w-3.5 h-3.5 text-red-500 flex-shrink-0" />;
  if (["docx", "doc"].includes(ext)) return <FileText className="w-3.5 h-3.5 text-blue-500 flex-shrink-0" />;
  if (["xlsx", "xls", "csv"].includes(ext)) return <FileSpreadsheet className="w-3.5 h-3.5 text-emerald-500 flex-shrink-0" />;
  if (["pptx", "ppt"].includes(ext)) return <Presentation className="w-3.5 h-3.5 text-amber-500 flex-shrink-0" />;
  if (["png", "jpg", "jpeg", "webp", "gif", "svg"].includes(ext)) return <ImageIcon className="w-3.5 h-3.5 text-purple-400 flex-shrink-0" />;
  if (["mp3", "wav", "ogg"].includes(ext)) return <Music className="w-3.5 h-3.5 text-emerald-400 flex-shrink-0" />;
  if (["mp4", "webm"].includes(ext)) return <Video className="w-3.5 h-3.5 text-blue-400 flex-shrink-0" />;
  if (["json", "js", "ts", "py", "html", "css"].includes(ext)) return <FileCode className="w-3.5 h-3.5 text-cyan-400 flex-shrink-0" />;
  return <FileText className="w-3.5 h-3.5 text-blue-400 flex-shrink-0" />;
};

interface FolderTreeItemProps {
  node: FolderTreeNode;
  activeFolderId: string | null;
  onSelectFolder: (folderId: string) => void;
  onSelectDoc?: (doc: DocumentListItem) => void;
  onPreviewDoc?: (doc: DocumentListItem) => void;
  depth?: number;
}

function FolderTreeItem({
  node,
  activeFolderId,
  onSelectFolder,
  onSelectDoc,
  onPreviewDoc,
  depth = 0,
}: FolderTreeItemProps) {
  const [expanded, setExpanded] = useState(false);
  const [folderFiles, setFolderFiles] = useState<DocumentListItem[]>([]);
  const childrenNodes = node.children || node.subfolders || [];
  const isSelected = activeFolderId === node.id;

  useEffect(() => {
    if (expanded) {
      api.documents.list({ folder_id: node.id, is_trashed: false })
        .then((docs) => setFolderFiles(docs || []))
        .catch(() => setFolderFiles([]));
    }
  }, [expanded, node.id]);

  const hasContent = childrenNodes.length > 0 || folderFiles.length > 0;

  return (
    <div className="select-none">
      <div
        className={`flex items-center gap-1 py-1 px-2 rounded-xl cursor-pointer transition-colors ${
          isSelected
            ? "bg-[#c2e7ff] text-[#001d35] font-bold"
            : "hover:bg-[#edf2fc] text-[#444746] hover:text-[#1f1f1f]"
        }`}
        style={{ paddingLeft: `${depth * 12 + 6}px` }}
        onClick={(e) => {
          e.stopPropagation();
          onSelectFolder(node.id);
        }}
      >
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

        <FolderIcon className="w-4 h-4 text-[#5f6368] fill-[#fbbc04] flex-shrink-0" />
        <span className="text-xs truncate">{node.name}</span>
      </div>

      {expanded && (
        <div className="flex flex-col">
          {childrenNodes.map((child) => (
            <FolderTreeItem
              key={child.id}
              node={child}
              activeFolderId={activeFolderId}
              onSelectFolder={onSelectFolder}
              onSelectDoc={onSelectDoc}
              onPreviewDoc={onPreviewDoc}
              depth={depth + 1}
            />
          ))}
          {folderFiles.map((file) => (
            <div
              key={file.id}
              className="flex items-center gap-1.5 py-1 px-2 rounded-xl cursor-pointer hover:bg-[#edf2fc] text-[#444746] hover:text-[#1f1f1f] transition-colors"
              style={{ paddingLeft: `${(depth + 1) * 12 + 18}px` }}
              onClick={(e) => {
                e.stopPropagation();
                onSelectFolder(node.id);
                if (onSelectDoc) onSelectDoc(file);
              }}
              onDoubleClick={(e) => {
                e.stopPropagation();
                if (onPreviewDoc) onPreviewDoc(file);
              }}
            >
              {getTreeFileIcon(file.title)}
              <span className="text-[11px] truncate max-w-[120px]" title={file.title}>
                {file.title}
              </span>
            </div>
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
  onSelectDoc?: (doc: DocumentListItem) => void;
  onPreviewDoc?: (doc: DocumentListItem) => void;
}

export function FolderTreeSidebar({
  tree,
  activeFolderId,
  onSelectFolder,
  onSelectDoc,
  onPreviewDoc,
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
          onSelectDoc={onSelectDoc}
          onPreviewDoc={onPreviewDoc}
        />
      ))}
    </div>
  );
}
