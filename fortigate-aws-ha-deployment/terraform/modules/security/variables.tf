# Security Module Variables

variable "vpc_id" {
  description = "VPC ID where security groups will be created"
  type        = string
}

variable "outside_subnet_cidrs" {
  description = "CIDR blocks for outside subnets"
  type        = list(string)
}

variable "inside_subnet_cidrs" {
  description = "CIDR blocks for inside subnets"
  type        = list(string)
}

variable "mgmt_subnet_cidrs" {
  description = "CIDR blocks for management subnets"
  type        = list(string)
}

variable "mgmt_access_cidrs" {
  description = "CIDR blocks allowed to access FortiGate management"
  type        = list(string)
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "owner_tag" {
  description = "Owner tag for resources"
  type        = string
}
