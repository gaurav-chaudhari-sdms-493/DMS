"use client";

import { useEffect, useLayoutEffect, useState } from "react";
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

// Raw backend sentinel field names, same mapping as workbench/page.tsx's
// SENTINEL_LABELS — this viewer is opened from both the workbench queue
// and DocumentPreviewModal's facts panel, so a sentinel like
// "_stitch_ambiguous" needs a real label here too, not just at the one
// call site that happened to add its own translation first.
const SENTINEL_LABELS: Record<string, string> = {
  _marginalia: "Handwritten margin note",
  _join_mismatch: "Table join couldn't be matched",
  _stitch_ambiguous: "Table continuation unclear",
};

function fieldLabel(fieldName: string): string {
  return SENTINEL_LABELS[fieldName] || fieldName;
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
  // A stitched or stitch-ambiguous fact's whole point is "does page A
  // relate to page B" — tab-switching between them one at a time made a
  // reviewer hold the first page in memory to compare against the second.
  // Side-by-side defaults on for those two cases (2 regions, most useful
  // to compare); a reviewer can still switch back to one-at-a-time for a
  // fact with more than 2 regions, where a full row of pages would be
  // cramped.
  const [sideBySide, setSideBySide] = useState(false);

  // The fixed pixel width this used to render at overflowed the modal on
  // phone/tablet-width screens (no horizontal scroll was offered, so the
  // page image and its highlight box just clipped). Measure the actual
  // container instead and never render wider than it.
  //
  // A plain useRef + useLayoutEffect(..., []) doesn't work here: this
  // component early-returns a "Loading…" placeholder until `fact` arrives,
  // so on first mount the container div doesn't exist yet and the
  // one-shot effect finds a null ref forever. A callback ref re-fires once
  // the div actually mounts (after loading finishes), so use that instead.
  const [containerEl, setContainerEl] = useState<HTMLDivElement | null>(null);
  const [containerWidth, setContainerWidth] = useState<number | null>(null);
  useLayoutEffect(() => {
    if (!containerEl) return;
    setContainerWidth(containerEl.clientWidth);
    const observer = new ResizeObserver((entries) => {
      const width = entries[0]?.contentRect.width;
      if (width) setContainerWidth(width);
    });
    observer.observe(containerEl);
    return () => observer.disconnect();
  }, [containerEl]);

  useEffect(() => {
    let cancelled = false;
    api.facts
      .get(factId)
      .then((data) => {
        if (cancelled) return;
        setFact(data);
        setActiveRegionId(data.regions?.[0]?.region_id ?? null);
        setSideBySide(data.regions?.length === 2);
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
  const effectiveWidth = Math.min(renderWidth, containerWidth ?? renderWidth);
  const renderHeight = effectiveWidth * (activeRegion.page_height / activeRegion.page_width);

  // Side by side always shows every region in one or two columns, wrapping
  // to a new row past that — capped at 2 columns because a highlight box
  // and its page need to stay legibly wide, not because more than 2
  // regions can't happen (a table can stitch across 3+ pages).
  const columns = Math.min(fact.regions.length, 2);
  const gapPx = 12;
  const cellWidth = containerWidth
    ? Math.max(140, (containerWidth - gapPx * (columns - 1)) / columns)
    : renderWidth / columns;

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <div className="text-sm">
          <span className="font-medium">{fieldLabel(fact.field_name)}</span>
          {fact.confidence != null && (
            <span className="ml-2 text-neutral-500">confidence {Math.round(fact.confidence * 100)}%</span>
          )}
        </div>
        {fact.regions.length > 1 && (
          <button
            onClick={() => setSideBySide((v) => !v)}
            className="text-xs px-2.5 py-1.5 rounded border border-neutral-300 text-neutral-600 hover:border-teal-500 hover:text-teal-600 min-h-[32px]"
          >
            {sideBySide ? "View one page at a time" : "Compare pages side by side"}
          </button>
        )}
      </div>

      {!sideBySide && fact.regions.length > 1 && (
        <div className="flex gap-2 text-xs flex-wrap">
          {fact.regions.map((r) => (
            <button
              key={r.region_id}
              onClick={() => setActiveRegionId(r.region_id)}
              className={`px-2 py-1.5 rounded border min-h-[36px] ${
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

      {sideBySide ? (
        <div ref={setContainerEl} className="flex flex-wrap gap-3">
          {fact.regions.map((r) => (
            <div key={r.region_id} className="flex flex-col gap-1" style={{ width: cellWidth }}>
              <div className="text-xs font-medium text-neutral-500">page {r.page_number}</div>
              <div className="relative" style={{ height: cellWidth * (r.page_height / r.page_width) }}>
                <Document file={fact.download_url} loading={<div className="text-sm text-neutral-500">Rendering page…</div>}>
                  <Page
                    pageNumber={r.page_number}
                    width={cellWidth}
                    rotate={r.rotation}
                    renderAnnotationLayer={false}
                    renderTextLayer={false}
                  />
                </Document>
                <div
                  className="absolute border-2 border-amber-400 bg-amber-300/25 pointer-events-none"
                  style={{
                    left: `${r.x0 * 100}%`,
                    top: `${r.y0 * 100}%`,
                    width: `${(r.x1 - r.x0) * 100}%`,
                    height: `${(r.y1 - r.y0) * 100}%`,
                  }}
                />
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div ref={setContainerEl} className="relative w-full" style={{ height: renderHeight || undefined }}>
          <Document file={fact.download_url} loading={<div className="text-sm text-neutral-500">Rendering page…</div>}>
            <Page
              pageNumber={activeRegion.page_number}
              width={effectiveWidth}
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
      )}
    </div>
  );
}
