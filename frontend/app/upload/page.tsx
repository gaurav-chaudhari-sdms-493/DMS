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

  const handleFileSelected = async (file: File) => {
    const id = Math.random().toString(36).substring(7);
    const newUpload: UploadTask = { id, file, progress: 0, status: "uploading" };
    setUploads((prev) => [newUpload, ...prev]);

    // Simulate progress
    const interval = setInterval(() => {
      setUploads((prev) =>
        prev.map((u) => {
          if (u.id === id && u.status === "uploading") {
            const next = u.progress + 10;
            if (next >= 100) return { ...u, progress: 99 };
            return { ...u, progress: next };
          }
          return u;
        })
      );
    }, 200);

    try {
      await api.documents.upload(file);
      clearInterval(interval);
      setUploads((prev) =>
        prev.map((u) => (u.id === id ? { ...u, progress: 100, status: "indexed" } : u))
      );
    } catch (error) {
      clearInterval(interval);
      setUploads((prev) =>
        prev.map((u) => (u.id === id ? { ...u, status: "failed" } : u))
      );
    }
  };

  return (
    <div className="max-w-3xl mx-auto py-8 animate-fadeIn">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-textMain mb-2">Upload Documents</h1>
        <p className="text-textMuted">Add PDFs, Word docs, or text files to your knowledge base.</p>
      </div>

      <UploadZone onFileSelected={handleFileSelected} />

      {uploads.length > 0 && (
        <div className="mt-12">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-xl font-semibold text-textMain">Recent Uploads</h2>
            <Link href="/search">
              <Button variant="ghost" size="sm" className="gap-2">
                Go to Search
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
