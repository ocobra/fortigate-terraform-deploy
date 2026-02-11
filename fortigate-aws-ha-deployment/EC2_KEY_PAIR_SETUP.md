# EC2 Key Pair Setup Guide

## Overview

EC2 key pairs are required for SSH access to FortiGate instances. This guide explains how to create, import, or use existing key pairs for the FortiGate AWS HA deployment.

## Table of Contents

1. [What is an EC2 Key Pair?](#what-is-an-ec2-key-pair)
2. [Why Do You Need It?](#why-do-you-need-it)
3. [Creating a New Key Pair](#creating-a-new-key-pair)
4. [Importing an Existing Key Pair](#importing-an-existing-key-pair)
5. [Using the Key Pair in Deployment](#using-the-key-pair-in-deployment)
6. [Connecting to FortiGate Instances](#connecting-to-fortigate-instances)
7. [Troubleshooting](#troubleshooting)
8. [Security Best Practices](#security-best-practices)

## What is an EC2 Key Pair?

An EC2 key pair consists of:
- **Public key**: Stored by AWS and injected into EC2 instances at launch
- **Private key**: Downloaded to your local machine and used for SSH authentication

The key pair enables secure SSH access to your FortiGate instances for:
- Initial configuration verification
- Troubleshooting connectivity issues
- Emergency access if web interface is unavailable
- Log collection and diagnostics

## Why Do You Need It?

The FortiGate deployment script requires a key pair name because:

1. **Emergency Access**: If the FortiGate web interface becomes unavailable, SSH provides an alternative access method
2. **Automation**: Some deployment scripts may need to SSH into instances for configuration verification
3. **Troubleshooting**: Direct CLI access is essential for diagnosing network and HA issues
4. **AWS Requirement**: EC2 instances must be launched with a key pair (even if you don't plan to use SSH)

**Note**: While FortiGate is primarily managed through its web interface, having SSH access is a critical backup access method.

## Creating a New Key Pair

### Option 1: Using AWS Console

1. **Navigate to EC2 Console**:
   - Open the AWS Console
   - Go to **EC2** → **Network & Security** → **Key Pairs**

2. **Create Key Pair**:
   - Click **Create key pair**
   - Enter a name: `fortigate-ha-keypair`
   - Key pair type: **RSA**
   - Private key file format:
     - **`.pem`** for Linux/Mac (OpenSSH)
     - **`.ppk`** for Windows (PuTTY)
   - Click **Create key pair**

3. **Save the Private Key**:
   - The private key file will download automatically
   - **IMPORTANT**: This is your only chance to download the private key!
   - Save it securely: `~/.ssh/fortigate-ha-keypair.pem`

4. **Set Correct Permissions** (Linux/Mac):
   ```bash
   chmod 400 ~/.ssh/fortigate-ha-keypair.pem
   ```

### Option 2: Using AWS CLI

```bash
# Create key pair and save private key
aws ec2 create-key-pair \
  --key-name fortigate-ha-keypair \
  --key-type rsa \
  --key-format pem \
  --query 'KeyMaterial' \
  --output text > ~/.ssh/fortigate-ha-keypair.pem

# Set correct permissions
chmod 400 ~/.ssh/fortigate-ha-keypair.pem

# Verify key pair was created
aws ec2 describe-key-pairs --key-names fortigate-ha-keypair
```

### Option 3: Using Terraform

If you want Terraform to manage the key pair:

```hcl
# Generate a new key pair
resource "tls_private_key" "fortigate_key" {
  algorithm = "RSA"
  rsa_bits  = 4096
}

# Create AWS key pair from generated key
resource "aws_key_pair" "fortigate_keypair" {
  key_name   = "fortigate-ha-keypair"
  public_key = tls_private_key.fortigate_key.public_key_openssh
}

# Save private key locally (be careful with this in production!)
resource "local_file" "private_key" {
  content         = tls_private_key.fortigate_key.private_key_pem
  filename        = "${path.module}/fortigate-ha-keypair.pem"
  file_permission = "0400"
}

# Output the key name for use in deployment
output "key_pair_name" {
  value = aws_key_pair.fortigate_keypair.key_name
}
```

## Importing an Existing Key Pair

If you already have an SSH key pair you want to use:

### Option 1: Using AWS Console

1. **Navigate to Key Pairs**:
   - EC2 Console → **Network & Security** → **Key Pairs**

2. **Import Key Pair**:
   - Click **Actions** → **Import key pair**
   - Name: `fortigate-ha-keypair`
   - Browse and select your **public key** file (`.pub`)
   - Click **Import key pair**

### Option 2: Using AWS CLI

```bash
# Import existing public key
aws ec2 import-key-pair \
  --key-name fortigate-ha-keypair \
  --public-key-material fileb://~/.ssh/id_rsa.pub

# Verify import
aws ec2 describe-key-pairs --key-names fortigate-ha-keypair
```

### Generating a Key Pair Locally First

If you don't have an existing key pair:

```bash
# Generate new SSH key pair
ssh-keygen -t rsa -b 4096 -f ~/.ssh/fortigate-ha-keypair -C "fortigate-ha-access"

# This creates:
# - Private key: ~/.ssh/fortigate-ha-keypair
# - Public key: ~/.ssh/fortigate-ha-keypair.pub

# Set correct permissions
chmod 400 ~/.ssh/fortigate-ha-keypair

# Import public key to AWS
aws ec2 import-key-pair \
  --key-name fortigate-ha-keypair \
  --public-key-material fileb://~/.ssh/fortigate-ha-keypair.pub
```

## Using the Key Pair in Deployment

### Interactive Deployment Script

When running `python deploy.py`, you'll be prompted:

```
🛡️  FortiGate Configuration
==================================================

Instance Configuration:
Instance type [c5.xlarge]: 
EC2 Key Pair name: fortigate-ha-keypair
```

Enter the **name** of your key pair (not the file path).

### Configuration File

In your `config.yaml`:

```yaml
fortigate:
  ami_id: ami-xxxxx
  instance_type: c5.xlarge
  key_pair_name: fortigate-ha-keypair  # Just the name, not the path
  admin_password: "{{ secrets.admin_password }}"
  ha_password: "{{ secrets.ha_password }}"
```

### Terraform Variables

In `terraform.tfvars`:

```hcl
key_pair_name = "fortigate-ha-keypair"
```

## Connecting to FortiGate Instances

### Getting Instance IP Addresses

After deployment, get the management IP addresses:

```bash
# Using Terraform outputs
cd terraform
terraform output fortigate_primary_mgmt_ip
terraform output fortigate_backup_mgmt_ip

# Or using AWS CLI
aws ec2 describe-instances \
  --filters "Name=tag:Name,Values=fortigate-primary" \
  --query 'Reservations[0].Instances[0].NetworkInterfaces[?Description==`mgmt`].PrivateIpAddress' \
  --output text
```

### SSH Connection

#### Basic SSH Connection

```bash
# Connect to primary FortiGate
ssh -i ~/.ssh/fortigate-ha-keypair.pem admin@<primary-mgmt-ip>

# Connect to backup FortiGate
ssh -i ~/.ssh/fortigate-ha-keypair.pem admin@<backup-mgmt-ip>
```

#### SSH Through Bastion Host

If FortiGate management interfaces are in private subnets:

```bash
# SSH through bastion host
ssh -i ~/.ssh/fortigate-ha-keypair.pem \
  -o ProxyCommand="ssh -i ~/.ssh/bastion-key.pem -W %h:%p ec2-user@<bastion-ip>" \
  admin@<fortigate-mgmt-ip>
```

#### SSH Config for Easy Access

Add to `~/.ssh/config`:

```
# Bastion host
Host bastion
  HostName <bastion-public-ip>
  User ec2-user
  IdentityFile ~/.ssh/bastion-key.pem

# FortiGate Primary
Host fortigate-primary
  HostName <primary-mgmt-private-ip>
  User admin
  IdentityFile ~/.ssh/fortigate-ha-keypair.pem
  ProxyJump bastion

# FortiGate Backup
Host fortigate-backup
  HostName <backup-mgmt-private-ip>
  User admin
  IdentityFile ~/.ssh/fortigate-ha-keypair.pem
  ProxyJump bastion
```

Then connect simply with:

```bash
ssh fortigate-primary
ssh fortigate-backup
```

### FortiGate CLI Commands

Once connected via SSH:

```bash
# Check system status
get system status

# Check HA status
get system ha status

# Check BGP neighbors
get router info bgp summary

# Check routing table
get router info routing-table all

# View logs
execute log display

# Check interface status
get system interface physical
```

## Troubleshooting

### Issue: "Key pair not found"

**Error when running deploy.py:**
```
❌ Error validating key pair fortigate-ha-keypair: The key pair 'fortigate-ha-keypair' does not exist
```

**Solution:**
1. List available key pairs:
   ```bash
   aws ec2 describe-key-pairs --query 'KeyPairs[*].KeyName'
   ```

2. Create or import a key pair (see sections above)

3. Ensure you're in the correct AWS region:
   ```bash
   aws configure get region
   ```

### Issue: "Permission denied (publickey)"

**Error when connecting via SSH:**
```
Permission denied (publickey).
```

**Solutions:**

1. **Check key file permissions:**
   ```bash
   ls -l ~/.ssh/fortigate-ha-keypair.pem
   # Should show: -r-------- (400)
   
   # Fix if needed:
   chmod 400 ~/.ssh/fortigate-ha-keypair.pem
   ```

2. **Verify you're using the correct key:**
   ```bash
   # Check key fingerprint matches AWS
   ssh-keygen -l -f ~/.ssh/fortigate-ha-keypair.pem
   aws ec2 describe-key-pairs --key-names fortigate-ha-keypair --query 'KeyPairs[0].KeyFingerprint'
   ```

3. **Verify correct username:**
   - FortiGate default SSH user is `admin`, not `ec2-user`
   ```bash
   ssh -i ~/.ssh/fortigate-ha-keypair.pem admin@<ip>
   ```

4. **Check security group allows SSH:**
   ```bash
   # Verify port 22 is open from your IP
   aws ec2 describe-security-groups \
     --filters "Name=tag:Name,Values=fortigate-mgmt-sg" \
     --query 'SecurityGroups[0].IpPermissions[?FromPort==`22`]'
   ```

### Issue: "Connection timed out"

**Error:**
```
ssh: connect to host <ip> port 22: Connection timed out
```

**Solutions:**

1. **Check instance is running:**
   ```bash
   aws ec2 describe-instances \
     --filters "Name=tag:Name,Values=fortigate-primary" \
     --query 'Reservations[0].Instances[0].State.Name'
   ```

2. **Verify security group rules:**
   - Management security group must allow SSH (port 22) from your IP

3. **Check network ACLs:**
   - Ensure NACLs allow inbound/outbound SSH traffic

4. **Verify route to management subnet:**
   - If management is in private subnet, ensure you're connecting through bastion/VPN

### Issue: "Wrong key pair used during deployment"

If you deployed with the wrong key pair:

1. **Option 1: Redeploy with correct key pair**
   ```bash
   # Update terraform.tfvars
   key_pair_name = "correct-keypair-name"
   
   # Redeploy
   terraform apply
   ```

2. **Option 2: Use EC2 Instance Connect (if enabled)**
   ```bash
   aws ec2-instance-connect send-ssh-public-key \
     --instance-id <instance-id> \
     --instance-os-user admin \
     --ssh-public-key file://~/.ssh/new-key.pub
   ```

3. **Option 3: Use Systems Manager Session Manager (if configured)**
   ```bash
   aws ssm start-session --target <instance-id>
   ```

## Security Best Practices

### Key Management

1. **Protect Private Keys:**
   ```bash
   # Store in secure location
   mkdir -p ~/.ssh
   chmod 700 ~/.ssh
   chmod 400 ~/.ssh/fortigate-ha-keypair.pem
   ```

2. **Never Commit Keys to Version Control:**
   ```bash
   # Add to .gitignore
   echo "*.pem" >> .gitignore
   echo "*.ppk" >> .gitignore
   echo ".ssh/" >> .gitignore
   ```

3. **Use Different Keys for Different Environments:**
   - Dev: `fortigate-dev-keypair`
   - Staging: `fortigate-staging-keypair`
   - Prod: `fortigate-prod-keypair`

4. **Rotate Keys Regularly:**
   ```bash
   # Create new key pair
   aws ec2 create-key-pair --key-name fortigate-ha-keypair-2024 ...
   
   # Update instances (requires redeployment or manual update)
   # Then delete old key pair
   aws ec2 delete-key-pair --key-name fortigate-ha-keypair-old
   ```

### Access Control

1. **Limit SSH Access by IP:**
   ```hcl
   # In security group configuration
   ingress {
     from_port   = 22
     to_port     = 22
     protocol    = "tcp"
     cidr_blocks = ["203.0.113.0/24"]  # Your office IP range only
     description = "SSH from office network"
   }
   ```

2. **Use Bastion Hosts:**
   - Never expose FortiGate management interfaces directly to internet
   - Route SSH through hardened bastion hosts

3. **Enable CloudTrail Logging:**
   ```bash
   # Monitor key pair usage
   aws cloudtrail lookup-events \
     --lookup-attributes AttributeKey=ResourceName,AttributeValue=fortigate-ha-keypair
   ```

4. **Use IAM Policies to Control Key Pair Management:**
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Effect": "Allow",
         "Action": [
           "ec2:DescribeKeyPairs"
         ],
         "Resource": "*"
       },
       {
         "Effect": "Allow",
         "Action": [
           "ec2:CreateKeyPair",
           "ec2:DeleteKeyPair"
         ],
         "Resource": "*",
         "Condition": {
           "StringEquals": {
             "aws:RequestedRegion": "us-east-1"
           }
         }
       }
     ]
   }
   ```

### Backup and Recovery

1. **Document Key Pair Names:**
   - Keep a record of which key pairs are used for which deployments
   - Store in password manager or secure documentation

2. **Backup Private Keys Securely:**
   - Use encrypted storage (e.g., AWS Secrets Manager, HashiCorp Vault)
   - Never store unencrypted keys in cloud storage

3. **Have Emergency Access Plan:**
   - Document alternative access methods (Systems Manager, EC2 Instance Connect)
   - Maintain bastion host access separately

## Quick Reference

### Common Commands

```bash
# List key pairs in current region
aws ec2 describe-key-pairs --query 'KeyPairs[*].[KeyName,KeyFingerprint]' --output table

# Create new key pair
aws ec2 create-key-pair --key-name fortigate-ha-keypair --query 'KeyMaterial' --output text > ~/.ssh/fortigate-ha-keypair.pem && chmod 400 ~/.ssh/fortigate-ha-keypair.pem

# Import existing key pair
aws ec2 import-key-pair --key-name fortigate-ha-keypair --public-key-material fileb://~/.ssh/id_rsa.pub

# Delete key pair
aws ec2 delete-key-pair --key-name fortigate-ha-keypair

# SSH to FortiGate
ssh -i ~/.ssh/fortigate-ha-keypair.pem admin@<mgmt-ip>

# Check key fingerprint
ssh-keygen -l -f ~/.ssh/fortigate-ha-keypair.pem
```

### Deployment Script Usage

```bash
# Interactive deployment (will prompt for key pair name)
python deploy.py

# With configuration file
python deploy.py --config config.yaml

# The script will validate the key pair exists before deployment
```

## Additional Resources

- [AWS EC2 Key Pairs Documentation](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-key-pairs.html)
- [FortiGate CLI Reference](https://docs.fortinet.com/document/fortigate/latest/cli-reference)
- [SSH Best Practices](https://www.ssh.com/academy/ssh/best-practices)
- [IAM and Security Requirements](IAM_AND_SECURITY_REQUIREMENTS.md)
- [Main README](README.md)

## Support

If you encounter issues with key pair setup:

1. Verify you're in the correct AWS region
2. Check IAM permissions for EC2 key pair operations
3. Ensure key file has correct permissions (400)
4. Review security group rules for SSH access
5. Check CloudTrail logs for key pair API calls
