# FortiGate HA EIP Failover - Requirements Specification

## Overview
Implement FortiGate AWS SDN connector-based HA failover to enable automatic Elastic IP (EIP) migration for OUTSIDE interfaces between primary and backup FortiGate instances during failover events. 

**CRITICAL:** Management EIPs remain statically associated to maintain continuous administrative access.

## Problem Statement

### Current Issues
1. **Terraform Static EIP Associations**: `terraform/modules/fortigate-ha/main.tf` creates static EIP associations for OUTSIDE interfaces
2. **Missing IAM Permissions**: FortiGate instances lack IAM role with EC2 EIP management permissions
3. **No AWS SDN Connector**: FortiGate configuration templates missing AWS SDN connector setup
4. **No EIP Failover Configuration**: FortiGate HA configuration doesn't include EIP failover settings

### Impact
- When primary FortiGate fails, OUTSIDE EIP remains attached to failed instance
- Internet traffic cannot reach the new active instance (backup)
- Manual intervention required to move OUTSIDE EIPs
- Service disruption during failover
- **Management access remains available** (EIPs stay associated)

## User Stories

### 1. Network Administrator - Automatic EIP Failover
**As a** Network Administrator  
**I want** FortiGate HA to automatically move OUTSIDE EIPs from failed primary to backup  
**So that** internet traffic continues without manual intervention

**Acceptance Criteria:**
- OUTSIDE EIP failover completes within 60 seconds
- No manual AWS console/CLI intervention required
- Traffic resumes automatically through backup instance
- Works for planned and unplanned failover events
- Management EIPs remain on their respective instances

### 2. DevOps Engineer - IAM Infrastructure
**As a** DevOps Engineer  
**I want** Terraform to provision IAM roles and policies for FortiGate EIP management  
**So that** infrastructure supports automated failover

**Acceptance Criteria:**
- IAM role created with EC2 EIP management permissions
- IAM instance profile attached to both FortiGate instances
- Permissions follow principle of least privilege
- Resources properly tagged for management

### 3. Security Engineer - Least Privilege
**As a** Security Engineer  
**I want** FortiGate instances to have minimal IAM permissions  
**So that** security posture is maintained while supporting failover

**Acceptance Criteria:**
- IAM policy grants only required EC2 permissions
- Permissions scoped to resources with specific tags
- No wildcard permissions for sensitive operations
- IAM policy documented and auditable

### 4. System Operator - Failover Validation
**As a** System Operator  
**I want** to verify EIP failover works correctly through testing  
**So that** I can trust the HA configuration in production

**Acceptance Criteria:**
- Test plan includes multiple failover scenarios
- Validation script checks EIP association status
- Failover timing measured and documented
- Rollback procedure documented


## Functional Requirements

### FR1: IAM Role and Instance Profile
**Priority:** High | **Status:** Not Started

#### FR1.1: IAM Role Creation
- Terraform creates IAM role named `fortigate-ha-eip-management-role`
- Role has trust relationship with EC2 service
- Role includes inline policy for EIP management
- Role tagged with project metadata

#### FR1.2: IAM Policy Permissions
**Describe Permissions** (read-only, no resource restrictions):
- `ec2:DescribeInstances`
- `ec2:DescribeNetworkInterfaces`
- `ec2:DescribeAddresses`
- `ec2:DescribeVpcs`
- `ec2:DescribeSubnets`
- `ec2:DescribeRouteTables`

**EIP Management Permissions** (restricted by tag):
- `ec2:AssociateAddress`
- `ec2:DisassociateAddress`
- Condition: `ec2:ResourceTag/ManagedBy = "FortiGate-HA"`

#### FR1.3: IAM Instance Profile
- Instance profile created from IAM role
- Attached to both primary and backup FortiGate instances
- Conditional creation based on `enable_eip_failover` variable

### FR2: EIP Allocation Without Static Association
**Priority:** High | **Status:** Completed (create-enis.py)

