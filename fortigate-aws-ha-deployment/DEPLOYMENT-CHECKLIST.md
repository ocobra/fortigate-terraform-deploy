# FortiGate HA Deployment Checklist

## ✅ Step 1: ENI Creation (COMPLETED)

You've successfully created 8 ENIs with the following IDs:

**Primary FortiGate:**
- Outside ENI: `eni-0f2b7af07f935dc95`
- Inside ENI: `eni-05d7c0464ff090f3b`
- HA ENI: `eni-04323804fb6e0f9b1`
- Management ENI: `eni-005955f7041309036`

**Backup FortiGate:**
- Outside ENI: `eni-02b5b2520f46276f5`
- Inside ENI: `eni-0d20398ff6e3b1fb9`
- HA ENI: `eni-01a6621b246697bd6`
- Management ENI: `eni-00a1afab6a01f1af9`

These have been added to `terraform/terraform.tfvars`.

---

## 📋 Step 2: Complete terraform.tfvars Configuration

Open `terraform/terraform.tfvars` and update the following values:

### Required Changes:

#### 1. VPC ID
```hcl
vpc_id = "vpc-XXXXXXXXX"  # Replace with your actual VPC ID
```

**How to find it:**
```bash
aws ec2 describe-vpcs --region us-east-1 --query 'Vpcs[*].[VpcId,Tags[?Key==`Name`].Value|[0]]' --output table
```

#### 2. FortiGate AMI ID
```hcl
fortigate_ami_id = "ami-XXXXXXXXX"  # Replace with FortiGate AMI ID
```

**How to find it:**
```bash
# List FortiGate AMIs
aws ec2 describe-images \
  --region us-east-1 \
  --owners 679593333241 \
  --filters "Name=name,Values=FortiGate-VM64-AWS-7.4*-BYOL-*" \
  --query 'Images[*].[ImageId,Name,CreationDate]' \
  --output table | sort -k3 -r | head -5
```

Or use the deploy.py script's AMI discovery:
```bash
python3 deploy.py --auto-discover-ami --license-type BYOL --fortigate-version 7.4
```

#### 3. EC2 Key Pair Name
```hcl
key_pair_name = "YOUR-KEY-PAIR"  # Replace with your EC2 key pair name
```

**How to find it:**
```bash
aws ec2 describe-key-pairs --region us-east-1 --query 'KeyPairs[*].KeyName' --output table
```

**To create a new key pair:**
```bash
aws ec2 create-key-pair --key-name fortigate-ha-key --region us-east-1 --query 'KeyMaterial' --output text > fortigate-ha-key.pem
chmod 400 fortigate-ha-key.pem
```

#### 4. Admin Password
```hcl
admin_password = "CHANGE-ME-SECURE-PASSWORD-123!"  # Change to a secure password
```

**Requirements:**
- Minimum 8 characters
- Include uppercase, lowercase, numbers, and special characters
- Example: `MySecure@FortiGate2024!`

#### 5. HA Password
```hcl
ha_password = "CHANGE-ME-HA-PASSWORD-123!"  # Change to a secure password
```

**Requirements:**
- Minimum 8 characters
- Different from admin password
- Example: `MyHA@Sync2024!`

#### 6. Transit Gateway ID (if using existing)
```hcl
create_transit_gateway = false
existing_transit_gateway_id = "tgw-XXXXXXXXX"  # Replace with your TGW ID
```

**How to find it:**
```bash
aws ec2 describe-transit-gateways --region us-east-1 --query 'TransitGateways[*].[TransitGatewayId,State,Tags[?Key==`Name`].Value|[0]]' --output table
```

**Or create a new one:**
```hcl
create_transit_gateway = true
# existing_transit_gateway_id not needed
```

### Optional Changes:

#### 7. Spoke VPC CIDRs
```hcl
spoke_vpc_cidrs = ["10.1.0.0/16", "10.2.0.0/16"]  # Update with your spoke VPC CIDRs
```

#### 8. Management Access CIDRs
```hcl
mgmt_access_cidrs = ["10.0.0.0/8"]  # Update with your management network CIDRs
```

#### 9. Availability Zones
```hcl
availability_zones = ["us-east-1a", "us-east-1b"]  # Verify these match your subnets
```

---

## 🔍 Step 3: Verify Configuration

Run this command to check your configuration:

```bash
cd terraform
terraform init
terraform validate
```

---

## 📊 Step 4: Review Terraform Plan

Generate and review the deployment plan:

```bash
terraform plan
```

