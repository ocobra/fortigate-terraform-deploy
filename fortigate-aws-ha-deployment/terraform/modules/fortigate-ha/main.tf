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

# ============================================================================
# IAM Role and Instance Profile for FortiGate HA EIP Management
# ============================================================================

# IAM Role for FortiGate HA EIP Management
resource "aws_iam_role" "fortigate_ha_eip_management" {
  count = var.enable_eip_failover ? 1 : 0
  name  = "fortigate-ha-eip-management-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "ec2.amazonaws.com"
      }
    }]
  })

  tags = {
    Name        = "fortigate-ha-eip-management-role"
    Environment = var.environment
    Owner       = var.owner_tag
    ManagedBy   = "Terraform"
    Project     = "FortiGate-HA-Deployment"
  }
}

# IAM Policy for FortiGate EIP Management
resource "aws_iam_role_policy" "fortigate_eip_management" {
  count = var.enable_eip_failover ? 1 : 0
  name  = "fortigate-eip-management-policy"
  role  = aws_iam_role.fortigate_ha_eip_management[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "FortiGateDescribeResources"
        Effect = "Allow"
        Action = [
          "ec2:DescribeInstances",
          "ec2:DescribeNetworkInterfaces",
          "ec2:DescribeAddresses",
          "ec2:DescribeVpcs",
          "ec2:DescribeSubnets",
          "ec2:DescribeRouteTables"
        ]
        Resource = "*"
      },
      {
        Sid    = "FortiGateManageEIPs"
        Effect = "Allow"
        Action = [
          "ec2:AssociateAddress",
          "ec2:DisassociateAddress"
        ]
        Resource = "*"
      },
      {
        Sid    = "FortiGateManageNetworkInterfaces"
        Effect = "Allow"
        Action = [
          "ec2:AssignPrivateIpAddresses",
          "ec2:UnassignPrivateIpAddresses"
        ]
        Resource = "*"
      },
      {
        Sid    = "FortiGateManageRoutes"
        Effect = "Allow"
        Action = [
          "ec2:ReplaceRoute",
          "ec2:CreateRoute",
          "ec2:DeleteRoute"
        ]
        Resource = "*"
      }
    ]
  })
}

# IAM Instance Profile
resource "aws_iam_instance_profile" "fortigate_ha" {
  count = var.enable_eip_failover ? 1 : 0
  name  = "fortigate-ha-instance-profile"
  role  = aws_iam_role.fortigate_ha_eip_management[0].name

  tags = {
    Name        = "fortigate-ha-instance-profile"
    Environment = var.environment
    Owner       = var.owner_tag
    ManagedBy   = "Terraform"
    Project     = "FortiGate-HA-Deployment"
  }
}

