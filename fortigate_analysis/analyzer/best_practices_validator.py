"""
Best practices validator implementation for checking Terraform code quality.
"""

import re
import os
from pathlib import Path
from typing import List, Dict, Any, Set, Optional

from ..models import (
    TerraformFile, BestPracticeIssue, BestPracticesReport, 
    Severity, Category, Resource, Variable, Output, Module
)
from ..interfaces import BestPracticesValidatorProtocol, BaseAnalyzer


class BestPracticesValidator(BaseAnalyzer):
    """
    Validates adherence to Terraform and cloud provider best practices.
    
    Checks naming conventions, module organization, documentation completeness,
    state management, version pinning, and other code quality aspects.
    """
    
    def __init__(self, config: Dict = None):
        super().__init__(config)
        self._setup_default_rules()
    
    def _setup_default_rules(self):
        """Setup default validation rules and patterns."""
        # Naming convention patterns
        self.naming_patterns = self.config.get('naming_patterns', {
            'resource': r'^[a-z][a-z0-9_]*[a-z0-9]$',
            'variable': r'^[a-z][a-z0-9_]*[a-z0-9]$',
            'output': r'^[a-z][a-z0-9_]*[a-z0-9]$',
            'module': r'^[a-z][a-z0-9_]*[a-z0-9]$',
            'data_source': r'^[a-z][a-z0-9_]*[a-z0-9]$'
        })
        
        # Required variable attributes
        self.required_variable_attrs = self.config.get('required_variable_attrs', {
            'description': True,
            'type': True,
            'default': False  # Optional but recommended
        })
        
        # Required output attributes
        self.required_output_attrs = self.config.get('required_output_attrs', {
            'description': True,
            'value': True
        })
        
        # Documentation requirements
        self.doc_requirements = self.config.get('documentation', {
            'readme_required': True,
            'inline_comments_threshold': 0.3,  # 30% of resources should have comments
            'variable_descriptions_required': True,
            'output_descriptions_required': True
        })
        
        # State management best practices
        self.state_requirements = self.config.get('state_management', {
            'backend_required': True,
            'state_locking_required': True,
            'encryption_required': True
        })
        
        # Version pinning requirements
        self.version_requirements = self.config.get('version_pinning', {
            'terraform_version_required': True,
            'provider_versions_required': True,
            'module_versions_required': True
        })
    
    def analyze(self, terraform_files: List[TerraformFile]) -> BestPracticesReport:
        """Alias for validate_practices to match BaseAnalyzer interface."""
        return self.validate_practices(terraform_files)
    
    def validate_practices(self, terraform_files: List[TerraformFile]) -> BestPracticesReport:
        """
        Validate adherence to best practices.
        
        Args:
            terraform_files: List of Terraform files to validate
            
        Returns:
            BestPracticesReport with violations and recommendations
        """
        violations = []
        
        try:
            # Validate naming conventions
            for tf_file in terraform_files:
                violations.extend(self._check_file_naming_conventions(tf_file))
                violations.extend(self._check_variable_usage(tf_file))
                violations.extend(self._check_output_usage(tf_file))
                violations.extend(self._check_module_organization(tf_file))
                violations.extend(self._check_state_management(tf_file))
                violations.extend(self._check_version_pinning(tf_file))
            
            # Check documentation completeness across all files
            violations.extend(self.check_documentation(terraform_files))
            
            # Generate summary
            summary = self._generate_summary(violations)
            
            # Generate recommendations
            recommendations = self._generate_recommendations(violations)
            
            return BestPracticesReport(
                violations=violations,
                summary=summary,
                recommendations=recommendations
            )
            
        except Exception as e:
            self.handle_error(e, "best practices validation")
            return BestPracticesReport()
    
    def _check_file_naming_conventions(self, tf_file: TerraformFile) -> List[BestPracticeIssue]:
        """Check naming conventions for resources, variables, and outputs in a file."""
        violations = []
        
        # Check resource naming
        for resource in tf_file.resources:
            violations.extend(self._validate_resource_naming(resource, tf_file.path))
        
        # Check variable naming
        for variable in tf_file.variables:
            violations.extend(self._validate_variable_naming(variable, tf_file.path))
        
        # Check output naming
        for output in tf_file.outputs:
            violations.extend(self._validate_output_naming(output, tf_file.path))
        
        # Check module naming
        for module in tf_file.modules:
            violations.extend(self._validate_module_naming(module, tf_file.path))
        
        return violations
    
    def _validate_resource_naming(self, resource: Resource, file_path: str) -> List[BestPracticeIssue]:
        """Validate resource naming conventions."""
        violations = []
        pattern = self.naming_patterns['resource']
        
        if not re.match(pattern, resource.name):
            violations.append(BestPracticeIssue(
                severity=Severity.MEDIUM,
                category=Category.BEST_PRACTICES,
                description=f"Resource '{resource.name}' does not follow naming convention. "
                           f"Expected pattern: {pattern}",
                file_path=file_path,
                line_number=resource.line_number,
                recommendation="Use lowercase letters, numbers, and underscores. "
                              "Start with a letter, end with letter or number.",
                rule_name="resource_naming_convention",
                affected_resources=[f"{resource.type}.{resource.name}"]
            ))
        
        # Check for descriptive naming
        if len(resource.name) < 3:
            violations.append(BestPracticeIssue(
                severity=Severity.LOW,
                category=Category.BEST_PRACTICES,
                description=f"Resource name '{resource.name}' is too short and not descriptive",
                file_path=file_path,
                line_number=resource.line_number,
                recommendation="Use descriptive names that clearly indicate the resource purpose",
                rule_name="resource_descriptive_naming",
                affected_resources=[f"{resource.type}.{resource.name}"]
            ))
        
        return violations
    
    def _validate_variable_naming(self, variable: Variable, file_path: str) -> List[BestPracticeIssue]:
        """Validate variable naming conventions."""
        violations = []
        pattern = self.naming_patterns['variable']
        
        if not re.match(pattern, variable.name):
            violations.append(BestPracticeIssue(
                severity=Severity.MEDIUM,
                category=Category.BEST_PRACTICES,
                description=f"Variable '{variable.name}' does not follow naming convention. "
                           f"Expected pattern: {pattern}",
                file_path=file_path,
                line_number=1,  # Variables typically at top of file
                recommendation="Use lowercase letters, numbers, and underscores. "
                              "Start with a letter, end with letter or number.",
                rule_name="variable_naming_convention",
                affected_resources=[f"var.{variable.name}"]
            ))
        
        return violations
    
    def _validate_output_naming(self, output: Output, file_path: str) -> List[BestPracticeIssue]:
        """Validate output naming conventions."""
        violations = []
        pattern = self.naming_patterns['output']
        
        if not re.match(pattern, output.name):
            violations.append(BestPracticeIssue(
                severity=Severity.MEDIUM,
                category=Category.BEST_PRACTICES,
                description=f"Output '{output.name}' does not follow naming convention. "
                           f"Expected pattern: {pattern}",
                file_path=file_path,
                line_number=1,  # Outputs typically at end of file
                recommendation="Use lowercase letters, numbers, and underscores. "
                              "Start with a letter, end with letter or number.",
                rule_name="output_naming_convention",
                affected_resources=[f"output.{output.name}"]
            ))
        
        return violations
    
    def _validate_module_naming(self, module: Module, file_path: str) -> List[BestPracticeIssue]:
        """Validate module naming conventions."""
        violations = []
        pattern = self.naming_patterns['module']
        
        if not re.match(pattern, module.name):
            violations.append(BestPracticeIssue(
                severity=Severity.MEDIUM,
                category=Category.BEST_PRACTICES,
                description=f"Module '{module.name}' does not follow naming convention. "
                           f"Expected pattern: {pattern}",
                file_path=file_path,
                line_number=1,
                recommendation="Use lowercase letters, numbers, and underscores. "
                              "Start with a letter, end with letter or number.",
                rule_name="module_naming_convention",
                affected_resources=[f"module.{module.name}"]
            ))
        
        return violations
    
    def _check_variable_usage(self, tf_file: TerraformFile) -> List[BestPracticeIssue]:
        """Check variable usage best practices."""
        violations = []
        
        for variable in tf_file.variables:
            # Check for required attributes
            if self.required_variable_attrs.get('description') and not variable.description:
                violations.append(BestPracticeIssue(
                    severity=Severity.HIGH,
                    category=Category.DOCUMENTATION,
                    description=f"Variable '{variable.name}' is missing description",
                    file_path=tf_file.path,
                    line_number=1,
                    recommendation="Add a clear description explaining the variable's purpose and usage",
                    rule_name="variable_description_required",
                    affected_resources=[f"var.{variable.name}"]
                ))
            
            if self.required_variable_attrs.get('type') and not variable.type:
                violations.append(BestPracticeIssue(
                    severity=Severity.HIGH,
                    category=Category.BEST_PRACTICES,
                    description=f"Variable '{variable.name}' is missing type specification",
                    file_path=tf_file.path,
                    line_number=1,
                    recommendation="Specify explicit type (string, number, bool, list, map, object)",
                    rule_name="variable_type_required",
                    affected_resources=[f"var.{variable.name}"]
                ))
            
            # Check for sensitive variables without proper handling
            if variable.sensitive and variable.default is not None:
                violations.append(BestPracticeIssue(
                    severity=Severity.HIGH,
                    category=Category.SECURITY,
                    description=f"Sensitive variable '{variable.name}' has a default value",
                    file_path=tf_file.path,
                    line_number=1,
                    recommendation="Remove default value for sensitive variables to prevent exposure",
                    rule_name="sensitive_variable_no_default",
                    affected_resources=[f"var.{variable.name}"]
                ))
        
        return violations
    
    def _check_output_usage(self, tf_file: TerraformFile) -> List[BestPracticeIssue]:
        """Check output usage best practices."""
        violations = []
        
        for output in tf_file.outputs:
            # Check for required attributes
            if self.required_output_attrs.get('description') and not output.description:
                violations.append(BestPracticeIssue(
                    severity=Severity.MEDIUM,
                    category=Category.DOCUMENTATION,
                    description=f"Output '{output.name}' is missing description",
                    file_path=tf_file.path,
                    line_number=1,
                    recommendation="Add a clear description explaining what the output represents",
                    rule_name="output_description_required",
                    affected_resources=[f"output.{output.name}"]
                ))
        
        return violations
    
    def _check_module_organization(self, tf_file: TerraformFile) -> List[BestPracticeIssue]:
        """Check module organization and structure."""
        violations = []
        file_path = Path(tf_file.path)
        
        # Check for proper file organization
        if file_path.name == "main.tf":
            # Main files should primarily contain module calls, not resources
            if len(tf_file.resources) > 5:
                violations.append(BestPracticeIssue(
                    severity=Severity.MEDIUM,
                    category=Category.ARCHITECTURE,
                    description=f"main.tf contains {len(tf_file.resources)} resources. "
                               "Consider breaking into modules for better organization",
                    file_path=tf_file.path,
                    line_number=1,
                    recommendation="Move resources into separate modules and call them from main.tf",
                    rule_name="main_file_organization",
                    affected_resources=[f"{r.type}.{r.name}" for r in tf_file.resources]
                ))
        
        # Check for module versioning
        for module in tf_file.modules:
            if not module.version and not module.source.startswith("./") and not module.source.startswith("../"):
                violations.append(BestPracticeIssue(
                    severity=Severity.HIGH,
                    category=Category.BEST_PRACTICES,
                    description=f"Module '{module.name}' from external source '{module.source}' "
                               "is not version pinned",
                    file_path=tf_file.path,
                    line_number=1,
                    recommendation="Pin module to specific version to ensure reproducible deployments",
                    rule_name="module_version_pinning",
                    affected_resources=[f"module.{module.name}"]
                ))
        
        return violations
    
    def _check_state_management(self, tf_file: TerraformFile) -> List[BestPracticeIssue]:
        """Check state management best practices."""
        violations = []
        
        if not tf_file.ast:
            return violations
        
        terraform_block = tf_file.ast.terraform_block or {}
        backend_config = terraform_block.get('backend')
        
        if self.state_requirements.get('backend_required') and not backend_config:
            violations.append(BestPracticeIssue(
                severity=Severity.HIGH,
                category=Category.BEST_PRACTICES,
                description="No backend configuration found. Using local state is not recommended for production",
                file_path=tf_file.path,
                line_number=1,
                recommendation="Configure remote backend (S3, Azure Storage, GCS) for state management",
                rule_name="backend_configuration_required",
                affected_resources=["terraform.backend"]
            ))
        
        # Check for state locking (if using supported backend)
        if backend_config and self.state_requirements.get('state_locking_required'):
            backend_type = list(backend_config.keys())[0] if backend_config else None
            if backend_type == 's3':
                s3_config = backend_config.get('s3', {})
                if not s3_config.get('dynamodb_table'):
                    violations.append(BestPracticeIssue(
                        severity=Severity.HIGH,
                        category=Category.BEST_PRACTICES,
                        description="S3 backend is missing DynamoDB table for state locking",
                        file_path=tf_file.path,
                        line_number=1,
                        recommendation="Add dynamodb_table parameter to enable state locking",
                        rule_name="state_locking_required",
                        affected_resources=["terraform.backend.s3"]
                    ))
        
        return violations
    
    def _check_version_pinning(self, tf_file: TerraformFile) -> List[BestPracticeIssue]:
        """Check version pinning best practices."""
        violations = []
        
        if not tf_file.ast:
            return violations
        
        # Check Terraform version constraint
        if self.version_requirements.get('terraform_version_required'):
            terraform_block = tf_file.ast.terraform_block or {}
            if not terraform_block.get('required_version'):
                violations.append(BestPracticeIssue(
                    severity=Severity.HIGH,
                    category=Category.BEST_PRACTICES,
                    description="Terraform version constraint is not specified",
                    file_path=tf_file.path,
                    line_number=1,
                    recommendation="Add required_version constraint in terraform block",
                    rule_name="terraform_version_required",
                    affected_resources=["terraform.required_version"]
                ))
        
        # Check provider version constraints
        if self.version_requirements.get('provider_versions_required'):
            terraform_block = tf_file.ast.terraform_block or {}
            required_providers = terraform_block.get('required_providers', {})
            
            for provider in tf_file.ast.providers:
                provider_name = provider.get('name') or list(provider.keys())[0]
                if provider_name not in required_providers:
                    violations.append(BestPracticeIssue(
                        severity=Severity.HIGH,
                        category=Category.BEST_PRACTICES,
                        description=f"Provider '{provider_name}' is not version constrained",
                        file_path=tf_file.path,
                        line_number=1,
                        recommendation="Add version constraint in required_providers block",
                        rule_name="provider_version_required",
                        affected_resources=[f"provider.{provider_name}"]
                    ))
        
        return violations
    
    def check_documentation(self, files: List[TerraformFile]) -> List[BestPracticeIssue]:
        """Check documentation completeness across all files."""
        violations = []
        
        # Check for README file
        if self.doc_requirements.get('readme_required'):
            file_dirs = {Path(f.path).parent for f in files}
            for directory in file_dirs:
                readme_files = list(directory.glob('README*'))
                if not readme_files:
                    violations.append(BestPracticeIssue(
                        severity=Severity.MEDIUM,
                        category=Category.DOCUMENTATION,
                        description=f"No README file found in directory {directory}",
                        file_path=str(directory),
                        line_number=1,
                        recommendation="Add README.md with module description, usage examples, and requirements",
                        rule_name="readme_required",
                        affected_resources=["documentation"]
                    ))
        
        # Check inline documentation coverage
        if self.doc_requirements.get('inline_comments_threshold'):
            for tf_file in files:
                violations.extend(self._check_inline_documentation(tf_file))
        
        return violations
    
    def _check_inline_documentation(self, tf_file: TerraformFile) -> List[BestPracticeIssue]:
        """Check inline documentation coverage for a file."""
        violations = []
        
        # This is a simplified check - in a real implementation, you'd parse comments from the HCL
        total_resources = len(tf_file.resources)
        if total_resources == 0:
            return violations
        
        # For now, assume low documentation coverage as an example
        # In practice, you'd parse the actual file to count comments
        threshold = self.doc_requirements.get('inline_comments_threshold', 0.3)
        documented_resources = 0  # Would be calculated from actual comment parsing
        
        coverage = documented_resources / total_resources if total_resources > 0 else 0
        
        if coverage < threshold:
            violations.append(BestPracticeIssue(
                severity=Severity.LOW,
                category=Category.DOCUMENTATION,
                description=f"Low inline documentation coverage ({coverage:.1%}). "
                           f"Expected at least {threshold:.1%}",
                file_path=tf_file.path,
                line_number=1,
                recommendation="Add inline comments explaining complex resources and configurations",
                rule_name="inline_documentation_coverage",
                affected_resources=[f"{r.type}.{r.name}" for r in tf_file.resources]
            ))
        
        return violations
    
    def _generate_summary(self, violations: List[BestPracticeIssue]) -> Dict[str, int]:
        """Generate summary statistics for violations."""
        summary = {
            'total_violations': len(violations),
            'critical': 0,
            'high': 0,
            'medium': 0,
            'low': 0
        }
        
        for violation in violations:
            summary[violation.severity.value.lower()] += 1
        
        # Add category breakdown
        categories = {}
        for violation in violations:
            category = violation.category.value
            categories[category] = categories.get(category, 0) + 1
        
        summary.update(categories)
        return summary
    
    def _generate_recommendations(self, violations: List[BestPracticeIssue]) -> List[str]:
        """Generate high-level recommendations based on violations."""
        recommendations = []
        
        # Count violations by rule
        rule_counts = {}
        for violation in violations:
            rule_counts[violation.rule_name] = rule_counts.get(violation.rule_name, 0) + 1
        
        # Generate recommendations for most common issues
        if rule_counts.get('variable_description_required', 0) > 0:
            recommendations.append(
                "Add descriptions to all variables to improve code maintainability and understanding"
            )
        
        if rule_counts.get('provider_version_required', 0) > 0:
            recommendations.append(
                "Pin provider versions to ensure reproducible deployments and avoid breaking changes"
            )
        
        if rule_counts.get('backend_configuration_required', 0) > 0:
            recommendations.append(
                "Configure remote backend for state management to enable team collaboration"
            )
        
        if rule_counts.get('readme_required', 0) > 0:
            recommendations.append(
                "Add README files to document module usage, requirements, and examples"
            )
        
        if rule_counts.get('module_version_pinning', 0) > 0:
            recommendations.append(
                "Pin external module versions to prevent unexpected changes during deployments"
            )
        
        return recommendations
    
    def check_naming_conventions(self, resources: List[Dict[str, Any]]) -> List[BestPracticeIssue]:
        """Check resource naming conventions (legacy interface)."""
        # Convert dict resources to Resource objects for validation
        violations = []
        for resource_dict in resources:
            # Create a mock Resource object
            resource = Resource(
                type=resource_dict.get('type', 'unknown'),
                name=resource_dict.get('name', 'unknown'),
                provider=resource_dict.get('provider', 'unknown'),
                configuration=resource_dict.get('configuration', {}),
                line_number=resource_dict.get('line_number', 1)
            )
            violations.extend(self._validate_resource_naming(resource, resource_dict.get('file_path', 'unknown')))
        
        return violations
    
    def validate_module_structure(self, modules: List[Dict[str, Any]]) -> List[BestPracticeIssue]:
        """Validate module organization and structure (legacy interface)."""
        violations = []
        
        for module_dict in modules:
            # Check module versioning
            if not module_dict.get('version') and not module_dict.get('source', '').startswith('./'):
                violations.append(BestPracticeIssue(
                    severity=Severity.HIGH,
                    category=Category.BEST_PRACTICES,
                    description=f"Module '{module_dict.get('name', 'unknown')}' is not version pinned",
                    file_path=module_dict.get('file_path', 'unknown'),
                    line_number=module_dict.get('line_number', 1),
                    recommendation="Pin module to specific version",
                    rule_name="module_version_pinning",
                    affected_resources=[f"module.{module_dict.get('name', 'unknown')}"]
                ))
        
        return violations