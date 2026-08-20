"use client";
import React, { useCallback, useState, useRef } from "react";
import { UploadCloud, File as FileIcon, X } from "lucide-react";

interface UploadZoneProps {
  onFilesSelected?: (files: File[]) => void;
  onFileSelected?: (file: File) => void;
  accept?: string;
  maxSizeMB?: number;
}

export const UploadZone: React.FC<UploadZoneProps> = ({
  onFilesSelected,
  onFileSelected,
  accept = ".pdf,.docx,.doc,.xlsx,.xls,.pptx,.ppt,.md,.csv,.rtf,.json,.txt,.png,.jpg,.jpeg,.webp,.bmp,.py,.js,.jsx,.ts,.tsx,.java,.c,.cpp,.h,.hpp,.cs,.go,.rb,.php,.sh,.bash,.sql,.yaml,.yml,.xml,.html,.css,.scss,.log,.ini,.toml,.conf",

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

  const processFiles = useCallback(
    (fileList: FileList | File[]) => {
      const filesArray = Array.from(fileList);
      if (filesArray.length === 0) return;

      const validFiles: File[] = [];
      const errors: string[] = [];

      const acceptedTypes = accept.split(",");

      filesArray.forEach((file) => {
        if (file.size > maxSizeMB * 1024 * 1024) {
          errors.push(`"${file.name}" exceeds ${maxSizeMB}MB limit.`);
          return;
        }

        const ext = "." + file.name.split(".").pop()?.toLowerCase();
        if (
          accept &&
          !acceptedTypes.includes(ext) &&
          !acceptedTypes.some((t) => file.type.includes(t.replace(".", "")))
        ) {
          errors.push(`"${file.name}" format not supported.`);
          return;
        }

        validFiles.push(file);
      });

      if (errors.length > 0) {
        setError(errors.join(" "));
      }

      if (validFiles.length > 0) {
        if (onFilesSelected) {
          onFilesSelected(validFiles);
        } else if (onFileSelected) {
          validFiles.forEach((f) => onFileSelected(f));
        }
      }
    },
    [onFilesSelected, onFileSelected, accept, maxSizeMB]
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      setIsDragging(false);
      setError(null);

      const files = e.dataTransfer.files;
      if (files && files.length > 0) {
        processFiles(files);
      }
    },
    [processFiles]
  );

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setError(null);
    if (e.target.files && e.target.files.length > 0) {
      processFiles(e.target.files);
    }
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
        multiple
        className="hidden"
      />
      <div className="w-16 h-16 mb-4 rounded-full bg-surface flex items-center justify-center text-primary">
        <UploadCloud className="w-8 h-8" />
      </div>
      <h3 className="text-lg font-semibold text-textMain mb-2">
        Click or drag document(s) to this area to upload
      </h3>
      <p className="text-sm text-textMuted max-w-sm">
        Supports {accept.replace(/,/g, ", ")}. Max file size {maxSizeMB}MB per file.
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
