# SSH Key Pair Setup Guide for Windows

This guide shows you how to create an SSH key pair called `ALICO-FORTIGATE-KEYPAIR` and store the private key in AWS Secrets Manager.

## Prerequisites

- AWS CLI installed and configured
- PowerShell or Command Prompt
- AWS profile configured (e.g., `renaws`)

## Method 1: Create Key Pair via AWS CLI (Recommended)

This method creates the key pair directly in AWS and stores the private key in Secrets Manager.

### PowerShell:

```powershell
# Set your AWS profile
$env:AWS_PROFILE = "renaws"

# Create the key pair and save private key to file
aws ec2 create-key-pair `
    --key-name ALICO-FORTIGATE-KEYPAIR `
    --region us-east-1 `
    --query 'KeyMaterial' `
    --output text | Out-File -FilePath ALICO-FORTIGATE-KEYPAIR.pem -Encoding ASCII

# Display success message
Write-Host "✅ Key pair created: ALICO-FORTIGATE-KEYPAIR" -ForegroundColor Green
Write-Host "✅ Private key saved to: ALICO-FORTIGATE-KEYPAIR.pem" -ForegroundColor Green

# Read the private key content
$privateKey = Get-Content -Path ALICO-FORTIGATE-KEYPAIR.pem -Raw

# Store private key in Secrets Manager
aws secretsmanager create-secret `
    --name fortigate/ssh-private-key `
    --description "FortiGate SSH Private Key for ALICO-FORTIGATE-KEYPAIR" `
    --secret-string $privateKey `
    --region us-east-1

Write-Host "✅ Private key stored in Secrets Manager: fortigate/ssh-private-key" -ForegroundColor Green

# Verify the secret was created
aws secretsmanager describe-secret `
    --secret-id fortigate/ssh-private-key `
    --region us-east-1

# Set proper permissions on the private key file (for SSH client)
icacls ALICO-FORTIGATE-KEYPAIR.pem /inheritance:r
icacls ALICO-FORTIGATE-KEYPAIR.pem /grant:r "$($env:USERNAME):(R)"

Write-Host "`n✅ Setup complete!" -ForegroundColor Green
Write-Host "Key pair name for Terraform: ALICO-FORTIGATE-KEYPAIR" -ForegroundColor Cyan
Write-Host "Private key file: ALICO-FORTIGATE-KEYPAIR.pem" -ForegroundColor Cyan
Write-Host "Secrets Manager secret: fortigate/ssh-private-key" -ForegroundColor Cyan
```

### Command Prompt (CMD):

```cmd
REM Set your AWS profile
set AWS_PROFILE=renaws

REM Create the key pair and save private key to file
aws ec2 create-key-pair ^
    --key-name ALICO-FORTIGATE-KEYPAIR ^
    --region us-east-1 ^
    --query "KeyMaterial" ^
    --output text > ALICO-FORTIGATE-KEYPAIR.pem

echo Key pair created: ALICO-FORTIGATE-KEYPAIR
echo Private key saved to: ALICO-FORTIGATE-KEYPAIR.pem

REM Store private key in Secrets Manager
aws secretsmanager create-secret ^
    --name fortigate/ssh-private-key ^
    --description "FortiGate SSH Private Key for ALICO-FORTIGATE-KEYPAIR" ^
    --secret-string file://ALICO-FORTIGATE-KEYPAIR.pem ^
    --region us-east-1

echo Private key stored in Secrets Manager: fortigate/ssh-private-key

REM Verify the secret was created
aws secretsmanager describe-secret ^
    --secret-id fortigate/ssh-private-key ^
    --region us-east-1

echo Setup complete!
```

## Method 2: Use Existing Key Pair

If you already have an SSH key pair, you can import it to AWS and store in Secrets Manager.

### PowerShell:

```powershell
$env:AWS_PROFILE = "renaws"

