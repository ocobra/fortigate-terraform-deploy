"""
Unit tests for the ArchitectureMapper class.

Tests entry point identification, dependency mapping, deployment categorization,
and data flow analysis functionality.
"""

import pytest
from unittest.mock import Mock, patch
from pathlib import Path

from fortigate_analysis.analyzer.architecture_mapper import ArchitectureMapper
from fortigate_analysis.models import (
    TerraformFile, TerraformAST, Module, Resource, Variable, Output,
    ArchitectureMap, ArchitectureComponent
)


class TestArchitectureMapper:
    """Test cases for ArchitectureMapper class."""
    
    @pytest.fixture
    def mapper(self):
        """Create ArchitectureMapper instance for testing."""
        return ArchitectureMapper()
    
    @pytest.fixture
    def sample_terraform_files(self):
        """Create sample Terraform files for testing."""
        # Main entry point file
        main_file = TerraformFile(
            path="main.tf",
            cloud_provider="aws",
            deployment_type="single",
            fortigate_versions=["7.0"],
            modules=[
                Module(
                    name="vpc",
                    source="./modules/vpc",
                    variables={"cidr_block": "10.0.0.0/16"},
                    dependencies=[]
                ),
                Module(
                    name="fortigate",
                    source="./modules/fortigate",
                    variables={"vpc_id": "${module.vpc.vpc_id}"},
                    dependencies=["module.vpc"]
                )
            ],
            resources=[
                Resource(
                    type="aws_instance",
                    name="fortigate",
                    provider="aws",
                    configuration={"instance_type": "t3.medium"},
                    line_number=10,
                    dependencies=[]
                )
            ]
        )
        main_file.ast = TerraformAST(
            terraform_block={"required_version": ">= 1.0"},
            providers=[{"name": "aws", "config": {"region": "us-west-2"}}]
        )
        main_file._content = """
        terraform {
          required_version = ">= 1.0"
        }
        
        provider "aws" {
          region = "us-west-2"
        }
        
        module "vpc" {
          source = "./modules/vpc"
          cidr_block = "10.0.0.0/16"
        }
        
        module "fortigate" {
          source = "./modules/fortigate"
          vpc_id = module.vpc.vpc_id
        }
        """
        
        # VPC module file
        vpc_file = TerraformFile(
            path="modules/vpc/main.tf",
            cloud_provider="aws",
            deployment_type="single",
            fortigate_versions=[],
            modules=[],
            resources=[
                Resource(
                    type="aws_vpc",
                    name="main",
                    provider="aws",
                    configuration={"cidr_block": "${var.cidr_block}"},
                    line_number=5,
                    dependencies=["var.cidr_block"]
                ),
                Resource(
                    type="aws_subnet",
                    name="public",
                    provider="aws",
                    configuration={"vpc_id": "${aws_vpc.main.id}"},
                    line_number=10,
                    dependencies=["aws_vpc.main"]
                )
            ]
        )
        
        # FortiGate module file
        fortigate_file = TerraformFile(
            path="modules/fortigate/main.tf",
            cloud_provider="aws",
            deployment_type="single",
            fortigate_versions=["7.0"],
            modules=[],
            resources=[
                Resource(
                    type="aws_instance",
                    name="fortigate",
                    provider="aws",
                    configuration={"subnet_id": "${var.subnet_id}"},
                    line_number=5,
                    dependencies=["var.subnet_id"]
                ),
                Resource(
                    type="aws_security_group",
                    name="fortigate",
                    provider="aws",
                    configuration={"vpc_id": "${var.vpc_id}"},
                    line_number=15,
                    dependencies=["var.vpc_id"]
                )
            ]
        )
        
        # HA deployment file
        ha_file = TerraformFile(
            path="deployments/ha/main.tf",
            cloud_provider="aws",
            deployment_type="ha",
            fortigate_versions=["7.2"],
            modules=[
                Module(
                    name="fortigate_primary",
                    source="../../modules/fortigate",
                    variables={"availability_zone": "us-west-2a"},
                    dependencies=[]
                ),
                Module(
                    name="fortigate_secondary",
                    source="../../modules/fortigate",
                    variables={"availability_zone": "us-west-2b"},
                    dependencies=[]
                )
            ],
            resources=[]
        )
        ha_file._content = """
        module "fortigate_primary" {
          source = "../../modules/fortigate"
          availability_zone = "us-west-2a"
          count = 1
        }
        
        module "fortigate_secondary" {
          source = "../../modules/fortigate"
          availability_zone = "us-west-2b"
          count = 1
        }
        """
        
        return [main_file, vpc_file, fortigate_file, ha_file]
    
    def test_map_architecture_basic(self, mapper, sample_terraform_files):
        """Test basic architecture mapping functionality."""
        result = mapper.map_architecture(sample_terraform_files)
        
        assert isinstance(result, ArchitectureMap)
        assert len(result.components) > 0
        assert len(result.entry_points) > 0
        assert isinstance(result.dependency_graph, dict)
        assert len(result.deployment_scenarios) > 0
        assert len(result.cloud_providers) > 0
    
    def test_identify_entry_points_from_files(self, mapper, sample_terraform_files):
        """Test entry point identification from files."""
        entry_points = mapper.identify_entry_points_from_files(sample_terraform_files)
        
        assert isinstance(entry_points, list)
        assert len(entry_points) > 0
        # main.tf should be identified as an entry point
        assert any("main.tf" in ep for ep in entry_points)
    
    def test_identify_entry_points_main_file(self, mapper):
        """Test entry point identification for main.tf files."""
        terraform_files = [
            TerraformFile(
                path="main.tf",
                cloud_provider="aws",
                deployment_type="single",
                fortigate_versions=[],
                modules=[],
                resources=[]
            )
        ]
        terraform_files[0].ast = TerraformAST(terraform_block={"required_version": ">= 1.0"})
        
        entry_points = mapper.identify_entry_points_from_files(terraform_files)
        
        assert "main.tf" in entry_points
    
    def test_identify_entry_points_root_indicators(self, mapper):
        """Test entry point identification based on root indicators."""
        terraform_files = [
            TerraformFile(
                path="infrastructure.tf",
                cloud_provider="aws",
                deployment_type="single",
                fortigate_versions=[],
                modules=[],
                resources=[]
            )
        ]
        terraform_files[0].ast = TerraformAST(
            providers=[{"name": "aws", "config": {"region": "us-west-2"}}]
        )
        
        entry_points = mapper.identify_entry_points_from_files(terraform_files)
        
        assert "infrastructure.tf" in entry_points
    
    def test_map_dependencies_basic(self, mapper):
        """Test basic dependency mapping."""
        modules = [
            {
                "name": "vpc",
                "source": "./modules/vpc",
                "variables": {},
                "dependencies": []
            },
            {
                "name": "fortigate",
                "source": "./modules/fortigate",
                "variables": {"vpc_id": "${module.vpc.vpc_id}"},
                "dependencies": []
            }
        ]
        
        result = mapper.map_dependencies(modules)
        
        assert isinstance(result, dict)
        assert "vpc" in result
        assert "fortigate" in result
        # fortigate should depend on vpc
        assert "vpc" in result["fortigate"]
    
    def test_map_dependencies_cycle_detection(self, mapper):
        """Test cycle detection in dependency mapping."""
        modules = [
            {
                "name": "module_a",
                "source": "./modules/a",
                "variables": {"input": "${module.module_b.output}"},
                "dependencies": []
            },
            {
                "name": "module_b",
                "source": "./modules/b",
                "variables": {"input": "${module.module_a.output}"},
                "dependencies": []
            }
        ]
        
        with patch.object(mapper, '_detect_dependency_cycles') as mock_detect:
            mock_detect.return_value = [["module_a", "module_b", "module_a"]]
            result = mapper.map_dependencies(modules)
            
            assert isinstance(result, dict)
            mock_detect.assert_called_once()
    
    def test_categorize_deployments(self, mapper, sample_terraform_files):
        """Test deployment scenario categorization."""
        scenarios = mapper.categorize_deployments(sample_terraform_files)
        
        assert isinstance(scenarios, list)
        assert len(scenarios) > 0
        # Should include both single and ha scenarios from sample files
        assert any(scenario in ["single", "ha"] for scenario in scenarios)
    
    def test_create_architecture_components(self, mapper, sample_terraform_files):
        """Test architecture component creation."""
        all_modules = []
        all_resources = []
        
        for tf_file in sample_terraform_files:
            all_modules.extend(tf_file.modules)
            all_resources.extend(tf_file.resources)
        
        components = mapper._create_architecture_components(
            sample_terraform_files, all_modules, all_resources
        )
        
        assert isinstance(components, list)
        assert len(components) > 0
        
        # Check that we have both module and resource components
        component_types = [comp.type for comp in components]
        assert "module" in component_types
        assert "resource" in component_types
        
        # Check component structure
        for component in components:
            assert isinstance(component, ArchitectureComponent)
            assert component.name
            assert component.type in ["module", "resource", "data_source"]
            assert component.cloud_provider
    
    def test_build_dependency_graph(self, mapper, sample_terraform_files):
        """Test dependency graph construction."""
        all_modules = []
        all_resources = []
        
        for tf_file in sample_terraform_files:
            all_modules.extend(tf_file.modules)
            all_resources.extend(tf_file.resources)
        
        components = mapper._create_architecture_components(
            sample_terraform_files, all_modules, all_resources
        )
        
        dependency_graph = mapper._build_dependency_graph(components, all_modules, all_resources)
        
        assert isinstance(dependency_graph, dict)
        assert len(dependency_graph) > 0
        
        # Check that dependencies are properly mapped
        for component_name, dependencies in dependency_graph.items():
            assert isinstance(dependencies, list)
            # No self-references
            assert component_name not in dependencies
    
    def test_detect_dependency_cycles(self, mapper):
        """Test dependency cycle detection."""
        # Create a graph with a cycle
        dependency_graph = {
            "a": ["b"],
            "b": ["c"],
            "c": ["a"]  # Creates cycle: a -> b -> c -> a
        }
        
        cycles = mapper._detect_dependency_cycles(dependency_graph)
        
        assert isinstance(cycles, list)
        assert len(cycles) > 0
        # Should detect the cycle
        assert any(len(cycle) >= 3 for cycle in cycles)
    
    def test_detect_dependency_cycles_no_cycle(self, mapper):
        """Test cycle detection with no cycles."""
        dependency_graph = {
            "a": ["b"],
            "b": ["c"],
            "c": []
        }
        
        cycles = mapper._detect_dependency_cycles(dependency_graph)
        
        assert isinstance(cycles, list)
        assert len(cycles) == 0
    
    def test_categorize_deployment_scenarios(self, mapper, sample_terraform_files):
        """Test deployment scenario categorization."""
        scenarios = mapper._categorize_deployment_scenarios(sample_terraform_files)
        
        assert isinstance(scenarios, list)
        assert len(scenarios) > 0
        
        # Should identify scenarios from the sample files
        assert any(scenario in ["single", "ha"] for scenario in scenarios)
    
    def test_identify_common_patterns(self, mapper, sample_terraform_files):
        """Test common pattern identification."""
        all_resources = []
        for tf_file in sample_terraform_files:
            all_resources.extend(tf_file.resources)
        
        patterns = mapper._identify_common_patterns(all_resources, sample_terraform_files)
        
        assert isinstance(patterns, list)
        # Should identify networking and compute patterns from sample resources
        pattern_text = " ".join(patterns).lower()
        assert any(keyword in pattern_text for keyword in ["networking", "compute", "security"])
    
    def test_has_root_indicators(self, mapper):
        """Test root indicator detection."""
        # File with terraform block
        tf_file_with_terraform = TerraformFile(
            path="main.tf",
            cloud_provider="aws",
            deployment_type="single",
            fortigate_versions=[],
            modules=[],
            resources=[]
        )
        tf_file_with_terraform.ast = TerraformAST(terraform_block={"required_version": ">= 1.0"})
        
        assert mapper._has_root_indicators(tf_file_with_terraform)
        
        # File with providers
        tf_file_with_provider = TerraformFile(
            path="providers.tf",
            cloud_provider="aws",
            deployment_type="single",
            fortigate_versions=[],
            modules=[],
            resources=[]
        )
        tf_file_with_provider.ast = TerraformAST(
            providers=[{"name": "aws", "config": {"region": "us-west-2"}}]
        )
        
        assert mapper._has_root_indicators(tf_file_with_provider)
        
        # File without root indicators
        tf_file_no_indicators = TerraformFile(
            path="module.tf",
            cloud_provider="aws",
            deployment_type="single",
            fortigate_versions=[],
            modules=[],
            resources=[]
        )
        tf_file_no_indicators.ast = TerraformAST()
        
        assert not mapper._has_root_indicators(tf_file_no_indicators)
    
    def test_extract_dependencies_from_value(self, mapper):
        """Test dependency extraction from string values."""
        test_value = "${module.vpc.vpc_id} and ${data.aws_ami.ubuntu.id} and ${aws_instance.web.id}"
        
        dependencies = mapper._extract_dependencies_from_value(test_value)
        
        assert isinstance(dependencies, list)
        assert len(dependencies) > 0
        assert "vpc" in dependencies  # from module.vpc
        assert any("aws_ami.ubuntu" in dep for dep in dependencies)  # from data reference
    
    def test_infer_cloud_provider_from_module(self, mapper):
        """Test cloud provider inference from module."""
        aws_module = Module(
            name="aws_vpc_module",
            source="terraform-aws-modules/vpc/aws",
            variables={},
            dependencies=[]
        )
        
        provider = mapper._infer_cloud_provider_from_module(aws_module)
        assert provider == "aws"
        
        azure_module = Module(
            name="azure_network",
            source="./modules/azure-network",
            variables={},
            dependencies=[]
        )
        
        provider = mapper._infer_cloud_provider_from_module(azure_module)
        assert provider == "azure"
        
        unknown_module = Module(
            name="generic_module",
            source="./modules/generic",
            variables={},
            dependencies=[]
        )
        
        provider = mapper._infer_cloud_provider_from_module(unknown_module)
        assert provider == "unknown"
    
    def test_infer_cloud_provider_from_name(self, mapper):
        """Test cloud provider inference from resource name."""
        assert mapper._infer_cloud_provider_from_name("aws_instance") == "aws"
        assert mapper._infer_cloud_provider_from_name("azurerm_virtual_machine") == "azure"
        assert mapper._infer_cloud_provider_from_name("google_compute_instance") == "gcp"
        assert mapper._infer_cloud_provider_from_name("ibm_is_instance") == "ibm"
        assert mapper._infer_cloud_provider_from_name("oci_core_instance") == "oci"
        assert mapper._infer_cloud_provider_from_name("alicloud_instance") == "alicloud"
        assert mapper._infer_cloud_provider_from_name("openstack_compute_instance_v2") == "openstack"
        assert mapper._infer_cloud_provider_from_name("unknown_resource") == "unknown"
    
    def test_analyze_deployment_patterns_in_file(self, mapper):
        """Test deployment pattern analysis in individual files."""
        # HA deployment file
        ha_file = TerraformFile(
            path="deployments/ha-cluster/main.tf",
            cloud_provider="aws",
            deployment_type="ha",
            fortigate_versions=["7.2"],
            modules=[],
            resources=[]
        )
        ha_file._content = "count = 2\navailability_zone = var.az"
        
        patterns = mapper._analyze_deployment_patterns_in_file(ha_file)
        
        assert isinstance(patterns, list)
        assert "high_availability" in patterns
        
        # Load balancer file
        lb_file = TerraformFile(
            path="deployments/load-balancer/main.tf",
            cloud_provider="aws",
            deployment_type="load_balancer",
            fortigate_versions=["7.0"],
            modules=[],
            resources=[]
        )
        lb_file._content = "aws_lb target_group listener"
        
        patterns = mapper._analyze_deployment_patterns_in_file(lb_file)
        
        assert isinstance(patterns, list)
        assert "load_balancer" in patterns
    
    def test_fallback_entry_point_detection(self, mapper):
        """Test fallback entry point detection."""
        terraform_files = [
            TerraformFile(
                path="file1.tf",
                cloud_provider="aws",
                deployment_type="single",
                fortigate_versions=[],
                modules=[],
                resources=[]
            ),
            TerraformFile(
                path="subdir/file2.tf",
                cloud_provider="aws",
                deployment_type="single",
                fortigate_versions=[],
                modules=[],
                resources=[]
            ),
            TerraformFile(
                path="deep/nested/file3.tf",
                cloud_provider="aws",
                deployment_type="single",
                fortigate_versions=[],
                modules=[],
                resources=[]
            )
        ]
        
        entry_points = mapper._fallback_entry_point_detection(terraform_files)
        
        assert isinstance(entry_points, list)
        assert len(entry_points) > 0
        # Should prefer root-level files
        assert "file1.tf" in entry_points
    
    def test_error_handling(self, mapper):
        """Test error handling in architecture mapping."""
        # Test with invalid/empty input
        result = mapper.map_architecture([])
        
        assert isinstance(result, ArchitectureMap)
        assert len(result.components) == 0
        assert len(result.entry_points) == 0
        
        # Test with malformed terraform file
        malformed_file = TerraformFile(
            path="malformed.tf",
            cloud_provider="unknown",
            deployment_type="unknown",
            fortigate_versions=[],
            modules=[],
            resources=[]
        )
        malformed_file.ast = None  # Simulate parsing failure
        
        result = mapper.map_architecture([malformed_file])
        
        assert isinstance(result, ArchitectureMap)
        # Should handle gracefully without crashing
    
    def test_configuration_options(self):
        """Test mapper configuration options."""
        config = {
            'cycle_detection': False,
            'max_dependency_depth': 5
        }
        
        mapper = ArchitectureMapper(config)
        
        assert mapper.cycle_detection_enabled is False
        assert mapper.max_dependency_depth == 5
    
    def test_multi_cloud_pattern_detection(self, mapper):
        """Test multi-cloud pattern detection."""
        terraform_files = [
            TerraformFile(
                path="aws.tf",
                cloud_provider="aws",
                deployment_type="single",
                fortigate_versions=[],
                modules=[],
                resources=[]
            ),
            TerraformFile(
                path="azure.tf",
                cloud_provider="azure",
                deployment_type="single",
                fortigate_versions=[],
                modules=[],
                resources=[]
            )
        ]
        
        patterns = mapper._identify_common_patterns([], terraform_files)
        
        assert isinstance(patterns, list)
        pattern_text = " ".join(patterns).lower()
        assert "multi_cloud" in pattern_text
    
    def test_identify_best_practice_patterns(self, mapper):
        """Test identification of Terraform best practice patterns."""
        terraform_files = [
            TerraformFile(
                path="good_practices.tf",
                cloud_provider="aws",
                deployment_type="single",
                fortigate_versions=[],
                modules=[],
                resources=[]
            )
        ]
        terraform_files[0]._content = """
        variable "instance_type" {
          description = "EC2 instance type"
          type        = string
          default     = "t3.medium"
        }
        
        output "vpc_id" {
          description = "VPC ID"
          value       = aws_vpc.main.id
        }
        
        data "aws_ami" "ubuntu" {
          most_recent = true
          owners      = ["099720109477"]
        }
        
        locals {
          common_tags = {
            Environment = var.environment
            Project     = var.project
          }
        }
        
        module "vpc" {
          source = "./modules/vpc"
          cidr   = var.vpc_cidr
        }
        """
        
        patterns = mapper._identify_best_practice_patterns(terraform_files)
        
        assert isinstance(patterns, list)
        assert len(patterns) > 0
        
        pattern_names = [p.split('(')[0].strip() for p in patterns]
        assert any('variable_usage' in name for name in pattern_names)
        assert any('output_usage' in name for name in pattern_names)
        assert any('data_sources' in name for name in pattern_names)
        assert any('locals' in name for name in pattern_names)
        assert any('module_composition' in name for name in pattern_names)
    
    def test_identify_anti_patterns(self, mapper):
        """Test identification of Terraform anti-patterns."""
        terraform_files = [
            TerraformFile(
                path="bad_practices.tf",
                cloud_provider="aws",
                deployment_type="single",
                fortigate_versions=[],
                modules=[],
                resources=[]
            )
        ]
        terraform_files[0]._content = """
        resource "aws_instance" "web" {
          ami           = "ami-12345678"  # Hardcoded AMI
          instance_type = "t3.medium"
          subnet_id     = "subnet-12345678"  # Hardcoded subnet
          
          vpc_security_group_ids = [aws_security_group.web.id]
        }
        
        resource "aws_security_group" "web" {
          name = "web-sg"
          
          ingress {
            from_port   = 0
            to_port     = 65535
            protocol    = "tcp"
            cidr_blocks = ["0.0.0.0/0"]  # Overly permissive
          }
        }
        
        module "database" {
          source = "terraform-aws-modules/rds/aws"
          # Missing version constraint
        }
        """
        
        patterns = mapper._identify_anti_patterns(terraform_files)
        
        assert isinstance(patterns, list)
        assert len(patterns) > 0
        
        pattern_text = " ".join(patterns).lower()
        assert "hardcoded_values" in pattern_text
        assert "overly_permissive_security" in pattern_text
        assert "missing_versioning" in pattern_text
    
    def test_identify_fortigate_patterns(self, mapper):
        """Test identification of FortiGate-specific patterns."""
        terraform_files = [
            TerraformFile(
                path="fortigate_config.tf",
                cloud_provider="aws",
                deployment_type="ha",
                fortigate_versions=["7.2"],
                modules=[],
                resources=[]
            )
        ]
        terraform_files[0]._content = """
        resource "fortios_system_ha" "cluster" {
          group_name = "fortigate-cluster"
          mode       = "a-p"
          priority   = 200
          
          unicast_peer {
            id   = 1
            peer = "10.0.1.100"
          }
        }
        
        resource "fortios_firewall_policy" "allow_web" {
          policyid = 1
          name     = "allow-web-traffic"
          srcintf  = ["port1"]
          dstintf  = ["port2"]
          srcaddr  = ["all"]
          dstaddr  = ["all"]
          action   = "accept"
          service  = ["HTTP", "HTTPS"]
        }
        
        resource "fortios_system_interface" "port1" {
          name = "port1"
          ip   = "10.0.1.10/24"
          allowaccess = ["ping", "https", "ssh"]
        }
        """
        
        patterns = mapper._identify_fortigate_patterns(terraform_files)
        
        assert isinstance(patterns, list)
        assert len(patterns) > 0
        
        pattern_text = " ".join(patterns).lower()
        assert "ha_configuration" in pattern_text or "security_policies" in pattern_text
    
    def test_identify_reusable_components(self, mapper):
        """Test identification of reusable components across cloud providers."""
        terraform_files = [
            TerraformFile(
                path="aws_main.tf",
                cloud_provider="aws",
                deployment_type="single",
                fortigate_versions=[],
                modules=[
                    Module(
                        name="vpc",
                        source="./modules/vpc",
                        variables={},
                        dependencies=[]
                    ),
                    Module(
                        name="fortigate",
                        source="./modules/fortigate",
                        variables={},
                        dependencies=[]
                    )
                ],
                resources=[]
            ),
            TerraformFile(
                path="azure_main.tf",
                cloud_provider="azure",
                deployment_type="single",
                fortigate_versions=[],
                modules=[
                    Module(
                        name="network",
                        source="./modules/vpc",  # Same module used across providers
                        variables={},
                        dependencies=[]
                    ),
                    Module(
                        name="fortigate",
                        source="./modules/fortigate",  # Reused module
                        variables={},
                        dependencies=[]
                    )
                ],
                resources=[]
            )
        ]
        
        patterns = mapper._identify_reusable_components(terraform_files)
        
        assert isinstance(patterns, list)
        assert len(patterns) > 0
        
        pattern_text = " ".join(patterns).lower()
        assert "reusable" in pattern_text
    
    def test_analyze_configuration_similarity(self, mapper):
        """Test configuration similarity analysis."""
        terraform_files = [
            TerraformFile(
                path="config1.tf",
                cloud_provider="aws",
                deployment_type="single",
                fortigate_versions=[],
                modules=[],
                resources=[
                    Resource(type="aws_vpc", name="main", provider="aws", configuration={}, line_number=1),
                    Resource(type="aws_subnet", name="public", provider="aws", configuration={}, line_number=2),
                    Resource(type="aws_instance", name="web", provider="aws", configuration={}, line_number=3)
                ]
            ),
            TerraformFile(
                path="config2.tf",
                cloud_provider="aws",
                deployment_type="single",
                fortigate_versions=[],
                modules=[],
                resources=[
                    Resource(type="aws_vpc", name="main", provider="aws", configuration={}, line_number=1),
                    Resource(type="aws_subnet", name="public", provider="aws", configuration={}, line_number=2),
                    Resource(type="aws_instance", name="app", provider="aws", configuration={}, line_number=3)
                ]
            )
        ]
        
        patterns = mapper._analyze_configuration_similarity(terraform_files)
        
        assert isinstance(patterns, list)
        # Should identify high similarity between the two configurations
        pattern_text = " ".join(patterns).lower()
        assert "similarity" in pattern_text or "template" in pattern_text
    
    def test_calculate_configuration_similarity(self, mapper):
        """Test configuration similarity calculation."""
        # Similar configurations
        similar_files = [
            TerraformFile(
                path="config1.tf",
                cloud_provider="aws",
                deployment_type="single",
                fortigate_versions=[],
                modules=[],
                resources=[
                    Resource(type="aws_vpc", name="main", provider="aws", configuration={}, line_number=1),
                    Resource(type="aws_subnet", name="public", provider="aws", configuration={}, line_number=2)
                ]
            ),
            TerraformFile(
                path="config2.tf",
                cloud_provider="aws",
                deployment_type="single",
                fortigate_versions=[],
                modules=[],
                resources=[
                    Resource(type="aws_vpc", name="main", provider="aws", configuration={}, line_number=1),
                    Resource(type="aws_subnet", name="private", provider="aws", configuration={}, line_number=2)
                ]
            )
        ]
        
        similarity = mapper._calculate_configuration_similarity(similar_files)
        
        assert isinstance(similarity, float)
        assert 0.0 <= similarity <= 1.0
        assert similarity > 0.5  # Should be fairly similar
        
        # Dissimilar configurations
        dissimilar_files = [
            TerraformFile(
                path="config1.tf",
                cloud_provider="aws",
                deployment_type="single",
                fortigate_versions=[],
                modules=[],
                resources=[
                    Resource(type="aws_vpc", name="main", provider="aws", configuration={}, line_number=1)
                ]
            ),
            TerraformFile(
                path="config2.tf",
                cloud_provider="aws",
                deployment_type="single",
                fortigate_versions=[],
                modules=[],
                resources=[
                    Resource(type="aws_s3_bucket", name="data", provider="aws", configuration={}, line_number=1)
                ]
            )
        ]
        
        similarity = mapper._calculate_configuration_similarity(dissimilar_files)
        
        assert isinstance(similarity, float)
        assert 0.0 <= similarity <= 1.0
        assert similarity < 0.5  # Should be dissimilar
    
    def test_normalize_resource_type(self, mapper):
        """Test resource type normalization."""
        assert mapper._normalize_resource_type("aws_instance") == "compute_instance"
        assert mapper._normalize_resource_type("azurerm_virtual_machine") == "compute_instance"
        assert mapper._normalize_resource_type("google_compute_instance") == "compute_instance"
        
        assert mapper._normalize_resource_type("aws_vpc") == "virtual_network"
        assert mapper._normalize_resource_type("azurerm_virtual_network") == "virtual_network"
        assert mapper._normalize_resource_type("google_compute_network") == "virtual_network"
        
        assert mapper._normalize_resource_type("aws_subnet") == "subnet"
        assert mapper._normalize_resource_type("azurerm_subnet") == "subnet"
        assert mapper._normalize_resource_type("google_compute_subnetwork") == "subnet"
        
        assert mapper._normalize_resource_type("aws_security_group") == "security_group"
        assert mapper._normalize_resource_type("azurerm_network_security_group") == "security_group"
        
        assert mapper._normalize_resource_type("unknown_resource") == "unknown_resource"
    
    def test_identify_cross_provider_resource_patterns(self, mapper):
        """Test cross-provider resource pattern identification."""
        terraform_files = [
            TerraformFile(
                path="aws.tf",
                cloud_provider="aws",
                deployment_type="single",
                fortigate_versions=[],
                modules=[],
                resources=[
                    Resource(type="aws_instance", name="web", provider="aws", configuration={}, line_number=1),
                    Resource(type="aws_vpc", name="main", provider="aws", configuration={}, line_number=2)
                ]
            ),
            TerraformFile(
                path="azure.tf",
                cloud_provider="azure",
                deployment_type="single",
                fortigate_versions=[],
                modules=[],
                resources=[
                    Resource(type="azurerm_virtual_machine", name="web", provider="azure", configuration={}, line_number=1),
                    Resource(type="azurerm_virtual_network", name="main", provider="azure", configuration={}, line_number=2)
                ]
            )
        ]
        
        patterns = mapper._identify_cross_provider_resource_patterns(terraform_files)
        
        assert isinstance(patterns, list)
        assert len(patterns) > 0
        
        pattern_text = " ".join(patterns).lower()
        assert "cross_provider" in pattern_text
        assert "compute_instance" in pattern_text or "virtual_network" in pattern_text
    
    def test_generate_pattern_documentation(self, mapper):
        """Test pattern documentation generation."""
        # Create architecture map with various patterns
        architecture_map = ArchitectureMap(
            components=[],
            entry_points=[],
            dependency_graph={},
            deployment_scenarios=[],
            cloud_providers=["aws", "azure"],
            common_patterns=[
                "best_practice_variable_usage (Proper use of variables, found in 5 files)",
                "anti_pattern_hardcoded_values (Hardcoded IP addresses, severity: MEDIUM, found in 3 files)",
                "fortigate_ha_configuration (FortiGate HA config, found in 2 files)",
                "multi_cloud_reusable_module (./modules/vpc, used across aws, azure)",
                "high_similarity_cluster (single_aws, 4 files, similarity: 0.85)"
            ]
        )
        
        documentation = mapper.generate_pattern_documentation(architecture_map)
        
        assert isinstance(documentation, dict)
        assert 'pattern_summary' in documentation
        assert 'pattern_details' in documentation
        assert 'usage_examples' in documentation
        assert 'improvement_suggestions' in documentation
        
        # Check pattern summary
        summary = documentation['pattern_summary']
        assert 'total_patterns' in summary
        assert summary['total_patterns'] == 5
        assert 'pattern_categories' in summary
        assert 'recommendations' in summary
        
        # Check that categories are properly identified
        categories = summary['pattern_categories']
        assert 'best_practices' in categories
        assert 'anti_patterns' in categories
        assert 'fortigate_specific' in categories
        assert 'reusable_components' in categories
        assert 'similarity_clusters' in categories
        
        # Check pattern details
        details = documentation['pattern_details']
        assert len(details) > 0
        
        for category, category_info in details.items():
            assert 'description' in category_info
            assert 'patterns' in category_info
            assert 'impact' in category_info
            assert 'recommendations' in category_info
    
    def test_parse_pattern_info(self, mapper):
        """Test pattern information parsing."""
        pattern = "anti_pattern_hardcoded_values (Hardcoded IP addresses, severity: HIGH, found in 3 files)"
        
        pattern_info = mapper._parse_pattern_info(pattern)
        
        assert isinstance(pattern_info, dict)
        assert pattern_info['name'] == 'anti_pattern_hardcoded_values'
        assert pattern_info['severity'] == 'HIGH'
        assert pattern_info['count'] == 3
        assert 'description' in pattern_info
        assert 'details' in pattern_info
    
    def test_enhanced_pattern_recognition_integration(self, mapper, sample_terraform_files):
        """Test integration of enhanced pattern recognition with main architecture mapping."""
        # Add content to sample files to trigger pattern detection
        sample_terraform_files[0]._content = """
        variable "instance_type" {
          description = "Instance type"
          type        = string
          default     = "t3.medium"
        }
        
        resource "aws_instance" "web" {
          ami           = "ami-12345678"  # Hardcoded
          instance_type = var.instance_type
          
          tags = {
            Name = "web-server"
          }
        }
        
        output "instance_id" {
          value = aws_instance.web.id
        }
        """
        
        result = mapper.map_architecture(sample_terraform_files)
        
        assert isinstance(result, ArchitectureMap)
        assert len(result.common_patterns) > 0
        assert result.pattern_documentation is not None
        
        # Check that various pattern types are detected
        pattern_text = " ".join(result.common_patterns).lower()
        
        # Should detect some patterns (exact patterns depend on content)
        assert len(result.common_patterns) > 0
        
        # Check pattern documentation structure
        doc = result.pattern_documentation
        assert 'pattern_summary' in doc
        assert 'pattern_details' in doc
        assert doc['pattern_summary']['total_patterns'] > 0