# FortiGate AMI and Licensing Guide

## Overview

This guide explains how to find FortiGate AMI IDs and understand the different licensing models available for FortiGate deployments on AWS.

## Finding FortiGate AMI IDs

### Method 1: AWS Console (Recommended for Manual Discovery)

1. **Navigate to EC2 AMI Section**:
   - Open AWS Console: https://console.aws.amazon.com/ec2/
   - Select your target region (e.g., us-east-1)
   - Click "AMIs" in the left sidebar under "Images"

2. **Search for FortiGate AMIs**:
   - Change filter from "Owned by me" to "Public images"
   - In the search box, enter one of these patterns:
     ```
     FortiGate-VM64-AWS-7.4-OnDemand
     FortiGate-VM64-AWS-7.2-OnDemand
     FortiGate-VM64-AWS-7.0-OnDemand
     ```
   - Or search by owner: `679593333241` (Fortinet's AWS account)

3. **Select the Appropriate AMI**:
   - Look for the most recent build date
   - Verify the FortiOS version matches your requirements
   - Note the AMI ID (format: `ami-0123456789abcdef0`)

4. **Copy the AMI ID**:
   - Select the AMI from the results
   - Copy the AMI ID from the details pane
   - Use this ID when the deployment script prompts you

### Method 2: AWS Marketplace

1. **Visit AWS Marketplace**:
   - Go to: https://aws.amazon.com/marketplace
   - Search for "FortiGate"

2. **Select FortiGate Product**:
   - Choose "Fortinet FortiGate Next-Generation Firewall"
   - Select the appropriate licensing model:
     - **On-Demand**: Pay-as-you-go hourly billing
     - **BYOL**: Bring Your Own License
     - **Reserved**: Discounted pricing with commitment

3. **Continue to Subscribe**:
   - Click "Continue to Subscribe"
   - Accept the terms
   - Click "Continue to Configuration"

4. **Get AMI ID**:
   - Select your region
   - Select FortiOS version
   - The AMI ID will be displayed
   - Copy the AMI ID for use in deployment

### Method 3: AWS CLI (Requires Valid Credentials)

If your AWS credentials are working, you can use the AWS CLI:

```bash
# Search for FortiGate 7.4 OnDemand AMIs
aws ec2 describe-images \
  --owners 679593333241 \
  --filters "Name=name,Values=FortiGate-VM64-AWS-7.4*OnDemand*" \
  --query 'Images[*].[ImageId,Name,CreationDate]' \
  --output table \
  --region us-east-1

# Search for FortiGate 7.2 OnDemand AMIs
aws ec2 describe-images \
  --owners 679593333241 \
  --filters "Name=name,Values=FortiGate-VM64-AWS-7.2*OnDemand*" \
  --query 'Images[*].[ImageId,Name,CreationDate]' \
  --output table \
  --region us-east-1
```

### Method 4: Fortinet Documentation

Visit Fortinet's official documentation:
- https://docs.fortinet.com/document/fortigate-public-cloud/latest/aws-administration-guide

The documentation includes AMI IDs for each region and FortiOS version.

## FortiGate Licensing Models

### 1. On-Demand (PAYG - Pay As You Go)

**Description**: Hourly billing with no upfront costs or long-term commitments.

**Characteristics**:
- No license file required
- Billing integrated with AWS
- Includes FortiGuard services
- Easy to start and stop
- Higher hourly cost

**Use Cases**:
- Testing and development
- Short-term deployments
- Variable workloads
- Proof of concept

**AMI Naming Pattern**: `FortiGate-VM64-AWS-{version}-OnDemand`

**Example AMI Names**:
- `FortiGate-VM64-AWS-7.4.1-OnDemand-build2463`
- `FortiGate-VM64-AWS-7.2.5-OnDemand-build1517`

### 2. BYOL (Bring Your Own License)

**Description**: Use existing FortiGate licenses purchased from Fortinet.

**Characteristics**:
- Requires valid FortiGate VM license file
- Lower AWS compute costs (no licensing markup)
- Separate FortiGuard subscription required
- License must match VM specifications
- More complex initial setup

**Use Cases**:
- Enterprise deployments
- Long-term production environments
- Organizations with existing Fortinet agreements
- Cost optimization for sustained use

**AMI Naming Pattern**: `FortiGate-VM64-AWS-{version}-BYOL`

**License Requirements**:
- Valid `.lic` file from Fortinet
- License must match instance type and vCPU count
- FortiGuard subscription (separate purchase)

**License Upload Process**:
1. Deploy FortiGate instance
2. Access FortiGate web UI
3. Navigate to System > FortiGuard
4. Upload license file
5. Reboot instance

### 3. Reserved Instances

**Description**: Discounted pricing with 1-year or 3-year commitment.

**Characteristics**:
- Significant cost savings (up to 60% off On-Demand)
- Requires upfront payment or commitment
- Region-specific
- Can be combined with BYOL for maximum savings

**Use Cases**:
- Production environments
- Predictable, steady-state workloads
- Long-term deployments
- Cost optimization

## AMI Selection Guidelines

### By FortiOS Version

| Version | Status | Recommendation |
|---------|--------|----------------|
| 7.6.x | Latest | Newest features, may have limited testing |
| 7.4.x | Stable | **Recommended** for production |
| 7.2.x | Mature | Proven stability, widely deployed |
| 7.0.x | Legacy | Consider upgrading |
| 6.4.x | EOL Soon | Upgrade recommended |

### By Instance Type

FortiGate performance varies by AWS instance type:

| Instance Type | vCPUs | Memory | Throughput | Use Case |
|---------------|-------|--------|------------|----------|
| c5.large | 2 | 4 GB | 1 Gbps | Small/Dev |
| c5.xlarge | 4 | 8 GB | 2.5 Gbps | Medium |
| c5.2xlarge | 8 | 16 GB | 5 Gbps | Large |
| c5.4xlarge | 16 | 32 GB | 10 Gbps | Enterprise |
| c5n.xlarge | 4 | 10.5 GB | 25 Gbps | High throughput |

### By Region

AMI IDs are **region-specific**. You must use the AMI ID for your target region.

**Common Regions**:
- `us-east-1` (N. Virginia)
- `us-west-2` (Oregon)
- `eu-west-1` (Ireland)
- `ap-southeast-1` (Singapore)

## Troubleshooting AMI Discovery

### Issue: "AWS was not able to validate the provided access credentials"

**Cause**: Invalid or expired AWS credentials.

**Solution**:
1. Verify AWS credentials are configured correctly
2. Test credentials: `aws sts get-caller-identity`
3. If failed, reconfigure: `aws configure`
4. Generate new access keys from AWS Console if needed
5. See `AWS_CREDENTIALS_SETUP.md` for detailed instructions

### Issue: "No AMIs found matching criteria"

**Cause**: Searching in wrong region or incorrect filters.

**Solution**:
1. Verify you're searching in the correct AWS region
2. Use AWS Console method (Method 1) for manual verification
3. Check Fortinet's official documentation for AMI IDs
4. Ensure you're searching public images, not just owned images

### Issue: "AMI not available in my region"

**Cause**: FortiGate AMIs may not be published in all regions.

**Solution**:
1. Check AWS Marketplace for region availability
2. Consider using a different region
3. Contact Fortinet support for region-specific AMI availability
4. Copy AMI from another region (advanced, requires permissions)

## Using AMI ID in Deployment Script

When running the deployment script:

```bash
python deploy.py
```

**If auto-discovery works**:
- Script will find the latest AMI automatically
- You can accept the suggested AMI or choose a different version

**If auto-discovery fails** (credential issues):
- Answer "n" when asked "Auto-discover FortiGate AMI?"
- Manually enter the AMI ID when prompted
- Format: `ami-0123456789abcdef0`

**Example**:
```
Auto-discover FortiGate AMI? [Y/n]: n
FortiGate AMI ID: ami-0a1b2c3d4e5f67890
```

## Cost Estimation

### On-Demand Pricing Example (us-east-1)

| Instance Type | FortiGate License | EC2 Compute | Total/Hour | Total/Month |
|---------------|-------------------|-------------|------------|-------------|
| c5.xlarge | $0.40 | $0.17 | $0.57 | ~$416 |
| c5.2xlarge | $0.80 | $0.34 | $1.14 | ~$832 |
| c5.4xlarge | $1.60 | $0.68 | $2.28 | ~$1,664 |

### BYOL Pricing Example (us-east-1)

| Instance Type | FortiGate License | EC2 Compute | Total/Hour | Total/Month |
|---------------|-------------------|-------------|------------|-------------|
| c5.xlarge | $0.00* | $0.17 | $0.17 | ~$124 |
| c5.2xlarge | $0.00* | $0.34 | $0.34 | ~$248 |
| c5.4xlarge | $0.00* | $0.68 | $0.68 | ~$496 |

*Requires separate license purchase from Fortinet

## Additional Resources

- **Fortinet AWS Documentation**: https://docs.fortinet.com/document/fortigate-public-cloud/latest/aws-administration-guide
- **AWS Marketplace**: https://aws.amazon.com/marketplace/seller-profile?id=8f26c7e6-3e2f-4c4e-8e0e-e6c8e5e5e5e5
- **FortiGate VM Licensing Guide**: https://docs.fortinet.com/document/fortigate/latest/vm-license-guide
- **AWS EC2 Pricing**: https://aws.amazon.com/ec2/pricing/on-demand/
- **Fortinet Support**: https://support.fortinet.com

## Quick Reference: Finding AMI ID

**Fastest Method for Manual Discovery**:

1. Open AWS Console → EC2 → AMIs
2. Change to "Public images"
3. Search: `FortiGate-VM64-AWS-7.4-OnDemand`
4. Sort by "Creation date" (newest first)
5. Copy AMI ID from the top result
6. Use in deployment script

**Example AMI IDs by Region** (as of documentation date):

| Region | FortiOS 7.4 OnDemand | FortiOS 7.2 OnDemand |
|--------|---------------------|---------------------|
| us-east-1 | ami-0xxxxxxxxxxxxx | ami-0xxxxxxxxxxxxx |
| us-west-2 | ami-0xxxxxxxxxxxxx | ami-0xxxxxxxxxxxxx |
| eu-west-1 | ami-0xxxxxxxxxxxxx | ami-0xxxxxxxxxxxxx |

⚠️ **Note**: AMI IDs change with each FortiOS release. Always verify the current AMI ID in your region using one of the methods above.
