"use client";
import React, { useState, useEffect, useRef } from "react";
import { Search, X, Command } from "lucide-react";
import { Spinner } from "../ui/Spinner";

interface SearchBarProps {
  onSearch: (query: string) => void;
  loading: boolean;
}

const placeholders = [
  "Search for 'Q3 Financial Report'",
  "Ask 'What is the company policy on remote work?'",
  "Find 'Marketing Strategy 2024'",
  "Search 'Employee Onboarding Guide'",
];

export const SearchBar: React.FC<SearchBarProps> = ({ onSearch, loading }) => {
  const [query, setQuery] = useState("");
  const [placeholderIndex, setPlaceholderIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const interval = setInterval(() => {
      setPlaceholderIndex((prev) => (prev + 1) % placeholders.length);
    }, 3000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        inputRef.current?.focus();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim()) {
      onSearch(query.trim());
    }
  };

  return (
    <form onSubmit={handleSubmit} className="relative w-full group">
      <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none text-textMuted group-focus-within:text-primary transition-colors">
        {loading ? <Spinner className="w-5 h-5" /> : <Search className="w-5 h-5" />}
      </div>
      <input
        ref={inputRef}
        type="text"
        className="w-full h-14 pl-12 pr-24 bg-surface/50 border border-borderDark rounded-full text-textMain placeholder-textMuted focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary focus:bg-surface transition-all shadow-sm focus:shadow-[0_0_20px_rgba(99,102,241,0.2)] glass"
        placeholder={placeholders[placeholderIndex]}
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        autoFocus
      />
      
      <div className="absolute inset-y-0 right-0 pr-3 flex items-center gap-2">
        {query && (
          <button
            type="button"
            onClick={() => setQuery("")}
            className="p-1 text-textMuted hover:text-textMain rounded-full hover:bg-surface transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        )}
        <div className="hidden sm:flex items-center gap-1 px-2 py-1 rounded bg-surface border border-borderDark text-xs text-textMuted font-medium pointer-events-none">
          <Command className="w-3 h-3" />
          <span>K</span>
        </div>
      </div>
    </form>
  );
};
