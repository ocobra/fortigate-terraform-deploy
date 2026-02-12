# Custom Tag Feature for Resource Identification

## Overview

The `create-enis.py` script now supports a `--tag` option that adds a custom "CreatedBy" tag to all resources created by the script. This makes it easy to identify and manage resources created during specific deployments or by specific users.

## Usage

### Basic Syntax

```bash
python3 create-enis.py --profile <profile> --region <region> --account <account-id> --tag <tag-value>
```

### Examples

#### Example 1: Tag by Deployment ID

```bash
python3 create-enis.py --profile renaws --region us-east-1 --account 678632990402 --tag "deployment-001"
```

This will add the following tag to all created resources:
- **Key**: `CreatedBy`
- **Value**: `deployment-001`

#### Example 2: Tag by User

```bash
python3 create-enis.py --profile renaws --region us-east-1 --account 678632990402 --tag "john-test"
```

This will add:
- **Key**: `CreatedBy`
- **Value**: `john-test`

#### Example 3: Tag by Environment and Date

```bash
python3 create-enis.py --profile renaws --region us-east-1 --account 678632990402 --tag "prod-2024-02-12"
```

This will add:
- **Key**: `CreatedBy`
- **Value**: `prod-2024-02-12`

#### Example 4: With EIP Allocation

```bash
python3 create-enis.py --profile renaws --region us-east-1 --account 678632990402 \
  --allocate-eips --tag "deployment-001"
```

This will tag both ENIs and EIPs with the custom tag.

## Resources Tagged

The custom tag is applied to:

1. **Network Interfaces (ENIs)** - All 8 ENIs (4 primary + 4 backup)
2. **Security Groups** - All 3 security groups (mgmt, data, ha)
3. **Elastic IPs** - Both EIPs if `--allocate-eips` is used

## Default Tags

All resources also receive these default tags:

- `Project`: FortiGate-HA-Deployment
- `ManagedBy`: Terraform
- `Environment`: prod
- `Owner`: NetworkTeam

Plus resource-specific tags:
- `Name`: Resource-specific name
- `Interface`: Interface type (outside, inside, ha, mgmt)
- `FortiGateRole`: primary or backup

## Finding Resources by Custom Tag

### Using AWS CLI

#### List all ENIs with your custom tag

```bash
aws ec2 describe-network-interfaces \
  --filters "Name=tag:CreatedBy,Values=deployment-001" \
  --profile renaws \
  --region us-east-1 \
  --query 'NetworkInterfaces[*].[NetworkInterfaceId,Description,PrivateIpAddress]' \
  --output table
```

#### List all Security Groups with your custom tag

```bash
aws ec2 describe-security-groups \
  --filters "Name=tag:CreatedBy,Values=deployment-001" \
  --profile renaws \
  --region us-east-1 \
  --query 'SecurityGroups[*].[GroupId,GroupName,Description]' \
  --output table
```

#### List all EIPs with your custom tag

```bash
aws ec2 describe-addresses \
  --filters "Name=tag:CreatedBy,Values=deployment-001" \
  --profile renaws \
  --region us-east-1 \
  --query 'Addresses[*].[AllocationId,PublicIp,NetworkInterfaceId]' \
  --output table
```

#### List ALL resources with your custom tag

```bash
aws resourcegroupstaggingapi get-resources \
  --tag-filters "Key=CreatedBy,Values=deployment-001" \
  --profile renaws \
  --region us-east-1 \
  --query 'ResourceTagMappingList[*].[ResourceARN]' \
  --output table
```

### Using AWS Console

1. Go to EC2 Dashboard
2. Select "Network Interfaces", "Security Groups", or "Elastic IPs"
3. Add filter: `CreatedBy` = `your-tag-value`
4. View all resources with that tag

## Cleanup by Custom Tag

### Delete all ENIs with custom tag

```bash
# Get ENI IDs
ENI_IDS=$(aws ec2 describe-network-interfaces \
  --filters "Name=tag:CreatedBy,Values=deployment-001" \
  --profile renaws \
  --region us-east-1 \
  --query 'NetworkInterfaces[*].NetworkInterfaceId' \
  --output text)

# Delete each ENI
for eni_id in $ENI_IDS; do
  echo "Deleting ENI: $eni_id"
  aws ec2 delete-network-interface \
    --network-interface-id $eni_id \
    --profile renaws \
    --region us-east-1
done
```

### Release all EIPs with custom tag

```bash
# Get EIP allocation IDs
EIP_IDS=$(aws ec2 describe-addresses \
  --filters "Name=tag:CreatedBy,Values=deployment-001" \
  --profile renaws \
  --region us-east-1 \
  --query 'Addresses[*].AllocationId' \
  --output text)

# Release each EIP
for eip_id in $EIP_IDS; do
  echo "Releasing EIP: $eip_id"
  aws ec2 release-address \
    --allocation-id $eip_id \
    --profile renaws \
    --region us-east-1
done
```

