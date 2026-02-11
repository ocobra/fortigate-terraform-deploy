# FortiGate AWS HA Deployment

A comprehensive infrastructure-as-code solution for deploying highly available FortiGate firewall pairs on AWS in a hub-and-spoke architecture using Transit Gateway.

## Architecture Overview

```
Internal VPC Subnets → Transit Gateway → FortiGate HA Pair → Internet
```

### Key Features

- **High Availability**: Primary/backup FortiGate pair across multiple AZs
- **Hub-and-Spoke Design**: Centralized traffic inspection via Transit Gateway
- **4-Interface Configuration**: OUTSIDE, INSIDE, HA, and MGMT interfaces per FortiGate
- **Pre-assigned Resources**: Uses existing VPC, subnets, and ENIs
- **Comprehensive Logging**: VPC Flow Logs and FortiGate security logs
- **Idempotent Deployment**: Safe rollback and recovery capabilities
- **Interactive Deployment**: CLI and web-based interfaces
- **Validation Integration**: Leverages FortiGate Terraform Analysis System

## Quick Start

### Prerequisites

- Python 3.8+
- Terraform 1.0+
- AWS CLI configured with appropriate permissions
- FortiGate AMI access in target region
- **EC2 Key Pair** for SSH access (see [EC2_KEY_PAIR_SETUP.md](EC2_KEY_PAIR_SETUP.md))

> **📖 Detailed State Management Guide**: For comprehensive instructions on setting up and using Terraform remote state management, see **[STATE_MANAGEMENT_GUIDE.md](STATE_MANAGEMENT_GUIDE.md)**. This guide covers architecture, security, troubleshooting, and best practices.

> **🔑 EC2 Key Pair Setup**: If you don't have an EC2 key pair yet, see **[EC2_KEY_PAIR_SETUP.md](EC2_KEY_PAIR_SETUP.md)** for step-by-step instructions on creating or importing key pairs.

### Step 1: Bootstrap State Management

Before deploying FortiGate infrastructure, you must first create the S3 bucket and DynamoDB table for Terraform state management:

```bash
# Navigate to bootstrap directory
cd terraform/bootstrap

# Copy and configure variables
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your specific values

# Run bootstrap
terraform init
terraform plan
terraform apply

# Note the outputs for next step
terraform output
```

### Step 2: Configure Main Deployment

```bash
# Navigate back to main terraform directory
cd ../

# Initialize with remote backend (use values from bootstrap output)
terraform init \
  -backend-config="bucket=your-bucket-name" \
  -backend-config="key=fortigate-ha/terraform.tfstate" \
  -backend-config="region=us-east-1" \
  -backend-config="encrypt=true" \
  -backend-config="dynamodb_table=fortigate-terraform-locks"
```

### Step 3: Deploy FortiGate Infrastructure

```bash
# Interactive CLI deployment
python deploy.py

# Or use the web interface
streamlit run web_app.py
```

## Project Structure

```
fortigate-aws-ha-deployment/
├── terraform/                  # Terraform modules
│   ├── modules/
│   │   ├── fortigate-ha/      # Main FortiGate HA module
│   │   ├── transit-gateway/   # Transit Gateway configuration
│   │   ├── networking/        # VPC and subnet management
│   │   ├── security/          # Security groups and NACLs
│   │   └── monitoring/        # CloudWatch logs and dashboards
│   ├── main.tf               # Root module
│   ├── variables.tf          # Input variables
│   ├── outputs.tf            # Output values
│   └── terraform.tfvars.example
├── python/                    # Python deployment engine
│   ├── deploy.py             # Main deployment script
│   ├── config/               # Configuration management
│   ├── validation/           # Input validation
│   └── analysis/             # Analysis system integration
├── web/                      # Streamlit web frontend
│   └── app.py               # Web application
├── docs/                     # Documentation
└── tests/                    # Test suites
```

## Usage Examples

### CLI Deployment

```bash
# Generate plan only (no deployment)
python deploy.py --plan-only

# Deploy with custom configuration
python deploy.py --config my-config.yaml

# Rollback to previous state
python deploy.py --rollback
```

### Configuration File Example

```yaml
# deployment-config.yaml
aws:
  region: us-east-1
  profile: default

network:
  vpc_id: vpc-12345678
  availability_zones:
    - us-east-1a
    - us-east-1b
  
  subnets:
    outside_primary: subnet-11111111
    inside_primary: subnet-22222222
    ha_primary: subnet-33333333
    mgmt_primary: subnet-44444444
    outside_backup: subnet-55555555
    inside_backup: subnet-66666666
    ha_backup: subnet-77777777
    mgmt_backup: subnet-88888888

fortigate:
  ami_id: ami-fortigate-7.4
  instance_type: c5.xlarge
  key_pair: my-keypair
  admin_password: "{{ secrets.admin_password }}"
  ha_password: "{{ secrets.ha_password }}"

transit_gateway:
  create_new: false  # Use existing TGW
  transit_gateway_id: tgw-12345678
  bgp_asn: 65000

monitoring:
  enable_flow_logs: true
  log_retention_days: 30
```

