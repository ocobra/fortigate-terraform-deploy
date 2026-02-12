# ENI Creation for FortiGate HA Deployment

## Quick Links
- [Quick Start Guide](./QUICK-START-ENI.md) - Get started in 5 minutes
- [Complete Documentation](./ENI-CREATION-README.md) - Full reference guide
- [Workflow Diagram](./ENI-WORKFLOW.md) - Visual workflow explanation

## What This Does

Creates 8 Network Interfaces (ENIs) for FortiGate HA deployment:
- 4 ENIs for Primary FortiGate (outside, inside, HA, management)
- 4 ENIs for Backup FortiGate (outside, inside, HA, management)

Each ENI is configured with:
- Static private IP address (10th IP in subnet)
- Appropriate security groups
- Source/destination check disabled
- Resource tags

## Prerequisites

```bash
# Install Python dependencies
pip install boto3

# Configure AWS credentials (choose one method)
aws configure                    # Default credentials
aws configure --profile myprofile  # Named profile
```

## Usage

### Interactive Mode (Recommended)
```bash
python3 create-enis.py --profile myprofile --region us-east-1 --account 678632990402
```

The script will prompt you for each subnet ID.

### With Configuration File
```bash
python3 create-enis.py --profile myprofile --region us-east-1 --account 678632990402 --subnet-file subnet-config.json
```

## Example Subnet Configuration File

See `subnet-config.example.json`:
```json
{
  "primary": {
    "outside": "subnet-xxxxxxxxx",
    "inside": "subnet-xxxxxxxxx",
    "ha": "subnet-xxxxxxxxx",
    "mgmt": "subnet-xxxxxxxxx"
  },
  "backup": {
    "outside": "subnet-xxxxxxxxx",
    "inside": "subnet-xxxxxxxxx",
    "ha": "subnet-xxxxxxxxx",
    "mgmt": "subnet-xxxxxxxxx"
  }
}
```

## Output

The script generates:
1. **Console output** - ENI IDs and IP addresses
2. **eni-ids.json** - Detailed ENI information
3. **Terraform variables** - Ready to paste into terraform.tfvars

Example output:
```
Primary FortiGate ENIs:
  OUTSIDE    - eni-0123456789abcdef0 - 10.0.1.10
  INSIDE     - eni-0123456789abcdef1 - 10.0.2.10
  HA         - eni-0123456789abcdef2 - 10.0.3.10
  MGMT       - eni-0123456789abcdef3 - 10.0.4.10

Backup FortiGate ENIs:
  OUTSIDE    - eni-0123456789abcdef4 - 10.0.5.10
  INSIDE     - eni-0123456789abcdef5 - 10.0.6.10
  HA         - eni-0123456789abcdef6 - 10.0.7.10
  MGMT       - eni-0123456789abcdef7 - 10.0.8.10
```

## Next Steps

1. Copy the ENI IDs from the output
2. Add them to `terraform/terraform.tfvars`
3. Run Terraform deployment:
   ```bash
   cd terraform
   terraform init
   terraform plan
   terraform apply
   ```

## Troubleshooting

### "Unable to locate credentials"
```bash
# Configure AWS credentials
aws configure

# Or use a profile
python3 create-enis.py --profile myprofile --region us-east-1 --account 678632990402
```

### "Invalid subnet ID format"
Subnet IDs must be in format: `subnet-xxxxxxxxx` (where x is a-f or 0-9)

### "Access Denied"
Verify your IAM user/role has these permissions:
- ec2:DescribeSubnets
- ec2:CreateNetworkInterface
- ec2:CreateSecurityGroup
- ec2:ModifyNetworkInterfaceAttribute
- ec2:CreateTags

## Files in This Directory

| File | Description |
|------|-------------|
| `create-enis.py` | Main script to create ENIs |
| `subnet-config.example.json` | Example subnet configuration |
| `QUICK-START-ENI.md` | Quick start guide |
| `ENI-CREATION-README.md` | Complete documentation |
| `ENI-WORKFLOW.md` | Visual workflow diagram |
| `README-ENI-CREATION.md` | This file |

## Support

For issues or questions:
1. Check the [Complete Documentation](./ENI-CREATION-README.md)
2. Review the [Workflow Diagram](./ENI-WORKFLOW.md)
3. Verify AWS credentials and permissions
4. Check subnet IDs are correct and in the right region
