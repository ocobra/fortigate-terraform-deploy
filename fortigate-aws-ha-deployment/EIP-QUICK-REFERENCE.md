# Elastic IP Support - Quick Reference Guide

## What Changed?

The FortiGate HA deployment system now supports Elastic IPs (EIPs) for the outside interfaces, enabling internet routing through the Internet Gateway.

## Quick Start

### Option 1: Create ENIs with EIPs (Recommended)

```bash
# Create ENIs with EIPs
python3 create-enis.py --profile renaws --region us-east-1 --account 678632990402 --allocate-eips

# Deploy using the EIP allocation IDs from above
python3 deploy.py
# When prompted:
# - "Allocate Elastic IPs for outside interfaces?" → yes
# - "Use existing EIP allocation IDs?" → yes
# - Provide the EIP allocation IDs from create-enis.py output
```

### Option 2: Let Terraform Create EIPs

```bash
# Create ENIs without EIPs
python3 create-enis.py --profile renaws --region us-east-1 --account 678632990402

# Deploy and let Terraform create EIPs
python3 deploy.py
# When prompted:
# - "Allocate Elastic IPs for outside interfaces?" → yes
# - "Use existing EIP allocation IDs?" → no
```

### Option 3: No EIPs

```bash
# Create ENIs
python3 create-enis.py --profile renaws --region us-east-1 --account 678632990402

# Deploy without EIPs
python3 deploy.py
# When prompted:
# - "Allocate Elastic IPs for outside interfaces?" → no
```

## New Interactive Prompts

When running `deploy.py`, you'll see these new prompts:

```
Elastic IP Configuration (for internet routing):
Allocate Elastic IPs for outside interfaces? [y/N]: y
Use existing EIP allocation IDs? [y/N]: y
Primary outside EIP allocation ID (or leave empty to create new): eipalloc-xxxxx
Backup outside EIP allocation ID (or leave empty to create new): eipalloc-xxxxx
```

## Terraform Variables Added

The following variables are now included in `terraform.tfvars`:

```hcl
# Elastic IP Configuration (for internet routing)
allocate_eips = true
primary_outside_eip_id = "eipalloc-xxxxx"
backup_outside_eip_id = "eipalloc-xxxxx"
```

## Command Line Examples

### create-enis.py with EIPs

```bash
# Interactive mode with EIPs
python3 create-enis.py --profile renaws --region us-east-1 --account 678632990402 --allocate-eips

# With subnet config file and EIPs
python3 create-enis.py --profile renaws --region us-east-1 --account 678632990402 \
  --subnet-file subnet-config.json --allocate-eips
```

### deploy.py Examples

```bash
# Interactive mode
python3 deploy.py

# With configuration file
python3 deploy.py --config deployment-config.json

# Plan only (no deployment)
python3 deploy.py --plan-only

# Skip AWS validation
python3 deploy.py --skip-validation

# Destroy deployment
python3 deploy.py --destroy
```

## Configuration File Format

When using configuration files, include EIP settings:

```json
{
  "aws": {
    "region": "us-east-1",
    "profile": "renaws"
  },
  "network": {
    "vpc_id": "vpc-xxxxx",
    "allocate_eips": true,
    "primary_outside_eip_id": "eipalloc-xxxxx",
    "backup_outside_eip_id": "eipalloc-xxxxx",
    "outside_subnet_primary": "subnet-xxxxx",
    "inside_subnet_primary": "subnet-xxxxx",
    ...
  },
  ...
}
```

## Validation

The deployment script validates:

1. **EIP Allocation IDs**: Verifies they exist in AWS
2. **EIP Associations**: Warns if already associated with other resources
3. **Permissions**: Checks you have permission to describe addresses

## Expected Output

### create-enis.py with --allocate-eips

