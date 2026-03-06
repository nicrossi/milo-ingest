# Local Runbook (Windows)

This runbook is the fastest reliable setup for local development on Windows.

## Services you need

Keep these running:

1. PostgreSQL (`milo-pg` on `localhost:5432`)
2. LocalStack (`S3` + `SQS` on `localhost:4566`)
3. Ingest worker (`src/main.py`)
4. Upload gateway (`src/upload_gateway.py`)

Optional (if testing full chat):

5. Orchestrator API (`uvicorn src.main:app --port 8000`)
6. Frontend (`npm start`)

## 1. Start infrastructure

```powershell
docker rm -f milo-pg localstack 2>$null

docker run -d --name milo-pg `
  -e POSTGRES_USER=postgres `
  -e POSTGRES_PASSWORD=postgres `
  -e POSTGRES_DB=milo `
  -p 5432:5432 `
  pgvector/pgvector:pg16

docker run -d --name localstack -p 4566:4566 -e SERVICES=s3,sqs localstack/localstack:latest
```

Create bucket + queue (idempotent enough for local use):

```powershell
docker run --rm -e AWS_ACCESS_KEY_ID=test -e AWS_SECRET_ACCESS_KEY=test -e AWS_DEFAULT_REGION=us-east-1 amazon/aws-cli --endpoint-url=http://host.docker.internal:4566 s3api create-bucket --bucket milo-raw-ingest-local

docker run --rm -e AWS_ACCESS_KEY_ID=test -e AWS_SECRET_ACCESS_KEY=test -e AWS_DEFAULT_REGION=us-east-1 amazon/aws-cli --endpoint-url=http://host.docker.internal:4566 sqs create-queue --queue-name milo-ingest-local
```

Queue URL used by ingest:

`http://sqs.us-east-1.localhost.localstack.cloud:4566/000000000000/milo-ingest-local`

## 2. Configure `.env` in ingest repo

Create `.env` from `.env.example` and set at least:

```env
ENV=local
AWS_REGION=us-east-1
AWS_ENDPOINT_URL=http://localhost:4566
AWS_ACCESS_KEY_ID=test
AWS_SECRET_ACCESS_KEY=test

SQS_QUEUE_URL=http://sqs.us-east-1.localhost.localstack.cloud:4566/000000000000/milo-ingest-local
DB_URL=postgresql://postgres:postgres@localhost:5432/milo

INGEST_BUCKET=milo-raw-ingest-local
UPLOAD_PREFIX=uploads
UPLOAD_GATEWAY_HOST=0.0.0.0
UPLOAD_GATEWAY_PORT=8010
UPLOAD_GATEWAY_ALLOW_ORIGIN=http://localhost:3000

EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
VECTOR_DIMENSION=384
```

## 3. Start ingest processes (2 terminals)

Terminal A (worker):

```powershell
cd C:\Users\Fede\Desktop\milo-ingest-clones\milo-ingest
.\.venv311\Scripts\python.exe src\main.py
```

Expected:

`Worker started. Listening on: ...milo-ingest-local`

Terminal B (upload gateway):

```powershell
cd C:\Users\Fede\Desktop\milo-ingest-clones\milo-ingest
.\.venv311\Scripts\python.exe src\upload_gateway.py
```

Expected:

`Upload gateway listening on http://0.0.0.0:8010 (bucket=..., sqs=http://...)`

If it shows `sqs=<disabled>`, your `.env` is missing `SQS_QUEUE_URL`.

## 4. Test upload path quickly

```powershell
Invoke-RestMethod http://localhost:8010/health
```

Then upload from frontend chat (or `test-upload.ps1`).

Gateway logs should show:

- `Uploaded to s3://...`
- `Published ingest event to SQS...`

Worker logs should show:

- `Processing s3://...`
- parse/embed/save logs

## 5. Verify embeddings in DB

```powershell
docker exec -it milo-pg psql -U postgres -d milo -c "SELECT source_file, COUNT(*) FROM document_embeddings GROUP BY source_file ORDER BY COUNT(*) DESC;"
```

## 6. Reset everything (clean slate)

Clear tables:

```powershell
docker exec -it milo-pg psql -U postgres -d milo -c "TRUNCATE TABLE chat_messages RESTART IDENTITY CASCADE; TRUNCATE TABLE document_embeddings RESTART IDENTITY;"
```

Clear S3 objects:

```powershell
docker run --rm -e AWS_ACCESS_KEY_ID=test -e AWS_SECRET_ACCESS_KEY=test -e AWS_DEFAULT_REGION=us-east-1 amazon/aws-cli --endpoint-url=http://host.docker.internal:4566 s3 rm s3://milo-raw-ingest-local --recursive
```

## 7. Common issues

1. Error tries port `5433`:
- Ensure `DB_URL` is `...:5432/milo`
- Ensure `src/main.py` prefers `DB_URL` instead of hardcoding local `5433`

2. Upload works but no embeddings:
- Gateway must show `Published ingest event to SQS`
- Worker must be running on same `SQS_QUEUE_URL`

3. Gateway runs but env not read:
- Ensure `upload_gateway.py` calls `load_dotenv()`

4. Missing Python modules:

```powershell
.\.venv311\Scripts\python.exe -m pip install -r requirements.txt
```

## 8. Optional full app (chat)

Orchestrator:

```powershell
cd C:\Users\Fede\Desktop\milo-agent-orchestrator-main
$env:DATABASE_URL="postgresql://postgres:postgres@localhost:5432/milo"
$env:GOOGLE_API_KEY="YOUR_REAL_GEMINI_KEY"
$env:RAG_SERVICE_URL="http://localhost:9999"
.\.venv311\Scripts\python.exe -m uvicorn src.main:app --host 0.0.0.0 --port 8000
```

Frontend `.env.local`:

```env
REACT_APP_USE_MOCK_API=false
REACT_APP_API_BASE_URL=http://localhost:8000
REACT_APP_WS_BASE_URL=ws://localhost:8000
REACT_APP_UPLOAD_API_URL=http://localhost:8010
```

Frontend:

```powershell
cd C:\Users\Fede\Desktop\Milo
npm start
```
