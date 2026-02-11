# Milo Ingest Pipeline

> Event-driven S3-to-SQS ingestion pipeline with AWS infrastructure provisioned via Terraform

## Overview

The **Milo Ingest Pipeline** is a data ingestion system that automatically processes files uploaded to S3. 
When a file is uploaded, S3 triggers an event notification to SQS, and a Python consumer worker processes the messages in real-time.

## Architecture
### Diagram
<div style="text-align: center;">
  <img src="/docs/milo-ingest-overview-diagram.png" alt="Milo Ingest Architecture Diagram" width="800" />
</div>

### Pipeline Flow
```
┌─────────────┐     ┌──────────────┐     ┌────────────┐     ┌──────────────┐
│   S3 Bucket │────▶│  SQS Queue   │────▶│   Worker   │────▶│  PostgreSQL  │
│  (PDF file) │     │ (S3 Events)  │     │  (Docker)  │     │  + pgvector  │
└─────────────┘     └──────────────┘     └────────────┘     └──────────────┘
                                               │
                                               ▼
                                    ┌──────────────────────┐
                                    │  1. Parse (Docling)  │
                                    │  2. Chunk (sliding)  │
                                    │  3. Embed (ST)       │
                                    │  4. Store (pgvector) │
                                    └──────────────────────┘
```

### Components

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Parser** | Docling | Extract structured text and tables from PDFs |
| **Embedder** | sentence-transformers | Generate 384-dim semantic vectors |
| **Store** | PostgreSQL + pgvector | Persist and search vector embeddings |
| **Container** | Docker | Package dependencies and runtime |
| **Orchestration** | Docker Compose | Manage local database infrastructure |
| **AWS Simulation** | LocalStack | Test S3/SQS event-driven workflows |

---

## ⚠️ Critical Configuration

**The following environment variables MUST match exactly across both the Ingest and RAG repositories:**

**See [embedding_config.md](src/docs/embedding_config.md) for complete configuration guide**

### Required Environment Variables

| Variable | Default Value | Description |
|----------|---------------|-------------|
| `EMBEDDING_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` | The sentence-transformer model used to generate embeddings |
| `VECTOR_DIMENSION` | `384` | The dimension of the embedding vectors (must match model output) |

**Why this matters:**
- If the Ingest service uses a different embedding model than the RAG service, vector similarity searches will produce meaningless results
- The `VECTOR_DIMENSION` must match the PostgreSQL column definition: `embedding vector(384)`
- Both services must be configured identically via Doppler or environment variables

**To configure via Doppler:**
```bash
doppler secrets set EMBEDDING_MODEL="sentence-transformers/all-MiniLM-L6-v2" --project milo-ingest --config dev
doppler secrets set VECTOR_DIMENSION="384" --project milo-ingest --config dev
```

> **Note:** If you change the embedding model, you must update both variables, drop/recreate the database table, and re-process all documents.

---
### Prerequisites
- **Python 3.11+**
- **Terraform 1.5+** (or `terraform-local` for LocalStack)
- **AWS CLI** (or `awslocal` for LocalStack)
- **Doppler CLI** (for secret management)
- **Docker** (optional, for containerized deployment)

---
## Test
### Unit test: Pytest
From project root folder, 
Test individual components without external dependencies:

```bash
  # Run all unit tests
  python -m pytest tests/ -v

  # Run specific test modules
  python -m pytest tests/test_parser.py -v
```

### Integration test: Docker and LocalStack

For a local test, follow the **[Local Test Guide](src/docs/local-test.md)**:

---

## Deployment

### Configure Doppler Secrets

Set up your Doppler project and generate a service token. See **[Doppler Setup Guide](deploy/docs/doppler_setup.md)**.

---
## Resources

- **Docling Documentation**: https://github.com/DS4SD/docling
- **pgvector Guide**: https://github.com/pgvector/pgvector
- **sentence-transformers**: https://www.sbert.net/
- **Docker Compose**: https://docs.docker.com/compose/
- **LocalStack**: https://docs.localstack.cloud/
- **Doppler Secrets**: https://docs.doppler.com/
