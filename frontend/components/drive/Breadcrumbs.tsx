"use client";
import React from "react";
import { ChevronRight, HardDrive } from "lucide-react";
import type { Folder } from "@/types";

interface BreadcrumbItem {
  id: string | null;
  name: string;
}

interface BreadcrumbsProps {
  currentFolder: Folder | null;
  folderPath: Folder[];
  onNavigate: (folderId: string | null) => void;
  viewTitle?: string;
}

export function Breadcrumbs({
  currentFolder,
  folderPath,
  onNavigate,
  viewTitle,
}: BreadcrumbsProps) {
  if (viewTitle) {
    return (
      <div className="flex items-center gap-2 py-2 text-lg font-bold text-textMain tracking-tight">
        <span>{viewTitle}</span>
      </div>
    );
  }

  return (
    <nav className="flex items-center gap-1.5 py-2 text-sm text-textMuted overflow-x-auto select-none no-scrollbar">
      <button
        onClick={() => onNavigate(null)}
        className={`flex items-center gap-2 font-medium hover:text-textMain transition-colors px-2 py-1 rounded-lg hover:bg-surface ${
          !currentFolder ? "text-textMain font-semibold" : ""
        }`}
      >
        <HardDrive className="w-4 h-4 text-primary" />
        <span>My Drive</span>
      </button>

      {folderPath.map((folder) => {
        const isCurrent = currentFolder?.id === folder.id;
        return (
          <React.Fragment key={folder.id}>
            <ChevronRight className="w-4 h-4 text-borderDark flex-shrink-0" />
            <button
              onClick={() => onNavigate(folder.id)}
              className={`font-medium hover:text-textMain transition-colors px-2 py-1 rounded-lg hover:bg-surface truncate max-w-[160px] ${
                isCurrent ? "text-textMain font-semibold bg-surface/50" : ""
              }`}
            >
              {folder.name}
            </button>
          </React.Fragment>
        );
      })}
    </nav>
  );
}
