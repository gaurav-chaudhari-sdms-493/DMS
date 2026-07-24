"use client";
import React, { useState } from "react";
import { Sparkles, X, User, LogOut, BarChart3, ChevronDown, ShieldCheck } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";

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
  const router = useRouter();
  const [query, setQuery] = useState(searchQuery);
  const [dropdownOpen, setDropdownOpen] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim()) {
      onSearch(query.trim(), true);
    }
  };

  const handleLogout = () => {
    api.auth.logout();
  };

  return (
    <header className="h-16 px-4 flex items-center justify-between gap-4 bg-gdriveBg select-none border-b border-[#e1e3e1]/40 relative z-30">
      {/* Left: Brand Logo & Title */}
      <div className="flex items-center gap-3 flex-shrink-0">
        <Link href="/drive" className="bg-[#1e1e24] px-3 py-1.5 rounded-xl border border-[#333538] flex items-center shadow-sm hover:border-primary/50 transition-colors">
          <img
            src="/stark-logo-white.avif"
            alt="Stark Logo"
            className="h-6 w-auto object-contain"
          />
        </Link>
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

      {/* Right User Badge with Dropdown */}
      <div className="relative">
        <button
          onClick={() => setDropdownOpen(!dropdownOpen)}
          className="flex items-center gap-1.5 p-1 rounded-full hover:bg-[#e1e3e1]/60 transition-colors focus:outline-none"
        >
          <div
            className="w-9 h-9 rounded-full bg-[#c2e7ff] text-[#001d35] font-bold text-xs flex items-center justify-center border border-[#727775] shadow-sm hover:ring-2 hover:ring-[#0b57d0] transition-all"
            title="Account Menu"
          >
            DMS
          </div>
          <ChevronDown className="w-3.5 h-3.5 text-[#444746]" />
        </button>

        {dropdownOpen && (
          <>
            <div
              className="fixed inset-0 z-40"
              onClick={() => setDropdownOpen(false)}
            />
            <div className="absolute right-0 mt-2 w-56 bg-surface border border-borderDark rounded-xl shadow-xl z-50 py-2 animate-fadeIn text-textMain">
              <div className="px-4 py-2.5 border-b border-borderDark/60">
                <p className="text-xs text-textMuted uppercase font-semibold tracking-wider">Account</p>
                <p className="text-sm font-semibold truncate text-textMain mt-0.5">DocSearch User</p>
              </div>

              <div className="py-1">
                <Link
                  href="/profile"
                  onClick={() => setDropdownOpen(false)}
                  className="flex items-center gap-2.5 px-4 py-2 text-sm text-textMain hover:bg-white/5 transition-colors"
                >
                  <User className="w-4 h-4 text-primary" />
                  <span>Profile & Analytics</span>
                </Link>
                <Link
                  href="/profile"
                  onClick={() => setDropdownOpen(false)}
                  className="flex items-center gap-2.5 px-4 py-2 text-sm text-textMuted hover:text-textMain hover:bg-white/5 transition-colors"
                >
                  <BarChart3 className="w-4 h-4 text-emerald-400" />
                  <span>Storage Stats</span>
                </Link>
                <Link
                  href="/admin"
                  onClick={() => setDropdownOpen(false)}
                  className="flex items-center gap-2.5 px-4 py-2 text-sm text-textMuted hover:text-textMain hover:bg-white/5 transition-colors"
                >
                  <ShieldCheck className="w-4 h-4 text-violet-500" />
                  <span>Admin Panel</span>
                </Link>
              </div>

              <div className="border-t border-borderDark/60 pt-1 mt-1">
                <button
                  onClick={handleLogout}
                  className="w-full flex items-center gap-2.5 px-4 py-2 text-sm text-red-400 hover:bg-red-500/10 transition-colors text-left"
                >
                  <LogOut className="w-4 h-4" />
                  <span>Log Out</span>
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </header>
  );
}

