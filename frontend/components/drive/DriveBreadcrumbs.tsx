import React from "react";
import { ChevronRight, HardDrive } from "lucide-react";
import type { Folder } from "@/types";

interface BreadcrumbItem {
  id: string | null;
  name: string;
}

interface DriveBreadcrumbsProps {
  currentView: string;
  currentFolder: Folder | null;
  folderPath: Folder[]; // Array of parent folders up to current folder
  onNavigateRoot: () => void;
  onNavigateFolder: (folderId: string) => void;
}

export function DriveBreadcrumbs({
  currentView,
  currentFolder,
  folderPath,
  onNavigateRoot,
  onNavigateFolder,
}: DriveBreadcrumbsProps) {
  const getViewTitle = () => {
    switch (currentView) {
      case "home":
        return "Home";
      case "recent":
        return "Recent";
      case "starred":
        return "Starred";
      case "trash":
        return "Bin";
      case "shared":
        return "Shared with me";
      default:
        return "My Drive";
    }
  };

  return (
    <nav className="flex items-center gap-1.5 text-sm text-[#444746] select-none my-1 overflow-x-auto">
      {/* Root Node */}
      <button
        onClick={onNavigateRoot}
        className="flex items-center gap-2 hover:bg-[#edf2fc] hover:text-[#0b57d0] px-2 py-1 rounded-lg transition-colors font-semibold text-[#1f1f1f]"
      >
        {currentView !== "home" && <HardDrive className="w-4 h-4 text-[#0b57d0]" />}
        <span>{getViewTitle()}</span>
      </button>

      {/* Path Folders */}
      {currentView === "my-drive" && (
        <>
          {folderPath.map((f) => (
            <React.Fragment key={f.id}>
              <ChevronRight className="w-4 h-4 text-[#8e918f] flex-shrink-0" />
              <button
                onClick={() => onNavigateFolder(f.id)}
                className={`hover:bg-[#edf2fc] hover:text-[#0b57d0] px-2 py-1 rounded-lg transition-colors truncate max-w-[160px] ${
                  currentFolder?.id === f.id ? "font-bold text-[#1f1f1f]" : "font-medium"
                }`}
                title={f.name}
              >
                {f.name}
              </button>
            </React.Fragment>
          ))}

          {currentFolder && !folderPath.some((f) => f.id === currentFolder.id) && (
            <>
              <ChevronRight className="w-4 h-4 text-[#8e918f] flex-shrink-0" />
              <span className="font-bold text-[#1f1f1f] px-2 py-1 truncate max-w-[180px]">
                {currentFolder.name}
              </span>
            </>
          )}
        </>
      )}
    </nav>
  );
}
