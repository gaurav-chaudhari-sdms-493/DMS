import { getAccessToken } from "./auth";
import type { Folder, FolderTreeNode, DocumentListItem, DocumentDetailResponse, DriveStats, SearchResponse } from "@/types";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function request(path: string, options: RequestInit = {}): Promise<any> {
  const headers = new Headers(options.headers || {});
  
  const token = getAccessToken();
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  
  if (!(options.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  
  const response = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers,
  });
  
  if (!response.ok) {
    if (response.status === 401) {
      if (typeof window !== "undefined") {
        localStorage.removeItem("access_token");
        localStorage.removeItem("refresh_token");
        window.location.href = "/login";
      }
    }
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

  return response.json();
}

export const api = {
  auth: {
    login: async (email: string, password: string): Promise<any> => {
      return await request("/api/v1/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });
    },
  },
  search: {
    query: async (query: string, limit: number = 5, filters: any = null): Promise<SearchResponse> => {
      return await request("/api/v1/search/", {
        method: "POST",
        body: JSON.stringify({ query, limit, filters }),
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
      return await request(`/api/v1/folders?${q.toString()}`);
    },
    get: async (folderId: string): Promise<Folder> => {
      return await request(`/api/v1/folders/${folderId}`);
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
      return await request(`/api/v1/documents?${q.toString()}`);
    },
    get: async (documentId: string): Promise<DocumentDetailResponse> => {
      return await request(`/api/v1/documents/${documentId}`);
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
    getStats: async (): Promise<DriveStats> => {
      return await request("/api/v1/documents/drive/stats");
    },
  },
};