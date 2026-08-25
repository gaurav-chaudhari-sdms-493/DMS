import { getAccessToken, getUserProfile, setUserProfile, clearTokens } from "./auth";
import { offlineStore } from "./offlineStore";
import type { Folder, FolderTreeNode, DocumentListItem, DocumentDetailResponse, DriveStats, SearchResponse, ChatSession, ChatMessage, ChatSessionListItem } from "@/types";

export const getBaseUrl = (): string => {
  if (typeof window !== "undefined") {
    const custom = localStorage.getItem("custom_backend_url");
    if (custom && custom.trim() !== "") {
      return custom.trim().replace(/\/+$/, "");
    }
  }
  let url = process.env.NEXT_PUBLIC_API_URL || "https://aa0d-103-226-171-223.ngrok-free.app";
  if (typeof window !== "undefined") {
    // If in browser and URL points to internal docker service name 'backend', use default ngrok URL
    if (url.includes("backend:8000")) {
      url = "https://aa0d-103-226-171-223.ngrok-free.app";
    }
  }
  return url.replace(/\/+$/, "");
};

export const setCustomBaseUrl = (url: string): void => {
  if (typeof window !== "undefined") {
    const cleaned = url.trim().replace(/\/+$/, "");
    if (cleaned) {
      localStorage.setItem("custom_backend_url", cleaned);
    } else {
      localStorage.removeItem("custom_backend_url");
    }
  }
};

export const testBackendConnection = async (targetUrl: string): Promise<{ success: boolean; message: string }> => {
  let cleaned = targetUrl.trim().replace(/\/+$/, "");
  if (!cleaned.startsWith("http://") && !cleaned.startsWith("https://")) {
    cleaned = `https://${cleaned}`;
  }
  
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 6000);
  
  try {
    const res = await fetch(`${cleaned}/api/v1/health`, {
      method: "GET",
      headers: {
        "ngrok-skip-browser-warning": "true",
      },
      signal: controller.signal,
    });
    clearTimeout(timeoutId);
    if (res.ok || res.status === 200) {
      setCustomBaseUrl(cleaned);
      return { success: true, message: `Connected successfully! Active backend set to: ${cleaned}` };
    } else if (res.status === 404 || res.status === 401) {
      setCustomBaseUrl(cleaned);
      return { success: true, message: `Server reached (status ${res.status}). Active backend set to: ${cleaned}` };
    } else {
      return { success: false, message: `Server returned error status ${res.status}` };
    }
  } catch (err: any) {
    clearTimeout(timeoutId);
    if (err.name === "AbortError") {
      return { success: false, message: "Connection timed out (6s). Please check if ngrok/backend is running." };
    }
    return { success: false, message: err.message || "Failed to connect to backend server address." };
  }
};

