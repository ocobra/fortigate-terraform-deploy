# ENI Creation Script

This script creates 8 Network Interfaces (ENIs) for FortiGate HA deployment with static IP addresses.

## Prerequisites

1. **Python 3** installed
2. **Boto3** library installed:
   ```bash
   pip install boto3
   ```
3. **AWS Credentials** configured (one of the following):
   - AWS CLI configured: `aws configure`
   - AWS profile in `~/.aws/credentials`
   - Environment variables: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`

## Required IAM Permissions

Your AWS credentials need the following permissions:
- `ec2:DescribeSubnets`
- `ec2:DescribeSecurityGroups`
- `ec2:CreateSecurityGroup`
- `ec2:AuthorizeSecurityGroupIngress`
- `ec2:CreateNetworkInterface`
- `ec2:ModifyNetworkInterfaceAttribute`
- `ec2:CreateTags`
- `sts:GetCallerIdentity`

## Usage

### Interactive Mode (Recommended for First-Time Users)
The script will prompt you for all subnet IDs:
```bash
python3 create-enis.py --profile <profile-name> --region us-east-1 --account 678632990402
```

You'll be prompted to enter each subnet ID:
```
📋 Subnet Configuration
======================================================================
Please provide the subnet IDs for each FortiGate interface.
Subnet IDs should be in the format: subnet-xxxxxxxxx

🔵 Primary FortiGate Subnets:
----------------------------------------------------------------------
  Outside    subnet ID: subnet-008c04ea3c16cfc44
  Inside     subnet ID: subnet-0dd89264e19b79c71
  Ha         subnet ID: subnet-0e27fec5fef60e89c
  Mgmt       subnet ID: subnet-0b9fb7667ffd28db8

🟢 Backup FortiGate Subnets:
----------------------------------------------------------------------
  Outside    subnet ID: subnet-011055542bb0745aa
  Inside     subnet ID: subnet-0c5d1b3f9c73030a5
  Ha         subnet ID: subnet-0d3db8dca9a438fea
  Mgmt       subnet ID: subnet-0dd259113cb275883
```

### Using a Configuration File
If you have a subnet configuration file:
```bash
python3 create-enis.py --profile <profile-name> --region us-east-1 --account 678632990402 --subnet-file subnet-config.json
```

### Using Default Credentials
```bash
python3 create-enis.py --region us-east-1 --account 678632990402
```

## Subnet Configuration File Format

Create a JSON file with your subnet IDs:
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

See `subnet-config.example.json` for a complete example.

## Command Line Arguments

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `--profile` | No | None | AWS CLI profile name from ~/.aws/credentials |
| `--region` | No | us-east-1 | AWS region where ENIs will be created |
| `--account` | Yes | - | AWS account ID (for verification) |
| `--subnet-file` | No | None | JSON file with subnet IDs (will prompt if not provided) |

## What the Script Does

1. **Authenticates** with AWS using the specified profile or default credentials
2. **Verifies** the account ID matches your credentials
3. **Prompts for subnet IDs** (or loads from file if provided)
4. **Validates subnet ID format** (subnet-xxxxxxxxx)
5. **Optionally saves** subnet configuration for reuse
6. **Gets subnet information** for all 8 subnets
7. **Creates or uses existing security groups**:
   - `fortigate-mgmt-sg` - For management interfaces
   - `fortigate-data-sg` - For data plane interfaces (outside/inside)
   - `fortigate-ha-sg` - For HA synchronization
8. **Creates 8 ENIs** with static IP addresses:
   - Primary FortiGate: outside, inside, HA, management
   - Backup FortiGate: outside, inside, HA, management
9. **Configures ENIs**:
   - Assigns static private IP (10th IP in each subnet)
   - Disables source/destination check
   - Applies appropriate security groups
   - Adds resource tags
10. **Outputs**:
   - Displays all ENI IDs and IP addresses
   - Saves details to `eni-ids.json`
   - Generates Terraform variable snippet

## Output Files

### eni-ids.json
Contains detailed information about all created ENIs:
```json
{
  "primary_outside": {
    "eni_id": "eni-xxxxx",
    "private_ip": "10.0.1.10",
    "subnet_id": "subnet-xxxxx",
    "az": "us-east-1a"
  },
  ...
}
```

## Example Output

```
🚀 Creating Network Interfaces for FortiGate HA Deployment
======================================================================
Region: us-east-1
Account: 678632990402
Profile: myprofile

