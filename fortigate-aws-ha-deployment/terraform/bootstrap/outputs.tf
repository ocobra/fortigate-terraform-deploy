# Bootstrap Outputs

output "s3_bucket_name" {
  description = "Name of the S3 bucket for Terraform state"
  value       = module.state_management.s3_bucket_name
}

output "dynamodb_table_name" {
  description = "Name of the DynamoDB table for state locking"
  value       = module.state_management.dynamodb_table_name
}

output "backend_config" {
  description = "Backend configuration for main Terraform deployment"
  value       = module.state_management.backend_config
}

output "next_steps" {
  description = "Instructions for next steps"
  value = <<-EOT
    Bootstrap completed successfully!
    
    Next steps:
    1. Initialize the main Terraform configuration with remote backend:
       cd ../
       terraform init -backend-config="bucket=${module.state_management.s3_bucket_name}" \
                      -backend-config="key=fortigate-ha/terraform.tfstate" \
                      -backend-config="region=${var.aws_region}" \
                      -backend-config="encrypt=true" \
                      -backend-config="dynamodb_table=${module.state_management.dynamodb_table_name}"
    
    2. Run terraform plan and apply for the main deployment
    
    Backend Configuration:
    - S3 Bucket: ${module.state_management.s3_bucket_name}
    - DynamoDB Table: ${module.state_management.dynamodb_table_name}
    - Region: ${var.aws_region}
  EOT
}