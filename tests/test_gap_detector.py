"""
Unit tests for the GapDetector class.

This module contains comprehensive tests for gap detection functionality,
including missing functionality detection, configuration inconsistency detection,
and completeness analysis.
"""

import pytest
from datetime import datetime
from pathlib import Path

from fortigate_analysis.analyzer.gap_detector import GapDetector
from fortigate_analysis.models import (
    RepositoryInventory,
    TerraformFile,
    CloudProviderConfig,
    DeploymentScenario,
    DocumentationFile,
    GapAnalysis,
    Variable,
    Resource,
    Output,
    TerraformAST,
)


class TestGapDetector:
    """Test cases for the GapDetector class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.gap_detector = GapDetector()
        
        # Create sample Terraform files for testing
        self.aws_single_file = TerraformFile(
            path="aws/7.0/single/main.tf",
            cloud_provider="aws",
            deployment_type="single",
            fortigate_versions=["7.0"],
            variables=[
                Variable(name="instance_type", type="string", default="t3.medium"),
                Variable(name="key_name", type="string"),
            ],
            resources=[
                Resource(
                    type="aws_instance",
                    name="fortigate",
                    provider="aws",
                    configuration={"instance_type": "t3.medium"},
                    line_number=10
                ),
                Resource(
                    type="aws_security_group",
                    name="fortigate_sg",
                    provider="aws",
                    configuration={"name": "fortigate-sg"},
                    line_number=20
                )
            ],
            outputs=[
                Output(name="instance_id", value="${aws_instance.fortigate.id}"),
                Output(name="public_ip", value="${aws_instance.fortigate.public_ip}"),
            ]
        )
        
        self.azure_ha_file = TerraformFile(
            path="azure/7.0/ha-port1-mgmt/main.tf",
            cloud_provider="azure",
            deployment_type="ha-port1-mgmt",
            fortigate_versions=["7.0"],
            variables=[
                Variable(name="vm_size", type="string", default="Standard_F2s"),
                Variable(name="resource_group", type="string"),
            ],
            resources=[
                Resource(
                    type="azurerm_virtual_machine",
                    name="fortigate_primary",
                    provider="azurerm",
                    configuration={"vm_size": "Standard_F2s"},
                    line_number=15
                ),
                Resource(
                    type="azurerm_network_security_group",
                    name="fortigate_nsg",
                    provider="azurerm",
                    configuration={"name": "fortigate-nsg"},
                    line_number=25
                )
            ],
            outputs=[
                Output(name="vm_id", value="${azurerm_virtual_machine.fortigate_primary.id}"),
                Output(name="private_ip", value="${azurerm_virtual_machine.fortigate_primary.private_ip_address}"),
            ]
        )
        
        self.gcp_single_file = TerraformFile(
            path="gcp/7.0/single/main.tf",
            cloud_provider="gcp",
            deployment_type="single",
            fortigate_versions=["7.0"],
            variables=[
                Variable(name="machine_type", type="string", default="n1-standard-2"),
                Variable(name="project_id", type="string"),
            ],
            resources=[
                Resource(
                    type="google_compute_instance",
                    name="fortigate",
                    provider="google",
                    configuration={"machine_type": "n1-standard-2"},
                    line_number=12
                ),
                Resource(
                    type="google_compute_firewall",
                    name="fortigate_firewall",
                    provider="google",
                    configuration={"name": "fortigate-firewall"},
                    line_number=22
                )
            ],
            outputs=[
                Output(name="instance_id", value="${google_compute_instance.fortigate.id}"),
                Output(name="external_ip", value="${google_compute_instance.fortigate.network_interface.0.access_config.0.nat_ip}"),
            ]
        )
    
    def test_detect_gaps_with_complete_inventory(self):
        """Test gap detection with a complete repository inventory."""
        # Create a comprehensive inventory
        inventory = RepositoryInventory(
            terraform_files=[self.aws_single_file, self.azure_ha_file, self.gcp_single_file],
            cloud_provider_configs={
                "aws": CloudProviderConfig(
                    provider="aws",
                    deployment_scenarios=["single", "ha"],
                    supported_versions=["7.0", "7.2"],
                    configuration_files=["aws/7.0/single/main.tf"]
                ),
                "azure": CloudProviderConfig(
                    provider="azure",
                    deployment_scenarios=["ha-port1-mgmt"],
                    supported_versions=["7.0"],
                    configuration_files=["azure/7.0/ha-port1-mgmt/main.tf"]
                ),
                "gcp": CloudProviderConfig(
                    provider="gcp",
                    deployment_scenarios=["single"],
                    supported_versions=["7.0"],
                    configuration_files=["gcp/7.0/single/main.tf"]
                )
            },
            deployment_scenarios=[
                DeploymentScenario(
                    name="single",
                    description="Single instance deployment",
                    architecture_type="single",
                    complexity="low",
                    cloud_providers=["aws", "gcp"],
                    fortigate_versions=["7.0"]
                ),
                DeploymentScenario(
                    name="ha-port1-mgmt",
                    description="HA with port1 management",
                    architecture_type="ha",
                    complexity="medium",
                    cloud_providers=["azure"],
                    fortigate_versions=["7.0"]
                )
            ],
            documentation_files=[
                DocumentationFile(
                    path="README.md",
                    type="README",
                    content_summary="Main repository documentation"
                )
            ]
        )
        
        gap_analysis = self.gap_detector.detect_gaps(inventory)
        
        assert isinstance(gap_analysis, GapAnalysis)
        assert isinstance(gap_analysis.missing_functionality, list)
        assert isinstance(gap_analysis.inconsistencies, list)
        assert isinstance(gap_analysis.incomplete_scenarios, list)
        assert isinstance(gap_analysis.cross_provider_gaps, list)
    
    def test_detect_gaps_with_minimal_inventory(self):
        """Test gap detection with minimal repository inventory."""
        inventory = RepositoryInventory(
            terraform_files=[self.aws_single_file],
            cloud_provider_configs={
                "aws": CloudProviderConfig(
                    provider="aws",
                    deployment_scenarios=["single"],
                    supported_versions=["7.0"]
                )
            },
            deployment_scenarios=[
                DeploymentScenario(
                    name="single",
                    description="Single instance deployment",
                    architecture_type="single",
                    complexity="low",
                    cloud_providers=["aws"],
                    fortigate_versions=["7.0"]
                )
            ]
        )
        
        gap_analysis = self.gap_detector.detect_gaps(inventory)
        
        # Should identify many missing providers and scenarios
        assert len(gap_analysis.missing_functionality) > 0
        assert any("Missing cloud provider support" in item for item in gap_analysis.missing_functionality)
        assert any("Missing" in item and "scenario" in item for item in gap_analysis.missing_functionality)
    
    def test_find_missing_functionality(self):
        """Test identification of missing functionality."""
        # Test with limited scenarios
        limited_scenarios = ["single", "ha"]
        missing = self.gap_detector.find_missing_functionality(limited_scenarios)
        
        assert isinstance(missing, list)
        assert any("Gateway Load Balancer" in item for item in missing)
        assert any("Transit Gateway" in item for item in missing)
        
        # Test with comprehensive scenarios
        comprehensive_scenarios = list(self.gap_detector.expected_scenarios)
        missing_comprehensive = self.gap_detector.find_missing_functionality(comprehensive_scenarios)
        
        # Should have fewer missing items
        assert len(missing_comprehensive) < len(missing)
    
    def test_detect_inconsistencies(self):
        """Test detection of configuration inconsistencies."""
        configs = {
            "aws": [self.aws_single_file],
            "azure": [self.azure_ha_file],
            "gcp": [self.gcp_single_file]
        }
        
        inconsistencies = self.gap_detector.detect_inconsistencies(configs)
        
        assert isinstance(inconsistencies, list)
        # Should detect variable naming inconsistencies or similar variable patterns
        assert any("Similar variable names" in item or ("Variable" in item and "missing" in item) for item in inconsistencies)
    
    def test_analyze_variable_consistency(self):
        """Test analysis of variable naming consistency."""
        provider_files = {
            "aws": [self.aws_single_file],
            "azure": [self.azure_ha_file],
            "gcp": [self.gcp_single_file]
        }
        
        inconsistencies = self.gap_detector._analyze_variable_consistency(provider_files)
        
        assert isinstance(inconsistencies, list)
        # Different providers use different variable names, should detect inconsistencies
        assert len(inconsistencies) > 0
    
    def test_analyze_resource_consistency(self):
        """Test analysis of resource configuration consistency."""
        provider_files = {
            "aws": [self.aws_single_file],
            "azure": [self.azure_ha_file],
            "gcp": [self.gcp_single_file]
        }
        
        inconsistencies = self.gap_detector._analyze_resource_consistency(provider_files)
        
        assert isinstance(inconsistencies, list)
        # All providers should have network, security, compute resources
        # Some inconsistencies might be detected based on naming patterns
    
    def test_analyze_output_consistency(self):
        """Test analysis of output consistency."""
        provider_files = {
            "aws": [self.aws_single_file],
            "azure": [self.azure_ha_file],
            "gcp": [self.gcp_single_file]
        }
        
        inconsistencies = self.gap_detector._analyze_output_consistency(provider_files)
        
        assert isinstance(inconsistencies, list)
        # Should detect missing common outputs like instance_id in some providers
        assert any("missing common outputs" in item for item in inconsistencies)
    
    def test_check_scenario_completeness(self):
        """Test checking completeness of deployment scenarios."""
        scenario = DeploymentScenario(
            name="test-scenario",
            description="Test scenario",
            architecture_type="single",
            complexity="low",
            cloud_providers=["aws"],
            fortigate_versions=["7.0"]  # Limited versions
        )
        
        inventory = RepositoryInventory(
            terraform_files=[self.aws_single_file],
            documentation_files=[]  # No documentation
        )
        
        issues = self.gap_detector._check_scenario_completeness(scenario, inventory)
        
        assert isinstance(issues, list)
        assert any("lacks documentation" in item for item in issues)
        assert any("limited FortiGate versions" in item for item in issues)
        assert any("lacks example configurations" in item for item in issues)
    
    def test_extract_provider_features(self):
        """Test extraction of features from provider configurations."""
        inventory = RepositoryInventory(
            terraform_files=[self.aws_single_file, self.azure_ha_file, self.gcp_single_file]
        )
        
        features = self.gap_detector._extract_provider_features(inventory)
        
        assert isinstance(features, dict)
        assert "aws" in features
        assert "azure" in features
        assert "gcp" in features
        
        # Should detect security groups/networking features
        assert "security_groups" in features["aws"]
        assert "security_groups" in features["azure"]
        assert "security_groups" in features["gcp"]
    
    def test_find_feature_gaps(self):
        """Test identification of feature gaps across providers."""
        provider_features = {
            "aws": {"load_balancing", "security_groups", "auto_scaling"},
            "azure": {"security_groups", "networking"},
            "gcp": {"security_groups", "networking", "monitoring"}
        }
        
        gaps = self.gap_detector._find_feature_gaps(provider_features)
        
        assert isinstance(gaps, list)
        # Should identify missing features in different providers
        assert any("load_balancing" in item and "azure" in item for item in gaps)
        assert any("auto_scaling" in item for item in gaps)
    
    def test_filter_relevant_scenarios(self):
        """Test filtering of scenarios relevant to specific providers."""
        all_scenarios = {"single", "ha", "gwlb", "azurevwan", "ha-dualloadbalancer"}
        
        # Test AWS-specific filtering
        aws_relevant = self.gap_detector._filter_relevant_scenarios("aws", all_scenarios)
        assert "gwlb" in aws_relevant
        assert "azurevwan" not in aws_relevant
        
        # Test Azure-specific filtering
        azure_relevant = self.gap_detector._filter_relevant_scenarios("azure", all_scenarios)
        assert "azurevwan" in azure_relevant
        assert "gwlb" not in azure_relevant
        
        # Test GCP-specific filtering
        gcp_relevant = self.gap_detector._filter_relevant_scenarios("gcp", all_scenarios)
        assert "ha-dualloadbalancer" in gcp_relevant
        
        # Test unknown provider (should return common scenarios)
        unknown_relevant = self.gap_detector._filter_relevant_scenarios("unknown", all_scenarios)
        assert "single" in unknown_relevant
        assert "ha" in unknown_relevant
    
    def test_validate_input(self):
        """Test input validation for gap detection."""
        # Test with valid inventory
        valid_inventory = RepositoryInventory(
            terraform_files=[self.aws_single_file]
        )
        assert self.gap_detector.validate_input(valid_inventory) is True
        
        # Test with empty inventory
        empty_inventory = RepositoryInventory()
        assert self.gap_detector.validate_input(empty_inventory) is False
        
        # Test with None
        assert self.gap_detector.validate_input(None) is False
    
    def test_handle_error(self):
        """Test error handling during gap detection."""
        # This should not raise an exception
        test_error = ValueError("Test error")
        self.gap_detector.handle_error(test_error, "test context")
        
        # Test with invalid input to trigger error handling
        invalid_inventory = None
        
        with pytest.raises(ValueError):
            self.gap_detector.detect_gaps(invalid_inventory)
    
    def test_analyze_complexity_gaps(self):
        """Test analysis of configuration complexity differences."""
        inventory = RepositoryInventory(
            cloud_provider_configs={
                "aws": CloudProviderConfig(
                    provider="aws",
                    deployment_scenarios=["single", "ha", "gwlb", "transitgwy"],
                    supported_versions=["6.4", "7.0", "7.2", "7.4"]
                ),
                "azure": CloudProviderConfig(
                    provider="azure",
                    deployment_scenarios=["single"],
                    supported_versions=["7.0"]
                ),
                "gcp": CloudProviderConfig(
                    provider="gcp",
                    deployment_scenarios=["single", "ha"],
                    supported_versions=["7.0", "7.2"]
                )
            }
        )
        
        gaps = self.gap_detector._analyze_complexity_gaps(inventory)
        
        assert isinstance(gaps, list)
        # Azure should be identified as having lower complexity
        assert any("azure" in item.lower() and "lower configuration complexity" in item for item in gaps)
    
    def test_analyze_version_support_gaps(self):
        """Test analysis of FortiGate version support differences."""
        inventory = RepositoryInventory(
            deployment_scenarios=[
                DeploymentScenario(
                    name="single",
                    description="Single instance",
                    architecture_type="single",
                    complexity="low",
                    cloud_providers=["aws", "azure"],
                    fortigate_versions=["7.0", "7.2"]
                ),
                DeploymentScenario(
                    name="ha",
                    description="High availability",
                    architecture_type="ha",
                    complexity="medium",
                    cloud_providers=["aws"],
                    fortigate_versions=["6.4", "7.0", "7.2"]
                )
            ]
        )
        
        gaps = self.gap_detector._analyze_version_support_gaps(inventory)
        
        assert isinstance(gaps, list)
        # Azure should be missing version 6.4 support
        assert any("azure" in item.lower() and "6.4" in item for item in gaps)


class TestGapDetectorEdgeCases:
    """Test edge cases and error conditions for GapDetector."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.gap_detector = GapDetector()
    
    def test_empty_repository_inventory(self):
        """Test gap detection with completely empty inventory."""
        empty_inventory = RepositoryInventory()
        
        with pytest.raises(ValueError):
            self.gap_detector.detect_gaps(empty_inventory)
    
    def test_inventory_with_no_terraform_files(self):
        """Test gap detection with inventory containing no Terraform files."""
        inventory = RepositoryInventory(
            documentation_files=[
                DocumentationFile(path="README.md", type="README")
            ]
        )
        
        with pytest.raises(ValueError):
            self.gap_detector.detect_gaps(inventory)
    
    def test_single_provider_inventory(self):
        """Test gap detection with only one cloud provider."""
        inventory = RepositoryInventory(
            terraform_files=[
                TerraformFile(
                    path="aws/single/main.tf",
                    cloud_provider="aws",
                    deployment_type="single",
                    fortigate_versions=["7.0"]
                )
            ],
            cloud_provider_configs={
                "aws": CloudProviderConfig(
                    provider="aws",
                    deployment_scenarios=["single"],
                    supported_versions=["7.0"]
                )
            }
        )
        
        gap_analysis = self.gap_detector.detect_gaps(inventory)
        
        # Should identify missing cloud providers
        missing_providers = [item for item in gap_analysis.missing_functionality 
                           if "Missing cloud provider support" in item]
        assert len(missing_providers) > 0
    
    def test_configuration_with_syntax_errors(self):
        """Test gap detection with files containing syntax errors."""
        tf_file_with_errors = TerraformFile(
            path="aws/broken/main.tf",
            cloud_provider="aws",
            deployment_type="single",
            fortigate_versions=["7.0"],
            syntax_errors=["Unexpected token", "Missing closing brace"]
        )
        
        inventory = RepositoryInventory(
            terraform_files=[tf_file_with_errors],
            cloud_provider_configs={
                "aws": CloudProviderConfig(provider="aws")
            }
        )
        
        # Should not crash despite syntax errors
        gap_analysis = self.gap_detector.detect_gaps(inventory)
        assert isinstance(gap_analysis, GapAnalysis)
    
    def test_custom_configuration(self):
        """Test gap detector with custom configuration."""
        custom_config = {
            "expected_providers": ["aws", "azure"],
            "expected_scenarios": ["single", "ha"],
            "min_version_support": 2
        }
        
        custom_detector = GapDetector(config=custom_config)
        
        # Should still work with custom configuration
        assert custom_detector.config == custom_config
        assert hasattr(custom_detector, 'expected_providers')
        assert hasattr(custom_detector, 'expected_scenarios')


