"use client";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { UploadZone } from "@/components/upload/UploadZone";
import { UploadProgress } from "@/components/upload/UploadProgress";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/Button";
import { isAuthenticated } from "@/lib/auth";

interface UploadTask {
  id: string;
  file: File;
  progress: number;
  status: "uploading" | "processing" | "indexed" | "failed";
}

export default function UploadPage() {
  const router = useRouter();
  const [uploads, setUploads] = useState<UploadTask[]>([]);

  useEffect(() => {
    if (!isAuthenticated()) {
      router.replace("/login");
    }
  }, [router]);

  const handleFilesSelected = async (files: File[]) => {
    if (files.length === 0) return;

    const newTasks: UploadTask[] = files.map((file) => ({
      id: Math.random().toString(36).substring(7),
      file,
      progress: 0,
      status: "uploading",
    }));

    const taskIds = new Set(newTasks.map((t) => t.id));

    setUploads((prev) => [...newTasks, ...prev]);

    const interval = setInterval(() => {
      setUploads((prev) =>
        prev.map((u) => {
          if (taskIds.has(u.id) && u.status === "uploading") {
            const next = u.progress + 10;
            if (next >= 100) return { ...u, progress: 99 };
            return { ...u, progress: next };
          }
          return u;
        })
      );
    }, 200);

    try {
      if (files.length === 1) {
        await api.documents.upload(files[0]);
      } else {
        await api.documents.uploadBulk(files);
      }
      clearInterval(interval);
      setUploads((prev) =>
        prev.map((u) => (taskIds.has(u.id) ? { ...u, progress: 100, status: "indexed" } : u))
      );
    } catch (error) {
      clearInterval(interval);
      setUploads((prev) =>
        prev.map((u) => (taskIds.has(u.id) ? { ...u, status: "failed" } : u))
      );
    }
  };

  return (
    <div className="max-w-3xl mx-auto py-8 animate-fadeIn">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-textMain mb-2">Upload Documents</h1>
        <p className="text-textMuted">Add PDFs, Word docs, Excel sheets, PowerPoint, Markdown, CSV, RTF, JSON, or text files to your knowledge base.</p>

      </div>

      <UploadZone onFilesSelected={handleFilesSelected} />

      {uploads.length > 0 && (
        <div className="mt-12">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-xl font-semibold text-textMain">Recent Uploads</h2>
            <Link href="/drive">
              <Button variant="ghost" size="sm" className="gap-2">
                Go to DMS
                <ArrowRight className="w-4 h-4" />
              </Button>
            </Link>
          </div>
          <div className="flex flex-col gap-4">
            {uploads.map((upload) => (
              <UploadProgress
                key={upload.id}
                fileName={upload.file.name}
                progress={upload.progress}
                status={upload.status}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
