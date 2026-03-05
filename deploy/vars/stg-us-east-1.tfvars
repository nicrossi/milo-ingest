environment   = "stage"
aws_region    = "us-east-1"
aws_profile   = "milo-mgmt"

# Resource Settings for Stage database
# db_name, db_username, db_password are sourced from Doppler
instance_class    = "db.t3.micro"
ec2_instance_type = "t3.micro"

doppler_project = "milo-ingest"
doppler_config  = "stg"

