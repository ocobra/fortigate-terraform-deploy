# FortiGate HA EIP Failover - Technical Design

## Architecture Overview

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         AWS VPC                                  │
│                                                                   │
│  ┌──────────────────┐                  ┌──────────────────┐    │
│  │  Primary FGT     │                  │  Backup FGT      │    │
│  │  ┌────────────┐  │                  │  ┌────────────┐  │    │
│  │  │ IAM Role   │  │                  │  │ IAM Role   │  │    │
│  │  │ (EIP Mgmt) │  │                  │  │ (EIP Mgmt) │  │    │
│  │  └────────────┘  │                  │  └────────────┘  │    │
│  │  ┌────────────┐  │                  │  ┌────────────┐  │    │
│  │  │ AWS SDN    │  │                  │  │ AWS SDN    │  │    │
│  │  │ Connector  │  │                  │  │ Connector  │  │    │
│  │  └────────────┘  │                  │  └────────────┘  │    │
│  │                   │                  │                   │    │
│  │  port1 (OUTSIDE)  │◄────HA Sync────►│  port1 (OUTSIDE)  │    │
│  │  port2 (INSIDE)   │                  │  port2 (INSIDE)   │    │
│  │  port3 (HA)       │                  │  port3 (HA)       │    │
│  │  port4 (MGMT)     │                  │  port4 (MGMT)     │    │
│  └──────────────────┘                  └──────────────────┘    │
│         │                                        │               │
│         │                                        │               │
│  ┌──────▼────────┐                      ┌───────▼────────┐     │
│  │ EIP (OUTSIDE) │                      │ EIP (OUTSIDE)  │     │
│  │ NOT Associated│                      │ NOT Associated │     │
│  │ ManagedBy:    │                      │ ManagedBy:     │     │
│  │ FortiGate-HA  │                      │ FortiGate-HA   │     │
│  └───────────────┘                      └────────────────┘     │
│                                                                   │
│  ┌───────────────┐                      ┌────────────────┐     │
│  │ EIP (MGMT)    │                      │ EIP (MGMT)     │     │
│  │ ASSOCIATED    │                      │ ASSOCIATED     │     │
│  │ Static        │                      │ Static         │     │
│  └───────────────┘                      └────────────────┘     │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

### Failover Sequence

```
1. Primary Failure Detected
   ├─> Backup detects primary down (HA heartbeat)
   ├─> Backup becomes active
   └─> Backup priority increases

2. AWS SDN Connector Action
   ├─> SDN connector detects role change
   ├─> Queries AWS for EIPs with tag "ManagedBy=FortiGate-HA"
   ├─> Identifies OUTSIDE EIPs
   └─> Uses IAM role to associate EIPs

3. EIP Association
   ├─> Disassociate EIP from primary OUTSIDE ENI
   ├─> Associate EIP with backup OUTSIDE ENI
   └─> Update routing

4. Traffic Restoration
   ├─> Internet traffic flows to backup
   ├─> Sessions restored (if session-pickup enabled)
   └─> Normal operation resumes

Time: 30-60 seconds
```

## Component Design

### 1. IAM Role and Policy

#### IAM Role Resource
```hcl
resource "aws_iam_role" "fortigate_ha_eip_management" {
  count = var.enable_eip_failover ? 1 : 0
  name  = "fortigate-ha-eip-management-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "ec2.amazonaws.com"
      }
    }]
  })

  tags = {
    Name        = "fortigate-ha-eip-management-role"
    Environment = var.environment
    Owner       = var.owner_tag
    ManagedBy   = "Terraform"
  }
}
```

#### IAM Policy
```hcl
resource "aws_iam_role_policy" "fortigate_eip_management" {
  count = var.enable_eip_failover ? 1 : 0
  name  = "fortigate-eip-management-policy"
  role  = aws_iam_role.fortigate_ha_eip_management[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "FortiGateDescribeResources"
        Effect = "Allow"
        Action = [
          "ec2:DescribeInstances",
          "ec2:DescribeNetworkInterfaces",
          "ec2:DescribeAddresses",
          "ec2:DescribeVpcs",
          "ec2:DescribeSubnets",
          "ec2:DescribeRouteTables"
        ]
        Resource = "*"
      },
      {
        Sid    = "FortiGateManageEIPs"
        Effect = "Allow"
        Action = [
          "ec2:AssociateAddress",
          "ec2:DisassociateAddress"
        ]
        Resource = "*"
        Condition = {
          StringEquals = {
            "ec2:ResourceTag/ManagedBy" = "FortiGate-HA"
          }
        }
      }
    ]
  })
}
```

