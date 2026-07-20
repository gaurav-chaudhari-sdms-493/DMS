"use client";
import { useState } from "react";
import { FolderSearch, AlertCircle } from "lucide-react";
import { SearchBar } from "@/components/search/SearchBar";
import { AISummary } from "@/components/search/AISummary";
import { ResultCard } from "@/components/search/ResultCard";
import { api } from "@/lib/api";
import type { SearchResponse } from "@/types";

export default function SearchPage() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [response, setResponse] = useState<SearchResponse | null>(null);
  const [hasSearched, setHasSearched] = useState(false);

  const handleSearch = async (query: string) => {
    setLoading(true);
    setError(null);
    setHasSearched(true);
    
    try {
      const res = await api.search.query(query);
      setResponse(res);
    } catch (err: any) {
      setError(err.message || "Failed to perform search. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto py-8">
      <div className="mb-10 animate-fadeIn">
        <h1 className="text-3xl font-bold text-textMain mb-6 text-center">What are you looking for?</h1>
        <SearchBar onSearch={handleSearch} loading={loading} />
      </div>

      {loading && (
        <div className="flex flex-col gap-4 animate-pulse">
          <div className="h-32 bg-surface rounded-xl border border-borderDark/50"></div>
          <div className="h-40 bg-surface rounded-xl border border-borderDark/50"></div>
          <div className="h-40 bg-surface rounded-xl border border-borderDark/50"></div>
        </div>
      )}

      {error && !loading && (
        <div className="flex flex-col items-center justify-center p-12 glass rounded-2xl animate-fadeIn border-red-500/20">
          <div className="w-16 h-16 rounded-full bg-red-500/10 text-red-500 flex items-center justify-center mb-4">
            <AlertCircle className="w-8 h-8" />
          </div>
          <h3 className="text-xl font-bold text-textMain mb-2">Search Failed</h3>
          <p className="text-textMuted text-center max-w-md">{error}</p>
        </div>
      )}

      {!loading && !error && response && (
        <div className="animate-fadeIn">
          {response.ai_summary && <AISummary summary={response.ai_summary} />}
          
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-xl font-semibold text-textMain">Search Results</h2>
            <span className="text-sm text-textMuted">{response.results.length} results found ({response.took_ms}ms)</span>
          </div>

          {response.results.length > 0 ? (
            <div className="grid grid-cols-1 gap-4">
              {response.results.map((result, idx) => (
                <ResultCard key={`${result.document_id}-${idx}`} result={result} />
              ))}
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center p-12 glass rounded-2xl animate-fadeIn">
               <div className="w-20 h-20 rounded-full bg-surface border border-borderDark flex items-center justify-center mb-4 text-textMuted">
                 <FolderSearch className="w-10 h-10" />
               </div>
               <h3 className="text-xl font-bold text-textMain mb-2">No documents found</h3>
               <p className="text-textMuted text-center max-w-md">We couldn't find any documents matching your query. Try adjusting your search terms or upload more documents.</p>
            </div>
          )}
        </div>
      )}

      {!hasSearched && !loading && (
         <div className="flex flex-col items-center justify-center mt-20 opacity-50 pointer-events-none">
           <FolderSearch className="w-24 h-24 text-textMuted mb-6" />
           <p className="text-textMuted text-lg">Your search results will appear here</p>
         </div>
      )}
    </div>
  );
}
