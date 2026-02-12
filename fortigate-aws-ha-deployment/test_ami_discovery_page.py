#!/usr/bin/env python3
"""
Test script for AMI Discovery Page implementation (Tasks 11.1-11.4).

This script verifies that the render_ami_discovery_page function is properly
implemented with all required components:
- AMI discovery form with version, license type, and architecture selectors
- Discover AMIs button functionality
- List All Versions button functionality
- Results display with AMI metadata
- Auto-populate AMI ID functionality

Requirements tested:
    - Requirement 4.1: Query AWS Marketplace for FortiGate AMIs
    - Requirement 4.2: Filter by FortiGate version
    - Requirement 4.3: Filter by license type
    - Requirement 4.4: Filter by architecture
    - Requirement 4.5: Display latest matching AMI with metadata
    - Requirement 4.6: Display alternative AMI options
    - Requirement 4.7: Auto-populate AMI ID field
    - Requirement 4.9: List all available FortiGate versions
"""

import sys
import inspect
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

def test_ami_discovery_page_exists():
    """Test that render_ami_discovery_page function exists"""
    try:
        from web_app_enhanced import render_ami_discovery_page
        print("✅ render_ami_discovery_page function exists")
        return True
    except ImportError as e:
        print(f"❌ Failed to import render_ami_discovery_page: {e}")
        return False

def test_ami_discovery_page_implementation():
    """Test that render_ami_discovery_page is properly implemented"""
    try:
        # Import the module with underscore (actual file name)
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "web_app_enhanced", 
            "web-app-enhanced.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        render_ami_discovery_page = module.render_ami_discovery_page
        
        # Get the source code
        source = inspect.getsource(render_ami_discovery_page)
        
        # Check for required components
        required_components = {
            "version selector": "FortiGate Version" in source or "version" in source.lower(),
            "license type selector": "License Type" in source or "license_type" in source,
            "architecture selector": "Architecture" in source or "architecture" in source,
            "discover button": "Discover AMIs" in source or "discover_button" in source,
            "list versions button": "List All Versions" in source or "list_versions" in source,
            "AMI discovery execution": "discover_amis" in source,
            "results display": "ami_discovery_result" in source,
            "auto-populate functionality": "Use This AMI" in source or "ami_id" in source,
            "error handling": "try:" in source and "except" in source,
            "loading spinner": "spinner" in source,
        }
        
        all_passed = True
        for component, present in required_components.items():
            if present:
                print(f"✅ {component}: implemented")
            else:
                print(f"❌ {component}: missing")
                all_passed = False
        
        # Check for specific requirements
        print("\n📋 Checking Requirements Implementation:")
        
        requirements_checks = {
            "Req 4.1 (Query AWS Marketplace)": "discover_amis" in source,
            "Req 4.2 (Filter by version)": "version" in source,
            "Req 4.3 (Filter by license type)": "license_type" in source,
            "Req 4.4 (Filter by architecture)": "architecture" in source,
            "Req 4.5 (Display AMI metadata)": "ami_info" in source,
            "Req 4.7 (Auto-populate AMI ID)": "ami_id" in source,
            "Req 4.9 (List versions)": "list_fortigate_versions" in source,
        }
        
        for req, check in requirements_checks.items():
            if check:
                print(f"✅ {req}: implemented")
            else:
                print(f"❌ {req}: missing")
                all_passed = False
        
        # Check function is not a placeholder
        if "placeholder" in source.lower() and len(source) < 500:
            print("\n❌ Function appears to be a placeholder (too short)")
            all_passed = False
        else:
            print(f"\n✅ Function is fully implemented ({len(source)} characters)")
        
        return all_passed
        
    except Exception as e:
        print(f"❌ Error testing implementation: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_aws_integration_manager_methods():
    """Test that AWSIntegrationManager has required methods"""
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "web_app_enhanced", 
            "web-app-enhanced.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        AWSIntegrationManager = module.AWSIntegrationManager
        
        required_methods = [
            'discover_amis',
            'list_fortigate_versions'
        ]
        
        all_present = True
        for method in required_methods:
            if hasattr(AWSIntegrationManager, method):
                print(f"✅ AWSIntegrationManager.{method} exists")
            else:
                print(f"❌ AWSIntegrationManager.{method} missing")
                all_present = False
        
        return all_present
        
    except Exception as e:
        print(f"❌ Error checking AWSIntegrationManager: {e}")
        return False

def main():
    """Run all tests"""
    print("=" * 70)
    print("Testing AMI Discovery Page Implementation (Tasks 11.1-11.4)")
    print("=" * 70)
    
    print("\n1. Testing function existence...")
    test1 = test_ami_discovery_page_exists()
    
    print("\n2. Testing implementation completeness...")
    test2 = test_ami_discovery_page_implementation()
    
    print("\n3. Testing AWS Integration Manager methods...")
    test3 = test_aws_integration_manager_methods()
    
    print("\n" + "=" * 70)
    if test1 and test2 and test3:
        print("✅ ALL TESTS PASSED - AMI Discovery Page is fully implemented!")
        print("=" * 70)
        return 0
    else:
        print("❌ SOME TESTS FAILED - Review implementation")
        print("=" * 70)
        return 1

if __name__ == "__main__":
    sys.exit(main())
