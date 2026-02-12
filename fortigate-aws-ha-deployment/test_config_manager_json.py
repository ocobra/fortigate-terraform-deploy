#!/usr/bin/env python3
"""
Test script for ConfigurationManager JSON import/export and validation functionality.
This verifies Tasks 3.2, 3.3, and 3.4 implementation.
"""

import sys
import json
from pathlib import Path

# Add the deployment engine to the path
sys.path.append(str(Path(__file__).parent))

from deploy import (
    DeploymentConfig, AWSConfig, NetworkConfig,
    FortiGateConfig, TransitGatewayConfig, MonitoringConfig, BackendConfig,
    AMIDiscoveryConfig, LicensingConfig
)

# Import ConfigurationManager from web-app-enhanced
import importlib.util
spec = importlib.util.spec_from_file_location("web_app", "web-app-enhanced.py")
web_app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(web_app)

ConfigurationManager = web_app.ConfigurationManager


def create_sample_config():
    """Create a sample configuration for testing"""
    return DeploymentConfig(
        aws=AWSConfig(
            region="us-east-1",
            profile="default",
            access_key_id="AKIAIOSFODNN7EXAMPLE",
            secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
        ),
        network=NetworkConfig(
            vpc_id="vpc-0123456789abcdef0",
            availability_zone_primary="us-east-1a",
            availability_zone_backup="us-east-1b",
            primary_public_subnet_id="subnet-11111111",
            primary_private_subnet_id="subnet-22222222",
            primary_ha_subnet_id="subnet-33333333",
            primary_mgmt_subnet_id="subnet-44444444",
            backup_public_subnet_id="subnet-55555555",
            backup_private_subnet_id="subnet-66666666",
            backup_ha_subnet_id="subnet-77777777",
            backup_mgmt_subnet_id="subnet-88888888",
            mgmt_access_cidrs=["10.0.0.0/8"],
            primary_public_eni_id="eni-11111111",
            primary_private_eni_id="eni-22222222",
            primary_ha_eni_id="eni-33333333",
            primary_mgmt_eni_id="eni-44444444",
            backup_public_eni_id="eni-55555555",
            backup_private_eni_id="eni-66666666",
            backup_ha_eni_id="eni-77777777",
            backup_mgmt_eni_id="eni-88888888",
            allocate_eips=True,
            enable_eip_failover=True,
            primary_public_eip_id="eipalloc-12345678",
            backup_public_eip_id="eipalloc-87654321"
        ),
        fortigate=FortiGateConfig(
            ami_id="ami-0123456789abcdef0",
            ami_discovery=AMIDiscoveryConfig(
                enabled=False,
                version="7.4",
                license_type="byol",
                architecture="x86_64"
            ),
            licensing=LicensingConfig(
                license_type="byol",
                license_source="secrets_manager",
                primary_license_secret="fortigate-primary-license",
                backup_license_secret="fortigate-backup-license"
            ),
            instance_type="c5.xlarge",
            key_pair_name="my-keypair",
            admin_password="AdminPass123!",
            ha_password="HAPass123!",
            hostname_primary="fortigate-primary",
            hostname_backup="fortigate-backup"
        ),
        transit_gateway=TransitGatewayConfig(
            create_new=True,
            amazon_side_asn=64512,
            fortigate_asn=65000,
            spoke_vpc_cidrs=["10.1.0.0/16", "10.2.0.0/16"]
        ),
        monitoring=MonitoringConfig(
            enable_flow_logs=True,
            log_retention_days=30,
            enable_detailed_monitoring=True
        ),
        backend=BackendConfig(
            backend_type="s3",
            s3_bucket="my-terraform-state",
            s3_key="fortigate-ha/terraform.tfstate",
            s3_region="us-east-1",
            dynamodb_table="terraform-state-lock",
            encrypt=True
        ),
        environment="prod",
        owner_tag="NetworkTeam"
    )


