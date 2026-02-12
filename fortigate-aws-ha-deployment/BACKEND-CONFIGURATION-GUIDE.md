# Terraform Backend Configuration Guide

## Overview

The deploy.py script now supports both local and S3 backend configurations for Terraform state management. This guide explains how to use each option.

## Backend Options

### 1. Local Backend (Default)

Stores Terraform state file locally in the `terraform/` directory as `terraform.tfstate`.

**Pros:**
- Simple setup, no additional AWS resources needed
- Good for testing and development
- No additional costs

**Cons:**
- State file not shared across team members
- No state locking (risk of concurrent modifications)
- State file can be lost if local machine fails
- Not suitable for production deployments

**Usage:**
```bash
# Interactive mode (will prompt for backend type)
python3 deploy.py

# Or specify explicitly
python3 deploy.py --backend=local
```

### 2. S3 Backend with DynamoDB Locking (Recommended for Production)

Stores Terraform state in S3 bucket with DynamoDB table for state locking.

**Pros:**
- Centralized state management
- State locking prevents concurrent modifications
- State versioning and backup
- Team collaboration support
- Encrypted state storage
- Suitable for production deployments

**Cons:**
- Requires initial bootstrap setup
- Additional AWS resources (S3 bucket, DynamoDB table)
- Small additional costs for S3 and DynamoDB

## S3 Backend Setup

### Prerequisites

Before using S3 backend, you must create the S3 bucket and DynamoDB table using the bootstrap configuration.

### Step 1: Bootstrap State Management Infrastructure

Navigate to the bootstrap directory:

```bash
cd fortigate-aws-ha-deployment/terraform/bootstrap
```

### Step 2: Configure Bootstrap Variables

Copy the example variables file:

```bash
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars` with your values:

```hcl
# AWS Region
aws_region = "us-east-1"

# S3 Bucket Name (must be globally unique)
state_bucket_name = "my-company-fortigate-terraform-state"

# DynamoDB Table Name
dynamodb_table_name = "fortigate-terraform-locks"

# Environment
environment = "prod"

# Enable point-in-time recovery for DynamoDB
enable_point_in_time_recovery = true
```

### Step 3: Run Bootstrap

```bash
# Initialize Terraform (uses local state for bootstrap only)
terraform init

# Review the plan
terraform plan

# Apply the configuration
terraform apply
```

### Step 4: Note the Outputs

After successful bootstrap, note the outputs:

```
Outputs:

s3_bucket_name = "my-company-fortigate-terraform-state"
dynamodb_table_name = "fortigate-terraform-locks"
backend_config = {
  "bucket" = "my-company-fortigate-terraform-state"
  "dynamodb_table" = "fortigate-terraform-locks"
  "encrypt" = true
  "key" = "fortigate-ha/terraform.tfstate"
  "region" = "us-east-1"
}
```

## Using S3 Backend with deploy.py

### Method 1: Command-Line Options (Recommended)

```bash
python3 deploy.py \
  --backend=s3 \
  --s3-bucket=my-company-fortigate-terraform-state \
  --s3-region=us-east-1 \
  --dynamodb-table=fortigate-terraform-locks
```

Optional parameters:
```bash
python3 deploy.py \
  --backend=s3 \
  --s3-bucket=my-company-fortigate-terraform-state \
  --s3-key=fortigate-ha/prod/terraform.tfstate \
  --s3-region=us-east-1 \
  --dynamodb-table=fortigate-terraform-locks
```

### Method 2: Interactive Prompts

Run deploy.py without backend options and it will prompt you:

```bash
python3 deploy.py
```

You'll be prompted:
```
💾 Terraform Backend Configuration
==================================================
Backend type [local/s3] (local): s3

📦 S3 Backend Configuration
Note: S3 bucket and DynamoDB table should be created using terraform/bootstrap/

S3 bucket name (from bootstrap output): my-company-fortigate-terraform-state
S3 state file key [fortigate-ha/terraform.tfstate]: 
S3 bucket region [us-east-1]: 
DynamoDB table name (from bootstrap output) [fortigate-terraform-locks]: 
Encrypt state file? [Y/n]: y
Use AWS profile for backend? [Y/n]: y
AWS profile name [default]: renaws
```

### Method 3: Configuration File

Create a configuration file with backend settings:

```yaml
# config.yaml
aws:
  region: us-east-1
  profile: renaws

backend:
  backend_type: s3
  s3_bucket: my-company-fortigate-terraform-state
  s3_key: fortigate-ha/terraform.tfstate
  s3_region: us-east-1
  dynamodb_table: fortigate-terraform-locks
  encrypt: true
  s3_profile: renaws

# ... rest of configuration
```

Then use:
```bash
python3 deploy.py --config=config.yaml
```

## Backend Configuration Options

### S3 Backend Parameters

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `backend_type` | Yes | `local` | Backend type: `local` or `s3` |
| `s3_bucket` | Yes (for S3) | - | S3 bucket name for state storage |
| `s3_key` | No | `fortigate-ha/terraform.tfstate` | Path to state file in S3 bucket |
| `s3_region` | Yes (for S3) | - | AWS region where S3 bucket is located |
| `dynamodb_table` | Yes (for S3) | `fortigate-terraform-locks` | DynamoDB table for state locking |
| `encrypt` | No | `true` | Enable server-side encryption for state file |
| `s3_profile` | No | - | AWS profile to use for S3 backend |
| `kms_key_id` | No | - | KMS key ID for encryption (optional) |

