# Transit Gateway Module

# Transit Gateway
resource "aws_ec2_transit_gateway" "main" {
  description                     = "FortiGate HA Transit Gateway"
  amazon_side_asn                 = var.amazon_side_asn
  default_route_table_association = "enable"
  default_route_table_propagation = "enable"
  dns_support                     = "enable"
  vpn_ecmp_support                = "enable"

  tags = {
    Name        = "fortigate-ha-tgw"
    Environment = var.environment
    Owner       = var.owner_tag
  }
}

# Transit Gateway Route Table
resource "aws_ec2_transit_gateway_route_table" "main" {
  transit_gateway_id = aws_ec2_transit_gateway.main.id

  tags = {
    Name        = "fortigate-ha-tgw-rt"
    Environment = var.environment
    Owner       = var.owner_tag
  }
}
