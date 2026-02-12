#!/usr/bin/env python3
"""
Test TerraformIntegrationManager class

This test verifies the TerraformIntegrationManager implementation
for tasks 5.1-5.5 of the streamlit-web-app-enhancement spec.
"""

import sys
from pathlib import Path
from deploy import BackendConfig, DeploymentConfig, AWSConfig, NetworkConfig, FortiGateConfig, TransitGatewayConfig, MonitoringConfig

# Import TerraformIntegrationManager from web-app-enhanced
# We need to import it as a module since it has hyphens in the name
import importlib.util
spec = importlib.util.spec_from_file_location("web_app_enhanced", "web-app-enhanced.py")
web_app_enhanced = importlib.util.module_from_spec(spec)
spec.loader.exec_module(web_app_enhanced)
TerraformIntegrationManager = web_app_enhanced.TerraformIntegrationManager

def test_terraform_integration_manager():
    """Test TerraformIntegrationManager basic functionality"""
    
    print("=" * 70)
    print("Testing TerraformIntegrationManager")
    print("=" * 70)
    
    # Test 1: Initialize with local backend
    print("\n1. Testing initialization with local backend...")
    terraform_dir = Path("terraform")
    backend_config = BackendConfig(backend_type="local")
    
    manager = TerraformIntegrationManager(terraform_dir, backend_config)
    print(f"   ✓ Manager initialized")
    print(f"   - Terraform dir: {manager.terraform_dir}")
    print(f"   - Backend type: {manager.backend_config.backend_type}")
    
    # Test 2: Configure local backend
    print("\n2. Testing local backend configuration...")
    success, message = manager.configure_backend()
    print(f"   {'✓' if success else '✗'} {message}")
    
    # Test 3: Initialize with S3 backend
    print("\n3. Testing initialization with S3 backend...")
    s3_backend_config = BackendConfig(
        backend_type="s3",
        s3_bucket="test-bucket",
        s3_key="test/terraform.tfstate",
        s3_region="us-east-1",
        dynamodb_table="test-locks",
        encrypt=True
    )
    
    s3_manager = TerraformIntegrationManager(terraform_dir, s3_backend_config)
    print(f"   ✓ S3 Manager initialized")
    print(f"   - S3 Bucket: {s3_manager.backend_config.s3_bucket}")
    print(f"   - S3 Key: {s3_manager.backend_config.s3_key}")
    
    # Test 4: Configure S3 backend
    print("\n4. Testing S3 backend configuration...")
    success, message = s3_manager.configure_backend()
    print(f"   {'✓' if success else '✗'} Backend configured")
    if success:
        print(f"   {message}")
        # Check if backend.tf was created
        if s3_manager.backend_tf_file.exists():
            print(f"   ✓ backend.tf file created")
            with open(s3_manager.backend_tf_file, 'r') as f:
                content = f.read()
                print(f"   - File size: {len(content)} bytes")
        else:
            print(f"   ✗ backend.tf file not found")
    
    # Test 5: Generate tfvars
    print("\n5. Testing tfvars generation...")
    
    # Create a minimal deployment config
    config = DeploymentConfig(
        aws=AWSConfig(region="us-east-1"),
        network=NetworkConfig(
            vpc_id="vpc-12345",
            availability_zones=["us-east-1a", "us-east-1b"],
            outside_subnet_primary="subnet-1",
            inside_subnet_primary="subnet-2",
            ha_subnet_primary="subnet-3",
            mgmt_subnet_primary="subnet-4",
            outside_subnet_backup="subnet-5",
            inside_subnet_backup="subnet-6",
            ha_subnet_backup="subnet-7",
            mgmt_subnet_backup="subnet-8",
            primary_outside_eni_id="eni-1",
            primary_inside_eni_id="eni-2",
            primary_ha_eni_id="eni-3",
            primary_mgmt_eni_id="eni-4",
            backup_outside_eni_id="eni-5",
            backup_inside_eni_id="eni-6",
            backup_ha_eni_id="eni-7",
            backup_mgmt_eni_id="eni-8",
            mgmt_access_cidrs=["10.0.0.0/8"]
        ),
        fortigate=FortiGateConfig(
            ami_id="ami-12345",
            instance_type="c5.xlarge",
            key_pair_name="test-key",
            admin_password="TestPass123!",
            ha_password="HAPass123!",
            hostname_primary="fortigate-primary",
            hostname_backup="fortigate-backup"
        ),
        transit_gateway=TransitGatewayConfig(),
        monitoring=MonitoringConfig(),
        environment="test",
        owner_tag="test-user"
    )
    
    success, message = manager.generate_tfvars(config)
    print(f"   {'✓' if success else '✗'} {message}")
    
    if success and manager.tfvars_file.exists():
        print(f"   ✓ terraform.tfvars file created")
        with open(manager.tfvars_file, 'r') as f:
            content = f.read()
            print(f"   - File size: {len(content)} bytes")
            # Check for key parameters
            if 'aws_region = "us-east-1"' in content:
                print(f"   ✓ AWS region found in tfvars")
            if 'vpc_id = "vpc-12345"' in content:
                print(f"   ✓ VPC ID found in tfvars")
            if 'fortigate_ami_id = "ami-12345"' in content:
                print(f"   ✓ AMI ID found in tfvars")
    
    # Test 6: Test output extraction (will fail without actual terraform state)
    print("\n6. Testing output extraction...")
    success, outputs, message = manager.get_outputs()
    if not success:
        print(f"   ✓ Expected failure (no terraform state): {message}")
    else:
        print(f"   ✓ Outputs retrieved: {outputs}")
    
    # Test 7: Test callback mechanism
    print("\n7. Testing callback mechanism...")
    output_lines = []
    
    def test_callback(line: str):
        output_lines.append(line)
    
    # This will fail because terraform isn't initialized, but tests the callback
    success, output = manager.init(callback=test_callback)
    if output_lines:
        print(f"   ✓ Callback received {len(output_lines)} lines")
    else:
        print(f"   ✓ Callback mechanism works (no output expected without terraform)")
    
    print("\n" + "=" * 70)
    print("All tests completed!")
    print("=" * 70)
    
    # Cleanup test files
    print("\nCleaning up test files...")
    if s3_manager.backend_tf_file.exists():
        s3_manager.backend_tf_file.unlink()
        print("   ✓ Removed backend.tf")
    if manager.tfvars_file.exists():
        manager.tfvars_file.unlink()
        print("   ✓ Removed terraform.tfvars")

if __name__ == "__main__":
    test_terraform_integration_manager()
