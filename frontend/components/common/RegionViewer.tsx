"use client";

import dynamic from "next/dynamic";

const RegionViewer = dynamic(() => import("./RegionViewerImpl"), {
  ssr: false,
  loading: () => <div className="p-4 text-sm text-neutral-500">Loading viewer…</div>,
});

export default RegionViewer;
