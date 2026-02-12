# FortiGate HA EIP Failover - Specification

## Overview

This specification defines the implementation of FortiGate AWS SDN connector-based HA failover for automatic Elastic IP (EIP) migration during failover events.

**Key Principle:** OUTSIDE EIPs failover automatically. Management EIPs remain statically associated for continuous administrative access.

## Specification Documents

### 1. Requirements Specification
**File:** `fortigate-ha-eip-failover-requirements.md`

Defines:
- User stories and acceptance criteria
- Functional requirements (FR1-FR6)
- Non-functional requirements (NFR1-NFR5)
- Constraints and success metrics

**Status:** Complete

### 2. Technical Design
**File:** `fortigate-ha-eip-failover-design.md`

Defines:
- Architecture diagrams
- Component design (IAM, EIP, FortiGate config)
- Data flow and failover sequence
- Security considerations
- Testing strategy

**Status:** Complete

### 3. Implementation Tasks
**File:** `fortigate-ha-eip-failover-tasks.md`

Defines:
- 35 implementation tasks across 6 phases
- Task dependencies and timeline
- Acceptance criteria for each task
- Files to modify

**Status:** Complete

## Quick Reference

### What Changes?

**OUTSIDE EIPs (for internet traffic):**
- ✅ Allocated by create-enis.py (NO association)
- ✅ Tagged with `ManagedBy=FortiGate-HA`
- ✅ Managed by FortiGate HA for automatic failover
- ❌ NO static Terraform associations

**Management EIPs (for admin access):**
- ✅ Allocated by create-enis.py
- ✅ Associated with management ENIs
- ✅ Static associations (NO failover)
- ✅ Always accessible on both instances

### Implementation Phases

1. **Phase 1: IAM Infrastructure** (3 days)
   - Create IAM role with EIP permissions
   - Create IAM instance profile
   - Attach to FortiGate instances

2. **Phase 2: Remove Static Associations** (2 days)
   - Remove `aws_eip_association` resources
   - Update EIP tags
   - Update outputs

3. **Phase 3: FortiGate Configuration** (3 days)
   - Add AWS SDN connector to templates
   - Update HA configuration
   - Add template variables

4. **Phase 4: Testing and Validation** (4 days)
   - Create validation scripts
   - Test failover scenarios
   - Measure performance

5. **Phase 5: Documentation** (3 days)
   - Update README
   - Create deployment guide
   - Create troubleshooting guide

6. **Phase 6: Integration and Deployment** (2 days)
   - Update deploy.py
   - Deploy to test environment
   - Deploy to production

**Total Timeline:** 3 weeks

### Key Components

**IAM Role:**
- Name: `fortigate-ha-eip-management-role`
- Permissions: Describe EC2 resources, Associate/Disassociate EIPs
- Condition: Only EIPs tagged with `ManagedBy=FortiGate-HA`

**AWS SDN Connector:**
- Type: `aws`
- Credentials: IAM instance profile (`use-metadata-iam`)
- Update interval: 60 seconds
- Region: Templated from Terraform variable

**EIP Failover:**
- Automatic during HA failover
- Timing: 30-60 seconds
- No manual intervention required
- Management access maintained

### Success Metrics

- EIP failover time: <60 seconds (target: 30-45 seconds)
- Failover success rate: >99.9%
- Packet loss during planned failover: 0%
- Packet loss during unplanned failover: <1%
- Management access uptime: 100%

## Getting Started

### For Implementers

1. Read `fortigate-ha-eip-failover-requirements.md` for requirements
2. Review `fortigate-ha-eip-failover-design.md` for technical design
3. Follow `fortigate-ha-eip-failover-tasks.md` for implementation

### For Reviewers

1. Review requirements for completeness
2. Validate technical design against requirements
3. Check implementation tasks for feasibility
4. Approve before implementation begins

### For Operators

1. Wait for implementation completion
2. Review deployment guide (Phase 5)
3. Follow validation procedures (Phase 4)
4. Monitor failover performance

## References

- [FortiGate AWS HA Documentation](https://docs.fortinet.com/document/fortigate-public-cloud/7.0.0/aws-administration-guide/161167/ha-for-fortigate-on-aws)
- [AWS EIP Documentation](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/elastic-ip-addresses-eip.html)
- [FortiGate AWS SDN Connector](https://docs.fortinet.com/document/fortigate/7.0.0/administration-guide/866905/aws-sdn-connector)
- [AWS IAM Best Practices](https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html)

## Status

- **Requirements:** ✅ Complete
- **Design:** ✅ Complete
- **Tasks:** ✅ Complete
- **Implementation:** ⏳ Not Started
- **Testing:** ⏳ Not Started
- **Documentation:** ⏳ Not Started
- **Deployment:** ⏳ Not Started

## Contact

For questions or clarifications, contact the project team.
