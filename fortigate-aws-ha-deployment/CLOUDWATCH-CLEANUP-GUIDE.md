# CloudWatch Logs and VPC Flow Logs Cleanup Guide

## Problem

Terraform destroy does not always clean up CloudWatch Log Groups and VPC Flow Logs properly. This can happen because:

1. **CloudWatch Log Groups** - May be created outside of Terraform or persist after destroy
2. **VPC Flow Logs** - May not be tracked in Terraform state
3. **Missing Tags** - Resources created without proper tags can't be easily identified
4. **IAM Roles** - Flow Logs IAM roles may remain after log deletion

## Issues Identified

### 1. Missing Tags on Monitoring Resources

The monitoring module was not adding the `Project` and `ManagedBy` tags to:
- CloudWatch Log Groups
- VPC Flow Logs
- IAM Roles for Flow Logs
- CloudWatch Alarms

**Status**: ✅ FIXED - All monitoring resources now include:
- `Project = "FortiGate-HA-Deployment"`
- `ManagedBy = "Terraform"`

### 2. Orphaned CloudWatch Log Groups

CloudWatch Log Groups may exist without being tracked by Terraform:
- `/aws/vpc/flowlogs/vpc-0e16490e6ab8422fb` - VPC Flow Logs
- `/aws/ec2/fortigate/<instance-id>` - FortiGate instance logs

**Status**: ✅ FIXED - Created cleanup script

### 3. VPC Flow Logs Not Deleted

VPC Flow Logs resources may not be properly destroyed by Terraform.

**Status**: ✅ FIXED - Cleanup script handles this

## Solutions

### Solution 1: Use the Automated Cleanup Script (Recommended)

```bash
cd fortigate-aws-ha-deployment

# Dry run first to see what will be deleted
./cleanup-cloudwatch-logs.sh --profile renaws --region us-east-1 --dry-run

# Actually delete the resources
./cleanup-cloudwatch-logs.sh --profile renaws --region us-east-1
```

This script will:
1. ✅ Delete VPC Flow Logs
2. ✅ Delete CloudWatch Log Groups (fortigate and flowlogs)
3. ✅ Delete CloudWatch Alarms
4. ✅ Delete IAM Roles for Flow Logs

### Solution 2: Manual Cleanup

#### Step 1: List CloudWatch Log Groups
```bash
aws logs describe-log-groups \
  --profile renaws --region us-east-1 \
  --query 'logGroups[?contains(logGroupName, `fortigate`) || contains(logGroupName, `flowlogs`)].{Name:logGroupName,Retention:retentionInDays}' \
  --output table
```

#### Step 2: Delete CloudWatch Log Groups
```bash
# Delete VPC Flow Logs log group
aws logs delete-log-group \
  --log-group-name "/aws/vpc/flowlogs/vpc-0e16490e6ab8422fb" \
  --profile renaws --region us-east-1

# Delete FortiGate instance log groups (if any)
aws logs delete-log-group \
  --log-group-name "/aws/ec2/fortigate/<instance-id>" \
  --profile renaws --region us-east-1
```

#### Step 3: Delete VPC Flow Logs
```bash
# Find Flow Logs for your VPC
aws ec2 describe-flow-logs \
  --profile renaws --region us-east-1 \
  --filter "Name=resource-id,Values=vpc-0e16490e6ab8422fb" \
  --query 'FlowLogs[*].FlowLogId' \
  --output text

# Delete them
aws ec2 delete-flow-logs \
  --flow-log-ids <flow-log-id> \
  --profile renaws --region us-east-1
```

#### Step 4: Delete CloudWatch Alarms
```bash
# List alarms
aws cloudwatch describe-alarms \
  --profile renaws --region us-east-1 \
  --query 'MetricAlarms[?contains(AlarmName, `fortigate`)].AlarmName' \
  --output text

# Delete them
aws cloudwatch delete-alarms \
  --alarm-names <alarm-name-1> <alarm-name-2> \
  --profile renaws --region us-east-1
```

#### Step 5: Delete IAM Roles
```bash
# List Flow Logs IAM roles
aws iam list-roles \
  --profile renaws \
  --query 'Roles[?contains(RoleName, `fortigate-flow-logs`)].RoleName' \
  --output text

# Delete inline policies first
aws iam list-role-policies \
  --role-name <role-name> \
  --profile renaws \
  --query 'PolicyNames' \
  --output text

aws iam delete-role-policy \
  --role-name <role-name> \
  --policy-name <policy-name> \
  --profile renaws

# Delete the role
aws iam delete-role \
  --role-name <role-name> \
  --profile renaws
```

