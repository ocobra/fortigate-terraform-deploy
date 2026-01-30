# FortiGate AMI and Licensing Guide

## Overview

This guide covers how to obtain FortiGate AMI images and handle licensing for your AWS deployment.

## FortiGate AMI Options

### 1. AWS Marketplace AMIs

FortiGate AMIs are available through AWS Marketplace with different licensing models:

#### **BYOL (Bring Your Own License)**
- **AMI Name Pattern**: `FortiGate-VM64-AWS-*-BYOL-*`
- **Cost**: No hourly charges, only EC2 instance costs
- **License Required**: Yes, you must provide your own FortiGate license
- **Best For**: Existing FortiGate customers with licenses

#### **On-Demand (PAYG - Pay As You Go)**
- **AMI Name Pattern**: `FortiGate-VM64-AWS-*-OnDemand-*`
- **Cost**: Hourly licensing fees + EC2 instance costs
- **License Required**: No, included in hourly fee
- **Best For**: Testing, proof-of-concept, or short-term deployments

#### **Reserved Instance**
- **AMI Name Pattern**: `FortiGate-VM64-AWS-*-Reserved-*`
- **Cost**: Upfront payment + reduced hourly rates
- **License Required**: No, included in reserved pricing
- **Best For**: Long-term production deployments

### 2. AMI Discovery Methods

#### **Method 1: AWS Console**
1. Go to EC2 → Launch Instance
2. Search for "FortiGate" in AWS Marketplace
3. Filter by version (e.g., 7.4, 7.6)
4. Note the AMI ID for your region

#### **Method 2: AWS CLI**
```bash
# Find latest FortiGate 7.4 BYOL AMI
aws ec2 describe-images \
  --owners 679593333241 \
  --filters "Name=name,Values=FortiGate-VM64-AWS-7.4*-BYOL-*" \
  --query 'Images[*].[ImageId,Name,CreationDate]' \
  --output table \
  --region us-east-1

# Find latest FortiGate 7.4 OnDemand AMI
aws ec2 describe-images \
  --owners 679593333241 \
  --filters "Name=name,Values=FortiGate-VM64-AWS-7.4*-OnDemand-*" \
  --query 'Images[*].[ImageId,Name,CreationDate]' \
  --output table \
  --region us-east-1
```

#### **Method 3: Automated Discovery (Enhanced Script)**
The deployment script now includes automatic AMI discovery:

```bash
# Let the script find the latest AMI for you
python deploy.py --auto-discover-ami
```

## Licensing Options

### Option 1: BYOL (Bring Your Own License)

**Requirements:**
- Valid FortiGate VM license file (.lic)
- License must support the number of VMs you're deploying
- License must be appropriate for your instance size

**Implementation:**
1. Store license files in AWS Secrets Manager or S3
2. Configure the deployment to retrieve and apply licenses
3. License files are applied during initial configuration

**License File Storage:**
```bash
# Store license in AWS Secrets Manager
aws secretsmanager create-secret \
  --name "fortigate/primary/license" \
  --description "FortiGate Primary License" \
  --secret-string file://fortigate-primary.lic

aws secretsmanager create-secret \
  --name "fortigate/backup/license" \
  --description "FortiGate Backup License" \
  --secret-string file://fortigate-backup.lic
```

### Option 2: On-Demand/PAYG

**Requirements:**
- AWS Marketplace subscription
- Accept FortiGate terms and conditions
- No license files needed

**Implementation:**
- Use OnDemand AMI
- Licensing is automatic
- Costs are billed hourly through AWS

### Option 3: Reserved Instance

**Requirements:**
- AWS Marketplace reserved instance purchase
- Upfront payment commitment
- No license files needed

**Implementation:**
- Purchase reserved capacity
- Use Reserved AMI
- Lower hourly costs

## Enhanced Deployment Configuration

### Updated Configuration Options

```yaml
# Enhanced config with AMI and licensing options
fortigate:
  # AMI Configuration
  ami_discovery:
    enabled: true
    version: "7.4"  # FortiGate version
    license_type: "BYOL"  # BYOL, OnDemand, or Reserved
    architecture: "x86_64"
  
  # Manual AMI specification (overrides discovery)
  ami_id: ""  # Leave empty for auto-discovery
  
  # Instance Configuration
  instance_type: c5.xlarge
  key_pair_name: my-keypair
  
  # Licensing (for BYOL only)
  licensing:
    type: "BYOL"  # BYOL, OnDemand, Reserved
    primary_license_secret: "fortigate/primary/license"    # AWS Secrets Manager
    backup_license_secret: "fortigate/backup/license"      # AWS Secrets Manager
    # Alternative: S3 bucket storage
    license_s3_bucket: ""
    primary_license_s3_key: ""
    backup_license_s3_key: ""
  
  # Authentication
  admin_password: "MySecurePassword123!"
  ha_password: "MyHAPassword123!"
  hostname_primary: fortigate-primary
  hostname_backup: fortigate-backup
```

