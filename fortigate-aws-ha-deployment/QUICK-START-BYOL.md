# Quick Start: FortiGate BYOL License Deployment

## 1. Store License Tokens (One-Time Setup)

**PowerShell:**
```powershell
$env:AWS_PROFILE = "renaws"
aws secretsmanager create-secret --name fortigate/primary-license-token --secret-string "YOUR-PRIMARY-TOKEN" --region us-east-1
aws secretsmanager create-secret --name fortigate/backup-license-token --secret-string "YOUR-BACKUP-TOKEN" --region us-east-1
```

**Bash:**
```bash
export AWS_PROFILE=renaws
aws secretsmanager create-secret --name fortigate/primary-license-token --secret-string "YOUR-PRIMARY-TOKEN" --region us-east-1
aws secretsmanager create-secret --name fortigate/backup-license-token --secret-string "YOUR-BACKUP-TOKEN" --region us-east-1
```

## 2. Enable in terraform.tfvars

Add this line:
```hcl
enable_license_token_retrieval = true
```

## 3. Deploy

**PowerShell:**
```powershell
cd fortigate-aws-ha-deployment\terraform
$env:AWS_PROFILE = "renaws"
terraform apply -var-file=terraform.tfvars
```

**Bash:**
```bash
cd fortigate-aws-ha-deployment/terraform
export AWS_PROFILE=renaws
terraform apply -var-file=terraform.tfvars
```

## 4. Verify (Wait 5-10 minutes after deployment)

```bash
ssh admin@<MANAGEMENT_IP>
get system status
execute shell
cat /var/log/fortigate-license.log
```

## Done! 🎉

Licenses are automatically applied during boot. Check the log file for confirmation.

---

**Need help?** See [BYOL-LICENSE-DEPLOYMENT-GUIDE.md](./BYOL-LICENSE-DEPLOYMENT-GUIDE.md) for detailed instructions.
