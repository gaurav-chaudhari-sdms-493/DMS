"use client";
import React from "react";
import { X } from "lucide-react";
import CitationPageViewer from "./CitationPageViewer";
import RegionViewer from "@/components/common/RegionViewer";

export interface CitationModalCitation {
  number: number;
  document_name: string;
  page_number: number | null;
  download_url?: string | null;
  fact_id?: string | null;
}

interface CitationModalProps {
  citation: CitationModalCitation | null;
  onClose: () => void;
}

/** T71 — modal shown when a [N] citation marker is clicked. */
export function CitationModal({ citation, onClose }: CitationModalProps) {
  if (!citation) return null;

  return (
    <div
      role="presentation"
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-xs animate-fadeIn"
      onClick={onClose}
    >
      <div
        role="presentation"
        className="w-full max-w-2xl max-h-[85vh] overflow-y-auto bg-white border border-[#e1e3e1] rounded-3xl shadow-2xl animate-scaleUp text-[#1f1f1f]"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-6 pt-6 pb-2">
          <h3 className="text-lg font-bold text-[#1f1f1f]">Source [{citation.number}]</h3>
          <button
            onClick={onClose}
            className="p-1.5 text-[#747775] hover:text-[#1f1f1f] rounded-full hover:bg-[#f0f4f9] transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="px-6 py-4">
          {citation.fact_id ? (
            // T73 — a citation bound to an extracted field, not a chunk:
            // same precise region-highlight viewer the checking screen
            // and Entity 360 use, instead of a page-level jump.
            <div className="h-[400px] relative">
              <RegionViewer factId={citation.fact_id} />
            </div>
          ) : citation.download_url && citation.page_number ? (
            <CitationPageViewer
              downloadUrl={citation.download_url}
              pageNumber={citation.page_number}
              documentTitle={citation.document_name}
              renderWidth={620}
            />
          ) : (
            <p className="text-sm text-[#444746]">
              {citation.document_name}
              {citation.page_number ? ` — page ${citation.page_number}` : ""}
              <br />
              <span className="text-[#747775]">No preview available for this source.</span>
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
