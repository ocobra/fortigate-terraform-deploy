# AWS Credentials Workaround Guide

## Problem

You're getting this error:
```
Error validating AMI: An error occurred (AuthFailure) when calling the DescribeImages operation: 
AWS was not able to validate the provided access credentials
```

## Solution: Use --skip-validation Flag

The deployment script now supports a `--skip-validation` flag that bypasses all AWS API validation checks during the configuration phase. Terraform will still validate everything when it runs.

### How to Use

```powershell
# Run the deployment script with skip-validation flag
python deploy.py --skip-validation
```

### What This Does

1. **Skips AWS API calls** during configuration validation
2. **Allows you to proceed** even with broken credentials
3. **Terraform will validate** resources when it actually runs
4. **You still need credentials** for Terraform to work (but Terraform might use different credential sources)

### Complete Workflow

1. **Find AMI ID manually** (see below)
2. **Run script with flag**:
   ```powershell
   python deploy.py --skip-validation
   ```
3. **When prompted**:
   - "Auto-discover FortiGate AMI?" → Answer `n`
   - "FortiGate AMI ID" → Paste the AMI ID you found
4. **Continue with configuration** as normal
5. **Terraform will run** and validate resources using its own credential chain

## Finding AMI ID Manually

### Quick Method (AWS Console)

1. **Log into AWS Console**: https://console.aws.amazon.com/
2. **Go to EC2 → AMIs**:
   - Services → EC2
   - Left sidebar → "AMIs" (under Images)
   - Change dropdown to "Public images"
3. **Search**: `FortiGate-VM64-AWS 7.2 OnDemand`
   - Or use `7.4` for newer version
   - Or use `BYOL` if you have licenses
4. **Copy AMI ID**: Looks like `ami-0123456789abcdef0`

### Example AMI IDs by Region

These are examples - always verify current AMI IDs:

**FortiGate 7.2 OnDemand:**
- us-east-1: `ami-0a868b222f973e16b` (example)
- us-west-2: `ami-0xxxxxxxxxxxxx`
- eu-west-1: `ami-0xxxxxxxxxxxxx`

**FortiGate 7.4 OnDemand:**
- us-east-1: `ami-0xxxxxxxxxxxxx`
- us-west-2: `ami-0xxxxxxxxxxxxx`

## Why This Works

The Python script uses boto3 to validate resources, but Terraform has its own credential chain:

1. **Terraform checks**:
   - Environment variables (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`)
   - AWS credentials file (`~/.aws/credentials`)
   - IAM role (if running on EC2)
   - AWS profile

2. **Your credentials might work for Terraform** even if boto3 can't use them

## Full Command Examples

### Basic deployment with skip-validation
```powershell
python deploy.py --skip-validation
```

### Plan only (see what will be created)
```powershell
python deploy.py --skip-validation --plan-only
```

### Save configuration for later
```powershell
python deploy.py --skip-validation --save-config my-config.yaml
```

### Use saved configuration
```powershell
python deploy.py --config my-config.yaml --skip-validation
```

## Important Notes

### ⚠️ Limitations

1. **No pre-validation**: Resources won't be validated until Terraform runs
2. **Errors appear later**: Invalid VPC IDs, subnet IDs, etc. will fail during Terraform apply
3. **Still need credentials**: Terraform still needs working AWS credentials to deploy

### ✅ Benefits

1. **Bypass boto3 issues**: Works around Python credential problems
2. **Manual control**: You specify exact AMI ID
3. **Faster setup**: No waiting for API calls during configuration

## Fixing Credentials Properly

While `--skip-validation` works as a workaround, you should still fix your credentials:

### Test Current Credentials

```powershell
# Test if AWS CLI works
aws sts get-caller-identity

# If this fails, your credentials are broken
```

### Fix Credentials

```powershell
# Reconfigure AWS CLI
aws configure

# Enter:
# - AWS Access Key ID
# - AWS Secret Access Key
# - Default region (e.g., us-east-1)
# - Output format (json)
```

### Get New Access Keys

If your keys are expired:

1. Log into AWS Console
2. Go to IAM → Users → Your Username
3. Click "Security credentials" tab
4. Click "Create access key"
5. Save the keys
6. Run `aws configure` and enter them

## Troubleshooting

### Issue: Script still asks for auto-discovery

**Problem**: You forgot the `--skip-validation` flag

**Solution**: 
```powershell
python deploy.py --skip-validation
```

### Issue: Terraform fails with credential error

**Problem**: Terraform can't find credentials either

**Solution**: Set environment variables before running:
```powershell
$env:AWS_ACCESS_KEY_ID="your-key-here"
$env:AWS_SECRET_ACCESS_KEY="your-secret-here"
$env:AWS_DEFAULT_REGION="us-east-1"

python deploy.py --skip-validation
```

### Issue: Invalid AMI ID error from Terraform

**Problem**: The AMI ID you provided doesn't exist in your region

**Solution**: 
1. Verify you're using the correct region
2. Find the AMI ID for your specific region
3. AMI IDs are region-specific!

## Quick Reference

### Command to Run
```powershell
python deploy.py --skip-validation
```

### When Prompted
- Auto-discover AMI? → `n`
- FortiGate AMI ID → `ami-0a868b222f973e16b` (your AMI)
- Continue with other prompts normally

### Where to Find AMI
AWS Console → EC2 → AMIs → Public images → Search "FortiGate-VM64-AWS"

## Additional Resources

- [AWS_CREDENTIALS_SETUP.md](AWS_CREDENTIALS_SETUP.md) - Full credential setup guide
- [AMI_AND_LICENSING_GUIDE.md](AMI_AND_LICENSING_GUIDE.md) - Detailed AMI finding instructions
- [USAGE.md](USAGE.md) - Complete deployment guide

## Summary

**Quick Fix**: Use `python deploy.py --skip-validation` and provide AMI ID manually when prompted.

**Long-term Fix**: Fix your AWS credentials using `aws configure` so all features work properly.
