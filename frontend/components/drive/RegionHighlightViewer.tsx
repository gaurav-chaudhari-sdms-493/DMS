"use client";

import dynamic from "next/dynamic";

// pdf.js touches browser-only APIs at module load time (and, on newer
// pdfjs-dist versions, Promise.withResolvers — unavailable on Node 20,
// which this app's server runs on). Loading it with ssr:false keeps it
// out of the server render entirely, so any consumer of this component
// gets that safety for free instead of having to remember it themselves.
const RegionHighlightViewer = dynamic(() => import("./RegionHighlightViewerImpl"), {
  ssr: false,
  loading: () => <div className="p-4 text-sm text-neutral-500">Loading viewer…</div>,
});

export default RegionHighlightViewer;
