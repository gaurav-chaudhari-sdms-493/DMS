"use client";

import { useEffect, useRef, useState } from "react";
import { pdfjs } from "react-pdf";
import { api } from "@/lib/api";

// Use the same worker as react-pdf
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

export default function RegionViewerImpl({ factId }: { factId: string | null }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [fact, setFact] = useState<FactDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!factId) {
      setFact(null);
      setError(null);
      return;
    }
    let cancelled = false;
    setLoading(true);
    setError(null);
    api.facts
      .get(factId)
      .then((data) => {
        if (!cancelled) setFact(data);
      })
      .catch((err) => {
        if (!cancelled) setError(err.message || "Failed to load fact");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [factId]);

  useEffect(() => {
    if (!fact || !fact.download_url || fact.regions.length === 0 || !canvasRef.current) return;

    let cancelled = false;
    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const url = fact.download_url;
    const region = fact.regions[0];

    const drawBoxes = (width: number, height: number) => {
      ctx.save();
      for (const r of fact.regions) {
        if (r.page_number !== region.page_number) continue;
        
        ctx.save();
        
        const boxX = r.x0 * width;
        const boxY = r.y0 * height;
        const boxW = (r.x1 - r.x0) * width;
        const boxH = (r.y1 - r.y0) * height;
        
        const cx = boxX + boxW / 2;
        const cy = boxY + boxH / 2;
        
        ctx.translate(cx, cy);
        
        // Rotation and skew
        const rotRad = (r.rotation * Math.PI) / 180;
        const skewRad = (r.skew * Math.PI) / 180;
        
        ctx.rotate(rotRad);
        ctx.transform(1, 0, Math.tan(skewRad), 1, 0, 0);
        
        ctx.translate(-cx, -cy);
        
        ctx.fillStyle = "rgba(251, 191, 36, 0.25)"; // amber-300 with 25% opacity
        ctx.strokeStyle = "rgba(251, 191, 36, 1)";
        ctx.lineWidth = 2;
        ctx.fillRect(boxX, boxY, boxW, boxH);
        ctx.strokeRect(boxX, boxY, boxW, boxH);
        
        ctx.restore();
      }
      ctx.restore();
    };

    // Very naive check for PDF vs Image
    const isPdf = url.split("?")[0].toLowerCase().endsWith(".pdf") || url.includes("application/pdf");

    if (isPdf) {
      pdfjs.getDocument(url).promise.then((pdf) => {
        if (cancelled) return;
        return pdf.getPage(region.page_number);
      }).then((page) => {
        if (cancelled || !page) return;
        
        const unscaledViewport = page.getViewport({ scale: 1.0 });
        const scale = 800 / unscaledViewport.width;
        const viewport = page.getViewport({ scale });
        
        canvas.width = viewport.width;
        canvas.height = viewport.height;
        
        return page.render({ canvasContext: ctx, viewport }).promise.then(() => {
          if (!cancelled) drawBoxes(viewport.width, viewport.height);
        });
      }).catch((err) => {
        if (!cancelled) setError("Failed to render PDF: " + err.message);
      });
    } else {
      const img = new Image();
      img.crossOrigin = "anonymous";
      img.onload = () => {
        if (cancelled) return;
        const scale = 800 / img.width;
        canvas.width = 800;
        canvas.height = img.height * scale;
        ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
        drawBoxes(canvas.width, canvas.height);
      };
      img.onerror = () => {
        if (!cancelled) setError("Failed to load image");
      };
      img.src = url;
    }

    return () => {
      cancelled = true;
    };
  }, [fact]);

  if (!factId) return <div className="p-4 text-sm text-neutral-500">Select an item to view its source.</div>;
  if (error) return <div className="p-4 text-sm text-red-500">{error}</div>;
  if (loading) return <div className="p-4 text-sm text-neutral-500">Loading viewer…</div>;
  if (fact && (!fact.download_url || fact.regions.length === 0)) {
    return <div className="p-4 text-sm text-neutral-500">No region on file for this fact.</div>;
  }

  return (
    <div className="flex flex-col gap-3 w-full h-full overflow-auto p-4">
      {fact && (
        <div className="text-sm bg-white p-2 rounded shadow-sm border border-neutral-200">
          <span className="font-medium text-neutral-900">{fact.field_name}</span>
          {fact.confidence != null && (
            <span className="ml-2 text-neutral-500">confidence {Math.round(fact.confidence * 100)}%</span>
          )}
          <div className="text-neutral-700 mt-1">{String(fact.value?.v ?? fact.value)}</div>
        </div>
      )}
      <div className="relative mx-auto">
        <canvas ref={canvasRef} className="shadow-md bg-white max-w-full h-auto" />
      </div>
    </div>
  );
}
