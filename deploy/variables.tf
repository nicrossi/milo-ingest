variable "environment" {
  description = "Deployment environment"
  type        = string
}

variable "aws_region" {
  description = "AWS Region"
  type        = string
  default     = "us-east-1"
}

variable "aws_profile" {
  description = "AWS CLI Profile to use"
  type        = string
  default     = null
}

variable "aws_local_url" {
  description = "The endpoint URL for LocalStack. If null, real AWS is used."
  type        = string
  default     = null
}

variable "env_vars" {
  description = "Environment vars override"
  type        = map(string)
  default     = {}
}

variable "doppler_project" {
  description = "Doppler project name"
  type        = string
  default     = "milo-ingest"
}

variable "doppler_config" {
  description = "Doppler config name (e.g., dev, staging, prd)"
  type        = string
  default     = null
}

# RDS module
variable "db_name" {
    type = string
}

variable "db_username" {
    type = string
}

variable "db_password" {
  type      = string
  sensitive = true
}

variable "instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.micro"
}