def test_json_export_import():
    """Test JSON export and import functionality (Task 3.2)"""
    print("\n" + "=" * 60)
    print("Task 3.2: Testing JSON export/import...")
    print("=" * 60)
    
    config = create_sample_config()
    manager = ConfigurationManager()
    
    # Test export without redaction
    print("\n1. Testing JSON export without redaction...")
    json_content = manager.export_json(config, redact_sensitive=False)
    print("✓ Export successful")
    
    # Verify it's valid JSON
    json_dict = json.loads(json_content)
    assert isinstance(json_dict, dict), "Should be a valid JSON object"
    assert "AdminPass123!" in json_content, "Password should be present"
    assert "us-east-1" in json_content, "Region should be present"
    assert "AKIAIOSFODNN7EXAMPLE" in json_content, "Access key should be present"
    print("✓ JSON is valid and contains expected data")
    
    # Test export with redaction
    print("\n2. Testing JSON export with redaction...")
    json_redacted = manager.export_json(config, redact_sensitive=True)
    print("✓ Export with redaction successful")
    
    json_redacted_dict = json.loads(json_redacted)
    assert "[REDACTED]" in json_redacted, "Sensitive data should be redacted"
    assert "AdminPass123!" not in json_redacted, "Admin password should be redacted"
    assert "HAPass123!" not in json_redacted, "HA password should be redacted"
    assert "AKIAIOSFODNN7EXAMPLE" not in json_redacted, "Access key should be redacted"
    assert "wJalrXUtnFEMI/K7MDENG" not in json_redacted, "Secret key should be redacted"
    assert "fortigate-primary-license" not in json_redacted, "License secret should be redacted"
    print("✓ All sensitive data properly redacted")
    
    # Test import
    print("\n3. Testing JSON import...")
    imported_config = manager.import_json(json_content)
    print("✓ Import successful")
    
    # Verify imported data
    assert imported_config.aws.region == "us-east-1", "Region should match"
    assert imported_config.aws.profile == "default", "Profile should match"
    assert imported_config.aws.access_key_id == "AKIAIOSFODNN7EXAMPLE", "Access key should match"
    assert imported_config.network.vpc_id == "vpc-0123456789abcdef0", "VPC ID should match"
    assert imported_config.network.primary_public_eni_id == "eni-11111111", "ENI ID should match"
    assert imported_config.fortigate.admin_password == "AdminPass123!", "Password should match"
    assert imported_config.fortigate.instance_type == "c5.xlarge", "Instance type should match"
    assert imported_config.fortigate.licensing.license_type == "byol", "License type should match"
    assert imported_config.transit_gateway.create_new == True, "TGW create flag should match"
    assert imported_config.backend.backend_type == "s3", "Backend type should match"
    assert imported_config.backend.s3_bucket == "my-terraform-state", "S3 bucket should match"
    print("✓ All data correctly imported")
    
    print("\n✓ Task 3.2 PASSED: JSON import/export works correctly")
    return True


def test_sensitive_data_redaction():
    """Test sensitive data redaction (Task 3.3)"""
    print("\n" + "=" * 60)
    print("Task 3.3: Testing sensitive data redaction...")
    print("=" * 60)
    
    config = create_sample_config()
    manager = ConfigurationManager()
    
    # Test YAML redaction
    print("\n1. Testing YAML redaction...")
    yaml_redacted = manager.export_yaml(config, redact_sensitive=True)
    
    sensitive_values = [
        "AdminPass123!",
        "HAPass123!",
        "AKIAIOSFODNN7EXAMPLE",
        "wJalrXUtnFEMI/K7MDENG",
        "fortigate-primary-license",
        "fortigate-backup-license"
    ]
    
    for value in sensitive_values:
        assert value not in yaml_redacted, f"Sensitive value '{value}' should be redacted in YAML"
    
    assert yaml_redacted.count("[REDACTED]") >= 6, "Should have at least 6 redacted fields"
    print(f"✓ YAML redaction successful ({yaml_redacted.count('[REDACTED]')} fields redacted)")
    
    # Test JSON redaction
    print("\n2. Testing JSON redaction...")
    json_redacted = manager.export_json(config, redact_sensitive=True)
    
    for value in sensitive_values:
        assert value not in json_redacted, f"Sensitive value '{value}' should be redacted in JSON"
    
    assert json_redacted.count("[REDACTED]") >= 6, "Should have at least 6 redacted fields"
    print(f"✓ JSON redaction successful ({json_redacted.count('[REDACTED]')} fields redacted)")
    
    # Verify non-sensitive data is preserved
    print("\n3. Verifying non-sensitive data is preserved...")
    assert "us-east-1" in yaml_redacted, "Region should not be redacted"
    assert "vpc-0123456789abcdef0" in yaml_redacted, "VPC ID should not be redacted"
    assert "c5.xlarge" in yaml_redacted, "Instance type should not be redacted"
    print("✓ Non-sensitive data preserved")
    
    print("\n✓ Task 3.3 PASSED: Sensitive data redaction works correctly")
    return True


