output "cluster_name" {
  description = "The name of the ECS Cluster"
  value       = aws_ecs_cluster.this.name
}

output "cluster_arn" {
  description = "The ARN of the ECS Cluster"
  value       = aws_ecs_cluster.this.arn
}

output "service_name" {
  description = "The name of the ECS Service"
  value       = aws_ecs_service.this.name
}

output "task_definition_arn" {
  description = "The ARN of the Task Definition"
  value       = aws_ecs_task_definition.ingest.arn
}

output "log_group_name" {
  description = "The name of the CloudWatch Log Group"
  value       = aws_cloudwatch_log_group.ingest.name
}
