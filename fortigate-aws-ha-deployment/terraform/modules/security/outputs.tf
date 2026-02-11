# Security Module Outputs

output "fortigate_security_group_ids" {
  description = "Map of security group IDs for FortiGate interfaces"
  value = {
    mgmt    = aws_security_group.fortigate_mgmt.id
    data    = aws_security_group.fortigate_data.id
    ha      = aws_security_group.fortigate_ha.id
  }
}

output "mgmt_security_group_id" {
  description = "Security group ID for management interface"
  value       = aws_security_group.fortigate_mgmt.id
}

output "data_security_group_id" {
  description = "Security group ID for data plane interfaces"
  value       = aws_security_group.fortigate_data.id
}

output "ha_security_group_id" {
  description = "Security group ID for HA interface"
  value       = aws_security_group.fortigate_ha.id
}
