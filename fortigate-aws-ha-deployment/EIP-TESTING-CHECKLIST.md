# EIP Support Testing Checklist

## Pre-Testing Setup

- [ ] Ensure AWS credentials are configured (profile: renaws)
- [ ] Verify region is set to us-east-1
- [ ] Confirm account ID: 678632990402
- [ ] Have subnet IDs ready for all 8 interfaces

## Test Scenario 1: Create ENIs with EIPs

### Step 1: Create ENIs with EIP Allocation

```bash
cd fortigate-aws-ha-deployment
python3 create-enis.py --profile renaws --region us-east-1 --account 678632990402 --allocate-eips
```

**Expected Output:**
- [ ] 8 ENIs created successfully
- [ ] 2 EIPs allocated (primary and backup outside)
- [ ] EIPs associated with outside ENIs
- [ ] Public IP addresses displayed
- [ ] EIP allocation IDs displayed
- [ ] eni-ids.json file created with EIP information
- [ ] Terraform variable snippet includes EIP allocation IDs

**Verify:**
```bash
# Check eni-ids.json contains EIP information
cat eni-ids.json | jq '.eips'

# Should show:
# {
#   "primary_outside": {
#     "allocation_id": "eipalloc-xxxxx",
#     "public_ip": "x.x.x.x",
#     "eni_id": "eni-xxxxx"
#   },
#   "backup_outside": {
#     "allocation_id": "eipalloc-xxxxx",
#     "public_ip": "x.x.x.x",
#     "eni_id": "eni-xxxxx"
#   }
# }
```

### Step 2: Deploy with Existing EIP Allocation IDs

```bash
python3 deploy.py
```

**Interactive Prompts - Expected Answers:**
- [ ] AWS Region: us-east-1
- [ ] Use AWS profile?: yes
- [ ] AWS Profile name: renaws
- [ ] VPC ID: vpc-0e16490e6ab8422fb
- [ ] Primary AZ: us-east-1a
- [ ] Backup AZ: us-east-1b
- [ ] Provide all 8 subnet IDs
- [ ] Provide all 8 ENI IDs (from create-enis.py output)
- [ ] Management access CIDRs: 10.0.0.0/8
- [ ] **Allocate Elastic IPs for outside interfaces?: yes**
- [ ] **Use existing EIP allocation IDs?: yes**
- [ ] **Primary outside EIP allocation ID: eipalloc-xxxxx** (from create-enis.py)
- [ ] **Backup outside EIP allocation ID: eipalloc-xxxxx** (from create-enis.py)
- [ ] Continue with FortiGate configuration prompts...

**Expected Validation:**
- [ ] EIP allocation IDs validated successfully
- [ ] Warning if EIPs already associated (expected on first run)
- [ ] All configuration validated

**Verify terraform.tfvars:**
```bash
cat terraform/terraform.tfvars | grep -A3 "Elastic IP"

# Should show:
# # Elastic IP Configuration (for internet routing)
# allocate_eips = true
# primary_outside_eip_id = "eipalloc-xxxxx"
# backup_outside_eip_id = "eipalloc-xxxxx"
```

### Step 3: Terraform Plan

**Expected Output:**
- [ ] Terraform plan shows EIP association resources
- [ ] No new EIP allocation resources (using existing)
- [ ] EIP associations for both primary and backup outside ENIs

```bash
cd terraform
terraform plan | grep -i eip

# Should show:
# + aws_eip_association.primary_outside
# + aws_eip_association.backup_outside
```

### Step 4: Terraform Apply

```bash
terraform apply
```

**Expected Results:**
- [ ] EIP associations created successfully
- [ ] FortiGate instances created
- [ ] All resources created without errors

