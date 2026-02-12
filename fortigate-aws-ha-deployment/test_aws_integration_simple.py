#!/usr/bin/env python3
"""
Simple test to verify AWSIntegrationManager class structure.

This test verifies the class is properly defined without requiring AWS credentials
or Streamlit dependencies.
"""

import sys
import ast
from pathlib import Path


def test_aws_integration_manager_structure():
    """Test that AWSIntegrationManager has all required methods."""
    
    print("=" * 80)
    print("Testing AWSIntegrationManager Structure")
    print("=" * 80)
    
    # Read the web-app-enhanced.py file
    web_app_file = Path(__file__).parent / "web-app-enhanced.py"
    
    with open(web_app_file, 'r') as f:
        content = f.read()
    
    # Parse the AST
    tree = ast.parse(content)
    
    # Find the AWSIntegrationManager class
    aws_manager_class = None
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "AWSIntegrationManager":
            aws_manager_class = node
            break
    
    if not aws_manager_class:
        print("❌ AWSIntegrationManager class not found!")
        return False
    
    print("\n✅ AWSIntegrationManager class found")
    
    # Extract method names
    methods = []
    for item in aws_manager_class.body:
        if isinstance(item, ast.FunctionDef):
            methods.append(item.name)
    
    print(f"\n📋 Found {len(methods)} methods:")
    for method in methods:
        print(f"   - {method}")
    
    # Check for required methods
    required_methods = [
        '__init__',
        'create_session',
        'validate_vpc',
        'validate_subnets',
        'validate_enis',
        'validate_eips',
        'validate_transit_gateway',
        'validate_ami',
        'validate_key_pair',
        'discover_amis',
        'list_fortigate_versions',
        'test_secrets_manager_access',
        'test_s3_access'
    ]
    
    print(f"\n🔍 Checking for required methods:")
    all_present = True
    for required_method in required_methods:
        if required_method in methods:
            print(f"   ✅ {required_method}")
        else:
            print(f"   ❌ {required_method} - MISSING!")
            all_present = False
    
    if not all_present:
        print("\n❌ Some required methods are missing!")
        return False
    
    print("\n✅ All required methods are present")
    
    # Check class docstring
    docstring = ast.get_docstring(aws_manager_class)
    if docstring:
        print("\n✅ Class has docstring")
        print(f"\n📝 Docstring preview:")
        print(f"   {docstring.split(chr(10))[0]}")
    else:
        print("\n⚠️  Class missing docstring")
    
    # Check that methods have docstrings
    print(f"\n🔍 Checking method docstrings:")
    methods_with_docs = 0
    for item in aws_manager_class.body:
        if isinstance(item, ast.FunctionDef):
            if ast.get_docstring(item):
                methods_with_docs += 1
    
    print(f"   {methods_with_docs}/{len(methods)} methods have docstrings")
    
    if methods_with_docs == len(methods):
        print("   ✅ All methods documented")
    else:
        print(f"   ⚠️  {len(methods) - methods_with_docs} methods missing docstrings")
    
    print("\n" + "=" * 80)
    print("Structure validation completed successfully!")
    print("=" * 80)
    
    return True


if __name__ == "__main__":
    try:
        success = test_aws_integration_manager_structure()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
