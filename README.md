# Milo Ingest Pipeline

> Event-driven S3-to-SQS ingestion pipeline with AWS infrastructure provisioned via Terraform

## Overview

The **Milo Ingest Pipeline** is a serverless data ingestion system that automatically processes files uploaded to S3. 
When a file is uploaded, S3 triggers an event notification to SQS, and a Python consumer worker processes the messages in real-time.

                                                  
### Prerequisites

- **Python 3.11+**
- **Terraform 1.5+** (or `terraform-local` for LocalStack)
- **AWS CLI** (or `awslocal` for LocalStack)
- **Doppler CLI** (for secret management)
- **Docker** (optional, for containerized deployment)
---
## Test with LocalStack

For a local test, follow the **[Local Test Guide](src/docs/local-test.md)**:

---

## Deployment

### Configure Doppler Secrets

Set up your Doppler project and generate a service token. See **[Doppler Setup Guide](deploy/docs/doppler_setup.md)**. 