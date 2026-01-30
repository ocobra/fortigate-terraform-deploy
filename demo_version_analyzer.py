#!/usr/bin/env python3
"""
Demo script for the VersionAnalyzer class.

This script demonstrates the comprehensive version analysis capabilities
of the FortiGate Terraform Analysis System's VersionAnalyzer.
"""

from fortigate_analysis.analyzer.version_analyzer import VersionAnalyzer
from fortigate_analysis.models import (
    TerraformFile,
    TerraformAST,
    Variable,
    Resource,
)


def create_sample_files():
    """Create sample Terraform files for demonstration."""
    # Legacy FortiGate 6.4 configuration
    legacy_ast = TerraformAST(
        variables=[
            Variable(name="fortigate_version", type="string", default="6.4")
        ],
        resources=[
            Resource(
                type="fortios_system_global",
                name="legacy_config",
                provider="fortios",
                configuration={"hostname": "legacy-fw"},
                line_number=5
            )
        ]
    )
    
    legacy_file = TerraformFile(
        path="legacy/main.tf",
        cloud_provider="aws",
        deployment_type="single",
        fortigate_versions=["6.4"],
        ast=legacy_ast
    )
    
    # Modern FortiGate 7.4 configuration with ZTNA
    modern_ast = TerraformAST(
        variables=[
            Variable(name="fortigate_version", type="string", default="7.4")
        ],
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
                line_number=15
            )
        ]
    )
    
    modern_file = TerraformFile(
        path="modern/main.tf",
        cloud_provider="azure",
        deployment_type="ha",
        fortigate_versions=["7.4"],
        ast=modern_ast
    )
    
    return [legacy_file, modern_file]


def main():
    """Demonstrate VersionAnalyzer capabilities."""
    print("=== FortiGate Version Analyzer Demo ===\n")
    
    # Initialize the analyzer
    analyzer = VersionAnalyzer()
    
    # Create sample files
    terraform_files = create_sample_files()
    
    print("Sample Terraform files:")
    for tf_file in terraform_files:
        print(f"  - {tf_file.path} (FortiGate {', '.join(tf_file.fortigate_versions)})")
    print()
    
    # Perform comprehensive version analysis
    print("Performing version analysis...")
    report = analyzer.analyze(terraform_files)
    
    # Display results
    print("\n=== Version Analysis Results ===\n")
    
    # Detected versions
    print("1. Detected Versions:")
    for file_path, versions in report.detected_versions.items():
        print(f"   {file_path}: {', '.join(versions)}")
    print()
    
    # Version conflicts
    print("2. Version Conflicts:")
    if report.version_conflicts:
        for conflict in report.version_conflicts:
            print(f"   ⚠️  {conflict}")
    else:
        print("   ✅ No version conflicts detected")
    print()
    
    # Compatibility issues
    print("3. Compatibility Issues:")
    if report.compatibility_issues:
        for issue in report.compatibility_issues:
            print(f"   🔴 {issue.severity.value}: {issue.description}")
            print(f"      File: {issue.file_path}:{issue.line_number}")
            print(f"      Recommendation: {issue.recommendation}")
    else:
        print("   ✅ No compatibility issues found")
    print()
    
    # Upgrade paths
    print("4. Upgrade Paths:")
    for upgrade_path in report.upgrade_paths:
        print(f"   {upgrade_path.from_version} → {upgrade_path.to_version}: {upgrade_path.compatibility}")
        if upgrade_path.breaking_changes:
            print(f"      Breaking changes: {', '.join(upgrade_path.breaking_changes)}")
        if upgrade_path.recommendations:
            print(f"      Recommendations: {upgrade_path.recommendations[0]}")
    print()
    
    # Recommendations
    print("5. Recommendations:")
    for recommendation in report.recommendations:
        print(f"   💡 {recommendation}")
    print()
    
    # Supported features by version
    print("6. Supported Features by Version:")
    for version, features in report.supported_features.items():
        print(f"   FortiGate {version}:")
        for feature in features[:3]:  # Show first 3 features
            print(f"     - {feature.name}: {feature.description}")
        if len(features) > 3:
            print(f"     ... and {len(features) - 3} more features")
    print()
    
    print("=== Demo Complete ===")


if __name__ == "__main__":
    main()