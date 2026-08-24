"use client";

import { Document, Page, pdfjs } from "react-pdf";
import "react-pdf/dist/Page/AnnotationLayer.css";
import "react-pdf/dist/Page/TextLayer.css";

// Same static-asset worker setup as RegionHighlightViewerImpl (T53) — letting
// Next.js's minifier process the worker's own ES module syntax breaks the
// production build, and pdf.js touches Node-incompatible APIs at import time.
pdfjs.GlobalWorkerOptions.workerSrc = "/pdf.worker.min.mjs";

/**
 * T71 — citation click-through, page-level. Search citations are bound to
 * chunks (page_number only), not facts with a precise region — that
 * highlighting needs the fact/region pipeline (T22, not built). This opens
 * the correct page honestly, with no highlight box pretending to be more
 * precise than the data actually is.
 */
export default function CitationPageViewer({
  downloadUrl,
  pageNumber,
  documentTitle,
  renderWidth = 700,
}: {
  downloadUrl: string;
  pageNumber: number;
  documentTitle: string;
  renderWidth?: number;
}) {
  return (
    <div className="flex flex-col gap-3">
      <div className="text-sm font-medium truncate">{documentTitle} — page {pageNumber}</div>
      <div style={{ width: renderWidth }}>
        <Document file={downloadUrl} loading={<div className="text-sm text-neutral-500">Rendering page…</div>}>
          <Page
            pageNumber={pageNumber}
            width={renderWidth}
            renderAnnotationLayer={false}
            renderTextLayer={false}
          />
        </Document>
      </div>
    </div>
  );
}