#### IAM Instance Profile
```hcl
resource "aws_iam_instance_profile" "fortigate_ha" {
  count = var.enable_eip_failover ? 1 : 0
  name  = "fortigate-ha-instance-profile"
  role  = aws_iam_role.fortigate_ha_eip_management[0].name

  tags = {
    Name        = "fortigate-ha-instance-profile"
    Environment = var.environment
    Owner       = var.owner_tag
    ManagedBy   = "Terraform"
  }
}
```

### 2. FortiGate Instance Configuration

#### Attach IAM Instance Profile
```hcl
resource "aws_instance" "fortigate_primary" {
  ami                     = var.fortigate_ami_id
  instance_type          = var.instance_type
  key_name               = var.key_pair_name
  iam_instance_profile   = var.enable_eip_failover ? aws_iam_instance_profile.fortigate_ha[0].name : null
  # ... rest of configuration
}

resource "aws_instance" "fortigate_backup" {
  ami                     = var.fortigate_ami_id
  instance_type          = var.instance_type
  key_name               = var.key_pair_name
  iam_instance_profile   = var.enable_eip_failover ? aws_iam_instance_profile.fortigate_ha[0].name : null
  # ... rest of configuration
}
```

### 3. EIP Resources (Modified)

#### Remove Static Associations
```hcl
# REMOVE THESE RESOURCES:
# resource "aws_eip_association" "primary_outside" { ... }
# resource "aws_eip_association" "backup_outside" { ... }

# KEEP THESE (allocation only):
resource "aws_eip" "primary_outside" {
  count  = var.allocate_eips && var.primary_outside_eip_id == "" ? 1 : 0
  domain = "vpc"
  
  tags = {
    Name        = "fortigate-primary-outside-eip"
    Environment = var.environment
    Owner       = var.owner_tag
    FortiGateRole = "primary"
    Interface   = "outside"
    ManagedBy   = "FortiGate-HA"  # CRITICAL TAG
  }
}

resource "aws_eip" "backup_outside" {
  count  = var.allocate_eips && var.backup_outside_eip_id == "" ? 1 : 0
  domain = "vpc"
  
  tags = {
    Name        = "fortigate-backup-outside-eip"
    Environment = var.environment
    Owner       = var.owner_tag
    FortiGateRole = "backup"
    Interface   = "outside"
    ManagedBy   = "FortiGate-HA"  # CRITICAL TAG
  }
}
```

### 4. FortiGate Configuration Templates

#### AWS SDN Connector Configuration
```
config system sdn-connector
    edit "aws-sdn"
        set type aws
        set use-metadata-iam enable
        set region ${aws_region}
        set update-interval 60
        set status enable
    next
end
```

#### HA Configuration (Enhanced)
```
config system ha
    set group-name "fortigate-ha-group"
    set mode a-p
    set hbdev "port3" 50
    set session-pickup enable
    set session-pickup-connectionless enable
    set ha-mgmt-status enable
    config ha-mgmt-interfaces
        edit 1
            set interface "port4"
            set gateway ${default_gateway}
        next
    end
    set override disable
    set priority ${ha_priority}
    set monitor "port1" "port2"
    set password "${ha_password}"
end
```

## Data Flow

### Normal Operation (Primary Active)
```
Internet → EIP (on Primary OUTSIDE) → Primary FortiGate → Inside Network
```

### During Failover
```
1. Primary fails
2. Backup detects failure (HA heartbeat timeout)
3. Backup becomes active
4. AWS SDN Connector on Backup:
   - Queries AWS for EIPs with ManagedBy=FortiGate-HA
   - Finds Primary OUTSIDE EIP
   - Disassociates from Primary OUTSIDE ENI
   - Associates with Backup OUTSIDE ENI
5. Internet → EIP (now on Backup OUTSIDE) → Backup FortiGate → Inside Network
```

