import React from "react";
import { Bot } from "lucide-react";
import { Card } from "../ui/Card";

interface AISummaryProps {
  summary: string;
}

export const AISummary: React.FC<AISummaryProps> = ({ summary }) => {
  const isNotFound = summary.toLowerCase().includes("not found in documents");

  return (
    <Card gradient glow className="animate-slideUp mb-8 relative">
      <div className="flex items-start gap-4">
        <div className="w-10 h-10 rounded-full bg-gradient-to-br from-primary to-secondary flex items-center justify-center shrink-0 shadow-[0_0_15px_rgba(99,102,241,0.5)]">
          <Bot className="w-6 h-6 text-white" />
        </div>
        <div className="flex-1">
          <div className="flex items-center justify-between mb-2">
            <h3 className="font-semibold text-lg text-textMain">AI Summary</h3>
            <span className="text-[10px] uppercase tracking-wider font-bold px-2 py-1 rounded bg-primary/20 text-primary border border-primary/30">
              Powered by AI
            </span>
          </div>
          <div className={`prose prose-invert max-w-none text-sm leading-relaxed ${isNotFound ? "text-textMuted" : "gradient-text font-medium"}`}>
            {summary}
          </div>
        </div>
      </div>
    </Card>
  );
};
