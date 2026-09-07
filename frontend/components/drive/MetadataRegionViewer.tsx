"use client";

import { useState } from "react";
import { Document, Page, pdfjs } from "react-pdf";
import "react-pdf/dist/Page/AnnotationLayer.css";
import "react-pdf/dist/Page/TextLayer.css";

// Served as a static asset (copied into public/ by the postinstall script)
// rather than bundled — same reasoning as RegionHighlightViewerImpl.tsx,
// and needed again here since this is a separate module react-pdf doesn't
// share worker config across.
pdfjs.GlobalWorkerOptions.workerSrc = "/pdf.worker.min.mjs";

/**
 * T05 — the metadata-item counterpart to RegionHighlightViewerImpl, for
 * non-VLM (`doc_dg_metadata_items`) source regions. Deliberately lighter:
 * these regions only ever come from a document's own real PDF text layer
 * (see source_location_service.py), so there's no rotation/skew to read
 * from a doc_dg_pages row the way a Fact's region does — react-pdf renders
 * the page as the PDF itself already encodes it, and the natural aspect
 * ratio is read directly off the rendered page via onLoadSuccess instead
 * of coming from the API.
 */
export default function MetadataRegionViewer({
  downloadUrl,
  pageNumber,
  region,
  renderWidth = 640,
}: {
  downloadUrl: string;
  pageNumber: number;
  region: { x0: number; y0: number; x1: number; y1: number };
  renderWidth?: number;
}) {
  const [aspectRatio, setAspectRatio] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  const renderHeight = aspectRatio ? renderWidth * aspectRatio : undefined;

  return (
    <div className="flex flex-col gap-2">
      <div className="relative w-full" style={{ height: renderHeight }}>
        {error ? (
          <div className="text-sm text-red-500 p-4">{error}</div>
        ) : (
          <Document
            file={downloadUrl}
            loading={<div className="text-sm text-neutral-500 p-4">Rendering page…</div>}
            onLoadError={(e) => setError(e?.message || "Failed to load document")}
          >
            <Page
              pageNumber={pageNumber}
              width={renderWidth}
              renderAnnotationLayer={false}
              renderTextLayer={false}
              onLoadSuccess={(page) => setAspectRatio(page.height / page.width)}
            />
          </Document>
        )}

        <div
          className="absolute border-2 border-amber-400 bg-amber-300/25 pointer-events-none"
          style={{
            left: `${region.x0 * 100}%`,
            top: `${region.y0 * 100}%`,
            width: `${(region.x1 - region.x0) * 100}%`,
            height: `${(region.y1 - region.y0) * 100}%`,
          }}
        />
      </div>
      <div className="text-xs text-neutral-500">page {pageNumber}</div>
    </div>
  );
}
