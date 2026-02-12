# FortiGate HA EIP Failover - Implementation Tasks

## Task Overview

This document outlines the implementation tasks for FortiGate AWS SDN connector-based HA failover.

**Status Legend:**
- `[ ]` Not Started
- `[~]` In Progress
- `[x]` Completed

## Phase 1: IAM Infrastructure

### Task 1.1: Create IAM Role Resource
- [ ] Add `aws_iam_role` resource to `terraform/modules/fortigate-ha/main.tf`
- [ ] Configure trust relationship with EC2 service
- [ ] Add conditional creation based on `enable_eip_failover` variable
- [ ] Add proper tags (Name, Environment, Owner, ManagedBy)
- [ ] Test role creation with `terraform plan`

**Files to Modify:**
- `terraform/modules/fortigate-ha/main.tf`

**Acceptance Criteria:**
- IAM role created successfully
- Trust relationship configured correctly
- Conditional creation works
- Tags applied properly

### Task 1.2: Create IAM Policy
- [ ] Add `aws_iam_role_policy` resource with inline policy
- [ ] Add Describe permissions (ec2:Describe*)
- [ ] Add EIP management permissions (AssociateAddress, DisassociateAddress)
- [ ] Add tag-based condition (ManagedBy=FortiGate-HA)
- [ ] Validate policy JSON syntax

**Files to Modify:**
- `terraform/modules/fortigate-ha/main.tf`

**Acceptance Criteria:**
- Policy attached to role
- Permissions scoped correctly
- Tag condition works
- JSON syntax valid

### Task 1.3: Create IAM Instance Profile
- [ ] Add `aws_iam_instance_profile` resource
- [ ] Link to IAM role
- [ ] Add conditional creation
- [ ] Add proper tags

**Files to Modify:**
- `terraform/modules/fortigate-ha/main.tf`

**Acceptance Criteria:**
- Instance profile created
- Linked to correct role
- Conditional creation works

### Task 1.4: Attach Instance Profile to FortiGate Instances
- [ ] Update `aws_instance.fortigate_primary` resource
- [ ] Update `aws_instance.fortigate_backup` resource
- [ ] Add `iam_instance_profile` parameter
- [ ] Make conditional based on `enable_eip_failover`

**Files to Modify:**
- `terraform/modules/fortigate-ha/main.tf`

**Acceptance Criteria:**
- Instance profile attached to both instances
- Conditional attachment works
- Instances can assume role

### Task 1.5: Add IAM Variables
- [ ] Add `enable_eip_failover` variable to `terraform/modules/fortigate-ha/variables.tf`
- [ ] Set default value to `true`
- [ ] Add description
- [ ] Add validation if needed

**Files to Modify:**
- `terraform/modules/fortigate-ha/variables.tf`
- `terraform/variables.tf` (root level)

**Acceptance Criteria:**
- Variable defined correctly
- Default value set
- Description clear

### Task 1.6: Add IAM Outputs
- [ ] Add `iam_role_arn` output
- [ ] Add `iam_instance_profile_name` output
- [ ] Add `eip_failover_enabled` output
- [ ] Make conditional based on `enable_eip_failover`

**Files to Modify:**
- `terraform/modules/fortigate-ha/outputs.tf`
- `terraform/outputs.tf` (root level)

**Acceptance Criteria:**
- Outputs defined correctly
- Conditional output works
- Values accessible

## Phase 2: Remove Static EIP Associations

### Task 2.1: Remove Primary OUTSIDE EIP Association
- [ ] Remove `aws_eip_association.primary_outside` resource
- [ ] Keep `aws_eip.primary_outside` allocation resource
- [ ] Update comments to explain why no association

**Files to Modify:**
- `terraform/modules/fortigate-ha/main.tf`

**Acceptance Criteria:**
- Association resource removed
- Allocation resource remains
- EIP allocated but not associated

### Task 2.2: Remove Backup OUTSIDE EIP Association
- [ ] Remove `aws_eip_association.backup_outside` resource
- [ ] Keep `aws_eip.backup_outside` allocation resource
- [ ] Update comments to explain why no association

**Files to Modify:**
- `terraform/modules/fortigate-ha/main.tf`

**Acceptance Criteria:**
- Association resource removed
- Allocation resource remains
- EIP allocated but not associated

### Task 2.3: Update EIP Tags
- [ ] Add `ManagedBy = "FortiGate-HA"` tag to primary OUTSIDE EIP
- [ ] Add `ManagedBy = "FortiGate-HA"` tag to backup OUTSIDE EIP
- [ ] Verify management EIPs do NOT have this tag

**Files to Modify:**
- `terraform/modules/fortigate-ha/main.tf`

