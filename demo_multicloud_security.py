#!/usr/bin/env python3
"""
Demonstration of multi-cloud security validation capabilities.

This script shows how the enhanced SecurityAnalyzer can detect security issues
across different cloud providers and identify cross-cloud inconsistencies.
"""

from fortigate_analysis.analyzer.security_analyzer import SecurityAnalyzer
from fortigate_analysis.models import (
    TerraformFile, Resource, Severity, Category
)


def create_sample_aws_resources():
    """Create sample AWS resources with security issues."""
    return [
        # EC2 instance without IMDSv2
        Resource(
            type="aws_instance",
            name="fortigate-instance",
            provider="aws",
            configuration={
                "ami": "ami-12345678",
                "instance_type": "c5.large",
                "metadata_options": {
                    "http_tokens": "optional"  # Security issue: IMDSv2 not enforced
                },
                "monitoring": False  # Security issue: No detailed monitoring
            },
            line_number=10
        ),
        # S3 bucket without encryption
        Resource(
            type="aws_s3_bucket",
            name="fortigate-backups",
            provider="aws",
            configuration={
                "bucket": "fortigate-backups-123",
                "versioning": {"enabled": False}  # Security issue: No versioning
                # Missing: server_side_encryption_configuration
            },
            line_number=20
        ),
        # Overly permissive security group
        Resource(
            type="aws_security_group",
            name="fortigate-sg",
            provider="aws",
            configuration={
                "ingress": [{
                    "from_port": 22,
                    "to_port": 22,
                    "protocol": "tcp",
                    "cidr_blocks": ["0.0.0.0/0"]  # Security issue: SSH open to world
                }]
            },
            line_number=30
        )
    ]


def create_sample_azure_resources():
    """Create sample Azure resources with security issues."""
    return [
        # VM without managed identity
        Resource(
            type="azurerm_virtual_machine",
            name="fortigate-vm",
            provider="azurerm",
            configuration={
                "vm_size": "Standard_D2s_v3",
                # Missing: identity configuration
                # Missing: boot_diagnostics
            },
            line_number=40
        ),
        # Storage account without HTTPS enforcement
        Resource(
            type="azurerm_storage_account",
            name="fortigate-storage",
            provider="azurerm",
            configuration={
                "account_tier": "Standard",
                "account_replication_type": "LRS",
                "enable_https_traffic_only": False,  # Security issue: HTTPS not enforced
                "min_tls_version": "TLS1_0"  # Security issue: Weak TLS version
            },
            line_number=50
        ),
        # Overly permissive NSG rule
        Resource(
            type="azurerm_network_security_rule",
            name="allow-ssh",
            provider="azurerm",
            configuration={
                "access": "Allow",
                "direction": "Inbound",
                "protocol": "Tcp",
                "source_address_prefix": "*",  # Security issue: Open to all
                "destination_port_range": "22"
            },
            line_number=60
        )
    ]


def create_sample_gcp_resources():
    """Create sample GCP resources with security issues."""
    return [
        # Compute instance without OS Login
        Resource(
            type="google_compute_instance",
            name="fortigate-instance",
            provider="google",
            configuration={
                "machine_type": "n1-standard-2",
                "metadata": {
                    "enable-oslogin": "false",  # Security issue: OS Login disabled
                    "serial-port-enable": "true"  # Security issue: Serial port enabled
                }
            },
            line_number=70
        ),
        # Storage bucket without uniform access
        Resource(
            type="google_storage_bucket",
            name="fortigate-backups",
            provider="google",
            configuration={
                "location": "US",
                "uniform_bucket_level_access": False  # Security issue: No uniform access
            },
            line_number=80
        ),
        # Overly broad IAM role
        Resource(
            type="google_project_iam_binding",
            name="fortigate-access",
            provider="google",
            configuration={
                "role": "roles/owner",  # Security issue: Overly broad role
                "members": ["serviceAccount:fortigate@project.iam.gserviceaccount.com"]
            },
            line_number=90
        )
    ]


