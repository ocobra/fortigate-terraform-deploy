# FortiGate AWS HA Deployment - Enhanced Web Application

## Overview

This enhanced Streamlit web application provides complete feature parity with the `deploy.py` CLI script, offering an intuitive interface for deploying and managing FortiGate HA pairs on AWS.

## Features

### Complete Parameter Support
- ✅ All 60+ deployment parameters from DEPLOYMENT-PARAMETERS-GUIDE.md
- ✅ AWS configuration (region, profile, credentials)
- ✅ Network configuration (VPC, subnets, AZs, CIDRs)
- ✅ ENI configuration (8 pre-created network interfaces)
- ✅ EIP configuration and failover
- ✅ FortiGate configuration (AMI, instance type, passwords)
- ✅ Transit Gateway configuration
- ✅ Monitoring configuration
- ✅ Backend configuration (local/S3)

### Advanced Features
- ✅ Configuration import/export (YAML/JSON)
- ✅ Real AWS API validation
- ✅ AMI discovery and selection
- ✅ Licensing management (BYOL, OnDemand, Reserved)
- ✅ Cost analysis and comparison
- ✅ Plan-only mode
- ✅ Real-time deployment tracking
- ✅ Destroy functionality

## Prerequisites

### Required Software
- Python 3.8 or higher
- pip (Python package manager)
- AWS CLI configured with appropriate credentials
- Terraform 1.5.0 or higher

### AWS Permissions
The AWS credentials used must have permissions for:
- EC2 (instances, ENIs, EIPs, VPCs, subnets)
- Transit Gateway
- CloudWatch Logs
- Secrets Manager (for BYOL licensing)
- S3 (for backend state and license files)

## Installation

### 1. Clone or Navigate to the Repository
```bash
cd fortigate-aws-ha-deployment
```

### 2. Create a Virtual Environment (Recommended)
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Verify Installation
```bash
python3 -m py_compile web-app-enhanced.py
echo "✅ Installation successful"
```

## Running the Application

### Start the Web Application
```bash
streamlit run web-app-enhanced.py
```

The application will automatically open in your default web browser at `http://localhost:8501`.

### Command-Line Options
```bash
# Run on a specific port
streamlit run web-app-enhanced.py --server.port 8080

# Run with a specific theme
streamlit run web-app-enhanced.py --theme.base dark

# Run without auto-opening browser
streamlit run web-app-enhanced.py --server.headless true
```

## Application Structure

### Pages

1. **🏠 Home**
   - Overview of features and capabilities
   - Quick start guide
   - System status

2. **⚙️ Configuration**
   - AWS configuration
   - Network configuration (VPC, subnets, ENIs)
   - FortiGate configuration
   - Transit Gateway configuration
   - Monitoring configuration
   - Backend configuration
   - Import/Export functionality

3. **🔍 AMI Discovery**
   - Discover FortiGate AMIs from AWS Marketplace
   - Filter by version, license type, and architecture
   - View AMI metadata and alternatives

4. **📄 Licensing**
   - Configure BYOL licensing (Secrets Manager or S3)
   - Configure OnDemand licensing
   - Configure Reserved Instance licensing
   - Upload and validate license files

5. **💰 Cost Analysis**
   - Compare licensing models
   - Calculate monthly and total costs
   - View cost breakdowns
   - Get recommendations

6. **🚀 Deployment**
   - Generate Terraform plans
   - Execute deployments
   - Track progress in real-time
   - View deployment logs
   - Destroy deployments

7. **📊 Monitoring**
   - View deployment status
   - Monitor FortiGate health
   - View traffic metrics

8. **📚 Documentation**
   - Deployment guides
   - Parameter reference
   - Troubleshooting
   - FAQ

## Configuration

### Session State
The application uses Streamlit's session state to persist configuration across page navigation. Your configuration is maintained throughout your session but is not saved to disk unless you explicitly export it.

### Configuration Files
You can import and export configurations in YAML or JSON format:

