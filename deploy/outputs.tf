output "bucket_id" {
  description = "The S3 bucket name for raw ingestion"
  value       = module.storage.bucket_id
}

output "queue_url" {
  description = "The SQS queue URL for the ingestion pipeline"
  value       = module.messaging.queue_url
}

output "queue_arn" {
  description = "The SQS queue ARN"
  value       = module.messaging.queue_arn
}
