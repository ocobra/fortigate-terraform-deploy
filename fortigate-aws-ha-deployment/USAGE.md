# FortiGate AWS HA Deployment - Usage Guide

## Quick Start

### 1. Interactive Deployment

```bash
# Run interactive deployment with AMI auto-discovery
python deploy.py

# This will prompt you for:
# - AWS credentials and region
# - AMI discovery options (auto-discover or manual)
# - Licensing configuration (BYOL, OnDemand, Reserved)
# - VPC and subnet IDs (pre-assigned)
# - FortiGate configuration
# - Transit Gateway settings
# - Monitoring preferences
```

### 2. Configuration File Deployment

```bash
# Copy and customize the example configuration
cp config-example.yaml my-deployment.yaml
# Edit my-deployment.yaml with your values

# Deploy using configuration file
python deploy.py --config my-deployment.yaml
```

### 3. AMI Discovery Options

```bash
# List available FortiGate versions
python deploy.py --list-versions

# Auto-discover specific AMI
python deploy.py --auto-discover-ami --license-type BYOL --fortigate-version 7.4

# Plan-only with auto-discovery
python deploy.py --plan-only --auto-discover-ami
```

### 4. License Setup (BYOL Only)

```bash
# Set up licenses in AWS Secrets Manager (recommended)
python setup-licensing.py secrets-manager \
  --primary-license ./fortigate-primary.lic \
  --backup-license ./fortigate-backup.lic

# Or set up licenses in S3
python setup-licensing.py s3 \
  --primary-license ./fortigate-primary.lic \
  --backup-license ./fortigate-backup.lic \
  --bucket my-fortigate-licenses \
  --create-bucket

# List available AMIs
python setup-licensing.py list-amis --region us-east-1
```

## Prerequisites

### AWS Permissions Required

Your AWS credentials need the following permissions:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "ec2:*",
                "logs:*",
                "iam:PassRole",
                "iam:CreateRole",
                "iam:AttachRolePolicy",
                "iam:CreateInstanceProfile",
                "iam:AddRoleToInstanceProfile",
                "secretsmanager:GetSecretValue",
                "s3:GetObject"
            ],
            "Resource": "*"
        }
    ]
}
```

### FortiGate Licensing Options

#### Option 1: BYOL (Bring Your Own License)
- **Requirements**: Valid FortiGate VM license files (.lic)
- **Cost**: Only EC2 instance costs (~$0.192/hour per c5.xlarge)
- **Setup**: Store licenses in AWS Secrets Manager or S3
- **Best For**: Existing FortiGate customers with licenses

#### Option 2: OnDemand (PAYG)
- **Requirements**: AWS Marketplace subscription
- **Cost**: EC2 + licensing fees (~$0.69-1.19/hour per instance)
- **Setup**: No license files needed
- **Best For**: Testing, proof-of-concept, short-term deployments

#### Option 3: Reserved Instance
- **Requirements**: AWS Marketplace reserved purchase
- **Cost**: Upfront payment + reduced hourly rates
- **Setup**: No license files needed
- **Best For**: Long-term production deployments

### Pre-assigned Resources

Before deployment, ensure you have:

1. **VPC ID** - Existing VPC where FortiGates will be deployed
2. **8 Subnet IDs** - Pre-assigned subnets across 2 AZs:
   - Primary AZ: outside, inside, ha, mgmt subnets
   - Backup AZ: outside, inside, ha, mgmt subnets
3. **Transit Gateway ID** (if using existing)
4. **EC2 Key Pair** - For SSH access to FortiGate instances
   - **📖 See [EC2_KEY_PAIR_SETUP.md](EC2_KEY_PAIR_SETUP.md) for detailed setup instructions**
   - Quick create: `aws ec2 create-key-pair --key-name fortigate-ha-keypair --query 'KeyMaterial' --output text > ~/.ssh/fortigate-ha-keypair.pem && chmod 400 ~/.ssh/fortigate-ha-keypair.pem`
5. **FortiGate Licenses** (for BYOL) - Stored in Secrets Manager or S3

## Deployment Process

### Step 1: License Setup (BYOL Only)

If using BYOL licensing, set up your licenses first:

```bash
# Option A: AWS Secrets Manager (Recommended)
python setup-licensing.py secrets-manager \
  --primary-license ./primary.lic \
  --backup-license ./backup.lic \
  --primary-secret "fortigate/primary/license" \
  --backup-secret "fortigate/backup/license"