### Management Access (Always Available)
```
Internet → Management EIP (Primary) → Primary FortiGate MGMT
Internet → Management EIP (Backup) → Backup FortiGate MGMT
(No failover - static associations maintained)
```

## Configuration Variables

### New Terraform Variables
```hcl
variable "enable_eip_failover" {
  description = "Enable FortiGate-managed EIP failover for OUTSIDE interfaces"
  type        = bool
  default     = true
}

variable "aws_region" {
  description = "AWS region for FortiGate SDN connector"
  type        = string
}
```

### Template Variables
```hcl
user_data = base64encode(templatefile("${path.module}/templates/fortigate-primary-config.tpl", {
  # Existing variables...
  aws_region              = var.aws_region
  primary_outside_eip_id  = var.primary_outside_eip_id
  backup_outside_eip_id   = var.backup_outside_eip_id
  ha_priority             = 200
}))
```

## Outputs

### New Terraform Outputs
```hcl
output "iam_role_arn" {
  description = "ARN of IAM role for FortiGate EIP management"
  value       = var.enable_eip_failover ? aws_iam_role.fortigate_ha_eip_management[0].arn : null
}

output "iam_instance_profile_name" {
  description = "Name of IAM instance profile attached to FortiGate instances"
  value       = var.enable_eip_failover ? aws_iam_instance_profile.fortigate_ha[0].name : null
}

output "eip_failover_enabled" {
  description = "Whether EIP failover is enabled"
  value       = var.enable_eip_failover
}

output "primary_outside_eip_allocation_id" {
  description = "Allocation ID of primary OUTSIDE EIP (for FortiGate config)"
  value       = var.allocate_eips ? (var.primary_outside_eip_id != "" ? var.primary_outside_eip_id : aws_eip.primary_outside[0].id) : null
}

output "backup_outside_eip_allocation_id" {
  description = "Allocation ID of backup OUTSIDE EIP (for FortiGate config)"
  value       = var.allocate_eips ? (var.backup_outside_eip_id != "" ? var.backup_outside_eip_id : aws_eip.backup_outside[0].id) : null
}
```

## Security Considerations

### IAM Permissions Scope
- Describe operations: No resource restrictions (read-only)
- EIP operations: Restricted to resources tagged with `ManagedBy=FortiGate-HA`
- No permissions for EIP allocation/release
- No permissions for instance termination

### Tag-Based Access Control
- Only EIPs with `ManagedBy=FortiGate-HA` can be managed
- Management EIPs lack this tag (cannot be moved)
- Prevents accidental association with wrong resources

### Credential Management
- IAM instance profile (no static credentials)
- Automatic credential rotation by AWS
- Credentials never exposed in configuration

## Testing Strategy

### Unit Tests
- IAM role creation
- IAM policy validation
- Instance profile attachment
- EIP tagging

### Integration Tests
- Primary failure scenario
- Manual failover trigger
- EIP association verification
- Failover timing measurement

### Validation Checks
- IAM role permissions
- SDN connector status
- EIP association status
- Management access continuity

## Rollback Plan

### If Failover Fails
1. Check IAM role attachment
2. Verify SDN connector status
3. Check EIP tags
4. Manual EIP association if needed
5. Review FortiGate logs

### Reverting to Static Associations
1. Set `enable_eip_failover = false`
2. Run `terraform apply`
3. Static associations recreated
4. IAM resources removed

## Performance Considerations

### Failover Timing
- HA detection: 10-15 seconds
- SDN connector update: 5-10 seconds
- EIP association: 5-10 seconds
- Route propagation: 5-10 seconds
- **Total: 30-45 seconds (target)**

### Optimization
- SDN connector update interval: 60 seconds (balance between responsiveness and API calls)
- HA heartbeat interval: 10 seconds
- Interface monitoring: Enabled for fast detection

## Monitoring and Logging

### CloudWatch Metrics
- EIP association changes
- IAM role usage
- FortiGate HA status

### FortiGate Logs
- HA state changes
- SDN connector activity
- EIP association events

### Alerts
- Failover events
- SDN connector failures
- IAM permission errors
