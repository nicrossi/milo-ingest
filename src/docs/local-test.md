# Ingest Pipeline: Local Test

Comprehensive guide to testing the document ingestion pipeline locally with two approaches:
1. **LocalStack Testing**: Simulate AWS S3-to-SQS event-driven processing
2. **Integration Testing**: Validate parsing, embedding, and storage with Docker

**Components:**
- **Parser**: Extracts text and structure from PDF documents using Docling
- **Embedder**: Generates semantic embeddings using sentence-transformers (384-dim)
- **Store**: Persists document chunks and embeddings to PostgreSQL with pgvector
- **Infrastructure**: LocalStack (AWS simulation) or Docker Compose (PostgreSQL)
- **Testing**: Unit tests, integration tests, and end-to-end event-driven workflows

**Technology Stack:**
- Python 3.11
- PostgreSQL 16 with pgvector extension
- Docling for document parsing
- sentence-transformers for embeddings
- Docker & Docker Compose
- LocalStack for AWS service simulation
- Terraform for infrastructure provisioning

---

## Prerequisites

### Required Tools
```bash
  # Docker & Docker Compose
  # Install Docker Desktop for macOS from https://www.docker.com/products/docker-desktop

  # Python 3.11+
  python --version

  # Doppler CLI (secrets management)
  brew install dopplerhq/cli/doppler

  # LocalStack (AWS service simulation)
  pip install localstack awscli-local terraform-local
```
---

## Test 1: LocalStack (S3/SQS Event-Driven)

Simulates the production AWS environment locally using LocalStack.
It tests the complete event-driven workflow: S3 upload → SQS notification → Worker processing.

### 1) Start LocalStack

Open a terminal and launch LocalStack:
```
localstack start
```

### 2) Deploy Infrastructure with Terraform

Navigate to the deploy directory and initialize Terraform:
```
cd deploy
tflocal init
```

Apply Terraform using local configuration:
```
tflocal apply -var-file="vars/local-us-east-1.tfvars" -auto-approve
```

**Expected output:**
```
Apply complete! Resources: X added, 0 changed, 0 destroyed.

Outputs:

bucket_id = "milo-raw-ingest-local"
queue_url = "http://localhost:4566/000000000000/milo-ingest-local"
```

### 3) Configure Doppler Secrets

Extract the SQS queue URL from Terraform outputs:
```
export QUEUE_URL=$(tflocal output -raw queue_url)
echo "Queue URL: $QUEUE_URL"
```

Update the Doppler `dev` config with the queue URL:
```
doppler secrets set SQS_QUEUE_URL="$QUEUE_URL" --project milo-ingest --config dev
```

> **Note:** To programmatically set secrets (write access), you must explicitly 
> generate a Service Token with R/W access.

Verify `SQS_QUEUE_URL` is configured:
```
doppler secrets --project milo-ingest --config dev
```

### 4) Start the Python Worker

Navigate to the source directory and start the worker using Doppler:
```
cd ../src
doppler run --project milo-ingest --config dev -- python main.py
```

**Expected output:**
```
2026-02-02 10:30:15,123 - docling-ack - INFO - Worker started. Listening on: http://localhost:4566/000000000000/milo-ingest-local
```

The worker is now polling the SQS queue every 20 seconds (long polling enabled).

### 5) Simulate File Upload to S3

In a **new terminal**, upload a test file to the S3 bucket:
```
echo "Test ingestion data" > test-file.txt

# Upload to S3 using awslocal
awslocal s3 cp test-file.txt s3://milo-raw-ingest-local/uploads/test-file.txt
```

**Expected output:**
```
upload: ./test-file.txt to s3://milo-raw-ingest-local/uploads/test-file.txt
```
**Verify the file exists:**
```bash
awslocal s3 ls s3://milo-raw-ingest-local/uploads/ --recursive
```
**Expected output:**
```
2026-02-02 10:30:45    20 uploads/test-file.txt
```

### 6) Verify SQS Message Processing

Check the worker logs - you should see the message being processed.

Verify the queue is empty (message was consumed and deleted):
```
awslocal sqs receive-message --queue-url http://localhost:4566/000000000000/milo-ingest-local --wait-time-seconds 5
```

**An empty response confirms the message was successfully processed and removed.**