# Option B: S3 Storage
python setup-licensing.py s3 \
  --primary-license ./primary.lic \
  --backup-license ./backup.lic \
  --bucket my-fortigate-licenses \
  --create-bucket
```

### Step 2: AMI Discovery

```bash
# List available FortiGate versions
python deploy.py --list-versions

# Output:
# Available FortiGate versions:
#   • 7.6
#   • 7.4
#   • 7.2
#   • 7.0

# Discover specific AMI
python deploy.py --auto-discover-ami --license-type BYOL --fortigate-version 7.4

# Output:
# 🔍 Searching for FortiGate 7.4 BYOL AMI...
# ✅ Found AMI: ami-0123456789abcdef0 - FortiGate-VM64-AWS-7.4.1-BYOL-20231201
```

### Step 3: Configuration

The script will prompt for or load from file:

```
🔧 AWS Configuration
- Region (e.g., us-east-1)
- AWS Profile or Access Keys

🛡️ FortiGate Configuration
AMI Configuration:
- Auto-discover FortiGate AMI? [Y/n]: y
- Available FortiGate versions: 7.6, 7.4, 7.2, 7.0
- FortiGate version [7.6]: 7.4
- License type (BYOL/OnDemand/Reserved) [BYOL]: BYOL

Licensing Configuration (BYOL):
- License source (secrets-manager/s3) [secrets-manager]: secrets-manager
- Primary FortiGate license secret name [fortigate/primary/license]: 
- Backup FortiGate license secret name [fortigate/backup/license]: 

Instance Configuration:
- Instance type [c5.xlarge]: 
- EC2 Key Pair name: my-keypair
- Admin password (min 8 chars): ********
- HA synchronization password (min 8 chars): ********

🌐 Network Configuration  
- VPC ID: vpc-12345678
- Availability Zones (2 required)
- 8 Subnet IDs (pre-assigned)
- Management access CIDRs

🌉 Transit Gateway Configuration
- Create new or use existing
- BGP ASN configuration
- Spoke VPC CIDRs

📊 Monitoring Configuration
- VPC Flow Logs
- Log retention
- Detailed monitoring
```

### Step 4: Validation

The script performs comprehensive validation:

```
🔍 Validating deployment configuration...
🔍 Auto-discovering FortiGate AMI...
🔍 Searching for FortiGate 7.4 BYOL AMI...
✅ Found AMI: ami-0123456789abcdef0 - FortiGate-VM64-AWS-7.4.1-BYOL-20231201
✅ Using discovered AMI: ami-0123456789abcdef0

🔐 Validating BYOL licensing configuration...
🔐 Retrieving license from Secrets Manager: fortigate/primary/license
✅ License retrieved successfully
✅ License format validation passed
🔐 Retrieving license from Secrets Manager: fortigate/backup/license
✅ License retrieved successfully
✅ License format validation passed
✅ BYOL licensing configuration validated

✅ VPC vpc-12345678 validated successfully
✅ All 8 subnets validated successfully  
✅ Transit Gateway tgw-12345678 validated successfully
✅ Key pair my-keypair validated successfully
✅ All configuration parameters validated successfully
```

### Step 5: Analysis (if available)

Integration with FortiGate Terraform Analysis System:

```
🔍 Running FortiGate Terraform Analysis validation...
✅ Analysis completed successfully
  • Security issues: 0
  • Best practice violations: 2
```

### Step 6: Plan Generation

```
📋 Generating Terraform deployment plan...
✅ Generated Terraform variables file
Running: terraform init
Running: terraform plan -var-file terraform.tfvars -out tfplan
```

### Step 7: Deployment Confirmation

```
Do you want to proceed with the deployment? [y/N]: y
🚀 Starting FortiGate HA deployment...
Running: terraform apply tfplan
```

## Advanced Usage

### AMI Management

```bash
# List all available AMIs in a region
python setup-licensing.py list-amis --region us-west-2

