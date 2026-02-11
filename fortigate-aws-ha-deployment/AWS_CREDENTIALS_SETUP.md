# AWS Credentials Setup Guide

## Error: AuthFailure - AWS Credentials Not Valid

If you see this error:
```
❌ Error discovering AMI: An error occurred (AuthFailure) when calling the DescribeImages operation: 
AWS was not able to validate the provided access credentials
```

This means your AWS credentials are not properly configured.

## Quick Fix

### Option 1: Configure AWS CLI (Recommended)

```bash
# Install AWS CLI if not already installed
# Windows: Download from https://aws.amazon.com/cli/
# Mac: brew install awscli
# Linux: sudo apt-get install awscli  or  sudo yum install awscli

# Configure AWS credentials
aws configure

# You'll be prompted for:
# AWS Access Key ID: [your-access-key]
# AWS Secret Access Key: [your-secret-key]
# Default region name: us-east-1
# Default output format: json
```

### Option 2: Set Environment Variables

**Windows (PowerShell):**
```powershell
$env:AWS_ACCESS_KEY_ID="your-access-key-here"
$env:AWS_SECRET_ACCESS_KEY="your-secret-key-here"
$env:AWS_DEFAULT_REGION="us-east-1"
```

**Windows (Command Prompt):**
```cmd
set AWS_ACCESS_KEY_ID=your-access-key-here
set AWS_SECRET_ACCESS_KEY=your-secret-key-here
set AWS_DEFAULT_REGION=us-east-1
```

**Linux/Mac:**
```bash
export AWS_ACCESS_KEY_ID="your-access-key-here"
export AWS_SECRET_ACCESS_KEY="your-secret-key-here"
export AWS_DEFAULT_REGION="us-east-1"
```

### Option 3: Use AWS Profile

If you have multiple AWS accounts, use profiles:

```bash
# Configure a named profile
aws configure --profile mycompany

# Then when running deploy.py, select "Use AWS profile" and enter "mycompany"
```

## Detailed Setup Instructions

### Step 1: Get AWS Credentials

You need AWS Access Keys from your AWS account:

1. **Log into AWS Console**: https://console.aws.amazon.com/
2. **Go to IAM**: Services → IAM (Identity and Access Management)
3. **Create/Select User**: 
   - Click "Users" in left sidebar
   - Click your username (or create a new user)
4. **Create Access Key**:
   - Click "Security credentials" tab
   - Scroll to "Access keys" section
   - Click "Create access key"
   - Choose "Command Line Interface (CLI)"
   - Click "Next" and "Create access key"
5. **Save Credentials**:
   - **Access Key ID**: Looks like `AKIAIOSFODNN7EXAMPLE`
   - **Secret Access Key**: Looks like `wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY`
   - ⚠️ **IMPORTANT**: Save these immediately! You can't view the secret key again.

### Step 2: Configure AWS CLI

#### Windows

1. **Install AWS CLI**:
   - Download from: https://awscli.amazonaws.com/AWSCLIV2.msi
   - Run the installer
   - Restart your terminal/PowerShell

2. **Verify Installation**:
   ```powershell
   aws --version
   # Should show: aws-cli/2.x.x ...
   ```

3. **Configure Credentials**:
   ```powershell
   aws configure
   ```

#### Mac

1. **Install AWS CLI**:
   ```bash
   # Using Homebrew
   brew install awscli
   
   # Or download from: https://awscli.amazonaws.com/AWSCLIV2.pkg
   ```

2. **Configure Credentials**:
   ```bash
   aws configure
   ```

#### Linux

1. **Install AWS CLI**:
   ```bash
   # Ubuntu/Debian
   sudo apt-get update
   sudo apt-get install awscli
   
   # Amazon Linux/RHEL/CentOS
   sudo yum install awscli
   
   # Or use pip
   pip install awscli --upgrade --user
   ```

2. **Configure Credentials**:
   ```bash
   aws configure
   ```

### Step 3: Verify Credentials Work

Test that your credentials are working:

```bash
# Test AWS credentials
aws sts get-caller-identity

# Should return something like:
# {
#     "UserId": "AIDAI...",
#     "Account": "123456789012",
#     "Arn": "arn:aws:iam::123456789012:user/your-username"
# }
```

If this works, your credentials are properly configured!

### Step 4: Run Deploy Script Again

Now try running the deployment script again:

```bash
python deploy.py
```

When prompted "Use AWS profile?", answer **yes** and use **default** (or your profile name).

## Troubleshooting

### Issue: "aws: command not found"

**Problem**: AWS CLI is not installed or not in PATH

**Solution**:
1. Install AWS CLI (see Step 2 above)
2. Restart your terminal
3. Verify: `aws --version`

### Issue: "Unable to locate credentials"

**Problem**: No credentials configured

**Solution**:
```bash
# Check if credentials file exists
# Windows: C:\Users\USERNAME\.aws\credentials
# Mac/Linux: ~/.aws/credentials

# If missing, run:
aws configure
```

### Issue: "The security token included in the request is invalid"

**Problem**: Credentials are expired or incorrect

**Solution**:
1. Generate new access keys in AWS Console
2. Run `aws configure` again with new keys
3. Or update credentials file directly

### Issue: "Access Denied" or "UnauthorizedOperation"

**Problem**: Your IAM user doesn't have required permissions

