# delete-enis.py - Implementation Summary

## Overview

Created a comprehensive resource deletion script that safely removes all resources created by `create-enis.py` using the `CreatedBy` tag.

## Files Created

1. **delete-enis.py** - Main deletion script (executable)
2. **DELETE-RESOURCES-GUIDE.md** - Complete usage guide
3. **DELETE-QUICK-REFERENCE.md** - Quick reference card

## Features

### Core Functionality

✅ **Tag-Based Deletion**
- Finds resources by `CreatedBy` tag
- Supports multiple deployments with different tags
- Prevents accidental deletion of unrelated resources

✅ **Resource Types Handled**
- Elastic IPs (EIPs) - Disassociate and release
- Network Interfaces (ENIs) - Detach and delete
- Security Groups - Delete with retry logic

✅ **Safety Features**
- Confirmation prompt (requires typing "DELETE")
- Dry-run mode to preview deletions
- Force mode for automation (use carefully)
- Detailed resource listing before deletion

✅ **Error Handling**
- Graceful handling of resources in use
- Automatic retry for security group dependencies
- Detailed error messages
- Partial deletion support

✅ **Progress Reporting**
- Real-time deletion progress
- Success/error counts
- Final summary report

## Usage Examples

### Basic Usage

```bash
# Dry run (recommended first step)
python3 delete-enis.py --profile renaws --region us-east-1 --tag "deployment-001" --dry-run

# Delete with confirmation
python3 delete-enis.py --profile renaws --region us-east-1 --tag "deployment-001"

# Force delete (no confirmation)
python3 delete-enis.py --profile renaws --region us-east-1 --tag "deployment-001" --force
```

### Real-World Scenarios

#### Scenario 1: Test Deployment Cleanup
```bash
# Create test resources
python3 create-enis.py --profile renaws --region us-east-1 --account 678632990402 \
  --allocate-eips --tag "john-test"

# Test deployment...

# Clean up
python3 delete-enis.py --profile renaws --region us-east-1 --tag "john-test"
```

#### Scenario 2: Multiple Deployments
```bash
# Clean up multiple test deployments
for tag in deployment-001 deployment-002 john-test sarah-dev; do
  echo "Cleaning up: $tag"
  python3 delete-enis.py --profile renaws --region us-east-1 --tag "$tag" --force
done
```

#### Scenario 3: Automated Testing
```bash
#!/bin/bash
TAG="test-$(date +%Y%m%d-%H%M%S)"

# Create resources
python3 create-enis.py --profile renaws --region us-east-1 --account 678632990402 --tag "$TAG"

# Run tests
./run-tests.sh

# Cleanup
python3 delete-enis.py --profile renaws --region us-east-1 --tag "$TAG" --force
```

## Deletion Process

### Order of Operations

1. **Elastic IPs**
   - Disassociate from ENIs
   - Release allocations
   - Wait between operations

2. **Network Interfaces**
   - Detach from instances (if attached)
   - Wait for detachment to complete
   - Delete ENI resources

3. **Security Groups**
   - Attempt deletion
   - Retry up to 3 times if dependencies exist
   - Report any remaining dependencies

### Timing

- EIP disassociation: ~1-2 seconds per EIP
- ENI detachment: ~5-10 seconds per ENI
- ENI deletion: ~1-2 seconds per ENI
- Security group deletion: ~1-2 seconds per SG (may retry)

**Total time**: ~1-3 minutes for typical deployment (8 ENIs, 2 EIPs, 3 SGs)

## Safety Mechanisms

### 1. Confirmation Prompt

```
⚠️  WARNING: DESTRUCTIVE OPERATION
======================================================================

You are about to DELETE 13 resources with tag:
  CreatedBy = deployment-001

This action CANNOT be undone!

Type 'DELETE' (in capital letters) to confirm:
```

### 2. Dry Run Mode

```bash
python3 delete-enis.py --profile renaws --region us-east-1 --tag "deployment-001" --dry-run
```

Shows what would be deleted without actually deleting.

### 3. Tag Filtering

Only resources with exact `CreatedBy` tag match are deleted.

### 4. Detailed Listing

Shows complete details of each resource before deletion:
- Resource IDs
- Descriptions
- IP addresses
- Attachment status
- Association status

## Error Handling

### Common Errors and Solutions

| Error | Cause | Solution |
|-------|-------|----------|
| ENI in use | Attached to running instance | Terminate instance first |
| SG has dependencies | Referenced by other resources | Script retries automatically |
| EIP still associated | Association not removed | Script handles automatically |
| No resources found | Wrong tag or already deleted | Verify tag value |

### Retry Logic

- Security groups: 3 attempts with 5-second delays
- ENI detachment: Waits up to 100 seconds for completion
- Graceful degradation: Continues with other resources if one fails

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

🔍 Searching for resources with tag: CreatedBy=deployment-001
✅ Found 8 Network Interface(s)
✅ Found 2 Elastic IP(s)
✅ Found 3 Security Group(s)

📊 Summary: 13 resource(s) found