# Auto-discover latest AMI for specific criteria
python deploy.py --auto-discover-ami \
  --license-type OnDemand \
  --fortigate-version 7.6

# Use specific AMI in configuration file
fortigate:
  ami_id: "ami-0123456789abcdef0"  # Override auto-discovery
  ami_discovery:
    enabled: false
```

### License Management

```bash
# Generate IAM policy for license access
python setup-licensing.py iam-policy

# Set up licenses with custom secret names
python setup-licensing.py secrets-manager \
  --primary-license ./primary.lic \
  --backup-license ./backup.lic \
  --primary-secret "prod/fortigate/primary/license" \
  --backup-secret "prod/fortigate/backup/license"

# Use S3 with custom bucket and keys
python setup-licensing.py s3 \
  --primary-license ./primary.lic \
  --backup-license ./backup.lic \
  --bucket my-company-fortigate-licenses \
  --primary-key "prod/licenses/fortigate-primary.lic" \
  --backup-key "prod/licenses/fortigate-backup.lic"
```

### Configuration File Examples

#### BYOL with Secrets Manager
```yaml
fortigate:
  ami_discovery:
    enabled: true
    version: "7.4"
    license_type: "BYOL"
  licensing:
    type: "BYOL"
    primary_license_secret: "fortigate/primary/license"
    backup_license_secret: "fortigate/backup/license"
```

#### BYOL with S3
```yaml
fortigate:
  ami_discovery:
    enabled: true
    version: "7.4"
    license_type: "BYOL"
  licensing:
    type: "BYOL"
    license_s3_bucket: "my-fortigate-licenses"
    primary_license_s3_key: "licenses/fortigate-primary.lic"
    backup_license_s3_key: "licenses/fortigate-backup.lic"
```

#### OnDemand (No License Files)
```yaml
fortigate:
  ami_discovery:
    enabled: true
    version: "7.4"
    license_type: "OnDemand"
  licensing:
    type: "OnDemand"
```

## Cost Optimization

### Licensing Cost Comparison

| License Type | EC2 Cost/Hour | License Cost/Hour | Total/Hour | Best For |
|--------------|---------------|-------------------|------------|----------|
| BYOL | $0.192 | $0 | $0.192 | Long-term, existing licenses |
| OnDemand | $0.192 | $0.50-1.00 | $0.69-1.19 | Testing, short-term |
| Reserved | $0.192 | $0.30-0.50 | $0.49-0.69 | Long-term commitment |

*Costs are approximate for c5.xlarge instances in us-east-1*

### Recommendations

- **Use BYOL** if you have existing FortiGate licenses
- **Use OnDemand** for testing and proof-of-concept
- **Use Reserved** for long-term production (>6 months)
- **Right-size instances** based on throughput requirements

## Troubleshooting

### AMI Discovery Issues

```bash
# No AMIs found
❌ No FortiGate 7.4 BYOL AMIs found
```
**Solutions:**
- Check if you have access to AWS Marketplace
- Verify region has FortiGate AMIs available
- Try different license type (OnDemand vs BYOL)
- Subscribe to FortiGate in AWS Marketplace

### License Issues

```bash
# License format validation failed
❌ License validation failed: Missing -----BEGIN FGT VM LICENSE-----
```
**Solutions:**
- Verify license file format is correct
- Ensure license file is not corrupted
- Check license is for VM deployment (not hardware)

```bash
# License retrieval failed
❌ Error retrieving license from Secrets Manager: AccessDenied
```
**Solutions:**
- Verify IAM permissions for Secrets Manager
- Check secret name is correct
- Ensure secret exists in the correct region

### Marketplace Subscription

```bash
# Marketplace subscription required
❌ You must accept the terms and subscribe
```
**Solutions:**
1. Go to AWS Marketplace
2. Search for "FortiGate"
3. Select the appropriate product (BYOL/OnDemand)
4. Accept terms and conditions
5. Subscribe to the product

## Support Resources

- **FortiGate AMI Guide**: See `AMI_AND_LICENSING_GUIDE.md`
- **Fortinet Documentation**: [docs.fortinet.com](https://docs.fortinet.com)
- **AWS Marketplace**: Search for "FortiGate"
- **Licensing Setup**: Use `setup-licensing.py` helper script

## Post-Deployment

### Verification Steps

1. **Check FortiGate Status**
   ```bash
   # SSH to primary FortiGate
   ssh -i ~/.ssh/my-keypair.pem admin@<primary-mgmt-ip>
   
   # Check HA status
   get system ha status
   ```

2. **Verify BGP Sessions**
   ```bash
   # Check BGP neighbors
   get router info bgp summary
   
   # Check routes
   get router info routing-table all
   ```

3. **Test Traffic Flow**
   ```bash
   # From spoke VPC instance, test internet connectivity
   curl -I http://www.google.com
   
   # Check FortiGate logs
   execute log filter category traffic
   execute log display
   ```

### Management Access

- **Primary FortiGate**: `https://<primary-mgmt-ip>`
- **Backup FortiGate**: `https://<backup-mgmt-ip>`
- **Default credentials**: admin / <your-admin-password>