def main():
    """Demonstrate multi-cloud security validation."""
    print("🔒 Multi-Cloud Security Validation Demo")
    print("=" * 50)
    
    # Initialize the security analyzer
    analyzer = SecurityAnalyzer()
    
    # Create sample Terraform files for different cloud providers
    aws_file = TerraformFile(
        path="aws/fortigate.tf",
        cloud_provider="aws",
        deployment_type="single",
        fortigate_versions=["7.0"],
        resources=create_sample_aws_resources()
    )
    
    azure_file = TerraformFile(
        path="azure/fortigate.tf",
        cloud_provider="azure",
        deployment_type="single",
        fortigate_versions=["7.0"],
        resources=create_sample_azure_resources()
    )
    
    gcp_file = TerraformFile(
        path="gcp/fortigate.tf",
        cloud_provider="gcp",
        deployment_type="single",
        fortigate_versions=["7.0"],
        resources=create_sample_gcp_resources()
    )
    
    # Analyze each cloud provider separately
    print("\n🔍 AWS Security Analysis:")
    print("-" * 30)
    aws_issues = analyzer.validate_multicloud_security(aws_file.resources, "aws")
    for issue in aws_issues:
        print(f"  • {issue.severity.value}: {issue.description}")
        print(f"    Rule: {issue.rule_id}")
        print(f"    Recommendation: {issue.recommendation}")
        print()
    
    print(f"Total AWS issues found: {len(aws_issues)}")
    
    print("\n🔍 Azure Security Analysis:")
    print("-" * 30)
    azure_issues = analyzer.validate_multicloud_security(azure_file.resources, "azure")
    for issue in azure_issues:
        print(f"  • {issue.severity.value}: {issue.description}")
        print(f"    Rule: {issue.rule_id}")
        print(f"    Recommendation: {issue.recommendation}")
        print()
    
    print(f"Total Azure issues found: {len(azure_issues)}")
    
    print("\n🔍 GCP Security Analysis:")
    print("-" * 30)
    gcp_issues = analyzer.validate_multicloud_security(gcp_file.resources, "gcp")
    for issue in gcp_issues:
        print(f"  • {issue.severity.value}: {issue.description}")
        print(f"    Rule: {issue.rule_id}")
        print(f"    Recommendation: {issue.recommendation}")
        print()
    
    print(f"Total GCP issues found: {len(gcp_issues)}")
    
    # Analyze cross-cloud consistency
    print("\n🌐 Cross-Cloud Consistency Analysis:")
    print("-" * 40)
    consistency_issues = analyzer.check_cross_cloud_consistency([aws_file, azure_file, gcp_file])
    
    if consistency_issues:
        for issue in consistency_issues:
            print(f"  • {issue.severity.value}: {issue.description}")
            print(f"    Rule: {issue.rule_id}")
            print(f"    Recommendation: {issue.recommendation}")
            print()
        print(f"Total consistency issues found: {len(consistency_issues)}")
    else:
        print("  ✅ No cross-cloud consistency issues detected")
    
    # Comprehensive analysis
    print("\n📊 Comprehensive Multi-Cloud Analysis:")
    print("-" * 45)
    all_files = [aws_file, azure_file, gcp_file]
    
    # Disable external tools for demo
    analyzer.enable_external_tools = False
    report = analyzer.analyze_security(all_files)
    
    print(f"Total security issues found: {report.summary['total_issues']}")
    print(f"  • Critical: {report.summary.get('critical', 0)}")
    print(f"  • High: {report.summary.get('high', 0)}")
    print(f"  • Medium: {report.summary.get('medium', 0)}")
    print(f"  • Low: {report.summary.get('low', 0)}")
    
    print("\nIssues by category:")
    for category, count in report.summary.get('by_category', {}).items():
        print(f"  • {category}: {count}")
    
    print("\n💡 Key Recommendations:")
    for i, recommendation in enumerate(report.recommendations[:5], 1):
        print(f"  {i}. {recommendation}")
    
    print("\n✨ Multi-cloud security validation completed!")
    print(f"   Analyzed {len(all_files)} cloud providers")
    print(f"   Found {len(report.issues)} total security issues")
    print(f"   Generated {len(report.recommendations)} recommendations")


if __name__ == "__main__":
    main()