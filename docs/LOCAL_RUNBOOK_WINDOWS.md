Terminal 1 (Infra: Postgres + LocalStack + bucket + queue)

docker rm -f milo-pg localstack 2>$null
docker run -d --name milo-pg -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=milo -p 5432:5432 pgvector/pgvector:pg16
docker run -d --name localstack -p 4566:4566 -e SERVICES=s3,sqs localstack/localstack:latest
docker run --rm -e AWS_ACCESS_KEY_ID=test -e AWS_SECRET_ACCESS_KEY=test -e AWS_DEFAULT_REGION=us-east-1 amazon/aws-cli --endpoint-url=http://host.docker.internal:4566 s3api create-bucket --bucket milo-raw-ingest-local
docker run --rm -e AWS_ACCESS_KEY_ID=test -e AWS_SECRET_ACCESS_KEY=test -e AWS_DEFAULT_REGION=us-east-1 amazon/aws-cli --endpoint-url=http://host.docker.internal:4566 sqs create-queue --queue-name milo-ingest-local

Terminal 2 (Ingest Worker)

cd C:\Users\Fede\Desktop\milo-ingest-clones\milo-ingest
.\.venv311\Scripts\python.exe src\main.py

Terminal 3 (Upload Gateway)

cd C:\Users\Fede\Desktop\milo-ingest-clones\milo-ingest
.\.venv311\Scripts\python.exe src\upload_gateway.py

Terminal 4 (Orchestrator)

cd C:\Users\Fede\Desktop\milo-agent-orchestrator-main
.\.venv311\Scripts\python.exe -m uvicorn src.main:app --host 0.0.0.0 --port 8000

Terminal 5 (Frontend)

cd C:\Users\Fede\Desktop\Milo
npm start