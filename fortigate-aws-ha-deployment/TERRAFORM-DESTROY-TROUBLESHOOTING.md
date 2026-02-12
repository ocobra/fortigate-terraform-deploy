# Terraform Destroy Troubleshooting Guide

## Problem: ENI Detachment Timeout

When running `terraform destroy`, you may encounter errors like:

```
Error: waiting for EC2 Network Interface (eni-xxxxx/eni-attach-xxxxx) detach: 
timeout while waiting for state to become 'detached' (timeout: 10m0s)
```

This happens when:
1. EC2 instances don't terminate cleanly
2. ENIs remain attached to instances
3. Terraform times out waiting for detachment (10-minute default)

---

## Quick Fix

### Option 1: Run the Force Cleanup Script (Recommended)

```bash
cd fortigate-aws-ha-deployment
./force-cleanup.sh --profile renaws --region us-east-1
```

This script will:
1. Terminate any running EC2 instances
2. Force detach stuck ENIs
3. Retry `terraform destroy`

### Option 2: Manual Cleanup

#### Step 1: Check Current State
```bash
./check-stuck-resources.sh --profile renaws --region us-east-1
```

#### Step 2: Terminate Instances Manually
```bash
# Find FortiGate instances
aws ec2 describe-instances \
  --filters "Name=tag:Project,Values=FortiGate-HA-Deployment" \
  --profile renaws \
  --region us-east-1 \
  --query 'Reservations[*].Instances[*].InstanceId' \
  --output text

# Terminate them
aws ec2 terminate-instances \
  --instance-ids i-02cd3f49d666e510c i-0503d48533a59c477 \
  --profile renaws \
  --region us-east-1

# Wait for termination
aws ec2 wait instance-terminated \
  --instance-ids i-02cd3f49d666e510c i-0503d48533a59c477 \
  --profile renaws \
  --region us-east-1
```

#### Step 3: Force Detach ENIs
```bash
# For each stuck ENI, get attachment ID and force detach
ENI_ID="eni-0da299fdba89d33e2"

ATTACH_ID=$(aws ec2 describe-network-interfaces \
  --network-interface-ids $ENI_ID \
  --profile renaws \
  --region us-east-1 \
  --query 'NetworkInterfaces[0].Attachment.AttachmentId' \
  --output text)

aws ec2 detach-network-interface \
  --attachment-id $ATTACH_ID \
  --force \
  --profile renaws \
  --region us-east-1
```

Repeat for all stuck ENIs:
- `eni-0da299fdba89d33e2` (primary HA)
- `eni-064c240470d3aefe7` (primary outside)
- `eni-0fbad7c4b511cb7de` (primary inside)
- `eni-04a1e3207a4b64483` (backup HA)
- `eni-015c428cd8c554b24` (primary mgmt)
- `eni-096b6da8014d797bd` (backup mgmt)

#### Step 4: Wait and Retry
```bash
# Wait 30 seconds for detachments to complete
sleep 30

# Retry Terraform destroy
cd terraform
terraform destroy -auto-approve
```

---

## Root Cause Analysis

### Why This Happens

1. **Instance Termination Delay**: EC2 instances may take time to fully terminate
2. **ENI Attachment State**: ENIs can get stuck in "detaching" state
3. **Terraform Timeout**: Default 10-minute timeout may not be enough for slow AWS API responses
4. **Delete on Termination**: If ENIs have `DeleteOnTermination=false`, they won't auto-delete

### Prevention for Future Deployments

#### 1. Ensure Delete on Termination
In your Terraform configuration, set:

```hcl
resource "aws_network_interface_attachment" "example" {
  # ... other config ...
  
  # This doesn't exist for network_interface_attachment
  # Instead, set it on the network interface itself
}

resource "aws_network_interface" "example" {
  # ... other config ...
  
  attachment {
    instance     = aws_instance.example.id
    device_index = 1
    
    # Note: delete_on_termination is not directly supported
    # ENIs created separately won't auto-delete
  }
}
```

#### 2. Add Explicit Dependencies
```hcl
resource "aws_instance" "fortigate" {
  # ... config ...
  
  lifecycle {
    create_before_destroy = false
  }
}

resource "aws_network_interface_attachment" "example" {
  # ... config ...
  
  depends_on = [aws_instance.fortigate]
}
```

#### 3. Use Terraform Timeouts
```hcl
resource "aws_network_interface_attachment" "example" {
  # ... config ...
  
  timeouts {
    create = "15m"
    delete = "15m"
  }
}
```

