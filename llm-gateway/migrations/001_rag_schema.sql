-- RAG schema: documents, chunks, and HNSW vector index
-- Runs automatically on first postgres container start via /docker-entrypoint-initdb.d

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "pgcrypto";  -- gen_random_uuid()

-- -----------------------------------------------------------------------
-- documents: one row per uploaded file
-- -----------------------------------------------------------------------
CREATE TABLE documents (
    id            UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    filename      TEXT        NOT NULL,
    content_type  TEXT        NOT NULL DEFAULT 'application/pdf',
    size_bytes    BIGINT,
    -- object key in MinIO (bucket/id/filename)
    storage_key   TEXT        NOT NULL,
    -- pending → processing → ready | failed
    status        TEXT        NOT NULL DEFAULT 'pending'
                                CHECK (status IN ('pending','processing','ready','failed')),
    error_message TEXT,
    chunk_count   INTEGER,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- -----------------------------------------------------------------------
-- chunks: one row per text chunk extracted from a document
-- embedding dim = 1536 (text-embedding-3-small)
-- -----------------------------------------------------------------------
CREATE TABLE chunks (
    id            UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id   UUID        NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index   INTEGER     NOT NULL,
    content       TEXT        NOT NULL,
    token_count   INTEGER,
    embedding     vector(1536),
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX chunks_document_id_idx ON chunks(document_id);

-- HNSW index for fast cosine-similarity search
-- m=16, ef_construction=64 is a solid production default
CREATE INDEX chunks_embedding_hnsw_idx ON chunks
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- -----------------------------------------------------------------------
-- Automatically update documents.updated_at on every row update
-- -----------------------------------------------------------------------
CREATE OR REPLACE FUNCTION touch_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;

CREATE TRIGGER documents_updated_at
    BEFORE UPDATE ON documents
    FOR EACH ROW EXECUTE FUNCTION touch_updated_at();
