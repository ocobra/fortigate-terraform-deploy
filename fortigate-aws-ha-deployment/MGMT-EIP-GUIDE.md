# Management Elastic IP Guide

## Overview

The `create-enis.py` script now supports allocating Elastic IP addresses for the management interfaces of both FortiGate instances, enabling direct internet access for management purposes.

## Feature Description

When you use the `--allocate-mgmt-eips` flag, the script will:

1. Allocate 2 Elastic IP addresses (one for each FortiGate)
2. Associate them with the management ENIs
3. Tag them appropriately for identification
4. Display management access URLs
5. Provide security recommendations

## Usage

### Basic Usage with Management EIPs

```bash
python3 create-enis.py \
  --profile renaws \
  --region us-east-1 \
  --account 678632990402 \
  --allocate-mgmt-eips \
  --tag "my-deployment"
```

### With Both Outside and Management EIPs

```bash
python3 create-enis.py \
  --profile renaws \
  --region us-east-1 \
  --account 678632990402 \
  --allocate-eips \
  --allocate-mgmt-eips \
  --tag "my-deployment"
```

## What Gets Created

### Without --allocate-mgmt-eips (Default)
- 8 ENIs (4 per FortiGate)
- Management interfaces have private IPs only
- Access only via VPN or bastion host

### With --allocate-mgmt-eips
- 8 ENIs (4 per FortiGate)
- 2 Elastic IPs for management interfaces
- Direct internet access to FortiGate management
- Public HTTPS and SSH access

## Output Example

When you run with `--allocate-mgmt-eips`, you'll see:

```
🌐 Allocating Elastic IP for Primary MGMT interface (management access)...
✅ Allocated and associated Management EIP: 54.123.45.67 (eipalloc-0abc123def456)
   Access FortiGate Primary via: https://54.123.45.67

🌐 Allocating Elastic IP for Backup MGMT interface (management access)...
✅ Allocated and associated Management EIP: 52.98.76.54 (eipalloc-0xyz789ghi012)
   Access FortiGate Backup via: https://52.98.76.54

...

🌐 Management Access Information
======================================================================

You can now access your FortiGate instances from the internet:

🔵 Primary FortiGate:
   HTTPS: https://54.123.45.67
   SSH:   ssh admin@54.123.45.67

🟢 Backup FortiGate:
   HTTPS: https://52.98.76.54
   SSH:   ssh admin@52.98.76.54

⚠️  Security Recommendations:
   1. Update the management security group to restrict access to your IP
   2. Change the default admin password immediately after first login
   3. Enable MFA for admin accounts
   4. Review and update firewall policies

📝 To restrict management access to your IP:
   aws ec2 authorize-security-group-ingress \
     --group-id sg-0abc123def456 \
     --protocol tcp --port 443 \
     --cidr YOUR_IP_ADDRESS/32 \
     --profile renaws \
     --region us-east-1
```

## Security Considerations

### Default Security Group Rules

The management security group created by the script allows:
- TCP port 443 (HTTPS) from 10.0.0.0/8
- TCP port 22 (SSH) from 10.0.0.0/8

### Recommended Security Hardening

After allocating management EIPs, you should:

#### 1. Restrict Access to Your IP

```bash
# Get your public IP
MY_IP=$(curl -s ifconfig.me)

# Update security group to allow only your IP
aws ec2 authorize-security-group-ingress \
  --group-id <security-group-id> \
  --protocol tcp \
  --port 443 \
  --cidr ${MY_IP}/32 \
  --profile renaws \
  --region us-east-1

# Also for SSH
aws ec2 authorize-security-group-ingress \
  --group-id <security-group-id> \
  --protocol tcp \
  --port 22 \
  --cidr ${MY_IP}/32 \
  --profile renaws \
  --region us-east-1
```

#### 2. Remove Broad Access Rules

