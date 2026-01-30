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
  value       = aws_network_interface.primary_inside.private_ip
}

output "backup_inside_ip" {
  description = "Inside interface IP of backup FortiGate"
  value       = aws_network_interface.backup_inside.private_ip
}

output "primary_outside_ip" {
  description = "Outside interface IP of primary FortiGate"
  value       = aws_network_interface.primary_outside.private_ip
}

output "backup_outside_ip" {
  description = "Outside interface IP of backup FortiGate"
  value       = aws_network_interface.backup_outside.private_ip
}

output "primary_mgmt_ip" {
  description = "Management interface IP of primary FortiGate"
  value       = aws_network_interface.primary_mgmt.private_ip
}

output "backup_mgmt_ip" {
  description = "Management interface IP of backup FortiGate"
  value       = aws_network_interface.backup_mgmt.private_ip
}

output "primary_ha_ip" {
  description = "HA interface IP of primary FortiGate"
  value       = aws_network_interface.primary_ha.private_ip
}

output "backup_ha_ip" {
  description = "HA interface IP of backup FortiGate"
  value       = aws_network_interface.backup_ha.private_ip
}

# ENI Information
output "primary_outside_eni_id" {
  description = "ENI ID of primary FortiGate outside interface"
  value       = aws_network_interface.primary_outside.id
}

output "primary_inside_eni_id" {
  description = "ENI ID of primary FortiGate inside interface"
  value       = aws_network_interface.primary_inside.id
}

output "primary_ha_eni_id" {
  description = "ENI ID of primary FortiGate HA interface"
  value       = aws_network_interface.primary_ha.id
}

output "primary_mgmt_eni_id" {
  description = "ENI ID of primary FortiGate management interface"
  value       = aws_network_interface.primary_mgmt.id
}

output "backup_outside_eni_id" {
  description = "ENI ID of backup FortiGate outside interface"
  value       = aws_network_interface.backup_outside.id
}

output "backup_inside_eni_id" {
  description = "ENI ID of backup FortiGate inside interface"
  value       = aws_network_interface.backup_inside.id
}

output "backup_ha_eni_id" {
  description = "ENI ID of backup FortiGate HA interface"
  value       = aws_network_interface.backup_ha.id
}

output "backup_mgmt_eni_id" {
  description = "ENI ID of backup FortiGate management interface"
  value       = aws_network_interface.backup_mgmt.id
}

# Transit Gateway Information
output "transit_gateway_attachment_id" {
  description = "Transit Gateway VPC attachment ID"
  value       = aws_ec2_transit_gateway_vpc_attachment.fortigate_attachment.id
}

# Route Table Information
output "inside_route_table_id" {
  description = "Route table ID for inside subnets"
  value       = aws_route_table.inside_primary.id
}

output "outside_route_table_id" {
  description = "Route table ID for outside subnets"
  value       = aws_route_table.outside_primary.id
}

# HA Configuration Information
output "ha_configuration" {
  description = "HA configuration details"
  value = {
    primary_hostname   = var.fortigate_hostname_primary
    backup_hostname    = var.fortigate_hostname_backup
    primary_ha_ip      = aws_network_interface.primary_ha.private_ip
    backup_ha_ip       = aws_network_interface.backup_ha.private_ip
    bgp_asn           = var.bgp_asn
  }
  sensitive = false
}