# Monitoring Module Variables

variable "vpc_id" {
  description = "VPC ID to monitor"
  type        = string
}

variable "subnet_ids" {
  description = "List of subnet IDs to monitor"
  type        = list(string)
}

variable "fortigate_instance_ids" {
  description = "List of FortiGate instance IDs to monitor"
  type        = list(string)
}

variable "enable_flow_logs" {
  description = "Enable VPC Flow Logs"
  type        = bool
  default     = true
}

variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 30
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "owner_tag" {
  description = "Owner tag for resources"
  type        = string
}