🗑️  Starting deletion process...
✅ Released EIP: eipalloc-xxxxx (2/2)
✅ Deleted ENI: eni-xxxxx (8/8)
✅ Deleted Security Group: sg-xxxxx (3/3)

======================================================================
🏁 Deletion Summary
======================================================================
✅ Successfully deleted: 13 resource(s)
✅ All resources deleted successfully!
```

### No Resources Found

```
🔍 Searching for resources with tag: CreatedBy=deployment-001
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

## Integration with create-enis.py

### Complete Lifecycle

```bash
# 1. Create resources
python3 create-enis.py --profile renaws --region us-east-1 --account 678632990402 \
  --allocate-eips --tag "deployment-001"

# 2. Deploy and test
python3 deploy.py
# ... testing ...

# 3. Destroy Terraform resources
terraform destroy

# 4. Clean up ENIs and related resources
python3 delete-enis.py --profile renaws --region us-east-1 --tag "deployment-001"
```

### Tag Consistency

Both scripts use the same `CreatedBy` tag:
- `create-enis.py --tag "value"` creates resources with tag
- `delete-enis.py --tag "value"` deletes resources with tag

## Best Practices

### 1. Always Dry Run First

```bash
python3 delete-enis.py --profile renaws --region us-east-1 --tag "deployment-001" --dry-run
```

### 2. Verify Tag Value

```bash
# List all CreatedBy tags
aws resourcegroupstaggingapi get-resources \
  --tag-filters "Key=CreatedBy" \
  --profile renaws --region us-east-1 \
  --query 'ResourceTagMappingList[*].Tags[?Key==`CreatedBy`].Value' \
  --output text | sort -u
```

### 3. Terminate Instances First

If ENIs are attached to EC2 instances:

```bash
# Terminate instances
terraform destroy

# Then clean up ENIs
python3 delete-enis.py --profile renaws --region us-east-1 --tag "deployment-001"
```

### 4. Log Deletions

```bash
python3 delete-enis.py --profile renaws --region us-east-1 --tag "deployment-001" \
  2>&1 | tee deletion-log-$(date +%Y%m%d-%H%M%S).txt
```

### 5. Use Unique Tags

- Include date: `deployment-2024-02-12`
- Include user: `john-test`
- Include purpose: `testing-bgp`

## Command-Line Options

| Option | Required | Default | Description |
|--------|----------|---------|-------------|
| `--profile` | No | None | AWS CLI profile name |
| `--region` | No | us-east-1 | AWS region |
| `--tag` | **Yes** | - | CreatedBy tag value |
| `--dry-run` | No | False | List resources without deleting |
| `--force` | No | False | Skip confirmation prompt |

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success - all resources deleted or none found |
| 1 | Error - some resources failed to delete |
| 1 | Cancelled by user |
| 1 | Authentication error |

## Permissions Required

The AWS credentials must have these permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ec2:DescribeNetworkInterfaces",
        "ec2:DescribeAddresses",
        "ec2:DescribeSecurityGroups",
        "ec2:DeleteNetworkInterface",
        "ec2:DetachNetworkInterface",
        "ec2:DisassociateAddress",
        "ec2:ReleaseAddress",
        "ec2:DeleteSecurityGroup"
      ],
      "Resource": "*"
    }
  ]
}
```

## Testing

### Test Scenarios

1. **Dry Run Test**
   ```bash
   python3 delete-enis.py --profile renaws --region us-east-1 --tag "test" --dry-run
   ```

2. **Delete Empty Tag**
   ```bash
   python3 delete-enis.py --profile renaws --region us-east-1 --tag "nonexistent"
   ```

3. **Delete with Confirmation**
   ```bash
   python3 delete-enis.py --profile renaws --region us-east-1 --tag "test"
   # Type "DELETE"
   ```

4. **Force Delete**
   ```bash
   python3 delete-enis.py --profile renaws --region us-east-1 --tag "test" --force
   ```

## Troubleshooting

### Script Won't Run

```bash
# Make executable
chmod +x delete-enis.py

# Check Python version
python3 --version  # Should be 3.6+

# Check boto3 installed
python3 -c "import boto3; print(boto3.__version__)"
```

### Authentication Errors

```bash
# Verify AWS credentials
aws sts get-caller-identity --profile renaws

# Check profile exists
cat ~/.aws/credentials | grep renaws
```

### Resources Not Found

```bash
# Check region
aws ec2 describe-network-interfaces \
  --filters "Name=tag:CreatedBy,Values=deployment-001" \
  --profile renaws --region us-east-1

# Try different region
python3 delete-enis.py --profile renaws --region us-west-2 --tag "deployment-001" --dry-run
```

## Summary

The `delete-enis.py` script provides:

✅ Safe, automated resource cleanup  
✅ Tag-based filtering for precision  
✅ Dry-run mode for verification  
✅ Comprehensive error handling  
✅ Detailed progress reporting  
✅ Integration with create-enis.py  

**Use Case**: Clean up test deployments, remove failed deployments, maintain clean AWS environment

**Safety**: Multiple confirmation layers prevent accidental deletions

**Efficiency**: Deletes all resources in 1-3 minutes

Ready to use for production cleanup operations! 🗑️✨
