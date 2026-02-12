# FortiGate AWS HA Deployment - Complete Parameters Guide

## Overview

This guide provides comprehensive documentation for all input parameters required by the FortiGate AWS HA deployment system. Parameters can be provided through:

1. **Interactive CLI** (`deploy.py`)
2. **Configuration File** (YAML/JSON)
3. **Terraform Variables** (`terraform.tfvars`)
4. **Command-Line Options**

## Table of Contents

- [AWS Configuration](#aws-configuration)
- [Network Configuration](#network-configuration)
- [ENI Configuration](#eni-configuration)
- [Elastic IP Configuration](#elastic-ip-configuration)
- [FortiGate Configuration](#fortigate-configuration)
- [Transit Gateway Configuration](#transit-gateway-configuration)
- [Monitoring Configuration](#monitoring-configuration)
- [Backend Configuration](#backend-configuration)
- [Command-Line Options](#command-line-options)
- [Configuration File Format](#configuration-file-format)

---

## AWS Configuration

### aws_region
- **Type**: String
- **Required**: Yes
- **Default**: `us-east-1`
- **Description**: AWS region where FortiGate instances will be deployed
- **Example**: `us-east-1`, `us-west-2`, `eu-west-1`
- **CLI Prompt**: "AWS Region"
- **Terraform Variable**: `aws_region`

### aws_profile
- **Type**: String
- **Required**: No
- **Default**: `""` (uses default credentials)
- **Description**: AWS CLI profile name for authentication
- **Example**: `default`, `production`, `fortigate-deploy`
- **CLI Prompt**: "AWS Profile name" (if "Use AWS profile?" is Yes)
- **Terraform Variable**: `aws_profile`

### environment
- **Type**: String
- **Required**: No
- **Default**: `prod`
- **Description**: Environment name for resource tagging
- **Example**: `prod`, `staging`, `dev`, `test`
- **CLI Prompt**: "Environment"
- **Terraform Variable**: `environment`

### owner_tag
- **Type**: String
- **Required**: No
- **Default**: `NetworkTeam`
- **Description**: Owner tag for resource identification and cost allocation
- **Example**: `NetworkTeam`, `SecurityTeam`, `john.doe@company.com`
- **CLI Prompt**: "Owner tag"
- **Terraform Variable**: `owner_tag`

---

## Network Configuration

### vpc_id
- **Type**: String (VPC ID format)
- **Required**: Yes
- **Description**: Pre-existing VPC ID where FortiGate instances will be deployed
- **Format**: `vpc-[a-z0-9]{8,17}`
- **Example**: `vpc-0e16490e6ab8422fb`
- **CLI Prompt**: "VPC ID (pre-assigned)"
- **Terraform Variable**: `vpc_id`
- **Validation**: Must be a valid AWS VPC identifier

### availability_zones
- **Type**: List of Strings
- **Required**: Yes
- **Minimum**: 2 zones
- **Description**: Availability zones for HA deployment (primary and backup)
- **Example**: `["us-east-1a", "us-east-1b"]`
- **CLI Prompt**: "Primary AZ" and "Backup AZ"
- **Terraform Variable**: `availability_zones`
- **Validation**: At least 2 availability zones required for HA

### Subnet IDs (Primary FortiGate)

#### outside_subnet_primary
- **Type**: String (Subnet ID format)
- **Required**: Yes
- **Description**: Outside (WAN) subnet ID for primary FortiGate
- **Format**: `subnet-[a-z0-9]{8,17}`
- **Example**: `subnet-0a1b2c3d4e5f6g7h8`
- **CLI Prompt**: "Primary FortiGate subnets: Outside subnet ID"
- **Terraform Variable**: `outside_subnet_primary`

#### inside_subnet_primary
- **Type**: String (Subnet ID format)
- **Required**: Yes
- **Description**: Inside (LAN) subnet ID for primary FortiGate
- **Format**: `subnet-[a-z0-9]{8,17}`
- **Example**: `subnet-1a2b3c4d5e6f7g8h9`
- **CLI Prompt**: "Primary FortiGate subnets: Inside subnet ID"
- **Terraform Variable**: `inside_subnet_primary`

#### ha_subnet_primary
- **Type**: String (Subnet ID format)
- **Required**: Yes
- **Description**: HA heartbeat subnet ID for primary FortiGate
- **Format**: `subnet-[a-z0-9]{8,17}`
- **Example**: `subnet-2a3b4c5d6e7f8g9h0`
- **CLI Prompt**: "Primary FortiGate subnets: HA subnet ID"
- **Terraform Variable**: `ha_subnet_primary`

#### mgmt_subnet_primary
- **Type**: String (Subnet ID format)
- **Required**: Yes
- **Description**: Management subnet ID for primary FortiGate
- **Format**: `subnet-[a-z0-9]{8,17}`
- **Example**: `subnet-3a4b5c6d7e8f9g0h1`
- **CLI Prompt**: "Primary FortiGate subnets: Management subnet ID"
- **Terraform Variable**: `mgmt_subnet_primary`

### Subnet IDs (Backup FortiGate)

#### outside_subnet_backup
- **Type**: String (Subnet ID format)
- **Required**: Yes
- **Description**: Outside (WAN) subnet ID for backup FortiGate
- **Format**: `subnet-[a-z0-9]{8,17}`
- **Example**: `subnet-4a5b6c7d8e9f0g1h2`
- **CLI Prompt**: "Backup FortiGate subnets: Outside subnet ID"
- **Terraform Variable**: `outside_subnet_backup`

#### inside_subnet_backup
- **Type**: String (Subnet ID format)
- **Required**: Yes
- **Description**: Inside (LAN) subnet ID for backup FortiGate
- **Format**: `subnet-[a-z0-9]{8,17}`
- **Example**: `subnet-5a6b7c8d9e0f1g2h3`
- **CLI Prompt**: "Backup FortiGate subnets: Inside subnet ID"
- **Terraform Variable**: `inside_subnet_backup`

#### ha_subnet_backup
- **Type**: String (Subnet ID format)
- **Required**: Yes
- **Description**: HA heartbeat subnet ID for backup FortiGate
- **Format**: `subnet-[a-z0-9]{8,17}`
- **Example**: `subnet-6a7b8c9d0e1f2g3h4`
- **CLI Prompt**: "Backup FortiGate subnets: HA subnet ID"
- **Terraform Variable**: `ha_subnet_backup`

#### mgmt_subnet_backup
- **Type**: String (Subnet ID format)
- **Required**: Yes
- **Description**: Management subnet ID for backup FortiGate
- **Format**: `subnet-[a-z0-9]{8,17}`
- **Example**: `subnet-7a8b9c0d1e2f3g4h5`
- **CLI Prompt**: "Backup FortiGate subnets: Management subnet ID"
- **Terraform Variable**: `mgmt_subnet_backup`

### mgmt_access_cidrs
- **Type**: List of Strings (CIDR format)
- **Required**: Yes
- **Default**: `["10.0.0.0/8"]`
- **Description**: CIDR blocks allowed for management access to FortiGate instances
- **Example**: `["10.0.0.0/8", "192.168.1.0/24"]`
- **CLI Prompt**: "Management access CIDRs (comma-separated)"
- **Terraform Variable**: `mgmt_access_cidrs`
- **Validation**: Must be valid CIDR blocks

---

## ENI Configuration

All ENIs must be pre-created by the network team before deployment. Use `create-enis.py` script to create them.

### Primary FortiGate ENIs

#### primary_outside_eni_id
- **Type**: String (ENI ID format)
- **Required**: Yes
- **Description**: Pre-created ENI ID for primary FortiGate outside interface
- **Format**: `eni-[a-z0-9]{8,17}`
- **Example**: `eni-0a1b2c3d4e5f6g7h8`
- **CLI Prompt**: "Primary FortiGate ENIs: Outside ENI ID"
- **Terraform Variable**: `primary_outside_eni_id`

#### primary_inside_eni_id
- **Type**: String (ENI ID format)
- **Required**: Yes
- **Description**: Pre-created ENI ID for primary FortiGate inside interface
- **Format**: `eni-[a-z0-9]{8,17}`
- **Example**: `eni-1a2b3c4d5e6f7g8h9`
- **CLI Prompt**: "Primary FortiGate ENIs: Inside ENI ID"
- **Terraform Variable**: `primary_inside_eni_id`

#### primary_ha_eni_id
- **Type**: String (ENI ID format)
- **Required**: Yes
- **Description**: Pre-created ENI ID for primary FortiGate HA interface
- **Format**: `eni-[a-z0-9]{8,17}`
- **Example**: `eni-2a3b4c5d6e7f8g9h0`
- **CLI Prompt**: "Primary FortiGate ENIs: HA ENI ID"
- **Terraform Variable**: `primary_ha_eni_id`

#### primary_mgmt_eni_id
- **Type**: String (ENI ID format)
- **Required**: Yes
- **Description**: Pre-created ENI ID for primary FortiGate management interface
- **Format**: `eni-[a-z0-9]{8,17}`
- **Example**: `eni-3a4b5c6d7e8f9g0h1`
- **CLI Prompt**: "Primary FortiGate ENIs: Management ENI ID"
- **Terraform Variable**: `primary_mgmt_eni_id`

### Backup FortiGate ENIs

#### backup_outside_eni_id
- **Type**: String (ENI ID format)
- **Required**: Yes
- **Description**: Pre-created ENI ID for backup FortiGate outside interface
- **Format**: `eni-[a-z0-9]{8,17}`
- **Example**: `eni-4a5b6c7d8e9f0g1h2`
- **CLI Prompt**: "Backup FortiGate ENIs: Outside ENI ID"
- **Terraform Variable**: `backup_outside_eni_id`

#### backup_inside_eni_id
- **Type**: String (ENI ID format)
- **Required**: Yes
- **Description**: Pre-created ENI ID for backup FortiGate inside interface
- **Format**: `eni-[a-z0-9]{8,17}`
- **Example**: `eni-5a6b7c8d9e0f1g2h3`
- **CLI Prompt**: "Backup FortiGate ENIs: Inside ENI ID"
- **Terraform Variable**: `backup_inside_eni_id`

#### backup_ha_eni_id
- **Type**: String (ENI ID format)
- **Required**: Yes
- **Description**: Pre-created ENI ID for backup FortiGate HA interface
- **Format**: `eni-[a-z0-9]{8,17}`
- **Example**: `eni-6a7b8c9d0e1f2g3h4`
- **CLI Prompt**: "Backup FortiGate ENIs: HA ENI ID"
- **Terraform Variable**: `backup_ha_eni_id`

#### backup_mgmt_eni_id
- **Type**: String (ENI ID format)
- **Required**: Yes
- **Description**: Pre-created ENI ID for backup FortiGate management interface
- **Format**: `eni-[a-z0-9]{8,17}`
- **Example**: `eni-7a8b9c0d1e2f3g4h5`
- **CLI Prompt**: "Backup FortiGate ENIs: Management ENI ID"
- **Terraform Variable**: `backup_mgmt_eni_id`

**Note**: Use the `create-enis.py` script to create all required ENIs before deployment. See [ENI-CREATION-README.md](ENI-CREATION-README.md) for details.

---

## Elastic IP Configuration

### allocate_eips
- **Type**: Boolean
- **Required**: No
- **Default**: `true`
- **Description**: Whether to allocate Elastic IPs for outside interfaces
- **Example**: `true`, `false`
- **CLI Prompt**: "Allocate Elastic IPs for outside interfaces?"
- **Terraform Variable**: `allocate_eips`
- **Note**: Set to `false` for internal-only deployments

### primary_outside_eip_id
- **Type**: String (EIP Allocation ID format)
- **Required**: No (only if using existing EIPs)
- **Default**: `""` (creates new EIP)
- **Description**: Existing Elastic IP allocation ID for primary outside interface
- **Format**: `eipalloc-[a-z0-9]{8,17}`
- **Example**: `eipalloc-0a1b2c3d4e5f6g7h8`
- **CLI Prompt**: "Primary outside EIP allocation ID (or leave empty to create new)"
- **Terraform Variable**: `primary_outside_eip_id`

### backup_outside_eip_id
- **Type**: String (EIP Allocation ID format)
- **Required**: No (only if using existing EIPs)
- **Default**: `""` (creates new EIP)
- **Description**: Existing Elastic IP allocation ID for backup outside interface
- **Format**: `eipalloc-[a-z0-9]{8,17}`
- **Example**: `eipalloc-1a2b3c4d5e6f7g8h9`
- **CLI Prompt**: "Backup outside EIP allocation ID (or leave empty to create new)"
- **Terraform Variable**: `backup_outside_eip_id`

### enable_eip_failover
- **Type**: Boolean
- **Required**: No
- **Default**: `true`
- **Description**: Enable FortiGate HA EIP failover using AWS SDN connector
- **Example**: `true`, `false`
- **CLI Prompt**: "Enable FortiGate HA EIP failover?"
- **Terraform Variable**: `enable_eip_failover`
- **Behavior**:
  - `true`: IAM role created, EIPs allocated but NOT associated, FortiGate manages failover
  - `false`: No IAM role, EIPs allocated AND statically associated, manual failover required
- **Note**: Requires IAM permissions for EC2 EIP management when enabled

---

## FortiGate Configuration

### fortigate_ami_id
- **Type**: String (AMI ID format)
- **Required**: Yes (unless auto-discovery enabled)
- **Description**: FortiGate AMI ID for the target region
- **Format**: `ami-[a-z0-9]{8,17}`
- **Example**: `ami-0a1b2c3d4e5f6g7h8`
- **CLI Prompt**: "FortiGate AMI ID" (if auto-discovery disabled)
- **Terraform Variable**: `fortigate_ami_id`
- **Note**: Can be auto-discovered using `--auto-discover-ami` flag

### AMI Discovery Configuration

#### ami_discovery.enabled
- **Type**: Boolean
- **Required**: No
- **Default**: `true`
- **Description**: Enable automatic AMI discovery from AWS Marketplace
- **CLI Prompt**: "Auto-discover FortiGate AMI?"
- **Note**: Requires AWS API access

#### ami_discovery.version
- **Type**: String
- **Required**: No (if auto-discovery enabled)
- **Default**: `7.4`
- **Description**: FortiGate version for AMI discovery
- **Example**: `7.4`, `7.2`, `7.0`
- **CLI Prompt**: "FortiGate version"

#### ami_discovery.license_type
- **Type**: String (Choice)
- **Required**: No (if auto-discovery enabled)
- **Default**: `BYOL`
- **Options**: `BYOL`, `OnDemand`, `Reserved`
- **Description**: FortiGate licensing model
- **CLI Prompt**: "License type"

#### ami_discovery.architecture
- **Type**: String
- **Required**: No
- **Default**: `x86_64`
- **Description**: CPU architecture for AMI
- **Example**: `x86_64`, `arm64`

### Licensing Configuration

#### licensing.type
- **Type**: String (Choice)
- **Required**: Yes
- **Default**: `BYOL`
- **Options**: `BYOL`, `OnDemand`, `Reserved`
- **Description**: FortiGate licensing model
- **CLI Prompt**: "License type"

#### licensing.primary_license_secret (BYOL only)
- **Type**: String
- **Required**: Yes (if BYOL and using Secrets Manager)
- **Description**: AWS Secrets Manager secret name for primary FortiGate license
- **Example**: `fortigate/primary/license`
- **CLI Prompt**: "Primary FortiGate license secret name"

#### licensing.backup_license_secret (BYOL only)
- **Type**: String
- **Required**: Yes (if BYOL and using Secrets Manager)
- **Description**: AWS Secrets Manager secret name for backup FortiGate license
- **Example**: `fortigate/backup/license`
- **CLI Prompt**: "Backup FortiGate license secret name"

#### licensing.license_s3_bucket (BYOL only)
- **Type**: String
- **Required**: Yes (if BYOL and using S3)
- **Description**: S3 bucket name containing FortiGate license files
- **Example**: `my-fortigate-licenses`
- **CLI Prompt**: "S3 bucket name"

#### licensing.primary_license_s3_key (BYOL only)
- **Type**: String
- **Required**: Yes (if BYOL and using S3)
- **Description**: S3 object key for primary FortiGate license file
- **Example**: `licenses/fortigate-primary.lic`
- **CLI Prompt**: "Primary license S3 key"

#### licensing.backup_license_s3_key (BYOL only)
- **Type**: String
- **Required**: Yes (if BYOL and using S3)
- **Description**: S3 object key for backup FortiGate license file
- **Example**: `licenses/fortigate-backup.lic`
- **CLI Prompt**: "Backup license S3 key"

### Instance Configuration

#### instance_type
- **Type**: String (Choice)
- **Required**: Yes
- **Default**: `c5.xlarge`
- **Options**: `c5.large`, `c5.xlarge`, `c5.2xlarge`, `c5.4xlarge`, `c5.9xlarge`, `c5n.large`, `c5n.xlarge`, `c5n.2xlarge`, `c5n.4xlarge`, `c5n.9xlarge`
- **Description**: EC2 instance type for FortiGate instances
- **CLI Prompt**: "Instance type"
- **Terraform Variable**: `instance_type`
- **Validation**: Must be a supported FortiGate instance type

#### key_pair_name
- **Type**: String
- **Required**: Yes
- **Description**: AWS EC2 Key Pair name for SSH access to FortiGate instances
- **Example**: `my-fortigate-keypair`
- **CLI Prompt**: "EC2 Key Pair name"
- **Terraform Variable**: `key_pair_name`
- **Note**: Key pair must exist in the target region before deployment

#### admin_password
- **Type**: String (Sensitive)
- **Required**: Yes
- **Minimum Length**: 8 characters
- **Description**: Admin password for FortiGate web UI and CLI access
- **CLI Prompt**: "Admin password (min 8 chars)"
- **Terraform Variable**: `admin_password`
- **Security**: Marked as sensitive, not displayed in logs or outputs

#### ha_password
- **Type**: String (Sensitive)
- **Required**: Yes
- **Minimum Length**: 8 characters
- **Description**: HA synchronization password between primary and backup FortiGate
- **CLI Prompt**: "HA synchronization password (min 8 chars)"
- **Terraform Variable**: `ha_password`
- **Security**: Marked as sensitive, not displayed in logs or outputs

#### fortigate_hostname_primary
- **Type**: String
- **Required**: No
- **Default**: `fortigate-primary`
- **Description**: Hostname for primary FortiGate instance
- **Example**: `fortigate-primary`, `fw-primary-prod`
- **CLI Prompt**: "Primary hostname"
- **Terraform Variable**: `fortigate_hostname_primary`

#### fortigate_hostname_backup
- **Type**: String
- **Required**: No
- **Default**: `fortigate-backup`
- **Description**: Hostname for backup FortiGate instance
- **Example**: `fortigate-backup`, `fw-backup-prod`
- **CLI Prompt**: "Backup hostname"
- **Terraform Variable**: `fortigate_hostname_backup`

---

## Transit Gateway Configuration

### create_transit_gateway
- **Type**: Boolean
- **Required**: Yes
- **Default**: `false`
- **Description**: Whether to create a new Transit Gateway or use existing
- **Example**: `true`, `false`
- **CLI Prompt**: "Create new Transit Gateway?"
- **Terraform Variable**: `create_transit_gateway`

### existing_transit_gateway_id
- **Type**: String (TGW ID format)
- **Required**: Yes (if create_transit_gateway is false)
- **Description**: Existing Transit Gateway ID to use
- **Format**: `tgw-[a-z0-9]{8,17}`
- **Example**: `tgw-0c0228dc5dffa8fa9`
- **CLI Prompt**: "Existing Transit Gateway ID"
- **Terraform Variable**: `existing_transit_gateway_id`
- **Validation**: Must be a valid Transit Gateway ID format

### bgp_asn
- **Type**: Number
- **Required**: Yes
- **Default**: `65000`
- **Range**: 64512-65534 (private ASN range)
- **Description**: BGP ASN for FortiGate instances
- **Example**: `65000`, `65100`
- **CLI Prompt**: "FortiGate BGP ASN"
- **Terraform Variable**: `bgp_asn`
- **Validation**: Must be in private ASN range (64512-65534)

### transit_gateway_asn
- **Type**: Number
- **Required**: Yes
- **Default**: `64512`
- **Range**: 64512-65534 (private ASN range)
- **Description**: BGP ASN for Transit Gateway
- **Example**: `64512`, `64513`
- **CLI Prompt**: "Transit Gateway ASN"
- **Terraform Variable**: `transit_gateway_asn`
- **Validation**: Must be in private ASN range (64512-65534)

### spoke_vpc_cidrs
- **Type**: List of Strings (CIDR format)
- **Required**: No
- **Default**: `["10.1.0.0/16", "10.2.0.0/16"]`
- **Description**: List of spoke VPC CIDR blocks for routing
- **Example**: `["10.1.0.0/16", "10.2.0.0/16", "10.3.0.0/16"]`
- **CLI Prompt**: "Spoke VPC CIDRs (comma-separated)"
- **Terraform Variable**: `spoke_vpc_cidrs`
- **Validation**: All entries must be valid CIDR blocks

---

## Monitoring Configuration

### enable_flow_logs
- **Type**: Boolean
- **Required**: No
- **Default**: `true`
- **Description**: Enable VPC Flow Logs for network traffic monitoring
- **Example**: `true`, `false`
- **CLI Prompt**: "Enable VPC Flow Logs?"
- **Terraform Variable**: `enable_flow_logs`

### log_retention_days
- **Type**: Number (Choice)
- **Required**: No
- **Default**: `30`
- **Options**: 1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365, 400, 545, 731, 1827, 3653
- **Description**: CloudWatch log retention period in days
- **Example**: `30`, `90`, `365`
- **CLI Prompt**: "Log retention days"
- **Terraform Variable**: `log_retention_days`
- **Validation**: Must be a valid CloudWatch retention period

### enable_detailed_monitoring
- **Type**: Boolean
- **Required**: No
- **Default**: `true`
- **Description**: Enable detailed CloudWatch monitoring for EC2 instances (1-minute intervals)
- **Example**: `true`, `false`
- **CLI Prompt**: "Enable detailed EC2 monitoring?"
- **Terraform Variable**: `enable_detailed_monitoring`
- **Note**: Detailed monitoring incurs additional costs

---

## Backend Configuration

### backend_type
- **Type**: String (Choice)
- **Required**: Yes
- **Default**: `local`
- **Options**: `local`, `s3`
- **Description**: Terraform backend type for state management
- **CLI Prompt**: "Backend type"
- **CLI Option**: `--backend`
- **Note**: S3 backend requires bootstrap setup first

### S3 Backend Configuration (if backend_type = s3)

#### s3_bucket
- **Type**: String
- **Required**: Yes (if using S3 backend)
- **Description**: S3 bucket name for Terraform state storage
- **Example**: `my-fortigate-terraform-state`
- **CLI Prompt**: "S3 bucket name (from bootstrap output)"
- **CLI Option**: `--s3-bucket`
- **Note**: Must be created using bootstrap process first

#### s3_key
- **Type**: String
- **Required**: Yes (if using S3 backend)
- **Default**: `fortigate-ha/terraform.tfstate`
- **Description**: S3 object key for state file
- **Example**: `fortigate-ha/terraform.tfstate`, `prod/fortigate.tfstate`
- **CLI Prompt**: "S3 state file key"
- **CLI Option**: `--s3-key`

#### s3_region
- **Type**: String
- **Required**: Yes (if using S3 backend)
- **Description**: AWS region where S3 bucket is located
- **Example**: `us-east-1`, `us-west-2`
- **CLI Prompt**: "S3 bucket region"
- **CLI Option**: `--s3-region`
- **Note**: Defaults to aws_region if not specified

#### dynamodb_table
- **Type**: String
- **Required**: Yes (if using S3 backend)
- **Default**: `fortigate-terraform-locks`
- **Description**: DynamoDB table name for state locking
- **Example**: `fortigate-terraform-locks`, `terraform-state-locks`
- **CLI Prompt**: "DynamoDB table name (from bootstrap output)"
- **CLI Option**: `--dynamodb-table`
- **Note**: Must be created using bootstrap process first

#### encrypt
- **Type**: Boolean
- **Required**: No
- **Default**: `true`
- **Description**: Enable server-side encryption for state file
- **CLI Prompt**: "Encrypt state file?"

#### s3_profile
- **Type**: String
- **Required**: No
- **Description**: AWS profile for S3 backend access
- **Example**: `default`, `terraform-backend`
- **CLI Prompt**: "AWS profile name" (if "Use AWS profile for backend?" is Yes)

#### kms_key_id
- **Type**: String
- **Required**: No
- **Description**: KMS key ID or ARN for state file encryption
- **Example**: `arn:aws:kms:us-east-1:123456789012:key/12345678-1234-1234-1234-123456789012`
- **CLI Prompt**: "KMS Key ID or ARN" (if "Use KMS encryption?" is Yes)

---

## Command-Line Options

The `deploy.py` script supports the following command-line options:

### General Options

#### --config, -c
- **Type**: File Path
- **Description**: Load configuration from YAML or JSON file
- **Example**: `python deploy.py --config my-config.yaml`

#### --plan-only
- **Type**: Flag
- **Description**: Generate Terraform plan only, do not deploy
- **Example**: `python deploy.py --plan-only`

#### --destroy
- **Type**: Flag
- **Description**: Destroy existing deployment
- **Example**: `python deploy.py --destroy`

#### --save-config
- **Type**: File Path
- **Description**: Save configuration to file after prompts
- **Example**: `python deploy.py --save-config deployment-config.yaml`

#### --skip-validation
- **Type**: Flag
- **Description**: Skip AWS API validation (use when credentials are limited)
- **Example**: `python deploy.py --skip-validation`
- **Note**: Terraform will still validate resources during deployment

### AMI Discovery Options

#### --auto-discover-ami
- **Type**: Flag
- **Description**: Auto-discover FortiGate AMI and exit
- **Example**: `python deploy.py --auto-discover-ami --license-type BYOL --fortigate-version 7.4`

#### --license-type
- **Type**: Choice (BYOL, OnDemand, Reserved)
- **Description**: License type for AMI discovery
- **Example**: `python deploy.py --auto-discover-ami --license-type BYOL`

#### --fortigate-version
- **Type**: String
- **Default**: `7.4`
- **Description**: FortiGate version for AMI discovery
- **Example**: `python deploy.py --auto-discover-ami --fortigate-version 7.2`

#### --list-versions
- **Type**: Flag
- **Description**: List available FortiGate versions and exit
- **Example**: `python deploy.py --list-versions`

### Backend Options

#### --backend
- **Type**: Choice (local, s3)
- **Description**: Terraform backend type
- **Example**: `python deploy.py --backend s3 --s3-bucket my-bucket`

#### --s3-bucket
- **Type**: String
- **Description**: S3 bucket name for remote state (requires --backend=s3)
- **Example**: `python deploy.py --backend s3 --s3-bucket my-terraform-state`

#### --s3-key
- **Type**: String
- **Default**: `fortigate-ha/terraform.tfstate`
- **Description**: S3 key for state file
- **Example**: `python deploy.py --backend s3 --s3-bucket my-bucket --s3-key prod/state.tfstate`

#### --s3-region
- **Type**: String
- **Description**: S3 bucket region
- **Example**: `python deploy.py --backend s3 --s3-bucket my-bucket --s3-region us-west-2`

#### --dynamodb-table
- **Type**: String
- **Default**: `fortigate-terraform-locks`
- **Description**: DynamoDB table for state locking
- **Example**: `python deploy.py --backend s3 --s3-bucket my-bucket --dynamodb-table my-locks`

#### --bootstrap-info
- **Type**: Flag
- **Description**: Show bootstrap setup information and exit
- **Example**: `python deploy.py --bootstrap-info`

---

## Configuration File Format

Configuration can be provided via YAML or JSON file using the `--config` option.

### YAML Example

```yaml
# deployment-config.yaml
aws:
  region: us-east-1
  profile: default

network:
  vpc_id: vpc-0e16490e6ab8422fb
  availability_zones:
    - us-east-1a
    - us-east-1b
  
  # Subnet IDs
  outside_subnet_primary: subnet-0a1b2c3d4e5f6g7h8
  inside_subnet_primary: subnet-1a2b3c4d5e6f7g8h9
  ha_subnet_primary: subnet-2a3b4c5d6e7f8g9h0
  mgmt_subnet_primary: subnet-3a4b5c6d7e8f9g0h1
  
  outside_subnet_backup: subnet-4a5b6c7d8e9f0g1h2
  inside_subnet_backup: subnet-5a6b7c8d9e0f1g2h3
  ha_subnet_backup: subnet-6a7b8c9d0e1f2g3h4
  mgmt_subnet_backup: subnet-7a8b9c0d1e2f3g4h5
  
  mgmt_access_cidrs:
    - 10.0.0.0/8
  
  # ENI IDs (pre-created)
  primary_outside_eni_id: eni-0a1b2c3d4e5f6g7h8
  primary_inside_eni_id: eni-1a2b3c4d5e6f7g8h9
  primary_ha_eni_id: eni-2a3b4c5d6e7f8g9h0
  primary_mgmt_eni_id: eni-3a4b5c6d7e8f9g0h1
  
  backup_outside_eni_id: eni-4a5b6c7d8e9f0g1h2
  backup_inside_eni_id: eni-5a6b7c8d9e0f1g2h3
  backup_ha_eni_id: eni-6a7b8c9d0e1f2g3h4
  backup_mgmt_eni_id: eni-7a8b9c0d1e2f3g4h5
  
  # EIP Configuration
  allocate_eips: true
  enable_eip_failover: true
  primary_outside_eip_id: ""  # Empty = create new
  backup_outside_eip_id: ""   # Empty = create new

fortigate:
  ami_id: ami-0a1b2c3d4e5f6g7h8
  
  ami_discovery:
    enabled: false
    version: "7.4"
    license_type: BYOL
    architecture: x86_64
  
  licensing:
    type: BYOL
    primary_license_secret: fortigate/primary/license
    backup_license_secret: fortigate/backup/license
  
  instance_type: c5.xlarge
  key_pair_name: my-fortigate-keypair
  admin_password: "MySecurePassword123!"
  ha_password: "MyHAPassword123!"
  hostname_primary: fortigate-primary
  hostname_backup: fortigate-backup

transit_gateway:
  create_new: false
  transit_gateway_id: tgw-0c0228dc5dffa8fa9
  bgp_asn: 65000
  transit_gateway_asn: 64512
  spoke_vpc_cidrs:
    - 10.1.0.0/16
    - 10.2.0.0/16

monitoring:
  enable_flow_logs: true
  log_retention_days: 30
  enable_detailed_monitoring: true

backend:
  backend_type: s3
  s3_bucket: my-fortigate-terraform-state
  s3_key: fortigate-ha/terraform.tfstate
  s3_region: us-east-1
  dynamodb_table: fortigate-terraform-locks
  encrypt: true
  s3_profile: default

environment: prod
owner_tag: NetworkTeam
```

### JSON Example

```json
{
  "aws": {
    "region": "us-east-1",
    "profile": "default"
  },
  "network": {
    "vpc_id": "vpc-0e16490e6ab8422fb",
    "availability_zones": ["us-east-1a", "us-east-1b"],
    "outside_subnet_primary": "subnet-0a1b2c3d4e5f6g7h8",
    "inside_subnet_primary": "subnet-1a2b3c4d5e6f7g8h9",
    "ha_subnet_primary": "subnet-2a3b4c5d6e7f8g9h0",
    "mgmt_subnet_primary": "subnet-3a4b5c6d7e8f9g0h1",
    "outside_subnet_backup": "subnet-4a5b6c7d8e9f0g1h2",
    "inside_subnet_backup": "subnet-5a6b7c8d9e0f1g2h3",
    "ha_subnet_backup": "subnet-6a7b8c9d0e1f2g3h4",
    "mgmt_subnet_backup": "subnet-7a8b9c0d1e2f3g4h5",
    "mgmt_access_cidrs": ["10.0.0.0/8"],
    "primary_outside_eni_id": "eni-0a1b2c3d4e5f6g7h8",
    "primary_inside_eni_id": "eni-1a2b3c4d5e6f7g8h9",
    "primary_ha_eni_id": "eni-2a3b4c5d6e7f8g9h0",
    "primary_mgmt_eni_id": "eni-3a4b5c6d7e8f9g0h1",
    "backup_outside_eni_id": "eni-4a5b6c7d8e9f0g1h2",
    "backup_inside_eni_id": "eni-5a6b7c8d9e0f1g2h3",
    "backup_ha_eni_id": "eni-6a7b8c9d0e1f2g3h4",
    "backup_mgmt_eni_id": "eni-7a8b9c0d1e2f3g4h5",
    "allocate_eips": true,
    "enable_eip_failover": true,
    "primary_outside_eip_id": "",
    "backup_outside_eip_id": ""
  },
  "fortigate": {
    "ami_id": "ami-0a1b2c3d4e5f6g7h8",
    "instance_type": "c5.xlarge",
    "key_pair_name": "my-fortigate-keypair",
    "admin_password": "MySecurePassword123!",
    "ha_password": "MyHAPassword123!",
    "hostname_primary": "fortigate-primary",
    "hostname_backup": "fortigate-backup"
  },
  "transit_gateway": {
    "create_new": false,
    "transit_gateway_id": "tgw-0c0228dc5dffa8fa9",
    "bgp_asn": 65000,
    "transit_gateway_asn": 64512,
    "spoke_vpc_cidrs": ["10.1.0.0/16", "10.2.0.0/16"]
  },
  "monitoring": {
    "enable_flow_logs": true,
    "log_retention_days": 30,
    "enable_detailed_monitoring": true
  },
  "backend": {
    "backend_type": "s3",
    "s3_bucket": "my-fortigate-terraform-state",
    "s3_key": "fortigate-ha/terraform.tfstate",
    "s3_region": "us-east-1",
    "dynamodb_table": "fortigate-terraform-locks",
    "encrypt": true
  },
  "environment": "prod",
  "owner_tag": "NetworkTeam"
}
```

---

## Usage Examples

### Example 1: Interactive Deployment with S3 Backend

```bash
python deploy.py --backend s3 \
  --s3-bucket my-fortigate-terraform-state \
  --s3-region us-east-1 \
  --dynamodb-table fortigate-terraform-locks
```

The script will prompt for all required parameters interactively.

### Example 2: Deployment from Configuration File

```bash
python deploy.py --config deployment-config.yaml
```

### Example 3: Generate Plan Only

```bash
python deploy.py --config deployment-config.yaml --plan-only
```

### Example 4: Auto-Discover AMI

```bash
python deploy.py --auto-discover-ami \
  --license-type BYOL \
  --fortigate-version 7.4
```

### Example 5: List Available FortiGate Versions

```bash
python deploy.py --list-versions
```

### Example 6: Deploy with Skip Validation

```bash
python deploy.py --skip-validation --config deployment-config.yaml
```

Use this when AWS credentials have limited permissions and cannot validate resources.

### Example 7: Destroy Deployment

```bash
python deploy.py --destroy --config deployment-config.yaml
```

### Example 8: Save Configuration After Interactive Prompts

```bash
python deploy.py --save-config my-deployment.yaml
```

---

## Terraform Variables File

Alternatively, you can use Terraform directly with a `terraform.tfvars` file:

```hcl
# terraform.tfvars

# AWS Configuration
aws_region  = "us-east-1"
environment = "prod"
owner_tag   = "NetworkTeam"

# Network Configuration
vpc_id             = "vpc-0e16490e6ab8422fb"
availability_zones = ["us-east-1a", "us-east-1b"]

# Subnet Configuration
outside_subnet_primary = "subnet-0a1b2c3d4e5f6g7h8"
inside_subnet_primary  = "subnet-1a2b3c4d5e6f7g8h9"
ha_subnet_primary      = "subnet-2a3b4c5d6e7f8g9h0"
mgmt_subnet_primary    = "subnet-3a4b5c6d7e8f9g0h1"

outside_subnet_backup = "subnet-4a5b6c7d8e9f0g1h2"
inside_subnet_backup  = "subnet-5a6b7c8d9e0f1g2h3"
ha_subnet_backup      = "subnet-6a7b8c9d0e1f2g3h4"
mgmt_subnet_backup    = "subnet-7a8b9c0d1e2f3g4h5"

# ENI Configuration
primary_outside_eni_id = "eni-0a1b2c3d4e5f6g7h8"
primary_inside_eni_id  = "eni-1a2b3c4d5e6f7g8h9"
primary_ha_eni_id      = "eni-2a3b4c5d6e7f8g9h0"
primary_mgmt_eni_id    = "eni-3a4b5c6d7e8f9g0h1"

backup_outside_eni_id = "eni-4a5b6c7d8e9f0g1h2"
backup_inside_eni_id  = "eni-5a6b7c8d9e0f1g2h3"
backup_ha_eni_id      = "eni-6a7b8c9d0e1f2g3h4"
backup_mgmt_eni_id    = "eni-7a8b9c0d1e2f3g4h5"

# EIP Configuration
allocate_eips          = true
enable_eip_failover    = true
primary_outside_eip_id = ""  # Empty = create new
backup_outside_eip_id  = ""  # Empty = create new

# FortiGate Configuration
fortigate_ami_id           = "ami-0a1b2c3d4e5f6g7h8"
instance_type              = "c5.xlarge"
key_pair_name              = "my-fortigate-keypair"
admin_password             = "MySecurePassword123!"
ha_password                = "MyHAPassword123!"
fortigate_hostname_primary = "fortigate-primary"
fortigate_hostname_backup  = "fortigate-backup"

# Transit Gateway Configuration
create_transit_gateway      = false
existing_transit_gateway_id = "tgw-0c0228dc5dffa8fa9"
transit_gateway_asn         = 64512
bgp_asn                     = 65000
spoke_vpc_cidrs             = ["10.1.0.0/16", "10.2.0.0/16"]

# Security Configuration
mgmt_access_cidrs = ["10.0.0.0/8"]

# Monitoring Configuration
enable_flow_logs           = true
log_retention_days         = 30
enable_detailed_monitoring = true
```

Then deploy with:

```bash
cd terraform
terraform init
terraform plan
terraform apply
```

---

## Quick Reference Table

| Parameter | Type | Required | Default | CLI Option |
|-----------|------|----------|---------|------------|
| aws_region | String | Yes | us-east-1 | - |
| vpc_id | String | Yes | - | - |
| availability_zones | List | Yes | - | - |
| allocate_eips | Boolean | No | true | - |
| enable_eip_failover | Boolean | No | true | - |
| fortigate_ami_id | String | Yes* | - | --auto-discover-ami |
| instance_type | String | Yes | c5.xlarge | - |
| key_pair_name | String | Yes | - | - |
| admin_password | String | Yes | - | - |
| ha_password | String | Yes | - | - |
| create_transit_gateway | Boolean | Yes | false | - |
| bgp_asn | Number | Yes | 65000 | - |
| enable_flow_logs | Boolean | No | true | - |
| backend_type | String | Yes | local | --backend |

*Required unless auto-discovery is enabled

---

## Related Documentation

- [ENI-CREATION-README.md](ENI-CREATION-README.md) - Creating ENIs before deployment
- [STATE_MANAGEMENT_GUIDE.md](STATE_MANAGEMENT_GUIDE.md) - Setting up S3 backend
- [AWS_CREDENTIALS_SETUP.md](AWS_CREDENTIALS_SETUP.md) - Configuring AWS credentials
- [EC2_KEY_PAIR_SETUP.md](EC2_KEY_PAIR_SETUP.md) - Creating EC2 key pairs
- [AMI_AND_LICENSING_GUIDE.md](AMI_AND_LICENSING_GUIDE.md) - Finding FortiGate AMIs
- [ROOT-LEVEL-INTEGRATION-COMPLETE.md](ROOT-LEVEL-INTEGRATION-COMPLETE.md) - EIP failover configuration

---

## Getting Help

### View All Command-Line Options

```bash
python deploy.py --help
```

### View Bootstrap Information

```bash
python deploy.py --bootstrap-info
```

### List Available FortiGate Versions

```bash
python deploy.py --list-versions
```

### Test Configuration Without Deploying

```bash
python deploy.py --config my-config.yaml --plan-only
```

---

## Troubleshooting

### Missing Required Parameters

If you see errors about missing parameters, ensure all required fields are provided either through:
- Interactive prompts
- Configuration file
- Terraform variables file

### Invalid Parameter Format

Check that IDs match the expected format:
- VPC ID: `vpc-[a-z0-9]{8,17}`
- Subnet ID: `subnet-[a-z0-9]{8,17}`
- ENI ID: `eni-[a-z0-9]{8,17}`
- AMI ID: `ami-[a-z0-9]{8,17}`
- EIP Allocation ID: `eipalloc-[a-z0-9]{8,17}`
- Transit Gateway ID: `tgw-[a-z0-9]{8,17}`

### AWS Validation Failures

If AWS validation fails:
1. Check AWS credentials are configured correctly
2. Verify resources exist in the specified region
3. Use `--skip-validation` flag to bypass validation (Terraform will still validate)

### Backend Configuration Issues

For S3 backend issues:
1. Ensure bootstrap process completed successfully
2. Verify S3 bucket and DynamoDB table exist
3. Check IAM permissions for S3 and DynamoDB access
4. See [STATE_MANAGEMENT_GUIDE.md](STATE_MANAGEMENT_GUIDE.md) for detailed troubleshooting

---

**Last Updated**: 2024
**Version**: 1.0
