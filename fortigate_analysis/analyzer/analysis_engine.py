"""
Unified analysis engine for orchestrating all FortiGate Terraform analysis components.

This module implements the main AnalysisEngine that coordinates all analyzer components,
manages the analysis workflow, handles errors, and aggregates results into comprehensive
analysis reports.
"""

import time
from typing import Optional, Dict, Any, List
from pathlib import Path
from datetime import datetime

from ..models import (
    AnalysisReport,
    RepositoryInventory,
    AnalysisMetrics,
    SecurityIssue,
    BestPracticeIssue,
    ArchitectureMap,
    GapAnalysis,
    VersionAnalysisReport,
    ImprovementTask,
    Severity,
)
from ..interfaces import (
    AnalysisEngineProtocol,
    RepositoryScannerProtocol,
    CodeParserProtocol,
    SecurityAnalyzerProtocol,
    BestPracticesValidatorProtocol,
    ArchitectureMapperProtocol,
    GapDetectorProtocol,
    VersionAnalyzerProtocol,
    TaskGeneratorProtocol,
    ReportGeneratorProtocol,
    BaseAnalyzer,
)

# Import concrete implementations
from ..scanner.repository_scanner import RepositoryScanner
from ..parser.code_parser import CodeParser
from .security_analyzer import SecurityAnalyzer
from .best_practices_validator import BestPracticesValidator
from .architecture_mapper import ArchitectureMapper
from .gap_detector import GapDetector
from .version_analyzer import VersionAnalyzer


