# FortiGate BYOL License Deployment Guide

This guide explains how to deploy FortiGate HA with BYOL (Bring Your Own License) using AWS Secrets Manager for automated license token application.

## Overview

The Terraform configuration now supports automatic license token retrieval and application from AWS Secrets Manager. This provides:
- ✅ Secure storage of license tokens
- ✅ Automatic license application during instance boot
- ✅ No manual intervention required
- ✅ Audit trail via CloudWatch logs

## Prerequisites

1. FortiGate BYOL license tokens (one for primary, one for backup)
2. AWS CLI configured with appropriate profile
3. Terraform installed
4. AWS account with permissions to create Secrets Manager secrets

## Step 1: Store License Tokens in AWS Secrets Manager

### PowerShell (Windows):
```powershell
# Set your AWS profile
$env:AWS_PROFILE = "renaws"

# Store primary license token
aws secretsmanager create-secret `
    --name fortigate/primary-license-token `
    --description "FortiGate Primary Instance BYOL License Token" `
    --secret-string "YOUR-PRIMARY-LICENSE-TOKEN-HERE" `
    --region us-east-1

# Store backup license token
aws secretsmanager create-secret `
    --name fortigate/backup-license-token `
    --description "FortiGate Backup Instance BYOL License Token" `
    --secret-string "YOUR-BACKUP-LICENSE-TOKEN-HERE" `
    --region us-east-1

# Verify secrets were created
aws secretsmanager list-secrets --region us-east-1 --query "SecretList[?contains(Name, 'fortigate')]"
```

### Bash (Linux/Mac):
```bash
# Set your AWS profile
export AWS_PROFILE=renaws

# Store primary license token
aws secretsmanager create-secret \
    --name fortigate/primary-license-token \
    --description "FortiGate Primary Instance BYOL License Token" \
    --secret-string "YOUR-PRIMARY-LICENSE-TOKEN-HERE" \
    --region us-east-1

# Store backup license token
aws secretsmanager create-secret \
    --name fortigate/backup-license-token \
    --description "FortiGate Backup Instance BYOL License Token" \
    --secret-string "YOUR-BACKUP-LICENSE-TOKEN-HERE" \
    --region us-east-1

# Verify secrets were created
aws secretsmanager list-secrets --region us-east-1 --query "SecretList[?contains(Name, 'fortigate')]"
```

## Step 2: Update terraform.tfvars

Add the following to your `terraform/terraform.tfvars` file:

```hcl
# Enable license token retrieval from Secrets Manager
enable_license_token_retrieval = true

# Optional: Customize secret names if you used different names
primary_license_secret_name = "fortigate/primary-license-token"
backup_license_secret_name  = "fortigate/backup-license-token"
```

## Step 3: Deploy with Terraform

### PowerShell (Windows):
```powershell
cd fortigate-aws-ha-deployment\terraform

# Set AWS profile
$env:AWS_PROFILE = "renaws"

# Initialize Terraform (if needed)
terraform init

# Plan deployment
terraform plan -var-file=terraform.tfvars

# Apply deployment
terraform apply -var-file=terraform.tfvars
```

### Bash (Linux/Mac):
```bash
cd fortigate-aws-ha-deployment/terraform

# Set AWS profile
export AWS_PROFILE=renaws

# Initialize Terraform (if needed)
terraform init

# Plan deployment
terraform plan -var-file=terraform.tfvars

# Apply deployment
terraform apply -var-file=terraform.tfvars
```

## Step 4: Verify License Application

After deployment completes (wait 5-10 minutes for bootstrap to complete):

### Check License Status via SSH:
```bash
# SSH to primary FortiGate
ssh admin@<PRIMARY_MANAGEMENT_IP>

# Check license status
get system status

# Check FortiGuard license status
diagnose debug rating

# View license details
execute fortiguard-license-token-info

# Check bootstrap log
execute shell
cat /var/log/fortigate-license.log
exit
```

### Expected Output:
```
[2026-02-13 10:15:30] Starting license token bootstrap...
[2026-02-13 10:15:30] Retrieving license token from Secrets Manager: fortigate/primary-license-token
[2026-02-13 10:15:32] License token retrieved successfully
[2026-02-13 10:15:32] Applying license token to FortiGate...
[2026-02-13 10:16:05] Verifying license status...
[2026-02-13 10:16:05] License token application completed
```

## Configuration Details

### IAM Permissions

The Terraform configuration automatically creates IAM policies that grant FortiGate instances permission to:
- Retrieve secrets from AWS Secrets Manager
- Manage EIPs for HA failover
- Manage network interfaces
- Manage routes

### License Bootstrap Process

1. FortiGate instance boots up
2. After 180 seconds (3 minutes), bootstrap script executes
3. Script retrieves license token from Secrets Manager
4. Script applies license token via FortiGate CLI
5. Script verifies license status
6. All actions are logged to `/var/log/fortigate-license.log`

