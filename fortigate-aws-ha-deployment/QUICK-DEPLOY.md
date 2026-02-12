# Quick Deploy Guide

## Your ENI IDs (Already Added to terraform.tfvars ✓)

```
Primary: eni-0f2b7af07f935dc95, eni-05d7c0464ff090f3b, eni-04323804fb6e0f9b1, eni-005955f7041309036
Backup:  eni-02b5b2520f46276f5, eni-0d20398ff6e3b1fb9, eni-01a6621b246697bd6, eni-00a1afab6a01f1af9
```

## Next Steps (5 minutes)

### 1. Edit terraform.tfvars
```bash
cd fortigate-aws-ha-deployment/terraform
nano terraform.tfvars  # or use your preferred editor
```

### 2. Update These Required Values:

```hcl
# Line 7: Your VPC ID
vpc_id = "vpc-XXXXXXXXX"

# Line 26: FortiGate AMI ID  
fortigate_ami_id = "ami-XXXXXXXXX"

# Line 28: Your EC2 key pair name
key_pair_name = "YOUR-KEY-PAIR"

# Line 29: Strong admin password
admin_password = "YourSecurePassword123!"

# Line 30: Strong HA password
ha_password = "YourHAPassword123!"

# Line 36: Transit Gateway ID (if using existing)
existing_transit_gateway_id = "tgw-XXXXXXXXX"
```

### 3. Find Your Values:

**VPC ID:**
```bash
aws ec2 describe-vpcs --region us-east-1 --query 'Vpcs[*].VpcId' --output text
```

**FortiGate AMI:**
```bash
aws ec2 describe-images --region us-east-1 --owners 679593333241 \
  --filters "Name=name,Values=FortiGate-VM64-AWS-7.4*-BYOL-*" \
  --query 'Images[0].ImageId' --output text
```

**Key Pairs:**
```bash
aws ec2 describe-key-pairs --region us-east-1 --query 'KeyPairs[*].KeyName'
```

**Transit Gateway:**
```bash
aws ec2 describe-transit-gateways --region us-east-1 --query 'TransitGateways[*].TransitGatewayId'
```

### 4. Deploy:

```bash
terraform init
terraform plan    # Review the plan
terraform apply   # Type 'yes' to confirm
```

### 5. Get Management IPs:

```bash
terraform output fortigate_primary_mgmt_ip
terraform output fortigate_backup_mgmt_ip
```

### 6. Access FortiGate:

```
https://<management_ip>
Username: admin
Password: <your_admin_password>
```

## Complete Checklist

See [DEPLOYMENT-CHECKLIST.md](./DEPLOYMENT-CHECKLIST.md) for detailed steps.

## Troubleshooting

**Can't find AMI?**
```bash
python3 ../deploy.py --auto-discover-ami --license-type BYOL --fortigate-version 7.4
```

**Need to create key pair?**
```bash
aws ec2 create-key-pair --key-name fortigate-ha-key --region us-east-1 \
  --query 'KeyMaterial' --output text > fortigate-ha-key.pem
chmod 400 fortigate-ha-key.pem
```

**Deployment fails?**
```bash
terraform destroy  # Clean up
# Fix the issue in terraform.tfvars
terraform apply    # Try again
```
