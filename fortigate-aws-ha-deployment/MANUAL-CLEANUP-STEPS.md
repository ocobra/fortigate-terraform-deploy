# Manual Cleanup Steps - Simple Guide

## Quick Manual Cleanup (No Scripts)

If you prefer to run commands manually instead of using the script:

### Step 1: Set AWS Profile
```bash
export AWS_PROFILE=renaws
export AWS_REGION=us-east-1
```

### Step 2: Terminate EC2 Instances
```bash
# Get instance IDs
aws ec2 describe-instances \
  --filters "Name=tag:Project,Values=FortiGate-HA-Deployment" "Name=instance-state-name,Values=running,stopped" \
  --query 'Reservations[*].Instances[*].InstanceId' \
  --output text

# Terminate them (replace with actual IDs if needed)
aws ec2 terminate-instances \
  --instance-ids i-02cd3f49d666e510c i-0503d48533a59c477

# Wait for termination (takes 2-3 minutes)
aws ec2 wait instance-terminated \
  --instance-ids i-02cd3f49d666e510c i-0503d48533a59c477
```

### Step 3: Force Detach ENIs
```bash
# For each stuck ENI, run these commands:

# ENI 1: eni-0da299fdba89d33e2
ATTACH_ID=$(aws ec2 describe-network-interfaces --network-interface-ids eni-0da299fdba89d33e2 --query 'NetworkInterfaces[0].Attachment.AttachmentId' --output text)
aws ec2 detach-network-interface --attachment-id $ATTACH_ID --force

# ENI 2: eni-064c240470d3aefe7
ATTACH_ID=$(aws ec2 describe-network-interfaces --network-interface-ids eni-064c240470d3aefe7 --query 'NetworkInterfaces[0].Attachment.AttachmentId' --output text)
aws ec2 detach-network-interface --attachment-id $ATTACH_ID --force

# ENI 3: eni-0fbad7c4b511cb7de
ATTACH_ID=$(aws ec2 describe-network-interfaces --network-interface-ids eni-0fbad7c4b511cb7de --query 'NetworkInterfaces[0].Attachment.AttachmentId' --output text)
aws ec2 detach-network-interface --attachment-id $ATTACH_ID --force

# ENI 4: eni-04a1e3207a4b64483
ATTACH_ID=$(aws ec2 describe-network-interfaces --network-interface-ids eni-04a1e3207a4b64483 --query 'NetworkInterfaces[0].Attachment.AttachmentId' --output text)
aws ec2 detach-network-interface --attachment-id $ATTACH_ID --force

# ENI 5: eni-015c428cd8c554b24
ATTACH_ID=$(aws ec2 describe-network-interfaces --network-interface-ids eni-015c428cd8c554b24 --query 'NetworkInterfaces[0].Attachment.AttachmentId' --output text)
aws ec2 detach-network-interface --attachment-id $ATTACH_ID --force

# ENI 6: eni-096b6da8014d797bd
ATTACH_ID=$(aws ec2 describe-network-interfaces --network-interface-ids eni-096b6da8014d797bd --query 'NetworkInterfaces[0].Attachment.AttachmentId' --output text)
aws ec2 detach-network-interface --attachment-id $ATTACH_ID --force
```

### Step 4: Wait for Detachment
```bash
# Wait 30 seconds for AWS to process detachments
sleep 30
```

### Step 5: Retry Terraform Destroy
```bash
cd fortigate-aws-ha-deployment/terraform

# Option A: Pass profile as variable
terraform destroy -var="aws_profile=renaws" -auto-approve

# Option B: Use environment variable (already set in Step 1)
terraform destroy -auto-approve
```

---

## Even Simpler: One-Liner Commands

If instances are already terminated and you just need to retry Terraform:

```bash
cd fortigate-aws-ha-deployment/terraform && \
export AWS_PROFILE=renaws && \
terraform destroy -var="aws_profile=renaws" -auto-approve
```

---

## If Terraform Still Fails

### Option 1: Remove Stuck Resources from State
```bash
cd fortigate-aws-ha-deployment/terraform

# Remove the stuck ENI attachments from Terraform state
terraform state rm 'module.fortigate_ha.aws_network_interface_attachment.primary_ha'
terraform state rm 'module.fortigate_ha.aws_network_interface_attachment.primary_outside'
terraform state rm 'module.fortigate_ha.aws_network_interface_attachment.primary_inside'
terraform state rm 'module.fortigate_ha.aws_network_interface_attachment.primary_mgmt'
terraform state rm 'module.fortigate_ha.aws_network_interface_attachment.backup_ha'
terraform state rm 'module.fortigate_ha.aws_network_interface_attachment.backup_mgmt'

# Retry destroy
terraform destroy -var="aws_profile=renaws" -auto-approve
```

### Option 2: Delete Everything Manually via AWS CLI
```bash
export AWS_PROFILE=renaws

# Delete Transit Gateway attachment
aws ec2 delete-transit-gateway-vpc-attachment \
  --transit-gateway-attachment-id tgw-attach-063cdde6212400647

# Delete security groups (after instances are terminated)
aws ec2 delete-security-group --group-id sg-06821887156ea017d  # data
aws ec2 delete-security-group --group-id sg-0e56c88f9d246d0d7  # ha
aws ec2 delete-security-group --group-id sg-0176a9b5fc7a87799  # mgmt

# Delete route tables (if created by Terraform)
# Check first: aws ec2 describe-route-tables --filters "Name=tag:Project,Values=FortiGate-HA-Deployment"

# Then clean Terraform state
cd fortigate-aws-ha-deployment/terraform
rm -f terraform.tfstate terraform.tfstate.backup
```

---

## Verification

After cleanup, verify everything is gone:

```bash
export AWS_PROFILE=renaws

# Check instances
aws ec2 describe-instances \
  --filters "Name=tag:Project,Values=FortiGate-HA-Deployment" \
  --query 'Reservations[*].Instances[*].[InstanceId,State.Name]' \
  --output table

# Check ENIs
aws ec2 describe-network-interfaces \
  --filters "Name=tag:Project,Values=FortiGate-HA-Deployment" \
  --query 'NetworkInterfaces[*].[NetworkInterfaceId,Status]' \
  --output table

# Check security groups
aws ec2 describe-security-groups \
  --filters "Name=tag:Project,Values=FortiGate-HA-Deployment" \
  --query 'SecurityGroups[*].[GroupId,GroupName]' \
  --output table
```

---

## Troubleshooting

### "No valid credential sources found"
**Solution**: Set AWS_PROFILE environment variable
```bash
export AWS_PROFILE=renaws
```

### "Attachment not found"
**Solution**: ENI already detached, skip to next one

### "Resource still in use"
**Solution**: Wait longer, then retry

### "DependencyViolation"
**Solution**: Delete resources in this order:
1. Instances
2. ENI attachments
3. ENIs (if not pre-created)
4. Transit Gateway attachments
5. Security groups
6. Route tables

---

## Quick Reference

```bash
# Set credentials
export AWS_PROFILE=renaws
export AWS_REGION=us-east-1

# Terminate instances
aws ec2 terminate-instances --instance-ids i-02cd3f49d666e510c i-0503d48533a59c477 --profile renaws --region us-east-1

# Wait
aws ec2 wait instance-terminated --instance-ids i-02cd3f49d666e510c i-0503d48533a59c477 --profile renaws --region us-east-1

# Retry Terraform
cd fortigate-aws-ha-deployment/terraform
terraform destroy -var="aws_profile=renaws" -auto-approve
```
