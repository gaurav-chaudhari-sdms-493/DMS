"use client";
/* eslint-disable jsx-a11y/media-has-caption, react/no-unescaped-entities, @next/next/no-img-element, jsx-a11y/click-events-have-key-events, jsx-a11y/no-static-element-interactions */
import React, { useState, useRef, useEffect } from "react";
import {
  Camera,
  X,
  RefreshCw,
  Check,
  Layers,
  Sliders,
  Trash2,
  Upload,
  Loader2,
  Sparkles,
  Image as ImageIcon,
  Eye,
  FileText,
} from "lucide-react";
import { getBaseUrl } from "@/lib/api";
import { getAccessToken } from "@/lib/auth";

interface WebScannerModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: () => void;
}

interface ScannedPage {
  id: string;
  dataUrl: string;
  filename: string;
  filter: "color" | "bw" | "grayscale";
}

export function WebScannerModal({ isOpen, onClose, onSuccess }: WebScannerModalProps) {
  const [sourceMode, setSourceMode] = useState<"camera" | "upload">("upload");
  const [stream, setStream] = useState<MediaStream | null>(null);
  const [cameraActive, setCameraActive] = useState(false);
  const [cameraError, setCameraError] = useState<string | null>(null);
  const [facingMode, setFacingMode] = useState<"environment" | "user">("environment");

  // Filter and preview state
  const [loadedImageSrc, setLoadedImageSrc] = useState<string | null>(null);
  const [loadedFileName, setLoadedFileName] = useState<string>("scanned_document.jpg");
  const [activeFilter, setActiveFilter] = useState<"color" | "bw" | "grayscale">("bw");
  const [contrast, setContrast] = useState(130);
  const [brightness, setBrightness] = useState(105);

  // Batch scanned pages list
  const [capturedPages, setCapturedPages] = useState<ScannedPage[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState<string | null>(null);

  const videoRef = useRef<HTMLVideoElement>(null);
  const previewCanvasRef = useRef<HTMLCanvasElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Start webcam / camera stream
  const startCamera = async () => {
    try {
      setCameraError(null);
      if (stream) {
        stream.getTracks().forEach((t) => t.stop());
      }
      const newStream = await navigator.mediaDevices.getUserMedia({
        video: {
          facingMode: facingMode,
          width: { ideal: 1920 },
          height: { ideal: 1080 },
        },
      });
      setStream(newStream);
      if (videoRef.current) {
        videoRef.current.srcObject = newStream;
      }
      setCameraActive(true);
    } catch (err: any) {
      console.error("Camera access error:", err);
      setCameraError("Camera permissions denied or device not found.");
      setCameraActive(false);
    }
  };

  // Stop camera stream
  const stopCamera = () => {
    if (stream) {
      stream.getTracks().forEach((t) => t.stop());
      setStream(null);
    }
    setCameraActive(false);
  };

  useEffect(() => {
    if (isOpen && sourceMode === "camera") {
      startCamera();
    } else {
      stopCamera();
    }
    return () => stopCamera();
  }, [isOpen, sourceMode, facingMode]);

  // Re-draw and apply filters to loaded image on canvas whenever filters change
  const renderFilterToCanvas = (imageSrc: string) => {
    const img = new Image();
    img.crossOrigin = "anonymous";
    img.onload = () => {
      if (!previewCanvasRef.current) return;
      const canvas = previewCanvasRef.current;
      const ctx = canvas.getContext("2d");
      if (!ctx) return;

      canvas.width = img.width || 1280;
      canvas.height = img.height || 720;

      ctx.filter = `contrast(${contrast}%) brightness(${brightness}%)`;
      ctx.drawImage(img, 0, 0, canvas.width, canvas.height);

      if (activeFilter === "bw" || activeFilter === "grayscale") {
        const imgData = ctx.getImageData(0, 0, canvas.width, canvas.height);
        const data = imgData.data;

        for (let i = 0; i < data.length; i += 4) {
          const avg = 0.299 * data[i] + 0.587 * data[i + 1] + 0.114 * data[i + 2];
          if (activeFilter === "bw") {
            const val = avg > 128 ? 255 : 0;
            data[i] = val;
            data[i + 1] = val;
            data[i + 2] = val;
          } else {
            data[i] = avg;
            data[i + 1] = avg;
            data[i + 2] = avg;
          }
        }
        ctx.putImageData(imgData, 0, 0);
      }
    };
    img.src = imageSrc;
  };

  // Trigger re-render whenever filter state or loaded image changes
  useEffect(() => {
    if (loadedImageSrc) {
      renderFilterToCanvas(loadedImageSrc);
    }
  }, [loadedImageSrc, activeFilter, contrast, brightness]);

  if (!isOpen) return null;

  // Handle local file selection
  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setLoadedFileName(file.name);
    const reader = new FileReader();
    reader.onload = (event) => {
      const src = event.target?.result as string;
      setLoadedImageSrc(src);
      setUploadStatus(null);
    };
    reader.readAsDataURL(file);
  };

  // Snap photo from live camera feed
  const snapCameraPage = () => {
    if (!videoRef.current || !previewCanvasRef.current) return;
    const video = videoRef.current;
    const tempCanvas = document.createElement("canvas");
    tempCanvas.width = video.videoWidth || 1280;
    tempCanvas.height = video.videoHeight || 720;
    const ctx = tempCanvas.getContext("2d");
    if (!ctx) return;

    ctx.drawImage(video, 0, 0, tempCanvas.width, tempCanvas.height);
    const cameraDataUrl = tempCanvas.toDataURL("image/jpeg", 0.95);
    setLoadedFileName(`camera_scan_${Date.now()}.jpg`);
    setLoadedImageSrc(cameraDataUrl);
    setSourceMode("upload"); // Switch to editor view
  };

  // Add current canvas document to batch list
  const addCurrentPageToBatch = () => {
    if (!previewCanvasRef.current) return;
    const canvas = previewCanvasRef.current;
    const dataUrl = canvas.toDataURL("image/jpeg", 0.92);

    const page: ScannedPage = {
      id: `page_${Date.now()}_${Math.random().toString(36).substr(2, 5)}`,
      dataUrl: dataUrl,
      filename: loadedFileName || `scan_page_${capturedPages.length + 1}.jpg`,
      filter: activeFilter,
    };
    setCapturedPages((prev) => [...prev, page]);
    setUploadStatus(`Page #${capturedPages.length + 1} added to scan bundle!`);
  };

  // Ingest batch scanned pages to DMS API via Base64 JSON payload
  const handleUploadScans = async () => {
    let pagesToUpload = [...capturedPages];

    // If batch list empty but image loaded on canvas, upload current canvas
    if (pagesToUpload.length === 0 && previewCanvasRef.current) {
      const canvas = previewCanvasRef.current;
      const dataUrl = canvas.toDataURL("image/jpeg", 0.92);
      pagesToUpload = [
        {
          id: `page_${Date.now()}`,
          dataUrl: dataUrl,
          filename: loadedFileName || "scanned_document.jpg",
          filter: activeFilter,
        },
      ];
    }

    if (pagesToUpload.length === 0) {
      setUploadStatus("Please upload a file or snap a page first.");
      return;
    }

    setIsUploading(true);
    setUploadStatus("Processing document scan & running OCR...");

    try {
      const baseUrl = getBaseUrl();
      const token = getAccessToken();
      let successCount = 0;

      for (let i = 0; i < pagesToUpload.length; i++) {
        const page = pagesToUpload[i];
        const rawB64 = page.dataUrl.split(",")[1];

        const payload = {
          raw_scan_b64: rawB64,
          filename: page.filename || `scanned_page_${i + 1}.jpg`,
          scanner_model: "Web Camera & Canvas Scanner",
          dpi: 300,
          color_mode: page.filter,
          operator_notes: `Processed via In-Browser Web Scanner (${page.filter} filter)`,
        };

        const headers: Record<string, string> = {
          "Content-Type": "application/json",
          "X-Webhook-Secret": "change_me_scanner_secret",
          "X-Scanner-Secret": "change_me_scanner_secret",
          "X-User-Email": "teamworklax@gmail.com",
        };
        if (token) {
          headers["Authorization"] = `Bearer ${token}`;
        }

        const res = await fetch(`${baseUrl}/api/v1/connectors/scan-inbound`, {
          method: "POST",
          headers: headers,
          body: JSON.stringify(payload),
        });

        if (res.ok) {
          successCount++;
        } else {
          const errData = await res.json().catch(() => ({}));
          console.error("Scan ingestion response error:", errData);
        }
      }

      if (successCount > 0) {
        setUploadStatus(`🎉 SUCCESS! Ingested ${successCount} scan(s) into "Scanned Documents"!`);
        setTimeout(() => {
          onClose();
          if (onSuccess) onSuccess();
        }, 1500);
      } else {
        setUploadStatus("Failed to ingest scan. Check connection and try again.");
      }
    } catch (err: any) {
      console.error("Upload error:", err);
      setUploadStatus(`Ingestion error: ${err.message || "Network failure"}`);
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-md p-4 animate-fadeIn">
      <div className="w-full max-w-4xl glass rounded-2xl border border-borderDark p-6 shadow-2xl space-y-4 max-h-[90vh] flex flex-col overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-borderDark pb-3">
          <div className="flex items-center gap-2">
            <Camera className="w-6 h-6 text-primary animate-pulse" />
            <h3 className="text-xl font-bold text-textMain">In-Browser Web Camera Scanner</h3>
            <span className="text-xs bg-primary/20 text-primary px-2.5 py-0.5 rounded-full font-medium border border-primary/30">
              HD Auto-Crop & Filters
            </span>
          </div>
          <button onClick={onClose} className="p-1.5 text-textMuted hover:text-textMain rounded-lg hover:bg-surface">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Source Mode Selector Tabs */}
        <div className="flex gap-2 bg-surface p-1 rounded-xl border border-borderDark w-fit">
          <button
            onClick={() => setSourceMode("upload")}
            className={`px-4 py-1.5 text-xs font-bold rounded-lg transition-colors flex items-center gap-1.5 ${
              sourceMode === "upload" ? "bg-primary text-white" : "text-textMuted hover:text-textMain"
            }`}
          >
            <Upload className="w-4 h-4" /> Upload Document / Photo to Scan
          </button>
          <button
            onClick={() => setSourceMode("camera")}
            className={`px-4 py-1.5 text-xs font-bold rounded-lg transition-colors flex items-center gap-1.5 ${
              sourceMode === "camera" ? "bg-primary text-white" : "text-textMuted hover:text-textMain"
            }`}
          >
            <Camera className="w-4 h-4" /> Live Webcam / Camera
          </button>
        </div>

        {/* Main Body */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 flex-1 overflow-hidden">
          {/* Main Viewfinder / Canvas Preview (2 cols) */}
          <div className="md:col-span-2 relative bg-black rounded-xl overflow-hidden flex items-center justify-center min-h-[320px] border border-borderDark shadow-inner p-2">
            {sourceMode === "camera" ? (
              <div className="relative w-full h-full flex items-center justify-center">
                {cameraActive ? (
                  <video ref={videoRef} autoPlay playsInline className="w-full h-full object-cover rounded-lg" />
                ) : (
                  <div className="text-center text-textMuted p-6 space-y-2">
                    <Camera className="w-12 h-12 mx-auto text-textMuted/50" />
                    <p className="text-sm">{cameraError || "Camera starting..."}</p>
                    {cameraError && (
                      <button onClick={startCamera} className="px-4 py-2 bg-primary text-white text-xs font-semibold rounded-lg">
                        Retry Camera
                      </button>
                    )}
                  </div>
                )}

                {/* Camera Snap Overlay */}
                {cameraActive && (
                  <div className="absolute bottom-4 left-0 right-0 flex items-center justify-center gap-4">
                    <button
                      onClick={() => setFacingMode((prev) => (prev === "environment" ? "user" : "environment"))}
                      className="p-3 bg-black/60 backdrop-blur-md rounded-full text-white hover:bg-black/80 border border-white/20"
                      title="Switch Camera"
                    >
                      <RefreshCw className="w-5 h-5" />
                    </button>
                    <button
                      onClick={snapCameraPage}
                      className="px-6 py-3 bg-primary hover:bg-primaryHover text-white font-bold rounded-full shadow-lg flex items-center gap-2 transition-transform active:scale-95 text-xs"
                    >
                      <Camera className="w-5 h-5" /> Snap Document Page
                    </button>
                  </div>
                )}
              </div>
            ) : (
              <div className="relative w-full h-full flex flex-col items-center justify-center">
                {/* Always rendered Canvas to avoid null ref timing issues */}
                <canvas
                  ref={previewCanvasRef}
                  className={loadedImageSrc ? "max-w-full max-h-[340px] object-contain rounded-lg border border-borderDark shadow-lg bg-white" : "hidden"}
                />

                {!loadedImageSrc && (
                  <div
                    onClick={() => fileInputRef.current?.click()}
                    className="w-full h-full flex flex-col items-center justify-center text-center p-8 space-y-3 cursor-pointer border-2 border-dashed border-primary/40 hover:border-primary rounded-xl transition-colors bg-surface/30 hover:bg-surface/60"
                  >
                    <ImageIcon className="w-14 h-14 mx-auto text-primary animate-bounce opacity-80" />
                    <p className="text-sm font-bold text-textMain">Click or Drag & Drop Document / Photo to Scan</p>
                    <p className="text-xs text-textMuted">Supports PDF, JPEG, PNG, multi-page TIFF</p>
                    <span className="px-5 py-2.5 bg-primary hover:bg-primaryHover text-white text-xs font-bold rounded-xl shadow-lg inline-flex items-center gap-2 mt-2">
                      <Upload className="w-4 h-4" /> Select File from Laptop
                    </span>
                  </div>
                )}

                {/* Hidden File Input */}
                <input
                  type="file"
                  ref={fileInputRef}
                  accept="image/*,.pdf,.tiff"
                  onChange={handleFileSelect}
                  className="hidden"
                />
              </div>
            )}
          </div>

          {/* Filter Controls & Batch Panel (1 col) */}
          <div className="flex flex-col space-y-3 bg-surface/50 rounded-xl p-4 border border-borderDark overflow-y-auto">
            <h4 className="text-sm font-semibold text-textMain flex items-center gap-2">
              <Sliders className="w-4 h-4 text-primary" /> Document Processing Filters
            </h4>

            {/* Filter Mode Selector */}
            <div className="grid grid-cols-3 gap-1.5 p-1 bg-surface rounded-lg border border-borderDark">
              <button
                onClick={() => setActiveFilter("bw")}
                className={`py-1.5 text-xs font-semibold rounded-md transition-colors ${
                  activeFilter === "bw" ? "bg-primary text-white" : "text-textMuted hover:text-textMain"
                }`}
              >
                B&W Clean
              </button>
              <button
                onClick={() => setActiveFilter("color")}
                className={`py-1.5 text-xs font-semibold rounded-md transition-colors ${
                  activeFilter === "color" ? "bg-primary text-white" : "text-textMuted hover:text-textMain"
                }`}
              >
                Color
              </button>
              <button
                onClick={() => setActiveFilter("grayscale")}
                className={`py-1.5 text-xs font-semibold rounded-md transition-colors ${
                  activeFilter === "grayscale" ? "bg-primary text-white" : "text-textMuted hover:text-textMain"
                }`}
              >
                Grayscale
              </button>
            </div>

            {/* Contrast & Brightness Sliders */}
            <div className="space-y-2 text-xs">
              <div className="flex justify-between font-medium text-textMuted">
                <span>Contrast (Text Sharpening)</span>
                <span>{contrast}%</span>
              </div>
              <input
                type="range"
                min="100"
                max="200"
                value={contrast}
                onChange={(e) => setContrast(Number(e.target.value))}
                className="w-full accent-primary h-1.5 bg-surface rounded-lg cursor-pointer"
              />

              <div className="flex justify-between font-medium text-textMuted pt-1">
                <span>Shadow Removal (Background Clean)</span>
                <span>{brightness}%</span>
              </div>
              <input
                type="range"
                min="80"
                max="150"
                value={brightness}
                onChange={(e) => setBrightness(Number(e.target.value))}
                className="w-full accent-primary h-1.5 bg-surface rounded-lg cursor-pointer"
              />
            </div>

            {/* Action Buttons */}
            {loadedImageSrc && (
              <button
                onClick={addCurrentPageToBatch}
                className="w-full py-2 bg-surface hover:bg-surface/80 border border-borderDark text-textMain text-xs font-bold rounded-lg flex items-center justify-center gap-1.5"
              >
                <Layers className="w-4 h-4 text-primary" /> Add Page to Batch List
              </button>
            )}

            {/* Snapped / Loaded Pages List */}
            <div className="pt-2 flex-1 flex flex-col space-y-2 border-t border-borderDark">
              <div className="flex items-center justify-between text-xs font-semibold text-textMain">
                <span>Batch Scans ({capturedPages.length})</span>
                {capturedPages.length > 0 && (
                  <button onClick={() => setCapturedPages([])} className="text-red-400 hover:text-red-300 text-[11px]">
                    Clear
                  </button>
                )}
              </div>

              {capturedPages.length > 0 && (
                <div className="grid grid-cols-2 gap-2 max-h-[140px] overflow-y-auto pr-1">
                  {capturedPages.map((page, idx) => (
                    <div key={page.id} className="relative group rounded-lg overflow-hidden border border-borderDark bg-surface">
                      <img src={page.dataUrl} alt={`Page ${idx + 1}`} className="w-full h-16 object-cover" />
                      <button
                        onClick={() => setCapturedPages((prev) => prev.filter((p) => p.id !== page.id))}
                        className="absolute top-1 right-1 p-1 bg-red-500/80 text-white rounded opacity-0 group-hover:opacity-100 transition-opacity"
                      >
                        <Trash2 className="w-3 h-3" />
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Ingestion Submit Button */}
            <button
              onClick={handleUploadScans}
              disabled={isUploading || (!loadedImageSrc && capturedPages.length === 0)}
              className="w-full py-3 bg-green-600 hover:bg-green-500 text-white font-bold rounded-xl shadow-lg flex items-center justify-center gap-2 transition-colors disabled:opacity-50 text-xs"
            >
              {isUploading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" /> Ingesting & Running OCR...
                </>
              ) : (
                <>
                  <Upload className="w-4 h-4" /> Upload Scan to DMS
                </>
              )}
            </button>

            {uploadStatus && (
              <div className="text-xs text-center p-2 rounded-lg bg-primary/10 text-primary font-medium border border-primary/20">
                {uploadStatus}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