# Import existing public key to AWS
aws ec2 import-key-pair `
    --key-name ALICO-FORTIGATE-KEYPAIR `
    --public-key-material fileb://path\to\your\public-key.pub `
    --region us-east-1

# Store existing private key in Secrets Manager
$privateKey = Get-Content -Path path\to\your\private-key.pem -Raw

aws secretsmanager create-secret `
    --name fortigate/ssh-private-key `
    --description "FortiGate SSH Private Key for ALICO-FORTIGATE-KEYPAIR" `
    --secret-string $privateKey `
    --region us-east-1

Write-Host "✅ Key pair imported and private key stored in Secrets Manager"
```

## Method 3: Generate Key Pair Locally with ssh-keygen

If you have OpenSSH installed (Windows 10/11 includes it by default):

### PowerShell:

```powershell
$env:AWS_PROFILE = "renaws"

# Create .ssh directory if it doesn't exist
$sshDir = "$env:USERPROFILE\.ssh"
if (-not (Test-Path $sshDir)) {
    New-Item -ItemType Directory -Path $sshDir | Out-Null
}

# Generate SSH key pair
ssh-keygen -t rsa -b 4096 -f "$sshDir\ALICO-FORTIGATE-KEYPAIR" -N '""' -C "fortigate-keypair"

Write-Host "✅ SSH key pair generated" -ForegroundColor Green

# Import public key to AWS
aws ec2 import-key-pair `
    --key-name ALICO-FORTIGATE-KEYPAIR `
    --public-key-material "fileb://$sshDir\ALICO-FORTIGATE-KEYPAIR.pub" `
    --region us-east-1

Write-Host "✅ Public key imported to AWS" -ForegroundColor Green

# Store private key in Secrets Manager
$privateKey = Get-Content -Path "$sshDir\ALICO-FORTIGATE-KEYPAIR" -Raw

aws secretsmanager create-secret `
    --name fortigate/ssh-private-key `
    --description "FortiGate SSH Private Key for ALICO-FORTIGATE-KEYPAIR" `
    --secret-string $privateKey `
    --region us-east-1

Write-Host "✅ Private key stored in Secrets Manager" -ForegroundColor Green

# Copy private key to current directory for easy access
Copy-Item "$sshDir\ALICO-FORTIGATE-KEYPAIR" -Destination ".\ALICO-FORTIGATE-KEYPAIR.pem"

Write-Host "`n✅ Setup complete!" -ForegroundColor Green
Write-Host "Private key location: $sshDir\ALICO-FORTIGATE-KEYPAIR" -ForegroundColor Cyan
Write-Host "Copy in current directory: .\ALICO-FORTIGATE-KEYPAIR.pem" -ForegroundColor Cyan
```

## Verification Steps

### 1. Verify Key Pair in AWS

**PowerShell:**
```powershell
$env:AWS_PROFILE = "renaws"

# List key pairs
aws ec2 describe-key-pairs `
    --key-names ALICO-FORTIGATE-KEYPAIR `
    --region us-east-1

# Should show:
# - KeyName: ALICO-FORTIGATE-KEYPAIR
# - KeyFingerprint: (fingerprint value)
```

### 2. Verify Secret in Secrets Manager

**PowerShell:**
```powershell
# Describe the secret
aws secretsmanager describe-secret `
    --secret-id fortigate/ssh-private-key `
    --region us-east-1

# Retrieve the secret (to verify it's accessible)
aws secretsmanager get-secret-value `
    --secret-id fortigate/ssh-private-key `
    --region us-east-1 `
    --query SecretString `
    --output text
