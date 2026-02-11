# Transit Gateway Module Outputs

output "transit_gateway_id" {
  description = "Transit Gateway ID"
  value       = aws_ec2_transit_gateway.main.id
}

output "transit_gateway_arn" {
  description = "Transit Gateway ARN"
  value       = aws_ec2_transit_gateway.main.arn
}

output "transit_gateway_route_table_id" {
  description = "Transit Gateway route table ID"
  value       = aws_ec2_transit_gateway_route_table.main.id
}

output "transit_gateway_asn" {
  description = "Transit Gateway ASN"
  value       = aws_ec2_transit_gateway.main.amazon_side_asn
}
