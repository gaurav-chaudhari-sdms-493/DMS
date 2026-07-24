"use client";
import React, { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { DriveTopHeader } from "@/components/drive/DriveTopHeader";
import { DriveSidebar } from "@/components/drive/DriveSidebar";
import { DriveBreadcrumbs } from "@/components/drive/DriveBreadcrumbs";
import { SuggestedFoldersSection } from "@/components/drive/SuggestedFoldersSection";
import { SuggestedFilesTable } from "@/components/drive/SuggestedFilesTable";
import { RightDock } from "@/components/drive/RightDock";
import { DriveDetailPanel } from "@/components/drive/DriveDetailPanel";
import { DocumentPreviewModal } from "@/components/drive/DocumentPreviewModal";
import { NewFolderModal, RenameModal, MoveModal } from "@/components/drive/Modals";
import { UploadWidget, UploadItem } from "@/components/drive/UploadWidget";
import { AISummary } from "@/components/search/AISummary";
import { ResultCard } from "@/components/search/ResultCard";
import { PersistentChatPanel } from "@/components/chat/PersistentChatPanel";
import { RightSideChatDrawer } from "@/components/chat/RightSideChatDrawer";
import { ConfirmModal } from "@/components/ui/ConfirmModal";


import { isAuthenticated } from "@/lib/auth";
import { api } from "@/lib/api";
import type { Folder, FolderTreeNode, DocumentListItem, DriveStats, SearchResponse, SearchResult } from "@/types";
import { Info, FolderSearch, Eye, Trash2, RotateCcw, Sparkles, FolderPlus, Upload, FolderUp, UploadCloud } from "lucide-react";



const isUUID = (str: string | null | undefined): boolean => {
  if (!str) return false;
  return /^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$/.test(str);
};

export default function DrivePage() {
  const router = useRouter();

  // Navigation View & Hierarchy State
  const [currentView, setCurrentView] = useState<"home" | "my-drive" | "recent" | "starred" | "trash" | "shared" | "chat">("home");
  const [currentFolderId, setCurrentFolderId] = useState<string | null>(null);
  const [currentFolder, setCurrentFolder] = useState<Folder | null>(null);
  const [folderPath, setFolderPath] = useState<Folder[]>([]);
  const [folderTree, setFolderTree] = useState<FolderTreeNode[]>([]);

  // Data State
  const [folders, setFolders] = useState<Folder[]>([]);
  const [documents, setDocuments] = useState<DocumentListItem[]>([]);
  const [selectedFolder, setSelectedFolder] = useState<Folder | null>(null);
  const [selectedDoc, setSelectedDoc] = useState<DocumentListItem | null>(null);

  // Document Previewer Modal State
  const [previewDoc, setPreviewDoc] = useState<DocumentListItem | null>(null);

  // UI State
  const [showDetailPanel, setShowDetailPanel] = useState(false);
  const [showRightChatDrawer, setShowRightChatDrawer] = useState(false);
  const [loading, setLoading] = useState(false);
  const [driveStats, setDriveStats] = useState<DriveStats | null>(null);

  // Search State
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResponse, setSearchResponse] = useState<SearchResponse | null>(null);
  const [searching, setSearching] = useState(false);

  // Modals State
  const [isNewFolderOpen, setIsNewFolderOpen] = useState(false);
  const [itemToRename, setItemToRename] = useState<{ type: "folder" | "doc"; item: Folder | DocumentListItem } | null>(null);
  const [itemToMove, setItemToMove] = useState<{ type: "folder" | "doc"; item: Folder | DocumentListItem } | null>(null);

  // Custom Modal Dialog State
  const [confirmModalConfig, setConfirmModalConfig] = useState<{
    isOpen: boolean;
    title?: string;
    message: string;
    type?: "danger" | "warning" | "info" | "success";
    confirmText?: string;
    showCancel?: boolean;
    onConfirm: () => void;
  }>({
    isOpen: false,
    message: "",
    onConfirm: () => {},
  });


  // Uploads & Drag-and-Drop State
  const [uploads, setUploads] = useState<UploadItem[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const folderInputRef = useRef<HTMLInputElement | null>(null);

  // Context Menu State
  const [contextMenu, setContextMenu] = useState<{ visible: boolean; x: number; y: number }>({
    visible: false,
    x: 0,
    y: 0,
  });

  const handleContextMenu = (e: React.MouseEvent) => {
    e.preventDefault();
    setContextMenu({
      visible: true,
      x: e.clientX,
      y: e.clientY,
    });
  };

  // Drag & Drop Handlers
  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.dataTransfer.types && Array.from(e.dataTransfer.types).includes("Files")) {
      setIsDragging(true);
    }
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.currentTarget.contains(e.relatedTarget as Node)) return;
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    const droppedFiles = Array.from(e.dataTransfer.files || []);
    if (droppedFiles.length > 0) {
      processFilesForUpload(droppedFiles);
    }
  };



  // Auth Protection
  useEffect(() => {
    if (!isAuthenticated()) {
      router.replace("/login");
    }
  }, [router]);

  // Fetch Folder Tree
  const loadFolderTree = async () => {
    try {
      const tree = await api.folders.getTree();
      setFolderTree(tree);
    } catch (err) {
      console.warn("Folder tree load notice:", err);
    }
  };

  // Load Folder Hierarchy Path
  const updateBreadcrumbPath = async (folderId: string | null) => {
    if (!folderId || !isUUID(folderId)) {
      setFolderPath([]);
      setCurrentFolder(null);
      return;
    }

    try {
      const curr = await api.folders.get(folderId);
      setCurrentFolder(curr);

      const path: Folder[] = [];
      let pId = curr.parent_id;
      while (pId && isUUID(pId)) {
        try {
          const parent = await api.folders.get(pId);
          path.unshift(parent);
          pId = parent.parent_id;
        } catch {
          break;
        }
      }
      setFolderPath(path);
    } catch (err) {
      console.warn("Could not resolve breadcrumb path:", err);
    }
  };

  // Fetch Contents Safely
  const loadContents = async () => {
    setLoading(true);
    try {
      api.documents.getStats().then((s) => setDriveStats(s)).catch(() => {});
      loadFolderTree();

      const validParentId = isUUID(currentFolderId) ? currentFolderId : null;
      updateBreadcrumbPath(validParentId);

      if (currentView === "starred") {
        const [fList, dList] = await Promise.all([
          api.folders.list({ is_starred: true, is_trashed: false }),
          api.documents.list({ is_starred: true, is_trashed: false }),
        ]);
        setFolders(fList);
        setDocuments(dList);
      } else if (currentView === "trash") {
        const [fList, dList] = await Promise.all([
          api.folders.list({ is_trashed: true }),
          api.documents.list({ is_trashed: true }),
        ]);
        setFolders(fList);
        setDocuments(dList);
      } else if (currentView === "home" || currentView === "recent") {
        const dList = await api.documents.list({ include_all: true, is_trashed: false });
        setFolders([]);
        setDocuments(dList);
      } else {
        const [fList, dList] = await Promise.all([
          api.folders.list({ parent_id: validParentId, is_trashed: false }),
          api.documents.list({ folder_id: validParentId, is_trashed: false }),
        ]);
        setFolders(fList);
        setDocuments(dList);
      }
    } catch (err) {
      console.warn("Could not fetch backend drive items:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!searchQuery) {
      loadContents();
    }
  }, [currentView, currentFolderId, searchQuery]);

  // Handlers
  const handleSearch = async (query: string, useAi: boolean) => {
    setSearchQuery(query);
    setSearching(true);
    try {
      const res = await api.search.query(query);
      setSearchResponse(res);
      // AUTO-OPEN RIGHT-SIDE PERSISTENT CHAT JUST IN TIME ON SEARCH
      setShowRightChatDrawer(true);
    } catch (err) {
      console.error("Search failed:", err);
    } finally {
      setSearching(false);
    }
  };


  const handleClearSearch = () => {
    setSearchQuery("");
    setSearchResponse(null);
    loadContents();
  };

  const handleOpenFolder = (folder: Folder) => {
    setCurrentView("my-drive");
    setCurrentFolderId(folder.id);
    setSelectedFolder(folder);
    setSelectedDoc(null);
  };

  const handleSelectFolderId = (folderId: string) => {
    setCurrentView("my-drive");
    setCurrentFolderId(folderId);
    setSelectedDoc(null);
  };

  const handleCreateFolder = async (name: string, color: string) => {
    try {
      const validParentId = isUUID(currentFolderId) ? currentFolderId : null;
      await api.folders.create(name, validParentId, color);
      loadContents();
    } catch (err: any) {
      alert(err.message || "Failed to create folder");
    }
  };

  const handlePerformRename = async (newName: string) => {
    if (!itemToRename) return;
    try {
      if (isUUID(itemToRename.item.id)) {
        if (itemToRename.type === "folder") {
          await api.folders.update(itemToRename.item.id, { name: newName });
        } else {
          await api.documents.update(itemToRename.item.id, { title: newName });
        }
      }
      setItemToRename(null);
      loadContents();
    } catch (err: any) {
      console.warn("Rename ignored for non-persistent item:", err);
    }
  };

  const handlePerformMove = async (targetFolderId: string | null) => {
    if (!itemToMove) return;
    try {
      const validTargetId = isUUID(targetFolderId) ? targetFolderId : null;
      if (isUUID(itemToMove.item.id)) {
        if (itemToMove.type === "folder") {
          await api.folders.update(itemToMove.item.id, { parent_id: validTargetId });
        } else {
          await api.documents.update(itemToMove.item.id, { folder_id: validTargetId });
        }
      }
      setItemToMove(null);
      loadContents();
    } catch (err: any) {
      console.warn("Move ignored for non-persistent item:", err);
    }
  };

  const handleRestoreItem = async (type: "folder" | "doc", id: string) => {
    if (!isUUID(id)) return;
    try {
      if (type === "folder") {
        await api.folders.toggleTrash(id);
      } else {
        await api.documents.toggleTrash(id);
      }
      loadContents();
    } catch (err) {
      console.warn("Restore failed:", err);
    }
  };

  const handlePermanentDelete = async (type: "folder" | "doc", id: string) => {
    if (!isUUID(id)) return;
    if (!confirm("Are you sure you want to permanently delete this item?")) return;
    try {
      if (type === "folder") {
        await api.folders.deletePermanent(id);
      } else {
        await api.documents.deletePermanent(id);
      }
      loadContents();
    } catch (err) {
      console.warn("Permanent delete failed:", err);
    }
  };

  const processFilesForUpload = async (files: File[]) => {
    if (files.length === 0) return;

    const validParentId = isUUID(currentFolderId) ? currentFolderId : null;

    const newUploadItems: UploadItem[] = files.map((f, i) => ({
      id: `${Date.now()}-${i}`,
      name: f.name,
      progress: 10,
      status: "uploading",
    }));

    setUploads((prev) => [...prev, ...newUploadItems]);

    try {
      if (files.length === 1) {
        await api.documents.upload(files[0], validParentId);
      } else {
        await api.documents.uploadBulk(files, validParentId);
      }

      setUploads((prev) =>
        prev.map((u) =>
          newUploadItems.some((n) => n.id === u.id)
            ? { ...u, progress: 100, status: "completed" }
            : u
        )
      );
      loadContents();
    } catch (err: any) {
      setUploads((prev) =>
        prev.map((u) =>
          newUploadItems.some((n) => n.id === u.id)
            ? { ...u, status: "error", errorMsg: err.message || "Upload failed" }
            : u
        )
      );
    }
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    if (files.length > 0) {
      await processFilesForUpload(files);
    }
    if (fileInputRef.current) fileInputRef.current.value = "";
    if (folderInputRef.current) folderInputRef.current.value = "";
  };


  // Preview Document from Search Result
  const handlePreviewSearchResult = (res: SearchResult) => {
    const searchDocItem: DocumentListItem = {
      id: res.document_id,
      title: res.document_name || "Search Result Document",
      status: "indexed",
      created_at: new Date().toISOString(),
      file_size_bytes: 1024,
      is_starred: false,
      is_trashed: false,
      download_url: res.download_url,
    };
    setPreviewDoc(searchDocItem);
  };

  return (
    <div className="flex flex-col h-screen w-screen bg-gdriveBg overflow-hidden select-none">
      {/* Hidden File & Folder Inputs */}
      <input
        type="file"
        multiple
        ref={fileInputRef}
        onChange={handleFileChange}
        className="hidden"
      />
      <input
        type="file"
        multiple
        ref={folderInputRef}
        onChange={handleFileChange}
        className="hidden"
        {...({ webkitdirectory: "", directory: "" } as any)}
      />

      {/* Top Header */}
      <DriveTopHeader
        onSearch={handleSearch}
        searchQuery={searchQuery}
        onClearSearch={handleClearSearch}
        showInfoPanel={showDetailPanel}
        onToggleInfoPanel={() => setShowDetailPanel(!showDetailPanel)}
      />

      {/* Body Area */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Navigation Sidebar with Tree */}
        <DriveSidebar
          currentView={currentView}
          onSelectView={(v) => {
            setSearchQuery("");
            setCurrentView(v);
            setCurrentFolderId(null);
            setSelectedFolder(null);
            setSelectedDoc(null);
          }}
          onOpenNewFolderModal={() => setIsNewFolderOpen(true)}
          onTriggerFileUpload={() => fileInputRef.current?.click()}
          stats={driveStats}
          folderTree={folderTree}
          activeFolderId={currentFolderId}
          onSelectFolder={handleSelectFolderId}
        />

        {/* Center Main Dashboard Canvas */}
        <main
          onContextMenu={handleContextMenu}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          className="flex-1 bg-white rounded-3xl my-2 ml-1 mr-2 p-6 flex flex-col overflow-y-auto border border-[#e1e3e1] shadow-sm relative"
        >
          {/* Drag and Drop Overlay Indicator */}
          {isDragging && (
            <div className="absolute inset-0 bg-[#0b57d0]/10 backdrop-blur-md rounded-3xl border-2 border-dashed border-[#0b57d0] z-40 flex flex-col items-center justify-center p-8 text-center animate-fadeIn pointer-events-none">
              <div className="w-20 h-20 bg-[#0b57d0] text-white rounded-full flex items-center justify-center shadow-xl shadow-[#0b57d0]/30 mb-4 animate-bounce">
                <UploadCloud className="w-10 h-10" />
              </div>
              <h3 className="text-xl font-bold text-[#001d35] mb-1">Drop files here to upload to DMS</h3>
              <p className="text-sm text-[#444746] max-w-md">
                Upload single or multiple documents directly into your current directory folder.
              </p>
            </div>
          )}


          {/* Top Breadcrumb & Canvas Header */}
          <div className="flex items-center justify-between mb-4 border-b border-[#e1e3e1] pb-3">
            <DriveBreadcrumbs
              currentView={currentView}
              currentFolder={currentFolder}
              folderPath={folderPath}
              onNavigateRoot={() => {
                setCurrentView("home");
                setCurrentFolderId(null);
              }}
              onNavigateFolder={handleSelectFolderId}
            />
          </div>

          {/* Active Chat Mode */}
          {currentView === "chat" ? (
            <div className="flex-1 flex overflow-hidden">
              <PersistentChatPanel onPreviewDocument={(doc) => setPreviewDoc(doc)} />
            </div>
          ) : searchQuery ? (
            <div className="flex-1 space-y-6">
              {searching ? (
                <div className="text-center py-12 text-sm text-[#444746] animate-pulse">
                  Searching your Drive with AI RAG...
                </div>
              ) : searchResponse ? (
                <div className="space-y-6">
                  {searchResponse.ai_summary && (
                    <AISummary summary={searchResponse.ai_summary} />
                  )}

                  <div className="flex items-center justify-between border-b border-[#e1e3e1] pb-2">
                    <h3 className="text-base font-semibold text-[#1f1f1f]">Search Results</h3>
                    <div className="flex items-center gap-3">
                      <button
                        onClick={() => setShowRightChatDrawer(!showRightChatDrawer)}
                        className="flex items-center gap-1.5 px-3 py-1.5 bg-[#0b57d0] hover:bg-[#0945a5] text-white rounded-full text-xs font-semibold shadow-sm transition-all"
                      >
                        <Sparkles className="w-3.5 h-3.5" />
                        <span>{showRightChatDrawer ? "Hide AI Assistant" : "AI Persistent Chatbot"}</span>
                      </button>
                      <span className="text-xs text-[#444746]">
                        {searchResponse.results.length} matches ({searchResponse.took_ms}ms)
                      </span>
                    </div>
                  </div>



                  {searchResponse.results.length > 0 ? (
                    <div className="grid grid-cols-1 gap-4">
                      {searchResponse.results.map((res, idx) => (
                        <ResultCard key={`${res.document_id}-${idx}`} result={res} onPreview={handlePreviewSearchResult} />
                      ))}
                    </div>
                  ) : (
                    <div className="text-center py-16 bg-[#f8f9fa] rounded-2xl border border-[#e1e3e1]">
                      <FolderSearch className="w-12 h-12 text-[#444746] mx-auto mb-3 opacity-50" />
                      <p className="text-[#1f1f1f] font-semibold text-sm">No search results found</p>
                      <p className="text-xs text-[#444746] mt-1">Try another search term or query.</p>
                    </div>
                  )}
                </div>
              ) : null}
            </div>
          ) : currentView === "trash" ? (
            /* Trash View with Restore & Permanent Delete */
            <div className="flex-1 space-y-6">
              <h2 className="text-xl font-normal text-[#1f1f1f]">Items in Bin</h2>
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
                {folders.map((f) => (
                  <div key={f.id} className="p-4 bg-[#f8f9fa] border border-[#e1e3e1] rounded-2xl flex items-center justify-between">
                    <span className="font-semibold text-sm text-[#1f1f1f] truncate">{f.name}</span>
                    <div className="flex items-center gap-1">
                      <button
                        onClick={() => handleRestoreItem("folder", f.id)}
                        className="p-1.5 text-blue-600 hover:bg-blue-50 rounded-lg"
                        title="Restore"
                      >
                        <RotateCcw className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => handlePermanentDelete("folder", f.id)}
                        className="p-1.5 text-red-600 hover:bg-red-50 rounded-lg"
                        title="Delete permanently"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                ))}

                {documents.map((d) => (
                  <div key={d.id} className="p-4 bg-[#f8f9fa] border border-[#e1e3e1] rounded-2xl flex items-center justify-between">
                    <span className="font-semibold text-sm text-[#1f1f1f] truncate">{d.title}</span>
                    <div className="flex items-center gap-1">
                      <button
                        onClick={() => handleRestoreItem("doc", d.id)}
                        className="p-1.5 text-blue-600 hover:bg-blue-50 rounded-lg"
                        title="Restore"
                      >
                        <RotateCcw className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => handlePermanentDelete("doc", d.id)}
                        className="p-1.5 text-red-600 hover:bg-red-50 rounded-lg"
                        title="Delete permanently"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ) : currentView === "home" ? (
            /* Home View - Shows Only Recent Files Open */
            <div className="flex-1 space-y-4">
              <SuggestedFilesTable
                documents={documents}
                onSelectDoc={(d) => {
                  setSelectedDoc(d);
                  setSelectedFolder(null);
                  setPreviewDoc(d);
                  setShowDetailPanel(true);
                }}
                onPreviewDoc={(d) => setPreviewDoc(d)}
                selectedDocId={selectedDoc?.id}
                onToggleStar={async (d) => {
                  if (isUUID(d.id)) {
                    await api.documents.toggleStar(d.id).catch(() => {});
                  }
                  loadContents();
                }}
                onRename={(d) => setItemToRename({ type: "doc", item: d })}
                onMove={(d) => setItemToMove({ type: "doc", item: d })}
                onTrash={async (d) => {
                  if (isUUID(d.id)) {
                    await api.documents.toggleTrash(d.id).catch(() => {});
                  }
                  loadContents();
                }}
              />
            </div>
          ) : (
            /* My Drive View & Subfolder Navigation */
            <div className="flex-1 space-y-6">
              {/* Suggested Folders Carousel */}
              <SuggestedFoldersSection
                folders={folders}
                onOpenFolder={handleOpenFolder}
                onToggleStar={async (f) => {
                  if (isUUID(f.id)) {
                    await api.folders.toggleStar(f.id).catch(() => {});
                  }
                  loadContents();
                }}
                onRename={(f) => setItemToRename({ type: "folder", item: f })}
                onMove={(f) => setItemToMove({ type: "folder", item: f })}
                onTrash={async (f) => {
                  if (isUUID(f.id)) {
                    await api.folders.toggleTrash(f.id).catch(() => {});
                  }
                  loadContents();
                }}
              />

              {/* Suggested Files Detailed Table */}
              <SuggestedFilesTable
                documents={documents}
                onSelectDoc={(d) => {
                  setSelectedDoc(d);
                  setSelectedFolder(null);
                  setPreviewDoc(d);
                  setShowDetailPanel(true);
                }}
                onPreviewDoc={(d) => setPreviewDoc(d)}
                selectedDocId={selectedDoc?.id}
                onToggleStar={async (d) => {
                  if (isUUID(d.id)) {
                    await api.documents.toggleStar(d.id).catch(() => {});
                  }
                  loadContents();
                }}
                onRename={(d) => setItemToRename({ type: "doc", item: d })}
                onMove={(d) => setItemToMove({ type: "doc", item: d })}
                onTrash={async (d) => {
                  if (isUUID(d.id)) {
                    await api.documents.toggleTrash(d.id).catch(() => {});
                  }
                  loadContents();
                }}
              />
            </div>
          )}
        </main>

        {/* Right Info Drawer */}
        {showDetailPanel && (
          <DriveDetailPanel
            selectedFolder={selectedFolder}
            selectedDoc={selectedDoc}
            onClose={() => setShowDetailPanel(false)}
          />
        )}

        {/* Right-Side Persistent Chat Drawer */}
        <RightSideChatDrawer
          isOpen={showRightChatDrawer}
          onClose={() => setShowRightChatDrawer(false)}
          initialQuery={searchQuery}
          initialResults={searchResponse?.results}
          onPreviewDocument={(doc) => setPreviewDoc(doc)}
        />

        {/* Far Right Apps Dock */}
        <RightDock />
      </div>

      {/* Universal Multi-Format Document Viewer Modal */}
      <DocumentPreviewModal
        isOpen={!!previewDoc}
        doc={previewDoc}
        onClose={() => setPreviewDoc(null)}
        onToggleStar={async (d) => {
          if (isUUID(d.id)) {
            await api.documents.toggleStar(d.id).catch(() => {});
            loadContents();
          }
        }}
      />

      {/* Modals */}
      <NewFolderModal
        isOpen={isNewFolderOpen}
        onClose={() => setIsNewFolderOpen(false)}
        onCreate={handleCreateFolder}
      />

      <RenameModal
        isOpen={!!itemToRename}
        currentName={
          itemToRename
            ? "name" in itemToRename.item
              ? itemToRename.item.name
              : itemToRename.item.title
            : ""
        }
        onClose={() => setItemToRename(null)}
        onRename={handlePerformRename}
      />

      <MoveModal
        isOpen={!!itemToMove}
        onClose={() => setItemToMove(null)}
        onMove={handlePerformMove}
      />

      {/* Upload Tracker Widget */}
      <UploadWidget uploads={uploads} onDismiss={() => setUploads([])} />

      {/* Right-Click Context Menu */}
      {contextMenu.visible && (
        <div
          className="fixed inset-0 z-50 pointer-events-auto"
          onClick={() => setContextMenu((prev) => ({ ...prev, visible: false }))}
          onContextMenu={(e) => {
            e.preventDefault();
            setContextMenu({ visible: true, x: e.clientX, y: e.clientY });
          }}
        >
          <div
            className="absolute w-56 bg-surface border border-borderDark rounded-2xl shadow-2xl py-2 text-textMain animate-fadeIn"
            style={{
              top: `${Math.min(contextMenu.y, typeof window !== "undefined" ? window.innerHeight - 160 : contextMenu.y)}px`,
              left: `${Math.min(contextMenu.x, typeof window !== "undefined" ? window.innerWidth - 240 : contextMenu.x)}px`,
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <button
              onClick={() => {
                setContextMenu((prev) => ({ ...prev, visible: false }));
                setIsNewFolderOpen(true);
              }}
              className="w-full flex items-center gap-3 px-4 py-2.5 text-sm font-medium text-textMain hover:bg-white/10 transition-colors text-left"
            >
              <FolderPlus className="w-4 h-4 text-primary" />
              <span>Create new folder</span>
            </button>
            <div className="my-1 border-t border-borderDark/60" />
            <button
              onClick={() => {
                setContextMenu((prev) => ({ ...prev, visible: false }));
                fileInputRef.current?.click();
              }}
              className="w-full flex items-center gap-3 px-4 py-2.5 text-sm font-medium text-textMain hover:bg-white/10 transition-colors text-left"
            >
              <Upload className="w-4 h-4 text-blue-400" />
              <span>Upload file</span>
            </button>
            <button
              onClick={() => {
                setContextMenu((prev) => ({ ...prev, visible: false }));
                folderInputRef.current?.click();
              }}
              className="w-full flex items-center gap-3 px-4 py-2.5 text-sm font-medium text-textMain hover:bg-white/10 transition-colors text-left"
            >
              <FolderUp className="w-4 h-4 text-amber-400" />
              <span>Folder upload</span>
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