**Example YAML Configuration:**
```yaml
aws:
  region: us-east-1
  profile: default

network:
  vpc_id: vpc-12345678
  availability_zones:
    - us-east-1a
    - us-east-1b
  # ... additional network configuration

fortigate:
  instance_type: c5.xlarge
  # ... additional FortiGate configuration
```

### Environment Variables
The application respects standard AWS environment variables:
- `AWS_REGION`
- `AWS_PROFILE`
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`

## Usage Workflow

### Basic Deployment Workflow

1. **Configure AWS Settings**
   - Navigate to Configuration page
   - Enter AWS region and credentials
   - Configure environment and owner tags

2. **Configure Network**
   - Enter VPC ID and availability zones
   - Enter subnet IDs for primary and backup FortiGates
   - Enter ENI IDs (8 total - 4 per FortiGate)
   - Configure EIP settings

3. **Discover AMI**
   - Navigate to AMI Discovery page
   - Select FortiGate version and license type
   - Click "Discover AMIs"
   - Select the appropriate AMI

4. **Configure Licensing**
   - Navigate to Licensing page
   - Select licensing model (BYOL, OnDemand, or Reserved)
   - Configure license sources if using BYOL

5. **Analyze Costs**
   - Navigate to Cost Analysis page
   - Set deployment duration and usage pattern
   - Compare licensing models
   - Review recommendations

6. **Deploy**
   - Navigate to Deployment page
   - Review configuration summary
   - Click "Generate Plan" to preview changes
   - Click "Deploy" to execute deployment
   - Monitor progress in real-time

### Configuration Import/Export

**Export Configuration:**
1. Navigate to Configuration page
2. Click "Export Configuration"
3. Choose YAML or JSON format
4. Save the file

**Import Configuration:**
1. Navigate to Configuration page
2. Click "Import Configuration"
3. Upload YAML or JSON file
4. Review and save

## Troubleshooting

### Application Won't Start
```bash
# Check Python version
python3 --version  # Should be 3.8 or higher

# Reinstall dependencies
pip install --upgrade -r requirements.txt

# Check for port conflicts
lsof -i :8501  # On Linux/Mac
netstat -ano | findstr :8501  # On Windows
```

### Import Errors
```bash
# Verify deploy.py is in the same directory
ls -la deploy.py

# Test imports manually
python3 -c "from deploy import DeploymentConfig; print('OK')"
```

### AWS Connection Issues
- Verify AWS credentials are configured: `aws sts get-caller-identity`
- Check IAM permissions
- Verify network connectivity to AWS

### Deployment Failures
- Review deployment logs in the Deployment page
- Check Terraform state: `terraform show`
- Verify all required parameters are provided
- Check AWS service quotas

## Development

### Project Structure
```
fortigate-aws-ha-deployment/
├── web-app-enhanced.py          # Main application file
├── deploy.py                    # Backend deployment engine
├── requirements.txt             # Python dependencies
├── terraform/                   # Terraform modules
│   ├── main.tf
│   ├── variables.tf
│   └── modules/
└── .kiro/specs/                 # Specification documents
    └── streamlit-web-app-enhancement/
```

### Adding New Features
1. Update the appropriate page rendering function
2. Add any new session state variables to `initialize_session_state()`
3. Test thoroughly before committing

### Running Tests
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test file
pytest tests/test_configuration.py
```

## Support

### Documentation
- [FortiGate Documentation](https://docs.fortinet.com/product/fortigate)
- [AWS Documentation](https://docs.aws.amazon.com/)
- [Terraform Documentation](https://www.terraform.io/docs)

### Common Issues
See the Documentation page in the application for:
- Deployment guides
- Parameter reference
- Troubleshooting steps
- FAQ

## Version History

### v2.0 (Current)
- Complete feature parity with deploy.py CLI
- All 60+ deployment parameters supported
- ENI and EIP configuration
- Configuration import/export
- Real AWS API validation
- AMI discovery integration
- Licensing management
- Cost analysis
- Real-time deployment tracking

### v1.0
- Basic deployment functionality
- Limited parameter support
- Simple UI

## License

This application is part of the FortiGate AWS HA Deployment solution.
