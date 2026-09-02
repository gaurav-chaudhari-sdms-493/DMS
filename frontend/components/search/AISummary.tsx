import React, { useState } from "react";
import { Bot, ChevronDown, ChevronUp } from "lucide-react";
import { Card } from "../ui/Card";
import { MarkdownViewer } from "../chat/MarkdownViewer";
import { CitationModal, CitationModalCitation } from "./CitationModal";

interface AISummaryProps {
  summary: string;
  citations?: CitationModalCitation[];
}

export const AISummary: React.FC<AISummaryProps> = ({ summary, citations = [] }) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [activeCitationNumber, setActiveCitationNumber] = useState<number | null>(null);
  const isLong = summary.length > 240;

  const activeCitation = citations.find((c) => c.number === activeCitationNumber) ?? null;

  return (
    <Card gradient glow className="animate-slideUp mb-8 relative">
      <div className="flex items-start gap-4">
        <div className="w-10 h-10 rounded-full bg-gradient-to-br from-primary to-secondary flex items-center justify-center shrink-0 shadow-[0_0_15px_rgba(99,102,241,0.5)]">
          <Bot className="w-6 h-6 text-white" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between mb-2">
            <h3 className="font-semibold text-lg text-textMain">AI Summary</h3>
          </div>

          <div className="relative">
            <div
              className={`text-sm leading-relaxed text-textMain bg-surface/40 p-4 rounded-xl border border-borderDark/40 transition-all duration-300 ${
                !isExpanded && isLong ? "max-h-48 overflow-hidden" : ""
              }`}
            >
              <MarkdownViewer
                content={summary}
                onCitationClick={citations.length > 0 ? (n) => setActiveCitationNumber(n) : undefined}
              />
            </div>

            {!isExpanded && isLong && (
              <div className="absolute bottom-0 inset-x-0 h-16 bg-gradient-to-t from-white via-white/80 to-transparent pointer-events-none rounded-b-xl" />
            )}
          </div>

          {isLong && (
            <div className="mt-2.5 flex justify-start">
              <button
                onClick={() => setIsExpanded(!isExpanded)}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-[#edf2fc] hover:bg-[#c2e7ff] text-[#0b57d0] rounded-full text-xs font-bold border border-[#d3d7dc] transition-all cursor-pointer shadow-xs"
              >
                <span>{isExpanded ? "Show Less" : "Show More"}</span>
                {isExpanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
              </button>
            </div>
          )}
        </div>
      </div>

      <CitationModal citation={activeCitation} onClose={() => setActiveCitationNumber(null)} />
    </Card>
  );
};
