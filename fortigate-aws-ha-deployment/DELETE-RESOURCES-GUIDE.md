# Resource Deletion Guide - delete-enis.py

## Overview

The `delete-enis.py` script safely deletes all resources created by `create-enis.py` by finding them using the `CreatedBy` tag. This provides a clean and automated way to remove test deployments or clean up after failed deployments.

## What Gets Deleted

The script deletes resources in this order:

1. **Elastic IPs (EIPs)**
   - Disassociates EIPs from ENIs
   - Releases EIP allocations

2. **Network Interfaces (ENIs)**
   - Detaches ENIs from instances (if attached)
   - Deletes ENI resources

3. **Security Groups**
   - Deletes security groups created by create-enis.py
   - Retries if dependencies exist

## Safety Features

### 1. Confirmation Required
- Script requires typing "DELETE" (in capitals) to confirm
- Shows detailed list of resources before deletion
- Can be bypassed with `--force` flag (use carefully!)

### 2. Dry Run Mode
- Use `--dry-run` to see what would be deleted without actually deleting
- Perfect for verification before actual deletion

### 3. Tag-Based Filtering
- Only deletes resources with matching `CreatedBy` tag
- Prevents accidental deletion of other resources
- Supports multiple deployments with different tags

### 4. Error Handling
- Gracefully handles resources in use
- Retries security group deletion if dependencies exist
- Reports detailed error messages

## Usage

### Basic Syntax

```bash
python3 delete-enis.py --profile <profile> --region <region> --tag <tag-value>
```

### Examples

#### Example 1: Dry Run (Recommended First Step)

```bash
# See what would be deleted without actually deleting
python3 delete-enis.py --profile renaws --region us-east-1 --tag "deployment-001" --dry-run
```

**Output**:
```
🔍 Searching for resources with tag: CreatedBy=deployment-001
✅ Found 8 Network Interface(s)
✅ Found 2 Elastic IP(s)
✅ Found 3 Security Group(s)

📋 Resource Details:
...

✅ DRY RUN completed - no resources were deleted
```

#### Example 2: Delete with Confirmation

```bash
# Delete resources with confirmation prompt
python3 delete-enis.py --profile renaws --region us-east-1 --tag "deployment-001"
```

**Interaction**:
```
⚠️  WARNING: DESTRUCTIVE OPERATION
You are about to DELETE 13 resources with tag:
  CreatedBy = deployment-001

Type 'DELETE' (in capital letters) to confirm: DELETE

🗑️  Starting deletion process...
✅ Successfully deleted: 13 resource(s)
```

#### Example 3: Force Delete (No Confirmation)

```bash
# Delete without confirmation (use carefully!)
python3 delete-enis.py --profile renaws --region us-east-1 --tag "deployment-001" --force
```

#### Example 4: Delete Multiple Deployments

```bash
# Delete first deployment
python3 delete-enis.py --profile renaws --region us-east-1 --tag "deployment-001"

# Delete second deployment
python3 delete-enis.py --profile renaws --region us-east-1 --tag "deployment-002"

# Delete test deployment
python3 delete-enis.py --profile renaws --region us-east-1 --tag "john-test"
```

## Command-Line Options

| Option | Required | Description |
|--------|----------|-------------|
| `--profile` | No | AWS CLI profile name |
| `--region` | No | AWS region (default: us-east-1) |
| `--tag` | **Yes** | CreatedBy tag value to identify resources |
| `--dry-run` | No | List resources without deleting |
| `--force` | No | Skip confirmation prompt |

## Workflow

### Recommended Workflow

```bash
# Step 1: Dry run to see what will be deleted
python3 delete-enis.py --profile renaws --region us-east-1 --tag "deployment-001" --dry-run

# Step 2: Review the output carefully

# Step 3: Delete with confirmation
python3 delete-enis.py --profile renaws --region us-east-1 --tag "deployment-001"

# Step 4: Type "DELETE" when prompted

# Step 5: Verify deletion completed successfully
```

### Automated Workflow (Scripts)

```bash
#!/bin/bash
# cleanup-deployment.sh

TAG="deployment-001"
PROFILE="renaws"
REGION="us-east-1"

echo "Cleaning up deployment: $TAG"

# Dry run first
python3 delete-enis.py --profile $PROFILE --region $REGION --tag "$TAG" --dry-run

# Ask for confirmation
read -p "Proceed with deletion? (yes/no): " confirm

if [ "$confirm" = "yes" ]; then
    python3 delete-enis.py --profile $PROFILE --region $REGION --tag "$TAG" --force
    echo "Cleanup completed"
else
    echo "Cleanup cancelled"
fi
```

## Output Examples

### Successful Deletion