**Verify EIP Associations:**
```bash
# Check primary outside ENI
aws ec2 describe-network-interfaces \
  --network-interface-ids <primary-outside-eni-id> \
  --profile renaws \
  --region us-east-1 \
  --query 'NetworkInterfaces[0].Association.PublicIp'

# Check backup outside ENI
aws ec2 describe-network-interfaces \
  --network-interface-ids <backup-outside-eni-id> \
  --profile renaws \
  --region us-east-1 \
  --query 'NetworkInterfaces[0].Association.PublicIp'
```

- [ ] Primary outside ENI has public IP
- [ ] Backup outside ENI has public IP
- [ ] Public IPs match EIP allocation IDs

### Step 5: Cleanup

```bash
cd terraform
terraform destroy
```

- [ ] All resources destroyed successfully
- [ ] EIPs remain (not destroyed, as expected)

**Cleanup EIPs manually:**
```bash
# Disassociate and release EIPs
aws ec2 release-address --allocation-id <primary-eip-allocation-id> --profile renaws --region us-east-1
aws ec2 release-address --allocation-id <backup-eip-allocation-id> --profile renaws --region us-east-1
```

**Cleanup ENIs:**
```bash
# Delete all 8 ENIs
aws ec2 delete-network-interface --network-interface-id <eni-id> --profile renaws --region us-east-1
# Repeat for all 8 ENIs
```

---

## Test Scenario 2: Deploy with Auto-Created EIPs

### Step 1: Create ENIs without EIPs

```bash
python3 create-enis.py --profile renaws --region us-east-1 --account 678632990402
```

**Expected Output:**
- [ ] 8 ENIs created successfully
- [ ] No EIPs allocated
- [ ] eni-ids.json file created without EIP information

### Step 2: Deploy with Auto-Created EIPs

```bash
python3 deploy.py
```

**Interactive Prompts - Expected Answers:**
- [ ] Provide all configuration as before
- [ ] **Allocate Elastic IPs for outside interfaces?: yes**
- [ ] **Use existing EIP allocation IDs?: no**

**Expected Validation:**
- [ ] Message: "EIP allocation enabled but no EIP allocation IDs provided - Terraform will create new EIPs"

**Verify terraform.tfvars:**
```bash
cat terraform/terraform.tfvars | grep -A3 "Elastic IP"

# Should show:
# # Elastic IP Configuration (for internet routing)
# allocate_eips = true
# primary_outside_eip_id = ""
# backup_outside_eip_id = ""
```

### Step 3: Terraform Plan

**Expected Output:**
- [ ] Terraform plan shows new EIP allocation resources
- [ ] Terraform plan shows EIP association resources

```bash
cd terraform
terraform plan | grep -i eip

# Should show:
# + aws_eip.primary_outside[0]
# + aws_eip.backup_outside[0]
# + aws_eip_association.primary_outside[0]
# + aws_eip_association.backup_outside[0]
```

### Step 4: Terraform Apply

```bash
terraform apply
```

**Expected Results:**
- [ ] 2 new EIPs created
- [ ] EIP associations created successfully
- [ ] FortiGate instances created
- [ ] All resources created without errors

**Verify EIP Creation:**
```bash
# List EIPs with FortiGate tags
aws ec2 describe-addresses \
  --filters "Name=tag:Project,Values=FortiGate-HA-Deployment" \
  --profile renaws \
  --region us-east-1 \
  --query 'Addresses[*].[AllocationId,PublicIp,Tags[?Key==`Name`].Value|[0]]' \
  --output table
```

- [ ] 2 EIPs listed
- [ ] Tags include "fortigate-primary-outside-eip" and "fortigate-backup-outside-eip"

### Step 5: Cleanup

```bash
cd terraform
terraform destroy
```

- [ ] All resources destroyed successfully
- [ ] EIPs destroyed (created by Terraform)

---

## Test Scenario 3: Deploy without EIPs

### Step 1: Create ENIs

```bash
python3 create-enis.py --profile renaws --region us-east-1 --account 678632990402
```

### Step 2: Deploy without EIPs

