resource "aws_ecs_cluster" "this" {
  name = "milo-ingest-ecs-cluster-${var.environment}"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

resource "aws_cloudwatch_log_group" "ingest" {
  name = "/ecs/milo-ingest-${var.environment}"
  retention_in_days = 14
}

resource "aws_ecs_task_definition" "ingest" {
  family                   = "milo-ingest"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = 256
  memory                   = 512
  execution_role_arn       = var.execution_role_arn
  task_role_arn            = var.task_role_arn

  container_definitions = jsonencode([
    {
      name      = "ingest"
      image     = var.container_image
      essential = true

      environment = concat(
        [
          { name = "DB_URL",        value = var.db_url },
          { name = "SQS_QUEUE_URL", value = var.sq_queue_url },
          { name = "S3_BUCKET",     value = var.s3_bucket_id },
          { name = "ENV",           value = var.environment }
        ],
        [for key, value in var.doppler_secrets : { name = key, value = value }]
      )

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.ingest.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "ecs"
        }
      }
    }
  ])
}

resource "aws_ecs_service" "this" {
  name            = "ingest-service"
  cluster         = aws_ecs_cluster.this.id
  task_definition = aws_ecs_task_definition.ingest.arn
  desired_count   = 1

  # pull the ':latest' image even if the tag name hasn't changed
  force_new_deployment = var.environment == "local"

  capacity_provider_strategy {
    capacity_provider = var.environment == "local" ? "FARGATE" : "FARGATE_SPOT"
    weight            = 100
  }

  network_configuration {
    subnets          = var.subnet_ids
    security_groups  = [var.security_group_id]
    assign_public_ip = var.environment == "local" # LocalStack needs this to route traffic
  }

  # Prevents Terraform from fighting with AS in higher envs
  lifecycle {
    ignore_changes = [desired_count]
  }
}
