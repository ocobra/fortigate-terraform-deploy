# ENI Creation Workflow

## Overview
This document explains the workflow for creating ENIs for FortiGate HA deployment.

## Workflow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│  1. Start Script                                            │
│     python3 create-enis.py --profile myprofile \            │
│       --region us-east-1 --account 678632990402             │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│  2. Authenticate with AWS                                   │
│     - Use specified profile or default credentials          │
│     - Verify account ID                                     │
│     - Check permissions                                     │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│  3. Get Subnet IDs                                          │
│     Option A: Interactive Prompt                            │
│       - Enter 8 subnet IDs manually                         │
│       - Validate format (subnet-xxxxxxxxx)                  │
│       - Confirm configuration                               │
│       - Optionally save to file                             │
│                                                             │
│     Option B: Load from File                                │
│       - Use --subnet-file parameter                         │
│       - Load JSON configuration                             │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│  4. Validate Subnets                                        │
│     - Query AWS for subnet details                          │
│     - Get VPC ID, CIDR blocks, AZs                          │
│     - Verify subnets exist and are accessible               │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│  5. Setup Security Groups                                   │
│     - Check if security groups exist                        │
│     - Create if needed:                                     │
│       • fortigate-mgmt-sg (HTTPS, SSH)                      │
│       • fortigate-data-sg (All traffic)                     │
│       • fortigate-ha-sg (All traffic, self-referencing)     │
│     - Tag security groups                                   │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│  6. Create ENIs (8 total)                                   │
│                                                             │
│     Primary FortiGate (4 ENIs):                             │
│     ┌─────────────────────────────────────────────┐        │
│     │ Outside ENI  → subnet-xxx → 10.x.x.10       │        │
│     │ Inside ENI   → subnet-xxx → 10.x.x.10       │        │
│     │ HA ENI       → subnet-xxx → 10.x.x.10       │        │
│     │ Mgmt ENI     → subnet-xxx → 10.x.x.10       │        │
│     └─────────────────────────────────────────────┘        │
│                                                             │
│     Backup FortiGate (4 ENIs):                              │
│     ┌─────────────────────────────────────────────┐        │
│     │ Outside ENI  → subnet-xxx → 10.x.x.10       │        │
│     │ Inside ENI   → subnet-xxx → 10.x.x.10       │        │
│     │ HA ENI       → subnet-xxx → 10.x.x.10       │        │
│     │ Mgmt ENI     → subnet-xxx → 10.x.x.10       │        │
│     └─────────────────────────────────────────────┘        │
│                                                             │
│     For each ENI:                                           │
│     - Assign static IP (10th IP in subnet)                  │
│     - Attach security group(s)                              │
│     - Disable source/dest check                             │
│     - Add tags                                              │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│  7. Output Results                                          │
│     - Display ENI IDs and IPs                               │
│     - Save to eni-ids.json                                  │
│     - Generate Terraform variables snippet                  │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│  8. Next Steps                                              │
│     - Copy ENI IDs to terraform.tfvars                      │
│     - Run terraform init/plan/apply                         │
└─────────────────────────────────────────────────────────────┘
```

## Interactive Prompt Example

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

📋 Subnet Summary:
----------------------------------------------------------------------

Primary FortiGate:
  Outside    - subnet-008c04ea3c16cfc44
  Inside     - subnet-0dd89264e19b79c71
  Ha         - subnet-0e27fec5fef60e89c
  Mgmt       - subnet-0b9fb7667ffd28db8

Backup FortiGate:
  Outside    - subnet-011055542bb0745aa
  Inside     - subnet-0c5d1b3f9c73030a5
  Ha         - subnet-0d3db8dca9a438fea
  Mgmt       - subnet-0dd259113cb275883

Is this configuration correct? (yes/no): yes

Would you like to save this subnet configuration to a file? (yes/no): yes
Enter filename (default: subnet-config.json): my-subnets.json
✅ Subnet configuration saved to: my-subnets.json
   You can reuse it with: --subnet-file my-subnets.json
```

## Subnet Configuration File Format

```json
{
  "primary": {
    "outside": "subnet-008c04ea3c16cfc44",
    "inside": "subnet-0dd89264e19b79c71",
    "ha": "subnet-0e27fec5fef60e89c",
    "mgmt": "subnet-0b9fb7667ffd28db8"
  },
  "backup": {
    "outside": "subnet-011055542bb0745aa",
    "inside": "subnet-0c5d1b3f9c73030a5",
    "ha": "subnet-0d3db8dca9a438fea",
    "mgmt": "subnet-0dd259113cb275883"
  }
}
```

## IP Address Assignment

The script automatically assigns static IPs using the 10th IP in each subnet:

| Subnet CIDR | Assigned IP | Notes |
|-------------|-------------|-------|
| 10.0.1.0/24 | 10.0.1.10 | .1 is gateway, .10 is safe |
| 10.0.2.0/24 | 10.0.2.10 | Consistent offset |
| 172.16.0.0/24 | 172.16.0.10 | Works with any CIDR |

## Security Group Configuration

### Management Security Group (fortigate-mgmt-sg)
- **Ingress**: HTTPS (443), SSH (22) from 10.0.0.0/8
- **Egress**: All traffic
- **Applied to**: Management ENIs

### Data Security Group (fortigate-data-sg)
- **Ingress**: All traffic from 0.0.0.0/0
- **Egress**: All traffic
- **Applied to**: Outside and Inside ENIs

### HA Security Group (fortigate-ha-sg)
- **Ingress**: All traffic (self-referencing)
- **Egress**: All traffic
- **Applied to**: HA ENIs

## Error Handling

The script includes comprehensive error handling:

1. **Credential Errors**: Clear instructions on how to configure AWS credentials
2. **Subnet Validation**: Format checking and AWS API validation
3. **Permission Errors**: Specific guidance on required IAM permissions
4. **Network Errors**: Retry logic and helpful error messages

## Reusability

Once you've created a subnet configuration file, you can reuse it:

```bash
# First time - interactive
python3 create-enis.py --profile prod --region us-east-1 --account 123456789012
# Save configuration when prompted

# Subsequent runs - automated
python3 create-enis.py --profile prod --region us-east-1 --account 123456789012 --subnet-file my-subnets.json
```

## Integration with Terraform

After ENI creation, the script outputs Terraform variables:

```hcl
primary_outside_eni_id = "eni-0123456789abcdef0"
primary_inside_eni_id  = "eni-0123456789abcdef1"
primary_ha_eni_id      = "eni-0123456789abcdef2"
primary_mgmt_eni_id    = "eni-0123456789abcdef3"

backup_outside_eni_id  = "eni-0123456789abcdef4"
backup_inside_eni_id   = "eni-0123456789abcdef5"
backup_ha_eni_id       = "eni-0123456789abcdef6"
backup_mgmt_eni_id     = "eni-0123456789abcdef7"
```

Copy these directly into your `terraform.tfvars` file.