### 7) Cleanup LocalStack Environment

Tear down the infrastructure:
```
cd deploy
tflocal destroy -var-file="vars/local-us-east-1.tfvars" -auto-approve
```

Stop LocalStack:
```
localstack stop
```

---

## Test 2: Integration Test (Docker + PostgreSQL)

This approach focuses on testing the document processing pipeline (parse → embed → store) 
without simulating AWS services.


### 1) Build the Docker Image

From the project root folder, build the Docker image for the ingestion service:

```bash
  docker build -t milo/ingest:latest .
```

**What happens:**
- Multi-stage build optimizes image size
- Stage 1: Installs Python dependencies including docling, torch (CPU), sentence-transformers
- Stage 2: Creates lean runtime image with only necessary files

**Verify the image:**
```bash
  docker images | grep milo/ingest
```

### 2) Start Docker Compose Services

Launch the PostgreSQL database with pgvector extension:

```bash
  docker-compose up -d
```

**Expected output:**
```
[+] Running 2/2
 ✔ Network milo-ingest_default      Created
 ✔ Container milo-postgres-dev      Started
```

**What happens:**
- PostgreSQL 16 with pgvector extension starts on port 5433
- Database initialization script (`init-db.sql`) creates:
  - `vector` extension
  - `document_embeddings` table with 384-dimensional vector column
  - HNSW index for fast similarity search
- Health check ensures database is ready before proceeding

**Check database logs (optional):**
```bash
  docker-compose logs postgres
```

### 3) Configure Environment Variables

The integration test requires database connection details. Set them via `.env` file:

Create a `.env` file in the project root:

```
cat > .env << EOF
POSTGRES_USER=milo_user
POSTGRES_PASSWORD=milo_password
POSTGRES_DB=milo_db
POSTGRES_CONTAINER_NAME=milo-postgres-dev
EOF
```

### 4) Run the Integration Test

The integration test validates the complete pipeline: parse → chunk → embed → store → verify.

```bash
  docker run --rm \
  --network host \
  -v $(pwd):/app \
  -w /app \
  -e PYTHONPATH=/app \
  milo/ingest:latest \
  python tests/integration/integration_test.py
```

**Expected output:**
```
2026-02-02 14:30:01,123 - integration_test - INFO - Downloading test PDF from https://github.com/mozilla/pdf.js/raw/master/test/pdfs/tracemonkey.pdf
2026-02-02 14:30:03,456 - integration_test - INFO - Starting integration pipeline
2026-02-02 14:30:05,789 - integration_test - INFO - Parsed 98234 characters
2026-02-02 14:30:06,012 - integration_test - INFO - Generated 87 chunks
2026-02-02 14:30:12,345 - integration_test - INFO - Generated 87 vectors
2026-02-02 14:30:12,567 - integration_test - INFO - Data persisted to database
2026-02-02 14:30:12,890 - integration_test - INFO - Found 87 rows for tracemonkey.pdf
2026-02-02 14:30:12,923 - integration_test - INFO - Vector verification passed (Distance: 0.000000)
2026-02-02 14:30:12,925 - integration_test - INFO - Integration test passed successfully
```

**What the test does:**
1. **Downloads** test PDF (tracemonkey.pdf from Mozilla)
2. **Parses** PDF to Markdown using Docling
3. **Chunks** text into semantic segments
4. **Embeds** each chunk using sentence-transformers (384-dim vectors)
5. **Stores** chunks and vectors in PostgreSQL
6. **Verifies** data integrity via vector similarity query


### 5) Verify Database Content

Connect to the PostgreSQL database and inspect the stored data:

```bash
  docker exec -it milo-db-local psql -U milo_user -d milo_db
```

**Query examples:**
```sql
-- Count total embeddings
SELECT COUNT(*) FROM document_embeddings;

-- View first 3 chunks
SELECT id, source_file, chunk_index, LEFT(chunk_text, 80) as preview
FROM document_embeddings
ORDER BY chunk_index
LIMIT 3;

```
### 6) Cleanup

Stop and remove all services:

```bash
# Stop services
docker-compose down

# Remove volumes (deletes all database data)
docker-compose down -v

# Remove downloaded test files
rm -f tracemonkey.pdf
```



