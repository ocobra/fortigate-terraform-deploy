# FortiGate HA Module - Variables

# Network Configuration
variable "vpc_id" {
  description = "VPC ID where FortiGate instances will be deployed"
  type        = string
}

variable "availability_zones" {
  description = "List of availability zones for HA deployment"
  type        = list(string)
}

# Subnet Configuration
variable "outside_subnet_primary" {
  description = "Outside subnet ID for primary FortiGate"
  type        = string
}

variable "inside_subnet_primary" {
  description = "Inside subnet ID for primary FortiGate"
  type        = string
}

variable "ha_subnet_primary" {
  description = "HA subnet ID for primary FortiGate"
  type        = string
}

variable "mgmt_subnet_primary" {
  description = "Management subnet ID for primary FortiGate"
  type        = string
}

variable "outside_subnet_backup" {
  description = "Outside subnet ID for backup FortiGate"
  type        = string
}

variable "inside_subnet_backup" {
  description = "Inside subnet ID for backup FortiGate"
  type        = string
}

variable "ha_subnet_backup" {
  description = "HA subnet ID for backup FortiGate"
  type        = string
}

variable "mgmt_subnet_backup" {
  description = "Management subnet ID for backup FortiGate"
  type        = string
}

# ENI Configuration (Pre-created by Network Team)
variable "primary_outside_eni_id" {
  description = "ENI ID for primary FortiGate outside interface (pre-created by network team)"
  type        = string
}

variable "primary_inside_eni_id" {
  description = "ENI ID for primary FortiGate inside interface (pre-created by network team)"
  type        = string
}

variable "primary_ha_eni_id" {
  description = "ENI ID for primary FortiGate HA interface (pre-created by network team)"
  type        = string
}

variable "primary_mgmt_eni_id" {
  description = "ENI ID for primary FortiGate management interface (pre-created by network team)"
  type        = string
}

variable "backup_outside_eni_id" {
  description = "ENI ID for backup FortiGate outside interface (pre-created by network team)"
  type        = string
}

variable "backup_inside_eni_id" {
  description = "ENI ID for backup FortiGate inside interface (pre-created by network team)"
  type        = string
}

variable "backup_ha_eni_id" {
  description = "ENI ID for backup FortiGate HA interface (pre-created by network team)"
  type        = string
}

variable "backup_mgmt_eni_id" {
  description = "ENI ID for backup FortiGate management interface (pre-created by network team)"
  type        = string
}

# FortiGate Configuration
variable "fortigate_ami_id" {
  description = "AMI ID for FortiGate instances"
  type        = string
}

variable "instance_type" {
  description = "EC2 instance type for FortiGate instances"
  type        = string
  default     = "c5.xlarge"
}

variable "key_pair_name" {
  description = "AWS Key Pair name for SSH access"
  type        = string
}

variable "admin_password" {
  description = "Admin password for FortiGate instances"
  type        = string
  sensitive   = true
}

variable "ha_password" {
  description = "HA synchronization password"
  type        = string
  sensitive   = true
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

# BGP Configuration
variable "bgp_asn" {
  description = "BGP ASN for FortiGate instances"
  type        = number
  default     = 65000
}

variable "transit_gateway_id" {
  description = "Transit Gateway ID for BGP peering"
  type        = string
}

# Security Configuration
variable "security_group_ids" {
  description = "List of security group IDs to attach to FortiGate instances"
  type        = list(string)
}

# Monitoring Configuration
variable "enable_detailed_monitoring" {
  description = "Enable detailed CloudWatch monitoring for EC2 instances"
  type        = bool
  default     = true
}

# Tags
variable "environment" {
  description = "Environment name"
  type        = string
  default     = "prod"
}

variable "owner_tag" {
  description = "Owner tag for resources"
  type        = string
  default     = "NetworkTeam"
}