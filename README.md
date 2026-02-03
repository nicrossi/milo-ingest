# Milo Ingest Pipeline

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> Event-driven S3-to-SQS ingestion pipeline with AWS infrastructure provisioned via Terraform

## Overview

The **Milo Ingest Pipeline** is a serverless data ingestion system that automatically processes files uploaded to S3. 
When a file is uploaded, S3 triggers an event notification to SQS, and a Python consumer worker processes the messages in real-time.

## Architecture

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
