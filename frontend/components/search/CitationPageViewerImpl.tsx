"use client";

import { Document, Page, pdfjs } from "react-pdf";
import "react-pdf/dist/Page/AnnotationLayer.css";
import "react-pdf/dist/Page/TextLayer.css";

// Same static-asset worker setup as RegionHighlightViewerImpl (T53) — letting
// Next.js's minifier process the worker's own ES module syntax breaks the
// production build, and pdf.js touches Node-incompatible APIs at import time.
pdfjs.GlobalWorkerOptions.workerSrc = "/pdf.worker.min.mjs";

// A citation's document isn't always a PDF — a standalone scanned image
// upload (jpg/png/...) goes through the exact same citation path (search
// and chat both cite chunks regardless of source file type) but always
// has exactly one "page". Feeding a raw image into react-pdf's <Document>
// makes pdf.js fail outright ("Failed to load PDF file") since it isn't a
// valid PDF stream at all. Same URL-based check DocumentPreviewModal and
// RegionViewerImpl already use elsewhere in this codebase.
function isPdfUrl(url: string): boolean {
  return url.split("?")[0].toLowerCase().endsWith(".pdf");
}

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
  const isPdf = isPdfUrl(downloadUrl);

  return (
    <div className="flex flex-col gap-3">
      <div className="text-sm font-medium truncate">
        {documentTitle}{isPdf ? ` — page ${pageNumber}` : ""}
      </div>
      <div style={{ width: renderWidth }}>
        {isPdf ? (
          <Document file={downloadUrl} loading={<div className="text-sm text-neutral-500">Rendering page…</div>}>
            <Page
              pageNumber={pageNumber}
              width={renderWidth}
              renderAnnotationLayer={false}
              renderTextLayer={false}
            />
          </Document>
        ) : (
          // eslint-disable-next-line @next/next/no-img-element -- external
          // presigned S3 URL, not a local/optimizable asset
          <img
            src={downloadUrl}
            alt={documentTitle}
            className="w-full h-auto rounded-lg border border-neutral-200 shadow-sm"
          />
        )}
      </div>
    </div>
  );
}
