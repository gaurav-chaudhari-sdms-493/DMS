"use client";

import { useState, useEffect, useCallback } from "react";
import { offlineStore, syncOfflineData } from "@/lib/offlineStore";
import { api, getBaseUrl } from "@/lib/api";

export function useOnlineStatus() {
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

  // Check connectivity actively
  const checkConnectivity = useCallback(async () => {
    if (typeof window === "undefined") return;
    if (!navigator.onLine) {
      setIsOnline(false);
      return;
    }

    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 4000);
      const res = await fetch(`${getBaseUrl()}/api/v1/health`, {
        method: "GET",
        headers: { "ngrok-skip-browser-warning": "true" },
        signal: controller.signal,
      });
      clearTimeout(timeoutId);

      const reachable = res.ok || res.status === 200 || res.status === 401 || res.status === 404;
      setIsOnline(reachable);

      if (reachable && offlineStore.getPendingCount() > 0 && !isSyncing) {
        triggerSync();
      }
    } catch (_) {
      setIsOnline(false);
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
