variable "environment" {
    type = string
}

variable "aws_region" {
    type = string
}

variable "vpc_id" {
  description = "VPC ID for the EC2 security group"
  type        = string
}

variable "subnet_ids" {
    type = list(string)
}

variable "db_security_group_id" {
  description = "RDS security group ID so the EC2 container instance can reach the DB"
  type        = string
}

variable "ec2_instance_role_name" {
  description = "IAM role name to attach to the ECS EC2 instance profile"
  type        = string
}

variable "container_image" {
    type = string
}

variable "execution_role_arn" {
    type = string
}

variable "task_role_arn" {
    type = string
}

variable "db_url" {
    type = string
}

variable "sq_queue_url" {
    type = string
}

variable "s3_bucket_id" {
    type = string
}

variable "ec2_instance_type" {
  description = "EC2 instance type for the ECS container instance"
  type        = string
  default     = "t3.micro"
}

variable "doppler_secrets" {
    description = "Map of secrets from Doppler"
    type        = map(string)
    default     = {}
    sensitive   = true
}