## Cost Considerations

### BYOL Pricing (Approximate)
- **EC2 Instance**: $0.192/hour (c5.xlarge)
- **FortiGate License**: $0 (you own the license)
- **Total**: ~$0.192/hour per instance

### OnDemand Pricing (Approximate)
- **EC2 Instance**: $0.192/hour (c5.xlarge)
- **FortiGate License**: $0.50-1.00/hour (varies by instance size)
- **Total**: ~$0.69-1.19/hour per instance

### Reserved Instance Pricing
- **Upfront Cost**: $3,000-5,000 (1-year term)
- **Hourly Rate**: $0.30-0.50/hour (reduced rate)
- **Best for**: Long-term deployments (>6 months)

## Implementation Steps

### Step 1: Choose Licensing Model

**For BYOL:**
1. Obtain FortiGate VM licenses from Fortinet
2. Store license files securely (Secrets Manager recommended)
3. Use BYOL AMI in deployment

**For OnDemand:**
1. Subscribe to FortiGate in AWS Marketplace
2. Accept terms and conditions
3. Use OnDemand AMI in deployment

### Step 2: AMI Selection

**Automated (Recommended):**
```bash
# Script will find latest AMI automatically
python deploy.py --auto-discover-ami --license-type BYOL
```

**Manual:**
```bash
# Find AMI ID manually and specify in config
aws ec2 describe-images --owners 679593333241 --filters "Name=name,Values=FortiGate-VM64-AWS-7.4*-BYOL-*"
```

### Step 3: License Management (BYOL Only)

**Store licenses in AWS Secrets Manager:**
```bash
# Create secrets for license files
aws secretsmanager create-secret \
  --name "fortigate/primary/license" \
  --secret-string file://primary.lic

aws secretsmanager create-secret \
  --name "fortigate/backup/license" \
  --secret-string file://backup.lic
```

**IAM Permissions for License Access:**
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "secretsmanager:GetSecretValue"
            ],
            "Resource": [
                "arn:aws:secretsmanager:*:*:secret:fortigate/*"
            ]
        }
    ]
}
```

## Regional AMI IDs (Examples)

### FortiGate 7.4 BYOL
| Region | AMI ID | Name |
|--------|--------|------|
| us-east-1 | ami-0123456789abcdef0 | FortiGate-VM64-AWS-7.4.1-BYOL-20231201 |
| us-west-2 | ami-0987654321fedcba0 | FortiGate-VM64-AWS-7.4.1-BYOL-20231201 |
| eu-west-1 | ami-0abcdef123456789a | FortiGate-VM64-AWS-7.4.1-BYOL-20231201 |

### FortiGate 7.4 OnDemand
| Region | AMI ID | Name |
|--------|--------|------|
| us-east-1 | ami-0234567890bcdef01 | FortiGate-VM64-AWS-7.4.1-OnDemand-20231201 |
| us-west-2 | ami-0876543210edcba09 | FortiGate-VM64-AWS-7.4.1-OnDemand-20231201 |
| eu-west-1 | ami-0bcdef234567890ab | FortiGate-VM64-AWS-7.4.1-OnDemand-20231201 |

*Note: These are example AMI IDs. Use the discovery methods above to find current AMI IDs.*

## Best Practices

### 1. License Management
- **Store licenses securely** in AWS Secrets Manager
- **Use IAM roles** instead of access keys for license retrieval
- **Rotate secrets regularly** for security
- **Monitor license usage** to avoid compliance issues

### 2. AMI Management
- **Use latest AMIs** for security updates
- **Test new AMIs** in non-production first
- **Document AMI versions** used in each environment
- **Automate AMI discovery** to stay current

### 3. Cost Optimization
- **Use BYOL for long-term** deployments if you have licenses
- **Consider Reserved Instances** for predictable workloads
- **Monitor costs** with AWS Cost Explorer
- **Right-size instances** based on actual usage

### 4. Security
- **Enable encryption** for license storage
- **Use least-privilege IAM** policies
- **Audit license access** regularly
- **Keep FortiGate updated** with latest patches

## Troubleshooting

### Common Issues

**AMI Not Found:**
```
Error: AMI ami-12345678 not found
```
- Verify AMI ID is correct for your region
- Check if you have access to the AMI
- Ensure AMI is still available (not deprecated)

**License Application Failed:**
```
Error: Failed to apply license file
```
- Verify license file format is correct
- Check license is valid and not expired
- Ensure license supports your instance type
- Verify IAM permissions for Secrets Manager

**Marketplace Subscription Required:**
```
Error: You must accept the terms and subscribe
```
- Go to AWS Marketplace
- Find FortiGate product
- Accept terms and conditions
- Subscribe to the product

## Support Resources

- **Fortinet Documentation**: [docs.fortinet.com](https://docs.fortinet.com)
- **AWS Marketplace**: Search for "FortiGate"
- **Fortinet Support**: For licensing questions
- **AWS Support**: For AMI and deployment issues