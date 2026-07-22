"use client";
import React, { useState } from "react";
import { Search, Sparkles, LayoutGrid, List, Info, X } from "lucide-react";

interface DriveHeaderProps {
  onSearch: (query: string, useAi: boolean) => void;
  onClearSearch: () => void;
  searchQuery: string;
  isAiSearch: boolean;
  viewMode: "grid" | "list";
  onToggleViewMode: () => void;
  showDetailPanel: boolean;
  onToggleDetailPanel: () => void;
}

export function DriveHeader({
  onSearch,
  onClearSearch,
  searchQuery,
  isAiSearch,
  viewMode,
  onToggleViewMode,
  showDetailPanel,
  onToggleDetailPanel,
}: DriveHeaderProps) {
  const [query, setQuery] = useState(searchQuery);
  const [aiMode, setAiMode] = useState(isAiSearch);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim()) {
      onSearch(query.trim(), aiMode);
    }
  };

  const handleClear = () => {
    setQuery("");
    onClearSearch();
  };

  return (
    <header className="flex items-center justify-between gap-4 py-3 px-2 mb-4 border-b border-borderDark/40">
      {/* Search Bar */}
      <form onSubmit={handleSubmit} className="flex-1 max-w-2xl relative">
        <div className="relative flex items-center">
          <div className="absolute left-4 text-textMuted pointer-events-none">
            {aiMode ? (
              <Sparkles className="w-5 h-5 text-secondary animate-pulse" />
            ) : (
              <Search className="w-5 h-5 text-textMuted" />
            )}
          </div>

          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={aiMode ? "Ask AI anything about your drive documents..." : "Search in Drive..."}
            className={`w-full pl-12 pr-28 py-3 rounded-full bg-surface/90 text-textMain placeholder:text-textMuted text-sm border focus:outline-none transition-all shadow-inner ${
              aiMode
                ? "border-secondary/50 focus:border-secondary focus:ring-2 focus:ring-secondary/20"
                : "border-borderDark/80 focus:border-primary focus:ring-2 focus:ring-primary/20"
            }`}
          />

          <div className="absolute right-3 flex items-center gap-2">
            {query && (
              <button
                type="button"
                onClick={handleClear}
                className="p-1 rounded-full text-textMuted hover:text-textMain hover:bg-surface"
              >
                <X className="w-4 h-4" />
              </button>
            )}

            {/* AI Search Mode Toggle */}
            <button
              type="button"
              onClick={() => {
                const nextMode = !aiMode;
                setAiMode(nextMode);
                if (query.trim()) {
                  onSearch(query.trim(), nextMode);
                }
              }}
              title={aiMode ? "AI Search Active (RAG Enabled)" : "Switch to AI RAG Search"}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold transition-all border ${
                aiMode
                  ? "bg-secondary/20 text-secondary border-secondary/40 shadow-sm"
                  : "bg-surface/50 text-textMuted border-borderDark/60 hover:text-textMain hover:border-textMuted"
              }`}
            >
              <Sparkles className="w-3.5 h-3.5" />
              <span>AI</span>
            </button>
          </div>
        </div>
      </form>

      {/* Toolbar Controls */}
      <div className="flex items-center gap-2">
        {/* View Switcher (Grid / List) */}
        <button
          onClick={onToggleViewMode}
          title={viewMode === "grid" ? "Switch to List view" : "Switch to Grid view"}
          className="p-2.5 rounded-full text-textMuted hover:text-textMain hover:bg-surface border border-borderDark/50 transition-colors"
        >
          {viewMode === "grid" ? (
            <List className="w-4 h-4" />
          ) : (
            <LayoutGrid className="w-4 h-4" />
          )}
        </button>

        {/* Info Drawer Toggle */}
        <button
          onClick={onToggleDetailPanel}
          title="Details & Activity"
          className={`p-2.5 rounded-full transition-colors border ${
            showDetailPanel
              ? "bg-primary/20 text-primary border-primary/40"
              : "text-textMuted hover:text-textMain hover:bg-surface border-borderDark/50"
          }`}
        >
          <Info className="w-4 h-4" />
        </button>
      </div>
    </header>
  );
}
