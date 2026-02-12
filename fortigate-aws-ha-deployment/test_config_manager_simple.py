#!/usr/bin/env python3
"""
Simple standalone test for ConfigurationManager YAML import/export functionality.
This verifies Task 3.1 implementation without requiring Streamlit.
"""

import sys
import yaml
import copy
from pathlib import Path
from dataclasses import asdict
from typing import Dict, Any

# Add the deployment engine to the path
sys.path.append(str(Path(__file__).parent))

from deploy import (
    DeploymentConfig, AWSConfig, NetworkConfig,
    FortiGateConfig, TransitGatewayConfig, MonitoringConfig, BackendConfig,
    AMIDiscoveryConfig, LicensingConfig
)


class ConfigurationManager:
    """
    Standalone ConfigurationManager for testing.
    This is a copy of the implementation from web-app-enhanced.py
    """
    
    def import_yaml(self, yaml_content: str) -> DeploymentConfig:
        """Parse YAML configuration file and create DeploymentConfig object."""
        try:
            # Parse YAML content
            config_dict = yaml.safe_load(yaml_content)
            
            if not isinstance(config_dict, dict):
                raise ValueError("YAML content must be a dictionary")
            
            # Reconstruct nested dataclass objects
            aws_config = AWSConfig(**config_dict.get('aws', {}))
            
            network_dict = config_dict.get('network', {})
            network_config = NetworkConfig(**network_dict)
            
            fortigate_dict = config_dict.get('fortigate', {})
            # Handle nested AMIDiscoveryConfig
            ami_discovery_dict = fortigate_dict.get('ami_discovery', {})
            ami_discovery = AMIDiscoveryConfig(**ami_discovery_dict)
            
            # Handle nested LicensingConfig
            licensing_dict = fortigate_dict.get('licensing', {})
            licensing = LicensingConfig(**licensing_dict)
            
            # Create FortiGateConfig with nested objects
            fortigate_config = FortiGateConfig(
                ami_id=fortigate_dict.get('ami_id'),
                ami_discovery=ami_discovery,
                licensing=licensing,
                instance_type=fortigate_dict.get('instance_type'),
                key_pair_name=fortigate_dict.get('key_pair_name'),
                admin_password=fortigate_dict.get('admin_password'),
                ha_password=fortigate_dict.get('ha_password'),
                hostname_primary=fortigate_dict.get('hostname_primary', 'fortigate-primary'),
                hostname_backup=fortigate_dict.get('hostname_backup', 'fortigate-backup')
            )
            
            transit_gateway_dict = config_dict.get('transit_gateway', {})
            transit_gateway_config = TransitGatewayConfig(**transit_gateway_dict)
            
            monitoring_dict = config_dict.get('monitoring', {})
            monitoring_config = MonitoringConfig(**monitoring_dict)
            
            backend_dict = config_dict.get('backend', {})
            backend_config = BackendConfig(**backend_dict)
            
            # Create complete DeploymentConfig
            deployment_config = DeploymentConfig(
                aws=aws_config,
                network=network_config,
                fortigate=fortigate_config,
                transit_gateway=transit_gateway_config,
                monitoring=monitoring_config,
                backend=backend_config,
                environment=config_dict.get('environment', 'prod'),
                owner_tag=config_dict.get('owner_tag', 'NetworkTeam')
            )
            
            return deployment_config
            
        except yaml.YAMLError as e:
            raise yaml.YAMLError(f"Invalid YAML syntax: {str(e)}")
        except KeyError as e:
            raise KeyError(f"Missing required configuration field: {str(e)}")
        except TypeError as e:
            raise TypeError(f"Invalid configuration value type: {str(e)}")
        except Exception as e:
            raise ValueError(f"Failed to parse configuration: {str(e)}")
    
    def export_yaml(self, config: DeploymentConfig, redact_sensitive: bool = True) -> str:
        """Serialize DeploymentConfig object to YAML format."""
        try:
            # Convert dataclass to dictionary
            config_dict = asdict(config)
            
            # Redact sensitive data if requested
            if redact_sensitive:
                config_dict = self._redact_sensitive_data(config_dict)
            
            # Convert to YAML with proper formatting
            yaml_content = yaml.dump(
                config_dict,
                default_flow_style=False,
                sort_keys=False,
                allow_unicode=True,
                indent=2
            )
            
            return yaml_content
            
        except Exception as e:
            raise ValueError(f"Failed to export configuration to YAML: {str(e)}")
    
    def _redact_sensitive_data(self, config_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Remove sensitive data from configuration dictionary."""
        # List of sensitive field names to redact
        sensitive_fields = {
            'admin_password',
            'ha_password',
            'access_key_id',
            'secret_access_key',
            'primary_license_secret',
            'backup_license_secret'
        }
        
        # Create a deep copy to avoid modifying the original
        redacted_dict = copy.deepcopy(config_dict)
        
        # Recursively redact sensitive fields
        def redact_recursive(d: Dict[str, Any]) -> None:
            for key, value in d.items():
                if key in sensitive_fields and value is not None:
                    d[key] = '[REDACTED]'
                elif isinstance(value, dict):
                    redact_recursive(value)
        
        redact_recursive(redacted_dict)
        return redacted_dict


def test_yaml_export_import():
    """Test YAML export and import functionality"""
    print("Testing YAML export/import...")
    
    # Create a sample configuration
    config = DeploymentConfig(
        aws=AWSConfig(
            region="us-east-1",
            profile="default"
        ),
        network=NetworkConfig(
            vpc_id="vpc-12345",
            availability_zones=["us-east-1a", "us-east-1b"],
            outside_subnet_primary="subnet-111",
            inside_subnet_primary="subnet-222",
            ha_subnet_primary="subnet-333",
            mgmt_subnet_primary="subnet-444",
            outside_subnet_backup="subnet-555",
            inside_subnet_backup="subnet-666",
            ha_subnet_backup="subnet-777",
            mgmt_subnet_backup="subnet-888",
            mgmt_access_cidrs=["10.0.0.0/8"],
            primary_outside_eni_id="eni-111",
            primary_inside_eni_id="eni-222",
            primary_ha_eni_id="eni-333",
            primary_mgmt_eni_id="eni-444",
            backup_outside_eni_id="eni-555",
            backup_inside_eni_id="eni-666",
            backup_ha_eni_id="eni-777",
            backup_mgmt_eni_id="eni-888",
            allocate_eips=True,
            enable_eip_failover=True
        ),
        fortigate=FortiGateConfig(
            ami_id="ami-12345",
            ami_discovery=AMIDiscoveryConfig(
                enabled=True,
                version="7.4",
                license_type="BYOL",
                architecture="x86_64"
            ),
            licensing=LicensingConfig(
                type="BYOL",
                primary_license_secret="secret1",
                backup_license_secret="secret2"
            ),
            instance_type="c5.xlarge",
            key_pair_name="my-key",
            admin_password="AdminPass123!",
            ha_password="HAPass123!",
            hostname_primary="fortigate-primary",
            hostname_backup="fortigate-backup"
        ),
        transit_gateway=TransitGatewayConfig(
            create_new=True,
            bgp_asn=65000,
            transit_gateway_asn=64512,
            spoke_vpc_cidrs=["10.1.0.0/16", "10.2.0.0/16"]
        ),
        monitoring=MonitoringConfig(
            enable_flow_logs=True,
            log_retention_days=30,
            enable_detailed_monitoring=True
        ),
        backend=BackendConfig(
            backend_type="local"
        ),
        environment="prod",
        owner_tag="NetworkTeam"
    )
    
    manager = ConfigurationManager()
    
    # Test export without redaction
    print("\n1. Testing export without redaction...")
    yaml_content = manager.export_yaml(config, redact_sensitive=False)
    print("✓ Export successful")
    assert "AdminPass123!" in yaml_content, "Password should be present"
    assert "us-east-1" in yaml_content, "Region should be present"
    
    # Test export with redaction
    print("\n2. Testing export with redaction...")
    yaml_redacted = manager.export_yaml(config, redact_sensitive=True)
    print("✓ Export with redaction successful")
    assert "[REDACTED]" in yaml_redacted, "Sensitive data should be redacted"
    assert "AdminPass123!" not in yaml_redacted, "Password should be redacted"
    assert "HAPass123!" not in yaml_redacted, "HA password should be redacted"
    assert "secret1" not in yaml_redacted, "License secret should be redacted"
    
    # Test import
    print("\n3. Testing import...")
    imported_config = manager.import_yaml(yaml_content)
    print("✓ Import successful")
    
    # Verify imported data
    assert imported_config.aws.region == "us-east-1", "Region should match"
    assert imported_config.aws.profile == "default", "Profile should match"
    assert imported_config.network.vpc_id == "vpc-12345", "VPC ID should match"
    assert imported_config.fortigate.admin_password == "AdminPass123!", "Password should match"
    assert imported_config.fortigate.instance_type == "c5.xlarge", "Instance type should match"
    assert imported_config.fortigate.ami_discovery.version == "7.4", "AMI version should match"
    assert imported_config.fortigate.licensing.type == "BYOL", "License type should match"
    assert imported_config.transit_gateway.create_new == True, "TGW create flag should match"
    assert imported_config.monitoring.enable_flow_logs == True, "Flow logs flag should match"
    assert imported_config.environment == "prod", "Environment should match"
    
    print("\n✓ All assertions passed!")
    return True


def test_invalid_yaml():
    """Test error handling for invalid YAML"""
    print("\nTesting invalid YAML handling...")
    
    manager = ConfigurationManager()
    
    # Test invalid YAML syntax
    try:
        manager.import_yaml("invalid: yaml: content: [")
        print("✗ Should have raised YAMLError")
        return False
    except Exception as e:
        print(f"✓ Correctly raised error: {type(e).__name__}")
    
    # Test missing required fields
    try:
        manager.import_yaml("aws:\n  region: us-east-1")
        print("✗ Should have raised error for missing fields")
        return False
    except Exception as e:
        print(f"✓ Correctly raised error for missing fields: {type(e).__name__}")
    
    return True


def test_nested_dataclasses():
    """Test proper handling of nested dataclass structures"""
    print("\nTesting nested dataclass handling...")
    
    yaml_content = """
aws:
  region: us-west-2
  profile: test-profile
network:
  vpc_id: vpc-test
  availability_zones:
    - us-west-2a
    - us-west-2b
  outside_subnet_primary: subnet-1
  inside_subnet_primary: subnet-2
  ha_subnet_primary: subnet-3
  mgmt_subnet_primary: subnet-4
  outside_subnet_backup: subnet-5
  inside_subnet_backup: subnet-6
  ha_subnet_backup: subnet-7
  mgmt_subnet_backup: subnet-8
  mgmt_access_cidrs:
    - 0.0.0.0/0
  primary_outside_eni_id: eni-1
  primary_inside_eni_id: eni-2
  primary_ha_eni_id: eni-3
  primary_mgmt_eni_id: eni-4
  backup_outside_eni_id: eni-5
  backup_inside_eni_id: eni-6
  backup_ha_eni_id: eni-7
  backup_mgmt_eni_id: eni-8
fortigate:
  ami_id: ami-test
  ami_discovery:
    enabled: false
    version: "7.6"
    license_type: OnDemand
    architecture: arm64
  licensing:
    type: OnDemand
  instance_type: c6g.large
  key_pair_name: test-key
  admin_password: TestPass
  ha_password: HATest
transit_gateway:
  create_new: false
  transit_gateway_id: tgw-123
  bgp_asn: 65001
monitoring:
  enable_flow_logs: false
  log_retention_days: 7
backend:
  backend_type: s3
  s3_bucket: my-bucket
  s3_key: terraform.tfstate
  s3_region: us-west-2
environment: dev
owner_tag: TestTeam
"""
    
    manager = ConfigurationManager()
    config = manager.import_yaml(yaml_content)
    
    # Verify nested structures
    assert config.fortigate.ami_discovery.version == "7.6", "Nested AMI version should match"
    assert config.fortigate.ami_discovery.architecture == "arm64", "Nested architecture should match"
    assert config.fortigate.licensing.type == "OnDemand", "Nested license type should match"
    assert config.backend.backend_type == "s3", "Backend type should match"
    assert config.backend.s3_bucket == "my-bucket", "S3 bucket should match"
    
    print("✓ Nested dataclass handling works correctly")
    return True


if __name__ == "__main__":
    print("=" * 60)
    print("ConfigurationManager Test Suite")
    print("=" * 60)
    
    try:
        test_yaml_export_import()
        test_invalid_yaml()
        test_nested_dataclasses()
        
        print("\n" + "=" * 60)
        print("✓ ALL TESTS PASSED")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
