# FortiGate AWS HA Deployment - Variables
# Input variables for the FortiGate HA deployment

# AWS Configuration
variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name (e.g., prod, staging, dev)"
  type        = string
  default     = "prod"
}

variable "owner_tag" {
  description = "Owner tag for resources"
  type        = string
  default     = "NetworkTeam"
}

# Network Configuration
variable "vpc_id" {
  description = "VPC ID where FortiGate instances will be deployed (pre-assigned)"
  type        = string
  validation {
    condition     = can(regex("^vpc-[a-z0-9]{8,17}$", var.vpc_id))
    error_message = "VPC ID must be a valid AWS VPC identifier."
  }
}

variable "availability_zones" {
  description = "List of availability zones for HA deployment"
  type        = list(string)
  validation {
    condition     = length(var.availability_zones) >= 2
    error_message = "At least 2 availability zones are required for HA deployment."
  }
}

# Subnet Configuration (Pre-assigned)
variable "outside_subnet_primary" {
  description = "Outside subnet ID for primary FortiGate (pre-assigned)"
  type        = string
  validation {
    condition     = can(regex("^subnet-[a-z0-9]{8,17}$", var.outside_subnet_primary))
    error_message = "Subnet ID must be a valid AWS subnet identifier."
  }
}

variable "inside_subnet_primary" {
  description = "Inside subnet ID for primary FortiGate (pre-assigned)"
  type        = string
  validation {
    condition     = can(regex("^subnet-[a-z0-9]{8,17}$", var.inside_subnet_primary))
    error_message = "Subnet ID must be a valid AWS subnet identifier."
  }
}

variable "ha_subnet_primary" {
  description = "HA subnet ID for primary FortiGate (pre-assigned)"
  type        = string
  validation {
    condition     = can(regex("^subnet-[a-z0-9]{8,17}$", var.ha_subnet_primary))
    error_message = "Subnet ID must be a valid AWS subnet identifier."
  }
}

variable "mgmt_subnet_primary" {
  description = "Management subnet ID for primary FortiGate (pre-assigned)"
  type        = string
  validation {
    condition     = can(regex("^subnet-[a-z0-9]{8,17}$", var.mgmt_subnet_primary))
    error_message = "Subnet ID must be a valid AWS subnet identifier."
  }
}

variable "outside_subnet_backup" {
  description = "Outside subnet ID for backup FortiGate (pre-assigned)"
  type        = string
  validation {
    condition     = can(regex("^subnet-[a-z0-9]{8,17}$", var.outside_subnet_backup))
    error_message = "Subnet ID must be a valid AWS subnet identifier."
  }
}

variable "inside_subnet_backup" {
  description = "Inside subnet ID for backup FortiGate (pre-assigned)"
  type        = string
  validation {
    condition     = can(regex("^subnet-[a-z0-9]{8,17}$", var.inside_subnet_backup))
    error_message = "Subnet ID must be a valid AWS subnet identifier."
  }
}

variable "ha_subnet_backup" {
  description = "HA subnet ID for backup FortiGate (pre-assigned)"
  type        = string
  validation {
    condition     = can(regex("^subnet-[a-z0-9]{8,17}$", var.ha_subnet_backup))
    error_message = "Subnet ID must be a valid AWS subnet identifier."
  }
}

variable "mgmt_subnet_backup" {
  description = "Management subnet ID for backup FortiGate (pre-assigned)"
  type        = string
  validation {
    condition     = can(regex("^subnet-[a-z0-9]{8,17}$", var.mgmt_subnet_backup))
    error_message = "Subnet ID must be a valid AWS subnet identifier."
  }
}

# FortiGate Configuration
variable "fortigate_ami_id" {
  description = "AMI ID for FortiGate instances"
  type        = string
  validation {
    condition     = can(regex("^ami-[a-z0-9]{8,17}$", var.fortigate_ami_id))
    error_message = "AMI ID must be a valid AWS AMI identifier."
  }
}

