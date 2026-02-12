# FortiGate AWS HA Deployment - Outputs
# Output values from the FortiGate HA deployment

# FortiGate Instance Information
output "fortigate_primary_instance_id" {
  description = "Instance ID of the primary FortiGate"
  value       = module.fortigate_ha.primary_instance_id
}

output "fortigate_backup_instance_id" {
  description = "Instance ID of the backup FortiGate"
  value       = module.fortigate_ha.backup_instance_id
}

output "fortigate_primary_private_ip" {
  description = "Primary private IP of the primary FortiGate (inside interface)"
  value       = module.fortigate_ha.primary_inside_ip
}

output "fortigate_backup_private_ip" {
  description = "Primary private IP of the backup FortiGate (inside interface)"
  value       = module.fortigate_ha.backup_inside_ip
}

output "fortigate_primary_mgmt_ip" {
  description = "Management IP of the primary FortiGate"
  value       = module.fortigate_ha.primary_mgmt_ip
}

output "fortigate_backup_mgmt_ip" {
  description = "Management IP of the backup FortiGate"
  value       = module.fortigate_ha.backup_mgmt_ip
}

# Network Interface Information
output "fortigate_primary_eni_ids" {
  description = "ENI IDs for primary FortiGate (outside, inside, ha, mgmt)"
  value = {
    outside = module.fortigate_ha.primary_outside_eni_id
    inside  = module.fortigate_ha.primary_inside_eni_id
    ha      = module.fortigate_ha.primary_ha_eni_id
    mgmt    = module.fortigate_ha.primary_mgmt_eni_id
  }
}

output "fortigate_backup_eni_ids" {
  description = "ENI IDs for backup FortiGate (outside, inside, ha, mgmt)"
  value = {
    outside = module.fortigate_ha.backup_outside_eni_id
    inside  = module.fortigate_ha.backup_inside_eni_id
    ha      = module.fortigate_ha.backup_ha_eni_id
    mgmt    = module.fortigate_ha.backup_mgmt_eni_id
  }
}

# Transit Gateway Information
output "transit_gateway_id" {
  description = "Transit Gateway ID (created or existing)"
  value       = var.create_transit_gateway ? module.transit_gateway[0].transit_gateway_id : var.existing_transit_gateway_id
}

output "transit_gateway_attachment_id" {
  description = "Transit Gateway VPC attachment ID"
  value       = module.fortigate_ha.transit_gateway_attachment_id
}

# Security Group Information
output "fortigate_security_group_ids" {
  description = "Security group IDs for FortiGate instances"
  value       = module.security.fortigate_security_group_ids
}

output "mgmt_security_group_id" {
  description = "Management security group ID"
  value       = module.security.mgmt_security_group_id
}

# Monitoring Information
output "cloudwatch_log_group_names" {
  description = "CloudWatch log group names"
  value       = module.monitoring.log_group_names
}

output "vpc_flow_logs_id" {
  description = "VPC Flow Logs ID"
  value       = module.monitoring.vpc_flow_logs_id
}

# BGP Configuration
output "bgp_configuration" {
  description = "BGP configuration details"
  value = {
    fortigate_asn         = var.bgp_asn
    transit_gateway_asn   = var.transit_gateway_asn
    spoke_vpc_cidrs       = var.spoke_vpc_cidrs
  }
  sensitive = false
}

# Deployment Information
output "deployment_summary" {
  description = "Summary of deployed resources"
  value = {
    vpc_id                = var.vpc_id
    availability_zones    = var.availability_zones
    fortigate_instances   = 2
    transit_gateway_mode  = var.create_transit_gateway ? "created" : "existing"
    monitoring_enabled    = var.enable_flow_logs
    environment          = var.environment
  }
}

# Connection Information
output "connection_info" {
  description = "Connection information for FortiGate management"
  value = {
    primary_mgmt_url   = "https://${module.fortigate_ha.primary_mgmt_ip}"
    backup_mgmt_url    = "https://${module.fortigate_ha.backup_mgmt_ip}"
    ssh_command_primary = "ssh -i ~/.ssh/${var.key_pair_name}.pem admin@${module.fortigate_ha.primary_mgmt_ip}"
    ssh_command_backup  = "ssh -i ~/.ssh/${var.key_pair_name}.pem admin@${module.fortigate_ha.backup_mgmt_ip}"
    primary_outside_public_ip = module.fortigate_ha.primary_outside_eip
    backup_outside_public_ip  = module.fortigate_ha.backup_outside_eip
  }
  sensitive = false
}

# Elastic IP Information
output "elastic_ips" {
  description = "Elastic IP addresses for outside interfaces"
  value = {
    primary_outside_eip = module.fortigate_ha.primary_outside_eip
    backup_outside_eip  = module.fortigate_ha.backup_outside_eip
    primary_eip_allocation_id = module.fortigate_ha.primary_outside_eip_allocation_id
    backup_eip_allocation_id  = module.fortigate_ha.backup_outside_eip_allocation_id
  }
}

# IAM Information (EIP Failover)
output "iam_configuration" {
  description = "IAM configuration for EIP failover"
  value = {
    iam_role_arn           = module.fortigate_ha.iam_role_arn
    iam_instance_profile   = module.fortigate_ha.iam_instance_profile_name
    eip_failover_enabled   = module.fortigate_ha.eip_failover_enabled
  }
}

# Route Table Information (for troubleshooting)
output "route_table_info" {
  description = "Route table information for troubleshooting"
  value = {
    inside_route_table_id  = module.fortigate_ha.inside_route_table_id
    outside_route_table_id = module.fortigate_ha.outside_route_table_id
  }
}