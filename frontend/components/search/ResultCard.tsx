import React from "react";
import { FileText, Download, User, Calendar, Tag } from "lucide-react";
import { Card } from "../ui/Card";
import type { SearchResult } from "@/types";
import { Badge } from "../ui/Badge";

interface ResultCardProps {
  result: SearchResult;
}

export const ResultCard: React.FC<ResultCardProps> = ({ result }) => {
  const createMarkup = (html: string) => {
    return { __html: html };
  };

  const getFileExtension = (filename: string): string => {
    const parts = filename.split(".");
    return parts.length > 1 ? parts[parts.length - 1].toLowerCase() : "";
  };

  const ext = getFileExtension(result.document_name);

  const getIconColor = (extension: string) => {
    if (extension === "pdf") return "text-red-500 bg-red-500/10 border-red-500/20";
    if (extension === "txt") return "text-blue-500 bg-blue-500/10 border-blue-500/20";
    if (extension === "docx" || extension === "doc") return "text-success bg-success/10 border-success/20";
    return "text-primary bg-primary/10 border-primary/20";
  };

  const getMatchGlow = (score: number) => {
    const pct = Math.round(score * 100);
    if (pct > 80) return "text-success bg-success/10 border-success/20 shadow-[0_0_15px_rgba(16,185,129,0.15)]";
    if (pct > 50) return "text-yellow-500 bg-yellow-500/10 border-yellow-500/20";
    if (pct > 20) return "text-primary bg-primary/10 border-primary/20";
    return "text-textMuted bg-surface border-borderDark";
  };

  const getProgressBarColor = (score: number) => {
    const pct = Math.round(score * 100);
    if (pct > 80) return "bg-success";
    if (pct > 50) return "bg-yellow-500";
    if (pct > 20) return "bg-primary";
    return "bg-textMuted";
  };

  const matchPct = Math.round(result.score * 100);

  // Extract custom metadata items
  const metadata = (result.metadata || {}) as Record<string, any>;
  const author = metadata.author as string | undefined;
  const date = metadata.date as string | undefined;
  const keyTopics = metadata.key_topics;

  const topicsList = Array.isArray(keyTopics) 
    ? keyTopics 
    : typeof keyTopics === "string" 
      ? JSON.parse(keyTopics) as string[]
      : [] as string[];

  return (
    <Card glow className="hover:border-primary/50 group animate-fadeIn flex flex-col gap-4">
      {/* File Title and Page */}
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3 overflow-hidden">
          <div className={`p-2.5 rounded-lg border transition-colors ${getIconColor(ext)}`}>
            <FileText className="w-5 h-5" />
          </div>
          <div className="flex flex-col min-w-0">
            <h4 className="font-bold text-textMain text-base truncate group-hover:text-primary transition-colors" title={result.document_name}>
              {result.document_name}
            </h4>
            
            {/* Author and Date if present */}
            {(author || date) && (
              <div className="flex items-center gap-3 mt-1 text-xs text-textMuted flex-wrap">
                {author && (
                  <span className="flex items-center gap-1">
                    <User className="w-3.5 h-3.5" />
                    {author}
                  </span>
                )}
                {date && (
                  <span className="flex items-center gap-1">
                    <Calendar className="w-3.5 h-3.5" />
                    {date}
                  </span>
                )}
              </div>
            )}
          </div>
        </div>
        
        {result.page_number && (
          <Badge status="default" className="shrink-0 ml-2">
            Page {result.page_number}
          </Badge>
        )}
      </div>

      {/* Snippet Content */}
      <div 
        className="text-sm text-textMuted leading-relaxed bg-surface/20 p-4 rounded-xl border border-borderDark/30 italic group-hover:bg-surface/30 group-hover:border-primary/10 transition-all duration-300"
        dangerouslySetInnerHTML={createMarkup(result.snippet)}
      />

      {/* Key Topics Tags if present */}
      {topicsList && topicsList.length > 0 && (
        <div className="flex items-center gap-2 flex-wrap pt-1">
          <Tag className="w-3.5 h-3.5 text-textMuted" />
          {topicsList.map((topic: string, i: number) => (
            <span key={i} className="text-[10px] font-bold px-2 py-0.5 rounded bg-primary/5 text-primary border border-primary/20 hover:bg-primary/10 transition-colors">
              {topic}
            </span>
          ))}
        </div>
      )}

      {/* Score Progress Bar and Download */}
      <div className="flex items-center justify-between mt-auto pt-3 border-t border-borderDark/40">
        <div className="flex items-center gap-3">
          <div className="w-24 h-2 bg-surface rounded-full overflow-hidden" title={`Relevance: ${matchPct}%`}>
            <div 
              className={`h-full rounded-full transition-all duration-500 ${getProgressBarColor(result.score)}`} 
              style={{ width: `${Math.max(5, matchPct)}%` }} 
            />
          </div>
          <span className={`text-xs font-semibold px-2.5 py-0.5 rounded-full border transition-all duration-300 ${getMatchGlow(result.score)}`}>
            {matchPct}% Match
          </span>
        </div>

        {result.download_url && (
          <a 
            href={result.download_url} 
            target="_blank" 
            rel="noopener noreferrer"
            className="flex items-center gap-1.5 text-xs font-semibold text-primary hover:text-indigo-400 bg-primary/10 hover:bg-primary/20 px-3 py-1.5 rounded-lg border border-primary/20 transition-all"
          >
            <Download className="w-3.5 h-3.5" />
            Download
          </a>
        )}
      </div>
    </Card>
  );
};