**Acceptance Criteria:**
- OUTSIDE EIPs tagged correctly
- Management EIPs unchanged
- Tags visible in AWS console

### Task 2.4: Update EIP Outputs
- [ ] Update outputs to reflect unassociated EIPs
- [ ] Add EIP allocation ID outputs
- [ ] Update output descriptions

**Files to Modify:**
- `terraform/modules/fortigate-ha/outputs.tf`

**Acceptance Criteria:**
- Outputs show allocation IDs
- Descriptions accurate
- No association IDs output

## Phase 3: FortiGate Configuration Templates

### Task 3.1: Add AWS SDN Connector to Primary Template
- [ ] Add `config system sdn-connector` section
- [ ] Set type to `aws`
- [ ] Enable `use-metadata-iam`
- [ ] Template `region` variable
- [ ] Set update-interval to 60
- [ ] Enable status

**Files to Modify:**
- `terraform/modules/fortigate-ha/templates/fortigate-primary-config.tpl`

**Acceptance Criteria:**
- SDN connector configured
- IAM role used for credentials
- Region templated correctly
- Syntax valid

### Task 3.2: Add AWS SDN Connector to Backup Template
- [ ] Add `config system sdn-connector` section (same as primary)
- [ ] Ensure configuration identical to primary

**Files to Modify:**
- `terraform/modules/fortigate-ha/templates/fortigate-backup-config.tpl`

**Acceptance Criteria:**
- SDN connector configured
- Configuration matches primary
- Syntax valid

### Task 3.3: Add Template Variables
- [ ] Add `aws_region` to template context
- [ ] Add `primary_outside_eip_id` to template context
- [ ] Add `backup_outside_eip_id` to template context
- [ ] Add `ha_priority` to template context

**Files to Modify:**
- `terraform/modules/fortigate-ha/main.tf` (user_data sections)

**Acceptance Criteria:**
- Variables passed to templates
- Values correct
- Templates render successfully

### Task 3.4: Add AWS Region Variable
- [ ] Add `aws_region` variable to module variables
- [ ] Add to root variables
- [ ] Set default or make required
- [ ] Add description

**Files to Modify:**
- `terraform/modules/fortigate-ha/variables.tf`
- `terraform/variables.tf`

**Acceptance Criteria:**
- Variable defined
- Description clear
- Default value appropriate

### Task 3.5: Update HA Configuration
- [ ] Verify HA priority in templates (primary: 200, backup: 100)
- [ ] Ensure interface monitoring enabled
- [ ] Verify session-pickup enabled
- [ ] Check HA management interface configuration

**Files to Modify:**
- `terraform/modules/fortigate-ha/templates/fortigate-primary-config.tpl`
- `terraform/modules/fortigate-ha/templates/fortigate-backup-config.tpl`

**Acceptance Criteria:**
- HA priorities correct
- Monitoring enabled
- Session pickup enabled
- Configuration valid

## Phase 4: Testing and Validation

### Task 4.1: Create Validation Script
- [ ] Create script to check IAM role permissions
- [ ] Add check for instance profile attachment
- [ ] Add check for EIP tags
- [ ] Add check for EIP association status
- [ ] Add check for SDN connector status

**Files to Create:**
- `fortigate-aws-ha-deployment/validate-eip-failover.sh`

**Acceptance Criteria:**
- Script checks all components
- Clear output messages
- Exit codes indicate success/failure

### Task 4.2: Create Test Plan Document
- [ ] Document primary failure scenario
- [ ] Document manual failover scenario
- [ ] Document failback scenario
- [ ] Document expected results
- [ ] Document timing expectations

**Files to Create:**
- `fortigate-aws-ha-deployment/EIP-FAILOVER-TEST-PLAN.md`

**Acceptance Criteria:**
- All scenarios documented
- Expected results clear
- Timing benchmarks defined

### Task 4.3: Test Primary Failure Scenario
- [ ] Deploy test environment
- [ ] Stop primary instance
- [ ] Monitor EIP association
- [ ] Measure failover time
- [ ] Verify traffic restoration
- [ ] Document results

**Acceptance Criteria:**
- Failover completes <60 seconds
- EIP moves to backup
- Traffic restored
- Management access maintained

### Task 4.4: Test Manual Failover
- [ ] Trigger manual failover via FortiGate CLI
- [ ] Monitor EIP association
- [ ] Measure failover time
- [ ] Verify traffic restoration
- [ ] Document results

**Acceptance Criteria:**
- Manual failover works
- EIP moves correctly
- Timing acceptable
- No errors

### Task 4.5: Test Failback
- [ ] Restart primary instance
- [ ] Wait for HA sync
- [ ] Trigger failback
- [ ] Monitor EIP association
- [ ] Verify traffic restoration

