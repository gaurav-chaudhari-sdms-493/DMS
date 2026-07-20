"use client";
import React, { useCallback, useState, useRef } from "react";
import { UploadCloud, File as FileIcon, X } from "lucide-react";

interface UploadZoneProps {
  onFileSelected: (file: File) => void;
  accept?: string;
  maxSizeMB?: number;
}

export const UploadZone: React.FC<UploadZoneProps> = ({
  onFileSelected,
  accept = ".pdf,.docx,.txt",
  maxSizeMB = 10,
}) => {
  const [isDragging, setIsDragging] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleDragEnter = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      setIsDragging(false);
      setError(null);

      const files = e.dataTransfer.files;
      if (files && files.length > 0) {
        processFile(files[0]);
      }
    },
    [onFileSelected, maxSizeMB]
  );

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setError(null);
    if (e.target.files && e.target.files.length > 0) {
      processFile(e.target.files[0]);
    }
  };

  const processFile = (file: File) => {
    if (file.size > maxSizeMB * 1024 * 1024) {
      setError(`File size exceeds ${maxSizeMB}MB limit.`);
      return;
    }
    // Very basic accept check (can be improved based on actual mime types)
    const ext = "." + file.name.split(".").pop()?.toLowerCase();
    const acceptedTypes = accept.split(",");
    if (accept && !acceptedTypes.includes(ext) && !acceptedTypes.some(t => file.type.includes(t.replace('.', '')))) {
      setError(`File type not supported. Please upload ${accept}`);
      return;
    }
    
    onFileSelected(file);
  };

  return (
    <div
      className={`relative w-full rounded-2xl border-2 border-dashed transition-all duration-300 flex flex-col items-center justify-center p-12 text-center cursor-pointer ${
        isDragging
          ? "border-primary bg-primary/5 scale-[1.02] shadow-[0_0_30px_rgba(99,102,241,0.2)]"
          : "border-borderDark hover:border-primary/50 hover:bg-surface animate-[pulseGlow_4s_infinite]"
      }`}
      onDragEnter={handleDragEnter}
      onDragOver={handleDragEnter}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      onClick={() => inputRef.current?.click()}
    >
      <input
        type="file"
        ref={inputRef}
        onChange={handleFileChange}
        accept={accept}
        className="hidden"
      />
      <div className="w-16 h-16 mb-4 rounded-full bg-surface flex items-center justify-center text-primary">
        <UploadCloud className="w-8 h-8" />
      </div>
      <h3 className="text-lg font-semibold text-textMain mb-2">
        Click or drag file to this area to upload
      </h3>
      <p className="text-sm text-textMuted max-w-sm">
        Supports {accept.replace(/,/g, ", ")}. Max file size {maxSizeMB}MB.
      </p>
      {error && (
        <div className="mt-4 text-sm text-red-500 bg-red-500/10 px-4 py-2 rounded-lg flex items-center">
          <X className="w-4 h-4 mr-2" />
          {error}
        </div>
      )}
    </div>
  );
};
