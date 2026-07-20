import React from "react";
import { File, CheckCircle, AlertCircle } from "lucide-react";

interface UploadProgressProps {
  fileName: string;
  progress: number; // 0 to 100
  status: "uploading" | "processing" | "indexed" | "failed";
}

export const UploadProgress: React.FC<UploadProgressProps> = ({ fileName, progress, status }) => {
  return (
    <div className="glass rounded-xl p-4 w-full animate-fadeIn">
      <div className="flex items-center mb-3">
        <File className="w-8 h-8 text-primary mr-3 opacity-80" />
        <div className="flex-1 truncate">
          <p className="text-sm font-medium text-textMain truncate">{fileName}</p>
          <p className="text-xs text-textMuted capitalize">
            {status === "uploading" && `Uploading... ${progress}%`}
            {status === "processing" && "Processing with AI..."}
            {status === "indexed" && "Upload complete"}
            {status === "failed" && "Upload failed"}
          </p>
        </div>
        <div className="ml-4">
          {status === "indexed" && <CheckCircle className="w-6 h-6 text-success" />}
          {status === "failed" && <AlertCircle className="w-6 h-6 text-red-500" />}
          {(status === "uploading" || status === "processing") && (
            <span className="text-xs font-bold text-primary">{progress}%</span>
          )}
        </div>
      </div>
      
      <div className="w-full h-2 bg-surface rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-300 ease-out ${
            status === "failed" ? "bg-red-500" : status === "indexed" ? "bg-success" : "bg-gradient-to-r from-primary to-secondary"
          }`}
          style={{ width: `${progress}%` }}
        />
      </div>
    </div>
  );
};