def test_configuration_validation():
    """Test configuration validation (Task 3.4)"""
    print("\n" + "=" * 60)
    print("Task 3.4: Testing configuration validation...")
    print("=" * 60)
    
    manager = ConfigurationManager()
    
    # Test valid configuration
    print("\n1. Testing valid configuration...")
    valid_config = create_sample_config()
    is_valid, errors = manager.validate_config(valid_config)
    assert is_valid == True, f"Valid config should pass validation. Errors: {errors}"
    assert len(errors) == 0, "Valid config should have no errors"
    print("✓ Valid configuration passes validation")
    
    # Test missing required fields
    print("\n2. Testing missing required fields...")
    invalid_config = DeploymentConfig(
        aws=AWSConfig(region="", profile="default"),  # Empty region
        network=NetworkConfig(
            vpc_id="",  # Empty VPC ID
            availability_zone_primary="",
            availability_zone_backup="",
            primary_public_subnet_id="",
            primary_private_subnet_id="",
            primary_ha_subnet_id="",
            primary_mgmt_subnet_id="",
            backup_public_subnet_id="",
            backup_private_subnet_id="",
            backup_ha_subnet_id="",
            backup_mgmt_subnet_id="",
            primary_public_eni_id="",
            primary_private_eni_id="",
            primary_ha_eni_id="",
            primary_mgmt_eni_id="",
            backup_public_eni_id="",
            backup_private_eni_id="",
            backup_ha_eni_id="",
            backup_mgmt_eni_id=""
        ),
        fortigate=FortiGateConfig(
            ami_id="",
            ami_discovery=AMIDiscoveryConfig(enabled=False),
            licensing=LicensingConfig(license_type="byol"),
            instance_type="",
            key_pair_name="",
            admin_password="",
            ha_password=""
        ),
        transit_gateway=TransitGatewayConfig(create_new=False),
        monitoring=MonitoringConfig(),
        backend=BackendConfig(backend_type="local")
    )
    
    is_valid, errors = manager.validate_config(invalid_config)
    assert is_valid == False, "Invalid config should fail validation"
    assert len(errors) > 0, "Invalid config should have errors"
    print(f"✓ Invalid configuration detected ({len(errors)} errors found)")
    
    # Test invalid formats
    print("\n3. Testing invalid formats...")
    invalid_format_config = create_sample_config()
    invalid_format_config.aws.region = "invalid-region"
    invalid_format_config.network.vpc_id = "invalid-vpc"
    invalid_format_config.network.primary_public_subnet_id = "invalid-subnet"
    invalid_format_config.network.primary_public_eni_id = "invalid-eni"
    invalid_format_config.fortigate.ami_id = "invalid-ami"
    
    is_valid, errors = manager.validate_config(invalid_format_config)
    assert is_valid == False, "Config with invalid formats should fail"
    assert any("region format" in err.lower() for err in errors), "Should detect invalid region format"
    assert any("vpc" in err.lower() for err in errors), "Should detect invalid VPC format"
    assert any("subnet" in err.lower() for err in errors), "Should detect invalid subnet format"
    assert any("eni" in err.lower() for err in errors), "Should detect invalid ENI format"
    assert any("ami" in err.lower() for err in errors), "Should detect invalid AMI format"
    print(f"✓ Invalid formats detected ({len(errors)} errors found)")
    
    # Test password length validation
    print("\n4. Testing password length validation...")
    short_password_config = create_sample_config()
    short_password_config.fortigate.admin_password = "short"
    short_password_config.fortigate.ha_password = "tiny"
    
    is_valid, errors = manager.validate_config(short_password_config)
    assert is_valid == False, "Config with short passwords should fail"
    assert any("password" in err.lower() and "8 characters" in err.lower() for err in errors), \
        "Should detect short passwords"
    print(f"✓ Password length validation works ({len(errors)} errors found)")
    
    # Test EIP validation
    print("\n5. Testing EIP validation...")
    eip_config = create_sample_config()
    eip_config.network.enable_eip_failover = True
    eip_config.network.primary_public_eip_id = ""
    eip_config.network.backup_public_eip_id = "invalid-eip"
    
    is_valid, errors = manager.validate_config(eip_config)
    assert is_valid == False, "Config with invalid EIP should fail"
    assert any("eip" in err.lower() for err in errors), "Should detect EIP issues"
    print(f"✓ EIP validation works ({len(errors)} errors found)")
    
    # Test Transit Gateway validation
    print("\n6. Testing Transit Gateway validation...")
    tgw_config = create_sample_config()
    tgw_config.transit_gateway.create_new = False
    tgw_config.transit_gateway.existing_tgw_id = ""
    
    is_valid, errors = manager.validate_config(tgw_config)
    assert is_valid == False, "Config without TGW ID should fail"
    assert any("transit gateway" in err.lower() for err in errors), "Should detect missing TGW ID"
    print(f"✓ Transit Gateway validation works")
    
    # Test ASN validation
    print("\n7. Testing ASN validation...")
    asn_config = create_sample_config()
    asn_config.transit_gateway.amazon_side_asn = 12345  # Invalid ASN
    asn_config.transit_gateway.fortigate_asn = 99999  # Invalid ASN
    
    is_valid, errors = manager.validate_config(asn_config)
    assert is_valid == False, "Config with invalid ASN should fail"
    assert any("asn" in err.lower() for err in errors), "Should detect invalid ASN"
    print(f"✓ ASN validation works ({len(errors)} errors found)")
    
    # Test S3 backend validation
    print("\n8. Testing S3 backend validation...")
    s3_config = create_sample_config()
    s3_config.backend.backend_type = "s3"
    s3_config.backend.s3_bucket = ""
    s3_config.backend.s3_key = ""
    s3_config.backend.s3_region = ""
    s3_config.backend.dynamodb_table = ""
    
    is_valid, errors = manager.validate_config(s3_config)
    assert is_valid == False, "Config with incomplete S3 backend should fail"
    assert any("s3" in err.lower() or "dynamodb" in err.lower() for err in errors), \
        "Should detect missing S3 backend fields"
    print(f"✓ S3 backend validation works ({len(errors)} errors found)")
    
    # Test BYOL licensing validation
    print("\n9. Testing BYOL licensing validation...")
    byol_config = create_sample_config()
    byol_config.fortigate.licensing.license_type = "byol"
    byol_config.fortigate.licensing.license_source = "secrets_manager"
    byol_config.fortigate.licensing.primary_license_secret = ""
    byol_config.fortigate.licensing.backup_license_secret = ""
    
    is_valid, errors = manager.validate_config(byol_config)
    assert is_valid == False, "Config with incomplete BYOL should fail"
    assert any("license" in err.lower() for err in errors), "Should detect missing license secrets"
    print(f"✓ BYOL licensing validation works ({len(errors)} errors found)")
    
    print("\n✓ Task 3.4 PASSED: Configuration validation works correctly")
    return True