### Monitoring

- **CloudWatch Logs**: Check log groups for VPC Flow Logs and FortiGate logs
- **CloudWatch Dashboards**: Monitor FortiGate health and traffic metrics
- **VPC Flow Logs**: Analyze network traffic patterns

## Troubleshooting

### Common Issues

1. **Subnet Validation Fails**
   ```
   ❌ Error validating subnets: Subnet subnet-12345678 not found
   ```
   - Verify subnet IDs are correct
   - Ensure subnets exist in specified AZs
   - Check AWS region matches

2. **Transit Gateway Validation Fails**
   ```
   ❌ Transit Gateway tgw-12345678 is not available: pending
   ```
   - Wait for Transit Gateway to become available
   - Verify Transit Gateway ID is correct

3. **AMI Not Found**
   ```
   ❌ AMI ami-12345678 not found
   ```
   - Verify AMI ID is correct for your region
   - Ensure you have access to FortiGate AMI
   - Check if AMI is available in target region

4. **Terraform Apply Fails**
   ```
   ❌ Terraform command failed: Error creating instance
   ```
   - Check AWS service limits
   - Verify IAM permissions
   - Review Terraform error messages

### Rollback

If deployment fails or you need to rollback:

```bash
# Destroy all resources
python deploy.py --destroy --config my-deployment.yaml

# Confirm destruction when prompted
Are you sure you want to destroy all resources? [y/N]: y
```

### Logs and Debugging

- **Terraform logs**: Check terraform directory for detailed logs
- **AWS CloudTrail**: Review API calls for permission issues
- **FortiGate logs**: SSH to instances and check system logs

## Advanced Usage

### Custom Terraform Backend

Edit `terraform/main.tf` to configure remote state:

```hcl
terraform {
  backend "s3" {
    bucket         = "my-terraform-state-bucket"
    key            = "fortigate-ha/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "terraform-state-lock"
  }
}
```

### Multiple Environments

Use different configuration files:

```bash
# Production deployment
python deploy.py --config prod-config.yaml

# Staging deployment  
python deploy.py --config staging-config.yaml
```

### CI/CD Integration

```bash
# Non-interactive deployment for CI/CD
python deploy.py --config config.yaml --plan-only
# Review plan, then:
cd terraform && terraform apply tfplan
```

## Security Best Practices

1. **Use strong passwords** for admin and HA passwords
2. **Restrict management access** to specific CIDR blocks
3. **Enable VPC Flow Logs** for network monitoring
4. **Use IAM roles** instead of access keys when possible
5. **Encrypt Terraform state** with remote backend
6. **Regularly update** FortiGate AMI to latest version
7. **Monitor security logs** in CloudWatch

## Support

For issues or questions:

1. Check this usage guide
2. Review Terraform error messages
3. Check AWS CloudTrail for permission issues
4. Verify all pre-assigned resources exist
5. Test with plan-only mode first