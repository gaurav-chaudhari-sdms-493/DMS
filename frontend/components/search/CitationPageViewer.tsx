"use client";

import dynamic from "next/dynamic";

// Same reasoning as RegionHighlightViewer's wrapper (T53): pdf.js must never
// run during SSR, so any consumer of this component gets that safety
// automatically instead of having to remember it themselves.
const CitationPageViewer = dynamic(() => import("./CitationPageViewerImpl"), {
  ssr: false,
  loading: () => <div className="p-4 text-sm text-neutral-500">Loading viewer…</div>,
});

export default CitationPageViewer;
