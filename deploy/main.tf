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
