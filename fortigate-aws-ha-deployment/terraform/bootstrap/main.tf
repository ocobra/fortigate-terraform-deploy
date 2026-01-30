# Bootstrap Configuration for Terraform State Management
# This must be run FIRST to create the S3 bucket and DynamoDB table
# for remote state storage and locking

terraform {
  required_version = ">= 1.0"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  
  # Note: This bootstrap configuration uses local state
  # After running this, the main configuration will use remote state
}

# Configure the AWS Provider
provider "aws" {
  region = var.aws_region
  
  default_tags {
    tags = {
      Project     = "FortiGate-HA-Deployment"
      Environment = var.environment
      ManagedBy   = "Terraform-Bootstrap"
      Purpose     = "State-Management"
    }
  }
}

# State Management Module
module "state_management" {
  source = "../modules/state-management"
  
  state_bucket_name           = var.state_bucket_name
  dynamodb_table_name        = var.dynamodb_table_name
  environment                = var.environment
  enable_point_in_time_recovery = var.enable_point_in_time_recovery
}