```
🗑️  FortiGate HA Deployment - Resource Cleanup
======================================================================
Region: us-east-1
Profile: renaws
Tag: CreatedBy=deployment-001

✅ Using AWS profile: renaws
✅ Authenticated as: arn:aws:iam::678632990402:user/admin
✅ Account ID: 678632990402

🔍 Searching for resources with tag: CreatedBy=deployment-001
----------------------------------------------------------------------
✅ Found 8 Network Interface(s)
✅ Found 2 Elastic IP(s)
✅ Found 3 Security Group(s)

📋 Resource Details:
======================================================================

🔌 Network Interfaces (ENIs):
----------------------------------------------------------------------
  • eni-0123456789abcdef0
    Description: FortiGate Primary OUTSIDE interface
    Private IP: 10.0.1.10
    Status: available
    Attached to: Not attached
    Public IP: 54.123.45.67

...

🌐 Elastic IPs (EIPs):
----------------------------------------------------------------------
  • eipalloc-0123456789abcdef0
    Public IP: 54.123.45.67
    Associated with: eni-0123456789abcdef0
    Association ID: eipassoc-0123456789abcdef0

...

🔒 Security Groups:
----------------------------------------------------------------------
  • sg-0123456789abcdef0
    Name: fortigate-mgmt-sg
    Description: Security group for FortiGate management interface
    VPC: vpc-0e16490e6ab8422fb

...

📊 Summary: 13 resource(s) found
  • 8 Network Interface(s)
  • 2 Elastic IP(s)
  • 3 Security Group(s)

⚠️  WARNING: DESTRUCTIVE OPERATION
======================================================================

You are about to DELETE 13 resources with tag:
  CreatedBy = deployment-001

This action CANNOT be undone!

Type 'DELETE' (in capital letters) to confirm: DELETE

🗑️  Starting deletion process...
======================================================================

🌐 Disassociating and Releasing Elastic IPs...
----------------------------------------------------------------------
  Disassociating EIP 54.123.45.67 (eipalloc-0123456789abcdef0)...
  ✅ Disassociated
  Releasing EIP 54.123.45.67 (eipalloc-0123456789abcdef0)...
  ✅ Released EIP: eipalloc-0123456789abcdef0
  ...

🔌 Deleting Network Interfaces...
----------------------------------------------------------------------
  Deleting ENI eni-0123456789abcdef0 (FortiGate Primary OUTSIDE interface)...
  ✅ Deleted ENI: eni-0123456789abcdef0
  ...

🔒 Deleting Security Groups...
----------------------------------------------------------------------
  Deleting Security Group sg-0123456789abcdef0 (fortigate-mgmt-sg)...
  ✅ Deleted Security Group: sg-0123456789abcdef0
  ...

======================================================================
🏁 Deletion Summary
======================================================================
✅ Successfully deleted: 13 resource(s)
✅ All resources deleted successfully!
```

### No Resources Found

```
🔍 Searching for resources with tag: CreatedBy=deployment-001
----------------------------------------------------------------------
✅ Found 0 Network Interface(s)
✅ Found 0 Elastic IP(s)
✅ Found 0 Security Group(s)

✅ No resources found with the specified tag.
   Tag: CreatedBy=deployment-001

Possible reasons:
  1. Resources were already deleted
  2. Wrong tag value specified
  3. Resources are in a different region
  4. Resources don't have the CreatedBy tag
```

### Partial Deletion (Some Errors)

```
🗑️  Starting deletion process...
======================================================================

🌐 Disassociating and Releasing Elastic IPs...
----------------------------------------------------------------------
  ✅ Released EIP: eipalloc-0123456789abcdef0
  ✅ Released EIP: eipalloc-0123456789abcdef1

🔌 Deleting Network Interfaces...
----------------------------------------------------------------------
  ✅ Deleted ENI: eni-0123456789abcdef0
  ❌ Error deleting ENI eni-0123456789abcdef1: Network interface is currently in use
  ...

🔒 Deleting Security Groups...
----------------------------------------------------------------------
  ⚠️  Security Group sg-0123456789abcdef0 has dependencies, will retry...
  ✅ Deleted Security Group: sg-0123456789abcdef0

======================================================================
🏁 Deletion Summary
======================================================================
✅ Successfully deleted: 11 resource(s)
❌ Failed to delete: 2 resource(s)

Note: Some resources may have dependencies or be in use.
      Wait a few minutes and try again, or delete manually.
```

## Troubleshooting

### Issue 1: ENI Cannot Be Deleted (In Use)

**Error**:
```
❌ Error deleting ENI eni-xxxxx: Network interface is currently in use
```

**Cause**: ENI is attached to a running EC2 instance

**Solution**:
```bash
# Option 1: Stop/terminate the instance first
aws ec2 terminate-instances --instance-ids i-xxxxx --profile renaws --region us-east-1

# Wait for termination, then retry
python3 delete-enis.py --profile renaws --region us-east-1 --tag "deployment-001"

# Option 2: Force detach (if instance is stopped)
aws ec2 detach-network-interface --attachment-id eni-attach-xxxxx --force \
  --profile renaws --region us-east-1
```

