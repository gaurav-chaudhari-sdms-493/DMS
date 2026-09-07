"use client";

import dynamic from "next/dynamic";

// Same reasoning as RegionHighlightViewer.tsx: pdf.js touches browser-only
// APIs at module load time, so this stays out of the server render.
const MetadataRegionViewer = dynamic(() => import("./MetadataRegionViewer"), {
  ssr: false,
  loading: () => <div className="p-4 text-sm text-neutral-500">Loading viewer…</div>,
});

export default MetadataRegionViewer;