```

### 3. Test SSH Connection (After FortiGate Deployment)

**PowerShell:**
```powershell
# SSH to FortiGate using the private key
ssh -i ALICO-FORTIGATE-KEYPAIR.pem admin@<FORTIGATE_MANAGEMENT_IP>
```

## Update Terraform Configuration

Add the key pair name to your `terraform.tfvars`:

```hcl
# SSH Key Pair
key_pair_name = "ALICO-FORTIGATE-KEYPAIR"
```

## Security Best Practices

### 1. Set Proper File Permissions

**PowerShell:**
```powershell
# Remove inherited permissions and grant only current user read access
icacls ALICO-FORTIGATE-KEYPAIR.pem /inheritance:r
icacls ALICO-FORTIGATE-KEYPAIR.pem /grant:r "$($env:USERNAME):(R)"
```

### 2. Backup the Private Key

```powershell
# Create encrypted backup
$privateKey = Get-Content -Path ALICO-FORTIGATE-KEYPAIR.pem -Raw
$secureString = ConvertTo-SecureString -String $privateKey -AsPlainText -Force
$encryptedKey = ConvertFrom-SecureString -SecureString $secureString
$encryptedKey | Out-File -FilePath ALICO-FORTIGATE-KEYPAIR.encrypted

Write-Host "✅ Encrypted backup created: ALICO-FORTIGATE-KEYPAIR.encrypted"
```

### 3. Restrict Secrets Manager Access

Create an IAM policy to restrict who can access the private key:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue",
        "secretsmanager:DescribeSecret"
      ],
      "Resource": "arn:aws:secretsmanager:us-east-1:*:secret:fortigate/ssh-private-key*",
      "Condition": {
        "StringEquals": {
          "aws:PrincipalTag/Team": "NetworkOps"
        }
      }
    }
  ]
}
```

## Troubleshooting

### Issue: "Key pair already exists"

**Solution:**
```powershell
# Delete existing key pair
aws ec2 delete-key-pair --key-name ALICO-FORTIGATE-KEYPAIR --region us-east-1

# Then recreate it
```

### Issue: "Secret already exists"

**Solution:**
```powershell
# Delete existing secret (with recovery window)
aws secretsmanager delete-secret `
    --secret-id fortigate/ssh-private-key `
    --recovery-window-in-days 7 `
    --region us-east-1

# Or force delete immediately (not recommended)
aws secretsmanager delete-secret `
    --secret-id fortigate/ssh-private-key `
    --force-delete-without-recovery `
    --region us-east-1

# Then recreate it
```

### Issue: "Permission denied (publickey)" when SSH

**Solution:**
```powershell
# Ensure correct permissions on private key file
icacls ALICO-FORTIGATE-KEYPAIR.pem /inheritance:r
icacls ALICO-FORTIGATE-KEYPAIR.pem /grant:r "$($env:USERNAME):(R)"

# Use correct SSH command
ssh -i ALICO-FORTIGATE-KEYPAIR.pem admin@<FORTIGATE_IP>
```

### Issue: "Invalid key format"

**Solution:**
```powershell
# Ensure the file has Unix line endings (LF, not CRLF)
# Use a text editor like Notepad++ or VS Code to convert line endings

# Or use PowerShell to fix line endings
$content = Get-Content -Path ALICO-FORTIGATE-KEYPAIR.pem -Raw
$content = $content -replace "`r`n", "`n"
$content | Out-File -FilePath ALICO-FORTIGATE-KEYPAIR.pem -Encoding ASCII -NoNewline
```

## Complete Setup Script

Here's a complete PowerShell script that does everything:

```powershell
# Complete SSH Key Pair Setup Script for Windows
# Creates key pair, stores in Secrets Manager, and configures permissions

param(
    [string]$KeyName = "ALICO-FORTIGATE-KEYPAIR",
    [string]$Region = "us-east-1",
    [string]$Profile = "renaws"
)

# Set AWS profile
$env:AWS_PROFILE = $Profile

Write-Host "🔐 FortiGate SSH Key Pair Setup" -ForegroundColor Cyan
Write-Host "================================`n" -ForegroundColor Cyan

