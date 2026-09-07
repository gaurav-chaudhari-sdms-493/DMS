"use client";

import { createContext, useContext, useState, useEffect, useCallback, useRef, ReactNode, createElement } from "react";
import { offlineStore, syncOfflineData } from "@/lib/offlineStore";
import { api, getBaseUrl } from "@/lib/api";

interface OnlineStatusValue {
  isOnline: boolean;
  pendingCount: number;
  isSyncing: boolean;
  syncStatusMsg: string;
  triggerSync: () => Promise<void>;
  updatePendingCount: () => void;
}

// Real bug found live 2026-09-02: this used to be a plain hook, called
// independently by both drive/page.tsx and OfflineBanner.tsx (each its
// own separate useState/useEffect instance) -- and NOWHERE else. The
// online/offline event listeners, the 10s polling loop, and triggerSync()
// only existed on whichever page happened to mount one of those two
// components, which in practice meant only /drive. A file queued offline
// from /upload (or any other page) never synced until the user happened
// to navigate to /drive -- confirmed live: went offline, uploaded a file
// (queued correctly), came back online while still on /upload, and the
// pending count stayed at 1 with no sync attempt.
//
// Fixed by making this a single Context instance mounted once in
// app/layout.tsx (OnlineStatusProvider), so the listeners/polling/sync
// logic run exactly once, application-wide, regardless of which page is
// active. useOnlineStatus() now just reads that shared instance --
// existing call sites (drive/page.tsx, OfflineBanner.tsx) needed no
// changes.
function useOnlineStatusInternal(): OnlineStatusValue {
  const [isOnline, setIsOnline] = useState<boolean>(true);
  const [pendingCount, setPendingCount] = useState<number>(0);
  const [isSyncing, setIsSyncing] = useState<boolean>(false);
  const [syncStatusMsg, setSyncStatusMsg] = useState<string>("");

  const updatePendingCount = useCallback(() => {
    setPendingCount(offlineStore.getPendingCount());
  }, []);

  const triggerSync = useCallback(async () => {
    if (isSyncing) return;
    setIsSyncing(true);
    setSyncStatusMsg("Syncing offline changes to server...");

    try {
      const res = await syncOfflineData(api);
      if (res.syncedActions > 0 || res.uploadedFiles > 0) {
        setSyncStatusMsg(`Successfully synced ${res.syncedActions} actions and ${res.uploadedFiles} files!`);
      } else if (res.errors.length > 0) {
        setSyncStatusMsg(`Sync completed with warnings: ${res.errors.join(", ")}`);
      } else {
        setSyncStatusMsg("All offline items up to date.");
      }
    } catch (err: any) {
      console.error("Auto sync error:", err);
      setSyncStatusMsg("Failed to sync offline items. Will retry.");
    } finally {
      setIsSyncing(false);
      updatePendingCount();
    }
  }, [isSyncing, updatePendingCount]);

  // Real bug found live 2026-09-03: a single failed check flipped isOnline
  // to false immediately. Under a burst of concurrent search/chat requests
  // competing for the browser's per-origin connection pool, this 4s-timeout
  // probe could itself get queued behind them and abort — even though the
  // backend was confirmed healthy throughout — incorrectly triggering the
  // blocking "Internet Connection Required" modal. Require two consecutive
  // failures before declaring offline so one contended check can't do that;
  // a single successful check still restores online status immediately.
  const consecutiveFailuresRef = useRef(0);

  // Check connectivity actively
  const checkConnectivity = useCallback(async () => {
    if (typeof window === "undefined") return;
    if (!navigator.onLine) {
      consecutiveFailuresRef.current = 0;
      setIsOnline(false);
      return;
    }

    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 6000);
      const res = await fetch(`${getBaseUrl()}/api/v1/health`, {
        method: "GET",
        headers: { "ngrok-skip-browser-warning": "true" },
        signal: controller.signal,
      });
      clearTimeout(timeoutId);

      const reachable = res.ok || res.status === 200 || res.status === 401 || res.status === 404;
      if (reachable) {
        consecutiveFailuresRef.current = 0;
        setIsOnline(true);
        if (offlineStore.getPendingCount() > 0 && !isSyncing) {
          triggerSync();
        }
      } else {
        consecutiveFailuresRef.current += 1;
        if (consecutiveFailuresRef.current >= 2) setIsOnline(false);
      }
    } catch (_) {
      consecutiveFailuresRef.current += 1;
      if (consecutiveFailuresRef.current >= 2) setIsOnline(false);
    }
  }, [isSyncing, triggerSync]);

  useEffect(() => {
    updatePendingCount();
    checkConnectivity();

    const handleOnline = () => {
      setIsOnline(true);
      checkConnectivity();
      if (offlineStore.getPendingCount() > 0) {
        triggerSync();
      }
    };

    const handleOffline = () => {
      setIsOnline(false);
    };

    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);

    const intervalId = setInterval(() => {
      updatePendingCount();
      checkConnectivity();
    }, 10000);

    return () => {
      window.removeEventListener("online", handleOnline);
      window.removeEventListener("offline", handleOffline);
      clearInterval(intervalId);
    };
  }, [checkConnectivity, triggerSync, updatePendingCount]);

  return {
    isOnline,
    pendingCount,
    isSyncing,
    syncStatusMsg,
    triggerSync,
    updatePendingCount,
  };
}

const OnlineStatusContext = createContext<OnlineStatusValue | null>(null);

export function OnlineStatusProvider({ children }: { children: ReactNode }) {
  const value = useOnlineStatusInternal();
  return createElement(OnlineStatusContext.Provider, { value }, children);
}

export function useOnlineStatus(): OnlineStatusValue {
  const ctx = useContext(OnlineStatusContext);
  if (!ctx) {
    throw new Error("useOnlineStatus() must be used within <OnlineStatusProvider> (mounted in app/layout.tsx)");
  }
  return ctx;
}
