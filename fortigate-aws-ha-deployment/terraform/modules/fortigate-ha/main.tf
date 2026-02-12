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

# Transit Gateway VPC Attachment
resource "aws_ec2_transit_gateway_vpc_attachment" "fortigate_attachment" {
  subnet_ids         = [var.inside_subnet_primary, var.inside_subnet_backup]
  transit_gateway_id = var.transit_gateway_id
  vpc_id             = var.vpc_id
  
  tags = {
    Name        = "fortigate-ha-attachment"
    Environment = var.environment
    Owner       = var.owner_tag
  }
}

# Route Tables for Inside Subnets (for Transit Gateway routing)
resource "aws_route_table" "inside_primary" {
  vpc_id = var.vpc_id
  
  # Route to Transit Gateway for spoke traffic
  route {
    cidr_block         = "0.0.0.0/0"
    transit_gateway_id = var.transit_gateway_id
  }
  
  tags = {
    Name        = "fortigate-inside-primary-rt"
    Environment = var.environment
    Owner       = var.owner_tag
  }
}

resource "aws_route_table" "inside_backup" {
  vpc_id = var.vpc_id
  
  # Route to Transit Gateway for spoke traffic
  route {
    cidr_block         = "0.0.0.0/0"
    transit_gateway_id = var.transit_gateway_id
  }
  
  tags = {
    Name        = "fortigate-inside-backup-rt"
    Environment = var.environment
    Owner       = var.owner_tag
  }
}

# Route Table Associations
resource "aws_route_table_association" "inside_primary" {
  subnet_id      = var.inside_subnet_primary
  route_table_id = aws_route_table.inside_primary.id
}

resource "aws_route_table_association" "inside_backup" {
  subnet_id      = var.inside_subnet_backup
  route_table_id = aws_route_table.inside_backup.id
}

# Route Tables for Outside Subnets (for Internet Gateway routing)
resource "aws_route_table" "outside_primary" {
  vpc_id = var.vpc_id
  
  tags = {
    Name        = "fortigate-outside-primary-rt"
    Environment = var.environment
    Owner       = var.owner_tag
  }
}

resource "aws_route_table" "outside_backup" {
  vpc_id = var.vpc_id
  
  tags = {
    Name        = "fortigate-outside-backup-rt"
    Environment = var.environment
    Owner       = var.owner_tag
  }
}

# Route Table Associations for Outside Subnets
resource "aws_route_table_association" "outside_primary" {
  subnet_id      = var.outside_subnet_primary
  route_table_id = aws_route_table.outside_primary.id
}

resource "aws_route_table_association" "outside_backup" {
  subnet_id      = var.outside_subnet_backup
  route_table_id = aws_route_table.outside_backup.id
}