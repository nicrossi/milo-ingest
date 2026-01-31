provider "aws" {
  region  = var.aws_region
  profile = var.aws_profile

  default_tags {
    tags = {
      Project     = "Milo"
      Environment = var.environment
      ManagedBy   = "Terraform"
      Component   = "Ingest-Pipeline"
    }
  }

  # LocalStack Overrides
  # These settings only activate if aws_local_url is provided.
  skip_credentials_validation = var.aws_local_url != null
  skip_metadata_api_check     = var.aws_local_url != null
  skip_requesting_account_id  = var.aws_local_url != null
  s3_use_path_style           = var.aws_local_url != null

  dynamic "endpoints" {
    for_each = var.aws_local_url != null ? [1] : []
    content {
      s3             = var.aws_local_url
      sqs            = var.aws_local_url
      ecs            = var.aws_local_url
      rds            = var.aws_local_url
      iam            = var.aws_local_url
      sts            = var.aws_local_url
      ecr            = var.aws_local_url
      cloudwatch     = var.aws_local_url
      logs           = var.aws_local_url
      resourcegroups = var.aws_local_url
    }
  }
}

provider "doppler" {
  # Authentication is handled via DOPPLER_TOKEN environment variable
  # Set this before running terraform: export DOPPLER_TOKEN="your-service-token"
}

