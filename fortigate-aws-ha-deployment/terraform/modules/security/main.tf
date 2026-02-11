# Security Module - Security Groups for FortiGate HA

# Security Group for FortiGate Management
resource "aws_security_group" "fortigate_mgmt" {
  name_prefix = "fortigate-mgmt-"
  description = "Security group for FortiGate management interface"
  vpc_id      = var.vpc_id

  # HTTPS access for management
  ingress {
    description = "HTTPS management access"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = var.mgmt_access_cidrs
  }

  # SSH access for management
  ingress {
    description = "SSH management access"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = var.mgmt_access_cidrs
  }

  # Allow all outbound
  egress {
    description = "Allow all outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "fortigate-mgmt-sg"
    Environment = var.environment
    Owner       = var.owner_tag
  }
}

# Security Group for FortiGate Data Plane (Outside/Inside)
resource "aws_security_group" "fortigate_data" {
  name_prefix = "fortigate-data-"
  description = "Security group for FortiGate data plane interfaces"
  vpc_id      = var.vpc_id

  # Allow all traffic for data plane
  ingress {
    description = "Allow all inbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Allow all outbound
  egress {
    description = "Allow all outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "fortigate-data-sg"
    Environment = var.environment
    Owner       = var.owner_tag
  }
}

# Security Group for FortiGate HA Sync
resource "aws_security_group" "fortigate_ha" {
  name_prefix = "fortigate-ha-"
  description = "Security group for FortiGate HA synchronization"
  vpc_id      = var.vpc_id

  # HA sync traffic
  ingress {
    description = "HA sync traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    self        = true
  }

  # Allow all outbound
  egress {
    description = "Allow all outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "fortigate-ha-sg"
    Environment = var.environment
    Owner       = var.owner_tag
  }
}