**Solution**:
Your IAM user needs these permissions:
- `ec2:DescribeImages`
- `ec2:DescribeVpcs`
- `ec2:DescribeSubnets`
- `ec2:DescribeKeyPairs`
- `ec2:DescribeTransitGateways`

See [IAM_AND_SECURITY_REQUIREMENTS.md](IAM_AND_SECURITY_REQUIREMENTS.md) for complete list.

### Issue: Credentials work for AWS CLI but not for Python script

**Problem**: Python is using different credentials or profile

**Solution**:

1. **Check which credentials Python sees**:
   ```python
   import boto3
   session = boto3.Session()
   credentials = session.get_credentials()
   print(f"Access Key: {credentials.access_key}")
   print(f"Region: {session.region_name}")
   ```

2. **Ensure Python uses same profile**:
   ```bash
   # Set environment variable
   export AWS_PROFILE=default  # or your profile name
   
   # Then run script
   python deploy.py
   ```

3. **Check credentials file location**:
   ```bash
   # Should be at:
   # Windows: C:\Users\USERNAME\.aws\credentials
   # Mac/Linux: ~/.aws/credentials
   
   # View contents (be careful not to share this!)
   cat ~/.aws/credentials
   ```

## Credentials File Format

Your `~/.aws/credentials` file should look like:

```ini
[default]
aws_access_key_id = AKIAIOSFODNN7EXAMPLE
aws_secret_access_key = wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY

[mycompany]
aws_access_key_id = AKIAI44QH8DHBEXAMPLE
aws_secret_access_key = je7MtGbClwBF/2Zp9Utk/h3yCo8nvbEXAMPLEKEY
```

Your `~/.aws/config` file should look like:

```ini
[default]
region = us-east-1
output = json

[profile mycompany]
region = us-west-2
output = json
```

## Security Best Practices

### 1. Never Commit Credentials to Git

```bash
# Add to .gitignore
echo ".aws/" >> .gitignore
echo "*.pem" >> .gitignore
echo "credentials" >> .gitignore
```

### 2. Use IAM Roles When Possible

If running on EC2, use IAM roles instead of access keys:
- No credentials needed in files
- Automatically rotated by AWS
- More secure

### 3. Rotate Access Keys Regularly

```bash
# Create new access key
aws iam create-access-key --user-name your-username

# Update credentials
aws configure

# Delete old access key
aws iam delete-access-key --access-key-id OLD_KEY_ID --user-name your-username
```

### 4. Use MFA for Sensitive Operations

Enable MFA on your IAM user for additional security.

### 5. Limit Permissions

Only grant the minimum IAM permissions needed. See [IAM_AND_SECURITY_REQUIREMENTS.md](IAM_AND_SECURITY_REQUIREMENTS.md).

## Alternative: Use IAM Role (Advanced)

If you're running on an EC2 instance or using AWS CloudShell:

1. **Attach IAM Role to EC2 Instance**
2. **No credentials needed** - boto3 automatically uses the instance role
3. **More secure** - no access keys to manage

## Getting Help

### Check AWS CLI Configuration

```bash
# View current configuration
aws configure list

# Output shows:
#       Name                    Value             Type    Location
#       ----                    -----             ----    --------
#    profile                <not set>             None    None
# access_key     ****************MPLE shared-credentials-file    
# secret_key     ****************MPLE shared-credentials-file    
#     region                us-east-1      config-file    ~/.aws/config
```

### Test Specific AWS Service

```bash
# Test EC2 access (needed for AMI discovery)
aws ec2 describe-regions

# Test Secrets Manager access (needed for BYOL licenses)
aws secretsmanager list-secrets

# Test S3 access (needed for state management)
aws s3 ls
```

### Enable Debug Mode

```bash
# See detailed AWS API calls
export AWS_DEBUG=1
python deploy.py
```

## Quick Reference

### Common Commands

```bash
# Configure credentials
aws configure

# Check current identity
aws sts get-caller-identity

# List configured profiles
aws configure list-profiles

# Use specific profile
export AWS_PROFILE=myprofile

# Set region
export AWS_DEFAULT_REGION=us-east-1

# Test EC2 access
aws ec2 describe-regions
```

### Credential Locations

- **Windows**: `C:\Users\USERNAME\.aws\credentials`
- **Mac/Linux**: `~/.aws/credentials`
- **Environment Variables**: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`

### Required IAM Permissions

Minimum permissions for deploy.py:
- `ec2:Describe*` (for validation)
- `ec2:RunInstances` (for deployment)
- `secretsmanager:GetSecretValue` (for BYOL licenses)
- `s3:GetObject` (for licenses in S3)

See complete list in [IAM_AND_SECURITY_REQUIREMENTS.md](IAM_AND_SECURITY_REQUIREMENTS.md).

## Next Steps

Once credentials are configured:

1. ✅ Verify: `aws sts get-caller-identity`
2. ✅ Test: `aws ec2 describe-regions`
3. ✅ Run: `python deploy.py`

## Additional Resources

- [AWS CLI Configuration Guide](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-files.html)
- [AWS Credentials Best Practices](https://docs.aws.amazon.com/general/latest/gr/aws-access-keys-best-practices.html)
- [IAM User Guide](https://docs.aws.amazon.com/IAM/latest/UserGuide/)
- [Boto3 Credentials](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/credentials.html)
