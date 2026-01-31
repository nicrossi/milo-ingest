output "db_endpoint" {
  description = "The connection endpoint for the database"
  value       = aws_db_instance.this.endpoint
}

output "db_security_group_id" {
  value = aws_security_group.this.id
}
