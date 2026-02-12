# FortiGate HA Module - Main Configuration
# Deploys a pair of FortiGate instances in HA configuration

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# Data sources for subnet information
data "aws_subnet" "outside_primary" {
  id = var.outside_subnet_primary
}

data "aws_subnet" "inside_primary" {
  id = var.inside_subnet_primary
}

data "aws_subnet" "ha_primary" {
  id = var.ha_subnet_primary
}

data "aws_subnet" "mgmt_primary" {
  id = var.mgmt_subnet_primary
}

data "aws_subnet" "outside_backup" {
  id = var.outside_subnet_backup
}

data "aws_subnet" "inside_backup" {
  id = var.inside_subnet_backup
}

data "aws_subnet" "ha_backup" {
  id = var.ha_subnet_backup
}

data "aws_subnet" "mgmt_backup" {
  id = var.mgmt_subnet_backup
}

# Data sources for pre-created ENIs
data "aws_network_interface" "primary_outside" {
  id = var.primary_outside_eni_id
}

data "aws_network_interface" "primary_inside" {
  id = var.primary_inside_eni_id
}

data "aws_network_interface" "primary_ha" {
  id = var.primary_ha_eni_id
}

data "aws_network_interface" "primary_mgmt" {
  id = var.primary_mgmt_eni_id
}

data "aws_network_interface" "backup_outside" {
  id = var.backup_outside_eni_id
}

data "aws_network_interface" "backup_inside" {
  id = var.backup_inside_eni_id
}

data "aws_network_interface" "backup_ha" {
  id = var.backup_ha_eni_id
}

data "aws_network_interface" "backup_mgmt" {
  id = var.backup_mgmt_eni_id
}

# Primary FortiGate Instance
resource "aws_instance" "fortigate_primary" {
  ami                     = var.fortigate_ami_id
  instance_type          = var.instance_type
  key_name               = var.key_pair_name
  availability_zone      = data.aws_subnet.outside_primary.availability_zone
  subnet_id              = data.aws_subnet.outside_primary.id
  vpc_security_group_ids = var.security_group_ids
  
  # Disable source/destination check for routing
  source_dest_check = false
  
  # Enable detailed monitoring if requested
  monitoring = var.enable_detailed_monitoring
  
  # Basic user data - detailed config will be applied post-deployment
  user_data = base64encode(templatefile("${path.module}/templates/fortigate-primary-config.tpl", {
    hostname        = var.fortigate_hostname_primary
    admin_password  = var.admin_password
    ha_password     = var.ha_password
    bgp_asn         = var.bgp_asn
    ha_peer_ip      = data.aws_network_interface.backup_ha.private_ip
    inside_ip       = data.aws_network_interface.primary_inside.private_ip
    inside_netmask  = cidrnetmask(data.aws_subnet.inside_primary.cidr_block)
    outside_ip      = data.aws_network_interface.primary_outside.private_ip
    outside_netmask = cidrnetmask(data.aws_subnet.outside_primary.cidr_block)
    ha_ip           = data.aws_network_interface.primary_ha.private_ip
    ha_netmask      = cidrnetmask(data.aws_subnet.ha_primary.cidr_block)
    mgmt_ip         = data.aws_network_interface.primary_mgmt.private_ip
    mgmt_netmask    = cidrnetmask(data.aws_subnet.mgmt_primary.cidr_block)
    default_gateway = cidrhost(data.aws_subnet.outside_primary.cidr_block, 1)
  }))
  
  tags = {
    Name        = "${var.fortigate_hostname_primary}"
    Role        = "FortiGate-Primary"
    Environment = var.environment
    Owner       = var.owner_tag
  }
  
  lifecycle {
    create_before_destroy = true
    ignore_changes = [user_data]  # Ignore changes after initial creation
  }
}

# Backup FortiGate Instance
resource "aws_instance" "fortigate_backup" {
  ami                     = var.fortigate_ami_id
  instance_type          = var.instance_type
  key_name               = var.key_pair_name
  availability_zone      = data.aws_subnet.outside_backup.availability_zone
  subnet_id              = data.aws_subnet.outside_backup.id
  vpc_security_group_ids = var.security_group_ids
  
  # Disable source/destination check for routing
  source_dest_check = false
  
  # Enable detailed monitoring if requested
  monitoring = var.enable_detailed_monitoring
  
  # Basic user data - detailed config will be applied post-deployment
  user_data = base64encode(templatefile("${path.module}/templates/fortigate-backup-config.tpl", {
    hostname        = var.fortigate_hostname_backup
    admin_password  = var.admin_password
    ha_password     = var.ha_password
    bgp_asn         = var.bgp_asn
    ha_peer_ip      = data.aws_network_interface.primary_ha.private_ip
    inside_ip       = data.aws_network_interface.backup_inside.private_ip
    inside_netmask  = cidrnetmask(data.aws_subnet.inside_backup.cidr_block)
    outside_ip      = data.aws_network_interface.backup_outside.private_ip
    outside_netmask = cidrnetmask(data.aws_subnet.outside_backup.cidr_block)
    ha_ip           = data.aws_network_interface.backup_ha.private_ip
    ha_netmask      = cidrnetmask(data.aws_subnet.ha_backup.cidr_block)
    mgmt_ip         = data.aws_network_interface.backup_mgmt.private_ip
    mgmt_netmask    = cidrnetmask(data.aws_subnet.mgmt_backup.cidr_block)
    default_gateway = cidrhost(data.aws_subnet.outside_backup.cidr_block, 1)
  }))
  
  tags = {
    Name        = "${var.fortigate_hostname_backup}"
    Role        = "FortiGate-Backup"
    Environment = var.environment
    Owner       = var.owner_tag
  }
  
  lifecycle {
    create_before_destroy = true
    ignore_changes = [user_data]  # Ignore changes after initial creation
  }
}

