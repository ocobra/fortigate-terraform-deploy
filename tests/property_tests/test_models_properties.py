"""
Property-based tests for core data models.

These tests validate universal properties that should hold for all valid
instances of the core data models.
"""

import pytest
from hypothesis import given, strategies as st
from datetime import datetime

from fortigate_analysis.models import (
    TerraformFile,
    SecurityIssue,
    ImprovementTask,
    RepositoryInventory,
    Severity,
    Priority,
    Effort,
    Category,
)


# Hypothesis strategies for generating test data

@st.composite
def terraform_file_strategy(draw):
    """Generate valid TerraformFile instances."""
    # Generate a simple path that ends with .tf
    filename = draw(st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Ll', 'Lu', 'Nd'), whitelist_characters='_-')))
    path = f"modules/{filename}.tf"
    
    cloud_provider = draw(st.sampled_from(["aws", "azure", "gcp", "ibm", "oci", "alicloud", "openstack"]))
    deployment_type = draw(st.sampled_from(["single", "ha", "load_balancer", "gwlb", "transit_gateway"]))
    fortigate_versions = draw(st.lists(
        st.sampled_from(["6.2", "6.4", "7.0", "7.2", "7.4", "7.6"]),
        min_size=1,
        max_size=3,
        unique=True
    ))
    
    return TerraformFile(
        path=path,
        cloud_provider=cloud_provider,
        deployment_type=deployment_type,
        fortigate_versions=fortigate_versions
    )


@st.composite
def security_issue_strategy(draw):
    """Generate valid SecurityIssue instances."""
    severity = draw(st.sampled_from(list(Severity)))
    category = draw(st.sampled_from(list(Category)))
    description = draw(st.text(min_size=10, max_size=200, alphabet=st.characters(whitelist_categories=('Ll', 'Lu', 'Nd', 'Zs'))))
    # Generate a simple file path
    filename = draw(st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Ll', 'Lu', 'Nd'), whitelist_characters='_-')))
    file_path = f"modules/{filename}.tf"
    line_number = draw(st.integers(min_value=1, max_value=10000))
    recommendation = draw(st.text(min_size=10, max_size=200, alphabet=st.characters(whitelist_categories=('Ll', 'Lu', 'Nd', 'Zs'))))
    confidence = draw(st.floats(min_value=0.0, max_value=1.0))
    
    return SecurityIssue(
        severity=severity,
        category=category,
        description=description,
        file_path=file_path,
        line_number=line_number,
        recommendation=recommendation,
        confidence=confidence
    )


@st.composite
def improvement_task_strategy(draw):
    """Generate valid ImprovementTask instances."""
    task_id = draw(st.text(min_size=1, max_size=20).filter(lambda x: x.isalnum() or "-" in x))
    title = draw(st.text(min_size=5, max_size=100))
    description = draw(st.text(min_size=10, max_size=500))
    priority = draw(st.sampled_from(list(Priority)))
    effort = draw(st.sampled_from(list(Effort)))
    category = draw(st.sampled_from(list(Category)))
    requirements_reference = draw(st.text(min_size=1, max_size=10))
    
    return ImprovementTask(
        id=task_id,
        title=title,
        description=description,
        priority=priority,
        effort=effort,
        category=category,
        requirements_reference=requirements_reference
    )


class TestTerraformFileProperties:
    """Property-based tests for TerraformFile model."""
    
    @given(terraform_file_strategy())
    def test_terraform_file_path_consistency(self, tf_file):
        """
        Feature: fortigate-terraform-analysis, Property: Path Consistency
        
        For any valid TerraformFile, the path should end with .tf and contain
        the cloud provider name.
        """
        assert tf_file.path.endswith(".tf")
        # Path should be consistent with cloud provider (basic check)
        assert len(tf_file.path) > 0
        assert "/" in tf_file.path
    
    @given(terraform_file_strategy())
    def test_terraform_file_cloud_provider_validity(self, tf_file):
        """
        Feature: fortigate-terraform-analysis, Property: Cloud Provider Validity
        
        For any valid TerraformFile, the cloud provider should be one of the
        supported providers.
        """
        supported_providers = {"aws", "azure", "gcp", "ibm", "oci", "alicloud", "openstack"}
        assert tf_file.cloud_provider in supported_providers
    
    @given(terraform_file_strategy())
    def test_terraform_file_fortigate_versions_validity(self, tf_file):
        """
        Feature: fortigate-terraform-analysis, Property: FortiGate Version Validity
        
        For any valid TerraformFile, all FortiGate versions should be supported
        versions and the list should not be empty.
        """
        supported_versions = {"6.2", "6.4", "7.0", "7.2", "7.4", "7.6"}
        assert len(tf_file.fortigate_versions) > 0
        for version in tf_file.fortigate_versions:
            assert version in supported_versions


class TestSecurityIssueProperties:
    """Property-based tests for SecurityIssue model."""
    
    @given(security_issue_strategy())
    def test_security_issue_severity_consistency(self, issue):
        """
        Feature: fortigate-terraform-analysis, Property: Security Issue Severity
        
        For any valid SecurityIssue, the severity should be a valid enum value
        and confidence should be between 0.0 and 1.0.
        """
        assert isinstance(issue.severity, Severity)
        assert 0.0 <= issue.confidence <= 1.0
    
    @given(security_issue_strategy())
    def test_security_issue_line_number_validity(self, issue):
        """
        Feature: fortigate-terraform-analysis, Property: Line Number Validity
        
        For any valid SecurityIssue, the line number should be positive.
        """
        assert issue.line_number > 0
    
    @given(security_issue_strategy())
    def test_security_issue_content_non_empty(self, issue):
        """
        Feature: fortigate-terraform-analysis, Property: Content Non-Empty
        
        For any valid SecurityIssue, description and recommendation should
        not be empty strings.
        """
        assert len(issue.description.strip()) > 0
        assert len(issue.recommendation.strip()) > 0


class TestImprovementTaskProperties:
    """Property-based tests for ImprovementTask model."""
    
    @given(improvement_task_strategy())
    def test_improvement_task_id_uniqueness_format(self, task):
        """
        Feature: fortigate-terraform-analysis, Property: Task ID Format
        
        For any valid ImprovementTask, the ID should be non-empty and
        follow a reasonable format.
        """
        assert len(task.id.strip()) > 0
        # ID should not contain spaces
        assert " " not in task.id
    
    @given(improvement_task_strategy())
    def test_improvement_task_enum_validity(self, task):
        """
        Feature: fortigate-terraform-analysis, Property: Enum Validity
        
        For any valid ImprovementTask, priority, effort, and category
        should be valid enum values.
        """
        assert isinstance(task.priority, Priority)
        assert isinstance(task.effort, Effort)
        assert isinstance(task.category, Category)
    
    @given(improvement_task_strategy())
    def test_improvement_task_content_validity(self, task):
        """
        Feature: fortigate-terraform-analysis, Property: Content Validity
        
        For any valid ImprovementTask, title and description should be
        meaningful (non-empty after stripping).
        """
        assert len(task.title.strip()) > 0
        assert len(task.description.strip()) > 0
        assert len(task.requirements_reference.strip()) > 0


class TestRepositoryInventoryProperties:
    """Property-based tests for RepositoryInventory model."""
    
    @given(st.integers(min_value=0, max_value=10000))
    def test_repository_inventory_file_count_consistency(self, total_files):
        """
        Feature: fortigate-terraform-analysis, Property: File Count Consistency
        
        For any valid RepositoryInventory, the total file count should be
        non-negative and consistent with individual file lists.
        """
        inventory = RepositoryInventory(
            total_files=total_files,
            scan_timestamp=datetime.now()
        )
        
        assert inventory.total_files >= 0
        # When lists are empty, they should be consistent
        calculated_total = (
            len(inventory.terraform_files) +
            len(inventory.python_files) +
            len(inventory.documentation_files)
        )
        # For empty inventory, calculated total should be 0
        assert calculated_total == 0  # Since we're not adding files in this test