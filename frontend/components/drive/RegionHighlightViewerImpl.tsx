"use client";

import { useEffect, useState } from "react";
import { Document, Page, pdfjs } from "react-pdf";
import "react-pdf/dist/Page/AnnotationLayer.css";
import "react-pdf/dist/Page/TextLayer.css";
import { api } from "@/lib/api";

// Served as a static asset (copied into public/ by the postinstall script)
// rather than bundled — letting Next.js's minifier process the worker's own
// ES module syntax breaks the production build.
pdfjs.GlobalWorkerOptions.workerSrc = "/pdf.worker.min.mjs";

interface FactRegion {
  region_id: string;
  page_number: number;
  page_width: number;
  page_height: number;
  rotation: number;
  skew: number;
  x0: number;
  y0: number;
  x1: number;
  y1: number;
}

interface FactDetail {
  fact_id: string;
  field_name: string;
  value: any;
  confidence: number | null;
  document_title: string;
  download_url: string | null;
  regions: FactRegion[];
}

/**
 * T53 — click a fact, see exactly where it came from on the page.
 * Coordinates are normalised 0-1 (per decision T06), so the highlight box
 * is positioned as a CSS percentage of the rendered page — correct at any
 * render width or zoom level, no pixel math needed.
 *
 * Rotation is applied via react-pdf's own `rotate` prop. Skew (fine-angle
 * drift from an imperfect scan) is carried through from the API but not
 * yet visually corrected — pdf.js renders the page as stored; true skew
 * correction would need image-level transform, not just a CSS rotate.
 */
export default function RegionHighlightViewer({
  factId,
  renderWidth = 700,
}: {
  factId: string;
  renderWidth?: number;
}) {
  const [fact, setFact] = useState<FactDetail | null>(null);
  const [activeRegionId, setActiveRegionId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    api.facts
      .get(factId)
      .then((data) => {
        if (cancelled) return;
        setFact(data);
        setActiveRegionId(data.regions?.[0]?.region_id ?? null);
      })
      .catch((e) => !cancelled && setError(e?.message || "Failed to load fact"));
    return () => {
      cancelled = true;
    };
  }, [factId]);

  if (error) {
    return <div className="p-4 text-sm text-red-500">{error}</div>;
  }
  if (!fact) {
    return <div className="p-4 text-sm text-neutral-500">Loading…</div>;
  }
  if (!fact.download_url || fact.regions.length === 0) {
    return <div className="p-4 text-sm text-neutral-500">No region on file for this fact.</div>;
  }

  const activeRegion = fact.regions.find((r) => r.region_id === activeRegionId) ?? fact.regions[0];
  const renderHeight = renderWidth * (activeRegion.page_height / activeRegion.page_width);

  return (
    <div className="flex flex-col gap-3">
      <div className="text-sm">
        <span className="font-medium">{fact.field_name}</span>
        {fact.confidence != null && (
          <span className="ml-2 text-neutral-500">confidence {Math.round(fact.confidence * 100)}%</span>
        )}
      </div>

      {fact.regions.length > 1 && (
        <div className="flex gap-2 text-xs">
          {fact.regions.map((r) => (
            <button
              key={r.region_id}
              onClick={() => setActiveRegionId(r.region_id)}
              className={`px-2 py-1 rounded border ${
                r.region_id === activeRegion.region_id
                  ? "border-teal-500 text-teal-600"
                  : "border-neutral-300 text-neutral-500"
              }`}
            >
              page {r.page_number}
            </button>
          ))}
        </div>
      )}

      <div className="relative" style={{ width: renderWidth, height: renderHeight }}>
        <Document file={fact.download_url} loading={<div className="text-sm text-neutral-500">Rendering page…</div>}>
          <Page
            pageNumber={activeRegion.page_number}
            width={renderWidth}
            rotate={activeRegion.rotation}
            renderAnnotationLayer={false}
            renderTextLayer={false}
          />
        </Document>

        <div
          className="absolute border-2 border-amber-400 bg-amber-300/25 pointer-events-none"
          style={{
            left: `${activeRegion.x0 * 100}%`,
            top: `${activeRegion.y0 * 100}%`,
            width: `${(activeRegion.x1 - activeRegion.x0) * 100}%`,
            height: `${(activeRegion.y1 - activeRegion.y0) * 100}%`,
          }}
        />
      </div>
    </div>
  );
}
