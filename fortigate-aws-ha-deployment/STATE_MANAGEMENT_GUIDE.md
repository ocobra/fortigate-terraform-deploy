# FortiGate AWS HA Deployment - Terraform State Management Guide

## Overview

This guide provides comprehensive instructions for setting up and using Terraform remote state management with S3 and DynamoDB for the FortiGate AWS HA deployment. Remote state management is **required** for production deployments to enable team collaboration, state locking, and disaster recovery.

## Table of Contents

1. [Why Remote State Management?](#why-remote-state-management)
2. [Architecture](#architecture)
3. [Prerequisites](#prerequisites)
4. [Step-by-Step Setup](#step-by-step-setup)
5. [Using Remote State](#using-remote-state)
6. [State Operations](#state-operations)
7. [Troubleshooting](#troubleshooting)
8. [Security Considerations](#security-considerations)

## Why Remote State Management?

### Problems with Local State

Without remote state management, Terraform stores state files locally on your machine, which creates several critical issues:

1. **No Team Collaboration**: Other team members can't access or modify the infrastructure
2. **No Backup**: If your laptop crashes, you lose the state file and can't manage resources
3. **Race Conditions**: Multiple people running Terraform simultaneously can corrupt state
4. **Security Risks**: State files contain sensitive data (passwords, IPs) stored on local disk
5. **No History**: Can't track changes or rollback to previous states

### Benefits of Remote State with S3 + DynamoDB

- **S3 Bucket**: Centralized, durable storage with versioning and encryption
- **DynamoDB Table**: State locking prevents concurrent modifications
- **Team Collaboration**: Multiple team members can safely work together
- **Disaster Recovery**: State files are backed up and versioned
- **Audit Trail**: Track all state changes with S3 versioning
- **Security**: Encryption at rest and in transit, IAM-controlled access

**Cost**: Approximately $1-2/month for enterprise-grade state management

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Terraform Workflow                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Developer 1                Developer 2                      │
│      │                          │                            │
│      │ terraform apply          │ terraform apply            │
│      ▼                          ▼                            │
│  ┌────────────────────────────────────────┐                 │
│  │      DynamoDB State Lock Table         │                 │
│  │  (Prevents concurrent modifications)   │                 │
│  └────────────────────────────────────────┘                 │
│                     │                                        │
│                     ▼                                        │
│  ┌────────────────────────────────────────┐                 │
│  │         S3 State Bucket                │                 │
│  │  • Versioning enabled                  │                 │
│  │  • Encryption at rest (AES256)         │                 │
│  │  • Public access blocked               │                 │
│  │  • Secure transport enforced           │                 │
│  └────────────────────────────────────────┘                 │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Prerequisites

Before setting up state management, ensure you have:

- **AWS CLI**: Configured with appropriate credentials
- **Terraform**: Version 1.0 or higher installed
- **IAM Permissions**: Ability to create S3 buckets and DynamoDB tables
- **AWS Account**: Access to the target AWS account

## Step-by-Step Setup

### Phase 1: Bootstrap State Management Infrastructure

The bootstrap process creates the S3 bucket and DynamoDB table needed for state management.

#### Step 1.1: Navigate to Bootstrap Directory

```bash
cd fortigate-aws-ha-deployment/terraform/bootstrap
```

#### Step 1.2: Configure Bootstrap Variables

Copy the example variables file:

```bash
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars` with your specific values:

```hcl
# AWS Configuration
aws_region = "us-east-1"

# State Management Resources
state_bucket_name = "my-company-fortigate-terraform-state"
dynamodb_table_name = "fortigate-terraform-locks"

# Environment Tag
environment = "prod"

# Optional: Enable point-in-time recovery for DynamoDB
enable_point_in_time_recovery = true
```

**Important Notes:**
- The S3 bucket name must be **globally unique** across all AWS accounts
- Use a naming convention like: `{company}-{project}-terraform-state`
- The DynamoDB table name should match what's configured in the main deployment

#### Step 1.3: Review IAM Permissions

Ensure your AWS credentials have the required permissions. See the [IAM_AND_SECURITY_REQUIREMENTS.md](IAM_AND_SECURITY_REQUIREMENTS.md) document for the complete bootstrap IAM policy.

Minimum required permissions:
- `s3:CreateBucket`, `s3:PutBucketVersioning`, `s3:PutBucketEncryption`
- `dynamodb:CreateTable`, `dynamodb:DescribeTable`

#### Step 1.4: Initialize and Apply Bootstrap

```bash
# Initialize Terraform (uses local state for bootstrap only)
terraform init

# Review what will be created
terraform plan

# Create the state management resources
terraform apply
```

Review the plan carefully and type `yes` to confirm.

#### Step 1.5: Capture Bootstrap Outputs

After successful apply, note the outputs:

```bash
terraform output
```

You'll see output like:

```
state_bucket_name = "my-company-fortigate-terraform-state"
state_bucket_arn = "arn:aws:s3:::my-company-fortigate-terraform-state"
dynamodb_table_name = "fortigate-terraform-locks"
dynamodb_table_arn = "arn:aws:dynamodb:us-east-1:123456789012:table/fortigate-terraform-locks"
```

**Save these values** - you'll need them for the main deployment configuration.

### Phase 2: Configure Main Deployment to Use Remote State

Now that the state management infrastructure exists, configure the main FortiGate deployment to use it.

#### Step 2.1: Navigate to Main Terraform Directory

```bash
cd ../  # Go back to terraform/ directory
```

#### Step 2.2: Verify Backend Configuration

Check that `main.tf` has the correct backend configuration:

```hcl
terraform {
  backend "s3" {
    # These values will be provided during terraform init
    # bucket         = "my-company-fortigate-terraform-state"
    # key            = "fortigate-ha/terraform.tfstate"
    # region         = "us-east-1"
    # encrypt        = true
    # dynamodb_table = "fortigate-terraform-locks"
  }
}
```

#### Step 2.3: Initialize with Remote Backend

Initialize Terraform with backend configuration using the values from bootstrap output:

```bash
terraform init \
  -backend-config="bucket=my-company-fortigate-terraform-state" \
  -backend-config="key=fortigate-ha/terraform.tfstate" \
  -backend-config="region=us-east-1" \
  -backend-config="encrypt=true" \
  -backend-config="dynamodb_table=fortigate-terraform-locks"
```

**Alternative: Create a Backend Config File**

You can also create a `backend.hcl` file:

```hcl
bucket         = "my-company-fortigate-terraform-state"
key            = "fortigate-ha/terraform.tfstate"
region         = "us-east-1"
encrypt        = true
dynamodb_table = "fortigate-terraform-locks"
```

Then initialize with:

```bash
terraform init -backend-config=backend.hcl
```

#### Step 2.4: Verify Remote State Configuration

After initialization, verify the backend is configured correctly:

```bash
terraform state list
```

If this is a fresh deployment, the list will be empty. That's expected.

Check the S3 bucket to confirm the state file location:

```bash
aws s3 ls s3://my-company-fortigate-terraform-state/fortigate-ha/
```

## Using Remote State

### Normal Terraform Operations

Once remote state is configured, use Terraform normally:

```bash
# Plan changes
terraform plan

# Apply changes (state locking happens automatically)
terraform apply

# View current state
terraform show

# List resources
terraform state list
```

### State Locking in Action

When you run `terraform apply`, Terraform automatically:

1. **Acquires Lock**: Creates a lock entry in DynamoDB
2. **Reads State**: Downloads current state from S3
3. **Makes Changes**: Applies infrastructure changes
4. **Updates State**: Uploads new state to S3
5. **Releases Lock**: Removes lock entry from DynamoDB

If another team member tries to run Terraform while you have the lock:

```
Error: Error acquiring the state lock

Error message: ConditionalCheckFailedException: The conditional request failed
Lock Info:
  ID:        a1b2c3d4-e5f6-7890-abcd-ef1234567890
  Path:      my-company-fortigate-terraform-state/fortigate-ha/terraform.tfstate
  Operation: OperationTypeApply
  Who:       john@example.com
  Version:   1.5.0
  Created:   2024-02-11 10:30:00 UTC
```

This prevents concurrent modifications and state corruption.

### Force Unlock (Emergency Only)

If a lock gets stuck (e.g., process crashed), you can force unlock:

```bash
terraform force-unlock <LOCK_ID>
```

**⚠️ WARNING**: Only use this if you're certain no other Terraform process is running!

## State Operations

### Viewing State History

S3 versioning allows you to see all previous versions of your state:

```bash
# List all versions of the state file
aws s3api list-object-versions \
  --bucket my-company-fortigate-terraform-state \
  --prefix fortigate-ha/terraform.tfstate
```

### Recovering from State Corruption

If your state file becomes corrupted, you can restore from a previous version:

```bash
# Download a specific version
aws s3api get-object \
  --bucket my-company-fortigate-terraform-state \
  --key fortigate-ha/terraform.tfstate \
  --version-id <VERSION_ID> \
  terraform.tfstate.backup

# Restore it (after backing up current state)
aws s3 cp terraform.tfstate.backup \
  s3://my-company-fortigate-terraform-state/fortigate-ha/terraform.tfstate
```

### Migrating Existing Local State to Remote

If you already have a local state file and want to migrate to remote:

```bash
# 1. Configure backend in main.tf (as shown above)

# 2. Initialize with backend config
terraform init -backend-config=backend.hcl

# 3. Terraform will detect local state and ask to migrate
# Answer "yes" when prompted:
# "Do you want to copy existing state to the new backend?"
```

### Backing Up State Manually

While S3 versioning provides automatic backups, you can also create manual backups:

```bash
# Download current state
terraform state pull > terraform.tfstate.backup-$(date +%Y%m%d-%H%M%S)

# Or download directly from S3
aws s3 cp \
  s3://my-company-fortigate-terraform-state/fortigate-ha/terraform.tfstate \
  terraform.tfstate.backup-$(date +%Y%m%d-%H%M%S)
```

## Troubleshooting

### Issue: S3 Bucket Name Already Exists

**Error:**
```
Error: Error creating S3 bucket: BucketAlreadyExists: The requested bucket name is not available
```

**Solution:**
S3 bucket names must be globally unique across all AWS accounts. Choose a different name:
- Add your company name: `acme-fortigate-terraform-state`
- Add region: `acme-us-east-1-fortigate-state`
- Add random suffix: `acme-fortigate-state-a1b2c3`

### Issue: Insufficient IAM Permissions

**Error:**
```
Error: Error creating S3 bucket: AccessDenied: Access Denied
```

**Solution:**
Verify your IAM user/role has the required permissions. Check:
1. AWS credentials are configured: `aws sts get-caller-identity`
2. IAM policy includes S3 and DynamoDB permissions
3. No SCPs (Service Control Policies) blocking the actions

### Issue: DynamoDB Table Already Exists

**Error:**
```
Error: Error creating DynamoDB Table: ResourceInUseException: Table already exists
```

**Solution:**
Either:
1. Use a different table name in `terraform.tfvars`
2. Import the existing table: `terraform import module.state_management.aws_dynamodb_table.terraform_locks fortigate-terraform-locks`
3. Delete the existing table (⚠️ only if not in use!)

### Issue: State Lock Timeout

**Error:**
```
Error: Error acquiring the state lock: timeout while waiting for state lock
```

**Solution:**
1. Check if another Terraform process is running
2. Check DynamoDB table for stuck locks:
   ```bash
   aws dynamodb scan --table-name fortigate-terraform-locks
   ```
3. If lock is stuck, force unlock: `terraform force-unlock <LOCK_ID>`

### Issue: Backend Configuration Mismatch

**Error:**
```
Error: Backend configuration changed
```

**Solution:**
Run `terraform init -reconfigure` to update the backend configuration.

### Issue: Cannot Access State File

**Error:**
```
Error: Error loading state: AccessDenied: Access Denied
```

**Solution:**
Verify your IAM permissions include:
- `s3:GetObject` on the state bucket
- `s3:PutObject` on the state bucket
- `dynamodb:PutItem`, `dynamodb:GetItem`, `dynamodb:DeleteItem` on the lock table

## Security Considerations

### Encryption

**At Rest:**
- S3 bucket uses AES-256 server-side encryption
- DynamoDB uses AWS-managed encryption keys

**In Transit:**
- All communication uses TLS 1.2 or higher
- S3 bucket policy enforces HTTPS-only access

### Access Control

**Principle of Least Privilege:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject"
      ],
      "Resource": "arn:aws:s3:::my-company-fortigate-terraform-state/fortigate-ha/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:ListBucket"
      ],
      "Resource": "arn:aws:s3:::my-company-fortigate-terraform-state"
    },
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:PutItem",
        "dynamodb:GetItem",
        "dynamodb:DeleteItem"
      ],
      "Resource": "arn:aws:dynamodb:*:*:table/fortigate-terraform-locks"
    }
  ]
}
```

### Audit Logging

Enable CloudTrail logging for state access:

```bash
# View recent state file access
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=ResourceName,AttributeValue=my-company-fortigate-terraform-state \
  --max-results 50
```

### Sensitive Data in State

**⚠️ Important**: Terraform state files contain sensitive data including:
- Resource IDs and ARNs
- IP addresses and network configurations
- Passwords and secrets (if not using external secret management)

**Best Practices:**
1. Never commit state files to version control
2. Restrict S3 bucket access to authorized personnel only
3. Use AWS Secrets Manager for sensitive values instead of hardcoding
4. Enable S3 bucket logging to track access
5. Use separate state files for different environments (dev/staging/prod)

## Multi-Environment Setup

For multiple environments, use separate state files:

```bash
# Development environment
terraform init \
  -backend-config="key=fortigate-ha/dev/terraform.tfstate"

# Staging environment
terraform init \
  -backend-config="key=fortigate-ha/staging/terraform.tfstate"

# Production environment
terraform init \
  -backend-config="key=fortigate-ha/prod/terraform.tfstate"
```

Or use Terraform workspaces:

```bash
# Create workspaces
terraform workspace new dev
terraform workspace new staging
terraform workspace new prod

# Switch between workspaces
terraform workspace select prod
```

## Cleanup

### Destroying State Management Resources

**⚠️ CRITICAL WARNING**: Only destroy state management resources if you're completely removing the FortiGate deployment and no longer need any state files!

```bash
cd terraform/bootstrap

# This will DELETE the S3 bucket and DynamoDB table
# All state history will be PERMANENTLY LOST
terraform destroy
```

Before destroying:
1. Ensure all FortiGate infrastructure is destroyed
2. Back up any state files you might need
3. Verify no other projects are using these resources

## Next Steps

After completing state management setup:

1. ✅ S3 bucket and DynamoDB table created
2. ✅ Main deployment configured to use remote state
3. ➡️ Proceed with FortiGate HA deployment
4. ➡️ Configure monitoring and logging
5. ➡️ Set up team access with appropriate IAM permissions

## Additional Resources

- [Terraform Backend Configuration](https://www.terraform.io/docs/language/settings/backends/s3.html)
- [AWS S3 Versioning](https://docs.aws.amazon.com/AmazonS3/latest/userguide/Versioning.html)
- [DynamoDB State Locking](https://www.terraform.io/docs/language/settings/backends/s3.html#dynamodb-state-locking)
- [IAM and Security Requirements](IAM_AND_SECURITY_REQUIREMENTS.md)
- [Bootstrap README](terraform/bootstrap/README.md)

## Support

For issues with state management:
1. Check this guide's troubleshooting section
2. Review AWS CloudTrail logs for API failures
3. Verify IAM permissions match requirements
4. Check S3 bucket and DynamoDB table exist and are accessible
5. Review Terraform logs with `TF_LOG=DEBUG terraform <command>`
