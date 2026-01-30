"""
Unit tests for the RepositoryScanner class.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, mock_open

from fortigate_analysis.scanner.repository_scanner import RepositoryScanner
from fortigate_analysis.models import TerraformFile, PythonFile, DocumentationFile


class TestRepositoryScanner:
    """Test cases for RepositoryScanner class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.scanner = RepositoryScanner()
        self.temp_dir = None
    
    def teardown_method(self):
        """Clean up test fixtures."""
        if self.temp_dir and Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)
    
    def create_temp_repo(self, structure):
        """
        Create a temporary repository with the given structure.
        
        Args:
            structure: Dict representing directory structure
        """
        self.temp_dir = tempfile.mkdtemp()
        repo_path = Path(self.temp_dir)
        
        def create_structure(base_path, struct):
            for name, content in struct.items():
                path = base_path / name
                if isinstance(content, dict):
                    path.mkdir(exist_ok=True)
                    create_structure(path, content)
                else:
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text(content, encoding='utf-8')
        
        create_structure(repo_path, structure)
        return repo_path
    
    def test_scan_empty_repository(self):
        """Test scanning an empty repository."""
        repo_path = self.create_temp_repo({})
        
        inventory = self.scanner.scan_repository(repo_path)
        
        assert inventory.total_files == 0
        assert len(inventory.terraform_files) == 0
        assert len(inventory.python_files) == 0
        assert len(inventory.documentation_files) == 0
        assert inventory.scan_timestamp is not None
    
    def test_scan_nonexistent_repository(self):
        """Test scanning a non-existent repository."""
        nonexistent_path = Path("/nonexistent/path")
        
        with pytest.raises(FileNotFoundError):
            self.scanner.scan_repository(nonexistent_path)
    
    def test_scan_file_instead_of_directory(self):
        """Test scanning a file instead of directory."""
        repo_path = self.create_temp_repo({"test.txt": "content"})
        file_path = repo_path / "test.txt"
        
        with pytest.raises(ValueError):
            self.scanner.scan_repository(file_path)
    
    def test_discover_terraform_files(self):
        """Test discovery of Terraform files."""
        structure = {
            "main.tf": """
                provider "aws" {
                  region = "us-west-2"
                }
                
                resource "aws_instance" "fortigate" {
                  ami           = "ami-12345"
                  instance_type = "t3.medium"
                }
            """,
            "variables.tf": """
                variable "region" {
                  description = "AWS region"
                  type        = string
                  default     = "us-west-2"
                }
            """,
            "terraform.tfvars": """
                region = "us-east-1"
            """,
            "modules": {
                "vpc": {
                    "main.tf": """
                        resource "aws_vpc" "main" {
                          cidr_block = "10.0.0.0/16"
                        }
                    """
                }
            }
        }
        
        repo_path = self.create_temp_repo(structure)
        inventory = self.scanner.scan_repository(repo_path)
        
        assert len(inventory.terraform_files) == 4
        assert inventory.total_files == 4
        
        # Check file paths
        tf_paths = [f.path for f in inventory.terraform_files]
        assert "main.tf" in tf_paths
        assert "variables.tf" in tf_paths
        assert "terraform.tfvars" in tf_paths
        assert "modules/vpc/main.tf" in tf_paths
        
        # Check cloud provider detection
        main_tf = next(f for f in inventory.terraform_files if f.path == "main.tf")
        assert main_tf.cloud_provider == "aws"
    
    def test_discover_python_files(self):
        """Test discovery of Python files."""
        structure = {
            "deploy.py": """
                #!/usr/bin/env python3
                import boto3
                
                def deploy_fortigate():
                    pass
                
                def main():
                    deploy_fortigate()
                
                if __name__ == "__main__":
                    main()
            """,
            "utils": {
                "helpers.py": """
                    def get_config():
                        return {}
                """
            },
            "tests": {
                "test_deploy.py": """
                    import pytest
                    
                    def test_deploy():
                        assert True
                """
            }
        }
        
        repo_path = self.create_temp_repo(structure)
        inventory = self.scanner.scan_repository(repo_path)
        
        assert len(inventory.python_files) == 3
        
        # Check file paths and purposes
        py_files = {f.path: f for f in inventory.python_files}
        
        assert "deploy.py" in py_files
        assert py_files["deploy.py"].purpose == "deployment"
        assert "main" in py_files["deploy.py"].functions
        assert "deploy_fortigate" in py_files["deploy.py"].functions
        assert "boto3" in py_files["deploy.py"].imports
        
        assert "utils/helpers.py" in py_files
        assert py_files["utils/helpers.py"].purpose == "utility"
        
        assert "tests/test_deploy.py" in py_files
        assert py_files["tests/test_deploy.py"].purpose == "test"
    
    def test_discover_documentation_files(self):
        """Test discovery of documentation files."""
        structure = {
            "README.md": """
                # FortiGate Terraform Deployment
                
                This repository contains Terraform configurations for deploying FortiGate.
            """,
            "docs": {
                "deployment-guide.md": """
                    # Deployment Guide
                    
                    Follow these steps to deploy FortiGate.
                """,
                "api.txt": """
                    API Documentation
                    
                    This file contains API documentation.
                """
            },
            "CHANGELOG.md": """
                # Changelog
                
                ## v1.0.0
                - Initial release
            """
        }
        
        repo_path = self.create_temp_repo(structure)
        inventory = self.scanner.scan_repository(repo_path)
        
        assert len(inventory.documentation_files) == 4  # Updated to match actual count
        
        # Check file types
        doc_files = {f.path: f for f in inventory.documentation_files}
        
        assert "README.md" in doc_files
        assert doc_files["README.md"].type == "README"
        
        assert "docs/deployment-guide.md" in doc_files
        assert doc_files["docs/deployment-guide.md"].type == "guide"
        
        assert "CHANGELOG.md" in doc_files
        assert doc_files["CHANGELOG.md"].type == "changelog"
    
    def test_cloud_provider_detection(self):
        """Test cloud provider detection from content and paths."""
        structure = {
            "aws": {
                "main.tf": """
                    resource "aws_instance" "test" {}
                """
            },
            "azure": {
                "main.tf": """
                    resource "azurerm_virtual_machine" "test" {}
                """
            },
            "gcp": {
                "main.tf": """
                    resource "google_compute_instance" "test" {}
                """
            }
        }
        
        repo_path = self.create_temp_repo(structure)
        inventory = self.scanner.scan_repository(repo_path)
        
        tf_files = {f.path: f for f in inventory.terraform_files}
        
        assert tf_files["aws/main.tf"].cloud_provider == "aws"
        assert tf_files["azure/main.tf"].cloud_provider == "azure"
        assert tf_files["gcp/main.tf"].cloud_provider == "gcp"
    
    def test_deployment_type_detection(self):
        """Test deployment type detection."""
        structure = {
            "single": {
                "main.tf": "# Single FortiGate deployment"
            },
            "ha": {
                "main.tf": "# High availability FortiGate cluster"
            },
            "load-balancer": {
                "main.tf": "# FortiGate with load balancer"
            }
        }
        
        repo_path = self.create_temp_repo(structure)
        inventory = self.scanner.scan_repository(repo_path)
        
        tf_files = {f.path: f for f in inventory.terraform_files}
        
        assert tf_files["single/main.tf"].deployment_type == "single"
        assert tf_files["ha/main.tf"].deployment_type == "ha"
        assert tf_files["load-balancer/main.tf"].deployment_type == "load_balancer"
    
    def test_fortigate_version_detection(self):
        """Test FortiGate version detection."""
        structure = {
            "main.tf": """
                # FortiGate 7.2 configuration
                # Supports versions 6.4, 7.0, and v7.2
                variable "fortigate_version" {
                  default = "7.4"
                }
            """
        }
        
        repo_path = self.create_temp_repo(structure)
        inventory = self.scanner.scan_repository(repo_path)
        
        tf_file = inventory.terraform_files[0]
        versions = set(tf_file.fortigate_versions)
        
        assert "7.2" in versions
        assert "6.4" in versions
        assert "7.0" in versions
        assert "7.4" in versions
    
    def test_exclude_directories(self):
        """Test exclusion of specified directories."""
        structure = {
            "main.tf": "resource 'aws_instance' 'test' {}",
            ".git": {
                "config": "git config"
            },
            ".terraform": {
                "providers": {
                    "registry.terraform.io": {
                        "hashicorp": {
                            "aws": "provider"
                        }
                    }
                }
            },
            "__pycache__": {
                "module.pyc": "compiled python"
            },
            "valid_dir": {
                "config.tf": "resource 'aws_vpc' 'test' {}"
            }
        }
        
        repo_path = self.create_temp_repo(structure)
        inventory = self.scanner.scan_repository(repo_path)
        
        # Should only find files in root and valid_dir
        assert len(inventory.terraform_files) == 2
        tf_paths = [f.path for f in inventory.terraform_files]
        assert "main.tf" in tf_paths
        assert "valid_dir/config.tf" in tf_paths
        
        # Should not find files in excluded directories
        assert not any(".git" in path for path in tf_paths)
        assert not any(".terraform" in path for path in tf_paths)
        assert not any("__pycache__" in path for path in tf_paths)
    
    def test_file_metadata_extraction(self):
        """Test extraction of file metadata."""
        structure = {
            "test.tf": "resource 'aws_instance' 'test' {}"
        }
        
        repo_path = self.create_temp_repo(structure)
        inventory = self.scanner.scan_repository(repo_path)
        
        tf_file = inventory.terraform_files[0]
        
        assert tf_file.file_size > 0
        assert tf_file.last_modified is not None
        assert isinstance(tf_file.last_modified, datetime)
        assert tf_file.encoding in ["utf-8", "ascii"]  # Both are valid for simple text
    
    def test_encoding_detection(self):
        """Test encoding detection for different file encodings."""
        # Create a file with non-UTF-8 content
        self.temp_dir = tempfile.mkdtemp()
        repo_path = Path(self.temp_dir)
        
        # Create a file with latin-1 encoding
        test_file = repo_path / "test.tf"
        test_content = "# Configuración con acentos: ñáéíóú"
        test_file.write_bytes(test_content.encode('latin-1'))
        
        inventory = self.scanner.scan_repository(repo_path)
        
        assert len(inventory.terraform_files) == 1
        tf_file = inventory.terraform_files[0]
        
        # Should detect encoding (might be latin-1 or similar)
        assert tf_file.encoding is not None
        assert tf_file.encoding != "utf-8"  # Should detect different encoding
    
    def test_large_file_handling(self):
        """Test handling of large files."""
        # Configure scanner with small max file size
        scanner = RepositoryScanner(config={'max_file_size': 100})
        
        structure = {
            "small.tf": "resource 'aws_instance' 'test' {}",
            "large.tf": "# " + "x" * 200  # File larger than 100 bytes
        }
        
        repo_path = self.create_temp_repo(structure)
        inventory = scanner.scan_repository(repo_path)
        
        # Should only find the small file
        assert len(inventory.terraform_files) == 1
        assert inventory.terraform_files[0].path == "small.tf"
    
    def test_cloud_provider_configs_generation(self):
        """Test generation of cloud provider configurations."""
        structure = {
            "aws": {
                "single": {
                    "main.tf": """
                        # FortiGate 7.2 single deployment
                        resource "aws_instance" "fortigate" {}
                    """
                },
                "ha": {
                    "main.tf": """
                        # FortiGate 7.4 HA deployment
                        resource "aws_instance" "fortigate_primary" {}
                        resource "aws_instance" "fortigate_secondary" {}
                    """
                }
            },
            "azure": {
                "single": {
                    "main.tf": """
                        # FortiGate 7.2 single deployment
                        resource "azurerm_virtual_machine" "fortigate" {}
                    """
                }
            }
        }
        
        repo_path = self.create_temp_repo(structure)
        inventory = self.scanner.scan_repository(repo_path)
        
        # Check cloud provider configs
        assert "aws" in inventory.cloud_provider_configs
        assert "azure" in inventory.cloud_provider_configs
        
        aws_config = inventory.cloud_provider_configs["aws"]
        assert aws_config.provider == "aws"
        assert "single" in aws_config.deployment_scenarios
        assert "ha" in aws_config.deployment_scenarios
        assert "7.2" in aws_config.supported_versions
        assert "7.4" in aws_config.supported_versions
        assert len(aws_config.configuration_files) == 2
        
        azure_config = inventory.cloud_provider_configs["azure"]
        assert azure_config.provider == "azure"
        assert "single" in azure_config.deployment_scenarios
        assert "7.2" in azure_config.supported_versions
        assert len(azure_config.configuration_files) == 1
    
    def test_error_handling_permission_denied(self):
        """Test error handling for permission denied scenarios."""
        structure = {
            "main.tf": "resource 'aws_instance' 'test' {}"
        }
        
        repo_path = self.create_temp_repo(structure)
        
        # Mock permission error
        with patch('pathlib.Path.iterdir', side_effect=PermissionError("Permission denied")):
            # Should not raise exception, but handle gracefully
            inventory = self.scanner.scan_repository(repo_path)
            # Should still return valid inventory even if some directories fail
            assert inventory is not None
    
    def test_error_handling_corrupted_file(self):
        """Test error handling for corrupted files."""
        structure = {
            "good.tf": "resource 'aws_instance' 'test' {}",
            "bad.tf": "corrupted content"
        }
        
        repo_path = self.create_temp_repo(structure)
        
        # Mock file reading error for one file
        original_read = Path.read_text
        
        def mock_read_text(self, encoding='utf-8', errors='strict'):
            if self.name == "bad.tf":
                raise UnicodeDecodeError("utf-8", b"", 0, 1, "invalid start byte")
            return original_read(self, encoding=encoding, errors=errors)
        
        with patch.object(Path, 'read_text', mock_read_text):
            inventory = self.scanner.scan_repository(repo_path)
            
            # Should still process good files
            assert len(inventory.terraform_files) >= 1
            
            # Check if bad file was processed with error
            bad_file = next((f for f in inventory.terraform_files if f.path == "bad.tf"), None)
            if bad_file:
                # If the bad file was processed, it should have error information
                assert len(bad_file.syntax_errors) > 0 or bad_file.cloud_provider == 'unknown'
    
    def test_get_methods(self):
        """Test getter methods for different file types."""
        structure = {
            "main.tf": "resource 'aws_instance' 'test' {}",
            "deploy.py": "def deploy(): pass",
            "README.md": "# Documentation"
        }
        
        repo_path = self.create_temp_repo(structure)
        self.scanner.scan_repository(repo_path)
        
        # Test getter methods
        terraform_files = self.scanner.get_terraform_files()
        python_files = self.scanner.get_python_files()
        doc_files = self.scanner.get_documentation_files()
        cloud_configs = self.scanner.get_cloud_provider_configs()
        
        assert len(terraform_files) == 1
        assert len(python_files) == 1
        assert len(doc_files) == 1
        assert len(cloud_configs) > 0
        
        # Check that cloud configs group files correctly
        assert "aws" in cloud_configs  # Based on content detection
        assert len(cloud_configs["aws"]) == 1