class AnalysisEngine(BaseAnalyzer, AnalysisEngineProtocol):
    """
    Unified analysis engine that orchestrates all FortiGate Terraform analysis components.
    
    This class coordinates the entire analysis workflow, from repository scanning through
    report generation, providing comprehensive analysis results with proper error handling
    and progress tracking.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the AnalysisEngine with optional configuration.
        
        Args:
            config: Optional configuration dictionary for customizing analysis behavior
        """
        super().__init__(config)
        
        # Initialize component configurations
        self.scanner_config = self.config.get('scanner', {})
        self.parser_config = self.config.get('parser', {})
        self.security_config = self.config.get('security', {})
        self.best_practices_config = self.config.get('best_practices', {})
        self.architecture_config = self.config.get('architecture', {})
        self.gap_config = self.config.get('gap_detection', {})
        self.version_config = self.config.get('version_analysis', {})
        
        # Initialize components with default implementations
        self._scanner: Optional[RepositoryScannerProtocol] = None
        self._parser: Optional[CodeParserProtocol] = None
        self._security_analyzer: Optional[SecurityAnalyzerProtocol] = None
        self._best_practices_validator: Optional[BestPracticesValidatorProtocol] = None
        self._architecture_mapper: Optional[ArchitectureMapperProtocol] = None
        self._gap_detector: Optional[GapDetectorProtocol] = None
        self._version_analyzer: Optional[VersionAnalyzerProtocol] = None
        self._task_generator: Optional[TaskGeneratorProtocol] = None
        self._report_generator: Optional[ReportGeneratorProtocol] = None
        
        # Analysis state
        self.current_analysis: Optional[AnalysisReport] = None
        self.analysis_start_time: Optional[float] = None
        self.progress_callback: Optional[callable] = None
        
        # Error tracking
        self.errors: List[str] = []
        self.warnings: List[str] = []
    
    def analyze(self, repo_path: Path) -> AnalysisReport:
        """
        Perform analysis operation (required by BaseAnalyzer).
        
        Args:
            repo_path: Path to the repository to analyze
            
        Returns:
            Comprehensive analysis report
        """
        return self.analyze_repository(repo_path)
    
    def analyze_repository(self, repo_path: Path) -> AnalysisReport:
        """
        Perform complete repository analysis using all available components.
        
        Args:
            repo_path: Path to the FortiGate Terraform repository
            
        Returns:
            Comprehensive AnalysisReport containing all findings and recommendations
        """
        if not self.validate_input(repo_path):
            raise ValueError(f"Invalid repository path: {repo_path}")
        
        self.analysis_start_time = time.time()
        self.errors.clear()
        self.warnings.clear()
        
        try:
            # Initialize default components if not set
            self._initialize_default_components()
            
            # Step 1: Repository Scanning
            self._report_progress("Scanning repository...", 0.1)
            inventory = self._scan_repository(repo_path)
            
            # Step 2: Code Parsing
            self._report_progress("Parsing code files...", 0.2)
            self._parse_files(inventory)
            
            # Step 3: Security Analysis
            self._report_progress("Analyzing security...", 0.4)
            security_issues = self._analyze_security(inventory)
            
            # Step 4: Best Practices Validation
            self._report_progress("Validating best practices...", 0.5)
            best_practice_violations = self._validate_best_practices(inventory)
            
            # Step 5: Architecture Mapping
            self._report_progress("Mapping architecture...", 0.6)
            architecture_map = self._map_architecture(inventory)
            
            # Step 6: Version Analysis
            self._report_progress("Analyzing versions...", 0.7)
            version_analysis = self._analyze_versions(inventory)
            
            # Step 7: Gap Detection
            self._report_progress("Detecting gaps...", 0.8)
            gap_analysis = self._detect_gaps(inventory)
            
            # Step 8: Generate Improvement Tasks
            self._report_progress("Generating improvement tasks...", 0.9)
            improvement_tasks = self._generate_tasks(
                security_issues, best_practice_violations, gap_analysis, version_analysis
            )
            
            # Step 9: Calculate Metrics
            self._report_progress("Calculating metrics...", 0.95)
            metrics = self._calculate_metrics(
                inventory, security_issues, best_practice_violations, improvement_tasks
            )
            
            # Step 10: Create Final Report
            self._report_progress("Finalizing report...", 1.0)
            analysis_report = AnalysisReport(
                repository_inventory=inventory,
                security_issues=security_issues,
                best_practice_violations=best_practice_violations,
                architecture_map=architecture_map,
                gap_analysis=gap_analysis,
                version_analysis=version_analysis,
                improvement_tasks=improvement_tasks,
                metrics=metrics,
                analysis_timestamp=datetime.now(),
                analysis_version="0.1.0"
            )
            
            self.current_analysis = analysis_report
            return analysis_report
            
        except Exception as e:
            self.handle_error(e, "repository analysis")
            # Return partial analysis on error
            return self._create_error_report(repo_path, str(e))
    
    def _initialize_default_components(self) -> None:
        """Initialize default component implementations if not already set."""
        if self._scanner is None:
            self._scanner = RepositoryScanner(self.scanner_config)
        
        if self._parser is None:
            self._parser = CodeParser(self.parser_config)
        
        if self._security_analyzer is None:
            self._security_analyzer = SecurityAnalyzer(self.security_config)
        
        if self._best_practices_validator is None:
            self._best_practices_validator = BestPracticesValidator(self.best_practices_config)
        
        if self._architecture_mapper is None:
            self._architecture_mapper = ArchitectureMapper(self.architecture_config)
        
        if self._gap_detector is None:
            self._gap_detector = GapDetector(self.gap_config)
        
        if self._version_analyzer is None:
            self._version_analyzer = VersionAnalyzer(self.version_config)
    
    def _scan_repository(self, repo_path: Path) -> RepositoryInventory:
        """Scan repository and return inventory."""
        try:
            return self._scanner.scan_repository(repo_path)
        except Exception as e:
            self.errors.append(f"Repository scanning failed: {e}")
            # Return empty inventory on error
            return RepositoryInventory()
    
    def _parse_files(self, inventory: RepositoryInventory) -> None:
        """Parse all files in the inventory and update their AST information."""
        try:
            for tf_file in inventory.terraform_files:
                if not tf_file.ast:  # Only parse if not already parsed
                    try:
                        ast = self._parser.parse_terraform_file(Path(tf_file.path))
                        tf_file.ast = ast
                        # Update extracted components
                        if hasattr(ast, 'variables'):
                            tf_file.variables = ast.variables
                        if hasattr(ast, 'resources'):
                            tf_file.resources = ast.resources
                        if hasattr(ast, 'outputs'):
                            tf_file.outputs = ast.outputs
                        if hasattr(ast, 'modules'):
                            tf_file.modules = ast.modules
                    except Exception as e:
                        self.warnings.append(f"Failed to parse {tf_file.path}: {e}")
                        tf_file.syntax_errors.append(str(e))
            
            for py_file in inventory.python_files:
                try:
                    metadata = self._parser.parse_python_file(Path(py_file.path))
                    if isinstance(metadata, dict):
                        py_file.functions = metadata.get('functions', [])
                        py_file.imports = metadata.get('imports', [])
                except Exception as e:
                    self.warnings.append(f"Failed to parse {py_file.path}: {e}")
                    py_file.syntax_errors.append(str(e))
                    
        except Exception as e:
            self.errors.append(f"File parsing failed: {e}")
    
    def _analyze_security(self, inventory: RepositoryInventory) -> List[SecurityIssue]:
        """Perform security analysis and return issues."""
        try:
            if self._security_analyzer:
                report = self._security_analyzer.analyze_security(inventory.terraform_files)
                return report.issues
            return []
        except Exception as e:
            self.errors.append(f"Security analysis failed: {e}")
            return []
    
    def _validate_best_practices(self, inventory: RepositoryInventory) -> List[BestPracticeIssue]:
        """Validate best practices and return violations."""
        try:
            if self._best_practices_validator:
                report = self._best_practices_validator.validate_practices(inventory.terraform_files)
                return report.violations
            return []
        except Exception as e:
            self.errors.append(f"Best practices validation failed: {e}")
            return []
    
    def _map_architecture(self, inventory: RepositoryInventory) -> Optional[ArchitectureMap]:
        """Map system architecture and return architecture map."""
        try:
            if self._architecture_mapper:
                return self._architecture_mapper.map_architecture(inventory.terraform_files)
            return None
        except Exception as e:
            self.errors.append(f"Architecture mapping failed: {e}")
            return None
    
    def _analyze_versions(self, inventory: RepositoryInventory) -> Optional[VersionAnalysisReport]:
        """Analyze version compatibility and return version analysis."""
        try:
            if self._version_analyzer:
                return self._version_analyzer.analyze_versions(inventory.terraform_files)
            return None
        except Exception as e:
            self.errors.append(f"Version analysis failed: {e}")
            return None
    
    def _detect_gaps(self, inventory: RepositoryInventory) -> Optional[GapAnalysis]:
        """Detect gaps and return gap analysis."""
        try:
            if self._gap_detector:
                return self._gap_detector.detect_gaps(inventory)
            return None
        except Exception as e:
            self.errors.append(f"Gap detection failed: {e}")
            return None
    
    def _generate_tasks(
        self,
        security_issues: List[SecurityIssue],
        best_practice_violations: List[BestPracticeIssue],
        gap_analysis: Optional[GapAnalysis],
        version_analysis: Optional[VersionAnalysisReport]
    ) -> List[ImprovementTask]:
        """Generate improvement tasks from analysis results."""
        try:
            if self._task_generator:
                # Create a temporary analysis report for task generation
                temp_report = AnalysisReport(
                    repository_inventory=RepositoryInventory(),
                    security_issues=security_issues,
                    best_practice_violations=best_practice_violations,
                    gap_analysis=gap_analysis,
                    version_analysis=version_analysis
                )
                return self._task_generator.generate_tasks(temp_report)
            
            # Fallback: create basic tasks from issues
            return self._create_basic_tasks(security_issues, best_practice_violations)
            
        except Exception as e:
            self.errors.append(f"Task generation failed: {e}")
            return []
    
    def _create_basic_tasks(
        self,
        security_issues: List[SecurityIssue],
        best_practice_violations: List[BestPracticeIssue]
    ) -> List[ImprovementTask]:
        """Create basic improvement tasks from issues when task generator is not available."""
        tasks = []
        
        # Create tasks from security issues
        for i, issue in enumerate(security_issues):
            if issue.severity in [Severity.CRITICAL, Severity.HIGH]:
                task = ImprovementTask(
                    id=f"security-{i+1}",
                    title=f"Fix {issue.category.value.lower()} issue",
                    description=issue.description,
                    priority=self._severity_to_priority(issue.severity),
                    effort=self._estimate_effort(issue),
                    category=issue.category,
                    requirements_reference="3.3",  # Security requirements
                    implementation_steps=[issue.recommendation],
                    validation_criteria=[f"Verify {issue.description} is resolved"],
                    affected_files=[issue.file_path]
                )
                tasks.append(task)
        
        # Create tasks from best practice violations
        for i, violation in enumerate(best_practice_violations):
            if violation.severity in [Severity.HIGH, Severity.MEDIUM]:
                task = ImprovementTask(
                    id=f"best-practice-{i+1}",
                    title=f"Fix {violation.category.value.lower()} violation",
                    description=violation.description,
                    priority=self._severity_to_priority(violation.severity),
                    effort=self._estimate_effort(violation),
                    category=violation.category,
                    requirements_reference="4.1",  # Best practices requirements
                    implementation_steps=[violation.recommendation],
                    validation_criteria=[f"Verify {violation.description} is resolved"],
                    affected_files=[violation.file_path]
                )
                tasks.append(task)
        
        return tasks
    
    def _severity_to_priority(self, severity: Severity):
        """Convert severity to priority enum."""
        from ..models import Priority
        
        if severity == Severity.CRITICAL:
            return Priority.HIGH
        elif severity == Severity.HIGH:
            return Priority.HIGH
        elif severity == Severity.MEDIUM:
            return Priority.MEDIUM
        else:
            return Priority.LOW
    
    def _estimate_effort(self, issue) -> Any:
        """Estimate effort required to fix an issue."""
        from ..models import Effort
        
        # Simple heuristic based on issue type and description
        if hasattr(issue, 'category'):
            if issue.category.value in ['SECRETS', 'ACCESS_CONTROL']:
                return Effort.SMALL
            elif issue.category.value in ['ENCRYPTION', 'NETWORK']:
                return Effort.MEDIUM
            else:
                return Effort.LARGE
        
        return Effort.MEDIUM
    
    def _calculate_metrics(
        self,
        inventory: RepositoryInventory,
        security_issues: List[SecurityIssue],
        best_practice_violations: List[BestPracticeIssue],
        improvement_tasks: List[ImprovementTask]
    ) -> AnalysisMetrics:
        """Calculate comprehensive analysis metrics."""
        # Count issues by severity
        security_by_severity = {}
        for severity in Severity:
            security_by_severity[severity.value] = sum(
                1 for issue in security_issues if issue.severity == severity
            )
        
        # Count cloud provider coverage
        cloud_provider_coverage = {}
        for provider, config in inventory.cloud_provider_configs.items():
            cloud_provider_coverage[provider] = len(config.configuration_files)
        
        # Count FortiGate version coverage
        fortigate_version_coverage = {}
        for scenario in inventory.deployment_scenarios:
            for version in scenario.fortigate_versions:
                fortigate_version_coverage[version] = fortigate_version_coverage.get(version, 0) + 1
        
        # Calculate analysis duration
        analysis_duration = 0.0
        if self.analysis_start_time:
            analysis_duration = time.time() - self.analysis_start_time
        
        return AnalysisMetrics(
            total_files=inventory.total_files,
            terraform_files=len(inventory.terraform_files),
            python_files=len(inventory.python_files),
            documentation_files=len(inventory.documentation_files),
            total_resources=sum(len(tf.resources) for tf in inventory.terraform_files),
            total_modules=sum(len(tf.modules) for tf in inventory.terraform_files),
            security_issues_by_severity=security_by_severity,
            best_practice_violations=len(best_practice_violations),
            cloud_provider_coverage=cloud_provider_coverage,
            fortigate_version_coverage=fortigate_version_coverage,
            analysis_duration=analysis_duration
        )
    
    def _create_error_report(self, repo_path: Path, error_message: str) -> AnalysisReport:
        """Create a minimal error report when analysis fails."""
        return AnalysisReport(
            repository_inventory=RepositoryInventory(),
            analysis_timestamp=datetime.now(),
            analysis_version="0.1.0"
        )
    
    def _report_progress(self, message: str, progress: float) -> None:
        """Report analysis progress if callback is set."""
        if self.progress_callback:
            try:
                self.progress_callback(message, progress)
            except Exception as e:
                # Don't let progress reporting errors break analysis
                self.warnings.append(f"Progress reporting failed: {e}")
    
    def set_progress_callback(self, callback: callable) -> None:
        """Set a callback function for progress reporting."""
        self.progress_callback = callback
    
    # Component setter methods (required by AnalysisEngineProtocol)
    
    def set_scanner(self, scanner: RepositoryScannerProtocol) -> None:
        """Set repository scanner component."""
        self._scanner = scanner
    
    def set_parser(self, parser: CodeParserProtocol) -> None:
        """Set code parser component."""
        self._parser = parser
    
    def set_security_analyzer(self, analyzer: SecurityAnalyzerProtocol) -> None:
        """Set security analyzer component."""
        self._security_analyzer = analyzer
    
    def set_best_practices_validator(self, validator: BestPracticesValidatorProtocol) -> None:
        """Set best practices validator component."""
        self._best_practices_validator = validator
    
    def set_architecture_mapper(self, mapper: ArchitectureMapperProtocol) -> None:
        """Set architecture mapper component."""
        self._architecture_mapper = mapper
    
    def set_gap_detector(self, detector: GapDetectorProtocol) -> None:
        """Set gap detector component."""
        self._gap_detector = detector
    
    def set_version_analyzer(self, analyzer: VersionAnalyzerProtocol) -> None:
        """Set version analyzer component."""
        self._version_analyzer = analyzer
    
    def set_task_generator(self, generator: TaskGeneratorProtocol) -> None:
        """Set task generator component."""
        self._task_generator = generator
    
    def set_report_generator(self, generator: ReportGeneratorProtocol) -> None:
        """Set report generator component."""
        self._report_generator = generator
    
    def validate_input(self, repo_path: Path) -> bool:
        """Validate that the repository path is valid for analysis."""
        if not repo_path:
            return False
        
        if not isinstance(repo_path, Path):
            try:
                repo_path = Path(repo_path)
            except Exception:
                return False
        
        if not repo_path.exists():
            return False
        
        if not repo_path.is_dir():
            return False
        
        return True
    
    def handle_error(self, error: Exception, context: str) -> None:
        """Handle errors during analysis with proper logging."""
        error_msg = f"Error during {context}: {error}"
        self.errors.append(error_msg)
        print(error_msg)  # In production, this would use proper logging
    
    def get_analysis_summary(self) -> Dict[str, Any]:
        """Get a summary of the current analysis state."""
        if not self.current_analysis:
            return {"status": "No analysis performed"}
        
        return {
            "status": "Analysis completed",
            "timestamp": self.current_analysis.analysis_timestamp,
            "metrics": self.current_analysis.metrics,
            "security_issues": len(self.current_analysis.security_issues),
            "best_practice_violations": len(self.current_analysis.best_practice_violations),
            "improvement_tasks": len(self.current_analysis.improvement_tasks),
            "errors": len(self.errors),
            "warnings": len(self.warnings)
        }
    
    def get_errors(self) -> List[str]:
        """Get list of errors encountered during analysis."""
        return self.errors.copy()
    
    def get_warnings(self) -> List[str]:
        """Get list of warnings encountered during analysis."""
        return self.warnings.copy()