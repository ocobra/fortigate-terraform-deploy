"""
Pytest configuration and shared fixtures for the FortiGate Terraform Analysis System tests.
"""

import pytest
from pathlib import Path
from typing import Dict, Any
from datetime import datetime

from fortigate_analysis.models import (
    TerraformFile,
    RepositoryInventory,
    TerraformAST,
    Variable,
    Resource,
    Output,
    Module,
)


@pytest.fixture
def sample_terraform_file() -> TerraformFile:
    """Create a sample Terraform file for testing."""
    return TerraformFile(
        path="aws/single-instance/main.tf",
        cloud_provider="aws",
        deployment_type="single-instance",
        fortigate_versions=["7.4", "7.6"],
        file_size=1024,
        last_modified=datetime.now(),
        encoding="utf-8"
    )


@pytest.fixture
def sample_terraform_ast() -> TerraformAST:
    """Create a sample Terraform AST for testing."""
    return TerraformAST(
        variables=[
            Variable(name="instance_type", type="string", default="t3.medium"),
            Variable(name="key_name", type="string", description="EC2 Key Pair name")
        ],
        resources=[
            Resource(
                type="aws_instance",
                name="fortigate",
                provider="aws",
                configuration={"instance_type": "${var.instance_type}"},
                line_number=10
            )
        ],
        outputs=[
            Output(name="instance_id", value="${aws_instance.fortigate.id}")
        ]
    )


@pytest.fixture
def sample_repository_inventory() -> RepositoryInventory:
    """Create a sample repository inventory for testing."""
    return RepositoryInventory(
        terraform_files=[],
        python_files=[],
        documentation_files=[],
        total_files=0,
        repository_size=0,
        scan_timestamp=datetime.now()
    )


@pytest.fixture
def temp_repository(tmp_path: Path) -> Path:
    """Create a temporary repository structure for testing."""
    # Create cloud provider directories
    for provider in ["aws", "azure", "gcp"]:
        provider_dir = tmp_path / provider
        provider_dir.mkdir()
        
        # Create a sample Terraform file
        tf_file = provider_dir / "main.tf"
        tf_file.write_text(f"""
# {provider.upper()} FortiGate deployment
resource "{provider}_instance" "fortigate" {{
  instance_type = "t3.medium"
  ami           = "ami-12345678"
}}

variable "instance_type" {{
  description = "EC2 instance type"
  type        = string
  default     = "t3.medium"
}}

output "instance_id" {{
  value = {provider}_instance.fortigate.id
}}
""")
    
    # Create a README file
    readme = tmp_path / "README.md"
    readme.write_text("# FortiGate Terraform Deployments\n\nMulti-cloud FortiGate deployments.")
    
    return tmp_path


@pytest.fixture
def analysis_config() -> Dict[str, Any]:
    """Create a sample analysis configuration for testing."""
    return {
        "security": {
            "check_secrets": True,
            "check_encryption": True,
            "check_access_controls": True
        },
        "best_practices": {
            "check_naming": True,
            "check_documentation": True,
            "check_module_structure": True
        },
        "output": {
            "formats": ["json", "html"],
            "include_metrics": True
        }
    }