variable "instance_type" {
  description = "EC2 instance type for FortiGate instances"
  type        = string
  default     = "c5.xlarge"
  validation {
    condition = contains([
      "c5.large", "c5.xlarge", "c5.2xlarge", "c5.4xlarge", "c5.9xlarge",
      "c5n.large", "c5n.xlarge", "c5n.2xlarge", "c5n.4xlarge", "c5n.9xlarge"
    ], var.instance_type)
    error_message = "Instance type must be a supported FortiGate instance type."
  }
}

variable "key_pair_name" {
  description = "AWS Key Pair name for SSH access"
  type        = string
}

variable "admin_password" {
  description = "Admin password for FortiGate instances"
  type        = string
  sensitive   = true
  validation {
    condition     = length(var.admin_password) >= 8
    error_message = "Admin password must be at least 8 characters long."
  }
}

variable "ha_password" {
  description = "HA synchronization password"
  type        = string
  sensitive   = true
  validation {
    condition     = length(var.ha_password) >= 8
    error_message = "HA password must be at least 8 characters long."
  }
}

variable "fortigate_hostname_primary" {
  description = "Hostname for primary FortiGate"
  type        = string
  default     = "fortigate-primary"
}

variable "fortigate_hostname_backup" {
  description = "Hostname for backup FortiGate"
  type        = string
  default     = "fortigate-backup"
}

# Transit Gateway Configuration
variable "create_transit_gateway" {
  description = "Whether to create a new Transit Gateway (true) or use existing (false)"
  type        = bool
  default     = false
}

variable "existing_transit_gateway_id" {
  description = "Existing Transit Gateway ID (required if create_transit_gateway is false)"
  type        = string
  default     = ""
  validation {
    condition = var.create_transit_gateway || (
      !var.create_transit_gateway && can(regex("^tgw-[a-z0-9]{8,17}$", var.existing_transit_gateway_id))
    )
    error_message = "When using existing Transit Gateway, a valid Transit Gateway ID must be provided."
  }
}

variable "transit_gateway_asn" {
  description = "BGP ASN for Transit Gateway"
  type        = number
  default     = 64512
  validation {
    condition     = var.transit_gateway_asn >= 64512 && var.transit_gateway_asn <= 65534
    error_message = "Transit Gateway ASN must be in the private ASN range (64512-65534)."
  }
}

variable "bgp_asn" {
  description = "BGP ASN for FortiGate instances"
  type        = number
  default     = 65000
  validation {
    condition     = var.bgp_asn >= 64512 && var.bgp_asn <= 65534
    error_message = "FortiGate BGP ASN must be in the private ASN range (64512-65534)."
  }
}

variable "spoke_vpc_cidrs" {
  description = "List of spoke VPC CIDR blocks for routing"
  type        = list(string)
  default     = ["10.1.0.0/16", "10.2.0.0/16"]
  validation {
    condition = alltrue([
      for cidr in var.spoke_vpc_cidrs : can(cidrhost(cidr, 0))
    ])
    error_message = "All spoke VPC CIDRs must be valid CIDR blocks."
  }
}

# Security Configuration
variable "mgmt_access_cidrs" {
  description = "CIDR blocks allowed for management access"
  type        = list(string)
  default     = ["10.0.0.0/8"]
  validation {
    condition = alltrue([
      for cidr in var.mgmt_access_cidrs : can(cidrhost(cidr, 0))
    ])
    error_message = "All management access CIDRs must be valid CIDR blocks."
  }
}

# Monitoring Configuration
variable "enable_flow_logs" {
  description = "Enable VPC Flow Logs"
  type        = bool
  default     = true
}

variable "log_retention_days" {
  description = "CloudWatch log retention period in days"
  type        = number
  default     = 30
  validation {
    condition = contains([
      1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365, 400, 545, 731, 1827, 3653
    ], var.log_retention_days)
    error_message = "Log retention days must be a valid CloudWatch retention period."
  }
}

variable "enable_detailed_monitoring" {
  description = "Enable detailed CloudWatch monitoring for EC2 instances"
  type        = bool
  default     = true
}