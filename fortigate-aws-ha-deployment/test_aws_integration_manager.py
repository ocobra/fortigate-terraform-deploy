#!/usr/bin/env python3
"""
Test script for AWSIntegrationManager class.

This script tests the basic functionality of the AWSIntegrationManager class
to ensure it properly wraps ConfigurationValidator, AMIDiscovery, and LicenseManager.
"""

import sys
from pathlib import Path

# Add parent directory to path to import from deploy.py and web-app-enhanced.py
sys.path.insert(0, str(Path(__file__).parent))

from deploy import AWSConfig

# Import from web-app-enhanced.py (note: Python converts hyphens to underscores in imports)
import importlib.util
spec = importlib.util.spec_from_file_location("web_app_enhanced", "web-app-enhanced.py")
web_app_enhanced = importlib.util.module_from_spec(spec)
spec.loader.exec_module(web_app_enhanced)
AWSIntegrationManager = web_app_enhanced.AWSIntegrationManager


def test_aws_integration_manager():
    """Test AWSIntegrationManager initialization and basic functionality."""
    
    print("=" * 80)
    print("Testing AWSIntegrationManager")
    print("=" * 80)
    
    # Test 1: Create AWSIntegrationManager with default credentials
    print("\n1. Testing AWSIntegrationManager initialization...")
    aws_config = AWSConfig(
        region="us-east-1",
        profile=None,
        access_key_id=None,
        secret_access_key=None
    )
    
    manager = AWSIntegrationManager(aws_config)
    print("✅ AWSIntegrationManager created successfully")
    
    # Test 2: Create AWS session
    print("\n2. Testing AWS session creation...")
    success, message = manager.create_session()
    print(f"   Result: {message}")
    
    if not success:
        print("⚠️  AWS session creation failed (this is expected if no AWS credentials are configured)")
        print("   Skipping remaining tests that require AWS access")
        return
    
    print("✅ AWS session created successfully")
    
    # Test 3: Verify helper classes are initialized
    print("\n3. Verifying helper classes are initialized...")
    assert manager.validator is not None, "ConfigurationValidator not initialized"
    print("   ✅ ConfigurationValidator initialized")
    
    assert manager.ami_discovery is not None, "AMIDiscovery not initialized"
    print("   ✅ AMIDiscovery initialized")
    
    assert manager.license_manager is not None, "LicenseManager not initialized"
    print("   ✅ LicenseManager initialized")
    
    # Test 4: Test validation methods (with invalid IDs to avoid actual AWS calls)
    print("\n4. Testing validation methods with invalid IDs...")
    
    # Test VPC validation
    is_valid, msg = manager.validate_vpc("vpc-invalid")
    print(f"   VPC validation: {msg}")
    
    # Test subnet validation
    is_valid, msg = manager.validate_subnets(["subnet-invalid"], ["us-east-1a"])
    print(f"   Subnet validation: {msg}")
    
    # Test ENI validation
    is_valid, msg = manager.validate_enis(["eni-invalid"])
    print(f"   ENI validation: {msg}")
    
    # Test EIP validation
    is_valid, msg = manager.validate_eips(["eipalloc-invalid"])
    print(f"   EIP validation: {msg}")
    
    # Test Transit Gateway validation
    is_valid, msg = manager.validate_transit_gateway("tgw-invalid")
    print(f"   Transit Gateway validation: {msg}")
    
    # Test AMI validation
    is_valid, msg = manager.validate_ami("ami-invalid")
    print(f"   AMI validation: {msg}")
    
    # Test key pair validation
    is_valid, msg = manager.validate_key_pair("nonexistent-key")
    print(f"   Key pair validation: {msg}")
    
    print("\n✅ All validation methods are callable")
    
    # Test 5: Test AMI discovery methods
    print("\n5. Testing AMI discovery methods...")
    
    # List FortiGate versions
    success, versions, msg = manager.list_fortigate_versions()
    print(f"   List versions: {msg}")
    if success and versions:
        print(f"   Found versions: {', '.join(versions[:5])}...")
    
    # Discover AMI (this will make a real AWS API call)
    print("\n   Attempting to discover FortiGate 7.6 BYOL AMI...")
    success, ami_info, msg = manager.discover_amis("7.6", "BYOL", "x86_64")
    print(f"   Discover AMI: {msg}")
    if success and ami_info:
        print(f"   AMI ID: {ami_info['id']}")
        print(f"   AMI Name: {ami_info['name']}")
        print(f"   Created: {ami_info['creation_date']}")
    
    print("\n✅ AMI discovery methods are callable")
    
    # Test 6: Test license manager methods (without actual secrets/S3)
    print("\n6. Testing license manager methods...")
    
    # Test Secrets Manager access (will fail without actual secret)
    success, msg = manager.test_secrets_manager_access("nonexistent-secret")
    print(f"   Secrets Manager test: {msg}")
    
    # Test S3 access (will fail without actual bucket/key)
    success, msg = manager.test_s3_access("nonexistent-bucket", "nonexistent-key")
    print(f"   S3 test: {msg}")
    
    print("\n✅ License manager methods are callable")
    
    print("\n" + "=" * 80)
    print("All tests completed successfully!")
    print("=" * 80)


if __name__ == "__main__":
    try:
        test_aws_integration_manager()
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