**Acceptance Criteria:**
- Failback works correctly
- EIP returns to primary
- No service disruption
- Management access maintained

## Phase 5: Documentation

### Task 5.1: Update README
- [ ] Add EIP failover architecture section
- [ ] Add IAM requirements section
- [ ] Update deployment instructions
- [ ] Add troubleshooting section

**Files to Modify:**
- `fortigate-aws-ha-deployment/README.md`

**Acceptance Criteria:**
- Architecture explained clearly
- IAM requirements documented
- Instructions updated
- Troubleshooting helpful

### Task 5.2: Create Deployment Guide
- [ ] Document step-by-step deployment
- [ ] Include EIP failover verification steps
- [ ] Add screenshots if helpful
- [ ] Include common issues and solutions

**Files to Create:**
- `fortigate-aws-ha-deployment/EIP-FAILOVER-DEPLOYMENT-GUIDE.md`

**Acceptance Criteria:**
- Steps clear and complete
- Verification steps included
- Common issues covered

### Task 5.3: Create Architecture Diagram
- [ ] Create high-level architecture diagram
- [ ] Create failover sequence diagram
- [ ] Show EIP movement during failover
- [ ] Show management EIP (static)

**Files to Create:**
- `fortigate-aws-ha-deployment/diagrams/eip-failover-architecture.png`
- `fortigate-aws-ha-deployment/diagrams/eip-failover-sequence.png`

**Acceptance Criteria:**
- Diagrams clear and accurate
- Shows all components
- Failover flow visible

### Task 5.4: Create Troubleshooting Guide
- [ ] Document common issues
- [ ] Add solutions for each issue
- [ ] Include diagnostic commands
- [ ] Add log locations

**Files to Create:**
- `fortigate-aws-ha-deployment/EIP-FAILOVER-TROUBLESHOOTING.md`

**Acceptance Criteria:**
- Common issues covered
- Solutions clear
- Diagnostic commands included

### Task 5.5: Create Migration Guide
- [ ] Document migration from static associations
- [ ] Include rollback procedure
- [ ] Add pre-migration checklist
- [ ] Add post-migration validation

**Files to Create:**
- `fortigate-aws-ha-deployment/EIP-FAILOVER-MIGRATION-GUIDE.md`

**Acceptance Criteria:**
- Migration steps clear
- Rollback documented
- Checklists complete

## Phase 6: Integration and Deployment

### Task 6.1: Update deploy.py
- [ ] Add support for `enable_eip_failover` variable
- [ ] Add prompts for EIP failover configuration
- [ ] Update terraform.tfvars generation
- [ ] Add validation for IAM permissions

**Files to Modify:**
- `fortigate-aws-ha-deployment/deploy.py`

**Acceptance Criteria:**
- Variable supported
- Prompts clear
- tfvars generated correctly

### Task 6.2: Run Terraform Plan
- [ ] Run `terraform plan` in test environment
- [ ] Verify IAM resources will be created
- [ ] Verify EIP associations will be removed
- [ ] Verify no unexpected changes

**Acceptance Criteria:**
- Plan shows expected changes
- No errors
- Resources correct

### Task 6.3: Deploy to Test Environment
- [ ] Run `terraform apply`
- [ ] Verify IAM role created
- [ ] Verify instance profiles attached
- [ ] Verify EIPs allocated but not associated
- [ ] Verify FortiGate instances running

**Acceptance Criteria:**
- Deployment successful
- All resources created
- No errors

### Task 6.4: Verify SDN Connector
- [ ] SSH to primary FortiGate
- [ ] Check SDN connector status
- [ ] Verify IAM role credentials working
- [ ] Check for errors in logs

**Acceptance Criteria:**
- SDN connector enabled
- IAM credentials working
- No errors

### Task 6.5: Production Deployment
- [ ] Review security audit
- [ ] Get approval from stakeholders
- [ ] Deploy to production
- [ ] Monitor for issues
- [ ] Document deployment

**Acceptance Criteria:**
- Security approved
- Deployment successful
- Monitoring in place
- Documentation complete

## Summary

**Total Tasks:** 35
**Completed:** 0
**In Progress:** 0
**Not Started:** 35

**Estimated Timeline:** 3 weeks
- Phase 1: 3 days
- Phase 2: 2 days
- Phase 3: 3 days
- Phase 4: 4 days
- Phase 5: 3 days
- Phase 6: 2 days

**Dependencies:**
- Phase 2 depends on Phase 1 (IAM must exist before removing associations)
- Phase 3 depends on Phase 1 (templates need IAM role)
- Phase 4 depends on Phases 1-3 (testing requires complete implementation)
- Phase 5 can run in parallel with Phase 4
- Phase 6 depends on all previous phases
