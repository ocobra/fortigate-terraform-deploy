"""
Version compatibility analyzer for FortiGate Terraform configurations.

This module provides comprehensive version analysis capabilities including:
- FortiGate version detection from configurations and documentation
- Version compatibility matrix for different deployment scenarios
- Version conflict detection logic across configurations
- Upgrade path analysis between FortiGate versions
- Version-specific feature validation and recommendations
"""

import re
import logging
from typing import List, Dict, Set, Optional, Tuple
from pathlib import Path

from ..interfaces import BaseAnalyzer
from ..models import (
    TerraformFile,
    VersionAnalysisReport,
    VersionCompatibilityIssue,
    VersionUpgradePath,
    VersionFeature,
    Severity,
)

logger = logging.getLogger(__name__)


class VersionAnalyzer(BaseAnalyzer):
    """Analyzes FortiGate version compatibility across Terraform configurations."""
    
    # Supported FortiGate versions in order
    SUPPORTED_VERSIONS = ["6.2", "6.4", "7.0", "7.2", "7.4", "7.6"]
    
    # Version patterns for detection
    VERSION_PATTERNS = [
        r'fortigate[_-]?version\s*[=:]\s*["\']?(\d+\.\d+(?:\.\d+)?)["\']?',
        r'version\s*[=:]\s*["\']?(\d+\.\d+(?:\.\d+)?)["\']?',
        r'default\s*=\s*["\'](\d+\.\d+(?:\.\d+)?)["\']',
        r'fortios[_-]?(\d+\.\d+(?:\.\d+)?)',
        r'v(\d+\.\d+(?:\.\d+)?)',
        r'(\d+\.\d+(?:\.\d+)?)[_-]?fortigate',
        r'firmware[_-]?version\s*[=:]\s*["\']?(\d+\.\d+(?:\.\d+)?)["\']?',
        r'FortiGate\s+version\s+(\d+\.\d+(?:\.\d+)?)',
        r'#.*version[:\s]+(\d+\.\d+(?:\.\d+)?)',
    ]
    
    # Version-specific features and their introduction/deprecation
    VERSION_FEATURES = {
        "6.2": [
            VersionFeature("basic_firewall_policies", "6.2", description="Basic firewall policy support"),
            VersionFeature("vdom_support", "6.2", description="Virtual Domain support"),
            VersionFeature("basic_vpn", "6.2", description="Basic VPN functionality"),
        ],
        "6.4": [
            VersionFeature("enhanced_logging", "6.4", description="Enhanced logging capabilities"),
            VersionFeature("improved_ha", "6.4", description="Improved High Availability features"),
            VersionFeature("advanced_routing", "6.4", description="Advanced routing protocols"),
        ],
        "7.0": [
            VersionFeature("security_fabric", "7.0", description="Security Fabric integration"),
            VersionFeature("ztna_support", "7.0", description="Zero Trust Network Access"),
            VersionFeature("cloud_integration", "7.0", description="Enhanced cloud provider integration"),
            VersionFeature("legacy_ssl_vpn", "6.2", "7.0", description="Legacy SSL VPN (deprecated in 7.0)"),
        ],
        "7.2": [
            VersionFeature("advanced_threat_protection", "7.2", description="Advanced threat protection features"),
            VersionFeature("ml_based_detection", "7.2", description="Machine learning-based threat detection"),
            VersionFeature("api_v2", "7.2", description="REST API v2 support"),
        ],
        "7.4": [
            VersionFeature("sase_integration", "7.4", description="SASE (Secure Access Service Edge) integration"),
            VersionFeature("enhanced_sdwan", "7.4", description="Enhanced SD-WAN capabilities"),
            VersionFeature("container_security", "7.4", description="Container security features"),
        ],
        "7.6": [
            VersionFeature("ai_powered_security", "7.6", description="AI-powered security analytics"),
            VersionFeature("quantum_ready_crypto", "7.6", description="Quantum-ready cryptography"),
            VersionFeature("unified_sase", "7.6", description="Unified SASE platform"),
        ],
    }
    
    # Version compatibility matrix
    COMPATIBILITY_MATRIX = {
        ("6.2", "6.4"): "COMPATIBLE",
        ("6.2", "7.0"): "PARTIAL",
        ("6.2", "7.2"): "PARTIAL",
        ("6.2", "7.4"): "INCOMPATIBLE",
        ("6.2", "7.6"): "INCOMPATIBLE",
        ("6.4", "7.0"): "COMPATIBLE",
        ("6.4", "7.2"): "COMPATIBLE",
        ("6.4", "7.4"): "PARTIAL",
        ("6.4", "7.6"): "PARTIAL",
        ("7.0", "7.2"): "COMPATIBLE",
        ("7.0", "7.4"): "COMPATIBLE",
        ("7.0", "7.6"): "COMPATIBLE",
        ("7.2", "7.4"): "COMPATIBLE",
        ("7.2", "7.6"): "COMPATIBLE",
        ("7.4", "7.6"): "COMPATIBLE",
    }
    
    def __init__(self, config: Optional[Dict[str, any]] = None):
        """Initialize the version analyzer with optional configuration."""
        super().__init__(config)
        self.custom_patterns = self.config.get("custom_version_patterns", [])
        self.strict_mode = self.config.get("strict_mode", False)
        
    def analyze(self, terraform_files: List[TerraformFile]) -> VersionAnalysisReport:
        """
        Perform comprehensive version compatibility analysis.
        
        Args:
            terraform_files: List of Terraform files to analyze
            
        Returns:
            VersionAnalysisReport containing all version analysis results
        """
        logger.info(f"Starting version analysis for {len(terraform_files)} files")
        
        try:
            # Detect versions from all files
            detected_versions = self.detect_versions(terraform_files)
            
            # Check for version conflicts
            version_conflicts = self.check_version_conflicts(detected_versions)
            
            # Analyze compatibility issues
            compatibility_issues = self._analyze_compatibility_issues(terraform_files, detected_versions)
            
            # Generate upgrade paths
            upgrade_paths = self._generate_upgrade_paths(detected_versions)
            
            # Generate recommendations
            recommendations = self._generate_recommendations(detected_versions, compatibility_issues, version_conflicts)
            
            # Get supported features for detected versions
            supported_features = self._get_supported_features(detected_versions)
            
            report = VersionAnalysisReport(
                detected_versions=detected_versions,
                compatibility_issues=compatibility_issues,
                upgrade_paths=upgrade_paths,
                version_conflicts=version_conflicts,
                recommendations=recommendations,
                supported_features=supported_features,
            )
            
            logger.info(f"Version analysis completed. Found {len(compatibility_issues)} issues, {len(version_conflicts)} conflicts")
            return report
            
        except Exception as e:
            self.handle_error(e, "version analysis")
            return VersionAnalysisReport()
    
    def detect_versions(self, terraform_files: List[TerraformFile]) -> Dict[str, List[str]]:
        """
        Detect FortiGate versions from configurations and documentation.
        
        Args:
            terraform_files: List of Terraform files to analyze
            
        Returns:
            Dictionary mapping file paths to detected versions
        """
        detected_versions = {}
        
        for tf_file in terraform_files:
            versions = set()
            
            # Check pre-detected versions from file metadata
            if tf_file.fortigate_versions:
                versions.update(tf_file.fortigate_versions)
            
            # Read file content for version detection
            try:
                file_path = Path(tf_file.path)
                if file_path.exists():
                    content = file_path.read_text(encoding=tf_file.encoding)
                    versions.update(self._extract_versions_from_content(content))
            except Exception as e:
                logger.warning(f"Could not read file {tf_file.path}: {e}")
            
            # Analyze AST for version-specific configurations
            if tf_file.ast:
                versions.update(self._extract_versions_from_ast(tf_file))
            
            if versions:
                detected_versions[tf_file.path] = sorted(list(versions))
        
        return detected_versions
    
    def check_version_conflicts(self, detected_versions: Dict[str, List[str]]) -> List[str]:
        """
        Check for version conflicts across configurations.
        
        Args:
            detected_versions: Dictionary of file paths to detected versions
            
        Returns:
            List of conflict descriptions
        """
        conflicts = []
        all_versions = set()
        
        # Collect all detected versions
        for file_path, versions in detected_versions.items():
            all_versions.update(versions)
        
        # Check for incompatible version combinations
        version_list = sorted(list(all_versions))
        for i, version1 in enumerate(version_list):
            for version2 in version_list[i+1:]:
                compatibility = self._get_version_compatibility(version1, version2)
                if compatibility == "INCOMPATIBLE":
                    conflicts.append(
                        f"Incompatible versions detected: {version1} and {version2}. "
                        f"These versions cannot be used together in the same deployment."
                    )
        
        # Check for mixed major versions
        major_versions = set()
        for version in all_versions:
            major = version.split('.')[0]
            major_versions.add(major)
        
        if len(major_versions) > 1:
            conflicts.append(
                f"Mixed major versions detected: {', '.join(sorted(major_versions))}. "
                f"Consider standardizing on a single major version for consistency."
            )
        
        return conflicts
    
    def analyze_upgrade_paths(self, from_version: str, to_version: str) -> VersionUpgradePath:
        """
        Analyze upgrade path between FortiGate versions.
        
        Args:
            from_version: Source version
            to_version: Target version
            
        Returns:
            VersionUpgradePath with upgrade analysis
        """
        compatibility = self._get_version_compatibility(from_version, to_version)
        breaking_changes = []
        required_changes = []
        recommendations = []
        
        # Analyze version-specific changes
        from_idx = self._get_version_index(from_version)
        to_idx = self._get_version_index(to_version)
        
        if from_idx is not None and to_idx is not None:
            if to_idx > from_idx:
                # Upgrading
                for i in range(from_idx + 1, to_idx + 1):
                    version = self.SUPPORTED_VERSIONS[i]
                    features = self.VERSION_FEATURES.get(version, [])
                    
                    for feature in features:
                        if feature.deprecated_version == from_version:
                            breaking_changes.append(f"Feature '{feature.name}' deprecated in {version}")
                        if feature.removed_version == version:
                            breaking_changes.append(f"Feature '{feature.name}' removed in {version}")
                            if feature.alternatives:
                                required_changes.append(f"Replace '{feature.name}' with: {', '.join(feature.alternatives)}")
            
            # Generate recommendations based on compatibility
            if compatibility == "COMPATIBLE":
                recommendations.append("Direct upgrade path available with minimal changes required")
            elif compatibility == "PARTIAL":
                recommendations.append("Upgrade possible but requires configuration review and testing")
                recommendations.append("Review deprecated features and plan migration strategy")
            else:
                recommendations.append("Direct upgrade not recommended - consider intermediate version")
                recommendations.append("Perform thorough compatibility assessment before proceeding")
        
        return VersionUpgradePath(
            from_version=from_version,
            to_version=to_version,
            compatibility=compatibility,
            breaking_changes=breaking_changes,
            required_changes=required_changes,
            recommendations=recommendations,
        )
    
    def validate_version_features(self, terraform_files: List[TerraformFile], version: str) -> List[VersionCompatibilityIssue]:
        """
        Validate version-specific feature usage.
        
        Args:
            terraform_files: List of Terraform files to validate
            version: Target FortiGate version
            
        Returns:
            List of version compatibility issues
        """
        issues = []
        version_features = self.VERSION_FEATURES.get(version, [])
        
        for tf_file in terraform_files:
            if not tf_file.ast:
                continue
                
            # Check resources for version-specific features
            for resource in tf_file.resources:
                resource_issues = self._validate_resource_version_compatibility(
                    resource, version, version_features, tf_file.path
                )
                issues.extend(resource_issues)
        
        return issues
    
    def _extract_versions_from_content(self, content: str) -> Set[str]:
        """Extract version numbers from file content using regex patterns."""
        versions = set()
        
        # Apply all version patterns
        all_patterns = self.VERSION_PATTERNS + self.custom_patterns
        for pattern in all_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                version = match.group(1)
                normalized_version = self._normalize_version(version)
                if normalized_version and self._is_supported_version(normalized_version):
                    versions.add(normalized_version)
        
        return versions
    
    def _extract_versions_from_ast(self, tf_file: TerraformFile) -> Set[str]:
        """Extract versions from Terraform AST by analyzing resource configurations."""
        versions = set()
        
        if not tf_file.ast:
            return versions
        
        # Check variables for version references
        for variable in tf_file.ast.variables:
            if "version" in variable.name.lower():
                if variable.default and isinstance(variable.default, str):
                    version = self._normalize_version(variable.default)
                    if version and self._is_supported_version(version):
                        versions.add(version)
        
        # Check resources for version-specific configurations
        for resource in tf_file.ast.resources:
            if resource.type.startswith("fortios_"):
                # Look for version-specific resource types or configurations
                resource_versions = self._infer_version_from_resource(resource)
                versions.update(resource_versions)
        
        return versions
    
    def _infer_version_from_resource(self, resource) -> Set[str]:
        """Infer FortiGate version from resource type and configuration."""
        versions = set()
        
        # Version-specific resource patterns
        version_specific_resources = {
            "fortios_system_sdn_connector": ["7.0", "7.2", "7.4", "7.6"],
            "fortios_system_ztna": ["7.0", "7.2", "7.4", "7.6"],
            "fortios_firewall_security_fabric": ["7.0", "7.2", "7.4", "7.6"],
            "fortios_system_sase": ["7.4", "7.6"],
            "fortios_system_ai_security": ["7.6"],
        }
        
        if resource.type in version_specific_resources:
            versions.update(version_specific_resources[resource.type])
        
        # Check configuration for version-specific features
        config = resource.configuration
        if isinstance(config, dict):
            # Look for version-specific configuration keys
            if "security_fabric" in config:
                versions.update(["7.0", "7.2", "7.4", "7.6"])
            if "ztna" in config:
                versions.update(["7.0", "7.2", "7.4", "7.6"])
            if "sase" in config:
                versions.update(["7.4", "7.6"])
        
        return versions
    
    def _analyze_compatibility_issues(self, terraform_files: List[TerraformFile], detected_versions: Dict[str, List[str]]) -> List[VersionCompatibilityIssue]:
        """Analyze compatibility issues across all files and versions."""
        issues = []
        
        # Get all unique versions
        all_versions = set()
        for versions in detected_versions.values():
            all_versions.update(versions)
        
        # For each file, check compatibility with all detected versions
        for tf_file in terraform_files:
            file_versions = detected_versions.get(tf_file.path, [])
            
            for version in all_versions:
                if version not in file_versions:
                    # Check if this file's resources are compatible with this version
                    compatibility_issues = self.validate_version_features([tf_file], version)
                    issues.extend(compatibility_issues)
        
        return issues
    
    def _generate_upgrade_paths(self, detected_versions: Dict[str, List[str]]) -> List[VersionUpgradePath]:
        """Generate upgrade paths for all detected version combinations."""
        upgrade_paths = []
        all_versions = set()
        
        for versions in detected_versions.values():
            all_versions.update(versions)
        
        version_list = sorted(list(all_versions))
        
        # Generate upgrade paths between consecutive versions
        for i, from_version in enumerate(version_list):
            for to_version in version_list[i+1:]:
                upgrade_path = self.analyze_upgrade_paths(from_version, to_version)
                upgrade_paths.append(upgrade_path)
        
        return upgrade_paths
    
    def _generate_recommendations(self, detected_versions: Dict[str, List[str]], 
                                compatibility_issues: List[VersionCompatibilityIssue],
                                version_conflicts: List[str]) -> List[str]:
        """Generate version-related recommendations."""
        recommendations = []
        
        # Version standardization recommendations
        all_versions = set()
        for versions in detected_versions.values():
            all_versions.update(versions)
        
        if len(all_versions) > 1:
            latest_version = max(all_versions, key=lambda v: self._get_version_index(v) or 0)
            recommendations.append(
                f"Consider standardizing on FortiGate version {latest_version} "
                f"for consistency across all configurations"
            )
        
        # Compatibility issue recommendations
        if compatibility_issues:
            recommendations.append(
                f"Found {len(compatibility_issues)} version compatibility issues. "
                f"Review and update configurations to ensure version compatibility"
            )
        
        # Version conflict recommendations
        if version_conflicts:
            recommendations.append(
                "Resolve version conflicts before deployment to avoid runtime issues"
            )
        
        # Upgrade recommendations
        if all_versions:
            oldest_version = min(all_versions, key=lambda v: self._get_version_index(v) or 0)
            if self._get_version_index(oldest_version) < len(self.SUPPORTED_VERSIONS) - 2:
                recommendations.append(
                    f"Consider upgrading from older version {oldest_version} "
                    f"to benefit from latest security features and improvements"
                )
        
        return recommendations
    
    def _get_supported_features(self, detected_versions: Dict[str, List[str]]) -> Dict[str, List[VersionFeature]]:
        """Get supported features for all detected versions."""
        supported_features = {}
        all_versions = set()
        
        for versions in detected_versions.values():
            all_versions.update(versions)
        
        for version in all_versions:
            supported_features[version] = self.VERSION_FEATURES.get(version, [])
        
        return supported_features
    
    def _validate_resource_version_compatibility(self, resource, version: str, 
                                               version_features: List[VersionFeature],
                                               file_path: str) -> List[VersionCompatibilityIssue]:
        """Validate a single resource against version compatibility."""
        issues = []
        
        # Check if resource type is supported in the target version
        resource_type = resource.type
        
        # Version-specific resource compatibility checks
        if version in ["6.2", "6.4"] and "ztna" in resource_type.lower():
            issues.append(VersionCompatibilityIssue(
                severity=Severity.HIGH,
                description=f"Resource type '{resource_type}' requires FortiGate 7.0 or later",
                file_path=file_path,
                line_number=resource.line_number,
                current_version=version,
                required_version="7.0",
                recommendation="Upgrade to FortiGate 7.0+ or use alternative configuration",
                affected_features=["ZTNA"]
            ))
        
        if version in ["6.2", "6.4", "7.0", "7.2"] and "sase" in resource_type.lower():
            issues.append(VersionCompatibilityIssue(
                severity=Severity.HIGH,
                description=f"Resource type '{resource_type}' requires FortiGate 7.4 or later",
                file_path=file_path,
                line_number=resource.line_number,
                current_version=version,
                required_version="7.4",
                recommendation="Upgrade to FortiGate 7.4+ or use alternative configuration",
                affected_features=["SASE"]
            ))
        
        return issues
    
    def _get_version_compatibility(self, version1: str, version2: str) -> str:
        """Get compatibility status between two versions."""
        # Normalize version order
        v1, v2 = sorted([version1, version2], key=lambda v: self._get_version_index(v) or 0)
        
        # Check compatibility matrix
        compatibility = self.COMPATIBILITY_MATRIX.get((v1, v2))
        if compatibility:
            return compatibility
        
        # Default compatibility logic
        v1_idx = self._get_version_index(v1)
        v2_idx = self._get_version_index(v2)
        
        if v1_idx is not None and v2_idx is not None:
            version_diff = v2_idx - v1_idx
            if version_diff <= 1:
                return "COMPATIBLE"
            elif version_diff <= 2:
                return "PARTIAL"
            else:
                return "INCOMPATIBLE"
        
        return "UNKNOWN"
    
    def _get_version_index(self, version: str) -> Optional[int]:
        """Get the index of a version in the supported versions list."""
        try:
            return self.SUPPORTED_VERSIONS.index(version)
        except ValueError:
            return None
    
    def _normalize_version(self, version: str) -> Optional[str]:
        """Normalize version string to standard format (X.Y)."""
        if not version:
            return None
        
        # Extract major.minor version
        match = re.match(r'(\d+)\.(\d+)', version.strip())
        if match:
            major, minor = match.groups()
            return f"{major}.{minor}"
        
        return None
    
    def _is_supported_version(self, version: str) -> bool:
        """Check if a version is in the supported versions list."""
        return version in self.SUPPORTED_VERSIONS