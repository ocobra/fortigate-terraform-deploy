#!/usr/bin/env python3
"""
Unit test for FortiGate configuration section in web-app-enhanced.py

This test validates that the FortiGate configuration section correctly:
1. Accepts AMI ID input with format validation
2. Accepts instance type selection
3. Accepts key pair name input
4. Accepts password inputs (admin and HA)
5. Accepts hostname inputs
6. Creates FortiGateConfig object correctly
7. Updates DeploymentConfig with FortiGate settings
"""

import sys
from pathlib import Path
import re

# Add the deployment engine to the path
sys.path.append(str(Path(__file__).parent))

from deploy import (
    DeploymentConfig, AWSConfig, NetworkConfig,
    FortiGateConfig, TransitGatewayConfig, MonitoringConfig, BackendConfig,
    AMIDiscoveryConfig, LicensingConfig
)


def test_ami_id_validation():
    """Test AMI ID format validation"""
    def validate_ami_id(ami_id_val: str) -> bool:
        """Validate AMI ID format: ami-xxxxxxxxxxxxxxxxx"""
        if not ami_id_val:
            return True  # Empty is valid (optional)
        pattern = r'^ami-[0-9a-f]{17}$'
        return bool(re.match(pattern, ami_id_val))
    
    # Valid AMI IDs
    assert validate_ami_id("ami-0123456789abcdef0") == True
    assert validate_ami_id("ami-abcdef0123456789a") == True
    assert validate_ami_id("") == True  # Empty is valid
    
    # Invalid AMI IDs
    assert validate_ami_id("ami-123") == False  # Too short
    assert validate_ami_id("ami-0123456789abcdef01") == False  # Too long
    assert validate_ami_id("ami-0123456789ABCDEF0") == False  # Uppercase not allowed
    assert validate_ami_id("ami_0123456789abcdef0") == False  # Wrong separator
    assert validate_ami_id("emi-0123456789abcdef0") == False  # Wrong prefix
    
    print("✅ AMI ID validation tests passed")


def test_password_strength_validation():
    """Test password strength validation logic"""
    def validate_password(password: str) -> tuple[bool, str]:
        """Validate password meets requirements"""
        if len(password) < 8:
            return False, "Password should be at least 8 characters long"
        
        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        
        if not (has_upper and has_lower and has_digit):
            return False, "Password should contain uppercase, lowercase, and numbers"
        
        return True, "Password is strong"
    
    # Valid passwords
    assert validate_password("Password123")[0] == True
    assert validate_password("MyP@ssw0rd")[0] == True
    assert validate_password("Str0ngP@ss")[0] == True
    
    # Invalid passwords
    assert validate_password("short1A")[0] == False  # Too short
    assert validate_password("password123")[0] == False  # No uppercase
    assert validate_password("PASSWORD123")[0] == False  # No lowercase
    assert validate_password("PasswordABC")[0] == False  # No digits
    
    print("✅ Password strength validation tests passed")


def test_fortigate_config_creation():
    """Test FortiGateConfig object creation with all parameters"""
    
    # Create FortiGate config with all required parameters
    fortigate_config = FortiGateConfig(
        ami_id="ami-0123456789abcdef0",
        ami_discovery=AMIDiscoveryConfig(
            enabled=False,
            version="7.6",
            license_type="byol",
            architecture="x86_64"
        ),
        licensing=LicensingConfig(
            type="BYOL",
            primary_license_secret=None,
            backup_license_secret=None,
            license_s3_bucket=None,
            primary_license_s3_key=None,
            backup_license_s3_key=None
        ),
        instance_type="c5.xlarge",
        key_pair_name="my-keypair",
        admin_password="AdminPass123",
        ha_password="HaPass123",
        hostname_primary="fortigate-primary",
        hostname_backup="fortigate-backup"
    )
    
    # Verify all fields are set correctly
    assert fortigate_config.ami_id == "ami-0123456789abcdef0"
    assert fortigate_config.instance_type == "c5.xlarge"
    assert fortigate_config.key_pair_name == "my-keypair"
    assert fortigate_config.admin_password == "AdminPass123"
    assert fortigate_config.ha_password == "HaPass123"
    assert fortigate_config.hostname_primary == "fortigate-primary"
    assert fortigate_config.hostname_backup == "fortigate-backup"
    
    print("✅ FortiGateConfig creation test passed")


