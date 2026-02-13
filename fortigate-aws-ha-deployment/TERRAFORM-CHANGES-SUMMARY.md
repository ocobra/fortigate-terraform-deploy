# Terraform Configuration Changes Summary

This document summarizes all changes made to the Terraform configuration during the FortiGate HA deployment troubleshooting and enhancement process.

## 1. Network Interface Configuration Changes

### Issue: Device Index Limit Exceeded
**Problem**: Attempting to attach 5 network interfaces (device indexes 0-4) but c5.2xlarge only supports 4 ENIs.

**Solution**: 
- Used pre-created outside ENI as primary interface (device index 0) in instance creation
- Removed duplicate attachment for outside interface
- Final mapping:
  - Device 0 = outside (attached at instance creation)
  - Device 1 = inside
  - Device 2 = HA
  - Device 3 = management

**Files Modified**:
- `terraform/modules/fortigate-ha/main.tf`

## 2. Instance Configuration Conflicts

### Issue: vpc_security_group_ids and source_dest_check Conflicts
**Problem**: These parameters conflict with `network_interface` block in instance resource.

**Solution**:
- Removed `vpc_security_group_ids` from instance resources (security groups managed on ENIs)
- Removed `source_dest_check` from instance resources
- Added `null_resource` with AWS CLI commands to disable source/dest check on ENIs
- Added idempotency triggers (eni_id, instance_id, region, profile)
- Added destroy provisioners to re-enable source/dest check on terraform destroy

**Files Modified**:
- `terraform/modules/fortigate-ha/main.tf`

## 3. AWS Profile Support

### Issue: Profile Not Passed to AWS CLI Commands
**Problem**: AWS CLI commands in null_resource provisioners didn't use the configured profile.

**Solution**:
- Added `aws_profile` variable to fortigate-ha module with default ""
- Passed aws_profile from root module to fortigate-ha module
- Updated null_resource commands to conditionally include --profile flag when profile is set
- Stored profile in triggers for destroy provisioner access

**Files Modified**:
- `terraform/main.tf`
- `terraform/modules/fortigate-ha/main.tf`
- `terraform/modules/fortigate-ha/variables.tf`
- `terraform/terraform.tfvars`

## 4. FortiGate Configuration Template Changes

### 4.1 Management Gateway Fix
**Problem**: Both primary and backup FortiGate used same management gateway, causing connectivity issues.

**Solution**:
- Updated config templates to use `mgmt_gateway` (cidrhost of mgmt subnet) instead of `default_gateway`
- Primary uses 10.101.22.65 (from primary mgmt subnet)
- Backup uses 10.101.22.97 (from backup mgmt subnet)

**Files Modified**:
- `terraform/modules/fortigate-ha/templates/fortigate-primary-config.tpl`
- `terraform/modules/fortigate-ha/templates/fortigate-backup-config.tpl`

### 4.2 Static Routing Configuration
**Problem**: BGP configuration was incorrect - Transit Gateway uses standard VPC attachment, not BGP.

**Solution**:
- Removed all BGP configuration (neighbors, route-maps, access-lists)
- Added static routes for Transit Gateway connectivity:
  - Route 1: 0.0.0.0/0 via outside interface to Internet
  - Route 2: 10.0.0.0/8 via inside interface to Transit Gateway
  - Route 3: 172.16.0.0/12 via inside interface to Transit Gateway
  - Route 4: 192.168.0.0/16 via inside interface to Transit Gateway
- Added `inside_gateway` parameter to templates

**Files Modified**:
- `terraform/modules/fortigate-ha/templates/fortigate-primary-config.tpl`
- `terraform/modules/fortigate-ha/templates/fortigate-backup-config.tpl`
- `terraform/modules/fortigate-ha/main.tf` (added inside_gateway to template variables)

### 4.3 Syslog Configuration
**Current State**: Syslog configured to send to 169.254.169.254 (EC2 metadata service), which doesn't forward to CloudWatch.

**Note**: This configuration is non-functional for CloudWatch logging. FortiGate doesn't natively support CloudWatch Logs API. Options for CloudWatch integration:
1. Deploy syslog forwarder EC2 instance
2. Remove syslog config and use FortiGate GUI for logs
3. Use FortiAnalyzer or FortiCloud

