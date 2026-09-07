"use client";

import { useEffect, useLayoutEffect, useRef, useState, useCallback } from "react";
import { Document, Page, pdfjs } from "react-pdf";
import "react-pdf/dist/Page/AnnotationLayer.css";
import "react-pdf/dist/Page/TextLayer.css";
import { RotateCw, Compass } from "lucide-react";
import { api } from "@/lib/api";
import { useI18n } from "@/lib/i18n";

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
 * Single Page + Affine Skew-Corrected Region View (T53)
 *
 * Implements genuine image-level 2D canvas transformation:
 * - When deskew is enabled and skew != 0: canvas bitmap is counter-rotated
 *   by -skew around page center, straightening crooked register rows.
 * - Highlight box is drawn via SVG overlay: in deskewed mode, it forms an
 *   axis-aligned highlight over the straightened row; in raw scan mode, it
 *   rotates by skew around the page center to match the tilted text.
 */
function PageRegionView({
  downloadUrl,
  region,
  width,
  deskewEnabled,
}: {
  downloadUrl: string;
  region: FactRegion;
  width: number;
  deskewEnabled: boolean;
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const pageAspect = region.page_height > 0 && region.page_width > 0 ? region.page_height / region.page_width : 1.414;
  const height = width * pageAspect;
  const hasSkew = region.skew !== 0 && !isNaN(region.skew);

  // Canvas post-processing: apply affine 2D transform to deskew the page bitmap
  const onRenderSuccess = useCallback(() => {
    if (!containerRef.current || !hasSkew || !deskewEnabled) return;
    const canvas = containerRef.current.querySelector("canvas");
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    // Create an offscreen buffer holding the rendered page
    const offscreen = document.createElement("canvas");
    offscreen.width = canvas.width;
    offscreen.height = canvas.height;
    const offCtx = offscreen.getContext("2d");
    if (!offCtx) return;
    offCtx.drawImage(canvas, 0, 0);

    // Clear and redraw with counter-rotation around center
    ctx.save();
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = "#ffffff";
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    const cx = canvas.width / 2;
    const cy = canvas.height / 2;
    const rad = (-region.skew * Math.PI) / 180;

    ctx.translate(cx, cy);
    ctx.rotate(rad);
    ctx.translate(-cx, -cy);
    ctx.drawImage(offscreen, 0, 0);
    ctx.restore();
  }, [hasSkew, deskewEnabled, region.skew]);

  // Pixel coordinates for SVG highlight bounding box
  const boxX = region.x0 * width;
  const boxY = region.y0 * height;
  const boxW = Math.max(2, (region.x1 - region.x0) * width);
  const boxH = Math.max(2, (region.y1 - region.y0) * height);
  const centerX = width / 2;
  const centerY = height / 2;

  return (
    <div
      ref={containerRef}
      className="relative overflow-hidden bg-white shadow-sm border border-[#e1e3e1] rounded-lg"
      style={{ width, height }}
    >
      <Document file={downloadUrl} loading={<div className="p-4 text-xs text-[#747775]">Rendering page…</div>}>
        <Page
          pageNumber={region.page_number}
          width={width}
          rotate={region.rotation}
          onRenderSuccess={onRenderSuccess}
          renderAnnotationLayer={false}
          renderTextLayer={false}
        />
      </Document>

      {/* SVG Affine Highlight Overlay */}
      <svg
        aria-hidden="true"
        className="absolute inset-0 w-full h-full pointer-events-none z-10"
        viewBox={`0 0 ${width} ${height}`}
      >
        <rect
          x={boxX}
          y={boxY}
          width={boxW}
          height={boxH}
          rx={3}
          transform={
            !deskewEnabled && hasSkew
              ? `rotate(${region.skew}, ${centerX}, ${centerY})`
              : undefined
          }
          className="fill-amber-400/30 stroke-amber-500 stroke-2"
          style={{ vectorEffect: "non-scaling-stroke" }}
        />
      </svg>
    </div>
  );
}

/**
 * T53 — Click a fact, see exactly where it came from on the page.
 * Coordinates are normalised 0-1 (per decision T06).
 *
 * Rotation is handled via react-pdf's `rotate` prop.
 * Skew (fine-angle scan drift) is visually corrected via 2D canvas affine
 * transform + SVG rotated highlight mapping.
 */
export default function RegionHighlightViewer({
  factId,
  renderWidth = 800,
}: {
  factId: string;
  renderWidth?: number;
}) {
  const { t } = useI18n();
  const [fact, setFact] = useState<FactDetail | null>(null);
  const [activeRegionId, setActiveRegionId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [sideBySide, setSideBySide] = useState(false);
  // T53: Deskew toggle state — defaults to true when scan has skew
  const [deskewEnabled, setDeskewEnabled] = useState(true);

  const [containerEl, setContainerEl] = useState<HTMLDivElement | null>(null);
  const [containerWidth, setContainerWidth] = useState<number | null>(null);

  const getFieldLabel = useCallback((fieldName: string): string => {
    if (fieldName === "_marginalia") return t("workbench.sentinel.marginalia", "Handwritten margin note");
    if (fieldName === "_join_mismatch") return t("workbench.sentinel.join_mismatch", "Table join couldn't be matched");
    if (fieldName === "_stitch_ambiguous") return t("workbench.sentinel.stitch_ambiguous", "Table continuation unclear");
    return fieldName;
  }, [t]);

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
    return <div className="p-4 text-sm text-[#747775]">{t("common.loading", "Loading…")}</div>;
  }
  if (!fact.download_url || fact.regions.length === 0) {
    return <div className="p-4 text-sm text-[#747775]">No region on file for this fact.</div>;
  }

  const activeRegion = fact.regions.find((r) => r.region_id === activeRegionId) ?? fact.regions[0];
  const effectiveWidth = Math.min(renderWidth, containerWidth ?? renderWidth);

  // Check if any visible region has detected skew
  const currentSkew = activeRegion.skew ?? 0;
  const hasSkew = currentSkew !== 0 && !isNaN(currentSkew);

  const columns = Math.min(fact.regions.length, 2);
  const gapPx = 12;
  const cellWidth = containerWidth
    ? Math.max(140, (containerWidth - gapPx * (columns - 1)) / columns)
    : renderWidth / columns;

  return (
    <div className="flex flex-col gap-3">
      {/* Top Header / Metadata & Skew Controls */}
      <div className="flex items-center justify-between gap-2 flex-wrap pb-2 border-b border-[#e1e3e1]">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-sm font-semibold text-[#1f1f1f]">{getFieldLabel(fact.field_name)}</span>
          {fact.confidence != null && (
            <span className="text-xs text-[#5f6368] font-mono px-2 py-0.5 rounded bg-[#f0f4f9] border border-[#e1e3e1]">
              {(fact.confidence * 100).toFixed(1)}% {t("workbench.label.confidence", "confidence")}
            </span>
          )}
          {hasSkew && (
            <span
              title={`Scan has a detected skew angle of ${currentSkew > 0 ? "+" : ""}${currentSkew.toFixed(1)}°`}
              className="flex items-center gap-1 text-xs px-2 py-0.5 rounded-full font-medium bg-amber-50 text-amber-800 border border-amber-200"
            >
              <Compass className="w-3.5 h-3.5" aria-hidden="true" />
              {t("workbench.deskew.skew_badge", "Skew")}: {currentSkew > 0 ? "+" : ""}{currentSkew.toFixed(1)}&deg;
            </span>
          )}
        </div>

        <div className="flex items-center gap-2">
          {/* T53: Operator Deskew / Straighten Toggle */}
          {hasSkew && (
            <button
              type="button"
              onClick={() => setDeskewEnabled((v) => !v)}
              aria-label={deskewEnabled ? "Switch to original raw scan view" : "Switch to auto-straightened scan view"}
              className={`flex items-center gap-1 text-xs px-2.5 py-1.5 rounded-lg border font-medium transition-colors ${
                deskewEnabled
                  ? "bg-[#0d2e5c] text-white border-[#0d2e5c]"
                  : "bg-white text-[#444746] border-[#e1e3e1] hover:bg-[#f0f4f9]"
              }`}
            >
              <RotateCw className="w-3.5 h-3.5" aria-hidden="true" />
              {deskewEnabled ? t("workbench.deskew.deskewed", "Straightened (Deskewed)") : t("workbench.deskew.original", "Original Scan")}
            </button>
          )}

          {fact.regions.length > 1 && (
            <button
              type="button"
              onClick={() => setSideBySide((v) => !v)}
              className="text-xs px-2.5 py-1.5 rounded-lg border border-[#e1e3e1] text-[#444746] bg-white hover:bg-[#f0f4f9] font-medium"
            >
              {sideBySide ? "View one page" : "Compare side-by-side"}
            </button>
          )}
        </div>
      </div>

      {/* Page Tabs for Multi-Region Facts (when not side-by-side) */}
      {!sideBySide && fact.regions.length > 1 && (
        <div role="tablist" aria-label="Document pages" className="flex gap-2 text-xs flex-wrap">
          {fact.regions.map((r) => (
            <button
              key={r.region_id}
              role="tab"
              aria-selected={r.region_id === activeRegion.region_id}
              onClick={() => setActiveRegionId(r.region_id)}
              className={`px-3 py-1.5 rounded-lg border font-medium transition-colors ${
                r.region_id === activeRegion.region_id
                  ? "bg-[#0d2e5c] text-white border-[#0d2e5c]"
                  : "bg-white text-[#444746] border-[#e1e3e1] hover:bg-[#f0f4f9]"
              }`}
            >
              Page {r.page_number}
              {r.skew !== 0 && ` (${r.skew > 0 ? "+" : ""}${r.skew.toFixed(1)}°)`}
            </button>
          ))}
        </div>
      )}

      {/* Main Scan Viewport */}
      {sideBySide ? (
        <div ref={setContainerEl} className="flex flex-wrap gap-3">
          {fact.regions.map((r) => (
            <div key={r.region_id} className="flex flex-col gap-1" style={{ width: cellWidth }}>
              <div className="text-xs font-medium text-[#5f6368] flex items-center justify-between">
                <span>Page {r.page_number}</span>
                {r.skew !== 0 && (
                  <span className="text-[10px] font-mono text-amber-700">
                    {r.skew > 0 ? "+" : ""}{r.skew.toFixed(1)}&deg;
                  </span>
                )}
              </div>
              <PageRegionView
                downloadUrl={fact.download_url!}
                region={r}
                width={cellWidth}
                deskewEnabled={deskewEnabled}
              />
            </div>
          ))}
        </div>
      ) : (
        <div ref={setContainerEl} className="relative w-full flex justify-center">
          <PageRegionView
            downloadUrl={fact.download_url}
            region={activeRegion}
            width={effectiveWidth}
            deskewEnabled={deskewEnabled}
          />
        </div>
      )}
    </div>
  );
}