```bash
# List current rules
aws ec2 describe-security-groups \
  --group-ids <security-group-id> \
  --profile renaws \
  --region us-east-1

# Remove the 10.0.0.0/8 rule if you only need internet access
aws ec2 revoke-security-group-ingress \
  --group-id <security-group-id> \
  --protocol tcp \
  --port 443 \
  --cidr 10.0.0.0/8 \
  --profile renaws \
  --region us-east-1
```

#### 3. Enable MFA on FortiGate

After first login:
1. Navigate to System > Administrators
2. Edit the admin user
3. Enable Two-Factor Authentication
4. Configure TOTP or email-based MFA

#### 4. Change Default Password

```bash
# Via SSH
ssh admin@<management-eip>

# In FortiGate CLI
config system admin
    edit admin
        set password <new-strong-password>
    end
end
```

#### 5. Enable HTTPS Certificate

```bash
# Upload your SSL certificate or use Let's Encrypt
config system global
    set admin-server-cert <certificate-name>
end
```

## Cost Implications

### Elastic IP Costs

- **Allocated but associated**: $0.00/hour (free when associated with a running instance)
- **Allocated but not associated**: $0.005/hour (~$3.60/month)
- **Data transfer**: Standard AWS data transfer rates apply

### For Management EIPs

Since management EIPs are associated with ENIs that will be attached to running FortiGate instances:
- **Cost**: $0.00/hour (free)
- **Total for 2 management EIPs**: $0.00/month

### Important Notes

- EIPs are free when associated with running instances
- If you stop the FortiGate instances, the EIPs will incur charges
- Release EIPs when not needed to avoid charges

## Comparison: Management Access Methods

### Method 1: VPN/Bastion Host (Default)
**Pros:**
- More secure (no public exposure)
- No additional EIP costs
- Follows AWS best practices

**Cons:**
- Requires VPN or bastion host setup
- More complex access path
- Additional infrastructure needed

**Use Case:** Production environments with strict security requirements

### Method 2: Management EIPs (--allocate-mgmt-eips)
**Pros:**
- Direct internet access
- Simple setup
- Easy troubleshooting
- No additional infrastructure needed

**Cons:**
- Public exposure (requires proper security group configuration)
- Potential security risk if not properly secured
- Subject to internet-based attacks

**Use Case:** Development, testing, or environments with proper security controls

### Method 3: Hybrid Approach
**Pros:**
- Flexibility for different use cases
- Can enable/disable as needed

**Cons:**
- More complex management
- Need to track which method is active

**Use Case:** Environments that need both secure and convenient access

## Terraform Integration

The EIP allocation IDs are automatically added to the `eni-ids.json` file:

```json
{
  "enis": {
    "primary_mgmt": {
      "eni_id": "eni-0abc123",
      "private_ip": "10.101.22.74",
      ...
    },
    ...
  },
  "eips": {
    "primary_mgmt": {
      "allocation_id": "eipalloc-0abc123",
      "public_ip": "54.123.45.67",
      "eni_id": "eni-0abc123",
      "purpose": "management"
    },
    "backup_mgmt": {
      "allocation_id": "eipalloc-0xyz789",
      "public_ip": "52.98.76.54",
      "eni_id": "eni-0xyz789",
      "purpose": "management"
    }
  }
}
```

## Cleanup

When you're done with the deployment, use the `delete-enis.py` script to clean up:

```bash
python3 delete-enis.py \
  --profile renaws \
  --region us-east-1 \
  --tag "my-deployment"
```

This will:
1. Disassociate and release all EIPs (including management EIPs)
2. Delete all ENIs
3. Delete security groups (if not in use)

## Troubleshooting

### Issue: Cannot access FortiGate via management EIP

**Possible Causes:**
1. Security group not allowing your IP
2. FortiGate instance not running
3. ENI not attached to instance
4. EIP not associated with ENI

**Solutions:**