```
✅ Created ENI: eni-xxxxx (FortiGate Primary OUTSIDE interface) - IP: 10.0.1.10
🌐 Allocating Elastic IP for Primary OUTSIDE interface...
✅ Allocated and associated EIP: 54.123.45.67 (eipalloc-xxxxx)

...

📝 Terraform Variables (add to terraform.tfvars):
primary_outside_eni_id = "eni-xxxxx"
...

# Elastic IP Configuration
allocate_eips = true
primary_outside_eip_id = "eipalloc-xxxxx"
backup_outside_eip_id = "eipalloc-xxxxx"
```

### deploy.py Validation

```
🔍 Validating deployment configuration...
✅ All 8 ENIs validated successfully
✅ All 2 EIP allocations validated successfully
⚠️  Warning: EIP eipalloc-xxxxx is already associated with eni-xxxxx
   Public IP: 54.123.45.67
✅ All configuration parameters validated successfully
```

## Troubleshooting

### Issue: "EIP allocation not found"

**Cause**: Invalid or incorrect EIP allocation ID

**Solution**: 
- Verify the EIP allocation ID exists: `aws ec2 describe-addresses --allocation-ids eipalloc-xxxxx`
- Check you're in the correct region
- Ensure you have permission to describe addresses

### Issue: "EIP already associated"

**Cause**: EIP is already associated with another ENI

**Solution**: 
- This is a warning, not an error
- If intentional (re-deploying), proceed
- If unintentional, check which resource is using the EIP
- Disassociate the EIP first if needed

### Issue: "Cannot auto-discover AMI with --skip-validation"

**Cause**: AMI discovery requires AWS API access

**Solution**: 
- Remove `--skip-validation` flag, OR
- Provide AMI ID manually when prompted

## Verification Commands

### Check EIP Association

```bash
# Check primary outside ENI
aws ec2 describe-network-interfaces \
  --network-interface-ids eni-xxxxx \
  --profile renaws \
  --region us-east-1 \
  --query 'NetworkInterfaces[0].Association.PublicIp'

# List all EIPs with FortiGate tags
aws ec2 describe-addresses \
  --filters "Name=tag:Project,Values=FortiGate-HA-Deployment" \
  --profile renaws \
  --region us-east-1 \
  --query 'Addresses[*].[AllocationId,PublicIp,Tags[?Key==`Name`].Value|[0]]' \
  --output table
```

### Check Terraform State

```bash
cd terraform

# Show EIP resources
terraform state list | grep eip

# Show EIP details
terraform state show 'module.fortigate_ha.aws_eip_association.primary_outside[0]'
```

## Important Notes

1. **EIP Lifecycle**:
   - EIPs created by `create-enis.py` are NOT destroyed by Terraform
   - EIPs created by Terraform ARE destroyed by Terraform
   - Always verify EIP associations after deployment

2. **Cost Considerations**:
   - EIPs are free when associated with running instances
   - Unassociated EIPs incur hourly charges
   - Clean up unused EIPs to avoid charges

3. **Internet Routing**:
   - EIPs enable FortiGate to route traffic to Internet Gateway
   - Configure FortiGate policies to allow internet traffic
   - Update route tables to route through FortiGate

4. **Security**:
   - Document public IP addresses for firewall rules
   - Update security groups to allow required traffic
   - Monitor internet-facing interfaces

## Next Steps After Deployment

1. Verify EIP associations:
   ```bash
   aws ec2 describe-network-interfaces --network-interface-ids <eni-id>
   ```

2. Test internet connectivity through FortiGate

3. Configure FortiGate policies for internet traffic

4. Update route tables to route through FortiGate

5. Document public IP addresses for:
   - Firewall rules
   - Allowlists
   - DNS records
   - Monitoring systems

## Support

For issues or questions:
1. Check the EIP-TESTING-CHECKLIST.md for detailed test scenarios
2. Review EIP-SUPPORT-SUMMARY.md for implementation details
3. Verify Terraform plan output before applying
4. Check AWS CloudWatch logs for deployment issues

## Files Modified

All changes are complete in:
- ✅ `terraform/` - Terraform modules and configurations
- ✅ `create-enis.py` - ENI creation script
- ✅ `deploy.py` - Deployment orchestration script

Ready to deploy!
