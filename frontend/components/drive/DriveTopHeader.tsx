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
      <div className="flex items-center gap-3 w-60 flex-shrink-0">
        <div className="w-9 h-9 flex items-center justify-center">
          {/* Authentic Google Drive Logo */}
          <svg className="w-8 h-8" viewBox="0 0 87.3 78" xmlns="http://www.w3.org/2000/svg">
            <path d="m6.6 66.85 3.85 6.65c.8 1.4 1.95 2.5 3.3 3.3l13.75-23.8h-27.5c0 1.55.4 3.1 1.2 4.5z" fill="#0066da"/>
            <path d="m43.65 25-13.75-23.8c-1.35.8-2.5 1.9-3.3 3.3l-25.4 44c-.8 1.4-1.2 2.95-1.2 4.5h27.5z" fill="#00ac47"/>
            <path d="m73.55 76.8c1.35-.8 2.5-1.9 3.3-3.3l1.6-2.75 7.65-13.25c.8-1.4 1.2-2.95 1.2-4.5h-27.5l5.85 10.15z" fill="#ea4335"/>
            <path d="m43.65 25 13.75-23.8c-1.4-.8-2.95-1.2-4.55-1.2h-18.4c-1.6 0-3.15.4-4.55 1.2z" fill="#00832d"/>
            <path d="m59.8 53h27.5c0-1.55-.4-3.1-1.2-4.5l-12.05-20.9-1.7-2.95c-.8-1.4-1.95-2.5-3.3-3.3l-13.75 23.8z" fill="#ffba00"/>
            <path d="m27.5 76.8h32.3c1.6 0 3.15-.4 4.55-1.2l-13.75-23.8h-27.55l-13.75 23.8c1.4.8 2.95 1.2 4.55 1.2z" fill="#2684fc"/>
          </svg>
        </div>
        <span className="text-xl font-medium text-[#444746] tracking-tight">Drive</span>
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
            placeholder="Get answers from Drive (AI Search)..."
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
