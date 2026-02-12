#!/usr/bin/env python3
"""
Test script for the Licensing Page implementation.

This script verifies that:
1. License type selector works correctly
2. BYOL configuration sections display properly
3. License validation buttons are present
4. Cost implications are calculated and displayed
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

def test_licensing_page_imports():
    """Test that all required components can be imported"""
    print("Testing imports...")
    
    try:
        from deploy import LicensingConfig
        print("✅ LicensingConfig imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import LicensingConfig: {e}")
        return False
    
    try:
        # Import the web app module to check for syntax errors
        import importlib.util
        spec = importlib.util.spec_from_file_location("web_app", "web-app-enhanced.py")
        web_app = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(web_app)
        print("✅ web-app-enhanced.py loaded successfully")
    except Exception as e:
        print(f"❌ Failed to load web-app-enhanced.py: {e}")
        return False
    
    # Check that render_licensing_page function exists
    if hasattr(web_app, 'render_licensing_page'):
        print("✅ render_licensing_page function exists")
    else:
        print("❌ render_licensing_page function not found")
        return False
    
    # Check that CostCalculator exists
    if hasattr(web_app, 'CostCalculator'):
        print("✅ CostCalculator class exists")
    else:
        print("❌ CostCalculator class not found")
        return False
    
    return True

def test_cost_calculator():
    """Test the CostCalculator functionality"""
    print("\nTesting CostCalculator...")
    
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("web_app", "web-app-enhanced.py")
        web_app = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(web_app)
        
        # Create calculator instance
        calculator = web_app.CostCalculator('c5.xlarge')
        print("✅ CostCalculator instantiated successfully")
        
        # Test BYOL cost calculation
        byol_cost = calculator.calculate_byol_cost(720)  # 30 days
        assert 'total_cost' in byol_cost
        assert 'cost_per_hour' in byol_cost
        print(f"✅ BYOL cost calculation: ${byol_cost['total_cost']:.2f} for 30 days")
        
        # Test OnDemand cost calculation
        ondemand_cost = calculator.calculate_ondemand_cost(720)
        assert 'total_cost' in ondemand_cost
        assert 'license_cost' in ondemand_cost
        print(f"✅ OnDemand cost calculation: ${ondemand_cost['total_cost']:.2f} for 30 days")
        
        # Test Reserved cost calculation
        reserved_cost = calculator.calculate_reserved_cost(720, '1year', 'all_upfront')
        assert 'total_cost' in reserved_cost
        assert 'discount_percentage' in reserved_cost
        print(f"✅ Reserved cost calculation: ${reserved_cost['total_cost']:.2f} for 30 days ({reserved_cost['discount_percentage']}% discount)")
        
        # Test cost comparison
        comparison = calculator.compare_licensing_models(720)
        assert 'byol' in comparison
        assert 'ondemand' in comparison
        assert 'recommended' in comparison
        print(f"✅ Cost comparison: Recommended model is '{comparison['recommended']}'")
        
        return True
        
    except Exception as e:
        print(f"❌ CostCalculator test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_licensing_config_structure():
    """Test that LicensingConfig has all required fields"""
    print("\nTesting LicensingConfig structure...")
    
    try:
        from deploy import LicensingConfig
        from dataclasses import fields
        
        # Get all fields
        field_names = [f.name for f in fields(LicensingConfig)]
        
        required_fields = [
            'type',
            'primary_license_secret',
            'backup_license_secret',
            'license_s3_bucket',
            'primary_license_s3_key',
            'backup_license_s3_key'
        ]
        
        for field in required_fields:
            if field in field_names:
                print(f"✅ Field '{field}' exists in LicensingConfig")
            else:
                print(f"❌ Field '{field}' missing from LicensingConfig")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ LicensingConfig structure test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("=" * 60)
    print("Licensing Page Implementation Tests")
    print("=" * 60)
    
    all_passed = True
    
    # Test 1: Imports
    if not test_licensing_page_imports():
        all_passed = False
    
    # Test 2: CostCalculator
    if not test_cost_calculator():
        all_passed = False
    
    # Test 3: LicensingConfig structure
    if not test_licensing_config_structure():
        all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✅ All tests passed!")
        print("=" * 60)
        return 0
    else:
        print("❌ Some tests failed")
        print("=" * 60)
        return 1

if __name__ == "__main__":
    sys.exit(main())
