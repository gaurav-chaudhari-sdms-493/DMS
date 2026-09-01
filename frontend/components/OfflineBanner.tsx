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

  // Solid, dark-on-light colors per state — the page background is
  // near-white (#f8f9fa), so pale/translucent tints (the previous
  // amber-100/200/400 on a 10-15% opacity amber wash) read as
  // yellow-on-yellow and are effectively unreadable. Each state gets its
  // own real background/text pairing, not one shared amber wash.
  const palette = !isOnline
    ? { bg: "bg-amber-100", border: "border-amber-300", text: "text-amber-900", sub: "text-amber-800", iconBg: "bg-amber-200", iconText: "text-amber-700" }
    : pendingCount > 0
    ? { bg: "bg-indigo-50", border: "border-indigo-200", text: "text-indigo-900", sub: "text-indigo-700", iconBg: "bg-indigo-100", iconText: "text-indigo-600" }
    : { bg: "bg-emerald-50", border: "border-emerald-200", text: "text-emerald-900", sub: "text-emerald-700", iconBg: "bg-emerald-100", iconText: "text-emerald-600" };

  return (
    <div className={`w-full ${palette.bg} border-b ${palette.border} px-4 py-2 text-xs font-medium ${palette.text} flex items-center justify-between backdrop-blur-md animate-fadeIn z-50`}>
      <div className="flex items-center gap-2.5">
        {!isOnline ? (
          <div className={`w-6 h-6 rounded-full ${palette.iconBg} ${palette.iconText} flex items-center justify-center shrink-0`}>
            <WifiOff className="w-3.5 h-3.5" />
          </div>
        ) : pendingCount > 0 ? (
          <div className={`w-6 h-6 rounded-full ${palette.iconBg} ${palette.iconText} flex items-center justify-center shrink-0`}>
            <UploadCloud className="w-3.5 h-3.5 animate-pulse" />
          </div>
        ) : (
          <div className={`w-6 h-6 rounded-full ${palette.iconBg} ${palette.iconText} flex items-center justify-center shrink-0`}>
            <CheckCircle2 className="w-3.5 h-3.5" />
          </div>
        )}

        <div className="flex flex-col sm:flex-row sm:items-center gap-1">
          <span className="font-bold tracking-wide">
            {!isOnline ? "Offline Mode" : pendingCount > 0 ? "Pending Offline Sync" : "Sync Active"}
          </span>
          <span className={palette.sub}>
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
          className="h-7 px-3 text-xs bg-indigo-100 hover:bg-indigo-200 border-indigo-300 text-indigo-900"
        >
          <RefreshCcw className="w-3 h-3 mr-1.5" />
          Sync Now
        </Button>
      )}
    </div>
  );
}
