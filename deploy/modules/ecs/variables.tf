variable "environment" {
    type = string
}

variable "aws_region" {
    type = string
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

variable "subnet_ids" {
    type = list(string)
}

variable "security_group_id" {
    type = string
}
