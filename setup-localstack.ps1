#Requires -Version 5.1

$ErrorActionPreference = 'Stop'

Write-Host "Setting up LocalStack infrastructure..."

# Wait for LocalStack to be ready
Write-Host "Waiting for LocalStack..."
while ($true) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:4566/_localstack/health" -UseBasicParsing
        if ($response.Content -match '"s3": "available"') {
            break
        }
    } catch {
        # Continue waiting
    }
    Start-Sleep -Seconds 2
}

# Create S3 bucket
Write-Host "Creating S3 bucket..."
aws --endpoint-url=http://localhost:4566 s3 mb s3://milo-raw-ingest-local

# Create SQS queue
Write-Host "Creating SQS queue..."
aws --endpoint-url=http://localhost:4566 sqs create-queue --queue-name milo-ingest-local

# Configure S3 bucket notification to SQS
Write-Host "Configuring S3 bucket notification..."
aws --endpoint-url=http://localhost:4566 s3api put-bucket-notification-configuration `
  --bucket milo-raw-ingest-local `
  --notification-configuration '{
    "QueueConfigurations": [
      {
        "QueueArn": "arn:aws:sqs:us-east-1:000000000000:milo-ingest-local",
        "Events": ["s3:ObjectCreated:*"]
      }
    ]
  }'

Write-Host "LocalStack setup complete!"