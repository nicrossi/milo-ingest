environment   = "stage"
aws_region    = "us-east-1"
aws_profile   = "milo-mgmt"

# Resource Settings for Stage database
# db_name, db_username, db_password are sourced from Doppler
instance_class   = "db.t2.micro"

doppler_project = "milo-ingest"
doppler_config  = "stg"