# Step 1: Create key pair in AWS
Write-Host "Step 1: Creating key pair in AWS..." -ForegroundColor Yellow
try {
    aws ec2 create-key-pair `
        --key-name $KeyName `
        --region $Region `
        --query 'KeyMaterial' `
        --output text | Out-File -FilePath "$KeyName.pem" -Encoding ASCII
    
    Write-Host "✅ Key pair created: $KeyName" -ForegroundColor Green
    Write-Host "✅ Private key saved to: $KeyName.pem" -ForegroundColor Green
} catch {
    Write-Host "❌ Failed to create key pair: $_" -ForegroundColor Red
    exit 1
}

# Step 2: Store private key in Secrets Manager
Write-Host "`nStep 2: Storing private key in Secrets Manager..." -ForegroundColor Yellow
try {
    $privateKey = Get-Content -Path "$KeyName.pem" -Raw
    
    aws secretsmanager create-secret `
        --name fortigate/ssh-private-key `
        --description "FortiGate SSH Private Key for $KeyName" `
        --secret-string $privateKey `
        --region $Region | Out-Null
    
    Write-Host "✅ Private key stored in Secrets Manager: fortigate/ssh-private-key" -ForegroundColor Green
} catch {
    Write-Host "❌ Failed to store private key: $_" -ForegroundColor Red
    Write-Host "⚠️  Key pair was created but not stored in Secrets Manager" -ForegroundColor Yellow
}

# Step 3: Set proper file permissions
Write-Host "`nStep 3: Setting file permissions..." -ForegroundColor Yellow
try {
    icacls "$KeyName.pem" /inheritance:r | Out-Null
    icacls "$KeyName.pem" /grant:r "$($env:USERNAME):(R)" | Out-Null
    Write-Host "✅ File permissions set correctly" -ForegroundColor Green
} catch {
    Write-Host "⚠️  Could not set file permissions automatically" -ForegroundColor Yellow
}

# Step 4: Verify setup
Write-Host "`nStep 4: Verifying setup..." -ForegroundColor Yellow

# Verify key pair
$keyPair = aws ec2 describe-key-pairs --key-names $KeyName --region $Region 2>$null
if ($keyPair) {
    Write-Host "✅ Key pair verified in AWS" -ForegroundColor Green
}

# Verify secret
$secret = aws secretsmanager describe-secret --secret-id fortigate/ssh-private-key --region $Region 2>$null
if ($secret) {
    Write-Host "✅ Secret verified in Secrets Manager" -ForegroundColor Green
}

# Summary
Write-Host "`n✅ Setup Complete!" -ForegroundColor Green
Write-Host "==================`n" -ForegroundColor Green
Write-Host "Key Pair Name (for Terraform): $KeyName" -ForegroundColor Cyan
Write-Host "Private Key File: $KeyName.pem" -ForegroundColor Cyan
Write-Host "Secrets Manager Secret: fortigate/ssh-private-key" -ForegroundColor Cyan
Write-Host "Region: $Region`n" -ForegroundColor Cyan

Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "1. Add 'key_pair_name = `"$KeyName`"' to terraform.tfvars" -ForegroundColor White
Write-Host "2. Keep $KeyName.pem file secure (needed for SSH access)" -ForegroundColor White
Write-Host "3. Deploy FortiGate with Terraform" -ForegroundColor White
Write-Host "4. SSH to FortiGate: ssh -i $KeyName.pem admin@<FORTIGATE_IP>`n" -ForegroundColor White
```

Save this as `setup-ssh-keypair.ps1` and run:

```powershell
.\setup-ssh-keypair.ps1
```

## Summary

After completing these steps, you will have:

1. ✅ AWS EC2 Key Pair: `ALICO-FORTIGATE-KEYPAIR`
2. ✅ Private Key File: `ALICO-FORTIGATE-KEYPAIR.pem`
3. ✅ Private Key in Secrets Manager: `fortigate/ssh-private-key`
4. ✅ Proper file permissions set

Use `ALICO-FORTIGATE-KEYPAIR` as the `key_pair_name` in your Terraform configuration.
