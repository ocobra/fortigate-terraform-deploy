"""
Core interfaces and protocols for the FortiGate Terraform Analysis System.

This module defines the abstract interfaces that all analyzer and generator
components must implement, ensuring consistent behavior and enabling
dependency injection and testing.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Protocol
from pathlib import Path

from .models import (
    TerraformFile,
    PythonFile,
    DocumentationFile,
    RepositoryInventory,
    SecurityIssue,
    BestPracticeIssue,
    ArchitectureMap,
    GapAnalysis,
    ImprovementTask,
    AnalysisReport,
    TerraformAST,
    SecurityReport,
    BestPracticesReport,
    VersionAnalysisReport,
    VersionCompatibilityIssue,
    VersionUpgradePath,
)


class RepositoryScannerProtocol(Protocol):
    """Protocol for repository scanning components."""
    
    def scan_repository(self, repo_path: Path) -> RepositoryInventory:
        """Scan repository and return complete inventory."""
        ...
    
    def get_terraform_files(self) -> List[TerraformFile]:
        """Get all discovered Terraform files."""
        ...
    
    def get_python_files(self) -> List[PythonFile]:
        """Get all discovered Python files."""
        ...
    
    def get_documentation_files(self) -> List[DocumentationFile]:
        """Get all discovered documentation files."""
        ...
    
    def get_cloud_provider_configs(self) -> Dict[str, List[TerraformFile]]:
        """Get configurations grouped by cloud provider."""
        ...


class CodeParserProtocol(Protocol):
    """Protocol for code parsing components."""
    
    def parse_terraform_file(self, file_path: Path) -> TerraformAST:
        """Parse a Terraform file and return AST."""
        ...
    
    def parse_python_file(self, file_path: Path) -> Dict[str, Any]:
        """Parse a Python file and extract metadata."""
        ...
    
    def extract_variables(self, ast: TerraformAST) -> List[Dict[str, Any]]:
        """Extract variables from Terraform AST."""
        ...
    
    def extract_resources(self, ast: TerraformAST) -> List[Dict[str, Any]]:
        """Extract resources from Terraform AST."""
        ...
    
    def extract_modules(self, ast: TerraformAST) -> List[Dict[str, Any]]:
        """Extract modules from Terraform AST."""
        ...


class SecurityAnalyzerProtocol(Protocol):
    """Protocol for security analysis components."""
    
    def analyze_security(self, terraform_files: List[TerraformFile]) -> SecurityReport:
        """Perform comprehensive security analysis."""
        ...
    
    def check_hardcoded_secrets(self, ast: TerraformAST) -> List[SecurityIssue]:
        """Check for hardcoded secrets and credentials."""
        ...
    
    def validate_access_controls(self, resources: List[Dict[str, Any]]) -> List[SecurityIssue]:
        """Validate access control configurations."""
        ...
    
    def check_encryption_settings(self, resources: List[Dict[str, Any]]) -> List[SecurityIssue]:
        """Check encryption configurations."""
        ...


class BestPracticesValidatorProtocol(Protocol):
    """Protocol for best practices validation components."""
    
    def validate_practices(self, terraform_files: List[TerraformFile]) -> BestPracticesReport:
        """Validate adherence to best practices."""
        ...
    
    def check_naming_conventions(self, resources: List[Dict[str, Any]]) -> List[BestPracticeIssue]:
        """Check resource naming conventions."""
        ...
    
    def validate_module_structure(self, modules: List[Dict[str, Any]]) -> List[BestPracticeIssue]:
        """Validate module organization and structure."""
        ...
    
    def check_documentation(self, files: List[TerraformFile]) -> List[BestPracticeIssue]:
        """Check documentation completeness."""
        ...


class ArchitectureMapperProtocol(Protocol):
    """Protocol for architecture mapping components."""
    
    def map_architecture(self, terraform_files: List[TerraformFile]) -> ArchitectureMap:
        """Map system architecture and relationships."""
        ...
    
    def identify_entry_points(self, modules: List[Dict[str, Any]]) -> List[str]:
        """Identify main entry points and root modules."""
        ...
    
    def map_dependencies(self, modules: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """Map module dependencies and data flow."""
        ...
    
    def categorize_deployments(self, files: List[TerraformFile]) -> List[str]:
        """Categorize deployment scenarios."""
        ...


class VersionAnalyzerProtocol(Protocol):
    """Protocol for version compatibility analysis components."""
    
    def analyze_versions(self, terraform_files: List[TerraformFile]) -> VersionAnalysisReport:
        """Perform comprehensive version compatibility analysis."""
        ...
    
    def detect_versions(self, terraform_files: List[TerraformFile]) -> Dict[str, List[str]]:
        """Detect FortiGate versions from configurations and documentation."""
        ...
    
    def check_version_conflicts(self, detected_versions: Dict[str, List[str]]) -> List[str]:
        """Check for version conflicts across configurations."""
        ...
    
    def analyze_upgrade_paths(self, from_version: str, to_version: str) -> VersionUpgradePath:
        """Analyze upgrade path between FortiGate versions."""
        ...
    
    def validate_version_features(self, terraform_files: List[TerraformFile], version: str) -> List[VersionCompatibilityIssue]:
        """Validate version-specific feature usage."""
        ...


class GapDetectorProtocol(Protocol):
    """Protocol for gap analysis components."""
    
    def detect_gaps(self, inventory: RepositoryInventory) -> GapAnalysis:
        """Detect gaps and missing functionality."""
        ...
    
    def find_missing_functionality(self, scenarios: List[str]) -> List[str]:
        """Find missing functionality across scenarios."""
        ...
    
    def detect_inconsistencies(self, configs: Dict[str, List[TerraformFile]]) -> List[str]:
        """Detect configuration inconsistencies."""
        ...


class TaskGeneratorProtocol(Protocol):
    """Protocol for improvement task generation components."""
    
    def generate_tasks(self, analysis_report: AnalysisReport) -> List[ImprovementTask]:
        """Generate actionable improvement tasks."""
        ...
    
    def prioritize_tasks(self, tasks: List[ImprovementTask]) -> List[ImprovementTask]:
        """Prioritize tasks by impact and effort."""
        ...
    
    def create_implementation_steps(self, task: ImprovementTask) -> List[str]:
        """Create detailed implementation steps."""
        ...


class ReportGeneratorProtocol(Protocol):
    """Protocol for report generation components."""
    
    def generate_report(self, analysis_report: AnalysisReport) -> Dict[str, Any]:
        """Generate comprehensive analysis report."""
        ...
    
    def export_json(self, report: AnalysisReport, output_path: Path) -> None:
        """Export report as JSON."""
        ...
    
    def export_html(self, report: AnalysisReport, output_path: Path) -> None:
        """Export report as HTML."""
        ...
    
    def export_markdown(self, report: AnalysisReport, output_path: Path) -> None:
        """Export report as Markdown."""
        ...


# Abstract base classes for concrete implementations

class BaseAnalyzer(ABC):
    """Base class for all analyzer components."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
    
    @abstractmethod
    def analyze(self, *args, **kwargs) -> Any:
        """Perform analysis operation."""
        pass
    
    def validate_input(self, *args, **kwargs) -> bool:
        """Validate input parameters."""
        return True
    
    def handle_error(self, error: Exception, context: str) -> None:
        """Handle analysis errors gracefully."""
        # Default implementation logs error and continues
        print(f"Error in {context}: {error}")


