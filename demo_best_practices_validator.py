#!/usr/bin/env python3
"""
Demonstration of the BestPracticesValidator functionality.

This script shows how the BestPracticesValidator can identify various
best practice violations in Terraform configurations.
"""

from fortigate_analysis.analyzer.best_practices_validator import BestPracticesValidator
from fortigate_analysis.models import (
    TerraformFile, TerraformAST, Variable, Resource, Output, Module
)


def create_sample_terraform_file():
    """Create a sample Terraform file with various best practice violations."""
    
    # Variables with issues
    variables = [
        Variable(
            name="InstanceType",  # Bad naming (uppercase)
            type=None,  # Missing type
            description=None  # Missing description
        ),
        Variable(
            name="api_key",
            type="string",
            description="API key for authentication",
            sensitive=True,
            default="default-key"  # Sensitive variable with default
        ),
        Variable(
            name="vm",  # Too short
            type="string",
            description="VM configuration"
        )
    ]
    
    # Resources with issues
    resources = [
        Resource(
            type="aws_instance",
            name="WebServer-1",  # Bad naming (uppercase, hyphen)
            provider="aws",
            configuration={},
            line_number=10
        ),
        Resource(
            type="aws_security_group",
            name="sg",  # Too short
            provider="aws",
            configuration={},
            line_number=20
        )
    ]
    
    # Outputs with issues
    outputs = [
        Output(
            name="instance_ip",
            value="aws_instance.web.public_ip",
            description=None  # Missing description
        )
    ]
    
    # Modules with issues
    modules = [
        Module(
            name="vpc",
            source="terraform-aws-modules/vpc/aws",  # External without version
            version=None
        )
    ]
    
    # Terraform AST with missing configurations
    ast = TerraformAST(
        variables=variables,
        resources=resources,
        outputs=outputs,
        modules=modules,
        providers=[{"aws": {}}],  # Provider without version constraint
        terraform_block={}  # Missing backend and version constraints
    )
    
    return TerraformFile(
        path="main.tf",
        cloud_provider="aws",
        deployment_type="single",
        fortigate_versions=["7.0"],
        ast=ast,
        variables=variables,
        resources=resources,
        outputs=outputs,
        modules=modules
    )


def demonstrate_best_practices_validation():
    """Demonstrate the BestPracticesValidator functionality."""
    
    print("🔍 FortiGate Terraform Analysis - Best Practices Validator Demo")
    print("=" * 70)
    
    # Create validator with default configuration
    validator = BestPracticesValidator()
    
    # Create sample file with violations
    tf_file = create_sample_terraform_file()
    
    print(f"\n📁 Analyzing file: {tf_file.path}")
    print(f"   Cloud Provider: {tf_file.cloud_provider}")
    print(f"   Deployment Type: {tf_file.deployment_type}")
    print(f"   FortiGate Versions: {', '.join(tf_file.fortigate_versions)}")
    
    # Perform validation
    result = validator.validate_practices([tf_file])
    
    print(f"\n📊 Validation Results:")
    print(f"   Total Violations: {result.summary['total_violations']}")
    print(f"   Critical: {result.summary.get('critical', 0)}")
    print(f"   High: {result.summary.get('high', 0)}")
    print(f"   Medium: {result.summary.get('medium', 0)}")
    print(f"   Low: {result.summary.get('low', 0)}")
    
    # Show violations by category
    print(f"\n📋 Violations by Category:")
    categories = ['SECURITY', 'BEST_PRACTICES', 'DOCUMENTATION', 'ARCHITECTURE']
    for category in categories:
        count = result.summary.get(category, 0)
        if count > 0:
            print(f"   {category}: {count}")
    
    # Show detailed violations
    print(f"\n🚨 Detailed Violations:")
    for i, violation in enumerate(result.violations, 1):
        print(f"\n   {i}. {violation.rule_name}")
        print(f"      Severity: {violation.severity.value}")
        print(f"      Category: {violation.category.value}")
        print(f"      Description: {violation.description}")
        print(f"      File: {violation.file_path}:{violation.line_number}")
        print(f"      Recommendation: {violation.recommendation}")
        if violation.affected_resources:
            print(f"      Affected Resources: {', '.join(violation.affected_resources)}")
    
    # Show recommendations
    print(f"\n💡 High-Level Recommendations:")
    for i, recommendation in enumerate(result.recommendations, 1):
        print(f"   {i}. {recommendation}")
    
    print(f"\n✅ Validation completed successfully!")


def demonstrate_custom_configuration():
    """Demonstrate custom validation configuration."""
    
    print(f"\n🔧 Custom Configuration Demo")
    print("=" * 40)
    
    # Custom configuration with stricter rules
    custom_config = {
        'naming_patterns': {
            'resource': r'^[a-z][a-z0-9_]*[a-z0-9]$',
            'variable': r'^[a-z][a-z0-9_]*[a-z0-9]$'
        },
        'required_variable_attrs': {
            'description': True,
            'type': True,
            'default': True  # Require defaults for all variables
        },
        'documentation': {
            'readme_required': True,
            'inline_comments_threshold': 0.5,  # 50% coverage required
            'variable_descriptions_required': True,
            'output_descriptions_required': True
        }
    }
    
    validator = BestPracticesValidator(custom_config)
    
    # Create a simple file for testing
    simple_file = TerraformFile(
        path="simple.tf",
        cloud_provider="aws",
        deployment_type="single",
        fortigate_versions=["7.0"],
        variables=[
            Variable(
                name="instance_type",
                type="string",
                description="EC2 instance type",
                default=None  # Will trigger violation with custom config
            )
        ]
    )
    
    result = validator.validate_practices([simple_file])
    
    print(f"Custom validation found {result.summary['total_violations']} violations")
    for violation in result.violations:
        print(f"  - {violation.rule_name}: {violation.description}")


if __name__ == "__main__":
    demonstrate_best_practices_validation()
    demonstrate_custom_configuration()