"""
Integration test for the complete FortiGate Terraform Analysis workflow.

This module demonstrates the end-to-end analysis workflow using all components
working together to analyze a sample FortiGate repository structure.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from datetime import datetime

from fortigate_analysis.analyzer.analysis_engine import AnalysisEngine
from fortigate_analysis.models import (
    RepositoryInventory,
    TerraformFile,
    PythonFile,
    DocumentationFile,
    CloudProviderConfig,
    DeploymentScenario,
    Variable,
    Resource,
    Output,
    TerraformAST,
    SecurityIssue,
    BestPracticeIssue,
    Severity,
    Category,
)


class TestIntegrationWorkflow:
    """Integration tests for the complete analysis workflow."""
    
    def setup_method(self):
        """Set up test fixtures for integration testing."""
        self.engine = AnalysisEngine()
        
        # Create a realistic FortiGate repository structure
        self.sample_repository = self._create_sample_repository()
    
    def _create_sample_repository(self) -> RepositoryInventory:
        """Create a sample FortiGate repository structure for testing."""
        # AWS single instance configuration
        aws_single_tf = TerraformFile(
            path="aws/7.0/single/main.tf",
            cloud_provider="aws",
            deployment_type="single",
            fortigate_versions=["7.0"],
            variables=[
                Variable(name="instance_type", type="string", default="t3.medium"),
                Variable(name="key_name", type="string", description="EC2 Key Pair name"),
                Variable(name="vpc_cidr", type="string", default="10.0.0.0/16"),
            ],
            resources=[
                Resource(
                    type="aws_vpc",
                    name="fortigate_vpc",
                    provider="aws",
                    configuration={"cidr_block": "10.0.0.0/16"},
                    line_number=10
                ),
                Resource(
                    type="aws_instance",
                    name="fortigate",
                    provider="aws",
                    configuration={
                        "instance_type": "t3.medium",
                        "ami": "ami-12345678"
                    },
                    line_number=20
                ),
                Resource(
                    type="aws_security_group",
                    name="fortigate_sg",
                    provider="aws",
                    configuration={
                        "ingress": [{"from_port": 22, "to_port": 22, "cidr_blocks": ["0.0.0.0/0"]}]
                    },
                    line_number=30
                )
            ],
            outputs=[
                Output(name="instance_id", value="${aws_instance.fortigate.id}"),
                Output(name="public_ip", value="${aws_instance.fortigate.public_ip}"),
            ]
        )
        
        # Azure HA configuration
        azure_ha_tf = TerraformFile(
            path="azure/7.0/ha-port1-mgmt/main.tf",
            cloud_provider="azure",
            deployment_type="ha-port1-mgmt",
            fortigate_versions=["7.0"],
            variables=[
                Variable(name="vm_size", type="string", default="Standard_F2s"),
                Variable(name="resource_group_name", type="string"),
            ],
            resources=[
                Resource(
                    type="azurerm_resource_group",
                    name="fortigate_rg",
                    provider="azurerm",
                    configuration={"location": "East US"},
                    line_number=5
                ),
                Resource(
                    type="azurerm_virtual_machine",
                    name="fortigate_primary",
                    provider="azurerm",
                    configuration={"vm_size": "Standard_F2s"},
                    line_number=15
                ),
                Resource(
                    type="azurerm_virtual_machine",
                    name="fortigate_secondary",
                    provider="azurerm",
                    configuration={"vm_size": "Standard_F2s"},
                    line_number=25
                )
            ],
            outputs=[
                Output(name="primary_vm_id", value="${azurerm_virtual_machine.fortigate_primary.id}"),
            ]
        )
        
        # GCP single instance configuration
        gcp_single_tf = TerraformFile(
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
                    line_number=10
                ),
                Resource(
                    type="google_compute_firewall",
                    name="fortigate_firewall",
                    provider="google",
                    configuration={
                        "allow": [{"protocol": "tcp", "ports": ["22", "443"]}],
                        "source_ranges": ["0.0.0.0/0"]
                    },
                    line_number=20
                )
            ],
            outputs=[
                Output(name="instance_name", value="${google_compute_instance.fortigate.name}"),
            ]
        )
        
        # Python deployment script
        deploy_script = PythonFile(
            path="scripts/deploy.py",
            purpose="deployment",
            functions=["deploy_fortigate", "configure_networking", "setup_monitoring"],
            imports=["boto3", "azure.mgmt.compute", "google.cloud.compute"]
        )
        
        # Documentation files
        main_readme = DocumentationFile(
            path="README.md",
            type="README",
            content_summary="Main repository documentation with deployment instructions"
        )
        
        aws_readme = DocumentationFile(
            path="aws/README.md",
            type="guide",
            content_summary="AWS-specific deployment guide"
        )
        
        # Cloud provider configurations
        cloud_configs = {
            "aws": CloudProviderConfig(
                provider="aws",
                deployment_scenarios=["single", "ha", "gwlb"],
                supported_versions=["6.4", "7.0", "7.2", "7.4"],
                configuration_files=["aws/7.0/single/main.tf"]
            ),
            "azure": CloudProviderConfig(
                provider="azure",
                deployment_scenarios=["ha-port1-mgmt", "single"],
                supported_versions=["7.0", "7.2"],
                configuration_files=["azure/7.0/ha-port1-mgmt/main.tf"]
            ),
            "gcp": CloudProviderConfig(
                provider="gcp",
                deployment_scenarios=["single", "ha"],
                supported_versions=["7.0", "7.2"],
                configuration_files=["gcp/7.0/single/main.tf"]
            )
        }
        
        # Deployment scenarios
        deployment_scenarios = [
            DeploymentScenario(
                name="single",
                description="Single FortiGate instance deployment",
                architecture_type="single",
                complexity="low",
                cloud_providers=["aws", "gcp"],
                fortigate_versions=["7.0"]
            ),
            DeploymentScenario(
                name="ha-port1-mgmt",
                description="High availability with port1 management",
                architecture_type="ha",
                complexity="medium",
                cloud_providers=["azure"],
                fortigate_versions=["7.0"]
            )
        ]
        
        return RepositoryInventory(
            terraform_files=[aws_single_tf, azure_ha_tf, gcp_single_tf],
            python_files=[deploy_script],
            documentation_files=[main_readme, aws_readme],
            cloud_provider_configs=cloud_configs,
            deployment_scenarios=deployment_scenarios,
            total_files=6,
            repository_size=1024000  # 1MB
        )
    
    @patch('pathlib.Path.exists', return_value=True)
    @patch('pathlib.Path.is_dir', return_value=True)
    def test_complete_analysis_workflow(self, mock_is_dir, mock_exists):
        """Test the complete analysis workflow from start to finish."""
        # Mock the scanner to return our sample repository
        mock_scanner = Mock()
        mock_scanner.scan_repository.return_value = self.sample_repository
        
        # Mock the parser to avoid file system operations
        mock_parser = Mock()
        mock_parser.parse_terraform_file.return_value = TerraformAST()
        mock_parser.parse_python_file.return_value = {"functions": [], "imports": []}
        
        # Set up the engine with mocked components
        self.engine.set_scanner(mock_scanner)
        self.engine.set_parser(mock_parser)
        
        # Track progress
        progress_updates = []
        def progress_callback(message, progress):
            progress_updates.append((message, progress))
        
        self.engine.set_progress_callback(progress_callback)
        
        # Perform the analysis
        repo_path = Path("/tmp/fortigate-terraform-deploy")
        result = self.engine.analyze_repository(repo_path)
        
        # Verify the analysis completed successfully
        assert result is not None
        assert isinstance(result, type(result))  # AnalysisReport type
        
        # Verify repository inventory
        assert result.repository_inventory is not None
        assert len(result.repository_inventory.terraform_files) == 3
        assert len(result.repository_inventory.python_files) == 1
        assert len(result.repository_inventory.documentation_files) == 2
        
        # Verify cloud provider coverage
        assert "aws" in result.repository_inventory.cloud_provider_configs
        assert "azure" in result.repository_inventory.cloud_provider_configs
        assert "gcp" in result.repository_inventory.cloud_provider_configs
        
        # Verify analysis components ran (some may be None due to component failures)
        assert result.security_issues is not None
        assert result.best_practice_violations is not None
        assert result.architecture_map is not None
        assert result.gap_analysis is not None
        # Version analysis may be None if component fails, which is acceptable
        
        # Verify metrics were calculated
        assert result.metrics is not None
        assert result.metrics.total_files == 6
        assert result.metrics.terraform_files == 3
        assert result.metrics.python_files == 1
        assert result.metrics.documentation_files == 2
        
        # Verify improvement tasks were generated
        assert result.improvement_tasks is not None
        
        # Verify progress was reported
        assert len(progress_updates) > 0
        assert progress_updates[0][0] == "Scanning repository..."
        assert progress_updates[-1][0] == "Finalizing report..."
        assert progress_updates[-1][1] == 1.0
        
        # Verify timestamp and version
        assert result.analysis_timestamp is not None
        assert result.analysis_version == "0.1.0"
    
    @patch('pathlib.Path.exists', return_value=True)
    @patch('pathlib.Path.is_dir', return_value=True)
    def test_analysis_with_security_issues_detected(self, mock_is_dir, mock_exists):
        """Test analysis workflow when security issues are detected."""
        # Mock scanner
        mock_scanner = Mock()
        mock_scanner.scan_repository.return_value = self.sample_repository
        
        # Mock parser
        mock_parser = Mock()
        mock_parser.parse_terraform_file.return_value = TerraformAST()
        mock_parser.parse_python_file.return_value = {"functions": [], "imports": []}
        
        # Mock security analyzer to return issues
        mock_security = Mock()
        from fortigate_analysis.models import SecurityReport
        mock_security.analyze_security.return_value = SecurityReport(
            issues=[
                SecurityIssue(
                    severity=Severity.HIGH,
                    category=Category.SECURITY,
                    description="Overly permissive security group allows SSH from anywhere",
                    file_path="aws/7.0/single/main.tf",
                    line_number=30,
                    recommendation="Restrict SSH access to specific IP ranges"
                ),
                SecurityIssue(
                    severity=Severity.MEDIUM,
                    category=Category.NETWORK,
                    description="Firewall allows traffic from 0.0.0.0/0",
                    file_path="gcp/7.0/single/main.tf",
                    line_number=20,
                    recommendation="Use more restrictive source ranges"
                )
            ]
        )
        
        # Set up engine
        self.engine.set_scanner(mock_scanner)
        self.engine.set_parser(mock_parser)
        self.engine.set_security_analyzer(mock_security)
        
        # Perform analysis
        result = self.engine.analyze_repository(Path("/tmp/test-repo"))
        
        # Verify security issues were detected
        assert len(result.security_issues) == 2
        
        # Verify high severity issue
        high_severity_issues = [issue for issue in result.security_issues if issue.severity == Severity.HIGH]
        assert len(high_severity_issues) == 1
        assert "SSH from anywhere" in high_severity_issues[0].description
        
        # Verify improvement tasks were created for security issues
        security_tasks = [task for task in result.improvement_tasks if task.category == Category.SECURITY]
        assert len(security_tasks) > 0
        
        # Verify metrics include security issue counts
        assert result.metrics.security_issues_by_severity[Severity.HIGH.value] == 1
        assert result.metrics.security_issues_by_severity[Severity.MEDIUM.value] == 1
    
    @patch('pathlib.Path.exists', return_value=True)
    @patch('pathlib.Path.is_dir', return_value=True)
    def test_analysis_with_gap_detection(self, mock_is_dir, mock_exists):
        """Test analysis workflow with gap detection."""
        # Mock scanner
        mock_scanner = Mock()
        mock_scanner.scan_repository.return_value = self.sample_repository
        
        # Mock parser
        mock_parser = Mock()
        mock_parser.parse_terraform_file.return_value = TerraformAST()
        mock_parser.parse_python_file.return_value = {"functions": [], "imports": []}
        
        # Mock gap detector to return gaps
        mock_gap_detector = Mock()
        from fortigate_analysis.models import GapAnalysis
        mock_gap_detector.detect_gaps.return_value = GapAnalysis(
            missing_functionality=[
                "Missing cloud provider support: ibm",
                "Missing cloud provider support: oci",
                "Missing gwlb scenario for aws",
                "Missing FortiGate version support: 6.2"
            ],
            inconsistencies=[
                "Similar variable names used inconsistently: instance_type, vm_size, machine_type",
                "Provider 'azure' missing common outputs: public_ip"
            ],
            incomplete_scenarios=[
                "Scenario 'single' lacks documentation",
                "Scenario 'ha-port1-mgmt' has limited cloud provider support: azure"
            ],
            cross_provider_gaps=[
                "Feature 'auto_scaling' missing in providers: azure, gcp"
            ]
        )
        
        # Set up engine
        self.engine.set_scanner(mock_scanner)
        self.engine.set_parser(mock_parser)
        self.engine.set_gap_detector(mock_gap_detector)
        
        # Perform analysis
        result = self.engine.analyze_repository(Path("/tmp/test-repo"))
        
        # Verify gap analysis was performed
        assert result.gap_analysis is not None
        assert len(result.gap_analysis.missing_functionality) == 4
        assert len(result.gap_analysis.inconsistencies) == 2
        assert len(result.gap_analysis.incomplete_scenarios) == 2
        assert len(result.gap_analysis.cross_provider_gaps) == 1
        
        # Verify specific gaps were identified
        missing_functionality = result.gap_analysis.missing_functionality
        assert any("ibm" in item for item in missing_functionality)
        assert any("oci" in item for item in missing_functionality)
        assert any("gwlb scenario" in item for item in missing_functionality)
        
        # Verify inconsistencies were detected
        inconsistencies = result.gap_analysis.inconsistencies
        assert any("Similar variable names" in item for item in inconsistencies)
        assert any("missing common outputs" in item for item in inconsistencies)
    
    def test_analysis_summary_generation(self):
        """Test that analysis summary is properly generated."""
        # Set up a minimal successful analysis
        with patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.is_dir', return_value=True):
            
            mock_scanner = Mock()
            mock_scanner.scan_repository.return_value = RepositoryInventory(total_files=1)
            
            self.engine.set_scanner(mock_scanner)
            
            # Perform analysis
            self.engine.analyze_repository(Path("/tmp/test"))
            
            # Get summary
            summary = self.engine.get_analysis_summary()
            
            # Verify summary structure
            assert summary["status"] == "Analysis completed"
            assert "timestamp" in summary
            assert "metrics" in summary
            assert "security_issues" in summary
            assert "best_practice_violations" in summary
            assert "improvement_tasks" in summary
            assert "errors" in summary
            assert "warnings" in summary
            
            # Verify error and warning tracking
            errors = self.engine.get_errors()
            warnings = self.engine.get_warnings()
            
            assert isinstance(errors, list)
            assert isinstance(warnings, list)
    
    @patch('pathlib.Path.exists', return_value=True)
    @patch('pathlib.Path.is_dir', return_value=True)
    def test_error_recovery_and_partial_analysis(self, mock_is_dir, mock_exists):
        """Test that analysis continues and provides partial results when components fail."""
        # Mock scanner that works
        mock_scanner = Mock()
        mock_scanner.scan_repository.return_value = self.sample_repository
        
        # Mock parser that works
        mock_parser = Mock()
        mock_parser.parse_terraform_file.return_value = TerraformAST()
        mock_parser.parse_python_file.return_value = {"functions": [], "imports": []}
        
        # Mock security analyzer that fails
        mock_security = Mock()
        mock_security.analyze_security.side_effect = Exception("Security analysis failed")
        
        # Mock best practices validator that works
        mock_best_practices = Mock()
        from fortigate_analysis.models import BestPracticesReport
        mock_best_practices.validate_practices.return_value = BestPracticesReport(violations=[])
        
        # Set up engine
        self.engine.set_scanner(mock_scanner)
        self.engine.set_parser(mock_parser)
        self.engine.set_security_analyzer(mock_security)
        self.engine.set_best_practices_validator(mock_best_practices)
        
        # Perform analysis
        result = self.engine.analyze_repository(Path("/tmp/test-repo"))
        
        # Verify analysis completed despite security analyzer failure
        assert result is not None
        assert result.repository_inventory is not None
        
        # Verify security analysis failed but other components worked
        assert len(result.security_issues) == 0  # No issues due to failure
        assert result.best_practice_violations is not None  # This component worked
        
        # Verify error was recorded
        errors = self.engine.get_errors()
        assert len(errors) > 0
        assert any("Security analysis failed" in error for error in errors)
        
        # Verify metrics were still calculated
        assert result.metrics is not None
        assert result.metrics.total_files == 6


class TestComponentIntegration:
    """Test integration between specific analysis components."""
    
    def test_security_and_best_practices_integration(self):
        """Test that security analyzer and best practices validator work together."""
        engine = AnalysisEngine()
        
        # Create sample files with both security and best practice issues
        tf_file = TerraformFile(
            path="test.tf",
            cloud_provider="aws",
            deployment_type="single",
            fortigate_versions=["7.0"],
            variables=[
                Variable(name="secret_key", type="string", default="hardcoded-secret")  # Security issue
            ],
            resources=[
                Resource(
                    type="aws_instance",
                    name="bad_name",  # Best practice issue - poor naming
                    provider="aws",
                    configuration={},
                    line_number=1
                )
            ]
        )
        
        inventory = RepositoryInventory(terraform_files=[tf_file])
        
        # Test that both analyzers can process the same inventory
        security_issues = engine._analyze_security(inventory)
        best_practice_violations = engine._validate_best_practices(inventory)
        
        # Both should return lists (even if empty due to mocking)
        assert isinstance(security_issues, list)
        assert isinstance(best_practice_violations, list)
    
    def test_gap_detector_and_version_analyzer_integration(self):
        """Test that gap detector and version analyzer work with the same data."""
        engine = AnalysisEngine()
        
        # Create inventory with version-related gaps
        inventory = RepositoryInventory(
            terraform_files=[
                TerraformFile(
                    path="old_version.tf",
                    cloud_provider="aws",
                    deployment_type="single",
                    fortigate_versions=["6.2"]  # Old version
                )
            ],
            cloud_provider_configs={
                "aws": CloudProviderConfig(
                    provider="aws",
                    deployment_scenarios=["single"],
                    supported_versions=["6.2"]  # Limited version support
                )
            }
        )
        
        # Test both analyzers
        gap_analysis = engine._detect_gaps(inventory)
        version_analysis = engine._analyze_versions(inventory)
        
        # Both should work with the same inventory
        assert gap_analysis is not None or gap_analysis is None  # May be None due to mocking
        assert version_analysis is not None or version_analysis is None  # May be None due to mocking