## Switching Between Backends

### From Local to S3

1. Ensure bootstrap is complete
2. Run deploy.py with S3 backend options
3. Terraform will automatically migrate state

```bash
python3 deploy.py \
  --backend=s3 \
  --s3-bucket=my-company-fortigate-terraform-state \
  --s3-region=us-east-1 \
  --dynamodb-table=fortigate-terraform-locks
```

Terraform will prompt:
```
Do you want to copy existing state to the new backend?
  Pre-existing state was found while migrating the previous "local" backend to the
  newly configured "s3" backend. No existing state was found in the newly
  configured "s3" backend. Do you want to copy this state to the new "s3"
  backend? Enter "yes" to copy and "no" to start with an empty state.

  Enter a value: yes
```

### From S3 to Local

1. Run deploy.py with local backend
2. Terraform will migrate state back to local

```bash
python3 deploy.py --backend=local
```

## Verification

### Verify S3 Backend

Check that state file exists in S3:

```bash
aws s3 ls s3://my-company-fortigate-terraform-state/fortigate-ha/ --profile renaws
```

Check DynamoDB table:

```bash
aws dynamodb describe-table \
  --table-name fortigate-terraform-locks \
  --profile renaws \
  --region us-east-1
```

### Verify State Locking

When running Terraform operations, you should see state locking in action:

```
Acquiring state lock. This may take a few moments...
```

Check DynamoDB for lock entries:

```bash
aws dynamodb scan \
  --table-name fortigate-terraform-locks \
  --profile renaws \
  --region us-east-1
```

## Troubleshooting

### Issue: "Error acquiring the state lock"

**Cause**: Another Terraform operation is in progress or a previous operation didn't release the lock.

**Solution**:
1. Wait for other operations to complete
2. If stuck, manually remove lock from DynamoDB:

```bash
aws dynamodb delete-item \
  --table-name fortigate-terraform-locks \
  --key '{"LockID":{"S":"my-company-fortigate-terraform-state/fortigate-ha/terraform.tfstate-md5"}}' \
  --profile renaws \
  --region us-east-1
```

### Issue: "Error loading state: AccessDenied"

**Cause**: AWS credentials don't have permission to access S3 bucket or DynamoDB table.

**Solution**: Ensure your AWS profile has the required permissions:
- `s3:GetObject`, `s3:PutObject` on the state bucket
- `dynamodb:GetItem`, `dynamodb:PutItem`, `dynamodb:DeleteItem` on the lock table

### Issue: "Backend configuration changed"

**Cause**: Backend configuration in `backend.tf` doesn't match current state.

**Solution**: Run terraform init with `-reconfigure` flag (deploy.py does this automatically).

## Best Practices

### 1. Use S3 Backend for Production

Always use S3 backend with DynamoDB locking for production deployments to ensure:
- State consistency
- Team collaboration
- State backup and versioning

### 2. Separate State Files by Environment

Use different S3 keys for different environments:

```bash
# Production
--s3-key=fortigate-ha/prod/terraform.tfstate

# Staging
--s3-key=fortigate-ha/staging/terraform.tfstate

# Development
--s3-key=fortigate-ha/dev/terraform.tfstate
```

### 3. Enable Versioning on S3 Bucket

The bootstrap configuration automatically enables versioning. This allows you to recover from accidental state corruption.

### 4. Enable Point-in-Time Recovery for DynamoDB

Set `enable_point_in_time_recovery = true` in bootstrap configuration for additional protection.

### 5. Use KMS Encryption

For sensitive deployments, use KMS encryption:

```bash
python3 deploy.py \
  --backend=s3 \
  --s3-bucket=my-company-fortigate-terraform-state \
  --s3-region=us-east-1 \
  --dynamodb-table=fortigate-terraform-locks
```

Then when prompted, provide KMS key ID.

### 6. Restrict Access to State Bucket

Use IAM policies to restrict access to the state bucket:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::ACCOUNT-ID:role/TerraformRole"
      },
      "Action": [
        "s3:GetObject",
        "s3:PutObject"
      ],
      "Resource": "arn:aws:s3:::my-company-fortigate-terraform-state/*"
    }
  ]
}
```

## Quick Reference

### Show Bootstrap Information
```bash
python3 deploy.py --bootstrap-info
```

### Deploy with Local Backend
```bash
python3 deploy.py --backend=local
```

### Deploy with S3 Backend
```bash
python3 deploy.py \
  --backend=s3 \
  --s3-bucket=my-company-fortigate-terraform-state \
  --s3-region=us-east-1 \
  --dynamodb-table=fortigate-terraform-locks
```

### Plan Only with S3 Backend
```bash
python3 deploy.py \
  --plan-only \
  --backend=s3 \
  --s3-bucket=my-company-fortigate-terraform-state \
  --s3-region=us-east-1
```

### Destroy with S3 Backend
```bash
python3 deploy.py \
  --destroy \
  --backend=s3 \
  --s3-bucket=my-company-fortigate-terraform-state \
  --s3-region=us-east-1
```

---

**Last Updated**: 2026-02-12
**Status**: Complete ✅

