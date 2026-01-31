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
  vpc_id      = var.vpc_id
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
