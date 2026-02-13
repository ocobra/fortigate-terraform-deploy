# Complete Terraform Configuration Updates

This document summarizes all Terraform configuration updates including BYOL license token support.

## Summary of All Changes

### 1. Network Interface Configuration ✅
- Fixed device index limit (4 ENIs max for c5.2xlarge)
- Outside ENI attached at instance creation (device index 0)
- Removed duplicate ENI attachments

### 2. IAM Permissions ✅
- Enhanced EIP management permissions
- Added network interface management (AssignPrivateIpAddresses, UnassignPrivateIpAddresses)
- Added route management (ReplaceRoute, CreateRoute, DeleteRoute)
- **NEW**: Added Secrets Manager permissions for license token retrieval

### 3. AWS Profile Support ✅
- Added aws_profile variable throughout configuration
- Conditional profile usage in AWS CLI commands
- Profile stored in null_resource triggers for destroy operations

### 4. Static Routing Configuration ✅
- Removed BGP configuration (not used with standard VPC attachment)
- Added static routes for Transit Gateway connectivity
- Added inside_gateway parameter to templates

### 5. Management Gateway Fix ✅
- Separate management gateways for primary and backup
- Uses cidrhost of respective management subnets

### 6. Source/Dest Check Management ✅
- Implemented via null_resource with AWS CLI
- Idempotent with triggers
- Automatic re-enable on destroy

### 7. **NEW: BYOL License Token Support** ✅
- Automatic license token retrieval from AWS Secrets Manager
- Bootstrap script applies license during instance boot
- Comprehensive logging to `/var/log/fortigate-license.log`
- Configurable via `enable_license_token_retrieval` flag

## Files Modified

### Core Terraform Files

#### 1. `terraform/main.tf`
**Changes:**
- Added aws_profile parameter passing to fortigate-ha module
- Added license token configuration parameters

#### 2. `terraform/variables.tf`
**Changes:**
- Added enable_license_token_retrieval variable
- Added primary_license_secret_name variable
- Added backup_license_secret_name variable

#### 3. `terraform/modules/fortigate-ha/main.tf`
**Changes:**
- Enhanced IAM policy with Secrets Manager permissions
- Added license token IAM policy resource
- Updated user_data template variables for both instances
- Added enable_license_token_retrieval and license_secret_name parameters

#### 4. `terraform/modules/fortigate-ha/variables.tf`
**Changes:**
- Added enable_license_token_retrieval variable
- Added primary_license_secret_name variable
- Added backup_license_secret_name variable

#### 5. `terraform/modules/fortigate-ha/templates/fortigate-primary-config.tpl`
**Changes:**
- Added license token bootstrap script section
- Conditional execution based on enable_license_token_retrieval flag
- Comprehensive logging and error handling

#### 6. `terraform/modules/fortigate-ha/templates/fortigate-backup-config.tpl`
**Changes:**
- Added license token bootstrap script section
- Conditional execution based on enable_license_token_retrieval flag
- Comprehensive logging and error handling

## New Features

### BYOL License Token Automation

**Configuration Variables:**
```hcl
# Enable automatic license token retrieval
enable_license_token_retrieval = true

# Customize secret names (optional)
primary_license_secret_name = "fortigate/primary-license-token"
backup_license_secret_name  = "fortigate/backup-license-token"
```

**IAM Permissions Added:**
```json
{
  "Sid": "FortiGateSecretsAccess",
  "Effect": "Allow",
  "Action": [
    "secretsmanager:GetSecretValue",
    "secretsmanager:DescribeSecret"
  ],
  "Resource": [
    "arn:aws:secretsmanager:*:*:secret:fortigate/primary-license-token*",
    "arn:aws:secretsmanager:*:*:secret:fortigate/backup-license-token*"
  ]
}
```

**Bootstrap Process:**
1. Wait 180 seconds for FortiGate to boot
2. Retrieve license token from Secrets Manager
3. Apply token via FortiGate CLI: `execute fortiguard-license-token`
4. Verify license status
5. Log all actions to `/var/log/fortigate-license.log`

## Usage Examples

### Deploy with License Token Automation

```hcl
# terraform.tfvars
enable_license_token_retrieval = true
primary_license_secret_name    = "fortigate/primary-license-token"
backup_license_secret_name     = "fortigate/backup-license-token"
```

### Deploy without License Token Automation

```hcl
# terraform.tfvars
enable_license_token_retrieval = false
```

Then apply licenses manually via FortiGate GUI or CLI.

## Deployment Workflow

### 1. Prerequisites
- Store license tokens in AWS Secrets Manager
- Configure terraform.tfvars with appropriate settings
- Ensure AWS profile has necessary permissions

### 2. Deploy
```bash
terraform init
terraform plan -var-file=terraform.tfvars
terraform apply -var-file=terraform.tfvars
```

