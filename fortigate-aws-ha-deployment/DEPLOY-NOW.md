# Deploy FortiGate HA Now

## ✅ Prerequisites Complete
- ✓ Terraform installed
- ✓ ENIs created
- ✓ terraform.tfvars configured
- ✓ VPC ID corrected (vpc-0e16490e6ab8422fb)
- ✓ Local state storage configured

## 🚀 Deploy in 3 Steps

### Step 1: Initialize Terraform
```bash
cd fortigate-aws-ha-deployment/terraform
terraform init
```

**Expected output:**
```
Initializing the backend...
Initializing provider plugins...
Terraform has been successfully initialized!
```

### Step 2: Review the Plan
```bash
terraform plan
```

**What to check:**
- Number of resources to create (~25-30 resources)
- ENI attachments look correct
- No errors or warnings

### Step 3: Deploy
```bash
terraform apply
```

Type `yes` when prompted.

**Deployment time:** ~5-10 minutes

---

## 📊 After Deployment

### Get Management IPs
```bash
terraform output fortigate_primary_mgmt_ip
terraform output fortigate_backup_mgmt_ip
```

### Access FortiGate Web UI

**Primary FortiGate:**
```
URL: https://<primary_mgmt_ip>
Username: admin
Password: !c0mpl3xp@ssw0rd$
```

**Backup FortiGate:**
```
URL: https://<backup_mgmt_ip>
Username: admin
Password: !c0mpl3xp@ssw0rd$
```

### Verify HA Status

1. Log into Primary FortiGate
2. Go to **System > HA**
3. Check status:
   - Primary should show: **Master/Active**
   - Backup should show: **Slave/Standby**

### Verify BGP

In FortiGate CLI:
```
get router info bgp summary
```

Should show BGP sessions with Transit Gateway (ASN 65321).

---

## 🔧 Troubleshooting

### Issue: "Error acquiring the state lock"
**Solution:** Another terraform process is running. Wait or:
```bash
terraform force-unlock <LOCK_ID>
```

### Issue: "ENI already attached"
**Solution:** ENIs might be attached to another instance. Check:
```bash
aws ec2 describe-network-interfaces --profile renaws --region us-east-1 \
  --network-interface-ids eni-0f2b7af07f935dc95 \
  --query 'NetworkInterfaces[0].Attachment'
```

### Issue: "Invalid AMI ID"
**Solution:** Verify AMI exists:
```bash
aws ec2 describe-images --profile renaws --region us-east-1 \
  --image-ids ami-0a868b222f973e16b
```

### Issue: Deployment fails
**Solution:** Check detailed error, fix issue, then:
```bash
terraform apply  # Terraform will resume from where it failed
```

---

## 📝 Your Configuration Summary

| Item | Value |
|------|-------|
| **VPC ID** | vpc-0e16490e6ab8422fb |
| **Region** | us-east-1 |
| **AZs** | us-east-1a, us-east-1b |
| **Instance Type** | c5.4xlarge |
| **AMI ID** | ami-0a868b222f973e16b |
| **Key Pair** | PERSONAL-FTNT |
| **Transit Gateway** | tgw-0c0228dc5dffa8fa9 |
| **BGP ASN (FortiGate)** | 65200 |
| **BGP ASN (TGW)** | 65321 |
| **Hostnames** | fgt-aws-a, fgt-aws-b |

---

## 🧹 Cleanup (if needed)

To destroy the deployment:
```bash
cd fortigate-aws-ha-deployment/terraform
terraform destroy
```

**Note:** This will NOT delete the ENIs (they were created separately).

To delete ENIs:
```bash
aws ec2 delete-network-interface --profile renaws --region us-east-1 --network-interface-id eni-0f2b7af07f935dc95
aws ec2 delete-network-interface --profile renaws --region us-east-1 --network-interface-id eni-05d7c0464ff090f3b
aws ec2 delete-network-interface --profile renaws --region us-east-1 --network-interface-id eni-04323804fb6e0f9b1
aws ec2 delete-network-interface --profile renaws --region us-east-1 --network-interface-id eni-005955f7041309036
aws ec2 delete-network-interface --profile renaws --region us-east-1 --network-interface-id eni-02b5b2520f46276f5
aws ec2 delete-network-interface --profile renaws --region us-east-1 --network-interface-id eni-0d20398ff6e3b1fb9
aws ec2 delete-network-interface --profile renaws --region us-east-1 --network-interface-id eni-01a6621b246697bd6
aws ec2 delete-network-interface --profile renaws --region us-east-1 --network-interface-id eni-00a1afab6a01f1af9
```

---

## 📂 State File Location

Your Terraform state will be stored locally at:
```
fortigate-aws-ha-deployment/terraform/terraform.tfstate
```

**Important:** 
- Back up this file after deployment
- Don't commit it to git (it contains sensitive data)
- Keep it safe for future terraform operations

---

## ✅ Ready to Deploy!

Run these commands now:
```bash
cd fortigate-aws-ha-deployment/terraform
terraform init
terraform plan
terraform apply
```
