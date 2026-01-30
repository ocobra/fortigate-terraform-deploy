# FortiGate AWS HA Deployment - Bootstrap Configuration

## Overview

This bootstrap configuration creates the necessary AWS resources for Terraform state management before deploying the main FortiGate infrastructure. It creates:

- **S3 Bucket**: For storing Terraform state files with versioning and encryption
- **DynamoDB Table**: For Terraform state locking to prevent concurrent modifications

## Prerequisites

- AWS CLI configured with appropriate permissions
- Terraform >= 1.0 installed
- IAM permissions for creating S3 buckets and DynamoDB tables

## Required IAM Permissions

The user or role running the bootstrap must have these permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:CreateBucket",
        "s3:DeleteBucket",
        "s3:GetBucketVersioning",
        "s3:PutBucketVersioning",
        "s3:GetBucketEncryption",
        "s3:PutBucketEncryption",
        "s3:GetBucketPublicAccessBlock",
        "s3:PutBucketPublicAccessBlock",
        "s3:GetBucketPolicy",
        "s3:PutBucketPolicy",
        "dynamodb:CreateTable",
        "dynamodb:DeleteTable",
        "dynamodb:DescribeTable",
        "dynamodb:TagResource"
      ],
      "Resource": "*"
    }
  ]
}
```

## Usage

### Step 1: Configure Variables

1. Copy the example variables file:
   ```bash
   cp terraform.tfvars.example terraform.tfvars
   ```

2. Edit `terraform.tfvars` with your specific values:
   ```hcl
   aws_region = "us-east-1"
   state_bucket_name = "my-company-fortigate-terraform-state"
   dynamodb_table_name = "fortigate-terraform-locks"
   environment = "prod"
   ```

   **Important**: The S3 bucket name must be globally unique across all AWS accounts.

### Step 2: Run Bootstrap

1. Initialize Terraform:
   ```bash
   terraform init
   ```

2. Review the plan:
   ```bash
   terraform plan
   ```

3. Apply the configuration:
   ```bash
   terraform apply
   ```

4. Note the outputs - you'll need these for the main deployment:
   ```bash
   terraform output
   ```

### Step 3: Configure Main Deployment

After the bootstrap completes successfully, configure the main deployment to use remote state:

1. Navigate to the main Terraform directory:
   ```bash
   cd ../
   ```

2. Initialize with remote backend (use the values from bootstrap output):
   ```bash
   terraform init \
     -backend-config="bucket=your-bucket-name" \
     -backend-config="key=fortigate-ha/terraform.tfstate" \
     -backend-config="region=us-east-1" \
     -backend-config="encrypt=true" \
     -backend-config="dynamodb_table=fortigate-terraform-locks"
   ```

## Resources Created

### S3 Bucket
- **Purpose**: Store Terraform state files
- **Features**: 
  - Versioning enabled
  - Server-side encryption (AES256)
  - Public access blocked
  - Secure transport enforced

### DynamoDB Table
- **Purpose**: Terraform state locking
- **Configuration**:
  - Pay-per-request billing
  - Hash key: `LockID` (String)
  - Point-in-time recovery (optional)

## Security Considerations

1. **Bucket Access**: The S3 bucket is configured with:
   - Public access blocked
   - Secure transport required (HTTPS only)
   - Server-side encryption enabled

2. **State Locking**: DynamoDB table prevents concurrent Terraform operations

3. **IAM Permissions**: Follow least-privilege principle for accessing state resources

## Troubleshooting

### Common Issues

1. **S3 Bucket Name Already Exists**
   - S3 bucket names must be globally unique
   - Try a different bucket name with your organization prefix

2. **Insufficient Permissions**
   - Ensure your AWS credentials have the required IAM permissions
   - Check CloudTrail logs for specific permission denials

3. **Region Mismatch**
   - Ensure all resources are created in the same region
   - Update the `aws_region` variable if needed

### Cleanup

To destroy the bootstrap resources (⚠️ **WARNING**: This will delete your Terraform state!):

```bash
terraform destroy
```

**Note**: Only destroy bootstrap resources if you're completely removing the FortiGate deployment and no longer need the state files.

## Next Steps

After successful bootstrap:

1. Configure the main FortiGate deployment with remote backend
2. Run `terraform init` in the main directory with backend configuration
3. Proceed with FortiGate HA deployment

## Support

For issues with the bootstrap process:
1. Check AWS CloudTrail for API call failures
2. Verify IAM permissions
3. Ensure S3 bucket name is globally unique
4. Review Terraform logs for detailed error messages