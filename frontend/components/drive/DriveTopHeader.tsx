"use client";
import React, { useState } from "react";
import { Sparkles, X } from "lucide-react";

interface DriveTopHeaderProps {
  onSearch: (query: string, useAi: boolean) => void;
  searchQuery: string;
  onClearSearch: () => void;
  onToggleInfoPanel: () => void;
  showInfoPanel: boolean;
}

export function DriveTopHeader({
  onSearch,
  searchQuery,
  onClearSearch,
  onToggleInfoPanel,
  showInfoPanel,
}: DriveTopHeaderProps) {
  const [query, setQuery] = useState(searchQuery);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim()) {
      onSearch(query.trim(), true);
    }
  };

  return (
    <header className="h-16 px-4 flex items-center justify-between gap-4 bg-gdriveBg select-none border-b border-[#e1e3e1]/40">
      {/* Left: Brand Logo & Title */}
      <div className="flex items-center gap-3 flex-shrink-0">
        <div className="bg-[#1e1e24] px-3 py-1.5 rounded-xl border border-[#333538] flex items-center shadow-sm">
          <img
            src="/stark-logo-white.avif"
            alt="Stark Logo"
            className="h-6 w-auto object-contain"
          />
        </div>
        <span className="text-xl font-bold text-[#1f1f1f] tracking-tight">DMS</span>
      </div>

      {/* Center: Search Bar ("Get answers from Drive") */}
      <form onSubmit={handleSubmit} className="flex-1 max-w-3xl">
        <div className="relative flex items-center">
          <button type="submit" className="absolute left-4 text-[#444746] hover:text-[#1f1f1f]">
            <Sparkles className="w-5 h-5 text-[#0b57d0]" />
          </button>

          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Get answers from DMS (AI Search)..."
            className="w-full pl-12 pr-12 py-3 rounded-full bg-[#edf2fc] text-[#1f1f1f] placeholder:text-[#444746] text-sm focus:outline-none focus:bg-white focus:shadow-md focus:ring-1 focus:ring-[#0b57d0] transition-all"
          />

          {query && (
            <button
              type="button"
              onClick={() => {
                setQuery("");
                onClearSearch();
              }}
              className="absolute right-4 p-1.5 rounded-full text-[#444746] hover:bg-[#e1e3e1]"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>
      </form>

      {/* Right User Badge */}
      <div className="flex items-center gap-2">
        <div
          className="w-9 h-9 rounded-full bg-[#c2e7ff] text-[#001d35] font-bold text-xs flex items-center justify-center border border-[#727775] cursor-pointer shadow-sm hover:ring-2 hover:ring-[#0b57d0] transition-all"
          title="Active Account"
        >
          DMS
        </div>
      </div>
    </header>
  );
}