class BaseGenerator(ABC):
    """Base class for all generator components."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
    
    @abstractmethod
    def generate(self, *args, **kwargs) -> Any:
        """Perform generation operation."""
        pass
    
    def validate_input(self, *args, **kwargs) -> bool:
        """Validate input parameters."""
        return True
    
    def handle_error(self, error: Exception, context: str) -> None:
        """Handle generation errors gracefully."""
        # Default implementation logs error and continues
        print(f"Error in {context}: {error}")


class AnalysisEngineProtocol(Protocol):
    """Protocol for the main analysis engine."""
    
    def analyze_repository(self, repo_path: Path) -> AnalysisReport:
        """Perform complete repository analysis."""
        ...
    
    def set_scanner(self, scanner: RepositoryScannerProtocol) -> None:
        """Set repository scanner component."""
        ...
    
    def set_parser(self, parser: CodeParserProtocol) -> None:
        """Set code parser component."""
        ...
    
    def set_security_analyzer(self, analyzer: SecurityAnalyzerProtocol) -> None:
        """Set security analyzer component."""
        ...
    
    def set_best_practices_validator(self, validator: BestPracticesValidatorProtocol) -> None:
        """Set best practices validator component."""
        ...
    
    def set_architecture_mapper(self, mapper: ArchitectureMapperProtocol) -> None:
        """Set architecture mapper component."""
        ...
    
    def set_gap_detector(self, detector: GapDetectorProtocol) -> None:
        """Set gap detector component."""
        ...
    
    def set_version_analyzer(self, analyzer: VersionAnalyzerProtocol) -> None:
        """Set version analyzer component."""
        ...
    
    def set_task_generator(self, generator: TaskGeneratorProtocol) -> None:
        """Set task generator component."""
        ...
    
    def set_report_generator(self, generator: ReportGeneratorProtocol) -> None:
        """Set report generator component."""
        ...