#!/usr/bin/env python3
"""
Simple test for TerraformIntegrationManager class structure

This test verifies the TerraformIntegrationManager implementation
by checking the code structure without executing it.
"""

import ast
import sys
from pathlib import Path

def test_terraform_integration_manager_structure():
    """Test TerraformIntegrationManager class structure"""
    
    print("=" * 70)
    print("Testing TerraformIntegrationManager Structure")
    print("=" * 70)
    
    # Read the web-app-enhanced.py file
    web_app_file = Path("web-app-enhanced.py")
    
    if not web_app_file.exists():
        print("✗ web-app-enhanced.py not found")
        return False
    
    with open(web_app_file, 'r') as f:
        content = f.read()
    
    # Parse the AST
    try:
        tree = ast.parse(content)
        print("✓ File parses successfully")
    except SyntaxError as e:
        print(f"✗ Syntax error: {e}")
        return False
    
    # Find the TerraformIntegrationManager class
    terraform_class = None
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "TerraformIntegrationManager":
            terraform_class = node
            break
    
    if not terraform_class:
        print("✗ TerraformIntegrationManager class not found")
        return False
    
    print("✓ TerraformIntegrationManager class found")
    
    # Check for required methods
    required_methods = {
        '__init__': 'Initialize with terraform_dir and backend_config',
        'configure_backend': 'Configure Terraform backend (local or S3)',
        'generate_tfvars': 'Generate terraform.tfvars from DeploymentConfig',
        'init': 'Run terraform init with output streaming',
        'plan': 'Run terraform plan with output streaming',
        'apply': 'Run terraform apply with output streaming',
        'destroy': 'Run terraform destroy with output streaming',
        'get_outputs': 'Retrieve Terraform outputs',
        '_run_terraform_command': 'Run Terraform command with streaming'
    }
    
    found_methods = {}
    for node in terraform_class.body:
        if isinstance(node, ast.FunctionDef):
            found_methods[node.name] = node
    
    print(f"\nChecking required methods:")
    all_methods_found = True
    for method_name, description in required_methods.items():
        if method_name in found_methods:
            print(f"  ✓ {method_name}: {description}")
        else:
            print(f"  ✗ {method_name}: MISSING")
            all_methods_found = False
    
    # Check method signatures
    print(f"\nChecking method signatures:")
    
    # Check __init__ signature
    init_method = found_methods.get('__init__')
    if init_method:
        args = [arg.arg for arg in init_method.args.args]
        if 'self' in args and 'terraform_dir' in args and 'backend_config' in args:
            print(f"  ✓ __init__ has correct parameters")
        else:
            print(f"  ✗ __init__ parameters: {args}")
    
    # Check configure_backend returns Tuple[bool, str]
    configure_method = found_methods.get('configure_backend')
    if configure_method:
        # Check if it has return annotation
        if configure_method.returns:
            print(f"  ✓ configure_backend has return type annotation")
        else:
            print(f"  ⚠ configure_backend missing return type annotation")
    
    # Check generate_tfvars signature
    generate_method = found_methods.get('generate_tfvars')
    if generate_method:
        args = [arg.arg for arg in generate_method.args.args]
        if 'self' in args and 'config' in args:
            print(f"  ✓ generate_tfvars has correct parameters")
        else:
            print(f"  ✗ generate_tfvars parameters: {args}")
    
    # Check streaming methods have callback parameter
    streaming_methods = ['init', 'plan', 'apply', 'destroy']
    for method_name in streaming_methods:
        method = found_methods.get(method_name)
        if method:
            args = [arg.arg for arg in method.args.args]
            if 'callback' in args:
                print(f"  ✓ {method_name} has callback parameter")
            else:
                print(f"  ⚠ {method_name} missing callback parameter")
    
    # Check get_outputs signature
    get_outputs_method = found_methods.get('get_outputs')
    if get_outputs_method:
        args = [arg.arg for arg in get_outputs_method.args.args]
        if len(args) == 1 and args[0] == 'self':
            print(f"  ✓ get_outputs has correct parameters (self only)")
        else:
            print(f"  ✗ get_outputs parameters: {args}")
    
    # Check for docstrings
    print(f"\nChecking docstrings:")
    class_has_docstring = ast.get_docstring(terraform_class) is not None
    if class_has_docstring:
        print(f"  ✓ Class has docstring")
    else:
        print(f"  ⚠ Class missing docstring")
    
    methods_with_docstrings = 0
    for method_name, method_node in found_methods.items():
        if ast.get_docstring(method_node):
            methods_with_docstrings += 1
    
    print(f"  ✓ {methods_with_docstrings}/{len(found_methods)} methods have docstrings")
    
    # Check for Requirements comments
    print(f"\nChecking Requirements documentation:")
    requirements_found = 0
    for method_name, method_node in found_methods.items():
        docstring = ast.get_docstring(method_node)
        if docstring and 'Requirement' in docstring:
            requirements_found += 1
    
    print(f"  ✓ {requirements_found}/{len(found_methods)} methods document requirements")
    
    # Summary
    print("\n" + "=" * 70)
    if all_methods_found:
        print("✓ All required methods implemented")
        print("✓ TerraformIntegrationManager structure is correct")
        print("=" * 70)
        return True
    else:
        print("✗ Some required methods are missing")
        print("=" * 70)
        return False

if __name__ == "__main__":
    success = test_terraform_integration_manager_structure()
    sys.exit(0 if success else 1)
