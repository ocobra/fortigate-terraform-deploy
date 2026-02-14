# Bootstrap Configuration Example
# Copy this file to terraform.tfvars and customize the values

# AWS Configuration
aws_region = "us-east-1"

# State Management Configuration
state_bucket_name = "renaws-fortigate-terraform-state"
dynamodb_table_name = "fortigate-terraform-locks"

# Environment
environment = "prod"

# DynamoDB Configuration
enable_point_in_time_recovery = true
