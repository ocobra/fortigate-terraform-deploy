# Transit Gateway Module Variables

variable "amazon_side_asn" {
  description = "ASN for the Amazon side of the Transit Gateway"
  type        = number
  default     = 64512
}

variable "spoke_vpc_cidrs" {
  description = "List of spoke VPC CIDR blocks"
  type        = list(string)
  default     = []
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "owner_tag" {
  description = "Owner tag for resources"
  type        = string
}