def test_invalid_json():
    """Test error handling for invalid JSON"""
    print("\n" + "=" * 60)
    print("Testing invalid JSON handling...")
    print("=" * 60)
    
    manager = ConfigurationManager()
    
    # Test invalid JSON syntax
    print("\n1. Testing invalid JSON syntax...")
    try:
        manager.import_json('{"invalid": json content}')
        print("✗ Should have raised JSONDecodeError")
        return False
    except json.JSONDecodeError as e:
        print(f"✓ Correctly raised JSONDecodeError")
    except Exception as e:
        print(f"✓ Correctly raised error: {type(e).__name__}")
    
    # Test non-object JSON
    print("\n2. Testing non-object JSON...")
    try:
        manager.import_json('["array", "not", "object"]')
        print("✗ Should have raised ValueError")
        return False
    except ValueError as e:
        print(f"✓ Correctly raised ValueError: {e}")
    except Exception as e:
        print(f"✓ Correctly raised error: {type(e).__name__}")
    
    print("\n✓ Invalid JSON handling works correctly")
    return True


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("ConfigurationManager Test Suite - Tasks 3.2, 3.3, 3.4")
    print("=" * 60)
    
    try:
        test_json_export_import()
        test_sensitive_data_redaction()
        test_configuration_validation()
        test_invalid_json()
        
        print("\n" + "=" * 60)
        print("✓ ALL TESTS PASSED - Tasks 3.2, 3.3, 3.4 Complete")
        print("=" * 60)
        
    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