### 3. Verify
```bash
# Wait 5-10 minutes for bootstrap to complete
ssh admin@<MANAGEMENT_IP>
get system status
execute shell
cat /var/log/fortigate-license.log
```

## Configuration Matrix

| Feature | Variable | Default | Description |
|---------|----------|---------|-------------|
| EIP Failover | `enable_eip_failover` | `true` | Enable automatic EIP failover |
| License Retrieval | `enable_license_token_retrieval` | `false` | Enable automatic license token retrieval |
| Primary Secret | `primary_license_secret_name` | `fortigate/primary-license-token` | Secrets Manager secret name for primary |
| Backup Secret | `backup_license_secret_name` | `fortigate/backup-license-token` | Secrets Manager secret name for backup |
| AWS Profile | `aws_profile` | `""` | AWS CLI profile name |

## IAM Permissions Summary

The FortiGate IAM role now includes:

### EC2 Permissions
- DescribeInstances, DescribeNetworkInterfaces, DescribeAddresses
- DescribeVpcs, DescribeSubnets, DescribeRouteTables
- AssociateAddress, DisassociateAddress
- AssignPrivateIpAddresses, UnassignPrivateIpAddresses
- ReplaceRoute, CreateRoute, DeleteRoute

### Secrets Manager Permissions (when enabled)
- GetSecretValue
- DescribeSecret

## Security Considerations

1. **Secrets Manager**: License tokens encrypted at rest
2. **IAM Policies**: Least privilege access to specific secrets
3. **Audit Trail**: CloudTrail logs all Secrets Manager API calls
4. **Network Security**: FortiGate uses IAM role, no credentials stored
5. **Log Security**: Bootstrap logs stored locally on FortiGate

## Cost Impact

### Secrets Manager
- $0.40 per secret per month
- $0.05 per 10,000 API calls
- **Total**: ~$0.80/month for 2 secrets + minimal API call costs

### No Additional Costs
- IAM roles and policies: Free
- CloudWatch logs: Covered by existing log retention settings
- Bootstrap scripts: No additional compute costs

## Troubleshooting

### License Not Applied

**Check logs:**
```bash
ssh admin@<MANAGEMENT_IP>
execute shell
cat /var/log/fortigate-license.log
```

**Common issues:**
1. Secret name mismatch
2. IAM permissions missing
3. Network connectivity issues
4. Invalid license token

**Manual application:**
```bash
# Get token from Secrets Manager
aws secretsmanager get-secret-value \
    --secret-id fortigate/primary-license-token \
    --region us-east-1 \
    --query SecretString \
    --output text

# Apply on FortiGate
execute fortiguard-license-token YOUR-TOKEN
```

## Testing

### Test Secrets Manager Access
```bash
aws secretsmanager get-secret-value \
    --secret-id fortigate/primary-license-token \
    --region us-east-1 \
    --profile renaws
```

### Test IAM Role
```bash
aws ec2 describe-instances \
    --instance-ids <INSTANCE_ID> \
    --query 'Reservations[0].Instances[0].IamInstanceProfile'
```

### Test License Status
```bash
ssh admin@<MANAGEMENT_IP>
get system status
diagnose debug rating
execute fortiguard-license-token-info
```

## Documentation

- **[BYOL-LICENSE-DEPLOYMENT-GUIDE.md](./BYOL-LICENSE-DEPLOYMENT-GUIDE.md)**: Comprehensive deployment guide
- **[QUICK-START-BYOL.md](./QUICK-START-BYOL.md)**: Quick reference for BYOL deployment
- **[TERRAFORM-CHANGES-SUMMARY.md](./TERRAFORM-CHANGES-SUMMARY.md)**: Previous Terraform changes
- **[STREAMLIT-APP-UPDATES-COMPLETED.md](./STREAMLIT-APP-UPDATES-COMPLETED.md)**: Web app updates

## Backward Compatibility

All changes are backward compatible:
- ✅ Existing deployments continue to work
- ✅ License token retrieval is opt-in (disabled by default)
- ✅ All previous features remain functional
- ✅ No breaking changes to existing configurations

## Next Steps

1. Store license tokens in Secrets Manager
2. Update terraform.tfvars with `enable_license_token_retrieval = true`
3. Run `terraform apply`
4. Verify license application via SSH
5. Monitor bootstrap logs for any issues

## Support

For issues or questions:
1. Check bootstrap logs: `/var/log/fortigate-license.log`
2. Review IAM permissions
3. Verify Secrets Manager secret names
4. Test manual license application
5. Refer to FortiGate AWS documentation

---

**Last Updated**: February 13, 2026
**Terraform Version**: >= 1.0
**AWS Provider Version**: ~> 5.0
**FortiOS Version**: 7.4.11
