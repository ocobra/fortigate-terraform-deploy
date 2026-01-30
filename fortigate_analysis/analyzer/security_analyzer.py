"""
Security analyzer implementation for identifying vulnerabilities and misconfigurations.
"""

import re
import math
import subprocess
import json
from typing import List, Dict, Any, Optional, Set
from pathlib import Path

from ..models import (
    TerraformFile, SecurityIssue, SecurityReport, TerraformAST, Resource,
    Severity, Category
)
from ..interfaces import SecurityAnalyzerProtocol, BaseAnalyzer


class SecurityAnalyzer(BaseAnalyzer):
    """
    Identifies security vulnerabilities and misconfigurations in Terraform code.
    
    Performs comprehensive security analysis including hardcoded secrets detection,
    access control validation, encryption settings verification, and network security analysis.
    """
    
    # Regex patterns for detecting hardcoded secrets
    SECRET_PATTERNS = {
        'aws_access_key': r'AKIA[0-9A-Z]{16}',
        'aws_secret_key': r'[A-Za-z0-9/+=]{40}',
        'generic_api_key': r'sk-[A-Za-z0-9]{32,}',
        'password': r'(?i)(password|passwd|pwd)\s*[=:]\s*["\']([^"\']{8,})["\']',
        'private_key': r'-----BEGIN\s+(RSA\s+)?PRIVATE\s+KEY-----',
        'certificate': r'-----BEGIN\s+CERTIFICATE-----',
        'jwt_token': r'eyJ[A-Za-z0-9_-]*\.eyJ[A-Za-z0-9_-]*\.[A-Za-z0-9_-]*',
        'github_token': r'ghp_[A-Za-z0-9]{36}',
        'slack_token': r'xox[baprs]-[A-Za-z0-9-]+',
        'google_api_key': r'AIza[0-9A-Za-z_-]{35}',
        # Removed overly broad azure_client_secret pattern
    }
    
    # Common insecure protocols and ports
    INSECURE_PROTOCOLS = {'http', 'ftp', 'telnet', 'smtp', 'pop3', 'imap'}
    INSECURE_PORTS = {21, 23, 25, 53, 80, 110, 143, 993, 995}
    
    # Overly permissive CIDR blocks
    PERMISSIVE_CIDRS = {'0.0.0.0/0', '::/0'}
    
    def __init__(self, config: Dict = None):
        super().__init__(config)
        self.enable_external_tools = config.get('enable_external_tools', True) if config else True
        self.tfsec_path = config.get('tfsec_path', 'tfsec') if config else 'tfsec'
        self.checkov_path = config.get('checkov_path', 'checkov') if config else 'checkov'
    
    def analyze(self, terraform_files: List[TerraformFile]) -> SecurityReport:
        """Alias for analyze_security to match BaseAnalyzer interface."""
        return self.analyze_security(terraform_files)
    
    def analyze_security(self, terraform_files: List[TerraformFile]) -> SecurityReport:
        """
        Perform comprehensive security analysis.
        
        Args:
            terraform_files: List of Terraform files to analyze
            
        Returns:
            SecurityReport with identified issues and recommendations
        """
        all_issues = []
        
        for tf_file in terraform_files:
            try:
                # Check for hardcoded secrets
                if tf_file.ast:
                    secrets_issues = self.check_hardcoded_secrets(tf_file.ast)
                    for issue in secrets_issues:
                        issue.file_path = tf_file.path
                    all_issues.extend(secrets_issues)
                
                # Validate access controls
                access_issues = self.validate_access_controls(tf_file.resources)
                for issue in access_issues:
                    issue.file_path = tf_file.path
                all_issues.extend(access_issues)
                
                # Check encryption settings
                encryption_issues = self.check_encryption_settings(tf_file.resources)
                for issue in encryption_issues:
                    issue.file_path = tf_file.path
                all_issues.extend(encryption_issues)
                
                # Analyze network security
                network_issues = self.analyze_network_security(tf_file.resources)
                for issue in network_issues:
                    issue.file_path = tf_file.path
                all_issues.extend(network_issues)
                
                # Multi-cloud specific security validation
                multicloud_issues = self.validate_multicloud_security(tf_file.resources, tf_file.cloud_provider)
                for issue in multicloud_issues:
                    issue.file_path = tf_file.path
                all_issues.extend(multicloud_issues)
                
            except Exception as e:
                self.handle_error(e, f"analyzing file {tf_file.path}")
        
        # Cross-cloud consistency checking
        consistency_issues = self.check_cross_cloud_consistency(terraform_files)
        all_issues.extend(consistency_issues)
        
        # Run external security tools if enabled
        if self.enable_external_tools:
            external_issues = self._run_external_tools(terraform_files)
            all_issues.extend(external_issues)
        
        # Generate summary and recommendations
        summary = self._generate_summary(all_issues)
        recommendations = self._generate_recommendations(all_issues)
        
        return SecurityReport(
            issues=all_issues,
            summary=summary,
            recommendations=recommendations
        )
    
    def check_hardcoded_secrets(self, ast: TerraformAST) -> List[SecurityIssue]:
        """
        Check for hardcoded secrets and credentials using regex patterns and entropy analysis.
        
        Args:
            ast: Terraform AST to analyze
            
        Returns:
            List of SecurityIssue objects for detected secrets
        """
        issues = []
        
        # Check all resources for hardcoded secrets
        for resource in ast.resources:
            issues.extend(self._check_resource_secrets(resource))
        
        # Check variables for potential secrets
        for variable in ast.variables:
            issues.extend(self._check_variable_secrets(variable))
        
        return issues
    
    def _check_resource_secrets(self, resource: Resource) -> List[SecurityIssue]:
        """Check a resource configuration for hardcoded secrets."""
        issues = []
        
        def check_value(key: str, value: Any, path: str = "") -> None:
            if isinstance(value, str):
                # Check against known secret patterns
                for secret_type, pattern in self.SECRET_PATTERNS.items():
                    matches = re.finditer(pattern, value)
                    for match in matches:
                        issues.append(SecurityIssue(
                            severity=Severity.CRITICAL,
                            category=Category.SECRETS,
                            description=f"Potential {secret_type} detected in {resource.type}.{resource.name}",
                            file_path="",  # Will be set by caller
                            line_number=resource.line_number,
                            recommendation=f"Move {secret_type} to environment variables or secure parameter store",
                            rule_id=f"hardcoded_{secret_type}",
                            affected_resources=[f"{resource.type}.{resource.name}"]
                        ))
                
                # Check entropy for potential secrets
                if len(value) > 16 and self._calculate_entropy(value) > 4.5:
                    # High entropy string might be a secret
                    if not self._is_likely_hash_or_id(value):
                        issues.append(SecurityIssue(
                            severity=Severity.MEDIUM,
                            category=Category.SECRETS,
                            description=f"High entropy string detected in {resource.type}.{resource.name}.{key}",
                            file_path="",
                            line_number=resource.line_number,
                            recommendation="Review if this is a hardcoded secret that should be externalized",
                            rule_id="high_entropy_string",
                            confidence=0.7,
                            affected_resources=[f"{resource.type}.{resource.name}"]
                        ))
            
            elif isinstance(value, dict):
                for k, v in value.items():
                    check_value(k, v, f"{path}.{k}" if path else k)
            
            elif isinstance(value, list):
                for i, item in enumerate(value):
                    check_value(f"{key}[{i}]", item, path)
        
        # Recursively check all configuration values
        for key, value in resource.configuration.items():
            check_value(key, value)
        
        return issues
    
    def _check_variable_secrets(self, variable) -> List[SecurityIssue]:
        """Check variable definitions for potential secrets."""
        issues = []
        
        # Check if variable name suggests it's a secret
        secret_keywords = ['password', 'secret', 'key', 'token', 'credential', 'auth']
        var_name_lower = variable.name.lower()
        
        if any(keyword in var_name_lower for keyword in secret_keywords):
            if not variable.sensitive:
                issues.append(SecurityIssue(
                    severity=Severity.HIGH,
                    category=Category.SECRETS,
                    description=f"Variable '{variable.name}' appears to be sensitive but not marked as sensitive",
                    file_path="",
                    line_number=0,  # Variable line number not available in current model
                    recommendation=f"Mark variable '{variable.name}' as sensitive = true",
                    rule_id="insensitive_secret_variable",
                    affected_resources=[f"var.{variable.name}"]
                ))
        
        # Check default values for secrets
        if variable.default and isinstance(variable.default, str):
            for secret_type, pattern in self.SECRET_PATTERNS.items():
                if re.search(pattern, variable.default):
                    issues.append(SecurityIssue(
                        severity=Severity.CRITICAL,
                        category=Category.SECRETS,
                        description=f"Hardcoded {secret_type} in variable '{variable.name}' default value",
                        file_path="",
                        line_number=0,
                        recommendation=f"Remove hardcoded {secret_type} from variable default",
                        rule_id=f"hardcoded_{secret_type}_in_variable",
                        affected_resources=[f"var.{variable.name}"]
                    ))
        
        return issues
    
    def validate_access_controls(self, resources: List[Resource]) -> List[SecurityIssue]:
        """
        Validate access control configurations for overly permissive access.
        
        Args:
            resources: List of resources to analyze
            
        Returns:
            List of SecurityIssue objects for access control violations
        """
        issues = []
        
        for resource in resources:
            try:
                # Check security groups
                if resource.type in ['aws_security_group', 'aws_security_group_rule']:
                    issues.extend(self._check_security_group(resource))
                
                # Check firewall rules
                elif resource.type in ['google_compute_firewall', 'azurerm_network_security_rule']:
                    issues.extend(self._check_firewall_rule(resource))
                
                # Check IAM policies
                elif resource.type in ['aws_iam_policy', 'aws_iam_role_policy']:
                    issues.extend(self._check_iam_policy(resource))
                
                # Check public access configurations
                elif resource.type in ['aws_s3_bucket_public_access_block', 'aws_s3_bucket_acl']:
                    issues.extend(self._check_public_access(resource))
                
            except Exception as e:
                self.handle_error(e, f"validating access controls for {resource.type}.{resource.name}")
        
        return issues
    
    def _check_security_group(self, resource: Resource) -> List[SecurityIssue]:
        """Check AWS security group for overly permissive rules."""
        issues = []
        config = resource.configuration
        
        # Check ingress rules
        ingress_rules = config.get('ingress', [])
        if not isinstance(ingress_rules, list):
            ingress_rules = [ingress_rules]
        
        for rule in ingress_rules:
            if isinstance(rule, dict):
                cidr_blocks = rule.get('cidr_blocks', [])
                from_port = rule.get('from_port', 0)
                to_port = rule.get('to_port', 0)
                protocol = rule.get('protocol', '')
                
                # Check for overly permissive CIDR blocks
                if any(cidr in self.PERMISSIVE_CIDRS for cidr in cidr_blocks):
                    severity = Severity.CRITICAL if from_port == 22 else Severity.HIGH
                    issues.append(SecurityIssue(
                        severity=severity,
                        category=Category.ACCESS_CONTROL,
                        description=f"Security group {resource.name} allows ingress from 0.0.0.0/0",
                        file_path="",
                        line_number=resource.line_number,
                        recommendation="Restrict ingress to specific IP ranges or security groups",
                        rule_id="overly_permissive_ingress",
                        affected_resources=[f"{resource.type}.{resource.name}"]
                    ))
                
                # Check for insecure ports
                if from_port in self.INSECURE_PORTS or to_port in self.INSECURE_PORTS:
                    issues.append(SecurityIssue(
                        severity=Severity.HIGH,
                        category=Category.NETWORK,
                        description=f"Security group {resource.name} allows access to insecure port {from_port}-{to_port}",
                        file_path="",
                        line_number=resource.line_number,
                        recommendation="Use secure alternatives or restrict access to trusted sources",
                        rule_id="insecure_port_access",
                        affected_resources=[f"{resource.type}.{resource.name}"]
                    ))
        
        return issues
    
    def _check_firewall_rule(self, resource: Resource) -> List[SecurityIssue]:
        """Check firewall rules for overly permissive access."""
        issues = []
        config = resource.configuration
        
        # Check source ranges for GCP firewall rules
        if resource.type == 'google_compute_firewall':
            source_ranges = config.get('source_ranges', [])
            if any(cidr in self.PERMISSIVE_CIDRS for cidr in source_ranges):
                issues.append(SecurityIssue(
                    severity=Severity.HIGH,
                    category=Category.ACCESS_CONTROL,
                    description=f"Firewall rule {resource.name} allows access from 0.0.0.0/0",
                    file_path="",
                    line_number=resource.line_number,
                    recommendation="Restrict source ranges to specific IP ranges",
                    rule_id="overly_permissive_firewall",
                    affected_resources=[f"{resource.type}.{resource.name}"]
                ))
        
        # Check Azure network security rules
        elif resource.type == 'azurerm_network_security_rule':
            source_address_prefix = config.get('source_address_prefix', '')
            if source_address_prefix in self.PERMISSIVE_CIDRS or source_address_prefix == '*':
                issues.append(SecurityIssue(
                    severity=Severity.HIGH,
                    category=Category.ACCESS_CONTROL,
                    description=f"Network security rule {resource.name} allows access from {source_address_prefix}",
                    file_path="",
                    line_number=resource.line_number,
                    recommendation="Restrict source address prefix to specific IP ranges",
                    rule_id="overly_permissive_azure_nsg",
                    affected_resources=[f"{resource.type}.{resource.name}"]
                ))
        
        return issues
    
    def _check_iam_policy(self, resource: Resource) -> List[SecurityIssue]:
        """Check IAM policies for overly permissive permissions."""
        issues = []
        config = resource.configuration
        
        # Check for wildcard permissions
        policy = config.get('policy', '')
        if isinstance(policy, str) and policy:
            # Try to parse as JSON to check for wildcard actions/resources
            try:
                # Handle both direct JSON strings and jsonencode() function calls
                if 'jsonencode(' in policy:
                    # Extract the JSON part from jsonencode(...)
                    start = policy.find('jsonencode(') + len('jsonencode(')
                    end = policy.rfind(')')
                    if end > start:
                        json_part = policy[start:end]
                        # Remove any Terraform interpolation syntax
                        json_part = json_part.replace('${', '').replace('}', '')
                        policy_doc = json.loads(json_part)
                    else:
                        return issues
                else:
                    policy_doc = json.loads(policy)
                
                if isinstance(policy_doc, dict) and 'Statement' in policy_doc:
                    statements = policy_doc['Statement']
                    if not isinstance(statements, list):
                        statements = [statements]
                    
                    for stmt in statements:
                        actions = stmt.get('Action', [])
                        resources = stmt.get('Resource', [])
                        
                        if '*' in actions or actions == '*':
                            issues.append(SecurityIssue(
                                severity=Severity.HIGH,
                                category=Category.ACCESS_CONTROL,
                                description=f"IAM policy {resource.name} grants wildcard actions (*)",
                                file_path="",
                                line_number=resource.line_number,
                                recommendation="Use specific actions instead of wildcard permissions",
                                rule_id="wildcard_iam_actions",
                                affected_resources=[f"{resource.type}.{resource.name}"]
                            ))
                        
                        if '*' in resources or resources == '*':
                            issues.append(SecurityIssue(
                                severity=Severity.HIGH,
                                category=Category.ACCESS_CONTROL,
                                description=f"IAM policy {resource.name} grants access to all resources (*)",
                                file_path="",
                                line_number=resource.line_number,
                                recommendation="Use specific resource ARNs instead of wildcard",
                                rule_id="wildcard_iam_resources",
                                affected_resources=[f"{resource.type}.{resource.name}"]
                            ))
            except (json.JSONDecodeError, KeyError, IndexError):
                pass  # Skip if policy is not valid JSON or has parsing issues
        
        return issues
    
    def _check_public_access(self, resource: Resource) -> List[SecurityIssue]:
        """Check for public access configurations."""
        issues = []
        config = resource.configuration
        
        if resource.type == 'aws_s3_bucket_public_access_block':
            # Check if public access is not blocked
            block_settings = [
                'block_public_acls',
                'block_public_policy',
                'ignore_public_acls',
                'restrict_public_buckets'
            ]
            
            for setting in block_settings:
                if config.get(setting, True) is False:
                    issues.append(SecurityIssue(
                        severity=Severity.HIGH,
                        category=Category.ACCESS_CONTROL,
                        description=f"S3 bucket public access setting '{setting}' is disabled",
                        file_path="",
                        line_number=resource.line_number,
                        recommendation=f"Enable '{setting}' to block public access",
                        rule_id="s3_public_access_enabled",
                        affected_resources=[f"{resource.type}.{resource.name}"]
                    ))
        
        return issues
    
    def check_encryption_settings(self, resources: List[Resource]) -> List[SecurityIssue]:
        """
        Check encryption configurations for data at rest and in transit.
        
        Args:
            resources: List of resources to analyze
            
        Returns:
            List of SecurityIssue objects for encryption violations
        """
        issues = []
        
        for resource in resources:
            try:
                # Check storage encryption
                if resource.type in ['aws_s3_bucket', 'aws_ebs_volume']:
                    issues.extend(self._check_storage_encryption(resource))
                
                # Check database encryption
                elif resource.type in ['aws_rds_instance', 'aws_rds_cluster', 'azurerm_sql_database']:
                    issues.extend(self._check_database_encryption(resource))
                
                # Check load balancer encryption
                elif resource.type in ['aws_lb_listener', 'aws_alb_listener']:
                    issues.extend(self._check_load_balancer_encryption(resource))
                
            except Exception as e:
                self.handle_error(e, f"checking encryption for {resource.type}.{resource.name}")
        
        return issues
    
    def _check_storage_encryption(self, resource: Resource) -> List[SecurityIssue]:
        """Check storage resources for encryption settings."""
        issues = []
        config = resource.configuration
        
        if resource.type == 'aws_s3_bucket':
            # Check for server-side encryption
            encryption = config.get('server_side_encryption_configuration', {})
            if not encryption:
                issues.append(SecurityIssue(
                    severity=Severity.HIGH,
                    category=Category.ENCRYPTION,
                    description=f"S3 bucket {resource.name} does not have server-side encryption configured",
                    file_path="",
                    line_number=resource.line_number,
                    recommendation="Enable server-side encryption for S3 bucket",
                    rule_id="s3_encryption_missing",
                    affected_resources=[f"{resource.type}.{resource.name}"]
                ))
        
        elif resource.type == 'aws_ebs_volume':
            # Check for EBS encryption
            encrypted = config.get('encrypted', False)
            if not encrypted:
                issues.append(SecurityIssue(
                    severity=Severity.HIGH,
                    category=Category.ENCRYPTION,
                    description=f"EBS volume {resource.name} is not encrypted",
                    file_path="",
                    line_number=resource.line_number,
                    recommendation="Enable encryption for EBS volume",
                    rule_id="ebs_encryption_missing",
                    affected_resources=[f"{resource.type}.{resource.name}"]
                ))
        
        return issues
    
    def _check_database_encryption(self, resource: Resource) -> List[SecurityIssue]:
        """Check database resources for encryption settings."""
        issues = []
        config = resource.configuration
        
        if resource.type in ['aws_rds_instance', 'aws_rds_cluster']:
            # Check for storage encryption
            storage_encrypted = config.get('storage_encrypted', False)
            if storage_encrypted is False:  # Explicitly check for False
                issues.append(SecurityIssue(
                    severity=Severity.HIGH,
                    category=Category.ENCRYPTION,
                    description=f"RDS {resource.name} does not have storage encryption enabled",
                    file_path="",
                    line_number=resource.line_number,
                    recommendation="Enable storage encryption for RDS instance",
                    rule_id="rds_storage_encryption_missing",
                    affected_resources=[f"{resource.type}.{resource.name}"]
                ))
        
        return issues
    
    def _check_load_balancer_encryption(self, resource: Resource) -> List[SecurityIssue]:
        """Check load balancer listeners for encryption settings."""
        issues = []
        config = resource.configuration
        
        protocol = config.get('protocol', '').upper()
        port = config.get('port', 0)
        
        # Check for HTTP instead of HTTPS
        if protocol == 'HTTP' or port == 80:
            issues.append(SecurityIssue(
                severity=Severity.MEDIUM,
                category=Category.ENCRYPTION,
                description=f"Load balancer listener {resource.name} uses HTTP instead of HTTPS",
                file_path="",
                line_number=resource.line_number,
                recommendation="Use HTTPS protocol for load balancer listeners",
                rule_id="lb_http_listener",
                affected_resources=[f"{resource.type}.{resource.name}"]
            ))
        
        return issues
    
    def analyze_network_security(self, resources: List[Resource]) -> List[SecurityIssue]:
        """
        Analyze network security configurations for public access and insecure protocols.
        
        Args:
            resources: List of resources to analyze
            
        Returns:
            List of SecurityIssue objects for network security violations
        """
        issues = []
        
        for resource in resources:
            try:
                # Check for public IP assignments
                if resource.type in ['aws_instance', 'aws_eip']:
                    issues.extend(self._check_public_ip(resource))
                
                # Check for insecure protocols
                if resource.type in ['aws_lb_listener', 'aws_alb_listener']:
                    issues.extend(self._check_insecure_protocols(resource))
                
                # Check VPC configurations
                elif resource.type in ['aws_vpc', 'aws_subnet']:
                    issues.extend(self._check_vpc_security(resource))
                
            except Exception as e:
                self.handle_error(e, f"analyzing network security for {resource.type}.{resource.name}")
        
        return issues
    
    def _check_public_ip(self, resource: Resource) -> List[SecurityIssue]:
        """Check for public IP assignments."""
        issues = []
        config = resource.configuration
        
        if resource.type == 'aws_instance':
            associate_public_ip = config.get('associate_public_ip_address', False)
            if associate_public_ip:
                issues.append(SecurityIssue(
                    severity=Severity.MEDIUM,
                    category=Category.NETWORK,
                    description=f"EC2 instance {resource.name} has public IP address assigned",
                    file_path="",
                    line_number=resource.line_number,
                    recommendation="Consider using private subnets and NAT gateway for outbound access",
                    rule_id="ec2_public_ip",
                    affected_resources=[f"{resource.type}.{resource.name}"]
                ))
        
        return issues
    
    def _check_insecure_protocols(self, resource: Resource) -> List[SecurityIssue]:
        """Check for insecure protocol usage."""
        issues = []
        config = resource.configuration
        
        protocol = config.get('protocol', '').lower()
        if protocol in self.INSECURE_PROTOCOLS:
            issues.append(SecurityIssue(
                severity=Severity.HIGH,
                category=Category.NETWORK,
                description=f"Load balancer listener {resource.name} uses insecure protocol {protocol}",
                file_path="",
                line_number=resource.line_number,
                recommendation=f"Use secure alternative to {protocol} protocol",
                rule_id="insecure_protocol",
                affected_resources=[f"{resource.type}.{resource.name}"]
            ))
        
        return issues
    
    def _check_vpc_security(self, resource: Resource) -> List[SecurityIssue]:
        """Check VPC security configurations."""
        issues = []
        config = resource.configuration
        
        if resource.type == 'aws_vpc':
            # Check for DNS hostnames and resolution
            enable_dns_hostnames = config.get('enable_dns_hostnames', False)
            enable_dns_support = config.get('enable_dns_support', True)
            
            if not enable_dns_support:
                issues.append(SecurityIssue(
                    severity=Severity.LOW,
                    category=Category.NETWORK,
                    description=f"VPC {resource.name} has DNS support disabled",
                    file_path="",
                    line_number=resource.line_number,
                    recommendation="Enable DNS support for proper name resolution",
                    rule_id="vpc_dns_support_disabled",
                    affected_resources=[f"{resource.type}.{resource.name}"]
                ))
        
        return issues
    
    def validate_multicloud_security(self, resources: List[Resource], cloud_provider: str) -> List[SecurityIssue]:
        """
        Perform cloud provider-specific security validation.
        
        Args:
            resources: List of resources to analyze
            cloud_provider: Cloud provider identifier (aws, azure, gcp, etc.)
            
        Returns:
            List of SecurityIssue objects for cloud-specific violations
        """
        issues = []
        
        try:
            if cloud_provider.lower() == 'aws':
                issues.extend(self._validate_aws_security(resources))
            elif cloud_provider.lower() == 'azure':
                issues.extend(self._validate_azure_security(resources))
            elif cloud_provider.lower() == 'gcp':
                issues.extend(self._validate_gcp_security(resources))
            elif cloud_provider.lower() == 'ibm':
                issues.extend(self._validate_ibm_security(resources))
            elif cloud_provider.lower() == 'oci':
                issues.extend(self._validate_oci_security(resources))
            elif cloud_provider.lower() == 'alicloud':
                issues.extend(self._validate_alicloud_security(resources))
            elif cloud_provider.lower() == 'openstack':
                issues.extend(self._validate_openstack_security(resources))
        except Exception as e:
            self.handle_error(e, f"validating {cloud_provider} security")
        
        return issues
    
    def _validate_aws_security(self, resources: List[Resource]) -> List[SecurityIssue]:
        """Validate AWS-specific security configurations."""
        issues = []
        
        for resource in resources:
            try:
                # EC2 Security Checks
                if resource.type == 'aws_instance':
                    issues.extend(self._check_aws_ec2_security(resource))
                
                # VPC Security Checks
                elif resource.type in ['aws_vpc', 'aws_subnet', 'aws_route_table']:
                    issues.extend(self._check_aws_vpc_security(resource))
                
                # Security Group Checks (enhanced)
                elif resource.type in ['aws_security_group', 'aws_security_group_rule']:
                    issues.extend(self._check_aws_security_group_enhanced(resource))
                
                # IAM Security Checks (enhanced)
                elif resource.type in ['aws_iam_role', 'aws_iam_policy', 'aws_iam_user', 'aws_iam_group']:
                    issues.extend(self._check_aws_iam_security(resource))
                
                # S3 Security Checks
                elif resource.type.startswith('aws_s3_'):
                    issues.extend(self._check_aws_s3_security(resource))
                
                # RDS Security Checks
                elif resource.type.startswith('aws_rds_') or resource.type.startswith('aws_db_'):
                    issues.extend(self._check_aws_rds_security(resource))
                
                # ELB/ALB Security Checks
                elif resource.type in ['aws_lb', 'aws_alb', 'aws_elb']:
                    issues.extend(self._check_aws_lb_security(resource))
                
                # CloudTrail Security Checks
                elif resource.type == 'aws_cloudtrail':
                    issues.extend(self._check_aws_cloudtrail_security(resource))
                
            except Exception as e:
                self.handle_error(e, f"validating AWS resource {resource.type}.{resource.name}")
        
        return issues
    
    def _validate_azure_security(self, resources: List[Resource]) -> List[SecurityIssue]:
        """Validate Azure-specific security configurations."""
        issues = []
        
        for resource in resources:
            try:
                # Resource Group Security
                if resource.type == 'azurerm_resource_group':
                    issues.extend(self._check_azure_resource_group_security(resource))
                
                # Virtual Network Security
                elif resource.type in ['azurerm_virtual_network', 'azurerm_subnet']:
                    issues.extend(self._check_azure_network_security(resource))
                
                # Virtual Machine Security
                elif resource.type == 'azurerm_virtual_machine' or resource.type == 'azurerm_linux_virtual_machine':
                    issues.extend(self._check_azure_vm_security(resource))
                
                # Network Security Group Checks
                elif resource.type in ['azurerm_network_security_group', 'azurerm_network_security_rule']:
                    issues.extend(self._check_azure_nsg_security(resource))
                
                # Storage Account Security
                elif resource.type == 'azurerm_storage_account':
                    issues.extend(self._check_azure_storage_security(resource))
                
                # Key Vault Security
                elif resource.type == 'azurerm_key_vault':
                    issues.extend(self._check_azure_keyvault_security(resource))
                
                # SQL Database Security
                elif resource.type.startswith('azurerm_sql_') or resource.type.startswith('azurerm_mssql_'):
                    issues.extend(self._check_azure_sql_security(resource))
                
            except Exception as e:
                self.handle_error(e, f"validating Azure resource {resource.type}.{resource.name}")
        
        return issues
    
    def _validate_gcp_security(self, resources: List[Resource]) -> List[SecurityIssue]:
        """Validate GCP-specific security configurations."""
        issues = []
        
        for resource in resources:
            try:
                # Compute Instance Security
                if resource.type == 'google_compute_instance':
                    issues.extend(self._check_gcp_compute_security(resource))
                
                # Network Security
                elif resource.type in ['google_compute_network', 'google_compute_subnetwork']:
                    issues.extend(self._check_gcp_network_security(resource))
                
                # Firewall Rules Security (enhanced)
                elif resource.type == 'google_compute_firewall':
                    issues.extend(self._check_gcp_firewall_security(resource))
                
                # IAM Security
                elif resource.type.startswith('google_project_iam_') or resource.type.startswith('google_service_account'):
                    issues.extend(self._check_gcp_iam_security(resource))
                
                # Cloud Storage Security
                elif resource.type.startswith('google_storage_'):
                    issues.extend(self._check_gcp_storage_security(resource))
                
                # Cloud SQL Security
                elif resource.type.startswith('google_sql_'):
                    issues.extend(self._check_gcp_sql_security(resource))
                
            except Exception as e:
                self.handle_error(e, f"validating GCP resource {resource.type}.{resource.name}")
        
        return issues
    
    def _validate_ibm_security(self, resources: List[Resource]) -> List[SecurityIssue]:
        """Validate IBM Cloud-specific security configurations."""
        issues = []
        
        for resource in resources:
            try:
                # Virtual Server Instance Security
                if resource.type == 'ibm_is_instance':
                    issues.extend(self._check_ibm_vsi_security(resource))
                
                # VPC Security
                elif resource.type in ['ibm_is_vpc', 'ibm_is_subnet']:
                    issues.extend(self._check_ibm_vpc_security(resource))
                
                # Security Group Security
                elif resource.type in ['ibm_is_security_group', 'ibm_is_security_group_rule']:
                    issues.extend(self._check_ibm_security_group_security(resource))
                
                # Cloud Object Storage Security
                elif resource.type.startswith('ibm_cos_'):
                    issues.extend(self._check_ibm_cos_security(resource))
                
            except Exception as e:
                self.handle_error(e, f"validating IBM resource {resource.type}.{resource.name}")
        
        return issues
    
    def _validate_oci_security(self, resources: List[Resource]) -> List[SecurityIssue]:
        """Validate Oracle Cloud Infrastructure-specific security configurations."""
        issues = []
        
        for resource in resources:
            try:
                # Compute Instance Security
                if resource.type == 'oci_core_instance':
                    issues.extend(self._check_oci_compute_security(resource))
                
                # VCN Security
                elif resource.type in ['oci_core_vcn', 'oci_core_subnet']:
                    issues.extend(self._check_oci_vcn_security(resource))
                
                # Security List Security
                elif resource.type in ['oci_core_security_list', 'oci_core_network_security_group']:
                    issues.extend(self._check_oci_security_list_security(resource))
                
                # Object Storage Security
                elif resource.type.startswith('oci_objectstorage_'):
                    issues.extend(self._check_oci_storage_security(resource))
                
            except Exception as e:
                self.handle_error(e, f"validating OCI resource {resource.type}.{resource.name}")
        
        return issues
    
    def _validate_alicloud_security(self, resources: List[Resource]) -> List[SecurityIssue]:
        """Validate Alibaba Cloud-specific security configurations."""
        issues = []
        
        for resource in resources:
            try:
                # ECS Instance Security
                if resource.type == 'alicloud_instance':
                    issues.extend(self._check_alicloud_ecs_security(resource))
                
                # VPC Security
                elif resource.type in ['alicloud_vpc', 'alicloud_vswitch']:
                    issues.extend(self._check_alicloud_vpc_security(resource))
                
                # Security Group Security
                elif resource.type in ['alicloud_security_group', 'alicloud_security_group_rule']:
                    issues.extend(self._check_alicloud_security_group_security(resource))
                
                # OSS Security
                elif resource.type.startswith('alicloud_oss_'):
                    issues.extend(self._check_alicloud_oss_security(resource))
                
            except Exception as e:
                self.handle_error(e, f"validating AliCloud resource {resource.type}.{resource.name}")
        
        return issues
    
    def _validate_openstack_security(self, resources: List[Resource]) -> List[SecurityIssue]:
        """Validate OpenStack-specific security configurations."""
        issues = []
        
        for resource in resources:
            try:
                # Compute Instance Security
                if resource.type == 'openstack_compute_instance_v2':
                    issues.extend(self._check_openstack_compute_security(resource))
                
                # Network Security
                elif resource.type in ['openstack_networking_network_v2', 'openstack_networking_subnet_v2']:
                    issues.extend(self._check_openstack_network_security(resource))
                
                # Security Group Security
                elif resource.type in ['openstack_networking_secgroup_v2', 'openstack_networking_secgroup_rule_v2']:
                    issues.extend(self._check_openstack_secgroup_security(resource))
                
            except Exception as e:
                self.handle_error(e, f"validating OpenStack resource {resource.type}.{resource.name}")
        
        return issues
    
    def validate_multicloud_security(self, resources: List[Resource], cloud_provider: str) -> List[SecurityIssue]:
        """
        Perform cloud provider-specific security validation.
        
        Args:
            resources: List of resources to analyze
            cloud_provider: Cloud provider identifier (aws, azure, gcp, etc.)
            
        Returns:
            List of SecurityIssue objects for cloud-specific violations
        """
        issues = []
        
        try:
            if cloud_provider.lower() == 'aws':
                issues.extend(self._validate_aws_security(resources))
            elif cloud_provider.lower() == 'azure':
                issues.extend(self._validate_azure_security(resources))
            elif cloud_provider.lower() == 'gcp':
                issues.extend(self._validate_gcp_security(resources))
            elif cloud_provider.lower() == 'ibm':
                issues.extend(self._validate_ibm_security(resources))
            elif cloud_provider.lower() == 'oci':
                issues.extend(self._validate_oci_security(resources))
            elif cloud_provider.lower() == 'alicloud':
                issues.extend(self._validate_alicloud_security(resources))
            elif cloud_provider.lower() == 'openstack':
                issues.extend(self._validate_openstack_security(resources))
        except Exception as e:
            self.handle_error(e, f"validating {cloud_provider} security")
        
        return issues
    
    def _validate_aws_security(self, resources: List[Resource]) -> List[SecurityIssue]:
        """Validate AWS-specific security configurations."""
        issues = []
        
        for resource in resources:
            try:
                # EC2 Security Checks
                if resource.type == 'aws_instance':
                    issues.extend(self._check_aws_ec2_security(resource))
                
                # VPC Security Checks
                elif resource.type in ['aws_vpc', 'aws_subnet', 'aws_route_table']:
                    issues.extend(self._check_aws_vpc_security(resource))
                
                # Security Group Checks (enhanced)
                elif resource.type in ['aws_security_group', 'aws_security_group_rule']:
                    issues.extend(self._check_aws_security_group_enhanced(resource))
                
                # IAM Security Checks (enhanced)
                elif resource.type in ['aws_iam_role', 'aws_iam_policy', 'aws_iam_user', 'aws_iam_group']:
                    issues.extend(self._check_aws_iam_security(resource))
                
                # S3 Security Checks
                elif resource.type.startswith('aws_s3_'):
                    issues.extend(self._check_aws_s3_security(resource))
                
                # RDS Security Checks
                elif resource.type.startswith('aws_rds_') or resource.type.startswith('aws_db_'):
                    issues.extend(self._check_aws_rds_security(resource))
                
                # ELB/ALB Security Checks
                elif resource.type in ['aws_lb', 'aws_alb', 'aws_elb']:
                    issues.extend(self._check_aws_lb_security(resource))
                
                # CloudTrail Security Checks
                elif resource.type == 'aws_cloudtrail':
                    issues.extend(self._check_aws_cloudtrail_security(resource))
                
            except Exception as e:
                self.handle_error(e, f"validating AWS resource {resource.type}.{resource.name}")
        
        return issues
    
    def _validate_azure_security(self, resources: List[Resource]) -> List[SecurityIssue]:
        """Validate Azure-specific security configurations."""
        issues = []
        
        for resource in resources:
            try:
                # Resource Group Security
                if resource.type == 'azurerm_resource_group':
                    issues.extend(self._check_azure_resource_group_security(resource))
                
                # Virtual Network Security
                elif resource.type in ['azurerm_virtual_network', 'azurerm_subnet']:
                    issues.extend(self._check_azure_network_security(resource))
                
                # Virtual Machine Security
                elif resource.type == 'azurerm_virtual_machine' or resource.type == 'azurerm_linux_virtual_machine':
                    issues.extend(self._check_azure_vm_security(resource))
                
                # Network Security Group Checks
                elif resource.type in ['azurerm_network_security_group', 'azurerm_network_security_rule']:
                    issues.extend(self._check_azure_nsg_security(resource))
                
                # Storage Account Security
                elif resource.type == 'azurerm_storage_account':
                    issues.extend(self._check_azure_storage_security(resource))
                
                # Key Vault Security
                elif resource.type == 'azurerm_key_vault':
                    issues.extend(self._check_azure_keyvault_security(resource))
                
                # SQL Database Security
                elif resource.type.startswith('azurerm_sql_') or resource.type.startswith('azurerm_mssql_'):
                    issues.extend(self._check_azure_sql_security(resource))
                
            except Exception as e:
                self.handle_error(e, f"validating Azure resource {resource.type}.{resource.name}")
        
        return issues
    
    def _validate_gcp_security(self, resources: List[Resource]) -> List[SecurityIssue]:
        """Validate GCP-specific security configurations."""
        issues = []
        
        for resource in resources:
            try:
                # Compute Instance Security
                if resource.type == 'google_compute_instance':
                    issues.extend(self._check_gcp_compute_security(resource))
                
                # Network Security
                elif resource.type in ['google_compute_network', 'google_compute_subnetwork']:
                    issues.extend(self._check_gcp_network_security(resource))
                
                # Firewall Rules Security (enhanced)
                elif resource.type == 'google_compute_firewall':
                    issues.extend(self._check_gcp_firewall_security(resource))
                
                # IAM Security
                elif resource.type.startswith('google_project_iam_') or resource.type.startswith('google_service_account'):
                    issues.extend(self._check_gcp_iam_security(resource))
                
                # Cloud Storage Security
                elif resource.type.startswith('google_storage_'):
                    issues.extend(self._check_gcp_storage_security(resource))
                
                # Cloud SQL Security
                elif resource.type.startswith('google_sql_'):
                    issues.extend(self._check_gcp_sql_security(resource))
                
            except Exception as e:
                self.handle_error(e, f"validating GCP resource {resource.type}.{resource.name}")
        
        return issues
    
    def _validate_ibm_security(self, resources: List[Resource]) -> List[SecurityIssue]:
        """Validate IBM Cloud-specific security configurations."""
        issues = []
        
        for resource in resources:
            try:
                # Virtual Server Instance Security
                if resource.type == 'ibm_is_instance':
                    issues.extend(self._check_ibm_vsi_security(resource))
                
                # VPC Security
                elif resource.type in ['ibm_is_vpc', 'ibm_is_subnet']:
                    issues.extend(self._check_ibm_vpc_security(resource))
                
                # Security Group Security
                elif resource.type in ['ibm_is_security_group', 'ibm_is_security_group_rule']:
                    issues.extend(self._check_ibm_security_group_security(resource))
                
                # Cloud Object Storage Security
                elif resource.type.startswith('ibm_cos_'):
                    issues.extend(self._check_ibm_cos_security(resource))
                
            except Exception as e:
                self.handle_error(e, f"validating IBM resource {resource.type}.{resource.name}")
        
        return issues
    
    def _validate_oci_security(self, resources: List[Resource]) -> List[SecurityIssue]:
        """Validate Oracle Cloud Infrastructure-specific security configurations."""
        issues = []
        
        for resource in resources:
            try:
                # Compute Instance Security
                if resource.type == 'oci_core_instance':
                    issues.extend(self._check_oci_compute_security(resource))
                
                # VCN Security
                elif resource.type in ['oci_core_vcn', 'oci_core_subnet']:
                    issues.extend(self._check_oci_vcn_security(resource))
                
                # Security List Security
                elif resource.type in ['oci_core_security_list', 'oci_core_network_security_group']:
                    issues.extend(self._check_oci_security_list_security(resource))
                
                # Object Storage Security
                elif resource.type.startswith('oci_objectstorage_'):
                    issues.extend(self._check_oci_storage_security(resource))
                
            except Exception as e:
                self.handle_error(e, f"validating OCI resource {resource.type}.{resource.name}")
        
        return issues
    
    def _validate_alicloud_security(self, resources: List[Resource]) -> List[SecurityIssue]:
        """Validate Alibaba Cloud-specific security configurations."""
        issues = []
        
        for resource in resources:
            try:
                # ECS Instance Security
                if resource.type == 'alicloud_instance':
                    issues.extend(self._check_alicloud_ecs_security(resource))
                
                # VPC Security
                elif resource.type in ['alicloud_vpc', 'alicloud_vswitch']:
                    issues.extend(self._check_alicloud_vpc_security(resource))
                
                # Security Group Security
                elif resource.type in ['alicloud_security_group', 'alicloud_security_group_rule']:
                    issues.extend(self._check_alicloud_security_group_security(resource))
                
                # OSS Security
                elif resource.type.startswith('alicloud_oss_'):
                    issues.extend(self._check_alicloud_oss_security(resource))
                
            except Exception as e:
                self.handle_error(e, f"validating AliCloud resource {resource.type}.{resource.name}")
        
        return issues
    
    def _validate_openstack_security(self, resources: List[Resource]) -> List[SecurityIssue]:
        """Validate OpenStack-specific security configurations."""
        issues = []
        
        for resource in resources:
            try:
                # Compute Instance Security
                if resource.type == 'openstack_compute_instance_v2':
                    issues.extend(self._check_openstack_compute_security(resource))
                
                # Network Security
                elif resource.type in ['openstack_networking_network_v2', 'openstack_networking_subnet_v2']:
                    issues.extend(self._check_openstack_network_security(resource))
                
                # Security Group Security
                elif resource.type in ['openstack_networking_secgroup_v2', 'openstack_networking_secgroup_rule_v2']:
                    issues.extend(self._check_openstack_secgroup_security(resource))
                
            except Exception as e:
                self.handle_error(e, f"validating OpenStack resource {resource.type}.{resource.name}")
        
        return issues
    
    def check_cross_cloud_consistency(self, terraform_files: List[TerraformFile]) -> List[SecurityIssue]:
        """
        Check for security consistency across different cloud providers.
        
        Args:
            terraform_files: List of all Terraform files to analyze
            
        Returns:
            List of SecurityIssue objects for cross-cloud inconsistencies
        """
        issues = []
        
        try:
            # Group files by cloud provider
            cloud_configs = {}
            for tf_file in terraform_files:
                provider = tf_file.cloud_provider.lower()
                if provider not in cloud_configs:
                    cloud_configs[provider] = []
                cloud_configs[provider].append(tf_file)
            
            # Check for inconsistent security patterns across providers
            if len(cloud_configs) > 1:
                issues.extend(self._check_encryption_consistency(cloud_configs))
                issues.extend(self._check_network_security_consistency(cloud_configs))
                issues.extend(self._check_access_control_consistency(cloud_configs))
                issues.extend(self._check_monitoring_consistency(cloud_configs))
        
        except Exception as e:
            self.handle_error(e, "checking cross-cloud consistency")
        
        return issues
    
    def _check_encryption_consistency(self, cloud_configs: Dict[str, List[TerraformFile]]) -> List[SecurityIssue]:
        """Check encryption consistency across cloud providers."""
        issues = []
        
        encryption_status = {}
        
        for provider, files in cloud_configs.items():
            encryption_enabled = False
            for tf_file in files:
                for resource in tf_file.resources:
                    # Check for encryption-related configurations
                    if self._has_encryption_config(resource):
                        encryption_enabled = True
                        break
                if encryption_enabled:
                    break
            encryption_status[provider] = encryption_enabled
        
        # Check if some providers have encryption while others don't
        providers_with_encryption = [p for p, enabled in encryption_status.items() if enabled]
        providers_without_encryption = [p for p, enabled in encryption_status.items() if not enabled]
        
        if providers_with_encryption and providers_without_encryption:
            issues.append(SecurityIssue(
                severity=Severity.MEDIUM,
                category=Category.ENCRYPTION,
                description=f"Inconsistent encryption configuration across cloud providers. "
                           f"Enabled in: {', '.join(providers_with_encryption)}. "
                           f"Missing in: {', '.join(providers_without_encryption)}",
                file_path="",
                line_number=0,
                recommendation="Ensure consistent encryption policies across all cloud providers",
                rule_id="cross_cloud_encryption_inconsistency",
                affected_resources=[]
            ))
        
        return issues
    
    def _check_network_security_consistency(self, cloud_configs: Dict[str, List[TerraformFile]]) -> List[SecurityIssue]:
        """Check network security consistency across cloud providers."""
        issues = []
        
        # Check for consistent firewall/security group configurations
        permissive_providers = []
        
        for provider, files in cloud_configs.items():
            has_permissive_rules = False
            for tf_file in files:
                for resource in tf_file.resources:
                    if self._has_permissive_network_rules(resource):
                        has_permissive_rules = True
                        break
                if has_permissive_rules:
                    break
            
            if has_permissive_rules:
                permissive_providers.append(provider)
        
        if permissive_providers and len(permissive_providers) != len(cloud_configs):
            issues.append(SecurityIssue(
                severity=Severity.HIGH,
                category=Category.NETWORK,
                description=f"Inconsistent network security policies. "
                           f"Permissive rules found in: {', '.join(permissive_providers)}",
                file_path="",
                line_number=0,
                recommendation="Review and standardize network security rules across all cloud providers",
                rule_id="cross_cloud_network_inconsistency",
                affected_resources=[]
            ))
        
        return issues
    
    def _check_access_control_consistency(self, cloud_configs: Dict[str, List[TerraformFile]]) -> List[SecurityIssue]:
        """Check access control consistency across cloud providers."""
        issues = []
        
        # Check for consistent IAM/access control patterns
        # This is a simplified check - in practice, this would be more sophisticated
        
        return issues
    
    def _check_monitoring_consistency(self, cloud_configs: Dict[str, List[TerraformFile]]) -> List[SecurityIssue]:
        """Check monitoring and logging consistency across cloud providers."""
        issues = []
        
        monitoring_status = {}
        
        for provider, files in cloud_configs.items():
            has_monitoring = False
            for tf_file in files:
                for resource in tf_file.resources:
                    if self._has_monitoring_config(resource):
                        has_monitoring = True
                        break
                if has_monitoring:
                    break
            monitoring_status[provider] = has_monitoring
        
        providers_with_monitoring = [p for p, enabled in monitoring_status.items() if enabled]
        providers_without_monitoring = [p for p, enabled in monitoring_status.items() if not enabled]
        
        if providers_with_monitoring and providers_without_monitoring:
            issues.append(SecurityIssue(
                severity=Severity.MEDIUM,
                category=Category.SECURITY,
                description=f"Inconsistent monitoring configuration across cloud providers. "
                           f"Enabled in: {', '.join(providers_with_monitoring)}. "
                           f"Missing in: {', '.join(providers_without_monitoring)}",
                file_path="",
                line_number=0,
                recommendation="Implement consistent monitoring and logging across all cloud providers",
                rule_id="cross_cloud_monitoring_inconsistency",
                affected_resources=[]
            ))
        
        return issues
    
    def _has_encryption_config(self, resource: Resource) -> bool:
        """Check if a resource has encryption configuration."""
        config = resource.configuration
        
        # Check for common encryption-related configuration keys
        encryption_keys = [
            'encrypted', 'encryption', 'server_side_encryption_configuration',
            'storage_encrypted', 'kms_key_id', 'encryption_key'
        ]
        
        for key in encryption_keys:
            if key in config and config[key]:
                return True
        
        return False
    
    def _has_permissive_network_rules(self, resource: Resource) -> bool:
        """Check if a resource has permissive network rules."""
        config = resource.configuration
        
        # Check for security group or firewall rules with permissive access
        if resource.type in ['aws_security_group', 'aws_security_group_rule']:
            ingress_rules = config.get('ingress', [])
            if not isinstance(ingress_rules, list):
                ingress_rules = [ingress_rules]
            
            for rule in ingress_rules:
                if isinstance(rule, dict):
                    cidr_blocks = rule.get('cidr_blocks', [])
                    if any(cidr in self.PERMISSIVE_CIDRS for cidr in cidr_blocks):
                        return True
        
        elif resource.type == 'google_compute_firewall':
            source_ranges = config.get('source_ranges', [])
            if any(cidr in self.PERMISSIVE_CIDRS for cidr in source_ranges):
                return True
        
        elif resource.type == 'azurerm_network_security_rule':
            source_address_prefix = config.get('source_address_prefix', '')
            if source_address_prefix in self.PERMISSIVE_CIDRS or source_address_prefix == '*':
                return True
        
        return False
    
    def _has_monitoring_config(self, resource: Resource) -> bool:
        """Check if a resource has monitoring configuration."""
        config = resource.configuration
        
        # Check for common monitoring-related configuration keys
        monitoring_keys = [
            'monitoring', 'logging', 'log_config', 'access_logs',
            'enable_log_file_validation', 'boot_diagnostics'
        ]
        
        for key in monitoring_keys:
            if key in config and config[key]:
                return True
        
        return False
    
    # AWS-specific security check implementations
    def _check_aws_ec2_security(self, resource: Resource) -> List[SecurityIssue]:
        """Check AWS EC2 instance security configurations."""
        issues = []
        config = resource.configuration
        
        # Check for IMDSv2 enforcement
        metadata_options = config.get('metadata_options', {})
        if isinstance(metadata_options, dict):
            http_tokens = metadata_options.get('http_tokens', 'optional')
            if http_tokens != 'required':
                issues.append(SecurityIssue(
                    severity=Severity.MEDIUM,
                    category=Category.SECURITY,
                    description=f"EC2 instance {resource.name} does not enforce IMDSv2",
                    file_path="",
                    line_number=resource.line_number,
                    recommendation="Set metadata_options.http_tokens to 'required' to enforce IMDSv2",
                    rule_id="ec2_imdsv2_not_enforced",
                    affected_resources=[f"{resource.type}.{resource.name}"]
                ))
        
        # Check for detailed monitoring
        monitoring = config.get('monitoring', False)
        if not monitoring:
            issues.append(SecurityIssue(
                severity=Severity.LOW,
                category=Category.SECURITY,
                description=f"EC2 instance {resource.name} does not have detailed monitoring enabled",
                file_path="",
                line_number=resource.line_number,
                recommendation="Enable detailed monitoring for better security visibility",
                rule_id="ec2_detailed_monitoring_disabled",
                affected_resources=[f"{resource.type}.{resource.name}"]
            ))
        
        return issues
    
    def _check_aws_vpc_security(self, resource: Resource) -> List[SecurityIssue]:
        """Check AWS VPC security configurations."""
        issues = []
        config = resource.configuration
        
        if resource.type == 'aws_vpc':
            # Check for flow logs
            # Note: This would need to be checked across all VPCs and flow log resources
            pass
        
        elif resource.type == 'aws_subnet':
            # Check for public subnet configurations
            map_public_ip = config.get('map_public_ip_on_launch', False)
            if map_public_ip:
                issues.append(SecurityIssue(
                    severity=Severity.MEDIUM,
                    category=Category.NETWORK,
                    description=f"Subnet {resource.name} automatically assigns public IPs",
                    file_path="",
                    line_number=resource.line_number,
                    recommendation="Consider using private subnets and NAT gateway for outbound access",
                    rule_id="subnet_auto_public_ip",
                    affected_resources=[f"{resource.type}.{resource.name}"]
                ))
        
        return issues
    
    def _check_aws_security_group_enhanced(self, resource: Resource) -> List[SecurityIssue]:
        """Enhanced AWS security group checks."""
        issues = []
        
        # Use existing security group checks and add more
        issues.extend(self._check_security_group(resource))
        
        config = resource.configuration
        
        # Check for unused security groups (would need cross-reference analysis)
        # Check for security group chaining
        ingress_rules = config.get('ingress', [])
        if not isinstance(ingress_rules, list):
            ingress_rules = [ingress_rules]
        
        for rule in ingress_rules:
            if isinstance(rule, dict):
                # Check for security group references in rules
                security_groups = rule.get('security_groups', [])
                if security_groups:
                    # This could indicate security group chaining which might be complex
                    pass
        
        return issues
    
    def _check_aws_iam_security(self, resource: Resource) -> List[SecurityIssue]:
        """Check AWS IAM security configurations."""
        issues = []
        config = resource.configuration
        
        if resource.type == 'aws_iam_role':
            # Check assume role policy
            assume_role_policy = config.get('assume_role_policy', '')
            if assume_role_policy and isinstance(assume_role_policy, str):
                if '*' in assume_role_policy:
                    issues.append(SecurityIssue(
                        severity=Severity.HIGH,
                        category=Category.ACCESS_CONTROL,
                        description=f"IAM role {resource.name} has overly permissive assume role policy",
                        file_path="",
                        line_number=resource.line_number,
                        recommendation="Restrict assume role policy to specific principals",
                        rule_id="iam_role_permissive_assume_policy",
                        affected_resources=[f"{resource.type}.{resource.name}"]
                    ))
        
        elif resource.type == 'aws_iam_user':
            # Check for programmatic access without MFA
            # This would need to be checked against MFA device resources
            pass
        
        return issues
    
    def _check_aws_s3_security(self, resource: Resource) -> List[SecurityIssue]:
        """Check AWS S3 security configurations."""
        issues = []
        config = resource.configuration
        
        if resource.type == 'aws_s3_bucket':
            # Check for versioning
            versioning = config.get('versioning', {})
            if isinstance(versioning, dict) and not versioning.get('enabled', False):
                issues.append(SecurityIssue(
                    severity=Severity.MEDIUM,
                    category=Category.SECURITY,
                    description=f"S3 bucket {resource.name} does not have versioning enabled",
                    file_path="",
                    line_number=resource.line_number,
                    recommendation="Enable versioning for data protection and recovery",
                    rule_id="s3_versioning_disabled",
                    affected_resources=[f"{resource.type}.{resource.name}"]
                ))
            
            # Check for logging
            logging = config.get('logging', {})
            if not logging:
                issues.append(SecurityIssue(
                    severity=Severity.LOW,
                    category=Category.SECURITY,
                    description=f"S3 bucket {resource.name} does not have access logging enabled",
                    file_path="",
                    line_number=resource.line_number,
                    recommendation="Enable access logging for audit trail",
                    rule_id="s3_access_logging_disabled",
                    affected_resources=[f"{resource.type}.{resource.name}"]
                ))
        
        return issues
    
    def _check_aws_rds_security(self, resource: Resource) -> List[SecurityIssue]:
        """Check AWS RDS security configurations."""
        issues = []
        config = resource.configuration
        
        # Check for backup retention
        backup_retention_period = config.get('backup_retention_period', 0)
        if backup_retention_period < 7:
            issues.append(SecurityIssue(
                severity=Severity.MEDIUM,
                category=Category.SECURITY,
                description=f"RDS {resource.name} has insufficient backup retention period",
                file_path="",
                line_number=resource.line_number,
                recommendation="Set backup retention period to at least 7 days",
                rule_id="rds_insufficient_backup_retention",
                affected_resources=[f"{resource.type}.{resource.name}"]
            ))
        
        # Check for multi-AZ deployment
        multi_az = config.get('multi_az', False)
        if not multi_az and resource.type == 'aws_rds_instance':
            issues.append(SecurityIssue(
                severity=Severity.LOW,
                category=Category.SECURITY,
                description=f"RDS {resource.name} is not configured for multi-AZ deployment",
                file_path="",
                line_number=resource.line_number,
                recommendation="Enable multi-AZ deployment for high availability",
                rule_id="rds_single_az_deployment",
                affected_resources=[f"{resource.type}.{resource.name}"]
            ))
        
        return issues
    
    def _check_aws_lb_security(self, resource: Resource) -> List[SecurityIssue]:
        """Check AWS Load Balancer security configurations."""
        issues = []
        config = resource.configuration
        
        # Check for access logs
        access_logs = config.get('access_logs', {})
        if isinstance(access_logs, dict) and not access_logs.get('enabled', False):
            issues.append(SecurityIssue(
                severity=Severity.LOW,
                category=Category.SECURITY,
                description=f"Load balancer {resource.name} does not have access logs enabled",
                file_path="",
                line_number=resource.line_number,
                recommendation="Enable access logs for audit trail",
                rule_id="lb_access_logs_disabled",
                affected_resources=[f"{resource.type}.{resource.name}"]
            ))
        
        # Check for deletion protection
        enable_deletion_protection = config.get('enable_deletion_protection', False)
        if not enable_deletion_protection:
            issues.append(SecurityIssue(
                severity=Severity.LOW,
                category=Category.SECURITY,
                description=f"Load balancer {resource.name} does not have deletion protection enabled",
                file_path="",
                line_number=resource.line_number,
                recommendation="Enable deletion protection to prevent accidental deletion",
                rule_id="lb_deletion_protection_disabled",
                affected_resources=[f"{resource.type}.{resource.name}"]
            ))
        
        return issues
    
    def _check_aws_cloudtrail_security(self, resource: Resource) -> List[SecurityIssue]:
        """Check AWS CloudTrail security configurations."""
        issues = []
        config = resource.configuration
        
        # Check for log file validation
        enable_log_file_validation = config.get('enable_log_file_validation', False)
        if not enable_log_file_validation:
            issues.append(SecurityIssue(
                severity=Severity.HIGH,
                category=Category.SECURITY,
                description=f"CloudTrail {resource.name} does not have log file validation enabled",
                file_path="",
                line_number=resource.line_number,
                recommendation="Enable log file validation to detect tampering",
                rule_id="cloudtrail_log_validation_disabled",
                affected_resources=[f"{resource.type}.{resource.name}"]
            ))
        
        # Check for KMS encryption
        kms_key_id = config.get('kms_key_id', '')
        if not kms_key_id:
            issues.append(SecurityIssue(
                severity=Severity.MEDIUM,
                category=Category.ENCRYPTION,
                description=f"CloudTrail {resource.name} does not use KMS encryption",
                file_path="",
                line_number=resource.line_number,
                recommendation="Enable KMS encryption for CloudTrail logs",
                rule_id="cloudtrail_kms_encryption_disabled",
                affected_resources=[f"{resource.type}.{resource.name}"]
            ))
        
        return issues
    
    # Azure-specific security check implementations
    def _check_azure_resource_group_security(self, resource: Resource) -> List[SecurityIssue]:
        """Check Azure Resource Group security configurations."""
        issues = []
        config = resource.configuration
        
        # Check for tags (governance)
        tags = config.get('tags', {})
        if not tags:
            issues.append(SecurityIssue(
                severity=Severity.LOW,
                category=Category.SECURITY,
                description=f"Resource group {resource.name} does not have tags for governance",
                file_path="",
                line_number=resource.line_number,
                recommendation="Add tags for resource governance and cost management",
                rule_id="azure_rg_no_tags",
                affected_resources=[f"{resource.type}.{resource.name}"]
            ))
        
        return issues
    
    def _check_azure_network_security(self, resource: Resource) -> List[SecurityIssue]:
        """Check Azure Virtual Network security configurations."""
        issues = []
        config = resource.configuration
        
        if resource.type == 'azurerm_virtual_network':
            # Check for DDoS protection
            ddos_protection_plan = config.get('ddos_protection_plan', {})
            if not ddos_protection_plan:
                issues.append(SecurityIssue(
                    severity=Severity.MEDIUM,
                    category=Category.NETWORK,
                    description=f"Virtual network {resource.name} does not have DDoS protection enabled",
                    file_path="",
                    line_number=resource.line_number,
                    recommendation="Enable DDoS protection for network security",
                    rule_id="azure_vnet_no_ddos_protection",
                    affected_resources=[f"{resource.type}.{resource.name}"]
                ))
        
        return issues
    
    def _check_azure_vm_security(self, resource: Resource) -> List[SecurityIssue]:
        """Check Azure Virtual Machine security configurations."""
        issues = []
        config = resource.configuration
        
        # Check for boot diagnostics
        boot_diagnostics = config.get('boot_diagnostics', {})
        if not boot_diagnostics:
            issues.append(SecurityIssue(
                severity=Severity.LOW,
                category=Category.SECURITY,
                description=f"VM {resource.name} does not have boot diagnostics enabled",
                file_path="",
                line_number=resource.line_number,
                recommendation="Enable boot diagnostics for troubleshooting",
                rule_id="azure_vm_no_boot_diagnostics",
                affected_resources=[f"{resource.type}.{resource.name}"]
            ))
        
        # Check for managed identity
        identity = config.get('identity', {})
        if not identity:
            issues.append(SecurityIssue(
                severity=Severity.MEDIUM,
                category=Category.ACCESS_CONTROL,
                description=f"VM {resource.name} does not have managed identity configured",
                file_path="",
                line_number=resource.line_number,
                recommendation="Configure managed identity for secure access to Azure resources",
                rule_id="azure_vm_no_managed_identity",
                affected_resources=[f"{resource.type}.{resource.name}"]
            ))
        
        return issues
    
    def _check_azure_nsg_security(self, resource: Resource) -> List[SecurityIssue]:
        """Check Azure Network Security Group configurations."""
        issues = []
        config = resource.configuration
        
        if resource.type == 'azurerm_network_security_rule':
            # Check for overly permissive rules
            source_address_prefix = config.get('source_address_prefix', '')
            destination_port_range = config.get('destination_port_range', '')
            access = config.get('access', '')
            
            if source_address_prefix in ['*', '0.0.0.0/0'] and access.lower() == 'allow':
                severity = Severity.CRITICAL if destination_port_range in ['22', '3389'] else Severity.HIGH
                issues.append(SecurityIssue(
                    severity=severity,
                    category=Category.ACCESS_CONTROL,
                    description=f"NSG rule {resource.name} allows access from any source",
                    file_path="",
                    line_number=resource.line_number,
                    recommendation="Restrict source address prefix to specific IP ranges",
                    rule_id="azure_nsg_overly_permissive",
                    affected_resources=[f"{resource.type}.{resource.name}"]
                ))
        
        return issues
    
    def _check_azure_storage_security(self, resource: Resource) -> List[SecurityIssue]:
        """Check Azure Storage Account security configurations."""
        issues = []
        config = resource.configuration
        
        # Check for HTTPS only
        enable_https_traffic_only = config.get('enable_https_traffic_only', False)
        if not enable_https_traffic_only:
            issues.append(SecurityIssue(
                severity=Severity.HIGH,
                category=Category.ENCRYPTION,
                description=f"Storage account {resource.name} does not enforce HTTPS only",
                file_path="",
                line_number=resource.line_number,
                recommendation="Enable HTTPS only traffic for storage account",
                rule_id="azure_storage_https_not_enforced",
                affected_resources=[f"{resource.type}.{resource.name}"]
            ))
        
        # Check for minimum TLS version
        min_tls_version = config.get('min_tls_version', '')
        if min_tls_version != 'TLS1_2':
            issues.append(SecurityIssue(
                severity=Severity.MEDIUM,
                category=Category.ENCRYPTION,
                description=f"Storage account {resource.name} does not enforce minimum TLS 1.2",
                file_path="",
                line_number=resource.line_number,
                recommendation="Set minimum TLS version to TLS1_2",
                rule_id="azure_storage_weak_tls",
                affected_resources=[f"{resource.type}.{resource.name}"]
            ))
        
        return issues
    
    def _check_azure_keyvault_security(self, resource: Resource) -> List[SecurityIssue]:
        """Check Azure Key Vault security configurations."""
        issues = []
        config = resource.configuration
        
        # Check for soft delete
        soft_delete_enabled = config.get('soft_delete_enabled', False)
        if not soft_delete_enabled:
            issues.append(SecurityIssue(
                severity=Severity.MEDIUM,
                category=Category.SECURITY,
                description=f"Key Vault {resource.name} does not have soft delete enabled",
                file_path="",
                line_number=resource.line_number,
                recommendation="Enable soft delete for Key Vault protection",
                rule_id="azure_keyvault_no_soft_delete",
                affected_resources=[f"{resource.type}.{resource.name}"]
            ))
        
        # Check for purge protection
        purge_protection_enabled = config.get('purge_protection_enabled', False)
        if not purge_protection_enabled:
            issues.append(SecurityIssue(
                severity=Severity.HIGH,
                category=Category.SECURITY,
                description=f"Key Vault {resource.name} does not have purge protection enabled",
                file_path="",
                line_number=resource.line_number,
                recommendation="Enable purge protection for Key Vault",
                rule_id="azure_keyvault_no_purge_protection",
                affected_resources=[f"{resource.type}.{resource.name}"]
            ))
        
        return issues
    
    def _check_azure_sql_security(self, resource: Resource) -> List[SecurityIssue]:
        """Check Azure SQL security configurations."""
        issues = []
        config = resource.configuration
        
        # Check for threat detection
        threat_detection_policy = config.get('threat_detection_policy', {})
        if not threat_detection_policy or not threat_detection_policy.get('state', '').lower() == 'enabled':
            issues.append(SecurityIssue(
                severity=Severity.MEDIUM,
                category=Category.SECURITY,
                description=f"SQL database {resource.name} does not have threat detection enabled",
                file_path="",
                line_number=resource.line_number,
                recommendation="Enable threat detection for SQL database",
                rule_id="azure_sql_no_threat_detection",
                affected_resources=[f"{resource.type}.{resource.name}"]
            ))
        
        return issues
    
    # GCP-specific security check implementations
    def _check_gcp_compute_security(self, resource: Resource) -> List[SecurityIssue]:
        """Check GCP Compute Instance security configurations."""
        issues = []
        config = resource.configuration
        
        # Check for OS Login
        metadata = config.get('metadata', {})
        enable_oslogin = metadata.get('enable-oslogin', 'false')
        if enable_oslogin.lower() != 'true':
            issues.append(SecurityIssue(
                severity=Severity.MEDIUM,
                category=Category.ACCESS_CONTROL,
                description=f"Compute instance {resource.name} does not have OS Login enabled",
                file_path="",
                line_number=resource.line_number,
                recommendation="Enable OS Login for centralized SSH key management",
                rule_id="gcp_compute_no_oslogin",
                affected_resources=[f"{resource.type}.{resource.name}"]
            ))
        
        # Check for serial port access
        enable_serial_port = metadata.get('serial-port-enable', 'false')
        if enable_serial_port.lower() == 'true':
            issues.append(SecurityIssue(
                severity=Severity.MEDIUM,
                category=Category.ACCESS_CONTROL,
                description=f"Compute instance {resource.name} has serial port access enabled",
                file_path="",
                line_number=resource.line_number,
                recommendation="Disable serial port access unless required",
                rule_id="gcp_compute_serial_port_enabled",
                affected_resources=[f"{resource.type}.{resource.name}"]
            ))
        
        return issues
    
    def _check_gcp_network_security(self, resource: Resource) -> List[SecurityIssue]:
        """Check GCP Network security configurations."""
        issues = []
        config = resource.configuration
        
        if resource.type == 'google_compute_network':
            # Check for auto create subnetworks
            auto_create_subnetworks = config.get('auto_create_subnetworks', True)
            if auto_create_subnetworks:
                issues.append(SecurityIssue(
                    severity=Severity.LOW,
                    category=Category.NETWORK,
                    description=f"Network {resource.name} has auto create subnetworks enabled",
                    file_path="",
                    line_number=resource.line_number,
                    recommendation="Disable auto create subnetworks for better network control",
                    rule_id="gcp_network_auto_subnets",
                    affected_resources=[f"{resource.type}.{resource.name}"]
                ))
        
        return issues
    
    def _check_gcp_firewall_security(self, resource: Resource) -> List[SecurityIssue]:
        """Check GCP Firewall security configurations."""
        issues = []
        
        # Use existing firewall checks and add GCP-specific ones
        issues.extend(self._check_firewall_rule(resource))
        
        config = resource.configuration
        
        # Check for logging
        log_config = config.get('log_config', {})
        if not log_config or not log_config.get('enable', False):
            issues.append(SecurityIssue(
                severity=Severity.LOW,
                category=Category.SECURITY,
                description=f"Firewall rule {resource.name} does not have logging enabled",
                file_path="",
                line_number=resource.line_number,
                recommendation="Enable logging for firewall rules for audit trail",
                rule_id="gcp_firewall_no_logging",
                affected_resources=[f"{resource.type}.{resource.name}"]
            ))
        
        return issues
    
    def _check_gcp_iam_security(self, resource: Resource) -> List[SecurityIssue]:
        """Check GCP IAM security configurations."""
        issues = []
        config = resource.configuration
        
        if resource.type.startswith('google_project_iam_'):
            # Check for overly broad roles
            role = config.get('role', '')
            if role in ['roles/owner', 'roles/editor']:
                issues.append(SecurityIssue(
                    severity=Severity.HIGH,
                    category=Category.ACCESS_CONTROL,
                    description=f"IAM binding uses overly broad role: {role}",
                    file_path="",
                    line_number=resource.line_number,
                    recommendation="Use more specific roles following principle of least privilege",
                    rule_id="gcp_iam_overly_broad_role",
                    affected_resources=[f"{resource.type}.{resource.name}"]
                ))
        
        return issues
    
    def _check_gcp_storage_security(self, resource: Resource) -> List[SecurityIssue]:
        """Check GCP Cloud Storage security configurations."""
        issues = []
        config = resource.configuration
        
        if resource.type == 'google_storage_bucket':
            # Check for uniform bucket-level access
            uniform_bucket_level_access = config.get('uniform_bucket_level_access', False)
            if not uniform_bucket_level_access:
                issues.append(SecurityIssue(
                    severity=Severity.MEDIUM,
                    category=Category.ACCESS_CONTROL,
                    description=f"Storage bucket {resource.name} does not use uniform bucket-level access",
                    file_path="",
                    line_number=resource.line_number,
                    recommendation="Enable uniform bucket-level access for consistent IAM",
                    rule_id="gcp_storage_no_uniform_access",
                    affected_resources=[f"{resource.type}.{resource.name}"]
                ))
        
        return issues
    
    def _check_gcp_sql_security(self, resource: Resource) -> List[SecurityIssue]:
        """Check GCP Cloud SQL security configurations."""
        issues = []
        config = resource.configuration
        
        if resource.type == 'google_sql_database_instance':
            settings = config.get('settings', {})
            if isinstance(settings, dict):
                # Check for backup configuration
                backup_configuration = settings.get('backup_configuration', {})
                if not backup_configuration or not backup_configuration.get('enabled', False):
                    issues.append(SecurityIssue(
                        severity=Severity.MEDIUM,
                        category=Category.SECURITY,
                        description=f"SQL instance {resource.name} does not have backups enabled",
                        file_path="",
                        line_number=resource.line_number,
                        recommendation="Enable backup configuration for data protection",
                        rule_id="gcp_sql_no_backups",
                        affected_resources=[f"{resource.type}.{resource.name}"]
                    ))
        
        return issues
    
    # IBM Cloud-specific security check implementations
    def _check_ibm_vsi_security(self, resource: Resource) -> List[SecurityIssue]:
        """Check IBM Virtual Server Instance security configurations."""
        issues = []
        config = resource.configuration
        
        # Check for boot volume encryption
        boot_volume = config.get('boot_volume', {})
        if isinstance(boot_volume, dict):
            encryption = boot_volume.get('encryption', '')
            if not encryption:
                issues.append(SecurityIssue(
                    severity=Severity.MEDIUM,
                    category=Category.ENCRYPTION,
                    description=f"VSI {resource.name} boot volume is not encrypted",
                    file_path="",
                    line_number=resource.line_number,
                    recommendation="Enable boot volume encryption",
                    rule_id="ibm_vsi_boot_volume_not_encrypted",
                    affected_resources=[f"{resource.type}.{resource.name}"]
                ))
        
        return issues
    
    def _check_ibm_vpc_security(self, resource: Resource) -> List[SecurityIssue]:
        """Check IBM VPC security configurations."""
        issues = []
        config = resource.configuration
        
        # Check for default security group rules
        if resource.type == 'ibm_is_vpc':
            # IBM VPCs should have proper security group configurations
            pass
        
        return issues
    
    def _check_ibm_security_group_security(self, resource: Resource) -> List[SecurityIssue]:
        """Check IBM Security Group configurations."""
        issues = []
        config = resource.configuration
        
        if resource.type == 'ibm_is_security_group_rule':
            # Check for overly permissive rules
            remote = config.get('remote', '')
            if remote == '0.0.0.0/0':
                issues.append(SecurityIssue(
                    severity=Severity.HIGH,
                    category=Category.ACCESS_CONTROL,
                    description=f"Security group rule {resource.name} allows access from any source",
                    file_path="",
                    line_number=resource.line_number,
                    recommendation="Restrict remote to specific IP ranges",
                    rule_id="ibm_sg_overly_permissive",
                    affected_resources=[f"{resource.type}.{resource.name}"]
                ))
        
        return issues
    
    def _check_ibm_cos_security(self, resource: Resource) -> List[SecurityIssue]:
        """Check IBM Cloud Object Storage security configurations."""
        issues = []
        config = resource.configuration
        
        # Check for encryption
        # IBM COS encryption checks would go here
        
        return issues
    
    # OCI-specific security check implementations
    def _check_oci_compute_security(self, resource: Resource) -> List[SecurityIssue]:
        """Check OCI Compute Instance security configurations."""
        issues = []
        config = resource.configuration
        
        # Check for in-transit encryption
        # OCI compute security checks would go here
        
        return issues
    
    def _check_oci_vcn_security(self, resource: Resource) -> List[SecurityIssue]:
        """Check OCI VCN security configurations."""
        issues = []
        config = resource.configuration
        
        # Check for DNS resolution
        # OCI VCN security checks would go here
        
        return issues
    
    def _check_oci_security_list_security(self, resource: Resource) -> List[SecurityIssue]:
        """Check OCI Security List configurations."""
        issues = []
        config = resource.configuration
        
        if resource.type == 'oci_core_security_list':
            # Check ingress and egress rules
            ingress_security_rules = config.get('ingress_security_rules', [])
            for rule in ingress_security_rules:
                if isinstance(rule, dict):
                    source = rule.get('source', '')
                    if source == '0.0.0.0/0':
                        issues.append(SecurityIssue(
                            severity=Severity.HIGH,
                            category=Category.ACCESS_CONTROL,
                            description=f"Security list {resource.name} allows ingress from any source",
                            file_path="",
                            line_number=resource.line_number,
                            recommendation="Restrict source to specific IP ranges",
                            rule_id="oci_security_list_overly_permissive",
                            affected_resources=[f"{resource.type}.{resource.name}"]
                        ))
        
        return issues
    
    def _check_oci_storage_security(self, resource: Resource) -> List[SecurityIssue]:
        """Check OCI Object Storage security configurations."""
        issues = []
        config = resource.configuration
        
        # Check for encryption and access policies
        # OCI storage security checks would go here
        
        return issues
    
    # AliCloud-specific security check implementations
    def _check_alicloud_ecs_security(self, resource: Resource) -> List[SecurityIssue]:
        """Check AliCloud ECS Instance security configurations."""
        issues = []
        config = resource.configuration
        
        # Check for system disk encryption
        system_disk_encrypted = config.get('system_disk_encrypted', False)
        if not system_disk_encrypted:
            issues.append(SecurityIssue(
                severity=Severity.MEDIUM,
                category=Category.ENCRYPTION,
                description=f"ECS instance {resource.name} system disk is not encrypted",
                file_path="",
                line_number=resource.line_number,
                recommendation="Enable system disk encryption",
                rule_id="alicloud_ecs_system_disk_not_encrypted",
                affected_resources=[f"{resource.type}.{resource.name}"]
            ))
        
        return issues
    
    def _check_alicloud_vpc_security(self, resource: Resource) -> List[SecurityIssue]:
        """Check AliCloud VPC security configurations."""
        issues = []
        config = resource.configuration
        
        # AliCloud VPC security checks would go here
        
        return issues
    
    def _check_alicloud_security_group_security(self, resource: Resource) -> List[SecurityIssue]:
        """Check AliCloud Security Group configurations."""
        issues = []
        config = resource.configuration
        
        if resource.type == 'alicloud_security_group_rule':
            # Check for overly permissive rules
            cidr_ip = config.get('cidr_ip', '')
            if cidr_ip == '0.0.0.0/0':
                issues.append(SecurityIssue(
                    severity=Severity.HIGH,
                    category=Category.ACCESS_CONTROL,
                    description=f"Security group rule {resource.name} allows access from any source",
                    file_path="",
                    line_number=resource.line_number,
                    recommendation="Restrict cidr_ip to specific IP ranges",
                    rule_id="alicloud_sg_overly_permissive",
                    affected_resources=[f"{resource.type}.{resource.name}"]
                ))
        
        return issues
    
    def _check_alicloud_oss_security(self, resource: Resource) -> List[SecurityIssue]:
        """Check AliCloud OSS security configurations."""
        issues = []
        config = resource.configuration
        
        # Check for server-side encryption
        server_side_encryption_rule = config.get('server_side_encryption_rule', {})
        if not server_side_encryption_rule:
            issues.append(SecurityIssue(
                severity=Severity.MEDIUM,
                category=Category.ENCRYPTION,
                description=f"OSS bucket {resource.name} does not have server-side encryption",
                file_path="",
                line_number=resource.line_number,
                recommendation="Enable server-side encryption for OSS bucket",
                rule_id="alicloud_oss_no_encryption",
                affected_resources=[f"{resource.type}.{resource.name}"]
            ))
        
        return issues
    
    # OpenStack-specific security check implementations
    def _check_openstack_compute_security(self, resource: Resource) -> List[SecurityIssue]:
        """Check OpenStack Compute Instance security configurations."""
        issues = []
        config = resource.configuration
        
        # Check for key pair usage
        key_pair = config.get('key_pair', '')
        if not key_pair:
            issues.append(SecurityIssue(
                severity=Severity.MEDIUM,
                category=Category.ACCESS_CONTROL,
                description=f"Compute instance {resource.name} does not have a key pair configured",
                file_path="",
                line_number=resource.line_number,
                recommendation="Configure a key pair for secure access",
                rule_id="openstack_compute_no_keypair",
                affected_resources=[f"{resource.type}.{resource.name}"]
            ))
        
        return issues
    
    def _check_openstack_network_security(self, resource: Resource) -> List[SecurityIssue]:
        """Check OpenStack Network security configurations."""
        issues = []
        config = resource.configuration
        
        # OpenStack network security checks would go here
        
        return issues
    
    def _check_openstack_secgroup_security(self, resource: Resource) -> List[SecurityIssue]:
        """Check OpenStack Security Group configurations."""
        issues = []
        config = resource.configuration
        
        if resource.type == 'openstack_networking_secgroup_rule_v2':
            # Check for overly permissive rules
            remote_ip_prefix = config.get('remote_ip_prefix', '')
            if remote_ip_prefix == '0.0.0.0/0':
                issues.append(SecurityIssue(
                    severity=Severity.HIGH,
                    category=Category.ACCESS_CONTROL,
                    description=f"Security group rule {resource.name} allows access from any source",
                    file_path="",
                    line_number=resource.line_number,
                    recommendation="Restrict remote_ip_prefix to specific IP ranges",
                    rule_id="openstack_sg_overly_permissive",
                    affected_resources=[f"{resource.type}.{resource.name}"]
                ))
        
        return issues
    
    def _run_external_tools(self, terraform_files: List[TerraformFile]) -> List[SecurityIssue]:
        """
        Run external security tools like tfsec or checkov for enhanced coverage.
        
        Args:
            terraform_files: List of Terraform files to analyze
            
        Returns:
            List of SecurityIssue objects from external tools
        """
        issues = []
        
        # Get unique directories containing Terraform files
        directories = set()
        for tf_file in terraform_files:
            directories.add(str(Path(tf_file.path).parent))
        
        for directory in directories:
            try:
                # Try running tfsec
                tfsec_issues = self._run_tfsec(directory)
                issues.extend(tfsec_issues)
                
                # Try running checkov
                checkov_issues = self._run_checkov(directory)
                issues.extend(checkov_issues)
                
            except Exception as e:
                self.handle_error(e, f"running external tools on {directory}")
        
        return issues
    
    def _run_tfsec(self, directory: str) -> List[SecurityIssue]:
        """Run tfsec security scanner."""
        issues = []
        
        try:
            result = subprocess.run(
                [self.tfsec_path, '--format', 'json', directory],
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            if result.returncode == 0 and result.stdout:
                tfsec_data = json.loads(result.stdout)
                results = tfsec_data.get('results', [])
                
                for result_item in results:
                    severity_map = {
                        'CRITICAL': Severity.CRITICAL,
                        'HIGH': Severity.HIGH,
                        'MEDIUM': Severity.MEDIUM,
                        'LOW': Severity.LOW
                    }
                    
                    issues.append(SecurityIssue(
                        severity=severity_map.get(result_item.get('severity', 'MEDIUM'), Severity.MEDIUM),
                        category=Category.SECURITY,
                        description=result_item.get('description', 'Security issue detected by tfsec'),
                        file_path=result_item.get('location', {}).get('filename', ''),
                        line_number=result_item.get('location', {}).get('start_line', 0),
                        recommendation=result_item.get('resolution', 'Review and fix the security issue'),
                        rule_id=result_item.get('rule_id', 'tfsec_unknown'),
                        cwe_id=result_item.get('links', [{}])[0].get('cwe', None) if result_item.get('links') else None
                    ))
        
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, json.JSONDecodeError, FileNotFoundError):
            # Tool not available or failed, continue without external analysis
            pass
        
        return issues
    
    def _run_checkov(self, directory: str) -> List[SecurityIssue]:
        """Run checkov security scanner."""
        issues = []
        
        try:
            result = subprocess.run(
                [self.checkov_path, '-d', directory, '--output', 'json'],
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            if result.stdout:
                checkov_data = json.loads(result.stdout)
                failed_checks = checkov_data.get('results', {}).get('failed_checks', [])
                
                for check in failed_checks:
                    severity_map = {
                        'CRITICAL': Severity.CRITICAL,
                        'HIGH': Severity.HIGH,
                        'MEDIUM': Severity.MEDIUM,
                        'LOW': Severity.LOW
                    }
                    
                    issues.append(SecurityIssue(
                        severity=severity_map.get(check.get('severity', 'MEDIUM'), Severity.MEDIUM),
                        category=Category.SECURITY,
                        description=check.get('check_name', 'Security issue detected by checkov'),
                        file_path=check.get('file_path', ''),
                        line_number=check.get('file_line_range', [0])[0],
                        recommendation=check.get('guideline', 'Review and fix the security issue'),
                        rule_id=check.get('check_id', 'checkov_unknown')
                    ))
        
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, json.JSONDecodeError, FileNotFoundError):
            # Tool not available or failed, continue without external analysis
            pass
        
        return issues
    
    def _calculate_entropy(self, text: str) -> float:
        """Calculate Shannon entropy of a string."""
        if not text:
            return 0.0
        
        # Count character frequencies
        char_counts = {}
        for char in text:
            char_counts[char] = char_counts.get(char, 0) + 1
        
        # Calculate entropy
        entropy = 0.0
        text_len = len(text)
        for count in char_counts.values():
            probability = count / text_len
            entropy -= probability * math.log2(probability)
        
        return entropy
    
    def _is_likely_hash_or_id(self, text: str) -> bool:
        """Check if a string is likely a hash or identifier rather than a secret."""
        # Common patterns for hashes and IDs that shouldn't be flagged as secrets
        hash_patterns = [
            r'^[a-f0-9]{32}$',  # MD5
            r'^[a-f0-9]{40}$',  # SHA1
            r'^[a-f0-9]{64}$',  # SHA256
            r'^[a-f0-9]{128}$', # SHA512
            r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',  # UUID
        ]
        
        return any(re.match(pattern, text.lower()) for pattern in hash_patterns)
    
    def _generate_summary(self, issues: List[SecurityIssue]) -> Dict[str, int]:
        """Generate summary statistics for security issues."""
        summary = {
            'total_issues': len(issues),
            'critical': 0,
            'high': 0,
            'medium': 0,
            'low': 0,
            'by_category': {}
        }
        
        for issue in issues:
            # Count by severity
            severity_key = issue.severity.value.lower()
            summary[severity_key] = summary.get(severity_key, 0) + 1
            
            # Count by category
            category_key = issue.category.value
            summary['by_category'][category_key] = summary['by_category'].get(category_key, 0) + 1
        
        return summary
    
    def _generate_recommendations(self, issues: List[SecurityIssue]) -> List[str]:
        """Generate high-level recommendations based on identified issues."""
        recommendations = []
        
        # Count issues by category
        category_counts = {}
        for issue in issues:
            category = issue.category.value
            category_counts[category] = category_counts.get(category, 0) + 1
        
        # Generate recommendations based on most common issues
        if category_counts.get('SECRETS', 0) > 0:
            recommendations.append(
                "Implement a secrets management solution (AWS Secrets Manager, HashiCorp Vault, etc.) "
                "to externalize hardcoded credentials and sensitive data."
            )
        
        if category_counts.get('ACCESS_CONTROL', 0) > 0:
            recommendations.append(
                "Review and tighten access control policies. Follow the principle of least privilege "
                "and avoid overly permissive security groups and IAM policies."
            )
        
        if category_counts.get('ENCRYPTION', 0) > 0:
            recommendations.append(
                "Enable encryption for data at rest and in transit. Use managed encryption services "
                "and ensure all sensitive data is properly encrypted."
            )
        
        if category_counts.get('NETWORK', 0) > 0:
            recommendations.append(
                "Implement network security best practices. Use private subnets, secure protocols, "
                "and restrict public access to only what is necessary."
            )
        
        # Add general recommendations
        recommendations.extend([
            "Regularly update Terraform providers and modules to get the latest security fixes.",
            "Implement infrastructure as code scanning in your CI/CD pipeline.",
            "Consider using Terraform Cloud or Enterprise for enhanced security features.",
            "Regularly audit and review your infrastructure configurations for security compliance."
        ])
        
        return recommendations