#### FR2.1: create-enis.py Behavior
- ✅ Allocates EIPs for OUTSIDE interfaces
- ✅ Does NOT associate OUTSIDE EIPs with ENIs
- ✅ Tags OUTSIDE EIPs with `ManagedBy=FortiGate-HA`
- ✅ Management EIPs remain associated (NO CHANGE)

#### FR2.2: Terraform EIP Resources
- Remove `aws_eip_association.primary_outside` resource
- Remove `aws_eip_association.backup_outside` resource
- Keep `aws_eip.primary_outside` allocation resource
- Keep `aws_eip.backup_outside` allocation resource
- Tag EIPs with `ManagedBy=FortiGate-HA`

### FR3: FortiGate AWS SDN Connector
**Priority:** High | **Status:** Not Started

#### FR3.1: SDN Connector Configuration
- Add `config system sdn-connector` to FortiGate templates
- Configure connector type as `aws`
- Enable `use-metadata-iam` for IAM role credentials
- Set region from Terraform variable
- Set update interval to 60 seconds

#### FR3.2: Template Variables
- Add `aws_region` variable to template context
- Add `primary_outside_eip_id` variable
- Add `backup_outside_eip_id` variable
- Pass EIP allocation IDs to FortiGate configuration

### FR4: FortiGate HA EIP Failover Configuration
**Priority:** High | **Status:** Not Started

#### FR4.1: HA Configuration Enhancement
- Update `config system ha` with EIP failover settings
- Configure primary to manage EIP associations
- Configure backup to take over on failover
- Set appropriate HA priorities (primary: 200, backup: 100)

#### FR4.2: Interface Configuration
- Configure OUTSIDE interface (port1) for EIP failover
- Ensure interface monitoring enabled
- Configure proper gateway settings

### FR5: Terraform Variables and Outputs
**Priority:** Medium | **Status:** Not Started

#### FR5.1: New Variables
- `enable_eip_failover` (bool, default: true)
- `aws_region` (string, required)

#### FR5.2: Updated Outputs
- `iam_role_arn`
- `iam_instance_profile_name`
- `primary_outside_eip_allocation_id`
- `backup_outside_eip_allocation_id`
- `eip_failover_enabled`

### FR6: Documentation
**Priority:** Medium | **Status:** Not Started

- Architecture documentation with diagrams
- Deployment guide with verification steps
- Troubleshooting guide
- Testing documentation
- Migration guide for existing deployments

## Non-Functional Requirements

### NFR1: Performance
- EIP failover completes within 60 seconds
- SDN connector update interval: 60 seconds
- Zero packet loss during planned failover
- <1% packet loss during unplanned failover

### NFR2: Security
- IAM permissions follow least privilege principle
- EIP management restricted by resource tags
- No wildcard permissions for sensitive operations
- Secure credential handling (IAM instance profile)

### NFR3: Reliability
- Failover success rate: 99.9%
- Automatic recovery from transient failures
- Proper error handling and logging
- Idempotent failover operations

### NFR4: Backward Compatibility
- Existing deployments continue to work
- No breaking changes to Terraform variables
- Migration path documented
- Feature flag for gradual rollout

## Constraints

- **Management EIPs MUST remain statically associated**
- Must maintain backward compatibility
- No FortiGate firmware upgrade required
- Must work with pre-created ENIs
- EIP failover only for OUTSIDE interfaces

## Success Metrics

- EIP failover time: <60 seconds (target: 30-45 seconds)
- Failover success rate: >99.9%
- Packet loss during planned failover: 0%
- Packet loss during unplanned failover: <1%
- **Management access uptime: 100%**
- IAM security audit: Pass

## References

- [FortiGate AWS HA Documentation](https://docs.fortinet.com/document/fortigate-public-cloud/7.0.0/aws-administration-guide/161167/ha-for-fortigate-on-aws)
- [AWS EIP Documentation](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/elastic-ip-addresses-eip.html)
- [FortiGate AWS SDN Connector](https://docs.fortinet.com/document/fortigate/7.0.0/administration-guide/866905/aws-sdn-connector)
