# Ingest Pipeline: Local Test

Validate the local ingestion pipeline that simulates S3-to-SQS event-driven
processing using LocalStack. 

**Components:**
- **Infrastructure**: Terraform provisions an S3 bucket (`milo-raw-ingest-local`) and SQS queue (`milo-ingest-local`)
- **Event Flow**: S3 sends ObjectCreated notifications to SQS when files are uploaded
- **Consumer**: Python worker polls SQS and logs file upload events
- **Configuration**: Doppler manages secrets and endpoints
---

## Prerequisites
```
  # LocalStack
  pip install localstack awscli-local

  # Terraform wrapper for LocalStack
  pip install terraform-local

  # Doppler CLI
  brew install dopplerhq/cli/doppler

  # Python dependencies
  pip install -r src/requirements.txt
```
Environment Setup:

- LocalStack running on http://localhost:4566
- Doppler authenticated (doppler login)
- AWS LocalStack profile configured
---

## 1) Start LocalStack
Open a terminal and launch:
```
localstack start
```
## 2) Deploy Infrastructure
Navigate to the deploy directory and init terraform:
```
cd deploy
tflocal init
```

Apply terraform using local config:
```
tflocal apply -var-file="vars/local-us-east-1.tfvars" -auto-approve
```
**Expected output**
```
Apply complete! Resources: X added, 0 changed, 0 destroyed.

Outputs:

bucket_id = "milo-raw-ingest-local"
queue_url = "http://localhost:4566/000000000000/milo-ingest-local"
```
## 3) Set Doppler secrets
Extract the SQS queue URL from terraform outputs:
```
export QUEUE_URL=$(tflocal output -raw queue_url)
echo "Queue URL: $QUEUE_URL"
```

Update the Doppler `dev` config with the queue URL:
```
doppler secrets set SQS_QUEUE_URL="$QUEUE_URL" --project milo-ingest --config dev
```
> To programmatically set secrets (write access),
> you must explicitly generate a Service Token with R/W access.

Verify `SQS_QUEUE_URL` is configured:
```
doppler secrets --project milo-ingest --config dev
```
## 4) Python Consumer
Navigate to the source directory and start the worker using Doppler:
```
cd ../src
doppler run --project milo-ingest --config dev -- python main.py
```
Expected Output:
```
2026-01-31 10:30:15,123 - docling-ack - INFO - Worker started. Listening on: http://localhost:4566/000000000000/milo-ingest-local
```
The worker is now polling the SQS queue every 20 seconds (long polling enabled).

## 5) Simulate File Upload
In a **new terminal**, simulate the upload of a file to the S3 bucket:
```
echo "Test ingestion data" > test-file.txt

# Upload to S3 using awslocal
awslocal s3 cp test-file.txt s3://milo-raw-ingest-local/uploads/test-file.txt
```
Expected Output:
```
upload: ./test-file.txt to s3://milo-raw-ingest-local/uploads/test-file.txt
```
Validation: Verify the file exists in S3:
```
awslocal s3 ls s3://milo-raw-ingest-local/uploads/ --recursive
```
Expected Output:
```
2026-01-31 10:30:45    20 uploads/test-file.txt
```

## 6) Verify Queue is Empty
Check that the message was consumed and deleted:
```
awslocal sqs receive-message --queue-url http://localhost:4566/000000000000/milo-ingest-local --wait-time-seconds 5
```
**An empty response confirms the message was successfully processed and removed.**

## 7) Cleanup
Optionally, if you want to tear down the infrastructure:

```
cd deploy
tflocal destroy -var-file="vars/local-us-east-1.tfvars" -auto-approve
```

Or stop LocalStack:

```
localstack stop
```