# FortiGate HA Module - Outputs

# Instance Information
output "primary_instance_id" {
  description = "Instance ID of the primary FortiGate"
  value       = aws_instance.fortigate_primary.id
}

output "backup_instance_id" {
  description = "Instance ID of the backup FortiGate"
  value       = aws_instance.fortigate_backup.id
}

output "instance_ids" {
  description = "List of all FortiGate instance IDs"
  value       = [aws_instance.fortigate_primary.id, aws_instance.fortigate_backup.id]
}

# IP Address Information
output "primary_inside_ip" {
  description = "Inside interface IP of primary FortiGate"
  value       = data.aws_network_interface.primary_inside.private_ip
}

output "backup_inside_ip" {
  description = "Inside interface IP of backup FortiGate"
  value       = data.aws_network_interface.backup_inside.private_ip
}

output "primary_outside_ip" {
  description = "Outside interface IP of primary FortiGate"
  value       = data.aws_network_interface.primary_outside.private_ip
}

output "backup_outside_ip" {
  description = "Outside interface IP of backup FortiGate"
  value       = data.aws_network_interface.backup_outside.private_ip
}

output "primary_mgmt_ip" {
  description = "Management interface IP of primary FortiGate"
  value       = data.aws_network_interface.primary_mgmt.private_ip
}

output "backup_mgmt_ip" {
  description = "Management interface IP of backup FortiGate"
  value       = data.aws_network_interface.backup_mgmt.private_ip
}

output "primary_ha_ip" {
  description = "HA interface IP of primary FortiGate"
  value       = data.aws_network_interface.primary_ha.private_ip
}

output "backup_ha_ip" {
  description = "HA interface IP of backup FortiGate"
  value       = data.aws_network_interface.backup_ha.private_ip
}

# ENI Information
output "primary_outside_eni_id" {
  description = "ENI ID of primary FortiGate outside interface"
  value       = var.primary_outside_eni_id
}

output "primary_inside_eni_id" {
  description = "ENI ID of primary FortiGate inside interface"
  value       = var.primary_inside_eni_id
}

output "primary_ha_eni_id" {
  description = "ENI ID of primary FortiGate HA interface"
  value       = var.primary_ha_eni_id
}

output "primary_mgmt_eni_id" {
  description = "ENI ID of primary FortiGate management interface"
  value       = var.primary_mgmt_eni_id
}

output "backup_outside_eni_id" {
  description = "ENI ID of backup FortiGate outside interface"
  value       = var.backup_outside_eni_id
}

output "backup_inside_eni_id" {
  description = "ENI ID of backup FortiGate inside interface"
  value       = var.backup_inside_eni_id
}

output "backup_ha_eni_id" {
  description = "ENI ID of backup FortiGate HA interface"
  value       = var.backup_ha_eni_id
}

output "backup_mgmt_eni_id" {
  description = "ENI ID of backup FortiGate management interface"
  value       = var.backup_mgmt_eni_id
}

# Transit Gateway Information
output "transit_gateway_attachment_id" {
  description = "Transit Gateway VPC attachment ID"
  value       = data.aws_ec2_transit_gateway_vpc_attachment.existing.id
}

# HA Configuration Information
output "ha_configuration" {
  description = "HA configuration details"
  value = {
    primary_hostname   = var.fortigate_hostname_primary
    backup_hostname    = var.fortigate_hostname_backup
    primary_ha_ip      = data.aws_network_interface.primary_ha.private_ip
    backup_ha_ip       = data.aws_network_interface.backup_ha.private_ip
    bgp_asn           = var.bgp_asn
  }
  sensitive = false
}

# Elastic IP Information
output "primary_outside_eip" {
  description = "Elastic IP address for primary FortiGate outside interface"
  value       = var.allocate_eips ? (var.primary_outside_eip_id != "" ? data.aws_eip.primary_outside_existing[0].public_ip : aws_eip.primary_outside[0].public_ip) : null
}

output "backup_outside_eip" {
  description = "Elastic IP address for backup FortiGate outside interface"
  value       = var.allocate_eips ? (var.backup_outside_eip_id != "" ? data.aws_eip.backup_outside_existing[0].public_ip : aws_eip.backup_outside[0].public_ip) : null
}

output "primary_outside_eip_allocation_id" {
  description = "Elastic IP allocation ID for primary FortiGate outside interface"
  value       = var.allocate_eips ? (var.primary_outside_eip_id != "" ? data.aws_eip.primary_outside_existing[0].id : aws_eip.primary_outside[0].id) : null
}

output "backup_outside_eip_allocation_id" {
  description = "Elastic IP allocation ID for backup FortiGate outside interface"
  value       = var.allocate_eips ? (var.backup_outside_eip_id != "" ? data.aws_eip.backup_outside_existing[0].id : aws_eip.backup_outside[0].id) : null
}


# IAM Role and Instance Profile Information
output "iam_role_arn" {
  description = "ARN of IAM role for FortiGate EIP management (null if EIP failover disabled)"
  value       = var.enable_eip_failover ? aws_iam_role.fortigate_ha_eip_management[0].arn : null
}

output "iam_role_name" {
  description = "Name of IAM role for FortiGate EIP management (null if EIP failover disabled)"
  value       = var.enable_eip_failover ? aws_iam_role.fortigate_ha_eip_management[0].name : null
}

output "iam_instance_profile_name" {
  description = "Name of IAM instance profile attached to FortiGate instances (null if EIP failover disabled)"
  value       = var.enable_eip_failover ? aws_iam_instance_profile.fortigate_ha[0].name : null
}

output "iam_instance_profile_arn" {
  description = "ARN of IAM instance profile attached to FortiGate instances (null if EIP failover disabled)"
  value       = var.enable_eip_failover ? aws_iam_instance_profile.fortigate_ha[0].arn : null
}

output "eip_failover_enabled" {
  description = "Whether EIP failover is enabled for FortiGate HA"
  value       = var.enable_eip_failover
}
