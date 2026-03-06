data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

# Fetch secrets from Doppler during apply phase
data "doppler_secrets" "this" {
  project = var.doppler_project
  config  = coalesce(var.doppler_config, var.environment)
}

# ECS EC2 security group created here so it can be referenced by both the
# database module (ingress rule) and the ECS module (launch template).
resource "aws_security_group" "ecs_ec2" {
  name        = "milo-ingest-ec2-sg-${var.environment}"
  description = "Allow outbound traffic from the ingest ECS EC2 instance"
  vpc_id      = data.aws_vpc.default.id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

module "storage" {
  source      = "./modules/storage"
  bucket_name = "milo-raw-ingest-${var.environment}"
  environment = var.environment
}

module "messaging" {
  source      = "./modules/messaging"
  environment = var.environment
  bucket_id   = module.storage.bucket_id
  bucket_arn  = module.storage.bucket_arn
}

module "database" {
  source                = "./modules/database"
  environment           = var.environment
  vpc_id                = data.aws_vpc.default.id
  db_name               = data.doppler_secrets.this.map["DB_NAME"]
  db_username           = data.doppler_secrets.this.map["DB_USERNAME"]
  db_password           = data.doppler_secrets.this.map["DB_PASSWORD"]
  instance_class        = var.instance_class
  app_security_group_id = aws_security_group.ecs_ec2.id
}

module "iam" {
  source      = "./modules/iam"
  environment = var.environment
  bucket_arn  = module.storage.bucket_arn
  queue_arn   = module.messaging.queue_arn
}

# Push the DB_URL into Doppler after the database is created
resource "null_resource" "doppler_db_url" {
  depends_on = [module.database]

  triggers = {
    db_endpoint = module.database.db_endpoint
  }

  provisioner "local-exec" {
    command = <<-EOT
      doppler secrets set DB_URL="postgresql://${data.doppler_secrets.this.map["DB_USERNAME"]}:${data.doppler_secrets.this.map["DB_PASSWORD"]}@${module.database.db_endpoint}/${data.doppler_secrets.this.map["DB_NAME"]}" \
        --project ${var.doppler_project} \
        --config ${coalesce(var.doppler_config, var.environment)}
    EOT
  }
}

# Push the SQS_QUEUE_URL into Doppler after the queue is created
resource "null_resource" "doppler_queue_url" {
  depends_on = [module.messaging]

  triggers = {
    queue_url = module.messaging.queue_url
  }

  provisioner "local-exec" {
    command = <<-EOT
      doppler secrets set SQS_QUEUE_URL="${module.messaging.queue_url}" \
        --project ${var.doppler_project} \
        --config ${coalesce(var.doppler_config, var.environment)}
    EOT
  }
}

module "ingest_service" {
  source                 = "./modules/ecs"
  environment            = var.environment
  aws_region             = var.aws_region
  subnet_ids             = data.aws_subnets.default.ids
  ec2_security_group_id  = aws_security_group.ecs_ec2.id
  ec2_instance_role_name = module.iam.ec2_instance_role_name
  ec2_instance_type      = var.ec2_instance_type
  container_image        = "nicrossi/milo-ingest:latest"
  execution_role_arn     = module.iam.execution_role_arn
  task_role_arn          = module.iam.task_role_arn
  db_url                 = module.database.db_endpoint
  sq_queue_url           = module.messaging.queue_url
  s3_bucket_id           = module.storage.bucket_id
  doppler_secrets        = data.doppler_secrets.this.map
}
