CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE TYPE user_role AS ENUM ('admin', 'editor', 'viewer');
CREATE TYPE doc_status AS ENUM ('pending', 'processing', 'indexed', 'failed');
CREATE TYPE permission_level AS ENUM ('read', 'write', 'admin');
CREATE TYPE resource_type AS ENUM ('document', 'tenant', 'search');
CREATE TYPE subject_type AS ENUM ('user', 'role');

CREATE TABLE tenants (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  name TEXT NOT NULL,
  slug TEXT NOT NULL UNIQUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  email TEXT NOT NULL,
  password_hash TEXT NOT NULL,
  role user_role NOT NULL DEFAULT 'viewer',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE(tenant_id, email)
);

CREATE TABLE documents (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  current_version_id UUID,  -- FK added after document_versions
  title TEXT NOT NULL,
  doc_type TEXT,
  status doc_status NOT NULL DEFAULT 'pending',
  created_by UUID REFERENCES users(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE document_versions (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  version_number INTEGER NOT NULL DEFAULT 1,
  s3_path TEXT NOT NULL,
  file_hash TEXT NOT NULL,
  file_size_bytes BIGINT,
  original_filename TEXT,
  uploaded_by UUID REFERENCES users(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE(document_id, version_number)
);

-- Add FK now that document_versions exists
ALTER TABLE documents ADD CONSTRAINT fk_current_version
  FOREIGN KEY (current_version_id) REFERENCES document_versions(id);

CREATE TABLE chunks (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  version_id UUID NOT NULL REFERENCES document_versions(id) ON DELETE CASCADE,
  content TEXT NOT NULL,
  content_tsv TSVECTOR GENERATED ALWAYS AS (to_tsvector('english', content)) STORED,
  embedding VECTOR(1536),
  page_number INTEGER,
  chunk_index INTEGER,
  bbox JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE metadata (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  key TEXT NOT NULL,
  value JSONB NOT NULL,
  source TEXT NOT NULL DEFAULT 'llm',
  confidence_score FLOAT CHECK (confidence_score >= 0 AND confidence_score <= 1),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE permissions (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  subject_type subject_type NOT NULL,
  subject_id UUID NOT NULL,
  resource_type resource_type NOT NULL,
  resource_id UUID,  -- NULL means applies to all resources of type
  permission_level permission_level NOT NULL,
  granted_by UUID REFERENCES users(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE(subject_type, subject_id, resource_type, resource_id, permission_level)
);

CREATE TABLE audit_logs (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  actor_id UUID,
  actor_tenant_id UUID REFERENCES tenants(id),
  action TEXT NOT NULL,
  resource_type TEXT,
  resource_id UUID,
  ip_address INET,
  user_agent TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  details JSONB
);

-- B-tree on all FK columns
CREATE INDEX idx_users_tenant_id ON users(tenant_id);
CREATE INDEX idx_documents_tenant_id ON documents(tenant_id);
CREATE INDEX idx_documents_status ON documents(status);
CREATE INDEX idx_documents_created_by ON documents(created_by);
CREATE INDEX idx_document_versions_document_id ON document_versions(document_id);
CREATE INDEX idx_document_versions_uploaded_by ON document_versions(uploaded_by);
CREATE INDEX idx_chunks_document_id ON chunks(document_id);
CREATE INDEX idx_chunks_version_id ON chunks(version_id);
CREATE INDEX idx_chunks_page_number ON chunks(page_number);
CREATE INDEX idx_metadata_document_id ON metadata(document_id);
CREATE INDEX idx_metadata_key ON metadata(key);
CREATE INDEX idx_permissions_subject ON permissions(subject_type, subject_id);
CREATE INDEX idx_permissions_resource ON permissions(resource_type, resource_id);
CREATE INDEX idx_audit_logs_actor_id ON audit_logs(actor_id);
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at);
CREATE INDEX idx_audit_logs_action ON audit_logs(action);

-- HNSW index for vector ANN search
CREATE INDEX idx_chunks_embedding ON chunks USING hnsw (embedding vector_cosine_ops)
  WITH (m = 16, ef_construction = 64);

-- GIN index for full-text search
CREATE INDEX idx_chunks_content_tsv ON chunks USING GIN (content_tsv);

-- GIN indexes for JSONB columns
CREATE INDEX idx_metadata_value ON metadata USING GIN (value);
CREATE INDEX idx_chunks_bbox ON chunks USING GIN (bbox);
CREATE INDEX idx_audit_logs_details ON audit_logs USING GIN (details);

-- Enable RLS
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE document_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE chunks ENABLE ROW LEVEL SECURITY;
ALTER TABLE metadata ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE permissions ENABLE ROW LEVEL SECURITY;

-- Force RLS (ensures table owners and app roles also respect RLS policies)
ALTER TABLE documents FORCE ROW LEVEL SECURITY;
ALTER TABLE document_versions FORCE ROW LEVEL SECURITY;
ALTER TABLE chunks FORCE ROW LEVEL SECURITY;
ALTER TABLE metadata FORCE ROW LEVEL SECURITY;
ALTER TABLE audit_logs FORCE ROW LEVEL SECURITY;
ALTER TABLE permissions FORCE ROW LEVEL SECURITY;

-- Create app role (used by the backend connection)
DO $$ BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'docsearch_app') THEN
    CREATE ROLE docsearch_app;
  END IF;
END $$;

GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO docsearch_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO docsearch_app;

-- RLS Policies: tenant isolation
CREATE POLICY documents_tenant_isolation ON documents
  USING (tenant_id = current_setting('app.current_tenant_id', true)::uuid);

CREATE POLICY document_versions_tenant_isolation ON document_versions
  USING (document_id IN (
    SELECT id FROM documents WHERE tenant_id = current_setting('app.current_tenant_id', true)::uuid
  ));

CREATE POLICY chunks_tenant_isolation ON chunks
  USING (document_id IN (
    SELECT id FROM documents WHERE tenant_id = current_setting('app.current_tenant_id', true)::uuid
  ));

CREATE POLICY metadata_tenant_isolation ON metadata
  USING (document_id IN (
    SELECT id FROM documents WHERE tenant_id = current_setting('app.current_tenant_id', true)::uuid
  ));

CREATE POLICY audit_logs_tenant_isolation ON audit_logs
  USING (actor_tenant_id = current_setting('app.current_tenant_id', true)::uuid);

CREATE POLICY permissions_tenant_isolation ON permissions
  USING (subject_id IN (
    SELECT id FROM users WHERE tenant_id = current_setting('app.current_tenant_id', true)::uuid
  ));

-- Insert default tenant
INSERT INTO tenants (id, name, slug) VALUES
  ('00000000-0000-0000-0000-000000000001', 'Default Tenant', 'default')
ON CONFLICT DO NOTHING;

-- Insert admin user (password: 'changeme' — bcrypt hash)
INSERT INTO users (id, tenant_id, email, password_hash, role) VALUES
  ('00000000-0000-0000-0000-000000000002',
   '00000000-0000-0000-0000-000000000001',
   'admin@example.com',
   '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewYpwBAM7j5FqAQe',
   'admin')
ON CONFLICT DO NOTHING;
