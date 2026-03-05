environment      = "local"
aws_region       = "us-east-1"
aws_profile      = "localstack"
aws_local_url    = "http://localhost:4566"

# Resource Settings for Local database
# db_name, db_username, db_password are sourced from Doppler
instance_class   = "db.t2.micro"

doppler_project = "milo-ingest"
doppler_config  = "dev"
