variable "bucket_name" {
  description = "The unique name for the S3 bucket"
  type        = string
}

variable "environment" {
  description = "The deployment environment (local, sandbox, etc)"
  type        = string
}
