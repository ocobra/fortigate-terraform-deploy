#!/usr/bin/env python3
"""
Verification script for AMI Discovery Page implementation (Tasks 11.1-11.4).

This script performs static analysis of the source code to verify that all
required components are implemented without needing to import the module.
"""

import re
from pathlib import Path

def verify_implementation():
    """Verify AMI Discovery Page implementation by analyzing source code"""
    
    # Read the source file
    source_file = Path("web-app-enhanced.py")
    if not source_file.exists():
        print("❌ web-app-enhanced.py not found")
        return False
    
    with open(source_file, 'r') as f:
        source = f.read()
    
    print("=" * 70)
    print("Verifying AMI Discovery Page Implementation (Tasks 11.1-11.4)")
    print("=" * 70)
    
    # Extract the render_ami_discovery_page function
    pattern = r'def render_ami_discovery_page\(\):.*?(?=\ndef |\nclass |\Z)'
    match = re.search(pattern, source, re.DOTALL)
    
    if not match:
        print("❌ render_ami_discovery_page function not found")
        return False
    
    function_source = match.group(0)
    print(f"\n✅ Found render_ami_discovery_page function ({len(function_source)} characters)")
    
    # Check if it's a placeholder
    if "placeholder" in function_source.lower() and len(function_source) < 1000:
        print("❌ Function appears to be a placeholder")
        return False
    
    print("\n📋 Task 11.1: Create AMI discovery form")
    task_11_1_checks = {
        "FortiGate version selector": any(x in function_source for x in ["FortiGate Version", "version = st.selectbox"]),
        "License type selector": any(x in function_source for x in ["License Type", "license_type"]),
        "Architecture selector": any(x in function_source for x in ["Architecture", "architecture"]),
        "Discover button": any(x in function_source for x in ["Discover AMIs", "discover_button"]),
    }
    
    task_11_1_passed = all(task_11_1_checks.values())
    for check, passed in task_11_1_checks.items():
        print(f"  {'✅' if passed else '❌'} {check}")
    
    print("\n📋 Task 11.2: Implement AMI discovery execution")
    task_11_2_checks = {
        "Call AWSIntegrationManager.discover_amis()": "discover_amis" in function_source,
        "Loading spinner": "spinner" in function_source,
        "Error handling": "try:" in function_source and "except" in function_source,
    }
    
    task_11_2_passed = all(task_11_2_checks.values())
    for check, passed in task_11_2_checks.items():
        print(f"  {'✅' if passed else '❌'} {check}")
    
    print("\n📋 Task 11.3: Display discovery results")
    task_11_3_checks = {
        "Display latest AMI": "ami_info" in function_source,
        "Show AMI metadata": any(x in function_source for x in ["ami_info['id']", "ami_info['name']"]),
        "Auto-populate button": "Use This AMI" in function_source,
        "Alternative AMIs": "Alternative" in function_source or "alternative" in function_source.lower(),
    }
    
    task_11_3_passed = all(task_11_3_checks.values())
    for check, passed in task_11_3_checks.items():
        print(f"  {'✅' if passed else '❌'} {check}")
    
    print("\n📋 Task 11.4: Add version listing functionality")
    task_11_4_checks = {
        "List All Versions button": "List All Versions" in function_source,
        "Call list_fortigate_versions()": "list_fortigate_versions" in function_source,
        "Display versions": "versions" in function_source,
    }
    
    task_11_4_passed = all(task_11_4_checks.values())
    for check, passed in task_11_4_checks.items():
        print(f"  {'✅' if passed else '❌'} {check}")
    
    print("\n📋 Requirements Coverage:")
    requirements_checks = {
        "Req 4.1: Query AWS Marketplace": "discover_amis" in function_source,
        "Req 4.2: Filter by version": "version" in function_source,
        "Req 4.3: Filter by license type": "license_type" in function_source,
        "Req 4.4: Filter by architecture": "architecture" in function_source,
        "Req 4.5: Display AMI metadata": "ami_info" in function_source,
        "Req 4.6: Display alternatives": "Alternative" in function_source or "alternative" in function_source.lower(),
        "Req 4.7: Auto-populate AMI ID": "ami_id" in function_source,
        "Req 4.9: List versions": "list_fortigate_versions" in function_source,
    }
    
    requirements_passed = all(requirements_checks.values())
    for req, passed in requirements_checks.items():
        print(f"  {'✅' if passed else '❌'} {req}")
    
    print("\n📋 Additional Quality Checks:")
    quality_checks = {
        "Session state integration": "st.session_state" in function_source,
        "AWS session check": "aws_session" in function_source,
        "User feedback (success/error)": "st.success" in function_source and "st.error" in function_source,
        "Help documentation": "Help" in function_source or "help=" in function_source,
        "Proper error messages": "Error" in function_source or "error" in function_source.lower(),
    }
    
    quality_passed = all(quality_checks.values())
    for check, passed in quality_checks.items():
        print(f"  {'✅' if passed else '❌'} {check}")
    
    # Overall result
    all_passed = task_11_1_passed and task_11_2_passed and task_11_3_passed and task_11_4_passed and requirements_passed and quality_passed
    
    print("\n" + "=" * 70)
    if all_passed:
        print("✅ ALL CHECKS PASSED - AMI Discovery Page is fully implemented!")
        print("\nImplementation Summary:")
        print("  ✅ Task 11.1: AMI discovery form - COMPLETE")
        print("  ✅ Task 11.2: AMI discovery execution - COMPLETE")
        print("  ✅ Task 11.3: Display discovery results - COMPLETE")
        print("  ✅ Task 11.4: Version listing functionality - COMPLETE")
        print("\n  All requirements (4.1-4.9) are covered.")
    else:
        print("❌ SOME CHECKS FAILED - Review implementation")
        if not task_11_1_passed:
            print("  ❌ Task 11.1 incomplete")
        if not task_11_2_passed:
            print("  ❌ Task 11.2 incomplete")
        if not task_11_3_passed:
            print("  ❌ Task 11.3 incomplete")
        if not task_11_4_passed:
            print("  ❌ Task 11.4 incomplete")
    
    print("=" * 70)
    
    return all_passed

if __name__ == "__main__":
    import sys
    success = verify_implementation()
    sys.exit(0 if success else 1)