# Attach Network Interfaces to Primary FortiGate
resource "aws_network_interface_attachment" "primary_outside" {
  instance_id          = aws_instance.fortigate_primary.id
  network_interface_id = var.primary_outside_eni_id
  device_index         = 1
}

resource "aws_network_interface_attachment" "primary_inside" {
  instance_id          = aws_instance.fortigate_primary.id
  network_interface_id = var.primary_inside_eni_id
  device_index         = 2
}

resource "aws_network_interface_attachment" "primary_ha" {
  instance_id          = aws_instance.fortigate_primary.id
  network_interface_id = var.primary_ha_eni_id
  device_index         = 3
}

resource "aws_network_interface_attachment" "primary_mgmt" {
  instance_id          = aws_instance.fortigate_primary.id
  network_interface_id = var.primary_mgmt_eni_id
  device_index         = 4
}

# Attach Network Interfaces to Backup FortiGate
resource "aws_network_interface_attachment" "backup_outside" {
  instance_id          = aws_instance.fortigate_backup.id
  network_interface_id = var.backup_outside_eni_id
  device_index         = 1
}

resource "aws_network_interface_attachment" "backup_inside" {
  instance_id          = aws_instance.fortigate_backup.id
  network_interface_id = var.backup_inside_eni_id
  device_index         = 2
}

resource "aws_network_interface_attachment" "backup_ha" {
  instance_id          = aws_instance.fortigate_backup.id
  network_interface_id = var.backup_ha_eni_id
  device_index         = 3
}

resource "aws_network_interface_attachment" "backup_mgmt" {
  instance_id          = aws_instance.fortigate_backup.id
  network_interface_id = var.backup_mgmt_eni_id
  device_index         = 4
}

# Transit Gateway VPC Attachment - Use existing attachment
data "aws_ec2_transit_gateway_vpc_attachment" "existing" {
  filter {
    name   = "vpc-id"
    values = [var.vpc_id]
  }
  
  filter {
    name   = "transit-gateway-id"
    values = [var.transit_gateway_id]
  }
  
  filter {
    name   = "state"
    values = ["available", "pending"]
  }
}

# Route Tables - Use existing route tables
data "aws_route_table" "inside_primary" {
  filter {
    name   = "association.subnet-id"
    values = [var.inside_subnet_primary]
  }
}

data "aws_route_table" "inside_backup" {
  filter {
    name   = "association.subnet-id"
    values = [var.inside_subnet_backup]
  }
}

data "aws_route_table" "outside_primary" {
  filter {
    name   = "association.subnet-id"
    values = [var.outside_subnet_primary]
  }
}

data "aws_route_table" "outside_backup" {
  filter {
    name   = "association.subnet-id"
    values = [var.outside_subnet_backup]
  }
}

# Elastic IP for Primary FortiGate Outside Interface
resource "aws_eip" "primary_outside" {
  count  = var.allocate_eips && var.primary_outside_eip_id == "" ? 1 : 0
  domain = "vpc"
  
  tags = {
    Name        = "fortigate-primary-outside-eip"
    Environment = var.environment
    Owner       = var.owner_tag
    FortiGateRole = "primary"
    Interface   = "outside"
  }
}

# Use existing EIP if provided
data "aws_eip" "primary_outside_existing" {
  count = var.allocate_eips && var.primary_outside_eip_id != "" ? 1 : 0
  id    = var.primary_outside_eip_id
}

# Associate EIP with Primary Outside ENI
resource "aws_eip_association" "primary_outside" {
  count                = var.allocate_eips ? 1 : 0
  allocation_id        = var.primary_outside_eip_id != "" ? data.aws_eip.primary_outside_existing[0].id : aws_eip.primary_outside[0].id
  network_interface_id = var.primary_outside_eni_id
}

# Elastic IP for Backup FortiGate Outside Interface
resource "aws_eip" "backup_outside" {
  count  = var.allocate_eips && var.backup_outside_eip_id == "" ? 1 : 0
  domain = "vpc"
  
  tags = {
    Name        = "fortigate-backup-outside-eip"
    Environment = var.environment
    Owner       = var.owner_tag
    FortiGateRole = "backup"
    Interface   = "outside"
  }
}

# Use existing EIP if provided
data "aws_eip" "backup_outside_existing" {
  count = var.allocate_eips && var.backup_outside_eip_id != "" ? 1 : 0
  id    = var.backup_outside_eip_id
}

# Associate EIP with Backup Outside ENI
resource "aws_eip_association" "backup_outside" {
  count                = var.allocate_eips ? 1 : 0
  allocation_id        = var.backup_outside_eip_id != "" ? data.aws_eip.backup_outside_existing[0].id : aws_eip.backup_outside[0].id
  network_interface_id = var.backup_outside_eni_id
}