## Traffic Flow

1. **Outbound Traffic**: Internal subnet → TGW → FortiGate → Internet
2. **Inbound Traffic**: Internet → FortiGate → TGW → Internal subnet
3. **HA Failover**: Automatic BGP session failover between primary/backup

## Security Features

- Least-privilege security groups
- Network ACLs for defense in depth
- Encrypted Terraform state
- Secrets Manager integration
- Comprehensive audit logging

## Monitoring and Troubleshooting

### CloudWatch Dashboards
- FortiGate health metrics
- Traffic flow statistics
- BGP session status
- Security event logs

### Log Sources
- VPC Flow Logs
- FortiGate security logs
- CloudTrail API logs
- Transit Gateway route logs

## Documentation

This project includes comprehensive documentation for deployment, operation, and troubleshooting:

### Core Documentation
- **[README.md](README.md)** - Main project overview and quick start guide
- **[STATE_MANAGEMENT_GUIDE.md](STATE_MANAGEMENT_GUIDE.md)** - **START HERE**: Complete guide for setting up S3 and DynamoDB for Terraform state management
- **[EC2_KEY_PAIR_SETUP.md](EC2_KEY_PAIR_SETUP.md)** - Complete guide for creating and managing EC2 key pairs for SSH access
- **[USAGE.md](USAGE.md)** - Detailed usage instructions and examples
- **[AMI_AND_LICENSING_GUIDE.md](AMI_AND_LICENSING_GUIDE.md)** - Complete guide for AMI discovery and licensing
- **[IAM_AND_SECURITY_REQUIREMENTS.md](IAM_AND_SECURITY_REQUIREMENTS.md)** - IAM permissions and security access requirements

### Operational Guides
- **[STREAMLIT_DEPLOYMENT_GUIDE.md](STREAMLIT_DEPLOYMENT_GUIDE.md)** - Complete guide for deploying and operating the Streamlit web application
- **[MONITORING_AND_TROUBLESHOOTING_GUIDE.md](MONITORING_AND_TROUBLESHOOTING_GUIDE.md)** - Comprehensive monitoring setup, VPC Flow Logs, CloudWatch configuration, and troubleshooting procedures
- **[COMPLETE_SOLUTION_OVERVIEW.md](COMPLETE_SOLUTION_OVERVIEW.md)** - High-level architecture and solution overview

### Web Application

The project includes a comprehensive Streamlit web application (`web-app.py`) that provides:

- **Interactive Configuration**: Web forms for all deployment parameters
- **AMI Discovery**: Automatic discovery of FortiGate AMIs from AWS Marketplace
- **Licensing Management**: Support for BYOL, OnDemand, and Reserved licensing
- **Cost Analysis**: Intelligent cost comparison and recommendations
- **Real-time Deployment**: Progress tracking and status monitoring
- **Monitoring Dashboard**: Health metrics and traffic visualization

**Start the web application:**
```bash
streamlit run web-app.py
```

Then open your browser to `http://localhost:8501`

### Monitoring and Troubleshooting

The deployment automatically configures comprehensive monitoring:

#### VPC Flow Logs
- **Enabled for**: All VPCs, subnets, and ENIs
- **Destination**: CloudWatch Logs (`/aws/vpc/fortigate-flowlogs`)
- **Analysis**: Pre-built CloudWatch Insights queries for traffic analysis

#### CloudWatch Monitoring
- **Log Groups**: System, traffic, and event logs from FortiGate instances
- **Metrics**: Custom metrics for HA status, BGP sessions, and throughput
- **Dashboards**: Real-time monitoring of FortiGate health and performance
- **Alarms**: Automated alerting for critical events and thresholds

#### FortiGate Logging
- **System Logs**: FortiGate system events and errors
- **Traffic Logs**: Security policy decisions and traffic flows
- **Event Logs**: Administrative events and configuration changes

**Key Monitoring Queries:**

```sql
# Top traffic flows
fields @timestamp, srcaddr, dstaddr, bytes
| filter action = "ACCEPT"
| stats sum(bytes) as total_bytes by srcaddr, dstaddr
| sort total_bytes desc
| limit 20

# BGP session monitoring
fields @timestamp, srcaddr, dstaddr, srcport, dstport
| filter (srcport = 179 or dstport = 179)
| stats count() as bgp_connections by srcaddr, dstaddr

# HA heartbeat traffic
fields @timestamp, srcaddr, dstaddr, protocol, bytes
| filter (srcaddr like /172\.31\.3\./ and dstaddr like /172\.31\.3\./) 
| stats sum(bytes) as ha_traffic by bin(1m)
```

For detailed monitoring setup and troubleshooting procedures, see [MONITORING_AND_TROUBLESHOOTING_GUIDE.md](MONITORING_AND_TROUBLESHOOTING_GUIDE.md).

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

## License

This project is licensed under the MIT License.