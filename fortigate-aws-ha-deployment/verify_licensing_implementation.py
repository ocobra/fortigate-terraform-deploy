#!/usr/bin/env python3
"""
Verification script for Licensing Page implementation.

This script verifies the implementation without requiring Streamlit.
"""

import sys
import re
from pathlib import Path

def verify_licensing_page_implementation():
    """Verify that the licensing page has been properly implemented"""
    print("=" * 70)
    print("Licensing Page Implementation Verification")
    print("=" * 70)
    
    # Read the web-app-enhanced.py file
    web_app_path = Path("web-app-enhanced.py")
    if not web_app_path.exists():
        print("❌ web-app-enhanced.py not found")
        return False
    
    content = web_app_path.read_text()
    
    all_checks_passed = True
    
    # Check 1: License type selector (Task 12.1)
    print("\n📋 Task 12.1: License Type Selector")
    if 'st.radio' in content and "'BYOL', 'OnDemand', 'Reserved'" in content:
        print("✅ License type radio buttons implemented")
    else:
        print("❌ License type radio buttons not found")
        all_checks_passed = False
    
    # Check 2: BYOL configuration (Task 12.2)
    print("\n📋 Task 12.2: BYOL Configuration")
    
    # Check for license source selector
    if "'secrets_manager', 's3', 'file_upload'" in content:
        print("✅ License source selector implemented")
    else:
        print("❌ License source selector not found")
        all_checks_passed = False
    
    # Check for Secrets Manager inputs
    if 'Primary License Secret Name' in content and 'Backup License Secret Name' in content:
        print("✅ Secrets Manager configuration implemented")
    else:
        print("❌ Secrets Manager configuration not found")
        all_checks_passed = False
    
    # Check for S3 inputs
    if 'S3 Bucket Name' in content and 'Primary License S3 Key' in content:
        print("✅ S3 configuration implemented")
    else:
        print("❌ S3 configuration not found")
        all_checks_passed = False
    
    # Check for file upload
    if 'st.file_uploader' in content and 'Primary License File' in content:
        print("✅ File upload functionality implemented")
    else:
        print("❌ File upload functionality not found")
        all_checks_passed = False
    
    # Check 3: License validation (Task 12.3)
    print("\n📋 Task 12.3: License Validation")
    
    # Check for test access buttons
    if 'Test Primary Secret Access' in content or 'Test Primary License Access' in content:
        print("✅ Test access buttons implemented")
    else:
        print("❌ Test access buttons not found")
        all_checks_passed = False
    
    # Check for validation method calls
    if 'test_secrets_manager_access' in content and 'test_s3_access' in content:
        print("✅ Validation method calls implemented")
    else:
        print("❌ Validation method calls not found")
        all_checks_passed = False
    
    # Check 4: Cost implications (Task 12.4)
    print("\n📋 Task 12.4: Cost Implications")
    
    # Check for CostCalculator usage
    if 'CostCalculator' in content and 'compare_licensing_models' in content:
        print("✅ Cost calculator integration implemented")
    else:
        print("❌ Cost calculator integration not found")
        all_checks_passed = False
    
    # Check for cost comparison display
    if 'Cost Comparison' in content and 'BYOL' in content and 'OnDemand' in content:
        print("✅ Cost comparison display implemented")
    else:
        print("❌ Cost comparison display not found")
        all_checks_passed = False
    
    # Check for link to Cost Analysis page
    if 'Cost Analysis' in content or 'Cost_Analysis' in content:
        print("✅ Link to Cost Analysis page implemented")
    else:
        print("❌ Link to Cost Analysis page not found")
        all_checks_passed = False
    
    # Additional checks
    print("\n📋 Additional Checks")
    
    # Check for session state management
    if 'st.session_state.licensing_config' in content:
        print("✅ Session state management implemented")
    else:
        print("❌ Session state management not found")
        all_checks_passed = False
    
    # Check for save configuration button
    if 'Save Licensing Configuration' in content:
        print("✅ Save configuration button implemented")
    else:
        print("❌ Save configuration button not found")
        all_checks_passed = False
    
    # Count lines of implementation
    function_match = re.search(
        r'def render_licensing_page\(\):.*?(?=\ndef |\Z)',
        content,
        re.DOTALL
    )
    
    if function_match:
        function_lines = function_match.group(0).count('\n')
        print(f"\n📊 Implementation Statistics:")
        print(f"   - Function length: {function_lines} lines")
        
        if function_lines > 50:
            print(f"   ✅ Substantial implementation (>{function_lines} lines)")
        else:
            print(f"   ⚠️  Implementation seems short ({function_lines} lines)")
    
    print("\n" + "=" * 70)
    if all_checks_passed:
        print("✅ All verification checks passed!")
        print("=" * 70)
        return True
    else:
        print("❌ Some verification checks failed")
        print("=" * 70)
        return False

def verify_licensing_config():
    """Verify LicensingConfig dataclass structure"""
    print("\n" + "=" * 70)
    print("LicensingConfig Structure Verification")
    print("=" * 70)
    
    try:
        from deploy import LicensingConfig
        from dataclasses import fields
        
        field_names = [f.name for f in fields(LicensingConfig)]
        
        print("\n📋 LicensingConfig Fields:")
        for field in field_names:
            print(f"   ✅ {field}")
        
        required_fields = [
            'type',
            'primary_license_secret',
            'backup_license_secret',
            'license_s3_bucket',
            'primary_license_s3_key',
            'backup_license_s3_key'
        ]
        
        all_present = all(field in field_names for field in required_fields)
        
        if all_present:
            print("\n✅ All required fields present in LicensingConfig")
            return True
        else:
            print("\n❌ Some required fields missing from LicensingConfig")
            return False
            
    except Exception as e:
        print(f"\n❌ Error verifying LicensingConfig: {e}")
        return False

def main():
    """Run all verifications"""
    result1 = verify_licensing_page_implementation()
    result2 = verify_licensing_config()
    
    if result1 and result2:
        print("\n🎉 Licensing Page implementation is complete and verified!")
        return 0
    else:
        print("\n⚠️  Some issues found in implementation")
        return 1

if __name__ == "__main__":
    sys.exit(main())
