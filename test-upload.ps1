# Test script to verify upload gateway works with LocalStack
# Run this after starting all services

Write-Host "Testing upload gateway..."

# Create a test file
"Test document content for ingestion pipeline." | Out-File -FilePath "test-file.txt" -Encoding UTF8

# Test upload via curl (you need curl installed)
# curl -X POST http://localhost:8010/upload -F "file=@test-file.txt" -F "session_id=test-session"

Write-Host "Test file created. Use this curl command to test:"
Write-Host 'curl -X POST http://localhost:8010/upload -F "file=@test-file.txt" -F "session_id=test-session"'

# Check health endpoint
Write-Host "Checking gateway health..."
try {
    $health = Invoke-WebRequest -Uri "http://localhost:8010/health" -UseBasicParsing
    Write-Host "Gateway health: $($health.Content)"
} catch {
    Write-Host "Gateway not responding: $($_.Exception.Message)"
}

# Check if file was uploaded to S3
Write-Host "Checking S3 bucket contents..."
aws --endpoint-url=http://localhost:4566 s3 ls s3://milo-raw-ingest-local/uploads/ --recursive

# Check SQS queue
Write-Host "Checking SQS queue..."
aws --endpoint-url=http://localhost:4566 sqs receive-message --queue-url http://localhost:4566/000000000000/milo-ingest-local --wait-time-seconds 5