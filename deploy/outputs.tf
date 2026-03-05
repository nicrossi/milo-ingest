output "db_url" {
  description = "Full PostgreSQL connection string for the RDS instance"
  value       = "postgresql://${data.doppler_secrets.this.map["DB_USERNAME"]}:${data.doppler_secrets.this.map["DB_PASSWORD"]}@${module.database.db_endpoint}/${data.doppler_secrets.this.map["DB_NAME"]}"
  sensitive   = true
}

output "db_endpoint" {
  description = "Raw RDS endpoint (host:port)"
  value       = module.database.db_endpoint
}

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
