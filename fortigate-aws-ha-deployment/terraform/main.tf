# FortiGate AWS HA Deployment - Main Terraform Configuration
# This is the root module that orchestrates all components

terraform {
  required_version = ">= 1.0"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  
  # Remote state backend configuration (commented out - using local state)
  # Uncomment and configure if you want to use S3 backend
  # backend "s3" {
  #   bucket         = "your-fortigate-terraform-state"
  #   key            = "fortigate-ha/terraform.tfstate"
  #   region         = "us-east-1"
  #   encrypt        = true
  #   dynamodb_table = "fortigate-terraform-locks"
  # }
}

# Configure the AWS Provider
provider "aws" {
  region  = var.aws_region
  profile = var.aws_profile != "" ? var.aws_profile : null
  
  default_tags {
    tags = {
      Project     = "FortiGate-HA-Deployment"
      Environment = var.environment
      ManagedBy   = "Terraform"
      Owner       = var.owner_tag
    }
  }
}

# Data sources for existing resources
data "aws_vpc" "main" {
  id = var.vpc_id
}

data "aws_availability_zones" "available" {
  state = "available"
}

# FortiGate HA Module
module "fortigate_ha" {
  source = "./modules/fortigate-ha"
  
  # Network Configuration
  vpc_id             = var.vpc_id
  availability_zones = var.availability_zones
  
  # Subnet Configuration
  outside_subnet_primary = var.outside_subnet_primary
  inside_subnet_primary  = var.inside_subnet_primary
  ha_subnet_primary      = var.ha_subnet_primary
  mgmt_subnet_primary    = var.mgmt_subnet_primary
  
  outside_subnet_backup = var.outside_subnet_backup
  inside_subnet_backup  = var.inside_subnet_backup
  ha_subnet_backup      = var.ha_subnet_backup
  mgmt_subnet_backup    = var.mgmt_subnet_backup
  
  # ENI Configuration (Pre-created by Network Team)
  primary_outside_eni_id = var.primary_outside_eni_id
  primary_inside_eni_id  = var.primary_inside_eni_id
  primary_ha_eni_id      = var.primary_ha_eni_id
  primary_mgmt_eni_id    = var.primary_mgmt_eni_id
  
  backup_outside_eni_id = var.backup_outside_eni_id
  backup_inside_eni_id  = var.backup_inside_eni_id
  backup_ha_eni_id      = var.backup_ha_eni_id
  backup_mgmt_eni_id    = var.backup_mgmt_eni_id
  
  # FortiGate Configuration
  fortigate_ami_id   = var.fortigate_ami_id
  instance_type      = var.instance_type
  key_pair_name      = var.key_pair_name
  admin_password     = var.admin_password
  ha_password        = var.ha_password
  fortigate_hostname_primary = var.fortigate_hostname_primary
  fortigate_hostname_backup  = var.fortigate_hostname_backup
  
  # BGP Configuration
  bgp_asn            = var.bgp_asn
  transit_gateway_id = var.create_transit_gateway ? module.transit_gateway[0].transit_gateway_id : var.existing_transit_gateway_id
  
  # Security Configuration
  security_group_ids = [
    module.security.mgmt_security_group_id,
    module.security.data_security_group_id,
    module.security.ha_security_group_id
  ]
  
  # Monitoring
  enable_detailed_monitoring = var.enable_detailed_monitoring
  
  # Elastic IP Configuration
  allocate_eips           = var.allocate_eips
  primary_outside_eip_id  = var.primary_outside_eip_id
  backup_outside_eip_id   = var.backup_outside_eip_id
  
  # EIP Failover Configuration
  enable_eip_failover = var.enable_eip_failover
  aws_region          = var.aws_region
  
  # Tags
  environment = var.environment
  owner_tag   = var.owner_tag
  
  depends_on = [
    module.security
  ]
}

# Transit Gateway Module (conditional)
module "transit_gateway" {
  count  = var.create_transit_gateway ? 1 : 0
  source = "./modules/transit-gateway"
  
  # BGP Configuration
  amazon_side_asn = var.transit_gateway_asn
  
  # Route Configuration
  spoke_vpc_cidrs = var.spoke_vpc_cidrs
  
  # Tags
  environment = var.environment
  owner_tag   = var.owner_tag
}

# Security Module
module "security" {
  source = "./modules/security"
  
  # Network Configuration
  vpc_id = var.vpc_id
  
  # Subnet Configuration for security group rules
  outside_subnet_cidrs = [
    data.aws_subnet.outside_primary.cidr_block,
    data.aws_subnet.outside_backup.cidr_block
  ]
  inside_subnet_cidrs = [
    data.aws_subnet.inside_primary.cidr_block,
    data.aws_subnet.inside_backup.cidr_block
  ]
  mgmt_subnet_cidrs = [
    data.aws_subnet.mgmt_primary.cidr_block,
    data.aws_subnet.mgmt_backup.cidr_block
  ]
  
  # Management access
  mgmt_access_cidrs = var.mgmt_access_cidrs
  
  # Tags
  environment = var.environment
  owner_tag   = var.owner_tag
}

# Monitoring Module
module "monitoring" {
  source = "./modules/monitoring"
  
  # Network Configuration
  vpc_id = var.vpc_id
  
  # Subnet IDs for Flow Logs
  subnet_ids = [
    var.outside_subnet_primary,
    var.inside_subnet_primary,
    var.ha_subnet_primary,
    var.mgmt_subnet_primary,
    var.outside_subnet_backup,
    var.inside_subnet_backup,
    var.ha_subnet_backup,
    var.mgmt_subnet_backup
  ]
  
  # FortiGate Configuration
  fortigate_instance_ids = module.fortigate_ha.instance_ids
  
  # Logging Configuration
  enable_flow_logs     = var.enable_flow_logs
  log_retention_days   = var.log_retention_days
  
  # Tags
  environment = var.environment
  owner_tag   = var.owner_tag
}

# Data sources for subnet information
data "aws_subnet" "outside_primary" {
  id = var.outside_subnet_primary
}

data "aws_subnet" "outside_backup" {
  id = var.outside_subnet_backup
}

data "aws_subnet" "inside_primary" {
  id = var.inside_subnet_primary
}

data "aws_subnet" "inside_backup" {
  id = var.inside_subnet_backup
}

data "aws_subnet" "mgmt_primary" {
  id = var.mgmt_subnet_primary
}

data "aws_subnet" "mgmt_backup" {
  id = var.mgmt_subnet_backup
}