**What to check:**
- Number of resources to create (should be ~20-30 resources)
- ENI attachments are correct
- Security groups are properly configured
- No errors or warnings

---

## 🚀 Step 5: Deploy

If the plan looks good, deploy:

```bash
terraform apply
```

Type `yes` when prompted to confirm.

**Deployment time:** Approximately 5-10 minutes

---

## ✅ Step 6: Verify Deployment

After deployment completes, verify:

### 1. Check FortiGate Instances
```bash
aws ec2 describe-instances \
  --region us-east-1 \
  --filters "Name=tag:Project,Values=FortiGate-HA-Deployment" \
  --query 'Reservations[*].Instances[*].[InstanceId,State.Name,Tags[?Key==`Name`].Value|[0]]' \
  --output table
```

### 2. Get Management IPs
```bash
terraform output
```

Look for:
- `fortigate_primary_mgmt_ip`
- `fortigate_backup_mgmt_ip`

### 3. Access FortiGate Web UI

**Primary FortiGate:**
```
https://<primary_mgmt_ip>
Username: admin
Password: <your_admin_password>
```

**Backup FortiGate:**
```
https://<backup_mgmt_ip>
Username: admin
Password: <your_admin_password>
```

### 4. Verify HA Status

In the FortiGate GUI:
1. Go to **System > HA**
2. Check HA status shows:
   - Primary: Master/Active
   - Backup: Slave/Standby
3. Verify HA sync is working

### 5. Verify BGP Sessions

In the FortiGate CLI:
```
get router info bgp summary
```

Should show BGP sessions with Transit Gateway.

---

## 📝 Configuration Summary

Once complete, save this information:

| Item | Value |
|------|-------|
| VPC ID | `vpc-XXXXXXXXX` |
| Primary FortiGate IP | `<from terraform output>` |
| Backup FortiGate IP | `<from terraform output>` |
| Transit Gateway ID | `tgw-XXXXXXXXX` |
| Key Pair Name | `YOUR-KEY-PAIR` |

---

## 🔧 Troubleshooting

### Issue: "Invalid AMI ID"
**Solution:** Verify the AMI ID exists in your region:
```bash
aws ec2 describe-images --region us-east-1 --image-ids ami-XXXXXXXXX
```

### Issue: "Key pair not found"
**Solution:** List available key pairs:
```bash
aws ec2 describe-key-pairs --region us-east-1
```

### Issue: "Subnet not found"
**Solution:** Verify subnets exist:
```bash
aws ec2 describe-subnets --region us-east-1 --subnet-ids subnet-XXXXXXXXX
```

### Issue: "ENI already attached"
**Solution:** Check if ENIs are already in use:
```bash
aws ec2 describe-network-interfaces --region us-east-1 --network-interface-ids eni-XXXXXXXXX
```

---

## 🧹 Cleanup (if needed)

To destroy the deployment:

```bash
cd terraform
terraform destroy
```

**Note:** This will NOT delete the ENIs (they were created separately). To delete ENIs:

```bash
aws ec2 delete-network-interface --region us-east-1 --network-interface-id eni-XXXXXXXXX
```

Or delete all ENIs created by the script:
```bash
aws ec2 describe-network-interfaces \
  --region us-east-1 \
  --filters "Name=tag:Project,Values=FortiGate-HA-Deployment" \
  --query 'NetworkInterfaces[*].NetworkInterfaceId' \
  --output text | xargs -n1 aws ec2 delete-network-interface --region us-east-1 --network-interface-id
```

---

## 📚 Additional Resources

- [FortiGate AWS Documentation](https://docs.fortinet.com/product/fortigate-public-cloud/aws)
- [Terraform AWS Provider Docs](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
- [AWS Transit Gateway Guide](https://docs.aws.amazon.com/vpc/latest/tgw/)

---

## ✅ Checklist Summary

- [ ] ENIs created (DONE ✓)
- [ ] terraform.tfvars updated with VPC ID
- [ ] terraform.tfvars updated with FortiGate AMI ID
- [ ] terraform.tfvars updated with EC2 key pair name
- [ ] terraform.tfvars updated with admin password
- [ ] terraform.tfvars updated with HA password
- [ ] terraform.tfvars updated with Transit Gateway ID (if using existing)
- [ ] Ran `terraform init`
- [ ] Ran `terraform validate`
- [ ] Reviewed `terraform plan`
- [ ] Ran `terraform apply`
- [ ] Verified FortiGate instances are running
- [ ] Accessed FortiGate web UI
- [ ] Verified HA status
- [ ] Verified BGP sessions