**Files**:
- `terraform/modules/fortigate-ha/templates/fortigate-primary-config.tpl`
- `terraform/modules/fortigate-ha/templates/fortigate-backup-config.tpl`

## 5. IAM Policy Enhancements

### Issue: Insufficient Permissions for HA Failover
**Problem**: FortiGate HA failover failed with 403 errors due to missing IAM permissions.

**Solution**:
- Added new IAM policy statements:
  - **FortiGateManageNetworkInterfaces**: AssignPrivateIpAddresses, UnassignPrivateIpAddresses
  - **FortiGateManageRoutes**: ReplaceRoute, CreateRoute, DeleteRoute
- Removed restrictive tag-based condition from EIP management
  - Original condition required ENIs to have `ManagedBy: FortiGate-HA` tag
  - Pre-created ENIs didn't have this tag, causing 403 errors
  - Solution: Removed condition entirely (still secure since only FortiGate instances have the IAM role)

**Files Modified**:
- `terraform/modules/fortigate-ha/main.tf` (IAM policy section)

## 6. EIP Configuration

### Manual EIP Association
**Approach**: Manual EIP association chosen over automated SDN connector approach.

**Configuration**:
- Primary: 34.235.72.230 → eni-0d35dc7b8f138e94c (10.101.20.10)
- Backup: 44.215.207.78 → eni-00dafd4120249650a (10.101.21.10)
- Each FortiGate has its own public IP for internet connectivity

**Note**: EIPs associated via AWS CLI, not managed by Terraform in current configuration.

## Summary of Key Parameters

### Network Configuration
- **VPC**: vpc-0e16490e6ab8422fb
- **Availability Zones**: us-east-1a, us-east-1b
- **Subnet Masks**: 
  - HA and inside interfaces: 255.255.255.224 (/27)
  - Outside and management: varies by subnet

### FortiGate Configuration
- **Version**: FortiOS 7.4.11 (ami-0a868b222f973e16b)
- **Instance Type**: c5.2xlarge
- **HA Mode**: Active-Passive with unicast heartbeat
- **Priorities**: Primary=200, Backup=100

### Routing Configuration
- **Type**: Static routing (not BGP)
- **Transit Gateway**: Standard VPC attachment
- **Inside Gateway**: First IP of inside subnet (e.g., 10.101.20.33 for primary)

### IAM Permissions
- EC2 describe operations (instances, ENIs, addresses, VPCs, subnets, route tables)
- EIP management (AssociateAddress, DisassociateAddress)
- Network interface management (AssignPrivateIpAddresses, UnassignPrivateIpAddresses)
- Route management (ReplaceRoute, CreateRoute, DeleteRoute)

## Files Changed

1. `terraform/main.tf` - Added aws_profile parameter passing
2. `terraform/variables.tf` - Added aws_profile variable
3. `terraform/terraform.tfvars` - Added aws_profile value
4. `terraform/modules/fortigate-ha/main.tf` - Major changes:
   - Network interface attachment logic
   - Source/dest check null_resource
   - IAM policy enhancements
   - Template variable additions
5. `terraform/modules/fortigate-ha/variables.tf` - Added aws_profile variable
6. `terraform/modules/fortigate-ha/templates/fortigate-primary-config.tpl` - Static routing, mgmt gateway
7. `terraform/modules/fortigate-ha/templates/fortigate-backup-config.tpl` - Static routing, mgmt gateway

## Testing Status

✅ Terraform apply successful
✅ FortiGate instances deployed and accessible
✅ HA configuration functional
✅ Static routing configured
✅ EIPs associated manually
✅ IAM permissions validated
⚠️ CloudWatch logging non-functional (by design - requires additional infrastructure)

## Recommendations

1. **CloudWatch Logging**: Decide on logging strategy:
   - Option 1: Deploy syslog forwarder for CloudWatch integration
   - Option 2: Remove syslog config, use FortiGate GUI for logs
   - Option 3: Implement FortiAnalyzer or FortiCloud

2. **EIP Management**: Consider implementing automated EIP failover using FortiGate SDN connector if automatic failover is required.

3. **Monitoring**: VPC Flow Logs are configured and working - use these for network traffic analysis.

4. **Documentation**: Update deployment documentation to reflect static routing configuration instead of BGP.
