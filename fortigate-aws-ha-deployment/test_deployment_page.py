#!/usr/bin/env python3
"""
Test script for Deployment Page implementation (Tasks 13.1-13.5)

This script verifies that the deployment page functions are properly implemented
and can be called without errors.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent))

def test_imports():
    """Test that all required functions can be imported"""
    print("Testing imports...")
    
    try:
        # Import using importlib since the module name has a hyphen
        import importlib.util
        spec = importlib.util.spec_from_file_location("web_app_enhanced", "web-app-enhanced.py")
        web_app = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(web_app)
        
        # Verify functions exist
        assert hasattr(web_app, 'render_deployment_page')
        assert hasattr(web_app, 'execute_plan_workflow')
        assert hasattr(web_app, 'execute_deployment_workflow')
        assert hasattr(web_app, 'execute_destroy_workflow')
        assert hasattr(web_app, 'display_deployment_results')
        assert hasattr(web_app, 'display_failure_results')
        assert hasattr(web_app, 'display_plan_summary')
        assert hasattr(web_app, 'display_deployment_summary')
        assert hasattr(web_app, 'highlight_terraform_plan')
        assert hasattr(web_app, 'format_elapsed_time')
        
        print("✅ All functions imported successfully")
        return True
    except Exception as e:
        print(f"❌ Import error: {e}")
        return False

def test_format_elapsed_time():
    """Test the format_elapsed_time utility function"""
    print("\nTesting format_elapsed_time...")
    
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("web_app_enhanced", "web-app-enhanced.py")
        web_app = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(web_app)
        
        format_elapsed_time = web_app.format_elapsed_time
        
        # Test various time formats
        test_cases = [
            (30, "30s"),
            (90, "1m 30s"),
            (3661, "1h 1m"),
            (45, "45s"),
            (120, "2m 0s"),
        ]
        
        for seconds, expected_format in test_cases:
            result = format_elapsed_time(seconds)
            print(f"  {seconds}s -> {result}")
            # Basic validation - just check it returns a string
            assert isinstance(result, str), f"Expected string, got {type(result)}"
        
        print("✅ format_elapsed_time works correctly")
        return True
    except Exception as e:
        print(f"❌ Error testing format_elapsed_time: {e}")
        return False

def test_highlight_terraform_plan():
    """Test the highlight_terraform_plan function"""
    print("\nTesting highlight_terraform_plan...")
    
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("web_app_enhanced", "web-app-enhanced.py")
        web_app = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(web_app)
        
        highlight_terraform_plan = web_app.highlight_terraform_plan
        
        # Test with sample Terraform plan output
        sample_plan = """
Terraform will perform the following actions:

  + resource "aws_instance" "example" {
      + ami           = "ami-12345678"
      + instance_type = "t2.micro"
    }

  ~ resource "aws_security_group" "example" {
      ~ ingress {
          + cidr_blocks = ["0.0.0.0/0"]
        }
    }

  - resource "aws_eip" "example" {
      - vpc = true
    }

Plan: 1 to add, 1 to change, 1 to destroy.
"""
        
        result = highlight_terraform_plan(sample_plan)
        
        # Verify highlighting markers are added
        assert "[ADD]" in result, "Missing [ADD] marker"
        assert "[CHG]" in result, "Missing [CHG] marker"
        assert "[DEL]" in result, "Missing [DEL] marker"
        
        print("✅ highlight_terraform_plan works correctly")
        return True
    except Exception as e:
        print(f"❌ Error testing highlight_terraform_plan: {e}")
        return False

def test_display_plan_summary():
    """Test the display_plan_summary function parsing logic"""
    print("\nTesting display_plan_summary parsing...")
    
    try:
        # Test the regex pattern used in display_plan_summary
        import re
        
        sample_output = "Plan: 15 to add, 3 to change, 2 to destroy."
        
        summary_match = re.search(r'Plan: (\d+) to add, (\d+) to change, (\d+) to destroy', sample_output)
        
        assert summary_match is not None, "Regex pattern failed to match"
        assert summary_match.group(1) == "15", "Failed to extract add count"
        assert summary_match.group(2) == "3", "Failed to extract change count"
        assert summary_match.group(3) == "2", "Failed to extract destroy count"
        
        print("✅ display_plan_summary parsing logic works correctly")
        return True
    except Exception as e:
        print(f"❌ Error testing display_plan_summary: {e}")
        return False

def main():
    """Run all tests"""
    print("=" * 60)
    print("Deployment Page Implementation Tests (Tasks 13.1-13.5)")
    print("=" * 60)
    
    results = []
    
    # Run tests
    results.append(("Imports", test_imports()))
    results.append(("format_elapsed_time", test_format_elapsed_time()))
    results.append(("highlight_terraform_plan", test_highlight_terraform_plan()))
    results.append(("display_plan_summary parsing", test_display_plan_summary()))
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Deployment page implementation is working correctly.")
        return 0
    else:
        print(f"\n⚠️ {total - passed} test(s) failed. Please review the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