```bash
# Check EIP association
aws ec2 describe-addresses \
  --allocation-ids <eip-allocation-id> \
  --profile renaws \
  --region us-east-1

# Check ENI attachment
aws ec2 describe-network-interfaces \
  --network-interface-ids <eni-id> \
  --profile renaws \
  --region us-east-1

# Check security group rules
aws ec2 describe-security-groups \
  --group-ids <sg-id> \
  --profile renaws \
  --region us-east-1

# Test connectivity
curl -k https://<management-eip>
```

### Issue: EIP allocation failed

**Possible Causes:**
1. EIP limit reached (default: 5 per region)
2. Insufficient permissions
3. Network error

**Solutions:**

```bash
# Check EIP limit
aws ec2 describe-account-attributes \
  --attribute-names max-elastic-ips \
  --profile renaws \
  --region us-east-1

# Request limit increase via AWS Support if needed

# Check IAM permissions
aws iam get-user --profile renaws
```

### Issue: Security group rules not working

**Possible Causes:**
1. Wrong CIDR block
2. Wrong port
3. Network ACLs blocking traffic

**Solutions:**

```bash
# Verify your public IP
curl ifconfig.me

# Check security group rules
aws ec2 describe-security-groups \
  --group-ids <sg-id> \
  --profile renaws \
  --region us-east-1 \
  --query 'SecurityGroups[0].IpPermissions'

# Check network ACLs
aws ec2 describe-network-acls \
  --filters "Name=vpc-id,Values=<vpc-id>" \
  --profile renaws \
  --region us-east-1
```

## Best Practices

### 1. Use Management EIPs for Development Only

For production environments, use VPN or AWS Systems Manager Session Manager instead.

### 2. Always Restrict Security Groups

Never leave management interfaces open to 0.0.0.0/0.

### 3. Enable Logging

Enable VPC Flow Logs to monitor access to management interfaces:

```bash
aws ec2 create-flow-logs \
  --resource-type NetworkInterface \
  --resource-ids <mgmt-eni-id> \
  --traffic-type ALL \
  --log-destination-type cloud-watch-logs \
  --log-group-name /aws/vpc/flowlogs/fortigate-mgmt \
  --profile renaws \
  --region us-east-1
```

### 4. Use Temporary Access

Consider using temporary EIP associations for maintenance windows:

```bash
# Allocate EIP temporarily
aws ec2 allocate-address --domain vpc

# Associate with management ENI
aws ec2 associate-address \
  --allocation-id <eip-alloc-id> \
  --network-interface-id <mgmt-eni-id>

# After maintenance, disassociate and release
aws ec2 disassociate-address --association-id <assoc-id>
aws ec2 release-address --allocation-id <eip-alloc-id>
```

### 5. Monitor Access

Set up CloudWatch alarms for unusual access patterns:

```bash
# Create metric filter for failed login attempts
aws logs put-metric-filter \
  --log-group-name /aws/vpc/flowlogs/fortigate-mgmt \
  --filter-name FailedLoginAttempts \
  --filter-pattern '[version, account, eni, source, destination, srcport, destport="443", protocol="6", packets, bytes, windowstart, windowend, action="REJECT", flowlogstatus]' \
  --metric-transformations \
    metricName=FailedMgmtAccess,metricNamespace=FortiGate,metricValue=1
```

## Quick Reference

### Allocate Management EIPs
```bash
python3 create-enis.py \
  --profile renaws \
  --region us-east-1 \
  --account 678632990402 \
  --allocate-mgmt-eips \
  --tag "my-deployment"
```

### Access FortiGate
```bash
# HTTPS
https://<management-eip>

# SSH
ssh admin@<management-eip>
```

### Restrict to Your IP
```bash
MY_IP=$(curl -s ifconfig.me)
aws ec2 authorize-security-group-ingress \
  --group-id <sg-id> \
  --protocol tcp --port 443 \
  --cidr ${MY_IP}/32 \
  --profile renaws --region us-east-1
```

### Cleanup
```bash
python3 delete-enis.py \
  --profile renaws \
  --region us-east-1 \
  --tag "my-deployment"
```

---

**Last Updated**: 2026-02-12
**Status**: Complete ✅

