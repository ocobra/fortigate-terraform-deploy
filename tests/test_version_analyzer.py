"""
Unit tests for the VersionAnalyzer class.

Tests version detection, compatibility analysis, upgrade path analysis,
and version-specific feature validation.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, mock_open

from fortigate_analysis.analyzer.version_analyzer import VersionAnalyzer
from fortigate_analysis.models import (
    TerraformFile,
    TerraformAST,
    Variable,
    Resource,
    VersionAnalysisReport,
    VersionCompatibilityIssue,
    VersionUpgradePath,
    Severity,
)


class TestVersionAnalyzer:
    """Test cases for VersionAnalyzer class."""
    
    @pytest.fixture
    def analyzer(self):
        """Create a VersionAnalyzer instance for testing."""
        return VersionAnalyzer()
    
    @pytest.fixture
    def sample_terraform_file(self):
        """Create a sample TerraformFile for testing."""
        ast = TerraformAST(
            variables=[
                Variable(name="fortigate_version", type="string", default="7.2")
            ],
            resources=[
                Resource(
                    type="fortios_system_global",
                    name="test",
                    provider="fortios",
                    configuration={"hostname": "test-fw"},
                    line_number=10
                )
            ]
        )
        
        return TerraformFile(
            path="test/main.tf",
            cloud_provider="aws",
            deployment_type="single",
            fortigate_versions=["7.2"],
            ast=ast,
            variables=[Variable(name="fortigate_version", type="string", default="7.2")],
            resources=[Resource(
                type="fortios_system_global",
                name="test",
                provider="fortios",
                configuration={"hostname": "test-fw"},
                line_number=10
            )]
        )
    
    def test_init_default_config(self, analyzer):
        """Test VersionAnalyzer initialization with default config."""
        assert analyzer.custom_patterns == []
        assert analyzer.strict_mode is False
        assert analyzer.SUPPORTED_VERSIONS == ["6.2", "6.4", "7.0", "7.2", "7.4", "7.6"]
    
    def test_init_custom_config(self):
        """Test VersionAnalyzer initialization with custom config."""
        config = {
            "custom_version_patterns": [r"custom_pattern_(\d+\.\d+)"],
            "strict_mode": True
        }
        analyzer = VersionAnalyzer(config)
        assert analyzer.custom_patterns == [r"custom_pattern_(\d+\.\d+)"]
        assert analyzer.strict_mode is True
    
    def test_normalize_version(self, analyzer):
        """Test version normalization."""
        assert analyzer._normalize_version("7.2.1") == "7.2"
        assert analyzer._normalize_version("6.4") == "6.4"
        assert analyzer._normalize_version("7.0.0") == "7.0"
        assert analyzer._normalize_version("invalid") is None
        assert analyzer._normalize_version("") is None
        assert analyzer._normalize_version(None) is None
    
    def test_is_supported_version(self, analyzer):
        """Test supported version checking."""
        assert analyzer._is_supported_version("7.2") is True
        assert analyzer._is_supported_version("6.4") is True
        assert analyzer._is_supported_version("5.6") is False
        assert analyzer._is_supported_version("8.0") is False
    
    def test_get_version_index(self, analyzer):
        """Test version index retrieval."""
        assert analyzer._get_version_index("6.2") == 0
        assert analyzer._get_version_index("7.2") == 3
        assert analyzer._get_version_index("7.6") == 5
        assert analyzer._get_version_index("invalid") is None
    
    def test_extract_versions_from_content(self, analyzer):
        """Test version extraction from file content."""
        content = """
        variable "fortigate_version" {
          default = "7.2"
        }
        
        # FortiGate version 6.4 configuration
        resource "fortios_system_global" "test" {
          hostname = "test-fw"
        }
        
        # Firmware version: 7.0.1
        """
        
        versions = analyzer._extract_versions_from_content(content)
        assert "7.2" in versions
        assert "6.4" in versions
        assert "7.0" in versions
    
    def test_extract_versions_from_ast(self, analyzer, sample_terraform_file):
        """Test version extraction from Terraform AST."""
        versions = analyzer._extract_versions_from_ast(sample_terraform_file)
        assert "7.2" in versions
    
    def test_infer_version_from_resource(self, analyzer):
        """Test version inference from resource types."""
        # ZTNA resource (7.0+)
        ztna_resource = Resource(
            type="fortios_system_ztna",
            name="test",
            provider="fortios",
            configuration={},
            line_number=1
        )
        versions = analyzer._infer_version_from_resource(ztna_resource)
        assert "7.0" in versions
        assert "7.2" in versions
        
        # SASE resource (7.4+)
        sase_resource = Resource(
            type="fortios_system_sase",
            name="test",
            provider="fortios",
            configuration={},
            line_number=1
        )
        versions = analyzer._infer_version_from_resource(sase_resource)
        assert "7.4" in versions
        assert "7.6" in versions
    
    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.read_text")
    def test_detect_versions(self, mock_read_text, mock_exists, analyzer, sample_terraform_file):
        """Test version detection from Terraform files."""
        mock_exists.return_value = True
        mock_read_text.return_value = 'variable "version" { default = "7.0" }'
        
        detected_versions = analyzer.detect_versions([sample_terraform_file])
        
        assert "test/main.tf" in detected_versions
        versions = detected_versions["test/main.tf"]
        assert "7.2" in versions  # From file metadata
        assert "7.0" in versions  # From file content
    
    def test_check_version_conflicts_no_conflicts(self, analyzer):
        """Test version conflict detection with compatible versions."""
        detected_versions = {
            "file1.tf": ["7.0"],
            "file2.tf": ["7.2"]
        }
        
        conflicts = analyzer.check_version_conflicts(detected_versions)
        assert len(conflicts) == 0
    
    def test_check_version_conflicts_with_conflicts(self, analyzer):
        """Test version conflict detection with incompatible versions."""
        detected_versions = {
            "file1.tf": ["6.2"],
            "file2.tf": ["7.6"]
        }
        
        conflicts = analyzer.check_version_conflicts(detected_versions)
        assert len(conflicts) > 0
        assert "Incompatible versions detected" in conflicts[0]
    
    def test_check_version_conflicts_mixed_major(self, analyzer):
        """Test version conflict detection with mixed major versions."""
        detected_versions = {
            "file1.tf": ["6.4"],
            "file2.tf": ["7.2"]
        }
        
        conflicts = analyzer.check_version_conflicts(detected_versions)
        assert any("Mixed major versions detected" in conflict for conflict in conflicts)
    
    def test_get_version_compatibility(self, analyzer):
        """Test version compatibility checking."""
        assert analyzer._get_version_compatibility("7.0", "7.2") == "COMPATIBLE"
        assert analyzer._get_version_compatibility("6.4", "7.0") == "COMPATIBLE"
        assert analyzer._get_version_compatibility("6.2", "7.0") == "PARTIAL"
        assert analyzer._get_version_compatibility("6.2", "7.6") == "INCOMPATIBLE"
    
    def test_analyze_upgrade_paths(self, analyzer):
        """Test upgrade path analysis."""
        upgrade_path = analyzer.analyze_upgrade_paths("7.0", "7.2")
        
        assert upgrade_path.from_version == "7.0"
        assert upgrade_path.to_version == "7.2"
        assert upgrade_path.compatibility == "COMPATIBLE"
        assert len(upgrade_path.recommendations) > 0
    
    def test_analyze_upgrade_paths_incompatible(self, analyzer):
        """Test upgrade path analysis for incompatible versions."""
        upgrade_path = analyzer.analyze_upgrade_paths("6.2", "7.6")
        
        assert upgrade_path.from_version == "6.2"
        assert upgrade_path.to_version == "7.6"
        assert upgrade_path.compatibility == "INCOMPATIBLE"
        assert any("not recommended" in rec for rec in upgrade_path.recommendations)
    
    def test_validate_version_features_compatible(self, analyzer, sample_terraform_file):
        """Test version feature validation for compatible version."""
        issues = analyzer.validate_version_features([sample_terraform_file], "7.2")
        
        # Should have no issues since the file is compatible with 7.2
        assert len(issues) == 0
    
    def test_validate_version_features_incompatible(self, analyzer):
        """Test version feature validation for incompatible version."""
        # Create a file with ZTNA resource (requires 7.0+)
        ast = TerraformAST(
            resources=[
                Resource(
                    type="fortios_system_ztna",
                    name="test",
                    provider="fortios",
                    configuration={},
                    line_number=15
                )
            ]
        )
        
        tf_file = TerraformFile(
            path="test/ztna.tf",
            cloud_provider="aws",
            deployment_type="single",
            fortigate_versions=["7.0"],
            ast=ast,
            resources=[Resource(
                type="fortios_system_ztna",
                name="test",
                provider="fortios",
                configuration={},
                line_number=15
            )]
        )
        
        # Validate against 6.4 (should fail)
        issues = analyzer.validate_version_features([tf_file], "6.4")
        
        assert len(issues) > 0
        assert issues[0].severity == Severity.HIGH
        assert "requires FortiGate 7.0 or later" in issues[0].description
    
    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.read_text")
    def test_analyze_full_workflow(self, mock_read_text, mock_exists, analyzer, sample_terraform_file):
        """Test complete analysis workflow."""
        mock_exists.return_value = True
        mock_read_text.return_value = 'variable "version" { default = "7.0" }'
        
        report = analyzer.analyze([sample_terraform_file])
        
        assert isinstance(report, VersionAnalysisReport)
        assert len(report.detected_versions) > 0
        assert isinstance(report.compatibility_issues, list)
        assert isinstance(report.upgrade_paths, list)
        assert isinstance(report.recommendations, list)
    
    def test_analyze_error_handling(self, analyzer):
        """Test error handling in analysis."""
        # Create a file with invalid path
        invalid_file = TerraformFile(
            path="nonexistent/file.tf",
            cloud_provider="aws",
            deployment_type="single",
            fortigate_versions=[],
            ast=None
        )
        
        # Should not raise exception, should return empty report
        report = analyzer.analyze([invalid_file])
        assert isinstance(report, VersionAnalysisReport)
    
    def test_version_features_data_structure(self, analyzer):
        """Test that version features are properly structured."""
        # Check that all supported versions have features defined
        for version in analyzer.SUPPORTED_VERSIONS:
            features = analyzer.VERSION_FEATURES.get(version, [])
            assert isinstance(features, list)
            
            for feature in features:
                assert hasattr(feature, 'name')
                assert hasattr(feature, 'introduced_version')
                assert hasattr(feature, 'description')
    
    def test_compatibility_matrix_completeness(self, analyzer):
        """Test that compatibility matrix covers all version pairs."""
        versions = analyzer.SUPPORTED_VERSIONS
        
        # Check that we have compatibility info for consecutive versions
        for i in range(len(versions) - 1):
            v1, v2 = versions[i], versions[i + 1]
            compatibility = analyzer._get_version_compatibility(v1, v2)
            assert compatibility in ["COMPATIBLE", "PARTIAL", "INCOMPATIBLE"]
    
    def test_custom_version_patterns(self):
        """Test custom version patterns configuration."""
        custom_patterns = [r"custom_version_(\d+\.\d+)"]
        config = {"custom_version_patterns": custom_patterns}
        analyzer = VersionAnalyzer(config)
        
        content = "custom_version_7.4 configuration"
        versions = analyzer._extract_versions_from_content(content)
        assert "7.4" in versions
    
    def test_generate_recommendations_multiple_versions(self, analyzer):
        """Test recommendation generation for multiple versions."""
        detected_versions = {
            "file1.tf": ["6.4", "7.0"],
            "file2.tf": ["7.2", "7.4"]
        }
        
        recommendations = analyzer._generate_recommendations(detected_versions, [], [])
        
        # Should recommend standardization
        assert any("standardizing" in rec for rec in recommendations)
    
    def test_generate_recommendations_old_version(self, analyzer):
        """Test recommendation generation for old versions."""
        detected_versions = {
            "file1.tf": ["6.2"]
        }
        
        recommendations = analyzer._generate_recommendations(detected_versions, [], [])
        
        # Should recommend upgrading from old version
        assert any("upgrading from older version" in rec for rec in recommendations)


class TestVersionAnalyzerIntegration:
    """Integration tests for VersionAnalyzer with real-world scenarios."""
    
    @pytest.fixture
    def analyzer(self):
        """Create a VersionAnalyzer instance for integration testing."""
        return VersionAnalyzer()
    
    def test_multi_cloud_version_analysis(self, analyzer):
        """Test version analysis across multiple cloud providers."""
        # Create files for different cloud providers with different versions
        aws_file = TerraformFile(
            path="aws/main.tf",
            cloud_provider="aws",
            deployment_type="ha",
            fortigate_versions=["7.2"],
            ast=TerraformAST()
        )
        
        azure_file = TerraformFile(
            path="azure/main.tf",
            cloud_provider="azure",
            deployment_type="single",
            fortigate_versions=["7.0"],
            ast=TerraformAST()
        )
        
        gcp_file = TerraformFile(
            path="gcp/main.tf",
            cloud_provider="gcp",
            deployment_type="load_balancer",
            fortigate_versions=["7.4"],
            ast=TerraformAST()
        )
        
        files = [aws_file, azure_file, gcp_file]
        
        with patch("pathlib.Path.exists", return_value=False):
            report = analyzer.analyze(files)
        
        assert len(report.detected_versions) == 3
        assert "aws/main.tf" in report.detected_versions
        assert "azure/main.tf" in report.detected_versions
        assert "gcp/main.tf" in report.detected_versions
        
        # Should have upgrade paths between versions
        assert len(report.upgrade_paths) > 0
    
    def test_version_conflict_resolution(self, analyzer):
        """Test version conflict detection and resolution recommendations."""
        # Create files with conflicting versions
        old_file = TerraformFile(
            path="legacy/main.tf",
            cloud_provider="aws",
            deployment_type="single",
            fortigate_versions=["6.2"],
            ast=TerraformAST()
        )
        
        new_file = TerraformFile(
            path="modern/main.tf",
            cloud_provider="aws",
            deployment_type="single",
            fortigate_versions=["7.6"],
            ast=TerraformAST()
        )
        
        files = [old_file, new_file]
        
        with patch("pathlib.Path.exists", return_value=False):
            report = analyzer.analyze(files)
        
        # Should detect version conflicts
        assert len(report.version_conflicts) > 0
        assert "Incompatible versions detected" in report.version_conflicts[0]
        
        # Should provide recommendations
        assert len(report.recommendations) > 0
    
    def test_feature_compatibility_across_versions(self, analyzer):
        """Test feature compatibility validation across different versions."""
        # Create file with version-specific features
        ast = TerraformAST(
            resources=[
                Resource(
                    type="fortios_system_ztna",
                    name="ztna_config",
                    provider="fortios",
                    configuration={"status": "enable"},
                    line_number=10
                ),
                Resource(
                    type="fortios_system_sase",
                    name="sase_config",
                    provider="fortios",
                    configuration={"status": "enable"},
                    line_number=20
                )
            ]
        )
        
        modern_file = TerraformFile(
            path="modern/features.tf",
            cloud_provider="aws",
            deployment_type="single",
            fortigate_versions=["7.6"],
            ast=ast,
            resources=[
                Resource(
                    type="fortios_system_ztna",
                    name="ztna_config",
                    provider="fortios",
                    configuration={"status": "enable"},
                    line_number=10
                ),
                Resource(
                    type="fortios_system_sase",
                    name="sase_config",
                    provider="fortios",
                    configuration={"status": "enable"},
                    line_number=20
                )
            ]
        )
        
        # Test compatibility with older version
        issues = analyzer.validate_version_features([modern_file], "6.4")
        
        # Should find compatibility issues
        assert len(issues) > 0
        ztna_issues = [i for i in issues if "ztna" in i.description.lower()]
        sase_issues = [i for i in issues if "sase" in i.description.lower()]
        
        assert len(ztna_issues) > 0
        assert len(sase_issues) > 0