✅ Using AWS profile: myprofile
✅ Authenticated as: arn:aws:iam::678632990402:user/myuser
✅ Account ID: 678632990402

VPC ID: vpc-xxxxx

🔒 Setting up security groups...
✅ Created security group: fortigate-mgmt-sg (sg-xxxxx)
✅ Created security group: fortigate-data-sg (sg-xxxxx)
✅ Created security group: fortigate-ha-sg (sg-xxxxx)

🔧 Creating ENIs for Primary FortiGate...
✅ Created ENI: eni-xxxxx (FortiGate Primary OUTSIDE interface) - IP: 10.0.1.10
✅ Created ENI: eni-xxxxx (FortiGate Primary INSIDE interface) - IP: 10.0.2.10
✅ Created ENI: eni-xxxxx (FortiGate Primary HA interface) - IP: 10.0.3.10
✅ Created ENI: eni-xxxxx (FortiGate Primary MGMT interface) - IP: 10.0.4.10

🔧 Creating ENIs for Backup FortiGate...
✅ Created ENI: eni-xxxxx (FortiGate Backup OUTSIDE interface) - IP: 10.0.5.10
✅ Created ENI: eni-xxxxx (FortiGate Backup INSIDE interface) - IP: 10.0.6.10
✅ Created ENI: eni-xxxxx (FortiGate Backup HA interface) - IP: 10.0.7.10
✅ Created ENI: eni-xxxxx (FortiGate Backup MGMT interface) - IP: 10.0.8.10

======================================================================
✅ All ENIs created successfully!

📋 ENI Summary:
----------------------------------------------------------------------

Primary FortiGate ENIs:
  OUTSIDE    - eni-xxxxx - 10.0.1.10
  INSIDE     - eni-xxxxx - 10.0.2.10
  HA         - eni-xxxxx - 10.0.3.10
  MGMT       - eni-xxxxx - 10.0.4.10

Backup FortiGate ENIs:
  OUTSIDE    - eni-xxxxx - 10.0.5.10
  INSIDE     - eni-xxxxx - 10.0.6.10
  HA         - eni-xxxxx - 10.0.7.10
  MGMT       - eni-xxxxx - 10.0.8.10

----------------------------------------------------------------------
💾 ENI details saved to: eni-ids.json

📝 Terraform Variables (add to terraform.tfvars):
----------------------------------------------------------------------
primary_outside_eni_id = "eni-xxxxx"
primary_inside_eni_id  = "eni-xxxxx"
primary_ha_eni_id      = "eni-xxxxx"
primary_mgmt_eni_id    = "eni-xxxxx"

backup_outside_eni_id  = "eni-xxxxx"
backup_inside_eni_id   = "eni-xxxxx"
backup_ha_eni_id       = "eni-xxxxx"
backup_mgmt_eni_id     = "eni-xxxxx"
```

## Troubleshooting

### Error: Unable to locate credentials
**Solution**: Configure AWS credentials using one of these methods:
```bash
# Option 1: Configure default credentials
aws configure

# Option 2: Use a specific profile
python3 create-enis.py --profile myprofile --region us-east-1 --account 678632990402

# Option 3: Set environment variables
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
python3 create-enis.py --region us-east-1 --account 678632990402
```

### Error: Profile not found
**Solution**: Check available profiles:
```bash
cat ~/.aws/credentials
```

### Error: Access Denied
**Solution**: Verify your IAM user/role has the required EC2 permissions listed above.

### Error: Subnet not found
**Solution**: Verify:
1. Subnet IDs are correct in the script
2. Subnets exist in the specified region
3. You have permission to access the subnets

## Next Steps

After creating the ENIs:

1. **Copy the ENI IDs** from the output
2. **Add them to your terraform.tfvars** file
3. **Run the deployment**:
   ```bash
   cd terraform
   terraform init
   terraform plan
   terraform apply
   ```

## Cleanup

To delete the created ENIs (if needed):
```bash
aws ec2 delete-network-interface --network-interface-id eni-xxxxx
```

Or use the AWS Console:
1. Go to EC2 → Network Interfaces
2. Filter by tag: `Project = FortiGate-HA-Deployment`
3. Select and delete the ENIs
