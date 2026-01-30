"""
Core data models for the FortiGate Terraform Analysis System.

This module defines the primary data structures used throughout the analysis system,
including representations for Terraform files, security issues, analysis reports,
and improvement tasks.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from datetime import datetime
from enum import Enum


class Severity(Enum):
    """Security issue and violation severity levels."""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class Priority(Enum):
    """Task priority levels."""
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class Effort(Enum):
    """Task effort estimation levels."""
    SMALL = "SMALL"
    MEDIUM = "MEDIUM"
    LARGE = "LARGE"


class Category(Enum):
    """Issue and task category types."""
    SECURITY = "SECURITY"
    BEST_PRACTICES = "BEST_PRACTICES"
    ARCHITECTURE = "ARCHITECTURE"
    DOCUMENTATION = "DOCUMENTATION"
    SECRETS = "SECRETS"
    ACCESS_CONTROL = "ACCESS_CONTROL"
    ENCRYPTION = "ENCRYPTION"
    NETWORK = "NETWORK"


@dataclass
class Variable:
    """Represents a Terraform variable definition."""
    name: str
    type: str
    description: Optional[str] = None
    default: Optional[Any] = None
    sensitive: bool = False
    validation: Optional[Dict[str, Any]] = None


@dataclass
class Resource:
    """Represents a Terraform resource definition."""
    type: str
    name: str
    provider: str
    configuration: Dict[str, Any]
    line_number: int
    dependencies: List[str] = field(default_factory=list)


@dataclass
class Output:
    """Represents a Terraform output definition."""
    name: str
    value: Any
    description: Optional[str] = None
    sensitive: bool = False


@dataclass
class Module:
    """Represents a Terraform module definition."""
    name: str
    source: str
    version: Optional[str] = None
    variables: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)


@dataclass
class TerraformAST:
    """Abstract Syntax Tree representation of a Terraform file."""
    variables: List[Variable] = field(default_factory=list)
    resources: List[Resource] = field(default_factory=list)
    outputs: List[Output] = field(default_factory=list)
    modules: List[Module] = field(default_factory=list)
    providers: List[Dict[str, Any]] = field(default_factory=list)
    terraform_block: Optional[Dict[str, Any]] = None


@dataclass
class TerraformFile:
    """Represents a Terraform configuration file with metadata and parsed content."""
    path: str
    cloud_provider: str
    deployment_type: str
    fortigate_versions: List[str]
    ast: Optional[TerraformAST] = None
    variables: List[Variable] = field(default_factory=list)
    resources: List[Resource] = field(default_factory=list)
    outputs: List[Output] = field(default_factory=list)
    modules: List[Module] = field(default_factory=list)
    file_size: int = 0
    last_modified: Optional[datetime] = None
    encoding: str = "utf-8"
    syntax_errors: List[str] = field(default_factory=list)


@dataclass
class PythonFile:
    """Represents a Python script file with metadata."""
    path: str
    purpose: str  # deployment, utility, test, etc.
    functions: List[str] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)
    file_size: int = 0
    last_modified: Optional[datetime] = None
    encoding: str = "utf-8"
    syntax_errors: List[str] = field(default_factory=list)


@dataclass
class DocumentationFile:
    """Represents a documentation file with metadata."""
    path: str
    type: str  # README, guide, comment, etc.
    content_summary: str = ""
    file_size: int = 0
    last_modified: Optional[datetime] = None
    encoding: str = "utf-8"


@dataclass
class SecurityIssue:
    """Represents a security vulnerability or misconfiguration."""
    severity: Severity
    category: Category
    description: str
    file_path: str
    line_number: int
    recommendation: str
    cwe_id: Optional[str] = None
    rule_id: Optional[str] = None
    confidence: float = 1.0  # 0.0 to 1.0
    affected_resources: List[str] = field(default_factory=list)


@dataclass
class BestPracticeIssue:
    """Represents a best practice violation."""
    severity: Severity
    category: Category
    description: str
    file_path: str
    line_number: int
    recommendation: str
    rule_name: str
    affected_resources: List[str] = field(default_factory=list)


@dataclass
class ArchitectureComponent:
    """Represents a component in the system architecture."""
    name: str
    type: str  # module, resource, data_source
    cloud_provider: str
    dependencies: List[str] = field(default_factory=list)
    dependents: List[str] = field(default_factory=list)
    entry_point: bool = False


@dataclass
class ArchitectureMap:
    """Represents the overall system architecture and component relationships."""
    components: List[ArchitectureComponent] = field(default_factory=list)
    entry_points: List[str] = field(default_factory=list)
    dependency_graph: Dict[str, List[str]] = field(default_factory=dict)
    deployment_scenarios: List[str] = field(default_factory=list)
    cloud_providers: List[str] = field(default_factory=list)
    common_patterns: List[str] = field(default_factory=list)
    pattern_documentation: Optional[Dict[str, Any]] = None


@dataclass
class GapAnalysis:
    """Represents identified gaps and missing functionality."""
    missing_functionality: List[str] = field(default_factory=list)
    inconsistencies: List[str] = field(default_factory=list)
    incomplete_scenarios: List[str] = field(default_factory=list)
    cross_provider_gaps: List[str] = field(default_factory=list)


@dataclass
class AnalysisMetrics:
    """Metrics and statistics from the analysis."""
    total_files: int = 0
    terraform_files: int = 0
    python_files: int = 0
    documentation_files: int = 0
    total_resources: int = 0
    total_modules: int = 0
    security_issues_by_severity: Dict[str, int] = field(default_factory=dict)
    best_practice_violations: int = 0
    cloud_provider_coverage: Dict[str, int] = field(default_factory=dict)
    fortigate_version_coverage: Dict[str, int] = field(default_factory=dict)
    analysis_duration: float = 0.0


@dataclass
class ImprovementTask:
    """Represents an actionable improvement task."""
    id: str
    title: str
    description: str
    priority: Priority
    effort: Effort
    category: Category
    requirements_reference: str
    implementation_steps: List[str] = field(default_factory=list)
    validation_criteria: List[str] = field(default_factory=list)
    affected_files: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    estimated_hours: Optional[int] = None
    completed: bool = False


@dataclass
class CloudProviderConfig:
    """Configuration and metadata for a specific cloud provider."""
    provider: str  # aws, azure, gcp, ibm, oci, alicloud, openstack
    deployment_scenarios: List[str] = field(default_factory=list)
    supported_versions: List[str] = field(default_factory=list)
    specific_features: List[str] = field(default_factory=list)
    configuration_files: List[str] = field(default_factory=list)


@dataclass
class DeploymentScenario:
    """Represents a specific deployment scenario."""
    name: str
    description: str
    architecture_type: str  # single, ha, load_balancer, gwlb, transit_gateway
    complexity: str
    cloud_providers: List[str] = field(default_factory=list)
    use_cases: List[str] = field(default_factory=list)
    fortigate_versions: List[str] = field(default_factory=list)


@dataclass
class RepositoryInventory:
    """Complete inventory of repository contents."""
    terraform_files: List[TerraformFile] = field(default_factory=list)
    python_files: List[PythonFile] = field(default_factory=list)
    documentation_files: List[DocumentationFile] = field(default_factory=list)
    cloud_provider_configs: Dict[str, CloudProviderConfig] = field(default_factory=dict)
    deployment_scenarios: List[DeploymentScenario] = field(default_factory=list)
    total_files: int = 0
    repository_size: int = 0
    scan_timestamp: Optional[datetime] = None


@dataclass
class SecurityReport:
    """Security analysis results."""
    issues: List[SecurityIssue] = field(default_factory=list)
    summary: Dict[str, int] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)


@dataclass
class BestPracticesReport:
    """Best practices validation results."""
    violations: List[BestPracticeIssue] = field(default_factory=list)
    summary: Dict[str, int] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)


@dataclass
class VersionCompatibilityIssue:
    """Represents a version compatibility issue."""
    severity: Severity
    description: str
    file_path: str
    line_number: int
    current_version: str
    required_version: str
    recommendation: str
    affected_features: List[str] = field(default_factory=list)


@dataclass
class VersionUpgradePath:
    """Represents an upgrade path between FortiGate versions."""
    from_version: str
    to_version: str
    compatibility: str  # COMPATIBLE, PARTIAL, INCOMPATIBLE
    breaking_changes: List[str] = field(default_factory=list)
    required_changes: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


@dataclass
class VersionFeature:
    """Represents a version-specific feature."""
    name: str
    introduced_version: str
    deprecated_version: Optional[str] = None
    removed_version: Optional[str] = None
    description: str = ""
    alternatives: List[str] = field(default_factory=list)


@dataclass
class VersionAnalysisReport:
    """Version compatibility analysis results."""
    detected_versions: Dict[str, List[str]] = field(default_factory=dict)  # file_path -> versions
    compatibility_issues: List[VersionCompatibilityIssue] = field(default_factory=list)
    upgrade_paths: List[VersionUpgradePath] = field(default_factory=list)
    version_conflicts: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    supported_features: Dict[str, List[VersionFeature]] = field(default_factory=dict)  # version -> features


@dataclass
class AnalysisReport:
    """Comprehensive analysis report containing all findings and recommendations."""
    repository_inventory: RepositoryInventory
    security_issues: List[SecurityIssue] = field(default_factory=list)
    best_practice_violations: List[BestPracticeIssue] = field(default_factory=list)
    architecture_map: Optional[ArchitectureMap] = None
    gap_analysis: Optional[GapAnalysis] = None
    version_analysis: Optional[VersionAnalysisReport] = None
    improvement_tasks: List[ImprovementTask] = field(default_factory=list)
    metrics: Optional[AnalysisMetrics] = None
    analysis_timestamp: Optional[datetime] = None
    analysis_version: str = "0.1.0"