### Issue 2: Security Group Has Dependencies

**Error**:
```
⚠️  Security Group sg-xxxxx has dependencies, will retry...
```

**Cause**: Security group is referenced by other resources or security groups

**Solution**:
- Script automatically retries 3 times
- If still fails, wait 5-10 minutes and retry
- Check for resources using the security group:

```bash
# Find resources using the security group
aws ec2 describe-network-interfaces \
  --filters "Name=group-id,Values=sg-xxxxx" \
  --profile renaws --region us-east-1

# Find security group rules referencing this SG
aws ec2 describe-security-groups \
  --filters "Name=ip-permission.group-id,Values=sg-xxxxx" \
  --profile renaws --region us-east-1
```

### Issue 3: EIP Cannot Be Released

**Error**:
```
❌ Error with EIP eipalloc-xxxxx: The address 'eipalloc-xxxxx' is still associated
```

**Cause**: EIP is still associated with an ENI

**Solution**:
```bash
# Disassociate manually
aws ec2 disassociate-address --association-id eipassoc-xxxxx \
  --profile renaws --region us-east-1

# Then release
aws ec2 release-address --allocation-id eipalloc-xxxxx \
  --profile renaws --region us-east-1
```

### Issue 4: Wrong Tag Value

**Error**:
```
✅ No resources found with the specified tag.
```

**Solution**:
```bash
# List all unique CreatedBy tags
aws resourcegroupstaggingapi get-resources \
  --tag-filters "Key=CreatedBy" \
  --profile renaws --region us-east-1 \
  --query 'ResourceTagMappingList[*].Tags[?Key==`CreatedBy`].Value' \
  --output text | sort -u

# Use the correct tag value
python3 delete-enis.py --profile renaws --region us-east-1 --tag "correct-tag-value"
```

## Best Practices

### 1. Always Dry Run First

```bash
# ALWAYS do a dry run first
python3 delete-enis.py --profile renaws --region us-east-1 --tag "deployment-001" --dry-run
```

### 2. Verify Resources Before Deletion

- Review the resource list carefully
- Ensure you're deleting the correct deployment
- Check that no production resources have the same tag

### 3. Delete in Correct Order

If manually deleting:
1. Terminate EC2 instances first (if any)
2. Run delete-enis.py to clean up ENIs, EIPs, and Security Groups

### 4. Keep Tag Values Unique

- Use descriptive, unique tag values
- Include date or deployment ID
- Examples: `deployment-001`, `test-2024-02-12`, `john-dev-env`

### 5. Document Deletions

```bash
# Log deletion for audit trail
python3 delete-enis.py --profile renaws --region us-east-1 --tag "deployment-001" \
  2>&1 | tee deletion-log-$(date +%Y%m%d-%H%M%S).txt
```

## Integration with create-enis.py

### Complete Lifecycle

```bash
# 1. Create resources with tag
python3 create-enis.py --profile renaws --region us-east-1 --account 678632990402 \
  --allocate-eips --tag "deployment-001"

# 2. Use resources for testing/deployment
# ... deploy FortiGate, test, etc ...

# 3. Clean up when done
python3 delete-enis.py --profile renaws --region us-east-1 --tag "deployment-001" --dry-run
python3 delete-enis.py --profile renaws --region us-east-1 --tag "deployment-001"
```

### Automated Testing Script

```bash
#!/bin/bash
# test-deployment.sh

TAG="test-$(date +%Y%m%d-%H%M%S)"
PROFILE="renaws"
REGION="us-east-1"
ACCOUNT="678632990402"

echo "Creating test deployment: $TAG"

# Create resources
python3 create-enis.py --profile $PROFILE --region $REGION --account $ACCOUNT \
  --allocate-eips --tag "$TAG"

if [ $? -eq 0 ]; then
    echo "Resources created successfully"
    
    # Run tests here
    # ...
    
    # Cleanup
    echo "Cleaning up test deployment"
    python3 delete-enis.py --profile $PROFILE --region $REGION --tag "$TAG" --force
else
    echo "Resource creation failed"
    exit 1
fi
```

## Safety Checklist

Before running delete-enis.py:

- [ ] Verified the correct tag value
- [ ] Ran dry-run mode first
- [ ] Reviewed the list of resources to be deleted
- [ ] Confirmed no production resources have the same tag
- [ ] Backed up any important data
- [ ] Terminated any EC2 instances using the ENIs
- [ ] Notified team members (if shared environment)
- [ ] Ready to type "DELETE" to confirm

## Summary

The `delete-enis.py` script provides:

- ✅ Safe, tag-based resource deletion
- ✅ Dry-run mode for verification
- ✅ Confirmation prompts to prevent accidents
- ✅ Detailed progress reporting
- ✅ Error handling and retry logic
- ✅ Complete cleanup of all created resources

Use it to maintain a clean AWS environment and easily remove test deployments!
