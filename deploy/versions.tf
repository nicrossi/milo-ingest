terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    doppler = {
      source  = "DopplerHQ/doppler"
      version = "~> 1.0"
    }
  }
}
