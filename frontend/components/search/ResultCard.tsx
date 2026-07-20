import React from "react";
import { FileText, Download, ExternalLink } from "lucide-react";
import { Card } from "../ui/Card";
import type { SearchResult } from "@/types";
import { Badge } from "../ui/Badge";

interface ResultCardProps {
  result: SearchResult;
}

export const ResultCard: React.FC<ResultCardProps> = ({ result }) => {
  // Mock logic to highlight bold tags from backend if snippet has HTML
  const createMarkup = (html: string) => {
    return { __html: html };
  };

  const getScoreColor = (score: number) => {
    if (score > 0.8) return "bg-success";
    if (score > 0.5) return "bg-yellow-500";
    return "bg-textMuted";
  };

  return (
    <Card className="hover:border-primary/50 group animate-fadeIn flex flex-col gap-4">
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3 overflow-hidden">
          <div className="p-2 rounded bg-surface border border-borderDark group-hover:border-primary/30 transition-colors">
            <FileText className="w-5 h-5 text-primary" />
          </div>
          <h4 className="font-medium text-textMain truncate" title={result.document_name}>
            {result.document_name}
          </h4>
        </div>
        {result.page_number && (
          <Badge status="default" className="shrink-0 ml-2">
            Page {result.page_number}
          </Badge>
        )}
      </div>

      <div 
        className="text-sm text-textMuted line-clamp-3 leading-relaxed bg-surface/30 p-3 rounded-lg border border-borderDark/50 italic"
        dangerouslySetInnerHTML={createMarkup(result.snippet)}
      />

      <div className="flex items-center justify-between mt-auto pt-2 border-t border-borderDark">
        <div className="flex items-center gap-2">
          <div className="w-16 h-1.5 bg-surface rounded-full overflow-hidden" title={`Relevance: ${Math.round(result.score * 100)}%`}>
            <div 
              className={`h-full rounded-full ${getScoreColor(result.score)}`} 
              style={{ width: `${Math.max(10, result.score * 100)}%` }} 
            />
          </div>
          <span className="text-xs text-textMuted font-medium">{Math.round(result.score * 100)}% Match</span>
        </div>

        <a 
          href={result.download_url} 
          target="_blank" 
          rel="noopener noreferrer"
          className="flex items-center gap-1.5 text-xs font-medium text-primary hover:text-indigo-400 transition-colors"
        >
          <Download className="w-3.5 h-3.5" />
          Download
        </a>
      </div>
    </Card>
  );
};
