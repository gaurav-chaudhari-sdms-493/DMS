import { getAccessToken } from "./auth";

const BASE_URL = "http://localhost:8000";

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
    query: async (query: string, limit: number = 5, filters: any = null): Promise<any> => {
      return await request("/api/v1/search/", {
        method: "POST",
        body: JSON.stringify({ query, limit, filters }),
      });
    },
  },
  documents: {
    upload: async (file: File): Promise<any> => {
      const formData = new FormData();
      formData.append("file", file);
      return await request("/api/v1/documents/", {
        method: "POST",
        body: formData,
      });
    },
  },
};