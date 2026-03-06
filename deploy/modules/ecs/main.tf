data "aws_ami" "ecs_optimized" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-ecs-hvm-*-x86_64"]
  }
}

resource "aws_security_group" "ec2" {
  name        = "milo-ingest-ec2-sg-${var.environment}"
  description = "Allow outbound traffic from the ingest ECS EC2 instance"
  vpc_id      = var.vpc_id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_iam_instance_profile" "ecs_ec2" {
  name = "milo-ingest-ecs-ec2-profile-${var.environment}"
  role = var.ec2_instance_role_name
}

resource "aws_launch_template" "ecs_ec2" {
  name_prefix   = "milo-ingest-ecs-ec2-${var.environment}-"
  image_id      = data.aws_ami.ecs_optimized.id
  instance_type = var.ec2_instance_type

  iam_instance_profile {
    name = aws_iam_instance_profile.ecs_ec2.name
  }

  vpc_security_group_ids = [aws_security_group.ec2.id, var.db_security_group_id]

  user_data = base64encode(<<-EOF
    #!/bin/bash
    echo ECS_CLUSTER=milo-ingest-ecs-cluster-${var.environment} >> /etc/ecs/ecs.config
  EOF
  )
}

resource "aws_autoscaling_group" "ecs_ec2" {
  name                = "milo-ingest-ecs-asg-${var.environment}"
  min_size            = 1
  max_size            = 1
  desired_capacity    = 1
  vpc_zone_identifier = var.subnet_ids

  launch_template {
    id      = aws_launch_template.ecs_ec2.id
    version = "$Latest"
  }

  tag {
    key                 = "AmazonECSManaged"
    value               = true
    propagate_at_launch = true
  }

  lifecycle {
    create_before_destroy = true
  }
}

# Scale the ASG to 0 before destroying the cluster so container instances
# are deregistered first (avoids ClusterContainsContainerInstancesException).
resource "null_resource" "drain_ecs_instances" {
  triggers = {
    asg_name = aws_autoscaling_group.ecs_ec2.name
    region   = var.aws_region
  }

  provisioner "local-exec" {
    when    = destroy
    command = <<-EOT
      aws autoscaling update-auto-scaling-group \
        --region "${self.triggers.region}" \
        --auto-scaling-group-name "${self.triggers.asg_name}" \
        --min-size 0 --max-size 0 --desired-capacity 0

      echo "Waiting for instances to terminate..."
      for i in $(seq 1 30); do
        COUNT=$(aws autoscaling describe-auto-scaling-groups \
          --region "${self.triggers.region}" \
          --auto-scaling-group-names "${self.triggers.asg_name}" \
          --query "AutoScalingGroups[0].Instances | length(@)" \
          --output text)
        echo "Instances remaining: $COUNT"
        [ "$COUNT" = "0" ] && break
        sleep 10
      done
    EOT
  }
}

resource "aws_ecs_capacity_provider" "ec2" {
  name = "milo-ingest-ec2-cp-${var.environment}"

  auto_scaling_group_provider {
    auto_scaling_group_arn = aws_autoscaling_group.ecs_ec2.arn

    managed_scaling {
      status          = "ENABLED"
      target_capacity = 100
    }
  }
}

resource "aws_ecs_cluster" "this" {
  name = "milo-ingest-ecs-cluster-${var.environment}"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  depends_on = [null_resource.drain_ecs_instances]
}

resource "aws_ecs_cluster_capacity_providers" "this" {
  cluster_name       = aws_ecs_cluster.this.name
  capacity_providers = [aws_ecs_capacity_provider.ec2.name]

  default_capacity_provider_strategy {
    capacity_provider = aws_ecs_capacity_provider.ec2.name
    weight            = 100
  }
}

resource "aws_cloudwatch_log_group" "ingest" {
  name              = "/ecs/milo-ingest-${var.environment}"
  retention_in_days = 14
}

resource "aws_ecs_task_definition" "ingest" {
  family                   = "milo-ingest"
  network_mode             = "bridge"
  requires_compatibilities = ["EC2"]
  execution_role_arn       = var.execution_role_arn
  task_role_arn            = var.task_role_arn

  container_definitions = jsonencode([
    {
      name      = "ingest"
      image     = var.container_image
      essential = true
      cpu       = 1024
      memory    = 2048

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

  # Use the capacity provider instead of launch_type so the ASG
  # is responsible for launching the EC2 container instance.
  capacity_provider_strategy {
    capacity_provider = aws_ecs_capacity_provider.ec2.name
    weight            = 100
  }

  # pull the ':latest' image even if the tag name hasn't changed
  force_new_deployment = true

  # Prevents Terraform from fighting with ASG in higher envs
  lifecycle {
    ignore_changes = [desired_count]
  }

  depends_on = [aws_ecs_cluster_capacity_providers.this]
}