## Prevention for Future Deployments

### 1. Ensure Proper Tagging

The monitoring module has been updated to include proper tags on all resources:

```hcl
tags = {
  Name        = "resource-name"
  Project     = "FortiGate-HA-Deployment"
  Environment = var.environment
  Owner       = var.owner_tag
  ManagedBy   = "Terraform"
}
```

### 2. Use Terraform Destroy Properly

Always run terraform destroy with the correct profile:

```bash
cd fortigate-aws-ha-deployment/terraform
terraform destroy -var="aws_profile=renaws" -auto-approve
```

### 3. Verify Cleanup After Destroy

After running `terraform destroy`, always verify:

```bash
# Check log groups
aws logs describe-log-groups \
  --profile renaws --region us-east-1 \
  --query 'logGroups[?contains(logGroupName, `fortigate`)].logGroupName'

# Check flow logs
aws ec2 describe-flow-logs \
  --profile renaws --region us-east-1 \
  --filter "Name=resource-id,Values=vpc-0e16490e6ab8422fb"

# Check alarms
aws cloudwatch describe-alarms \
  --profile renaws --region us-east-1 \
  --query 'MetricAlarms[?contains(AlarmName, `fortigate`)].AlarmName'
```

### 4. Run Cleanup Script After Destroy

Make it a habit to run the cleanup script after terraform destroy:

```bash
# After terraform destroy
./cleanup-cloudwatch-logs.sh --profile renaws --region us-east-1
```

## Verification

After cleanup, verify all resources are gone:

```bash
# Check CloudWatch Log Groups
aws logs describe-log-groups \
  --profile renaws --region us-east-1 \
  --query 'logGroups[?contains(logGroupName, `fortigate`) || contains(logGroupName, `flowlogs`)]' \
  --output table

# Check VPC Flow Logs
aws ec2 describe-flow-logs \
  --profile renaws --region us-east-1 \
  --filter "Name=resource-id,Values=vpc-0e16490e6ab8422fb" \
  --output table

# Check CloudWatch Alarms
aws cloudwatch describe-alarms \
  --profile renaws --region us-east-1 \
  --query 'MetricAlarms[?contains(AlarmName, `fortigate`)]' \
  --output table

# Check IAM Roles
aws iam list-roles \
  --profile renaws \
  --query 'Roles[?contains(RoleName, `fortigate-flow-logs`)]' \
  --output table
```

Expected output: Empty results or "None" for all commands.

## Cost Implications

Orphaned CloudWatch resources can incur costs:

- **CloudWatch Log Groups**: $0.50 per GB ingested, $0.03 per GB stored
- **VPC Flow Logs**: Data ingestion charges apply
- **CloudWatch Alarms**: $0.10 per alarm per month

Always clean up unused resources to avoid unnecessary charges.

## Troubleshooting

### Issue: "Cannot delete log group - resource not found"
**Solution**: Log group may already be deleted, continue to next resource

### Issue: "Cannot delete IAM role - role is in use"
**Solution**: Delete inline policies first, then delete the role

### Issue: "Access Denied when deleting IAM resources"
**Solution**: Ensure your AWS profile has IAM permissions:
- `iam:DeleteRole`
- `iam:DeleteRolePolicy`
- `iam:ListRoles`
- `iam:ListRolePolicies`

### Issue: "VPC Flow Log not found"
**Solution**: Flow log may already be deleted or was never created

## Quick Reference

```bash
# Dry run to see what will be deleted
./cleanup-cloudwatch-logs.sh --profile renaws --region us-east-1 --dry-run

# Actually delete resources
./cleanup-cloudwatch-logs.sh --profile renaws --region us-east-1

# Verify cleanup
aws logs describe-log-groups --profile renaws --region us-east-1 \
  --query 'logGroups[?contains(logGroupName, `fortigate`)].logGroupName'
```

## Files Modified

1. **terraform/modules/monitoring/main.tf** - Added `Project` and `ManagedBy` tags to all resources
2. **cleanup-cloudwatch-logs.sh** - New automated cleanup script
3. **CLOUDWATCH-CLEANUP-GUIDE.md** - This documentation

---

**Status**: Ready to use
**Last Updated**: 2026-02-12
**Tested**: Yes