### Delete all Security Groups with custom tag

```bash
# Get Security Group IDs
SG_IDS=$(aws ec2 describe-security-groups \
  --filters "Name=tag:CreatedBy,Values=deployment-001" \
  --profile renaws \
  --region us-east-1 \
  --query 'SecurityGroups[*].GroupId' \
  --output text)

# Delete each Security Group
for sg_id in $SG_IDS; do
  echo "Deleting Security Group: $sg_id"
  aws ec2 delete-security-group \
    --group-id $sg_id \
    --profile renaws \
    --region us-east-1
done
```

## Use Cases

### 1. Multiple Deployments

When testing multiple deployments, use different tags:

```bash
# First deployment
python3 create-enis.py --tag "test-deployment-1" ...

# Second deployment
python3 create-enis.py --tag "test-deployment-2" ...

# Third deployment
python3 create-enis.py --tag "test-deployment-3" ...
```

Now you can easily identify and clean up each deployment separately.

### 2. User Identification

When multiple team members are creating resources:

```bash
# John's deployment
python3 create-enis.py --tag "john-dev" ...

# Sarah's deployment
python3 create-enis.py --tag "sarah-test" ...
```

### 3. Environment Tracking

Track resources by environment:

```bash
# Development
python3 create-enis.py --tag "dev-env" ...

# Staging
python3 create-enis.py --tag "staging-env" ...

# Production
python3 create-enis.py --tag "prod-env" ...
```

### 4. Date-Based Tracking

Track resources by creation date:

```bash
python3 create-enis.py --tag "created-2024-02-12" ...
```

## Best Practices

1. **Use Descriptive Tags**: Choose tag values that clearly identify the purpose or owner
   - Good: `deployment-001`, `john-test`, `prod-2024-02-12`
   - Bad: `test`, `abc`, `123`

2. **Consistent Naming**: Use a consistent naming convention across your team
   - Format: `<user>-<purpose>` (e.g., `john-testing`)
   - Format: `<env>-<date>` (e.g., `prod-2024-02-12`)
   - Format: `<project>-<id>` (e.g., `fortigate-001`)

3. **Document Tags**: Keep a record of which tags are used for which deployments

4. **Clean Up**: Always clean up resources when done testing
   ```bash
   # List resources before cleanup
   aws resourcegroupstaggingapi get-resources \
     --tag-filters "Key=CreatedBy,Values=your-tag" \
     --profile renaws --region us-east-1
   
   # Then delete resources
   ```

5. **Avoid Special Characters**: Stick to alphanumeric characters and hyphens
   - Good: `deployment-001`, `john-test`
   - Avoid: `deployment#001`, `john's-test`

## Output Example

When you run the script with a custom tag:

```bash
python3 create-enis.py --profile renaws --region us-east-1 --account 678632990402 --tag "deployment-001"
```

You'll see:

```
🚀 Creating Network Interfaces for FortiGate HA Deployment
======================================================================
Region: us-east-1
Account: 678632990402
Profile: renaws
Custom Tag: CreatedBy=deployment-001

✅ Using AWS profile: renaws
✅ Authenticated as: arn:aws:iam::678632990402:user/john
✅ Account ID: 678632990402

...

✅ Created ENI: eni-xxxxx (FortiGate Primary OUTSIDE interface) - IP: 10.0.1.10
✅ Created ENI: eni-xxxxx (FortiGate Primary INSIDE interface) - IP: 10.0.2.10
...
```

## Verification

After creating resources, verify the custom tag was applied:

```bash
# Check a specific ENI
aws ec2 describe-network-interfaces \
  --network-interface-ids eni-xxxxx \
  --profile renaws \
  --region us-east-1 \
  --query 'NetworkInterfaces[0].TagSet[?Key==`CreatedBy`]'

# Expected output:
# [
#     {
#         "Key": "CreatedBy",
#         "Value": "deployment-001"
#     }
# ]
```

## Troubleshooting

### Issue: Tag not appearing on resources

**Cause**: Tag value might contain invalid characters

**Solution**: Use only alphanumeric characters, hyphens, and underscores

### Issue: Cannot find resources by tag

**Cause**: Tag might not have been applied due to permissions

**Solution**: 
- Verify you have `ec2:CreateTags` permission
- Check CloudTrail logs for tag creation events
- Verify the tag value matches exactly (case-sensitive)

## Integration with Terraform

The custom tag helps identify resources that should NOT be managed by Terraform:

```hcl
# In Terraform, you can filter out resources with specific tags
data "aws_network_interfaces" "existing" {
  filter {
    name   = "tag:CreatedBy"
    values = ["deployment-001"]
  }
}
```

## Summary

The `--tag` option provides:
- Easy resource identification
- Simplified cleanup
- Better resource management
- Team collaboration support
- Deployment tracking

Use it whenever you create resources with `create-enis.py` to maintain clear ownership and simplify resource management!
