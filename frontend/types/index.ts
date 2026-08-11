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

export interface Folder {
  id: string;
  name: string;
  parent_id?: string | null;
  tenant_id: string;
  created_by?: string | null;
  created_at: string;
  updated_at: string;
  is_starred: boolean;
  is_trashed: boolean;
  trashed_at?: string | null;
  color?: string;
}

export interface FolderTreeNode {
  id: string;
  name: string;
  parent_id?: string | null;
  color?: string;
  subfolders?: FolderTreeNode[];
  children?: FolderTreeNode[];
}

export interface DocumentListItem {
  id: string;
  title: string;
  doc_type?: string | null;
  status: string;
  created_at: string;
  folder_id?: string | null;
  is_starred: boolean;
  is_trashed: boolean;
  trashed_at?: string | null;
  file_size_bytes: number;
  current_version_id?: string | null;
  s3_path?: string | null;
  download_url?: string | null;
}

export interface DocumentDetailResponse {
  document_id: string;
  title: string;
  doc_type?: string | null;
  status: string;
  created_at: string;
  folder_id?: string | null;
  is_starred: boolean;
  is_trashed: boolean;
  trashed_at?: string | null;
  current_version?: {
    id: string;
    version: number;
    s3_path: string;
    file_size_bytes: number;
    download_url: string;
    created_at: string;
  } | null;
  metadata: Array<{
    key: string;
    value: string;
    source: string;
    confidence_score: number;
  }>;
  versions: Array<{
    id: string;
    version: number;
    s3_path: string;
    file_size_bytes: number;
    download_url: string;
    created_at: string;
  }>;
}

export interface DriveStats {
  total_files: number;
  total_folders: number;
  total_size_bytes: number;
  total_starred: number;
  total_trashed: number;
}

export interface SearchResult {
  document_id: string;
  document_name: string;
  download_url: string;
  page_number: number | null;
  snippet: string;
  score: number;
  tags?: string[];
  metadata: Record<string, unknown>;
}

export interface SearchResponse {
  query: string;
  ai_summary: string;
  results: SearchResult[];
  cached: boolean;
  took_ms: number;
  search_mode?: string;
  hyde_triggered?: boolean;
}

export interface ChatMessage {
  id: string;
  session_id: string;
  role: "user" | "assistant";
  content: string;
  results?: SearchResult[] | null;
  filters?: Record<string, any> | null;
  search_mode?: string;
  created_at: string;
}

export interface ChatSessionListItem {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  message_count: number;
}

export interface ChatSession {
  id: string;
  tenant_id: string;
  user_id: string;
  title: string;
  created_at: string;
  updated_at: string;
  messages: ChatMessage[];
}

