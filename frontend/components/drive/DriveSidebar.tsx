"use client";
import React, { useState } from "react";
import {
  Plus,
  Home,
  ChevronRight,
  HardDrive,
  Users,
  Clock,
  Star,
  Trash2,
  FolderPlus,
  Upload,
  Sparkles,
} from "lucide-react";
import type { DriveStats, FolderTreeNode } from "@/types";
import { FolderTreeSidebar } from "./FolderTreeSidebar";

interface DriveSidebarProps {
  currentView: "home" | "my-drive" | "recent" | "starred" | "trash" | "shared" | "chat";
  onSelectView: (view: "home" | "my-drive" | "recent" | "starred" | "trash" | "shared" | "chat") => void;
  onOpenNewFolderModal: () => void;
  onTriggerFileUpload: () => void;
  stats: DriveStats | null;
  folderTree?: FolderTreeNode[];
  activeFolderId?: string | null;
  onSelectFolder?: (folderId: string) => void;
}

export function DriveSidebar({
  currentView,
  onSelectView,
  onOpenNewFolderModal,
  onTriggerFileUpload,
  stats,
  folderTree = [],
  activeFolderId = null,
  onSelectFolder,
}: DriveSidebarProps) {
  const [showNewMenu, setShowNewMenu] = useState(false);
  const [expandDriveTree, setExpandDriveTree] = useState(true);

  const formatSize = (bytes: number) => {
    if (!bytes) return "0 B";
    const k = 1024;
    const sizes = ["B", "KB", "MB", "GB", "TB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
  };

  const usedBytes = stats?.total_size_bytes || 0;

  return (
    <aside className="w-60 flex-shrink-0 flex flex-col justify-between py-2 pr-2 select-none bg-gdriveBg overflow-y-auto">
      <div>
        {/* "+ New" Action Button */}
        <div className="relative mb-4 px-3">
          <button
            onClick={() => setShowNewMenu(!showNewMenu)}
            className="flex items-center gap-3 px-4 py-3 bg-white hover:bg-[#f1f3f4] text-[#1f1f1f] rounded-2xl shadow-md border border-[#c4c7c5] hover:shadow-lg transition-all duration-200 group"
          >
            <Plus className="w-6 h-6 text-[#1f1f1f] stroke-[2.5]" />
            <span className="font-semibold text-sm pr-2">New</span>
          </button>

          {showNewMenu && (
            <>
              <div className="fixed inset-0 z-40" onClick={() => setShowNewMenu(false)} />
              <div className="absolute left-3 top-14 z-50 w-56 bg-white rounded-2xl shadow-xl border border-[#e1e3e1] p-2 animate-fadeIn text-sm text-[#1f1f1f]">
                <button
                  onClick={() => {
                    setShowNewMenu(false);
                    onOpenNewFolderModal();
                  }}
                  className="flex items-center gap-3 w-full px-3 py-2.5 rounded-xl hover:bg-[#f0f4f9] font-medium text-left"
                >
                  <FolderPlus className="w-4 h-4 text-[#0b57d0]" />
                  <span>New folder</span>
                </button>

                <div className="h-px bg-[#e1e3e1] my-1" />

                <button
                  onClick={() => {
                    setShowNewMenu(false);
                    onTriggerFileUpload();
                  }}
                  className="flex items-center gap-3 w-full px-3 py-2.5 rounded-xl hover:bg-[#f0f4f9] font-medium text-left"
                >
                  <Upload className="w-4 h-4 text-[#00639b]" />
                  <span>File upload</span>
                </button>
              </div>
            </>
          )}
        </div>

        {/* Navigation Section Items */}
        <nav className="space-y-0.5">
          {/* Home */}
          <button
            onClick={() => onSelectView("home")}
            className={`flex items-center gap-4 w-full px-4 py-2 rounded-r-full text-sm font-medium transition-all ${currentView === "home"
              ? "bg-[#c2e7ff] text-[#001d35] font-bold"
              : "text-[#444746] hover:bg-[#edf2fc] hover:text-[#1f1f1f]"
              }`}
          >
            <Home className="w-4 h-4" />
            <span>Home</span>
          </button>

          {/* AI Chat */}
          <button
            onClick={() => onSelectView("chat")}
            className={`flex items-center gap-4 w-full px-4 py-2 rounded-r-full text-sm font-medium transition-all ${currentView === "chat"
              ? "bg-[#c2e7ff] text-[#001d35] font-bold"
              : "text-[#444746] hover:bg-[#edf2fc] hover:text-[#1f1f1f]"
              }`}
          >
            <Sparkles className="w-4 h-4 text-[#0b57d0]" />
            <span>AI Chat</span>
          </button>



          {/* My Drive Node */}
          <div>
            <div
              onClick={() => onSelectView("my-drive")}
              className={`flex items-center justify-between w-full px-4 py-2 rounded-r-full text-sm font-medium cursor-pointer transition-all ${currentView === "my-drive" && !activeFolderId
                ? "bg-[#c2e7ff] text-[#001d35] font-bold"
                : "text-[#444746] hover:bg-[#edf2fc] hover:text-[#1f1f1f]"
                }`}
            >
              <div className="flex items-center gap-4">
                <HardDrive className="w-4 h-4" />
                <span>My Drive</span>
              </div>
              {folderTree.length > 0 && (
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    setExpandDriveTree(!expandDriveTree);
                  }}
                  className="p-1 rounded-full hover:bg-black/10 transition-transform"
                >
                  <ChevronRight
                    className={`w-3.5 h-3.5 transition-transform ${expandDriveTree ? "rotate-90" : ""}`}
                  />
                </button>
              )}
            </div>

            {/* Subfolder Tree */}
            {expandDriveTree && folderTree.length > 0 && onSelectFolder && (
              <FolderTreeSidebar
                tree={folderTree}
                activeFolderId={activeFolderId}
                onSelectFolder={onSelectFolder}
              />
            )}
          </div>

          <div className="h-px bg-[#e1e3e1] my-2 mx-4" />

          {/* Shared with me */}
          <button
            onClick={() => onSelectView("shared")}
            className={`flex items-center gap-4 w-full px-4 py-2 rounded-r-full text-sm font-medium transition-all ${currentView === "shared"
              ? "bg-[#c2e7ff] text-[#001d35] font-bold"
              : "text-[#444746] hover:bg-[#edf2fc] hover:text-[#1f1f1f]"
              }`}
          >
            <Users className="w-4 h-4" />
            <span>Shared with me</span>
          </button>

          {/* Recent */}
          <button
            onClick={() => onSelectView("recent")}
            className={`flex items-center gap-4 w-full px-4 py-2 rounded-r-full text-sm font-medium transition-all ${currentView === "recent"
              ? "bg-[#c2e7ff] text-[#001d35] font-bold"
              : "text-[#444746] hover:bg-[#edf2fc] hover:text-[#1f1f1f]"
              }`}
          >
            <Clock className="w-4 h-4" />
            <span>Recent</span>
          </button>

          {/* Starred */}
          <button
            onClick={() => onSelectView("starred")}
            className={`flex items-center gap-4 w-full px-4 py-2 rounded-r-full text-sm font-medium transition-all ${currentView === "starred"
              ? "bg-[#c2e7ff] text-[#001d35] font-bold"
              : "text-[#444746] hover:bg-[#edf2fc] hover:text-[#1f1f1f]"
              }`}
          >
            <Star className="w-4 h-4" />
            <span>Starred</span>
          </button>

          {/* Bin */}
          <button
            onClick={() => onSelectView("trash")}
            className={`flex items-center gap-4 w-full px-4 py-2 rounded-r-full text-sm font-medium transition-all ${currentView === "trash"
              ? "bg-[#c2e7ff] text-[#001d35] font-bold"
              : "text-[#444746] hover:bg-[#edf2fc] hover:text-[#1f1f1f]"
              }`}
          >
            <Trash2 className="w-4 h-4" />
            <span>Bin</span>
          </button>
        </nav>
      </div>

      {/* Bottom Storage Meter */}
      <div className="px-4 py-3 border-t border-[#e1e3e1]/60">
        <div className="text-xs font-semibold text-[#1f1f1f] mb-1">Storage</div>
        <div className="text-xs text-[#444746]">
          {formatSize(usedBytes)} used
        </div>
      </div>
    </aside>
  );
}
