"""
Tests for multi-cloud security validation functionality.
"""

import pytest
from unittest.mock import Mock, patch

from fortigate_analysis.analyzer.security_analyzer import SecurityAnalyzer
from fortigate_analysis.models import (
    TerraformFile, Resource, SecurityIssue, Severity, Category, TerraformAST
)


class TestMultiCloudSecurityValidation:
    """Test multi-cloud security validation functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.analyzer = SecurityAnalyzer()
    
    def test_validate_multicloud_security_aws(self):
        """Test AWS-specific security validation."""
        # Create AWS EC2 resource without IMDSv2
        resource = Resource(
            type="aws_instance",
            name="test-instance",
            provider="aws",
            configuration={
                "metadata_options": {
                    "http_tokens": "optional"  # Should trigger IMDSv2 issue
                },
                "monitoring": False  # Should trigger monitoring issue
            },
            line_number=10
        )
        
        issues = self.analyzer.validate_multicloud_security([resource], "aws")
        
        # Should find IMDSv2 and monitoring issues
        assert len(issues) >= 2
        
        # Check for IMDSv2 issue
        imdsv2_issues = [i for i in issues if i.rule_id == "ec2_imdsv2_not_enforced"]
        assert len(imdsv2_issues) == 1
        assert imdsv2_issues[0].severity == Severity.MEDIUM
        
        # Check for monitoring issue
        monitoring_issues = [i for i in issues if i.rule_id == "ec2_detailed_monitoring_disabled"]
        assert len(monitoring_issues) == 1
        assert monitoring_issues[0].severity == Severity.LOW
    
    def test_validate_multicloud_security_azure(self):
        """Test Azure-specific security validation."""
        # Create Azure VM resource without managed identity
        resource = Resource(
            type="azurerm_virtual_machine",
            name="test-vm",
            provider="azurerm",
            configuration={
                # Missing identity configuration
                "boot_diagnostics": {}  # Empty but present
            },
            line_number=15
        )
        
        issues = self.analyzer.validate_multicloud_security([resource], "azure")
        
        # Should find managed identity issue
        identity_issues = [i for i in issues if i.rule_id == "azure_vm_no_managed_identity"]
        assert len(identity_issues) == 1
        assert identity_issues[0].severity == Severity.MEDIUM
    
    def test_validate_multicloud_security_gcp(self):
        """Test GCP-specific security validation."""
        # Create GCP compute instance without OS Login
        resource = Resource(
            type="google_compute_instance",
            name="test-instance",
            provider="google",
            configuration={
                "metadata": {
                    "enable-oslogin": "false",  # Should trigger OS Login issue
                    "serial-port-enable": "true"  # Should trigger serial port issue
                }
            },
            line_number=20
        )
        
        issues = self.analyzer.validate_multicloud_security([resource], "gcp")
        
        # Should find OS Login and serial port issues
        assert len(issues) >= 2
        
        # Check for OS Login issue
        oslogin_issues = [i for i in issues if i.rule_id == "gcp_compute_no_oslogin"]
        assert len(oslogin_issues) == 1
        assert oslogin_issues[0].severity == Severity.MEDIUM
        
        # Check for serial port issue
        serial_issues = [i for i in issues if i.rule_id == "gcp_compute_serial_port_enabled"]
        assert len(serial_issues) == 1
        assert serial_issues[0].severity == Severity.MEDIUM
    
    def test_validate_multicloud_security_ibm(self):
        """Test IBM Cloud-specific security validation."""
        # Create IBM VSI resource without boot volume encryption
        resource = Resource(
            type="ibm_is_instance",
            name="test-vsi",
            provider="ibm",
            configuration={
                "boot_volume": {
                    # Missing encryption configuration
                }
            },
            line_number=25
        )
        
        issues = self.analyzer.validate_multicloud_security([resource], "ibm")
        
        # Should find boot volume encryption issue
        encryption_issues = [i for i in issues if i.rule_id == "ibm_vsi_boot_volume_not_encrypted"]
        assert len(encryption_issues) == 1
        assert encryption_issues[0].severity == Severity.MEDIUM
    
    def test_validate_multicloud_security_alicloud(self):
        """Test AliCloud-specific security validation."""
        # Create AliCloud ECS instance without system disk encryption
        resource = Resource(
            type="alicloud_instance",
            name="test-ecs",
            provider="alicloud",
            configuration={
                "system_disk_encrypted": False  # Should trigger encryption issue
            },
            line_number=30
        )
        
        issues = self.analyzer.validate_multicloud_security([resource], "alicloud")
        
        # Should find system disk encryption issue
        encryption_issues = [i for i in issues if i.rule_id == "alicloud_ecs_system_disk_not_encrypted"]
        assert len(encryption_issues) == 1
        assert encryption_issues[0].severity == Severity.MEDIUM
    
    def test_validate_multicloud_security_openstack(self):
        """Test OpenStack-specific security validation."""
        # Create OpenStack compute instance without key pair
        resource = Resource(
            type="openstack_compute_instance_v2",
            name="test-instance",
            provider="openstack",
            configuration={
                # Missing key_pair configuration
            },
            line_number=35
        )
        
        issues = self.analyzer.validate_multicloud_security([resource], "openstack")
        
        # Should find key pair issue
        keypair_issues = [i for i in issues if i.rule_id == "openstack_compute_no_keypair"]
        assert len(keypair_issues) == 1
        assert keypair_issues[0].severity == Severity.MEDIUM
    
    def test_check_cross_cloud_consistency_encryption(self):
        """Test cross-cloud encryption consistency checking."""
        # Create files with different encryption configurations
        aws_file = TerraformFile(
            path="aws/main.tf",
            cloud_provider="aws",
            deployment_type="single",
            fortigate_versions=["7.0"],
            resources=[
                Resource(
                    type="aws_s3_bucket",
                    name="encrypted-bucket",
                    provider="aws",
                    configuration={
                        "server_side_encryption_configuration": {
                            "rule": {"apply_server_side_encryption_by_default": {"sse_algorithm": "AES256"}}
                        }
                    },
                    line_number=10
                )
            ]
        )
        
        azure_file = TerraformFile(
            path="azure/main.tf",
            cloud_provider="azure",
            deployment_type="single",
            fortigate_versions=["7.0"],
            resources=[
                Resource(
                    type="azurerm_storage_account",
                    name="unencrypted-storage",
                    provider="azurerm",
                    configuration={
                        # No encryption configuration
                    },
                    line_number=15
                )
            ]
        )
        
        issues = self.analyzer.check_cross_cloud_consistency([aws_file, azure_file])
        
        # Should find encryption inconsistency
        consistency_issues = [i for i in issues if i.rule_id == "cross_cloud_encryption_inconsistency"]
        assert len(consistency_issues) == 1
        assert consistency_issues[0].severity == Severity.MEDIUM
        assert "aws" in consistency_issues[0].description
        assert "azure" in consistency_issues[0].description
    
    def test_check_cross_cloud_consistency_network_security(self):
        """Test cross-cloud network security consistency checking."""
        # Create files with different network security configurations
        aws_file = TerraformFile(
            path="aws/main.tf",
            cloud_provider="aws",
            deployment_type="single",
            fortigate_versions=["7.0"],
            resources=[
                Resource(
                    type="aws_security_group",
                    name="permissive-sg",
                    provider="aws",
                    configuration={
                        "ingress": [{
                            "cidr_blocks": ["0.0.0.0/0"],
                            "from_port": 80,
                            "to_port": 80,
                            "protocol": "tcp"
                        }]
                    },
                    line_number=10
                )
            ]
        )
        
        gcp_file = TerraformFile(
            path="gcp/main.tf",
            cloud_provider="gcp",
            deployment_type="single",
            fortigate_versions=["7.0"],
            resources=[
                Resource(
                    type="google_compute_firewall",
                    name="restrictive-fw",
                    provider="google",
                    configuration={
                        "source_ranges": ["10.0.0.0/8"]  # Restrictive
                    },
                    line_number=15
                )
            ]
        )
        
        issues = self.analyzer.check_cross_cloud_consistency([aws_file, gcp_file])
        
        # Should find network security inconsistency
        consistency_issues = [i for i in issues if i.rule_id == "cross_cloud_network_inconsistency"]
        assert len(consistency_issues) == 1
        assert consistency_issues[0].severity == Severity.HIGH
        assert "aws" in consistency_issues[0].description
    
    def test_aws_s3_security_checks(self):
        """Test AWS S3-specific security checks."""
        resource = Resource(
            type="aws_s3_bucket",
            name="test-bucket",
            provider="aws",
            configuration={
                "versioning": {"enabled": False},  # Should trigger versioning issue
                # Missing logging configuration
            },
            line_number=10
        )
        
        issues = self.analyzer._check_aws_s3_security(resource)
        
        # Should find versioning and logging issues
        assert len(issues) >= 2
        
        versioning_issues = [i for i in issues if i.rule_id == "s3_versioning_disabled"]
        assert len(versioning_issues) == 1
        assert versioning_issues[0].severity == Severity.MEDIUM
        
        logging_issues = [i for i in issues if i.rule_id == "s3_access_logging_disabled"]
        assert len(logging_issues) == 1
        assert logging_issues[0].severity == Severity.LOW
    
    def test_azure_storage_security_checks(self):
        """Test Azure Storage Account security checks."""
        resource = Resource(
            type="azurerm_storage_account",
            name="test-storage",
            provider="azurerm",
            configuration={
                "enable_https_traffic_only": False,  # Should trigger HTTPS issue
                "min_tls_version": "TLS1_0"  # Should trigger TLS issue
            },
            line_number=15
        )
        
        issues = self.analyzer._check_azure_storage_security(resource)
        
        # Should find HTTPS and TLS issues
        assert len(issues) >= 2
        
        https_issues = [i for i in issues if i.rule_id == "azure_storage_https_not_enforced"]
        assert len(https_issues) == 1
        assert https_issues[0].severity == Severity.HIGH
        
        tls_issues = [i for i in issues if i.rule_id == "azure_storage_weak_tls"]
        assert len(tls_issues) == 1
        assert tls_issues[0].severity == Severity.MEDIUM
    
    def test_gcp_iam_security_checks(self):
        """Test GCP IAM security checks."""
        resource = Resource(
            type="google_project_iam_binding",
            name="test-binding",
            provider="google",
            configuration={
                "role": "roles/owner"  # Should trigger overly broad role issue
            },
            line_number=20
        )
        
        issues = self.analyzer._check_gcp_iam_security(resource)
        
        # Should find overly broad role issue
        role_issues = [i for i in issues if i.rule_id == "gcp_iam_overly_broad_role"]
        assert len(role_issues) == 1
        assert role_issues[0].severity == Severity.HIGH
        assert "roles/owner" in role_issues[0].description
    
    def test_has_encryption_config(self):
        """Test encryption configuration detection."""
        # Resource with encryption
        encrypted_resource = Resource(
            type="aws_s3_bucket",
            name="encrypted",
            provider="aws",
            configuration={
                "server_side_encryption_configuration": {"enabled": True}
            },
            line_number=10
        )
        
        # Resource without encryption
        unencrypted_resource = Resource(
            type="aws_s3_bucket",
            name="unencrypted",
            provider="aws",
            configuration={},
            line_number=15
        )
        
        assert self.analyzer._has_encryption_config(encrypted_resource) is True
        assert self.analyzer._has_encryption_config(unencrypted_resource) is False
    
    def test_has_permissive_network_rules(self):
        """Test permissive network rules detection."""
        # AWS security group with permissive rules
        permissive_aws = Resource(
            type="aws_security_group",
            name="permissive",
            provider="aws",
            configuration={
                "ingress": [{
                    "cidr_blocks": ["0.0.0.0/0"],
                    "from_port": 22,
                    "to_port": 22
                }]
            },
            line_number=10
        )
        
        # GCP firewall with restrictive rules
        restrictive_gcp = Resource(
            type="google_compute_firewall",
            name="restrictive",
            provider="google",
            configuration={
                "source_ranges": ["10.0.0.0/8"]
            },
            line_number=15
        )
        
        assert self.analyzer._has_permissive_network_rules(permissive_aws) is True
        assert self.analyzer._has_permissive_network_rules(restrictive_gcp) is False
    
    def test_has_monitoring_config(self):
        """Test monitoring configuration detection."""
        # Resource with monitoring
        monitored_resource = Resource(
            type="aws_instance",
            name="monitored",
            provider="aws",
            configuration={
                "monitoring": True
            },
            line_number=10
        )
        
        # Resource without monitoring
        unmonitored_resource = Resource(
            type="aws_instance",
            name="unmonitored",
            provider="aws",
            configuration={},
            line_number=15
        )
        
        assert self.analyzer._has_monitoring_config(monitored_resource) is True
        assert self.analyzer._has_monitoring_config(unmonitored_resource) is False
    
    def test_analyze_security_with_multicloud_integration(self):
        """Test that analyze_security properly integrates multi-cloud validation."""
        # Create a Terraform file with AWS resources
        tf_file = TerraformFile(
            path="aws/main.tf",
            cloud_provider="aws",
            deployment_type="single",
            fortigate_versions=["7.0"],
            resources=[
                Resource(
                    type="aws_instance",
                    name="test-instance",
                    provider="aws",
                    configuration={
                        "metadata_options": {"http_tokens": "optional"}
                    },
                    line_number=10
                )
            ]
        )
        
        # Mock external tools to avoid actual execution
        with patch.object(self.analyzer, '_run_external_tools', return_value=[]):
            report = self.analyzer.analyze_security([tf_file])
        
        # Should include multi-cloud specific issues
        imdsv2_issues = [i for i in report.issues if i.rule_id == "ec2_imdsv2_not_enforced"]
        assert len(imdsv2_issues) == 1
        
        # Should have proper file path set
        assert imdsv2_issues[0].file_path == "aws/main.tf"
    
    def test_unsupported_cloud_provider(self):
        """Test handling of unsupported cloud providers."""
        resource = Resource(
            type="unknown_resource",
            name="test",
            provider="unknown",
            configuration={},
            line_number=10
        )
        
        # Should not raise an exception and return empty list
        issues = self.analyzer.validate_multicloud_security([resource], "unknown_provider")
        assert issues == []
    
    def test_error_handling_in_multicloud_validation(self):
        """Test error handling in multi-cloud validation."""
        # Create a resource that might cause issues during validation
        resource = Resource(
            type="aws_instance",
            name="test",
            provider="aws",
            configuration=None,  # This might cause issues
            line_number=10
        )
        
        # Should handle errors gracefully
        issues = self.analyzer.validate_multicloud_security([resource], "aws")
        # Should not raise an exception, might return empty list or handle gracefully
        assert isinstance(issues, list)