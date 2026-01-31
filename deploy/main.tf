data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
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
  source      = "./modules/database"
  environment = var.environment
  vpc_id      = data.aws_vpc.default.id
  db_name     = var.db_name
  db_username = var.db_username
  db_password = var.db_password
  instance_class = var.instance_class
}

module "iam" {
  source      = "./modules/iam"
  environment = var.environment
  bucket_arn  = module.storage.bucket_arn
  queue_arn   = module.messaging.queue_arn
}

module "ingest_service" {
  source             = "./modules/ecs"
  environment        = var.environment
  aws_region         = var.aws_region
  container_image    = "milo/doclin:latest"
  execution_role_arn = module.iam.execution_role_arn
  task_role_arn      = module.iam.task_role_arn
  db_url             = module.database.db_endpoint
  sq_queue_url       = module.messaging.queue_url
  s3_bucket_id       = module.storage.bucket_id
  subnet_ids         = data.aws_subnets.default.ids
  security_group_id  = module.database.db_security_group_id # Shared for PoC
}
