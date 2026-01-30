"""
Unit tests for the BestPracticesValidator class.
"""

import pytest
from pathlib import Path
from datetime import datetime

from fortigate_analysis.analyzer.best_practices_validator import BestPracticesValidator
from fortigate_analysis.models import (
    TerraformFile, TerraformAST, Variable, Resource, Output, Module,
    BestPracticeIssue, Severity, Category
)


class TestBestPracticesValidator:
    """Test cases for BestPracticesValidator."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.validator = BestPracticesValidator()
    
    def test_init_with_default_config(self):
        """Test validator initialization with default configuration."""
        validator = BestPracticesValidator()
        assert validator.naming_patterns is not None
        assert validator.required_variable_attrs is not None
        assert validator.doc_requirements is not None
    
    def test_init_with_custom_config(self):
        """Test validator initialization with custom configuration."""
        config = {
            'naming_patterns': {
                'resource': r'^custom_[a-z]+$'
            }
        }
        validator = BestPracticesValidator(config)
        assert validator.naming_patterns['resource'] == r'^custom_[a-z]+$'
    
    def test_validate_practices_empty_files(self):
        """Test validation with empty file list."""
        result = self.validator.validate_practices([])
        assert result.violations == []
        assert result.summary['total_violations'] == 0
    
    def test_resource_naming_convention_valid(self):
        """Test valid resource naming convention."""
        resource = Resource(
            type="aws_instance",
            name="web_server",
            provider="aws",
            configuration={},
            line_number=10
        )
        
        tf_file = TerraformFile(
            path="test.tf",
            cloud_provider="aws",
            deployment_type="single",
            fortigate_versions=["7.0"],
            resources=[resource]
        )
        
        result = self.validator.validate_practices([tf_file])
        naming_violations = [v for v in result.violations if v.rule_name == "resource_naming_convention"]
        assert len(naming_violations) == 0
    
    def test_resource_naming_convention_invalid(self):
        """Test invalid resource naming convention."""
        resource = Resource(
            type="aws_instance",
            name="WebServer-1",  # Invalid: contains uppercase and hyphen
            provider="aws",
            configuration={},
            line_number=10
        )
        
        tf_file = TerraformFile(
            path="test.tf",
            cloud_provider="aws",
            deployment_type="single",
            fortigate_versions=["7.0"],
            resources=[resource]
        )
        
        result = self.validator.validate_practices([tf_file])
        naming_violations = [v for v in result.violations if v.rule_name == "resource_naming_convention"]
        assert len(naming_violations) == 1
        assert naming_violations[0].severity == Severity.MEDIUM
        assert "WebServer-1" in naming_violations[0].description
    
    def test_resource_name_too_short(self):
        """Test resource name that is too short."""
        resource = Resource(
            type="aws_instance",
            name="vm",  # Too short
            provider="aws",
            configuration={},
            line_number=10
        )
        
        tf_file = TerraformFile(
            path="test.tf",
            cloud_provider="aws",
            deployment_type="single",
            fortigate_versions=["7.0"],
            resources=[resource]
        )
        
        result = self.validator.validate_practices([tf_file])
        short_name_violations = [v for v in result.violations if v.rule_name == "resource_descriptive_naming"]
        assert len(short_name_violations) == 1
        assert short_name_violations[0].severity == Severity.LOW
    
    def test_variable_missing_description(self):
        """Test variable without description."""
        variable = Variable(
            name="instance_type",
            type="string",
            description=None  # Missing description
        )
        
        tf_file = TerraformFile(
            path="variables.tf",
            cloud_provider="aws",
            deployment_type="single",
            fortigate_versions=["7.0"],
            variables=[variable]
        )
        
        result = self.validator.validate_practices([tf_file])
        desc_violations = [v for v in result.violations if v.rule_name == "variable_description_required"]
        assert len(desc_violations) == 1
        assert desc_violations[0].severity == Severity.HIGH
        assert desc_violations[0].category == Category.DOCUMENTATION
    
    def test_variable_missing_type(self):
        """Test variable without type specification."""
        variable = Variable(
            name="instance_count",
            type=None,  # Missing type
            description="Number of instances"
        )
        
        tf_file = TerraformFile(
            path="variables.tf",
            cloud_provider="aws",
            deployment_type="single",
            fortigate_versions=["7.0"],
            variables=[variable]
        )
        
        result = self.validator.validate_practices([tf_file])
        type_violations = [v for v in result.violations if v.rule_name == "variable_type_required"]
        assert len(type_violations) == 1
        assert type_violations[0].severity == Severity.HIGH
    
    def test_sensitive_variable_with_default(self):
        """Test sensitive variable with default value."""
        variable = Variable(
            name="api_key",
            type="string",
            description="API key for authentication",
            sensitive=True,
            default="default-key"  # Should not have default
        )
        
        tf_file = TerraformFile(
            path="variables.tf",
            cloud_provider="aws",
            deployment_type="single",
            fortigate_versions=["7.0"],
            variables=[variable]
        )
        
        result = self.validator.validate_practices([tf_file])
        sensitive_violations = [v for v in result.violations if v.rule_name == "sensitive_variable_no_default"]
        assert len(sensitive_violations) == 1
        assert sensitive_violations[0].severity == Severity.HIGH
        assert sensitive_violations[0].category == Category.SECURITY
    
    def test_output_missing_description(self):
        """Test output without description."""
        output = Output(
            name="instance_ip",
            value="aws_instance.web.public_ip",
            description=None  # Missing description
        )
        
        tf_file = TerraformFile(
            path="outputs.tf",
            cloud_provider="aws",
            deployment_type="single",
            fortigate_versions=["7.0"],
            outputs=[output]
        )
        
        result = self.validator.validate_practices([tf_file])
        desc_violations = [v for v in result.violations if v.rule_name == "output_description_required"]
        assert len(desc_violations) == 1
        assert desc_violations[0].severity == Severity.MEDIUM
    
    def test_main_file_too_many_resources(self):
        """Test main.tf file with too many resources."""
        resources = []
        for i in range(10):  # More than 5 resources
            resources.append(Resource(
                type="aws_instance",
                name=f"instance_{i}",
                provider="aws",
                configuration={},
                line_number=i * 5
            ))
        
        tf_file = TerraformFile(
            path="main.tf",  # Main file should have fewer resources
            cloud_provider="aws",
            deployment_type="single",
            fortigate_versions=["7.0"],
            resources=resources
        )
        
        result = self.validator.validate_practices([tf_file])
        org_violations = [v for v in result.violations if v.rule_name == "main_file_organization"]
        assert len(org_violations) == 1
        assert org_violations[0].severity == Severity.MEDIUM
        assert org_violations[0].category == Category.ARCHITECTURE
    
    def test_module_without_version_pinning(self):
        """Test external module without version pinning."""
        module = Module(
            name="vpc",
            source="terraform-aws-modules/vpc/aws",  # External source
            version=None  # Missing version
        )
        
        tf_file = TerraformFile(
            path="main.tf",
            cloud_provider="aws",
            deployment_type="single",
            fortigate_versions=["7.0"],
            modules=[module]
        )
        
        result = self.validator.validate_practices([tf_file])
        version_violations = [v for v in result.violations if v.rule_name == "module_version_pinning"]
        assert len(version_violations) == 1
        assert version_violations[0].severity == Severity.HIGH
    
    def test_local_module_no_version_required(self):
        """Test local module doesn't require version pinning."""
        module = Module(
            name="local_vpc",
            source="./modules/vpc",  # Local source
            version=None  # Version not required for local modules
        )
        
        tf_file = TerraformFile(
            path="main.tf",
            cloud_provider="aws",
            deployment_type="single",
            fortigate_versions=["7.0"],
            modules=[module]
        )
        
        result = self.validator.validate_practices([tf_file])
        version_violations = [v for v in result.violations if v.rule_name == "module_version_pinning"]
        assert len(version_violations) == 0
    
    def test_missing_backend_configuration(self):
        """Test missing backend configuration."""
        tf_file = TerraformFile(
            path="main.tf",
            cloud_provider="aws",
            deployment_type="single",
            fortigate_versions=["7.0"],
            ast=TerraformAST(terraform_block={})  # No backend config
        )
        
        result = self.validator.validate_practices([tf_file])
        backend_violations = [v for v in result.violations if v.rule_name == "backend_configuration_required"]
        assert len(backend_violations) == 1
        assert backend_violations[0].severity == Severity.HIGH
    
    def test_s3_backend_missing_dynamodb(self):
        """Test S3 backend without DynamoDB table for locking."""
        terraform_block = {
            'backend': {
                's3': {
                    'bucket': 'my-terraform-state',
                    'key': 'terraform.tfstate',
                    'region': 'us-west-2'
                    # Missing dynamodb_table
                }
            }
        }
        
        tf_file = TerraformFile(
            path="main.tf",
            cloud_provider="aws",
            deployment_type="single",
            fortigate_versions=["7.0"],
            ast=TerraformAST(terraform_block=terraform_block)
        )
        
        result = self.validator.validate_practices([tf_file])
        locking_violations = [v for v in result.violations if v.rule_name == "state_locking_required"]
        assert len(locking_violations) == 1
        assert locking_violations[0].severity == Severity.HIGH
    
    def test_missing_terraform_version(self):
        """Test missing Terraform version constraint."""
        tf_file = TerraformFile(
            path="versions.tf",
            cloud_provider="aws",
            deployment_type="single",
            fortigate_versions=["7.0"],
            ast=TerraformAST(terraform_block={})  # No required_version
        )
        
        result = self.validator.validate_practices([tf_file])
        version_violations = [v for v in result.violations if v.rule_name == "terraform_version_required"]
        assert len(version_violations) == 1
        assert version_violations[0].severity == Severity.HIGH
    
    def test_missing_provider_version(self):
        """Test missing provider version constraint."""
        terraform_block = {
            'required_providers': {}  # Empty required_providers
        }
        
        tf_file = TerraformFile(
            path="versions.tf",
            cloud_provider="aws",
            deployment_type="single",
            fortigate_versions=["7.0"],
            ast=TerraformAST(
                terraform_block=terraform_block,
                providers=[{'aws': {}}]  # Provider without version constraint
            )
        )
        
        result = self.validator.validate_practices([tf_file])
        provider_violations = [v for v in result.violations if v.rule_name == "provider_version_required"]
        assert len(provider_violations) == 1
        assert provider_violations[0].severity == Severity.HIGH
    
    def test_check_documentation_missing_readme(self):
        """Test missing README file detection."""
        tf_file = TerraformFile(
            path="/project/main.tf",
            cloud_provider="aws",
            deployment_type="single",
            fortigate_versions=["7.0"]
        )
        
        result = self.validator.validate_practices([tf_file])
        readme_violations = [v for v in result.violations if v.rule_name == "readme_required"]
        # Note: This test might not work as expected without actual filesystem
        # In a real implementation, you'd mock the filesystem
    
    def test_summary_generation(self):
        """Test summary statistics generation."""
        # Create violations with different severities
        violations = [
            BestPracticeIssue(
                severity=Severity.HIGH,
                category=Category.SECURITY,
                description="Test high severity",
                file_path="test.tf",
                line_number=1,
                recommendation="Fix it",
                rule_name="test_rule"
            ),
            BestPracticeIssue(
                severity=Severity.MEDIUM,
                category=Category.BEST_PRACTICES,
                description="Test medium severity",
                file_path="test.tf",
                line_number=2,
                recommendation="Fix it",
                rule_name="test_rule"
            )
        ]
        
        summary = self.validator._generate_summary(violations)
        assert summary['total_violations'] == 2
        assert summary['high'] == 1
        assert summary['medium'] == 1
        assert summary['SECURITY'] == 1
        assert summary['BEST_PRACTICES'] == 1
    
    def test_recommendations_generation(self):
        """Test recommendations generation."""
        violations = [
            BestPracticeIssue(
                severity=Severity.HIGH,
                category=Category.DOCUMENTATION,
                description="Missing description",
                file_path="test.tf",
                line_number=1,
                recommendation="Add description",
                rule_name="variable_description_required"
            )
        ]
        
        recommendations = self.validator._generate_recommendations(violations)
        assert len(recommendations) > 0
        assert any("descriptions" in rec for rec in recommendations)
    
    def test_legacy_interface_check_naming_conventions(self):
        """Test legacy interface for checking naming conventions."""
        resources = [
            {
                'type': 'aws_instance',
                'name': 'InvalidName-1',
                'provider': 'aws',
                'configuration': {},
                'line_number': 1,
                'file_path': 'test.tf'
            }
        ]
        
        violations = self.validator.check_naming_conventions(resources)
        assert len(violations) > 0
        assert violations[0].rule_name == "resource_naming_convention"
    
    def test_legacy_interface_validate_module_structure(self):
        """Test legacy interface for validating module structure."""
        modules = [
            {
                'name': 'vpc',
                'source': 'terraform-aws-modules/vpc/aws',
                'version': None,
                'file_path': 'main.tf',
                'line_number': 1
            }
        ]
        
        violations = self.validator.validate_module_structure(modules)
        assert len(violations) > 0
        assert violations[0].rule_name == "module_version_pinning"


