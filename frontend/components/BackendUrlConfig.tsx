"use client";

import React, { useState, useEffect } from "react";
import { Server, CheckCircle2, AlertTriangle, RefreshCw, Radio, Link as LinkIcon } from "lucide-react";
import { getBaseUrl, setCustomBaseUrl, testBackendConnection } from "@/lib/api";
import { Button } from "@/components/ui/Button";

interface BackendUrlConfigProps {
  className?: string;
  compact?: boolean;
}

export default function BackendUrlConfig({ className = "", compact = false }: BackendUrlConfigProps) {
  const [url, setUrl] = useState("");
  const [activeUrl, setActiveUrl] = useState("");
  const [testing, setTesting] = useState(false);
  const [status, setStatus] = useState<{ type: "idle" | "success" | "error"; message: string }>({
    type: "idle",
    message: "",
  });

  useEffect(() => {
    const current = getBaseUrl();
    setUrl(current);
    setActiveUrl(current);
  }, []);

  const handleTestAndSave = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!url.trim()) {
      setStatus({ type: "error", message: "Please enter a valid backend URL." });
      return;
    }

    setTesting(true);
    setStatus({ type: "idle", message: "" });

    const result = await testBackendConnection(url);
    setTesting(false);

    if (result.success) {
      const updated = getBaseUrl();
      setActiveUrl(updated);
      setUrl(updated);
      setStatus({ type: "success", message: result.message });
    } else {
      setStatus({ type: "error", message: result.message });
    }
  };

  const handleReset = () => {
    setCustomBaseUrl("");
    const defaultUrl = getBaseUrl();
    setUrl(defaultUrl);
    setActiveUrl(defaultUrl);
    setStatus({ type: "success", message: `Reset backend URL to default: ${defaultUrl}` });
  };

  return (
    <div className={`glass p-6 rounded-2xl border border-borderDark/60 shadow-xl bg-surface/40 backdrop-blur-md transition-all ${className}`}>
      <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-primary/20 text-primary flex items-center justify-center shadow-[0_0_15px_rgba(99,102,241,0.25)]">
            <Server className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-base font-bold text-textMain flex items-center gap-2">
              Backend Server Address
              <span className="text-[10px] uppercase tracking-wider font-extrabold px-2 py-0.5 rounded-full bg-primary/20 text-primary border border-primary/30">
                Dev Config
              </span>
            </h3>
            <p className="text-xs text-textMuted">
              Set active ngrok or local backend address for runtime requests
            </p>
          </div>
        </div>

        {activeUrl && (
          <div className="flex items-center gap-1.5 text-xs text-emerald-700 font-medium bg-emerald-500/10 border border-emerald-500/20 px-3 py-1.5 rounded-full">
            <Radio className="w-3.5 h-3.5 animate-pulse" />
            <span className="truncate max-w-[200px]">{activeUrl}</span>
          </div>
        )}
      </div>

      <form onSubmit={handleTestAndSave} className="flex flex-col gap-3">
        <div className="flex flex-col sm:flex-row gap-2">
          <div className="relative flex-1">
            <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-textMuted">
              <LinkIcon className="w-4 h-4" />
            </div>
            <input
              type="text"
              aria-label="Backend server URL"
              placeholder="e.g. https://1d07-103-226-171-223.ngrok-free.app or http://localhost:8000"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              className="w-full h-11 pl-10 pr-4 bg-background/60 border border-borderDark rounded-xl text-textMain placeholder:text-textMuted/60 text-sm focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all font-mono"
            />
          </div>

          <div className="flex items-center gap-2">
            <Button
              type="submit"
              variant="primary"
              size="md"
              loading={testing}
              className="whitespace-nowrap h-11 px-5 font-semibold text-sm shadow-md"
            >
              Test Connection
            </Button>

            <Button
              type="button"
              variant="ghost"
              size="md"
              onClick={handleReset}
              title="Reset to default URL"
              className="h-11 px-3 text-textMuted hover:text-textMain border border-borderDark/40"
            >
              <RefreshCw className="w-4 h-4" />
            </Button>
          </div>
        </div>

        {status.type === "success" && (
          <div className="flex items-center gap-2 text-xs font-medium text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-4 py-2.5 rounded-xl animate-fadeIn">
            <CheckCircle2 className="w-4 h-4 shrink-0" />
            <span>{status.message}</span>
          </div>
        )}

        {status.type === "error" && (
          <div className="flex items-center gap-2 text-xs font-medium text-red-400 bg-red-500/10 border border-red-500/20 px-4 py-2.5 rounded-xl animate-fadeIn">
            <AlertTriangle className="w-4 h-4 shrink-0" />
            <span>{status.message}</span>
          </div>
        )}
      </form>
    </div>
  );
}