class TestGapDetectorIntegration:
    """Integration tests for GapDetector with realistic scenarios."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.gap_detector = GapDetector()
    
    def test_realistic_multi_cloud_repository(self):
        """Test gap detection on a realistic multi-cloud repository structure."""
        # Create a realistic repository inventory
        terraform_files = [
            # AWS configurations
            TerraformFile(
                path="aws/7.0/single/main.tf",
                cloud_provider="aws",
                deployment_type="single",
                fortigate_versions=["7.0"],
                variables=[Variable(name="instance_type", type="string")],
                resources=[
                    Resource(type="aws_instance", name="fortigate", provider="aws", 
                           configuration={}, line_number=1),
                    Resource(type="aws_security_group", name="sg", provider="aws", 
                           configuration={}, line_number=2)
                ],
                outputs=[Output(name="instance_id", value="test")]
            ),
            TerraformFile(
                path="aws/7.0/ha/main.tf",
                cloud_provider="aws",
                deployment_type="ha",
                fortigate_versions=["7.0"],
                variables=[Variable(name="instance_type", type="string")],
                resources=[
                    Resource(type="aws_instance", name="primary", provider="aws", 
                           configuration={}, line_number=1),
                    Resource(type="aws_instance", name="secondary", provider="aws", 
                           configuration={}, line_number=2)
                ],
                outputs=[Output(name="primary_id", value="test")]
            ),
            # Azure configurations
            TerraformFile(
                path="azure/7.0/single/main.tf",
                cloud_provider="azure",
                deployment_type="single",
                fortigate_versions=["7.0"],
                variables=[Variable(name="vm_size", type="string")],
                resources=[
                    Resource(type="azurerm_virtual_machine", name="fortigate", provider="azurerm", 
                           configuration={}, line_number=1)
                ],
                outputs=[Output(name="vm_id", value="test")]
            ),
            # GCP configurations (missing some scenarios)
            TerraformFile(
                path="gcp/7.0/single/main.tf",
                cloud_provider="gcp",
                deployment_type="single",
                fortigate_versions=["7.0"],
                variables=[Variable(name="machine_type", type="string")],
                resources=[
                    Resource(type="google_compute_instance", name="fortigate", provider="google", 
                           configuration={}, line_number=1)
                ],
                outputs=[Output(name="instance_name", value="test")]
            )
        ]
        
        inventory = RepositoryInventory(
            terraform_files=terraform_files,
            cloud_provider_configs={
                "aws": CloudProviderConfig(
                    provider="aws",
                    deployment_scenarios=["single", "ha"],
                    supported_versions=["7.0"]
                ),
                "azure": CloudProviderConfig(
                    provider="azure",
                    deployment_scenarios=["single"],
                    supported_versions=["7.0"]
                ),
                "gcp": CloudProviderConfig(
                    provider="gcp",
                    deployment_scenarios=["single"],
                    supported_versions=["7.0"]
                )
            },
            deployment_scenarios=[
                DeploymentScenario(
                    name="single",
                    description="Single instance",
                    architecture_type="single",
                    complexity="low",
                    cloud_providers=["aws", "azure", "gcp"],
                    fortigate_versions=["7.0"]
                ),
                DeploymentScenario(
                    name="ha",
                    description="High availability",
                    architecture_type="ha",
                    complexity="medium",
                    cloud_providers=["aws"],
                    fortigate_versions=["7.0"]
                )
            ],
            documentation_files=[
                DocumentationFile(path="README.md", type="README"),
                DocumentationFile(path="aws/README.md", type="guide")
            ]
        )
        
        gap_analysis = self.gap_detector.detect_gaps(inventory)
        
        # Verify comprehensive analysis
        assert len(gap_analysis.missing_functionality) > 0
        assert len(gap_analysis.inconsistencies) > 0
        # Cross-provider gaps might be empty if all providers have similar basic features
        # but we should have other types of gaps
        assert (len(gap_analysis.cross_provider_gaps) > 0 or 
                len(gap_analysis.incomplete_scenarios) > 0)
        
        # Should identify missing cloud providers
        assert any("ibm" in item.lower() for item in gap_analysis.missing_functionality)
        assert any("oci" in item.lower() for item in gap_analysis.missing_functionality)
        
        # Should identify missing scenarios for some providers
        assert any("ha" in item and ("azure" in item or "gcp" in item) 
                  for item in gap_analysis.missing_functionality)
        
        # Should identify output inconsistencies or similar variable names
        assert (any("missing common outputs" in item for item in gap_analysis.inconsistencies) or
                any("Similar variable names" in item for item in gap_analysis.inconsistencies))
        
        # Should identify version support gaps
        missing_versions = [item for item in gap_analysis.missing_functionality 
                          if "version support" in item]
        assert len(missing_versions) > 0