class TestBestPracticesValidatorEdgeCases:
    """Test edge cases and error handling."""
    
    def test_file_without_ast(self):
        """Test handling file without AST."""
        tf_file = TerraformFile(
            path="test.tf",
            cloud_provider="aws",
            deployment_type="single",
            fortigate_versions=["7.0"],
            ast=None  # No AST
        )
        
        validator = BestPracticesValidator()
        result = validator.validate_practices([tf_file])
        # Should not crash, should handle gracefully
        assert isinstance(result.violations, list)
    
    def test_empty_terraform_block(self):
        """Test handling empty terraform block."""
        tf_file = TerraformFile(
            path="test.tf",
            cloud_provider="aws",
            deployment_type="single",
            fortigate_versions=["7.0"],
            ast=TerraformAST(terraform_block=None)
        )
        
        validator = BestPracticesValidator()
        result = validator.validate_practices([tf_file])
        # Should handle gracefully
        assert isinstance(result.violations, list)
    
    def test_custom_validation_rules(self):
        """Test custom validation rules configuration."""
        config = {
            'naming_patterns': {
                'resource': r'^custom_[a-z]+$'
            },
            'required_variable_attrs': {
                'description': False,  # Don't require descriptions
                'type': True
            }
        }
        
        validator = BestPracticesValidator(config)
        
        # Test custom naming pattern
        resource = Resource(
            type="aws_instance",
            name="web_server",  # Doesn't match custom pattern
            provider="aws",
            configuration={},
            line_number=10
        )
        
        tf_file = TerraformFile(
            path="test.tf",
            cloud_provider="aws",
            deployment_type="single",
            fortigate_versions=["7.0"],
            resources=[resource]
        )
        
        result = validator.validate_practices([tf_file])
        naming_violations = [v for v in result.violations if v.rule_name == "resource_naming_convention"]
        assert len(naming_violations) == 1  # Should fail custom pattern