async function request(path: string, options: RequestInit = {}): Promise<any> {
  const headers = new Headers(options.headers || {});
  headers.set("ngrok-skip-browser-warning", "true");
  
  const token = getAccessToken();
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  
  if (!(options.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  
  const baseUrl = getBaseUrl();
  const method = (options.method || "GET").toUpperCase();

  let response: Response;
  try {
    response = await fetch(`${baseUrl}${path}`, {
      ...options,
      headers,
    });
  } catch (networkError) {
    if (method === "GET") {
      if (path.includes("/folders/tree")) {
        return offlineStore.getFolderTree();
      }
      if (path.includes("/documents/stats")) {
        return offlineStore.getStats();
      }
      if (path.includes("/auth/me") || path.includes("/users/me") || path.includes("/profile")) {
        return getUserProfile() || { full_name: "Offline User", email: "user@offline.local", role: "user" };
      }
      if (path.includes("/documents")) {
        const urlObj = new URL(`http://dummy.local${path}`);
        const folderId = urlObj.searchParams.get("folder_id");
        return offlineStore.getDocuments(folderId);
      }
    }
    throw new Error("Network unreachable. Working in Offline Mode.");
  }

  if (response.status === 401 && !path.includes("/auth/login") && !path.includes("/auth/refresh")) {
    const refreshToken = typeof window !== "undefined" ? localStorage.getItem("refresh_token") : null;
    let refreshed = false;
    if (refreshToken) {
      try {
        const refreshRes = await fetch(`${baseUrl}/api/v1/auth/refresh`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "ngrok-skip-browser-warning": "true",
          },
          body: JSON.stringify({ refresh_token: refreshToken }),
        });
        if (refreshRes.ok) {
          const data = await refreshRes.json();
          if (data.access_token) {
            localStorage.setItem("access_token", data.access_token);
            if (data.refresh_token) {
              localStorage.setItem("refresh_token", data.refresh_token);
            }
            headers.set("Authorization", `Bearer ${data.access_token}`);
            response = await fetch(`${baseUrl}${path}`, {
              ...options,
              headers,
            });
            refreshed = true;
          }
        }
      } catch (e) {
        console.error("Auto-refresh token failed", e);
      }
    }
    // Both the access token and the refresh token are invalid (expired,
    // corrupted, or from a stale session). Without this, the app would
    // keep retrying a dead refresh token on every request forever, with
    // every screen silently failing and no way for the user to recover
    // short of manually clearing browser storage.
    if (!refreshed) {
      clearTokens();
      if (typeof window !== "undefined") {
        window.location.href = "/login";
      }
      throw new Error("Session expired. Please log in again.");
    }
  }

  if (!response.ok) {
    let errorDetail = "Request failed";
    try {
      const errJson = await response.json();
      errorDetail = errJson.detail || JSON.stringify(errJson);
    } catch (_) {
      try {
        errorDetail = await response.text();
      } catch (__) {}
    }
    throw new Error(errorDetail);
  }
  
  if (response.status === 204) {
    return null;
  }

  const data = await response.json();

  if (method === "GET") {
    if (path.includes("/folders/tree")) {
      offlineStore.saveFolderTree(data);
    } else if (path.includes("/documents/stats")) {
      offlineStore.saveStats(data);
    } else if (path.includes("/auth/me") || path.includes("/users/me") || path.includes("/profile")) {
      setUserProfile(data);
    } else if (path.includes("/documents") && Array.isArray(data)) {
      const urlObj = new URL(`http://dummy.local${path}`);
      const folderId = urlObj.searchParams.get("folder_id");
      offlineStore.saveDocuments(folderId, data);
    }
  }

  return data;
}