# ============================================================================
# Data sources for subnet information
# ============================================================================
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
  iam_instance_profile   = var.enable_eip_failover ? aws_iam_instance_profile.fortigate_ha[0].name : null
  availability_zone      = data.aws_subnet.outside_primary.availability_zone
  
  # Use pre-created outside ENI as primary network interface (device index 0)
  network_interface {
    network_interface_id = var.primary_outside_eni_id
    device_index         = 0
  }
  
  # Enable detailed monitoring if requested
  monitoring = var.enable_detailed_monitoring
  
  # Basic user data - detailed config will be applied post-deployment
  user_data = base64encode(templatefile("${path.module}/templates/fortigate-primary-config.tpl", {
    hostname        = var.fortigate_hostname_primary
    admin_password  = var.admin_password
    ha_password     = var.ha_password
    bgp_asn         = var.bgp_asn
    aws_region      = var.aws_region
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
    inside_gateway  = cidrhost(data.aws_subnet.inside_primary.cidr_block, 1)
    mgmt_gateway    = cidrhost(data.aws_subnet.mgmt_primary.cidr_block, 1)
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
  iam_instance_profile   = var.enable_eip_failover ? aws_iam_instance_profile.fortigate_ha[0].name : null
  availability_zone      = data.aws_subnet.outside_backup.availability_zone
  
  # Use pre-created outside ENI as primary network interface (device index 0)
  network_interface {
    network_interface_id = var.backup_outside_eni_id
    device_index         = 0
  }
  
  # Enable detailed monitoring if requested
  monitoring = var.enable_detailed_monitoring
  
  # Basic user data - detailed config will be applied post-deployment
  user_data = base64encode(templatefile("${path.module}/templates/fortigate-backup-config.tpl", {
    hostname        = var.fortigate_hostname_backup
    admin_password  = var.admin_password
    ha_password     = var.ha_password
    bgp_asn         = var.bgp_asn
    aws_region      = var.aws_region
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
    inside_gateway  = cidrhost(data.aws_subnet.inside_backup.cidr_block, 1)
    mgmt_gateway    = cidrhost(data.aws_subnet.mgmt_backup.cidr_block, 1)
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
# Note: Outside interface (device index 0) is attached at instance creation

resource "aws_network_interface_attachment" "primary_inside" {
  instance_id          = aws_instance.fortigate_primary.id
  network_interface_id = var.primary_inside_eni_id
  device_index         = 1
}

resource "aws_network_interface_attachment" "primary_ha" {
  instance_id          = aws_instance.fortigate_primary.id
  network_interface_id = var.primary_ha_eni_id
  device_index         = 2
}

resource "aws_network_interface_attachment" "primary_mgmt" {
  instance_id          = aws_instance.fortigate_primary.id
  network_interface_id = var.primary_mgmt_eni_id
  device_index         = 3
}

# Attach Network Interfaces to Backup FortiGate
# Note: Outside interface (device index 0) is attached at instance creation

resource "aws_network_interface_attachment" "backup_inside" {
  instance_id          = aws_instance.fortigate_backup.id
  network_interface_id = var.backup_inside_eni_id
  device_index         = 1
}

resource "aws_network_interface_attachment" "backup_ha" {
  instance_id          = aws_instance.fortigate_backup.id
  network_interface_id = var.backup_ha_eni_id
  device_index         = 2
}

resource "aws_network_interface_attachment" "backup_mgmt" {
  instance_id          = aws_instance.fortigate_backup.id
  network_interface_id = var.backup_mgmt_eni_id
  device_index         = 3
}

# Disable source/destination check on ENIs for routing
# Using null_resource with triggers for idempotency
resource "null_resource" "disable_source_dest_check_primary_outside" {
  triggers = {
    eni_id      = var.primary_outside_eni_id
    instance_id = aws_instance.fortigate_primary.id
    region      = var.aws_region
    profile     = var.aws_profile
  }
  
  provisioner "local-exec" {
    command = var.aws_profile != "" ? "aws ec2 modify-network-interface-attribute --network-interface-id ${var.primary_outside_eni_id} --no-source-dest-check --region ${var.aws_region} --profile ${var.aws_profile}" : "aws ec2 modify-network-interface-attribute --network-interface-id ${var.primary_outside_eni_id} --no-source-dest-check --region ${var.aws_region}"
  }
  
  provisioner "local-exec" {
    when    = destroy
    command = self.triggers.profile != "" ? "aws ec2 modify-network-interface-attribute --network-interface-id ${self.triggers.eni_id} --source-dest-check --region ${self.triggers.region} --profile ${self.triggers.profile}" : "aws ec2 modify-network-interface-attribute --network-interface-id ${self.triggers.eni_id} --source-dest-check --region ${self.triggers.region}"
  }
  
  depends_on = [aws_instance.fortigate_primary]
}

resource "null_resource" "disable_source_dest_check_primary_inside" {
  triggers = {
    eni_id      = var.primary_inside_eni_id
    instance_id = aws_instance.fortigate_primary.id
    region      = var.aws_region
    profile     = var.aws_profile
  }
  
  provisioner "local-exec" {
    command = var.aws_profile != "" ? "aws ec2 modify-network-interface-attribute --network-interface-id ${var.primary_inside_eni_id} --no-source-dest-check --region ${var.aws_region} --profile ${var.aws_profile}" : "aws ec2 modify-network-interface-attribute --network-interface-id ${var.primary_inside_eni_id} --no-source-dest-check --region ${var.aws_region}"
  }
  
  provisioner "local-exec" {
    when    = destroy
    command = self.triggers.profile != "" ? "aws ec2 modify-network-interface-attribute --network-interface-id ${self.triggers.eni_id} --source-dest-check --region ${self.triggers.region} --profile ${self.triggers.profile}" : "aws ec2 modify-network-interface-attribute --network-interface-id ${self.triggers.eni_id} --source-dest-check --region ${self.triggers.region}"
  }
  
  depends_on = [aws_network_interface_attachment.primary_inside]
}

resource "null_resource" "disable_source_dest_check_backup_outside" {
  triggers = {
    eni_id      = var.backup_outside_eni_id
    instance_id = aws_instance.fortigate_backup.id
    region      = var.aws_region
    profile     = var.aws_profile
  }
  
  provisioner "local-exec" {
    command = var.aws_profile != "" ? "aws ec2 modify-network-interface-attribute --network-interface-id ${var.backup_outside_eni_id} --no-source-dest-check --region ${var.aws_region} --profile ${var.aws_profile}" : "aws ec2 modify-network-interface-attribute --network-interface-id ${var.backup_outside_eni_id} --no-source-dest-check --region ${var.aws_region}"
  }
  
  provisioner "local-exec" {
    when    = destroy
    command = self.triggers.profile != "" ? "aws ec2 modify-network-interface-attribute --network-interface-id ${self.triggers.eni_id} --source-dest-check --region ${self.triggers.region} --profile ${self.triggers.profile}" : "aws ec2 modify-network-interface-attribute --network-interface-id ${self.triggers.eni_id} --source-dest-check --region ${self.triggers.region}"
  }
  
  depends_on = [aws_instance.fortigate_backup]
}

resource "null_resource" "disable_source_dest_check_backup_inside" {
  triggers = {
    eni_id      = var.backup_inside_eni_id
    instance_id = aws_instance.fortigate_backup.id
    region      = var.aws_region
    profile     = var.aws_profile
  }
  
  provisioner "local-exec" {
    command = var.aws_profile != "" ? "aws ec2 modify-network-interface-attribute --network-interface-id ${var.backup_inside_eni_id} --no-source-dest-check --region ${var.aws_region} --profile ${var.aws_profile}" : "aws ec2 modify-network-interface-attribute --network-interface-id ${var.backup_inside_eni_id} --no-source-dest-check --region ${var.aws_region}"
  }
  
  provisioner "local-exec" {
    when    = destroy
    command = self.triggers.profile != "" ? "aws ec2 modify-network-interface-attribute --network-interface-id ${self.triggers.eni_id} --source-dest-check --region ${self.triggers.region} --profile ${self.triggers.profile}" : "aws ec2 modify-network-interface-attribute --network-interface-id ${self.triggers.eni_id} --source-dest-check --region ${self.triggers.region}"
  }
  
  depends_on = [aws_network_interface_attachment.backup_inside]
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

# ============================================================================
# Elastic IP Resources for OUTSIDE Interfaces
# NOTE: EIPs are allocated but NOT associated when enable_eip_failover=true
# FortiGate HA will manage EIP associations via AWS SDN connector
# ============================================================================

# Elastic IP for Primary FortiGate Outside Interface
resource "aws_eip" "primary_outside" {
  count  = var.allocate_eips && var.primary_outside_eip_id == "" ? 1 : 0
  domain = "vpc"
  
  tags = {
    Name          = "fortigate-primary-outside-eip"
    Environment   = var.environment
    Owner         = var.owner_tag
    FortiGateRole = "primary"
    Interface     = "outside"
    ManagedBy     = "FortiGate-HA"  # Required for IAM policy condition
  }
}

# Use existing EIP if provided
data "aws_eip" "primary_outside_existing" {
  count = var.allocate_eips && var.primary_outside_eip_id != "" ? 1 : 0
  id    = var.primary_outside_eip_id
}

# NOTE: EIP Association removed - FortiGate HA manages this via AWS SDN connector
# When enable_eip_failover=true, EIPs are allocated but not statically associated
# This allows FortiGate to move EIPs between primary and backup during failover

# Elastic IP for Backup FortiGate Outside Interface
resource "aws_eip" "backup_outside" {
  count  = var.allocate_eips && var.backup_outside_eip_id == "" ? 1 : 0
  domain = "vpc"
  
  tags = {
    Name          = "fortigate-backup-outside-eip"
    Environment   = var.environment
    Owner         = var.owner_tag
    FortiGateRole = "backup"
    Interface     = "outside"
    ManagedBy     = "FortiGate-HA"  # Required for IAM policy condition
  }
}

# Use existing EIP if provided
data "aws_eip" "backup_outside_existing" {
  count = var.allocate_eips && var.backup_outside_eip_id != "" ? 1 : 0
  id    = var.backup_outside_eip_id
}

# NOTE: EIP Association removed - FortiGate HA manages this via AWS SDN connector
# When enable_eip_failover=true, EIPs are allocated but not statically associated
# This allows FortiGate to move EIPs between primary and backup during failover