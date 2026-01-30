"""
Unit tests for the AnalysisEngine class.

This module contains comprehensive tests for the unified analysis engine,
including component orchestration, error handling, and workflow coordination.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from pathlib import Path
from datetime import datetime

from fortigate_analysis.analyzer.analysis_engine import AnalysisEngine
from fortigate_analysis.models import (
    AnalysisReport,
    RepositoryInventory,
    TerraformFile,
    SecurityIssue,
    BestPracticeIssue,
    ArchitectureMap,
    GapAnalysis,
    VersionAnalysisReport,
    ImprovementTask,
    AnalysisMetrics,
    Severity,
    Category,
    Priority,
    Effort,
    SecurityReport,
    BestPracticesReport,
    Variable,
    Resource,
    Output,
)


class TestAnalysisEngine:
    """Test cases for the AnalysisEngine class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.engine = AnalysisEngine()
        
        # Create mock repository path
        self.repo_path = Path("/tmp/test-repo")
        
        # Create sample data for testing
        self.sample_tf_file = TerraformFile(
            path="aws/single/main.tf",
            cloud_provider="aws",
            deployment_type="single",
            fortigate_versions=["7.0"],
            variables=[Variable(name="instance_type", type="string")],
            resources=[
                Resource(
                    type="aws_instance",
                    name="fortigate",
                    provider="aws",
                    configuration={},
                    line_number=1
                )
            ],
            outputs=[Output(name="instance_id", value="test")]
        )
        
        self.sample_inventory = RepositoryInventory(
            terraform_files=[self.sample_tf_file],
            total_files=1
        )
        
        self.sample_security_issue = SecurityIssue(
            severity=Severity.HIGH,
            category=Category.SECURITY,
            description="Test security issue",
            file_path="test.tf",
            line_number=1,
            recommendation="Fix the issue"
        )
        
        self.sample_best_practice_issue = BestPracticeIssue(
            severity=Severity.MEDIUM,
            category=Category.BEST_PRACTICES,
            description="Test best practice violation",
            file_path="test.tf",
            line_number=1,
            recommendation="Follow best practices",
            rule_name="test_rule"
        )
    
    def test_initialization_default(self):
        """Test AnalysisEngine initialization with default configuration."""
        engine = AnalysisEngine()
        
        assert engine.config == {}
        assert engine.current_analysis is None
        assert engine.analysis_start_time is None
        assert engine.errors == []
        assert engine.warnings == []
    
    def test_initialization_with_config(self):
        """Test AnalysisEngine initialization with custom configuration."""
        config = {
            'scanner': {'exclude_dirs': ['.git']},
            'security': {'enable_external_tools': False}
        }
        
        engine = AnalysisEngine(config)
        
        assert engine.config == config
        assert engine.scanner_config == {'exclude_dirs': ['.git']}
        assert engine.security_config == {'enable_external_tools': False}
    
    def test_validate_input_valid_path(self):
        """Test input validation with valid repository path."""
        with patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.is_dir', return_value=True):
            
            assert self.engine.validate_input(Path("/valid/repo")) is True
    
    def test_validate_input_invalid_path(self):
        """Test input validation with invalid repository path."""
        # Test None path
        assert self.engine.validate_input(None) is False
        
        # Test non-existent path
        with patch('pathlib.Path.exists', return_value=False):
            assert self.engine.validate_input(Path("/invalid/repo")) is False
        
        # Test file instead of directory
        with patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.is_dir', return_value=False):
            
            assert self.engine.validate_input(Path("/file/path")) is False
    
    @patch('fortigate_analysis.analyzer.analysis_engine.RepositoryScanner')
    @patch('fortigate_analysis.analyzer.analysis_engine.CodeParser')
    @patch('fortigate_analysis.analyzer.analysis_engine.SecurityAnalyzer')
    @patch('fortigate_analysis.analyzer.analysis_engine.BestPracticesValidator')
    @patch('fortigate_analysis.analyzer.analysis_engine.ArchitectureMapper')
    @patch('fortigate_analysis.analyzer.analysis_engine.GapDetector')
    @patch('fortigate_analysis.analyzer.analysis_engine.VersionAnalyzer')
    def test_initialize_default_components(
        self, mock_version, mock_gap, mock_arch, mock_best, mock_security, mock_parser, mock_scanner
    ):
        """Test initialization of default components."""
        engine = AnalysisEngine()
        engine._initialize_default_components()
        
        # Verify all components are initialized
        mock_scanner.assert_called_once_with({})
        mock_parser.assert_called_once_with({})
        mock_security.assert_called_once_with({})
        mock_best.assert_called_once_with({})
        mock_arch.assert_called_once_with({})
        mock_gap.assert_called_once_with({})
        mock_version.assert_called_once_with({})
    
    def test_analyze_repository_invalid_path(self):
        """Test analyze_repository with invalid path."""
        with pytest.raises(ValueError, match="Invalid repository path"):
            self.engine.analyze_repository(Path("/nonexistent"))
    
    @patch('pathlib.Path.exists', return_value=True)
    @patch('pathlib.Path.is_dir', return_value=True)
    def test_analyze_repository_success(self, mock_is_dir, mock_exists):
        """Test successful repository analysis."""
        # Mock all components
        mock_scanner = Mock()
        mock_scanner.scan_repository.return_value = self.sample_inventory
        
        mock_parser = Mock()
        mock_parser.parse_terraform_file.return_value = Mock(
            variables=[], resources=[], outputs=[], modules=[]
        )
        mock_parser.parse_python_file.return_value = {
            'functions': [], 'imports': []
        }
        
        mock_security = Mock()
        mock_security.analyze_security.return_value = SecurityReport(
            issues=[self.sample_security_issue]
        )
        
        mock_best_practices = Mock()
        mock_best_practices.validate_practices.return_value = BestPracticesReport(
            violations=[self.sample_best_practice_issue]
        )
        
        mock_architecture = Mock()
        mock_architecture.map_architecture.return_value = ArchitectureMap()
        
        mock_gap = Mock()
        mock_gap.detect_gaps.return_value = GapAnalysis()
        
        mock_version = Mock()
        mock_version.analyze_versions.return_value = VersionAnalysisReport()
        
        # Set components
        self.engine.set_scanner(mock_scanner)
        self.engine.set_parser(mock_parser)
        self.engine.set_security_analyzer(mock_security)
        self.engine.set_best_practices_validator(mock_best_practices)
        self.engine.set_architecture_mapper(mock_architecture)
        self.engine.set_gap_detector(mock_gap)
        self.engine.set_version_analyzer(mock_version)
        
        # Perform analysis
        result = self.engine.analyze_repository(self.repo_path)
        
        # Verify result
        assert isinstance(result, AnalysisReport)
        assert result.repository_inventory is not None
        assert len(result.security_issues) == 1
        assert len(result.best_practice_violations) == 1
        assert result.architecture_map is not None
        assert result.gap_analysis is not None
        assert result.version_analysis is not None
        assert result.metrics is not None
        
        # Verify components were called
        mock_scanner.scan_repository.assert_called_once_with(self.repo_path)
        mock_security.analyze_security.assert_called_once()
        mock_best_practices.validate_practices.assert_called_once()
        mock_architecture.map_architecture.assert_called_once()
        mock_gap.detect_gaps.assert_called_once()
        mock_version.analyze_versions.assert_called_once()
    
    @patch('pathlib.Path.exists', return_value=True)
    @patch('pathlib.Path.is_dir', return_value=True)
    def test_analyze_repository_with_errors(self, mock_is_dir, mock_exists):
        """Test repository analysis with component errors."""
        # Mock scanner that raises an exception
        mock_scanner = Mock()
        mock_scanner.scan_repository.side_effect = Exception("Scanner error")
        
        self.engine.set_scanner(mock_scanner)
        
        # Analysis should not crash but return error report
        result = self.engine.analyze_repository(self.repo_path)
        
        assert isinstance(result, AnalysisReport)
        assert len(self.engine.errors) > 0
        assert "Scanner error" in str(self.engine.errors)
    
    def test_create_basic_tasks(self):
        """Test creation of basic improvement tasks from issues."""
        security_issues = [self.sample_security_issue]
        best_practice_violations = [self.sample_best_practice_issue]
        
        tasks = self.engine._create_basic_tasks(security_issues, best_practice_violations)
        
        assert len(tasks) == 2
        
        # Check security task
        security_task = tasks[0]
        assert security_task.id == "security-1"
        assert security_task.priority == Priority.HIGH
        assert security_task.category == Category.SECURITY
        
        # Check best practice task
        bp_task = tasks[1]
        assert bp_task.id == "best-practice-1"
        assert bp_task.priority == Priority.MEDIUM
        assert bp_task.category == Category.BEST_PRACTICES
    
    def test_severity_to_priority_conversion(self):
        """Test conversion from severity to priority."""
        assert self.engine._severity_to_priority(Severity.CRITICAL) == Priority.HIGH
        assert self.engine._severity_to_priority(Severity.HIGH) == Priority.HIGH
        assert self.engine._severity_to_priority(Severity.MEDIUM) == Priority.MEDIUM
        assert self.engine._severity_to_priority(Severity.LOW) == Priority.LOW
    
    def test_estimate_effort(self):
        """Test effort estimation for issues."""
        # Test security issue
        security_issue = SecurityIssue(
            severity=Severity.HIGH,
            category=Category.SECRETS,
            description="Test",
            file_path="test.tf",
            line_number=1,
            recommendation="Fix"
        )
        
        effort = self.engine._estimate_effort(security_issue)
        assert effort == Effort.SMALL
        
        # Test encryption issue
        encryption_issue = SecurityIssue(
            severity=Severity.HIGH,
            category=Category.ENCRYPTION,
            description="Test",
            file_path="test.tf",
            line_number=1,
            recommendation="Fix"
        )
        
        effort = self.engine._estimate_effort(encryption_issue)
        assert effort == Effort.MEDIUM
    
    def test_calculate_metrics(self):
        """Test calculation of analysis metrics."""
        security_issues = [self.sample_security_issue]
        best_practice_violations = [self.sample_best_practice_issue]
        improvement_tasks = []
        
        metrics = self.engine._calculate_metrics(
            self.sample_inventory, security_issues, best_practice_violations, improvement_tasks
        )
        
        assert isinstance(metrics, AnalysisMetrics)
        assert metrics.total_files == 1
        assert metrics.terraform_files == 1
        assert metrics.security_issues_by_severity[Severity.HIGH.value] == 1
        assert metrics.best_practice_violations == 1
    
    def test_progress_reporting(self):
        """Test progress reporting functionality."""
        progress_calls = []
        
        def progress_callback(message, progress):
            progress_calls.append((message, progress))
        
        self.engine.set_progress_callback(progress_callback)
        self.engine._report_progress("Test message", 0.5)
        
        assert len(progress_calls) == 1
        assert progress_calls[0] == ("Test message", 0.5)
    
    def test_progress_reporting_with_error(self):
        """Test progress reporting with callback error."""
        def failing_callback(message, progress):
            raise Exception("Callback error")
        
        self.engine.set_progress_callback(failing_callback)
        
        # Should not crash
        self.engine._report_progress("Test message", 0.5)
        
        # Should add warning
        assert len(self.engine.warnings) > 0
        assert "Progress reporting failed" in self.engine.warnings[0]
    
    def test_component_setters(self):
        """Test component setter methods."""
        mock_scanner = Mock()
        mock_parser = Mock()
        mock_security = Mock()
        mock_best_practices = Mock()
        mock_architecture = Mock()
        mock_gap = Mock()
        mock_version = Mock()
        mock_task_gen = Mock()
        mock_report_gen = Mock()
        
        self.engine.set_scanner(mock_scanner)
        self.engine.set_parser(mock_parser)
        self.engine.set_security_analyzer(mock_security)
        self.engine.set_best_practices_validator(mock_best_practices)
        self.engine.set_architecture_mapper(mock_architecture)
        self.engine.set_gap_detector(mock_gap)
        self.engine.set_version_analyzer(mock_version)
        self.engine.set_task_generator(mock_task_gen)
        self.engine.set_report_generator(mock_report_gen)
        
        assert self.engine._scanner == mock_scanner
        assert self.engine._parser == mock_parser
        assert self.engine._security_analyzer == mock_security
        assert self.engine._best_practices_validator == mock_best_practices
        assert self.engine._architecture_mapper == mock_architecture
        assert self.engine._gap_detector == mock_gap
        assert self.engine._version_analyzer == mock_version
        assert self.engine._task_generator == mock_task_gen
        assert self.engine._report_generator == mock_report_gen
    
    def test_get_analysis_summary_no_analysis(self):
        """Test getting analysis summary when no analysis has been performed."""
        summary = self.engine.get_analysis_summary()
        
        assert summary["status"] == "No analysis performed"
    
    @patch('pathlib.Path.exists', return_value=True)
    @patch('pathlib.Path.is_dir', return_value=True)
    def test_get_analysis_summary_with_analysis(self, mock_is_dir, mock_exists):
        """Test getting analysis summary after analysis."""
        # Mock minimal components for successful analysis
        mock_scanner = Mock()
        mock_scanner.scan_repository.return_value = self.sample_inventory
        
        self.engine.set_scanner(mock_scanner)
        
        # Perform analysis
        self.engine.analyze_repository(self.repo_path)
        
        # Get summary
        summary = self.engine.get_analysis_summary()
        
        assert summary["status"] == "Analysis completed"
        assert "timestamp" in summary
        assert "metrics" in summary
        assert "security_issues" in summary
        assert "best_practice_violations" in summary
        assert "improvement_tasks" in summary
        assert "errors" in summary
        assert "warnings" in summary
    
    def test_error_and_warning_tracking(self):
        """Test error and warning tracking functionality."""
        # Add some errors and warnings
        self.engine.errors.append("Test error 1")
        self.engine.errors.append("Test error 2")
        self.engine.warnings.append("Test warning 1")
        
        # Get copies
        errors = self.engine.get_errors()
        warnings = self.engine.get_warnings()
        
        assert len(errors) == 2
        assert len(warnings) == 1
        assert "Test error 1" in errors
        assert "Test warning 1" in warnings
        
        # Verify they are copies (modifying shouldn't affect original)
        errors.append("New error")
        assert len(self.engine.get_errors()) == 2
    
    def test_handle_error(self):
        """Test error handling functionality."""
        test_error = ValueError("Test error")
        
        self.engine.handle_error(test_error, "test context")
        
        assert len(self.engine.errors) == 1
        assert "Error during test context: Test error" in self.engine.errors[0]
    
    def test_analyze_alias_method(self):
        """Test that analyze method works as alias for analyze_repository."""
        with patch.object(self.engine, 'analyze_repository') as mock_analyze:
            mock_analyze.return_value = AnalysisReport(repository_inventory=RepositoryInventory())
            
            result = self.engine.analyze(self.repo_path)
            
            mock_analyze.assert_called_once_with(self.repo_path)
            assert isinstance(result, AnalysisReport)