### Secrets Manager Secret Names

Default secret names:
- Primary: `fortigate/primary-license-token`
- Backup: `fortigate/backup-license-token`

You can customize these in `terraform.tfvars`:
```hcl
primary_license_secret_name = "my-custom/primary-token"
backup_license_secret_name  = "my-custom/backup-token"
```

## Troubleshooting

### License Not Applied

**Check bootstrap log:**
```bash
ssh admin@<MANAGEMENT_IP>
execute shell
cat /var/log/fortigate-license.log
```

**Common issues:**
1. **Secret not found**: Verify secret name matches configuration
2. **Permission denied**: Check IAM role has Secrets Manager permissions
3. **Network connectivity**: Ensure FortiGate can reach AWS API endpoints

**Manual application:**
```bash
# SSH to FortiGate
ssh admin@<MANAGEMENT_IP>

# Get token from Secrets Manager (from your workstation)
aws secretsmanager get-secret-value \
    --secret-id fortigate/primary-license-token \
    --region us-east-1 \
    --query SecretString \
    --output text \
    --profile renaws

# Apply token manually on FortiGate
execute fortiguard-license-token YOUR-TOKEN-HERE

# Verify
get system status
```

### Verify IAM Permissions

```bash
# Check IAM role attached to instance
aws ec2 describe-instances \
    --instance-ids <INSTANCE_ID> \
    --query 'Reservations[0].Instances[0].IamInstanceProfile' \
    --profile renaws

# Check IAM role policies
aws iam list-attached-role-policies \
    --role-name fortigate-ha-eip-management-role \
    --profile renaws

aws iam list-role-policies \
    --role-name fortigate-ha-eip-management-role \
    --profile renaws
```

### Test Secrets Manager Access

From your workstation:
```bash
# Test retrieving primary token
aws secretsmanager get-secret-value \
    --secret-id fortigate/primary-license-token \
    --region us-east-1 \
    --query SecretString \
    --output text \
    --profile renaws

# Test retrieving backup token
aws secretsmanager get-secret-value \
    --secret-id fortigate/backup-license-token \
    --region us-east-1 \
    --query SecretString \
    --output text \
    --profile renaws
```

## Disabling License Token Retrieval

If you want to disable automatic license token retrieval:

```hcl
# In terraform.tfvars
enable_license_token_retrieval = false
```

Then apply licenses manually via FortiGate GUI or CLI.

## Security Best Practices

1. **Restrict Secret Access**: Use IAM policies to limit which resources can access license tokens
2. **Enable Secret Rotation**: Consider rotating license tokens periodically
3. **Audit Access**: Enable CloudTrail logging for Secrets Manager API calls
4. **Use Encryption**: Secrets Manager encrypts secrets at rest by default
5. **Least Privilege**: IAM role only has permissions needed for license retrieval

## Cost Considerations

- **Secrets Manager**: $0.40 per secret per month + $0.05 per 10,000 API calls
- **Two secrets** (primary + backup): ~$0.80/month
- **API calls**: Minimal (one call per instance boot)

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     AWS Account                              │
│                                                              │
│  ┌──────────────────────┐      ┌──────────────────────┐   │
│  │  Secrets Manager     │      │  Secrets Manager     │   │
│  │  primary-license-    │      │  backup-license-     │   │
│  │  token               │      │  token               │   │
│  └──────────┬───────────┘      └──────────┬───────────┘   │
│             │                               │               │
│             │ IAM Role                      │ IAM Role      │
│             │ Permissions                   │ Permissions   │
│             ▼                               ▼               │
│  ┌──────────────────────┐      ┌──────────────────────┐   │
│  │  FortiGate Primary   │◄────►│  FortiGate Backup    │   │
│  │  - Retrieves token   │  HA  │  - Retrieves token   │   │
│  │  - Applies license   │      │  - Applies license   │   │
│  │  - Logs to file      │      │  - Logs to file      │   │
│  └──────────────────────┘      └──────────────────────┘   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Summary

This automated license deployment solution:
- ✅ Securely stores license tokens in AWS Secrets Manager
- ✅ Automatically applies licenses during instance boot
- ✅ Provides detailed logging for troubleshooting
- ✅ Follows AWS security best practices
- ✅ Requires minimal manual intervention
- ✅ Integrates seamlessly with existing Terraform configuration

For additional support, refer to:
- [TERRAFORM-CHANGES-SUMMARY.md](./TERRAFORM-CHANGES-SUMMARY.md) - Complete list of Terraform changes
- [FortiGate AWS Documentation](https://docs.fortinet.com/product/fortigate-public-cloud)
- [AWS Secrets Manager Documentation](https://docs.aws.amazon.com/secretsmanager/)
