export interface LoginRequest {
  email: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface DocumentUploadResponse {
  document_id: string;
  version_id: string;
  title: string;
  status: string;
  created_at: string;
}

export interface SearchResult {
  document_id: string;
  document_name: string;
  download_url: string;
  page_number: number | null;
  snippet: string;
  score: number;
  metadata: Record<string, unknown>;
}

export interface SearchResponse {
  query: string;
  ai_summary: string;
  results: SearchResult[];
  cached: boolean;
  took_ms: number;
}