---

## Alternative: Clean Slate Approach

If you want to completely start over:

### 1. Force Delete Everything via AWS CLI

```bash
# Terminate instances
aws ec2 terminate-instances \
  --instance-ids $(aws ec2 describe-instances \
    --filters "Name=tag:Project,Values=FortiGate-HA-Deployment" \
    --profile renaws --region us-east-1 \
    --query 'Reservations[*].Instances[*].InstanceId' \
    --output text) \
  --profile renaws --region us-east-1

# Wait 2 minutes
sleep 120

# Delete all ENIs (after detachment)
for eni in eni-0da299fdba89d33e2 eni-064c240470d3aefe7 eni-0fbad7c4b511cb7de \
           eni-04a1e3207a4b64483 eni-015c428cd8c554b24 eni-096b6da8014d797bd; do
  aws ec2 delete-network-interface \
    --network-interface-id $eni \
    --profile renaws --region us-east-1 2>/dev/null || echo "ENI $eni already deleted or in use"
done
```

### 2. Clean Terraform State

```bash
cd terraform

# Remove stuck resources from state
terraform state rm 'module.fortigate_ha.aws_network_interface_attachment.primary_ha'
terraform state rm 'module.fortigate_ha.aws_network_interface_attachment.primary_outside'
terraform state rm 'module.fortigate_ha.aws_network_interface_attachment.primary_inside'
terraform state rm 'module.fortigate_ha.aws_network_interface_attachment.primary_mgmt'
terraform state rm 'module.fortigate_ha.aws_network_interface_attachment.backup_ha'
terraform state rm 'module.fortigate_ha.aws_network_interface_attachment.backup_mgmt'

# Retry destroy
terraform destroy -auto-approve
```

### 3. Nuclear Option - Delete State File

⚠️ **WARNING**: Only use this if you're okay with manually cleaning up AWS resources

```bash
cd terraform
rm -f terraform.tfstate terraform.tfstate.backup
```

Then manually delete all AWS resources via Console or CLI.

---

## Verification

After cleanup, verify everything is gone:

```bash
# Check instances
aws ec2 describe-instances \
  --filters "Name=tag:Project,Values=FortiGate-HA-Deployment" \
  --profile renaws --region us-east-1

# Check ENIs
aws ec2 describe-network-interfaces \
  --filters "Name=tag:Project,Values=FortiGate-HA-Deployment" \
  --profile renaws --region us-east-1

# Check EIPs
aws ec2 describe-addresses \
  --filters "Name=tag:Project,Values=FortiGate-HA-Deployment" \
  --profile renaws --region us-east-1

# Check Security Groups
aws ec2 describe-security-groups \
  --filters "Name=tag:Project,Values=FortiGate-HA-Deployment" \
  --profile renaws --region us-east-1

# Check Transit Gateway Attachments
aws ec2 describe-transit-gateway-vpc-attachments \
  --filters "Name=vpc-id,Values=vpc-0e16490e6ab8422fb" \
  --profile renaws --region us-east-1
```

---

## Common Issues

### Issue 1: "Resource still in use"
**Solution**: Wait longer for AWS to process termination, then retry

### Issue 2: "Attachment not found"
**Solution**: ENI may already be detached, proceed to next step

### Issue 3: "Instance not found"
**Solution**: Instance already terminated, proceed to ENI detachment

### Issue 4: Terraform state out of sync
**Solution**: Use `terraform refresh` or manually remove from state

---

## Support

For additional help:
1. Check AWS CloudWatch logs for instance termination issues
2. Review AWS Console EC2 dashboard for stuck resources
3. Check Terraform state: `terraform state list`
4. Review Terraform logs: `TF_LOG=DEBUG terraform destroy`

---

## Quick Reference Commands

```bash
# Diagnostic
./check-stuck-resources.sh --profile renaws --region us-east-1

# Force cleanup (recommended)
./force-cleanup.sh --profile renaws --region us-east-1

# Manual instance termination
aws ec2 terminate-instances --instance-ids <id> --profile renaws --region us-east-1

# Manual ENI force detach
aws ec2 detach-network-interface --attachment-id <id> --force --profile renaws --region us-east-1

# Terraform state cleanup
terraform state rm 'module.fortigate_ha.aws_network_interface_attachment.primary_ha'

# Retry destroy with profile
cd terraform
terraform destroy -var="aws_profile=renaws" -auto-approve
```
