# Doppler Integration Guide

This Terraform configuration fetches secrets from Doppler during the `terraform apply` phase and injects them into your ECS Task Definition.

## Prerequisites

1. **Doppler Account**: Set up a Doppler account at https://doppler.com
2. **Doppler CLI** (optional, for testing): Install via `brew install dopplerhq/cli/doppler`
3. **Doppler Service Token**: Generate a service token for your project/config

## Setup Steps

### 1. Create Doppler Project and Config

In Doppler:
- Create a project named `milo-ingest` (or customize via `doppler_project` variable)
- Create configs for each environment (e.g., `dev`, `staging`, `prd`)
- Add your secrets to each config


### 2. Generate Service Token

1. Go to your Doppler project
2. Navigate to the specific config (e.g., `dev`)
3. Go to Settings → Service Tokens
4. Create a new service token with read access
5. Copy the token (starts with `dp.st.`)

### 3. Set Environment Variable

Before running Terraform, export your Doppler token:

```bash
  export DOPPLER_TOKEN="dp.st.your-service-token-here"
```

**Security Best Practice**: Store this token securely in your CI/CD system's secret management (GitHub Secrets, GitLab CI/CD variables, etc.)

### 4. Configure Terraform Variables

In your `.tfvars` file or as command-line arguments:

```hcl
# Optionally override the default Doppler project
doppler_project = "milo-ingest"

# Optionally specify a different config name than the environment
# If not set, it will use the value of 'environment' variable
doppler_config = "dev"  # or "staging", "prd", etc.
```

### 5. Initialize and Apply

```bash
# Initialize Terraform (downloads Doppler provider)
terraform init

# Plan to see what will be created
terraform plan -var-file="vars/local-us-east-1.tfvars"

# Apply the configuration
terraform apply -var-file="vars/local-us-east-1.tfvars"
```

## How It Works

1. **Data Source**: The `data.doppler_secrets.this` block fetches all secrets from your specified Doppler project/config during `terraform apply`
2. **Secrets Map**: Secrets are retrieved as a map of key-value pairs
3. **ECS Task Definition**: All Doppler secrets are automatically added as environment variables to your ECS containers
4. **Dynamic Updates**: When you update secrets in Doppler and re-run `terraform apply`, the ECS task definition will be updated with new values

## What Gets Injected

Your ECS container will have:

**Standard Environment Variables:**
- `DB_URL` - From RDS module
- `SQS_QUEUE_URL` - From messaging module
- `S3_BUCKET` - From storage module
- `ENV` - Current environment name

**Plus ALL secrets from Doppler** (e.g., `API_KEY`, `DATABASE_PASSWORD`, etc.)