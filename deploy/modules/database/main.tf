resource "aws_security_group" "this" {
  name        = "milo-db-sg-${var.environment}"
  description = "Allow inbound traffic to Postgres"
  vpc_id      = var.vpc_id

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    # when not in local, only allow access from the Docling ECS Service SG
    cidr_blocks     = var.environment == "local" ? ["0.0.0.0/0"] : []
    security_groups = var.app_security_group_id != null ? [var.app_security_group_id] : []
  }
}

resource "aws_db_parameter_group" "this" {
  name   = "milo-pg16-params-${var.environment}"
  family = "postgres16"
  description = "Custom parameter group for Milo pgvector support"
}

# RDS
resource "aws_db_instance" "this" {
  identifier           = "milo-db-${var.environment}"
  engine               = "postgres"
  engine_version       = "16.1"
  instance_class       = var.instance_class
  allocated_storage    = 20
  db_name              = var.db_name
  username             = var.db_username
  password             = var.db_password
  parameter_group_name = aws_db_parameter_group.this.name

  vpc_security_group_ids = [aws_security_group.this.id]

  skip_final_snapshot  = var.environment == "local"
  deletion_protection  = var.environment != "local"
  publicly_accessible  = var.environment == "local"
}
