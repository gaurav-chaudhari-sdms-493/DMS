"use client";

import React from "react";
import { WifiOff, RefreshCcw, CheckCircle2, UploadCloud } from "lucide-react";
import { useOnlineStatus } from "@/hooks/useOnlineStatus";
import { Button } from "@/components/ui/Button";

export default function OfflineBanner() {
  const { isOnline, pendingCount, isSyncing, syncStatusMsg, triggerSync } = useOnlineStatus();

  if (isOnline && pendingCount === 0 && !syncStatusMsg) {
    return null;
  }

  return (
    <div className="w-full bg-gradient-to-r from-amber-500/15 via-amber-600/10 to-orange-500/15 border-b border-amber-500/30 px-4 py-2 text-xs font-medium text-amber-200 flex items-center justify-between backdrop-blur-md animate-fadeIn z-50">
      <div className="flex items-center gap-2.5">
        {!isOnline ? (
          <div className="w-6 h-6 rounded-full bg-amber-500/20 text-amber-400 flex items-center justify-center shrink-0">
            <WifiOff className="w-3.5 h-3.5" />
          </div>
        ) : pendingCount > 0 ? (
          <div className="w-6 h-6 rounded-full bg-indigo-500/20 text-indigo-400 flex items-center justify-center shrink-0">
            <UploadCloud className="w-3.5 h-3.5 animate-pulse" />
          </div>
        ) : (
          <div className="w-6 h-6 rounded-full bg-emerald-500/20 text-emerald-400 flex items-center justify-center shrink-0">
            <CheckCircle2 className="w-3.5 h-3.5" />
          </div>
        )}

        <div className="flex flex-col sm:flex-row sm:items-center gap-1">
          <span className="font-bold tracking-wide">
            {!isOnline ? "Offline Mode" : pendingCount > 0 ? "Pending Offline Sync" : "Sync Active"}
          </span>
          <span className="text-amber-200/80">
            {!isOnline
              ? pendingCount > 0
                ? `— Working offline (${pendingCount} ${pendingCount === 1 ? "item" : "items"} queued for sync when online)`
                : "— You are working offline with cached data."
              : pendingCount > 0
              ? `— ${pendingCount} ${pendingCount === 1 ? "item" : "items"} ready to sync.`
              : syncStatusMsg}
          </span>
        </div>
      </div>

      {isOnline && pendingCount > 0 && (
        <Button
          variant="secondary"
          size="sm"
          loading={isSyncing}
          onClick={triggerSync}
          className="h-7 px-3 text-xs bg-amber-500/20 hover:bg-amber-500/30 border-amber-500/40 text-amber-100"
        >
          <RefreshCcw className="w-3 h-3 mr-1.5" />
          Sync Now
        </Button>
      )}
    </div>
  );
}
