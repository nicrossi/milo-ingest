# Embedding Configuration Guide

> **Critical Reference Document**: This configuration MUST be synchronized across both the Ingest and RAG repositories.

## Overview

The Milo system uses semantic embeddings to enable intelligent document search and retrieval. The embedding model and vector dimensions are **tightly coupled** between the ingestion pipeline and the RAG (Retrieval-Augmented Generation) service.

**⚠️ Mismatched configurations will result in:**
- Incompatible vector representations
- Meaningless similarity search results
- Database schema conflicts
- Complete system failure

---

## Required Environment Variables

### 1. EMBEDDING_MODEL

**Purpose**: Specifies the sentence-transformers model used to convert text into vector embeddings.

**Default Value**: `sentence-transformers/all-MiniLM-L6-v2`

**Requirements**:
- MUST be identical in both Ingest and RAG repositories
- MUST be a valid HuggingFace model identifier
- Model output dimension MUST match `VECTOR_DIMENSION`

**Supported Models**:

| Model Name | Dimension | Performance | Use Case |
|------------|-----------|-------------|----------|
| `sentence-transformers/all-MiniLM-L6-v2` | 384 | Fast, lightweight | General purpose, recommended |
| `sentence-transformers/all-mpnet-base-v2` | 768 | Slower, higher quality | High-precision retrieval |
| `sentence-transformers/all-MiniLM-L12-v2` | 384 | Balanced | Alternative to L6-v2 |

### 2. VECTOR_DIMENSION

**Purpose**: Defines the dimensionality of embedding vectors stored in PostgreSQL.

**Default Value**: `384`

**Requirements**:
- MUST match the output dimension of `EMBEDDING_MODEL`
- MUST match the PostgreSQL column definition: `embedding vector(N)`
- MUST be an integer value
- Cannot be changed without database migration
---

## Database Schema Requirements

The PostgreSQL `document_embeddings` table must be created with the correct vector dimension:

```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS document_embeddings (
    id SERIAL PRIMARY KEY,
    source_file TEXT NOT NULL,
    chunk_index INT NOT NULL,
    chunk_text TEXT NOT NULL,
    embedding vector(384),  -- MUST match VECTOR_DIMENSION
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_embedding ON document_embeddings
    USING hnsw (embedding vector_cosine_ops);
```

**Important**: The `embedding vector(384)` definition is **fixed at table creation time**. Changing `VECTOR_DIMENSION` requires:

1. Dropping the existing table:
   ```sql
   DROP TABLE IF EXISTS document_embeddings;
   ```

2. Recreating with new dimension:
   ```sql
   CREATE TABLE document_embeddings (
       ...
       embedding vector(768),  -- New dimension
       ...
   );
   ```

3. Re-processing all ingested documents to generate new embeddings

---

## Changing the Embedding Model

If you need to switch to a different embedding model:

### Step 1: Research Model Compatibility

Verify the new model's output dimension:
```python
from sentence_transformers import SentenceTransformer

model = SentenceTransformer("new-model-name")
dimension = model.get_sentence_embedding_dimension()
print(f"Model dimension: {dimension}")
```

### Step 2: Update Environment Variables

Update both repositories via Doppler or `.env`:
```bash
doppler secrets set EMBEDDING_MODEL="sentence-transformers/all-mpnet-base-v2" \
  --project milo-ingest --config dev

doppler secrets set VECTOR_DIMENSION="768" \
  --project milo-ingest --config dev

# Repeat for RAG repository
```

### Step 3: Migrate Database

```bash
# Connect to database
psql -U milo_user -d milo_db

# Drop existing table (⚠️ deletes all data)
DROP TABLE IF EXISTS document_embeddings;

# Recreate with new dimension
CREATE TABLE document_embeddings (
    id SERIAL PRIMARY KEY,
    source_file TEXT NOT NULL,
    chunk_index INT NOT NULL,
    chunk_text TEXT NOT NULL,
    embedding vector(768),  -- New dimension
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_embedding ON document_embeddings
    USING hnsw (embedding vector_cosine_ops);
```

### Step 4: Re-process Documents

Re-upload all documents to S3 to trigger re-ingestion with the new model.

---

## Verification Checklist

Before deploying to production, verify:

- [ ] `EMBEDDING_MODEL` is identical in Ingest and RAG
- [ ] `VECTOR_DIMENSION` is identical in Ingest and RAG
- [ ] `VECTOR_DIMENSION` matches the model's output dimension
- [ ] PostgreSQL table uses correct vector dimension
- [ ] Both services successfully connect to the database
- [ ] Integration tests pass with consistent embeddings
