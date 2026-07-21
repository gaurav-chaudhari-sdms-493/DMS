import { getAccessToken } from "./auth";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getAccessToken();
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string>),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  // Set JSON content-type if body is JSON string and header not set
  if (options.body && typeof options.body === "string" && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json";
  }

  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  });

  if (res.status === 401 && typeof window !== "undefined") {
    // Redirect to login on token invalid/expired
    if (!window.location.pathname.startsWith("/login")) {
      window.location.href = "/login";
    }
  }

  if (!res.ok) {
    const errorText = await res.text();
    try {
      const errJson = JSON.parse(errorText);
      throw new Error(errJson.detail || errJson.message || "API request failed");
    } catch {
      throw new Error(errorText || `Request failed with status ${res.status}`);
    }
  }

  return res.json() as Promise<T>;
}

export const api = {
  auth: {
    login: async (email: string, password: string): Promise<{ access_token: string; refresh_token: string }> => {
      return apiFetch("/api/v1/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });
    },
    refresh: async (refreshToken: string): Promise<{ access_token: string; refresh_token: string }> => {
      return apiFetch("/api/v1/auth/refresh", {
        method: "POST",
        body: JSON.stringify({ refresh_token: refreshToken }),
      });
    },
  },
  documents: {
    upload: async (file: File): Promise<{ document_id: string; version_id: string; title: str; status: str }> => {
      const formData = new FormData();
      formData.append("file", file);

      return apiFetch("/api/v1/documents", {
        method: "POST",
        body: formData,
      });
    },
    get: async (id: string): Promise<any> => {
      return apiFetch(`/api/v1/documents/${id}`);
    },
  },
  search: {
    query: async (query: string, limit: number = 5, filters?: object): Promise<any> => {
      return apiFetch("/api/v1/search", {
        method: "POST",
        body: JSON.stringify({ query, limit, filters }),
      });
    },
  },
};