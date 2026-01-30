"""
Unit tests for the core data models.
"""

import pytest
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


class TestTerraformFile:
    """Test cases for TerraformFile model."""
    
    def test_terraform_file_creation(self):
        """Test creating a TerraformFile instance."""
        tf_file = TerraformFile(
            path="aws/main.tf",
            cloud_provider="aws",
            deployment_type="single-instance",
            fortigate_versions=["7.4", "7.6"]
        )
        
        assert tf_file.path == "aws/main.tf"
        assert tf_file.cloud_provider == "aws"
        assert tf_file.deployment_type == "single-instance"
        assert tf_file.fortigate_versions == ["7.4", "7.6"]
        assert tf_file.variables == []
        assert tf_file.resources == []
        assert tf_file.outputs == []
        assert tf_file.modules == []


class TestSecurityIssue:
    """Test cases for SecurityIssue model."""
    
    def test_security_issue_creation(self):
        """Test creating a SecurityIssue instance."""
        issue = SecurityIssue(
            severity=Severity.HIGH,
            category=Category.SECRETS,
            description="Hardcoded password found",
            file_path="aws/main.tf",
            line_number=25,
            recommendation="Use variables or secrets manager"
        )
        
        assert issue.severity == Severity.HIGH
        assert issue.category == Category.SECRETS
        assert issue.description == "Hardcoded password found"
        assert issue.file_path == "aws/main.tf"
        assert issue.line_number == 25
        assert issue.recommendation == "Use variables or secrets manager"
        assert issue.confidence == 1.0


class TestImprovementTask:
    """Test cases for ImprovementTask model."""
    
    def test_improvement_task_creation(self):
        """Test creating an ImprovementTask instance."""
        task = ImprovementTask(
            id="TASK-001",
            title="Fix hardcoded secrets",
            description="Replace hardcoded passwords with variables",
            priority=Priority.HIGH,
            effort=Effort.MEDIUM,
            category=Category.SECURITY,
            requirements_reference="3.3"
        )
        
        assert task.id == "TASK-001"
        assert task.title == "Fix hardcoded secrets"
        assert task.priority == Priority.HIGH
        assert task.effort == Effort.MEDIUM
        assert task.category == Category.SECURITY
        assert task.requirements_reference == "3.3"
        assert not task.completed
        assert task.implementation_steps == []
        assert task.validation_criteria == []


class TestRepositoryInventory:
    """Test cases for RepositoryInventory model."""
    
    def test_repository_inventory_creation(self):
        """Test creating a RepositoryInventory instance."""
        inventory = RepositoryInventory(
            total_files=10,
            repository_size=1024000,
            scan_timestamp=datetime.now()
        )
        
        assert inventory.total_files == 10
        assert inventory.repository_size == 1024000
        assert inventory.scan_timestamp is not None
        assert inventory.terraform_files == []
        assert inventory.python_files == []
        assert inventory.documentation_files == []