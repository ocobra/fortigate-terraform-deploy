# Quick Start: Create ENIs for FortiGate HA

## Step 1: Install Dependencies
```bash
pip install boto3
```

## Step 2: Configure AWS Credentials

Choose one method:

### Method A: AWS CLI Profile (Recommended)
```bash
aws configure --profile myprofile
# Enter your AWS Access Key ID
# Enter your AWS Secret Access Key
# Enter default region: us-east-1
# Enter default output format: json
```

### Method B: Default Credentials
```bash
aws configure
```

### Method C: Environment Variables
```bash
export AWS_ACCESS_KEY_ID=your_access_key_here
export AWS_SECRET_ACCESS_KEY=your_secret_key_here
export AWS_DEFAULT_REGION=us-east-1
```

## Step 3: Run the Script

### Interactive Mode (Recommended):
```bash
cd fortigate-aws-ha-deployment
python3 create-enis.py --profile myprofile --region us-east-1 --account 678632990402
```

The script will prompt you for each subnet ID:
- Primary FortiGate: outside, inside, HA, management subnet IDs
- Backup FortiGate: outside, inside, HA, management subnet IDs

### With Subnet Configuration File:
```bash
cd fortigate-aws-ha-deployment
python3 create-enis.py --profile myprofile --region us-east-1 --account 678632990402 --subnet-file subnet-config.json
```

### With Default Credentials:
```bash
cd fortigate-aws-ha-deployment
python3 create-enis.py --region us-east-1 --account 678632990402
```

## Step 4: Copy the Output

The script will output ENI IDs like this:
```
📝 Terraform Variables (add to terraform.tfvars):
----------------------------------------------------------------------
primary_outside_eni_id = "eni-0123456789abcdef0"
primary_inside_eni_id  = "eni-0123456789abcdef1"
primary_ha_eni_id      = "eni-0123456789abcdef2"
primary_mgmt_eni_id    = "eni-0123456789abcdef3"

backup_outside_eni_id  = "eni-0123456789abcdef4"
backup_inside_eni_id   = "eni-0123456789abcdef5"
backup_ha_eni_id       = "eni-0123456789abcdef6"
backup_mgmt_eni_id     = "eni-0123456789abcdef7"
```

## Step 5: Add to terraform.tfvars

Copy the ENI IDs to your `terraform/terraform.tfvars` file.

## Step 6: Deploy with Terraform
```bash
cd terraform
terraform init
terraform plan
terraform apply
```

## Common Issues

### "Unable to locate credentials"
- Run `aws configure` or use `--profile` flag
- Check `~/.aws/credentials` file exists

### "Profile not found"
- List profiles: `cat ~/.aws/credentials`
- Use correct profile name with `--profile`

### "Access Denied"
- Verify IAM permissions for EC2 operations
- Check you're using the correct AWS account

## Need Help?
See the full documentation: [ENI-CREATION-README.md](./ENI-CREATION-README.md)