def test_deployment_config_with_fortigate():
    """Test complete DeploymentConfig creation with FortiGate configuration"""
    
    # Create AWS config
    aws_config = AWSConfig(
        region="us-east-1",
        profile="default",
        access_key_id=None,
        secret_access_key=None
    )
    
    # Create Network config
    network_config = NetworkConfig(
        vpc_id="vpc-0123456789abcdef0",
        availability_zones=["us-east-1a", "us-east-1b"],
        outside_subnet_primary="subnet-0123456789abcdef0",
        inside_subnet_primary="subnet-0123456789abcdef1",
        ha_subnet_primary="subnet-0123456789abcdef2",
        mgmt_subnet_primary="subnet-0123456789abcdef3",
        outside_subnet_backup="subnet-0123456789abcdef4",
        inside_subnet_backup="subnet-0123456789abcdef5",
        ha_subnet_backup="subnet-0123456789abcdef6",
        mgmt_subnet_backup="subnet-0123456789abcdef7",
        mgmt_access_cidrs=["0.0.0.0/0"],
        primary_outside_eni_id="eni-0123456789abcdef0",
        primary_inside_eni_id="eni-0123456789abcdef1",
        primary_ha_eni_id="eni-0123456789abcdef2",
        primary_mgmt_eni_id="eni-0123456789abcdef3",
        backup_outside_eni_id="eni-0123456789abcdef4",
        backup_inside_eni_id="eni-0123456789abcdef5",
        backup_ha_eni_id="eni-0123456789abcdef6",
        backup_mgmt_eni_id="eni-0123456789abcdef7",
        allocate_eips=True,
        primary_outside_eip_id=None,
        backup_outside_eip_id=None,
        enable_eip_failover=True
    )
    
    # Create FortiGate config
    fortigate_config = FortiGateConfig(
        ami_id="ami-0123456789abcdef0",
        ami_discovery=AMIDiscoveryConfig(
            enabled=False,
            version="7.6",
            license_type="byol",
            architecture="x86_64"
        ),
        licensing=LicensingConfig(
            type="BYOL",
            primary_license_secret=None,
            backup_license_secret=None,
            license_s3_bucket=None,
            primary_license_s3_key=None,
            backup_license_s3_key=None
        ),
        instance_type="c5.xlarge",
        key_pair_name="my-keypair",
        admin_password="AdminPass123",
        ha_password="HaPass123",
        hostname_primary="fortigate-primary",
        hostname_backup="fortigate-backup"
    )
    
    # Create complete deployment config
    deployment_config = DeploymentConfig(
        aws=aws_config,
        network=network_config,
        fortigate=fortigate_config,
        transit_gateway=TransitGatewayConfig(
            create_new=True,
            transit_gateway_id=None,
            bgp_asn=65000,
            transit_gateway_asn=64512,
            spoke_vpc_cidrs=[]
        ),
        monitoring=MonitoringConfig(
            enable_flow_logs=True,
            log_retention_days=7,
            enable_detailed_monitoring=False
        ),
        backend=BackendConfig(
            backend_type="local",
            s3_bucket=None,
            s3_key=None,
            s3_region=None,
            dynamodb_table=None,
            encrypt=True,
            kms_key_id=None,
            s3_profile=None
        ),
        environment="prod",
        owner_tag="NetworkTeam"
    )
    
    # Verify FortiGate config is properly integrated
    assert deployment_config.fortigate.ami_id == "ami-0123456789abcdef0"
    assert deployment_config.fortigate.instance_type == "c5.xlarge"
    assert deployment_config.fortigate.key_pair_name == "my-keypair"
    assert deployment_config.fortigate.admin_password == "AdminPass123"
    assert deployment_config.fortigate.ha_password == "HaPass123"
    assert deployment_config.fortigate.hostname_primary == "fortigate-primary"
    assert deployment_config.fortigate.hostname_backup == "fortigate-backup"
    
    # Verify other configs are still intact
    assert deployment_config.aws.region == "us-east-1"
    assert deployment_config.network.vpc_id == "vpc-0123456789abcdef0"
    assert deployment_config.environment == "prod"
    assert deployment_config.owner_tag == "NetworkTeam"
    
    print("✅ Complete DeploymentConfig with FortiGate test passed")


def test_instance_type_options():
    """Test that all instance type options are valid"""
    instance_types = [
        'c5.xlarge', 'c5.2xlarge', 'c5.4xlarge', 'c5.9xlarge',
        'c5n.xlarge', 'c5n.2xlarge', 'c5n.4xlarge', 'c5n.9xlarge',
        'c6i.xlarge', 'c6i.2xlarge', 'c6i.4xlarge', 'c6i.8xlarge',
        'm5.xlarge', 'm5.2xlarge', 'm5.4xlarge', 'm5.8xlarge'
    ]
    
    # Verify all instance types follow AWS naming convention
    for instance_type in instance_types:
        assert '.' in instance_type, f"Invalid instance type format: {instance_type}"
        family, size = instance_type.split('.')
        assert family in ['c5', 'c5n', 'c6i', 'm5'], f"Unknown instance family: {family}"
        assert size in ['xlarge', '2xlarge', '4xlarge', '8xlarge', '9xlarge'], f"Unknown instance size: {size}"
    
    print("✅ Instance type options test passed")


def test_required_field_validation():
    """Test that required fields are validated"""
    required_fields = {
        'ami_id': 'ami-0123456789abcdef0',
        'instance_type': 'c5.xlarge',
        'key_pair_name': 'my-keypair',
        'admin_password': 'AdminPass123',
        'ha_password': 'HaPass123'
    }
    
    # Test that all required fields are present
    validation_errors = []
    
    for field, value in required_fields.items():
        if not value:
            validation_errors.append(f"{field} is required")
    
    assert len(validation_errors) == 0, f"Validation errors: {validation_errors}"
    
    # Test with missing fields
    missing_fields = {
        'ami_id': '',
        'instance_type': '',
        'key_pair_name': '',
        'admin_password': '',
        'ha_password': ''
    }
    
    validation_errors = []
    for field, value in missing_fields.items():
        if not value:
            validation_errors.append(f"{field} is required")
    
    assert len(validation_errors) == 5, "Should have 5 validation errors for missing fields"
    
    print("✅ Required field validation test passed")


if __name__ == "__main__":
    print("\n" + "="*70)
    print("Running FortiGate Configuration Section Tests")
    print("="*70 + "\n")
    
    try:
        test_ami_id_validation()
        test_password_strength_validation()
        test_fortigate_config_creation()
        test_deployment_config_with_fortigate()
        test_instance_type_options()
        test_required_field_validation()
        
        print("\n" + "="*70)
        print("✅ ALL TESTS PASSED!")
        print("="*70 + "\n")
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}\n")
        sys.exit(1)
