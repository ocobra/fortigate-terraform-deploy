# Custom Tag Feature - Visual Example

## Before (Without Custom Tag)

### Command
```bash
python3 create-enis.py --profile renaws --region us-east-1 --account 678632990402
```

### Tags Applied to Resources
```
Project: FortiGate-HA-Deployment
ManagedBy: Terraform
Environment: prod
Owner: NetworkTeam
Name: fortigate-primary-outside
Interface: outside
FortiGateRole: primary
```

### Finding Resources
```bash
# Must use generic tags
aws ec2 describe-network-interfaces \
  --filters "Name=tag:Project,Values=FortiGate-HA-Deployment"
  
# Returns ALL FortiGate ENIs from ALL deployments
# Cannot distinguish between different deployments
```

---

## After (With Custom Tag)

### Command
```bash
python3 create-enis.py --profile renaws --region us-east-1 --account 678632990402 --tag "deployment-001"
```

### Tags Applied to Resources
```
Project: FortiGate-HA-Deployment
ManagedBy: Terraform
Environment: prod
Owner: NetworkTeam
CreatedBy: deployment-001          ← NEW!
Name: fortigate-primary-outside
Interface: outside
FortiGateRole: primary
```

### Finding Resources
```bash
# Use specific custom tag
aws ec2 describe-network-interfaces \
  --filters "Name=tag:CreatedBy,Values=deployment-001"
  
# Returns ONLY ENIs from deployment-001
# Easy to distinguish between different deployments
```

---

## Real-World Scenario

### Scenario: Three Team Members Testing

#### John's Deployment
```bash
python3 create-enis.py --profile renaws --region us-east-1 --account 678632990402 --tag "john-test"
```

**Resources Created**:
- 8 ENIs tagged with `CreatedBy: john-test`
- 3 Security Groups tagged with `CreatedBy: john-test`

#### Sarah's Deployment
```bash
python3 create-enis.py --profile renaws --region us-east-1 --account 678632990402 --tag "sarah-dev"
```

**Resources Created**:
- 8 ENIs tagged with `CreatedBy: sarah-dev`
- 3 Security Groups tagged with `CreatedBy: sarah-dev`

#### Production Deployment
```bash
python3 create-enis.py --profile renaws --region us-east-1 --account 678632990402 --tag "prod-2024-02-12"
```

**Resources Created**:
- 8 ENIs tagged with `CreatedBy: prod-2024-02-12`
- 3 Security Groups tagged with `CreatedBy: prod-2024-02-12`

### Finding John's Resources
```bash
aws ec2 describe-network-interfaces \
  --filters "Name=tag:CreatedBy,Values=john-test" \
  --query 'NetworkInterfaces[*].[NetworkInterfaceId,Description]' \
  --output table

# Output:
# eni-111111  FortiGate Primary OUTSIDE interface
# eni-222222  FortiGate Primary INSIDE interface
# eni-333333  FortiGate Primary HA interface
# eni-444444  FortiGate Primary MGMT interface
# eni-555555  FortiGate Backup OUTSIDE interface
# eni-666666  FortiGate Backup INSIDE interface
# eni-777777  FortiGate Backup HA interface
# eni-888888  FortiGate Backup MGMT interface
```

### Cleaning Up John's Resources
```bash
# Get all John's ENI IDs
ENI_IDS=$(aws ec2 describe-network-interfaces \
  --filters "Name=tag:CreatedBy,Values=john-test" \
  --query 'NetworkInterfaces[*].NetworkInterfaceId' \
  --output text)

# Delete them
for eni_id in $ENI_IDS; do
  echo "Deleting $eni_id"
  aws ec2 delete-network-interface --network-interface-id $eni_id
done

# Sarah's and Production resources remain untouched!
```

---

## Cost Tracking Example

### AWS Cost Explorer

With custom tags, you can track costs by deployment:

```
Filter by Tag: CreatedBy = deployment-001
Monthly Cost: $245.67

Filter by Tag: CreatedBy = john-test
Monthly Cost: $12.34

Filter by Tag: CreatedBy = prod-2024-02-12
Monthly Cost: $1,234.56
```

---

## Resource Inventory Example

### Before Custom Tag

```bash
aws ec2 describe-network-interfaces \
  --filters "Name=tag:Project,Values=FortiGate-HA-Deployment" \
  --query 'NetworkInterfaces[*].[NetworkInterfaceId,Description]' \
  --output table

# Output: 24 ENIs (3 deployments × 8 ENIs each)
# Cannot tell which ENIs belong to which deployment
```

### After Custom Tag

```bash
# List all deployments
aws resourcegroupstaggingapi get-resources \
  --tag-filters "Key=CreatedBy" \
  --resource-type-filters "ec2:network-interface" \
  --query 'ResourceTagMappingList[*].Tags[?Key==`CreatedBy`].Value' \
  --output text | sort -u

# Output:
# deployment-001
# john-test
# prod-2024-02-12
# sarah-dev

# Now list resources for each deployment
for tag in deployment-001 john-test prod-2024-02-12 sarah-dev; do
  echo "=== Resources for $tag ==="
  aws ec2 describe-network-interfaces \
    --filters "Name=tag:CreatedBy,Values=$tag" \
    --query 'NetworkInterfaces[*].[NetworkInterfaceId,Description]' \
    --output table
  echo ""
done
```

---

## Terraform Integration Example

### Exclude Tagged Resources from Terraform

```hcl
# data.tf
data "aws_network_interfaces" "manual_enis" {
  filter {
    name   = "tag:CreatedBy"
    values = ["deployment-001"]
  }
}

# main.tf
# Terraform will not manage these ENIs
# They are referenced but not created/destroyed by Terraform
```

---

## Audit Trail Example

### Who Created What?

```bash
# List all unique CreatedBy tags
aws resourcegroupstaggingapi get-resources \
  --tag-filters "Key=CreatedBy" \
  --query 'ResourceTagMappingList[*].Tags[?Key==`CreatedBy`].Value' \
  --output text | sort -u

# Output:
# deployment-001
# deployment-002
# deployment-003
# john-test
# sarah-dev
# prod-2024-02-12
# prod-2024-02-13

# Count resources per tag
for tag in $(aws resourcegroupstaggingapi get-resources \
  --tag-filters "Key=CreatedBy" \
  --query 'ResourceTagMappingList[*].Tags[?Key==`CreatedBy`].Value' \
  --output text | sort -u); do
  
  count=$(aws resourcegroupstaggingapi get-resources \
    --tag-filters "Key=CreatedBy,Values=$tag" \
    --query 'length(ResourceTagMappingList)' \
    --output text)
  
  echo "$tag: $count resources"
done

# Output:
# deployment-001: 11 resources (8 ENIs + 3 SGs)
# deployment-002: 11 resources
# john-test: 11 resources
# sarah-dev: 13 resources (8 ENIs + 3 SGs + 2 EIPs)
# prod-2024-02-12: 13 resources
```

---

## Summary

The custom tag feature transforms resource management from:

**Before**: "Which resources belong to which deployment?"
- Hard to identify
- Manual tracking required
- Risk of deleting wrong resources

**After**: "Show me all resources for deployment-001"
- Instant identification
- Automated tracking
- Safe, targeted cleanup

Use `--tag` on every deployment for better resource management!