export const api = {
  auth: {
    login: async (email: string, password: string): Promise<any> => {
      return await request("/api/v1/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });
    },
    signUp: async (fullName: string, email: string, password: string): Promise<any> => {
      return await request("/api/v1/auth/sign-up", {
        method: "POST",
        body: JSON.stringify({ full_name: fullName, email, password }),
      });
    },
    forgotPassword: async (email: string): Promise<any> => {
      return await request("/api/v1/auth/forgot-password", {
        method: "POST",
        body: JSON.stringify({ email }),
      });
    },
    resetPassword: async (email: string, resetToken: string, newPassword: string): Promise<any> => {
      return await request("/api/v1/auth/reset-password", {
        method: "POST",
        body: JSON.stringify({ email, reset_token: resetToken, new_password: newPassword }),
      });
    },
    getProfile: async (): Promise<any> => {
      return await request("/api/v1/auth/me", {
        method: "GET",
      });
    },
    logout: (): void => {
      clearTokens();
      if (typeof window !== "undefined") {
        window.location.href = "/login";
      }
    },
  },


  connectors: {
    getInfo: async (): Promise<any> => {
      return await request("/api/v1/connectors/info", {
        method: "GET",
      });
    },
  },
  facts: {
    get: async (factId: string): Promise<any> => {
      return await request(`/api/v1/facts/${factId}`, {
        method: "GET",
      });
    },
    // T51/T52 — the adjudication queue: 'low_confidence' is any in_review
    // fact; 'handwritten' filters on is_handwritten (nothing sets that yet,
    // T30 isn't built, but the category is ready). 'marginalia' and
    // 'join_mismatch' 501 on the backend — not built yet, not silently empty.
    getQueue: async (category: string = "low_confidence", limit: number = 50, offset: number = 0): Promise<any> => {
      return await request(`/api/v1/facts/queue?category=${encodeURIComponent(category)}&limit=${limit}&offset=${offset}`, {
        method: "GET",
      });
    },
    claim: async (factId: string): Promise<any> => {
      return await request(`/api/v1/facts/${factId}/claim`, { method: "POST" });
    },
    release: async (factId: string): Promise<any> => {
      return await request(`/api/v1/facts/${factId}/release`, { method: "POST" });
    },
    confirm: async (factId: string): Promise<any> => {
      return await request(`/api/v1/facts/${factId}/confirm`, { method: "POST" });
    },
    bulkConfirm: async (corpusFolderId: string, threshold: number, policyVersion: string): Promise<any> => {
      const params = new URLSearchParams({
        corpus_folder_id: corpusFolderId,
        threshold: String(threshold),
        policy_version: policyVersion,
      });
      return await request(`/api/v1/facts/bulk-confirm?${params.toString()}`, { method: "POST" });
    },
  },
  governance: {
    // T76 — completeness/reconciliation dashboard, gap-scored per corpus (folder).
    getCompleteness: async (corpusFolderId: string): Promise<any> => {
      return await request(`/api/v1/governance/completeness/${corpusFolderId}`, { method: "GET" });
    },
    getCompletenessDrill: async (corpusFolderId: string, category: string): Promise<any> => {
      return await request(`/api/v1/governance/completeness/${corpusFolderId}/drill?category=${encodeURIComponent(category)}`, { method: "GET" });
    },
  },
  entities: {
    // T62 — one entity, everything about it: records (current + original
    // state), linked entities/facts with tier and confirmation status.
    get360: async (nodeId: string): Promise<any> => {
      return await request(`/api/v1/entities/${nodeId}/360`, { method: "GET" });
    },
  },
  records: {
    // T60/T62 — base entry + every amendment, in order: the record's
    // full "versions" view, each entry citing its own source page.
    getHistory: async (recordId: string): Promise<any> => {
      return await request(`/api/v1/records/${recordId}/history`, { method: "GET" });
    },
  },
  search: {
    query: async (
      query: string,
      limit: number = 5,
      filters: any = null,
      rerankProvider: "cohere" | "bgem3" | null = null,
      generateSummary: boolean = true
    ): Promise<SearchResponse> => {
      return await request("/api/v1/search/", {
        method: "POST",
        body: JSON.stringify({
          query,
          limit,
          filters,
          rerank_provider: rerankProvider,
          generate_summary: generateSummary,
        }),
      });
    },
  },
  chat: {
    listSessions: async (): Promise<ChatSessionListItem[]> => {
      return await request("/api/v1/chat/sessions");
    },
    createSession: async (title?: string, initialQuery?: string): Promise<ChatSession> => {
      return await request("/api/v1/chat/sessions", {
        method: "POST",
        body: JSON.stringify({ title, initial_query: initialQuery }),
      });
    },
    getSession: async (sessionId: string): Promise<ChatSession> => {
      return await request(`/api/v1/chat/sessions/${sessionId}`);
    },
    sendMessage: async (sessionId: string, query: string, filters?: any): Promise<ChatMessage> => {
      return await request(`/api/v1/chat/sessions/${sessionId}/messages`, {
        method: "POST",
        body: JSON.stringify({ query, filters }),
      });
    },
    updateSessionTitle: async (sessionId: string, title: string): Promise<ChatSession> => {
      return await request(`/api/v1/chat/sessions/${sessionId}`, {
        method: "PATCH",
        body: JSON.stringify({ title }),
      });
    },
    deleteSession: async (sessionId: string): Promise<void> => {
      return await request(`/api/v1/chat/sessions/${sessionId}`, {
        method: "DELETE",
      });
    },
  },
  folders: {
    create: async (name: string, parentId?: string | null, color?: string): Promise<Folder> => {
      return await request("/api/v1/folders", {
        method: "POST",
        body: JSON.stringify({ name, parent_id: parentId || null, color }),
      });
    },
    list: async (params?: { parent_id?: string | null; include_root?: boolean; is_starred?: boolean; is_trashed?: boolean }): Promise<Folder[]> => {
      const q = new URLSearchParams();
      if (params?.parent_id) q.set("parent_id", params.parent_id);
      if (params?.include_root) q.set("include_root", "true");
      if (params?.is_starred !== undefined) q.set("is_starred", String(params.is_starred));
      if (params?.is_trashed !== undefined) q.set("is_trashed", String(params.is_trashed));
      try {
        return await request(`/api/v1/folders?${q.toString()}`);
      } catch (e) {
        const tree = offlineStore.getFolderTree();
        return (tree || []).map((t) => ({
          id: t.id,
          name: t.name,
          parent_id: t.parent_id,
          tenant_id: "local",
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
          is_starred: false,
          is_trashed: false,
        }));
      }
    },
    get: async (folderId: string): Promise<Folder> => {
      try {
        return await request(`/api/v1/folders/${folderId}`);
      } catch (e) {
        const tree = offlineStore.getFolderTree();
        const found = tree?.find((t) => t.id === folderId);
        return {
          id: folderId,
          name: found ? found.name : "Folder",
          parent_id: found ? found.parent_id : null,
          tenant_id: "local",
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
          is_starred: false,
          is_trashed: false,
        };
      }
    },
    getTree: async (): Promise<FolderTreeNode[]> => {
      return await request("/api/v1/folders/tree");
    },
    update: async (folderId: string, data: { name?: string; parent_id?: string | null; color?: string }): Promise<Folder> => {
      return await request(`/api/v1/folders/${folderId}`, {
        method: "PATCH",
        body: JSON.stringify(data),
      });
    },
    toggleStar: async (folderId: string): Promise<Folder> => {
      return await request(`/api/v1/folders/${folderId}/star`, {
        method: "POST",
      });
    },
    toggleTrash: async (folderId: string): Promise<Folder> => {
      return await request(`/api/v1/folders/${folderId}/trash`, {
        method: "POST",
      });
    },
    deletePermanent: async (folderId: string): Promise<void> => {
      return await request(`/api/v1/folders/${folderId}`, {
        method: "DELETE",
      });
    },
  },
  documents: {
    // T23 — the classification queue, same shape as the fact adjudication queue.
    getUnclassifiedQueue: async (limit: number = 50, offset: number = 0): Promise<any> => {
      return await request(`/api/v1/documents/queue/unclassified?limit=${limit}&offset=${offset}`, {
        method: "GET",
      });
    },
    upload: async (file: File, folderId?: string | null): Promise<any> => {
      const formData = new FormData();
      formData.append("file", file);
      const url = folderId ? `/api/v1/documents/?folder_id=${folderId}` : "/api/v1/documents/";
      return await request(url, {
        method: "POST",
        body: formData,
      });
    },
    uploadBulk: async (files: File[], folderId?: string | null): Promise<any> => {
      const formData = new FormData();
      files.forEach((file) => {
        formData.append("files", file);
      });
      const url = folderId ? `/api/v1/documents/bulk?folder_id=${folderId}` : "/api/v1/documents/bulk";
      return await request(url, {
        method: "POST",
        body: formData,
      });
    },
    list: async (params?: { folder_id?: string | null; include_all?: boolean; is_starred?: boolean; is_trashed?: boolean }): Promise<DocumentListItem[]> => {
      const q = new URLSearchParams();
      if (params?.folder_id) q.set("folder_id", params.folder_id);
      if (params?.include_all) q.set("include_all", "true");
      if (params?.is_starred !== undefined) q.set("is_starred", String(params.is_starred));
      if (params?.is_trashed !== undefined) q.set("is_trashed", String(params.is_trashed));
      try {
        return await request(`/api/v1/documents?${q.toString()}`);
      } catch (e) {
        return offlineStore.getDocuments(params?.folder_id);
      }
    },
    get: async (documentId: string): Promise<DocumentDetailResponse> => {
      try {
        return await request(`/api/v1/documents/${documentId}`);
      } catch (e) {
        return (
          offlineStore.getDocumentDetail(documentId) || {
            document_id: documentId,
            title: "Document",
            file_path: "",
            download_url: "",
            file_size_bytes: 0,
            mime_type: "application/octet-stream",
            status: "indexed",
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
            metadata: [],
            versions: [],
          }
        );
      }
    },
    update: async (documentId: string, data: { title?: string; folder_id?: string | null }): Promise<DocumentListItem> => {
      return await request(`/api/v1/documents/${documentId}`, {
        method: "PATCH",
        body: JSON.stringify(data),
      });
    },
    toggleStar: async (documentId: string): Promise<DocumentListItem> => {
      return await request(`/api/v1/documents/${documentId}/star`, {
        method: "POST",
      });
    },
    toggleTrash: async (documentId: string): Promise<DocumentListItem> => {
      return await request(`/api/v1/documents/${documentId}/trash`, {
        method: "POST",
      });
    },
    deletePermanent: async (documentId: string): Promise<void> => {
      return await request(`/api/v1/documents/${documentId}`, {
        method: "DELETE",
      });
    },
    cleanupTrash: async (retentionDays: number = 30): Promise<any> => {
      return await request(`/api/v1/documents/trash/cleanup?retention_days=${retentionDays}`, {
        method: "POST",
      });
    },
    getStats: async (): Promise<DriveStats> => {
      return await request("/api/v1/documents/drive/stats");
    },
  },
  admin: {
    getAnalytics: async (): Promise<any> => {
      return await request("/api/v1/admin/analytics");
    },
    getApiAnalytics: async (): Promise<any> => {
      return await request("/api/v1/admin/api-analytics");
    },
  },
};