```bash
python3 deploy.py
```

**Interactive Prompts - Expected Answers:**
- [ ] Provide all configuration as before
- [ ] **Allocate Elastic IPs for outside interfaces?: no**

**Verify terraform.tfvars:**
```bash
cat terraform/terraform.tfvars | grep -A3 "Elastic IP"

# Should show:
# # Elastic IP Configuration (for internet routing)
# allocate_eips = false
# primary_outside_eip_id = ""
# backup_outside_eip_id = ""
```

### Step 3: Terraform Plan

**Expected Output:**
- [ ] No EIP resources in plan
- [ ] No EIP association resources in plan

```bash
cd terraform
terraform plan | grep -i eip

# Should show nothing
```

### Step 4: Terraform Apply

```bash
terraform apply
```

**Expected Results:**
- [ ] FortiGate instances created
- [ ] No EIPs created or associated
- [ ] All resources created without errors

**Verify No EIP Associations:**
```bash
# Check primary outside ENI
aws ec2 describe-network-interfaces \
  --network-interface-ids <primary-outside-eni-id> \
  --profile renaws \
  --region us-east-1 \
  --query 'NetworkInterfaces[0].Association'

# Should return null or empty
```

### Step 5: Cleanup

```bash
cd terraform
terraform destroy
```

---

## Test Scenario 4: Skip Validation Mode

### Test with --skip-validation Flag

```bash
python3 deploy.py --skip-validation
```

**Expected Behavior:**
- [ ] Warning message displayed about skipped validation
- [ ] EIP validation skipped
- [ ] Terraform will validate during deployment
- [ ] Deployment proceeds without AWS API validation

---

## Test Scenario 5: Configuration File

### Create Configuration File

```bash
cat > test-config.json << 'EOF'
{
  "aws": {
    "region": "us-east-1",
    "profile": "renaws"
  },
  "network": {
    "vpc_id": "vpc-0e16490e6ab8422fb",
    "availability_zones": ["us-east-1a", "us-east-1b"],
    "allocate_eips": true,
    "primary_outside_eip_id": "eipalloc-xxxxx",
    "backup_outside_eip_id": "eipalloc-xxxxx",
    ...
  }
}
EOF
```

### Deploy with Configuration File

```bash
python3 deploy.py --config test-config.json
```

**Expected Behavior:**
- [ ] Configuration loaded from file
- [ ] EIP settings applied from config
- [ ] No interactive prompts for network configuration
- [ ] Deployment proceeds with file configuration

---

## Validation Checklist

### Code Quality
- [x] No syntax errors in deploy.py
- [x] All imports present
- [x] Type hints correct
- [x] Dataclass fields properly defined

### Functionality
- [ ] EIP allocation IDs validated correctly
- [ ] EIP associations created successfully
- [ ] Public IPs assigned to outside ENIs
- [ ] Terraform variables generated correctly
- [ ] Interactive prompts work as expected

### Error Handling
- [ ] Invalid EIP allocation IDs rejected
- [ ] Missing EIP allocation IDs handled gracefully
- [ ] AWS API errors caught and reported
- [ ] User-friendly error messages displayed

### Documentation
- [x] EIP-SUPPORT-SUMMARY.md created
- [x] EIP-TESTING-CHECKLIST.md created
- [ ] README updated with EIP information (if needed)

---

## Success Criteria

All test scenarios should:
1. Complete without errors
2. Create/associate EIPs as expected
3. Generate correct terraform.tfvars
4. Validate EIP allocation IDs when provided
5. Handle missing EIP allocation IDs gracefully
6. Clean up resources properly

## Notes

- EIPs created by create-enis.py are NOT destroyed by Terraform (referenced via data source)
- EIPs created by Terraform ARE destroyed by Terraform
- Always verify EIP associations after deployment
- Test internet connectivity through FortiGate outside interfaces
- Document public IP addresses for firewall rules and allowlists