class TestAnalysisEngineIntegration:
    """Integration tests for AnalysisEngine with real components."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.engine = AnalysisEngine()
    
    @patch('pathlib.Path.exists', return_value=True)
    @patch('pathlib.Path.is_dir', return_value=True)
    def test_end_to_end_analysis_with_defaults(self, mock_is_dir, mock_exists):
        """Test end-to-end analysis using default component implementations."""
        # Create a minimal repository structure
        repo_path = Path("/tmp/test-repo")
        
        # Mock the scanner to return a simple inventory
        with patch('fortigate_analysis.scanner.repository_scanner.RepositoryScanner.scan_repository') as mock_scan:
            mock_scan.return_value = RepositoryInventory(
                terraform_files=[
                    TerraformFile(
                        path="test.tf",
                        cloud_provider="aws",
                        deployment_type="single",
                        fortigate_versions=["7.0"]
                    )
                ],
                total_files=1
            )
            
            # Perform analysis
            result = self.engine.analyze_repository(repo_path)
            
            # Verify result structure
            assert isinstance(result, AnalysisReport)
            assert result.repository_inventory is not None
            assert result.metrics is not None
            assert result.analysis_timestamp is not None
            assert result.analysis_version == "0.1.0"
    
    def test_component_error_recovery(self):
        """Test that analysis continues when individual components fail."""
        # Create engine with failing components
        mock_scanner = Mock()
        mock_scanner.scan_repository.return_value = RepositoryInventory()
        
        mock_security = Mock()
        mock_security.analyze_security.side_effect = Exception("Security analysis failed")
        
        mock_best_practices = Mock()
        mock_best_practices.validate_practices.return_value = BestPracticesReport()
        
        self.engine.set_scanner(mock_scanner)
        self.engine.set_security_analyzer(mock_security)
        self.engine.set_best_practices_validator(mock_best_practices)
        
        with patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.is_dir', return_value=True):
            
            # Analysis should complete despite security analyzer failure
            result = self.engine.analyze_repository(Path("/tmp/test"))
            
            assert isinstance(result, AnalysisReport)
            assert len(result.security_issues) == 0  # No issues due to failure
            assert len(self.engine.errors) > 0  # Error was recorded
            assert "Security analysis failed" in str(self.engine.errors)
    
    def test_custom_configuration_propagation(self):
        """Test that custom configuration is properly propagated to components."""
        config = {
            'scanner': {'exclude_dirs': ['.git', 'node_modules']},
            'security': {'enable_external_tools': False},
            'best_practices': {'strict_mode': True}
        }
        
        engine = AnalysisEngine(config)
        
        # Verify configuration is stored correctly
        assert engine.scanner_config == {'exclude_dirs': ['.git', 'node_modules']}
        assert engine.security_config == {'enable_external_tools': False}
        assert engine.best_practices_config == {'strict_mode': True}
        
        # Verify default components get the right config
        with patch('fortigate_analysis.analyzer.analysis_engine.RepositoryScanner') as mock_scanner:
            engine._initialize_default_components()
            mock_scanner.assert_called_once_with({'exclude_dirs': ['.git', 'node_modules']})


class TestAnalysisEngineErrorHandling:
    """Test error handling scenarios for AnalysisEngine."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.engine = AnalysisEngine()
    
    def test_analysis_with_all_components_failing(self):
        """Test analysis when all components fail."""
        # Create failing mocks for all components
        failing_components = {}
        
        for component_name in ['scanner', 'parser', 'security_analyzer', 'best_practices_validator',
                              'architecture_mapper', 'gap_detector', 'version_analyzer']:
            mock_component = Mock()
            
            # Make all methods raise exceptions
            for method in dir(mock_component):
                if not method.startswith('_'):
                    setattr(mock_component, method, Mock(side_effect=Exception(f"{component_name} failed")))
            
            failing_components[component_name] = mock_component
        
        # Set all failing components
        self.engine.set_scanner(failing_components['scanner'])
        self.engine.set_parser(failing_components['parser'])
        self.engine.set_security_analyzer(failing_components['security_analyzer'])
        self.engine.set_best_practices_validator(failing_components['best_practices_validator'])
        self.engine.set_architecture_mapper(failing_components['architecture_mapper'])
        self.engine.set_gap_detector(failing_components['gap_detector'])
        self.engine.set_version_analyzer(failing_components['version_analyzer'])
        
        with patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.is_dir', return_value=True):
            
            # Analysis should still return a report (even if minimal)
            result = self.engine.analyze_repository(Path("/tmp/test"))
            
            assert isinstance(result, AnalysisReport)
            assert len(self.engine.errors) > 0  # Multiple errors recorded
    
    def test_memory_cleanup_on_error(self):
        """Test that memory is properly cleaned up when errors occur."""
        # This test ensures that failed analysis doesn't leave the engine in a bad state
        
        mock_scanner = Mock()
        mock_scanner.scan_repository.side_effect = Exception("Memory error")
        
        self.engine.set_scanner(mock_scanner)
        
        with patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.is_dir', return_value=True):
            
            # First analysis fails
            result1 = self.engine.analyze_repository(Path("/tmp/test1"))
            assert isinstance(result1, AnalysisReport)
            
            # Reset scanner to working state
            mock_scanner.scan_repository.side_effect = None
            mock_scanner.scan_repository.return_value = RepositoryInventory()
            
            # Second analysis should work
            result2 = self.engine.analyze_repository(Path("/tmp/test2"))
            assert isinstance(result2, AnalysisReport)
            
            # Verify state was properly reset
            assert self.engine.analysis_start_time is not None  # Should be set for second analysis