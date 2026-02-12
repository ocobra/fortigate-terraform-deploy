# Terraform Destroy Cleanup - Quick Summary

## Problem
Terraform destroy timed out after 10+ minutes trying to detach 6 ENIs from FortiGate instances.

## Solution Files Created

1. **force-cleanup.sh** - Automated cleanup script (RECOMMENDED) - Now with AWS credential fix
2. **check-stuck-resources.sh** - Diagnostic script
3. **cleanup-cloudwatch-logs.sh** - CloudWatch and VPC Flow Logs cleanup script
4. **TERRAFORM-DESTROY-TROUBLESHOOTING.md** - Complete troubleshooting guide
5. **MANUAL-CLEANUP-STEPS.md** - Simple step-by-step manual cleanup guide
6. **CLOUDWATCH-CLEANUP-GUIDE.md** - CloudWatch logs cleanup guide

## Quick Fix (Run This)

```bash
cd fortigate-aws-ha-deployment
./force-cleanup.sh --profile renaws --region us-east-1
```

**Note**: The script now accepts AWS profile and region as parameters (no hardcoded credentials).

This will:
- ✅ Terminate EC2 instances
- ✅ Force detach stuck ENIs
- ✅ Retry terraform destroy
- ✅ Complete cleanup

## Manual Alternative

If you prefer manual control or the script fails:

**Simplest approach:**
```bash
# Set AWS credentials
export AWS_PROFILE=renaws

# Go to terraform directory
cd fortigate-aws-ha-deployment/terraform

# Retry destroy with profile
terraform destroy -var="aws_profile=renaws" -auto-approve
```

**If that doesn't work, follow the complete manual steps:**

```bash
# 1. Check current state
./check-stuck-resources.sh

# 2. Terminate instances
aws ec2 terminate-instances \
  --instance-ids i-02cd3f49d666e510c i-0503d48533a59c477 \
  --profile renaws --region us-east-1

# 3. Wait for termination
aws ec2 wait instance-terminated \
  --instance-ids i-02cd3f49d666e510c i-0503d48533a59c477 \
  --profile renaws --region us-east-1

# 4. Force detach each ENI
for eni in eni-0da299fdba89d33e2 eni-064c240470d3aefe7 eni-0fbad7c4b511cb7de \
           eni-04a1e3207a4b64483 eni-015c428cd8c554b24 eni-096b6da8014d797bd; do
  ATTACH_ID=$(aws ec2 describe-network-interfaces \
    --network-interface-ids $eni \
    --profile renaws --region us-east-1 \
    --query 'NetworkInterfaces[0].Attachment.AttachmentId' \
    --output text)
  
  aws ec2 detach-network-interface \
    --attachment-id $ATTACH_ID \
    --force \
    --profile renaws --region us-east-1
done

# 5. Wait and retry
sleep 30
cd terraform
terraform destroy -auto-approve
```

## Stuck ENIs

These 6 ENIs were stuck in detaching state:
- `eni-0da299fdba89d33e2` - Primary HA interface
- `eni-064c240470d3aefe7` - Primary outside interface
- `eni-0fbad7c4b511cb7de` - Primary inside interface
- `eni-04a1e3207a4b64483` - Backup HA interface
- `eni-015c428cd8c554b24` - Primary mgmt interface
- `eni-096b6da8014d797bd` - Backup mgmt interface

## Why This Happened

1. EC2 instances didn't terminate quickly enough
2. ENIs remained attached during Terraform destroy
3. Terraform's 10-minute timeout was exceeded
4. AWS API was slow to process detachment requests

## Prevention

For future deployments, consider:
- Adding longer timeouts in Terraform
- Ensuring instances terminate before ENI detachment
- Using lifecycle rules for proper resource ordering

## Verification

After cleanup, verify all resources are deleted:

```bash
# Check instances
aws ec2 describe-instances \
  --filters "Name=tag:Project,Values=FortiGate-HA-Deployment" \
  --profile renaws --region us-east-1 \
  --query 'Reservations[*].Instances[*].[InstanceId,State.Name]' \
  --output table

# Check ENIs
aws ec2 describe-network-interfaces \
  --filters "Name=tag:Project,Values=FortiGate-HA-Deployment" \
  --profile renaws --region us-east-1 \
  --query 'NetworkInterfaces[*].[NetworkInterfaceId,Status]' \
  --output table

# Or use the diagnostic script
cd fortigate-aws-ha-deployment
./check-stuck-resources.sh --profile renaws --region us-east-1
```

## Next Steps

1. Run `./force-cleanup.sh --profile renaws --region us-east-1` to complete the cleanup
2. Run `./cleanup-cloudwatch-logs.sh --profile renaws --region us-east-1` to clean up CloudWatch logs
3. Verify all resources are deleted using `./check-stuck-resources.sh --profile renaws --region us-east-1`
4. Review TERRAFORM-DESTROY-TROUBLESHOOTING.md for detailed information
5. Review CLOUDWATCH-CLEANUP-GUIDE.md for CloudWatch cleanup details
6. Consider the prevention strategies for future deployments

---

**Status**: Ready to execute cleanup
**Estimated Time**: 3-5 minutes
**Risk Level**: Low (safe operations)
