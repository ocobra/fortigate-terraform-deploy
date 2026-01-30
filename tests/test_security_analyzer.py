"""
Unit tests for the SecurityAnalyzer class.

Tests cover hardcoded secrets detection, access control validation,
encryption settings verification, and network security analysis.
"""

import pytest
from unittest.mock import patch, MagicMock
import json

from fortigate_analysis.analyzer.security_analyzer import SecurityAnalyzer
from fortigate_analysis.models import (
    TerraformFile, TerraformAST, Resource, Variable, SecurityIssue,
    Severity, Category
)


class TestSecurityAnalyzer:
    """Test cases for SecurityAnalyzer class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.analyzer = SecurityAnalyzer()
    
    def test_init_with_config(self):
        """Test SecurityAnalyzer initialization with configuration."""
        config = {
            'enable_external_tools': False,
            'tfsec_path': '/custom/tfsec',
            'checkov_path': '/custom/checkov'
        }
        analyzer = SecurityAnalyzer(config)
        
        assert analyzer.enable_external_tools is False
        assert analyzer.tfsec_path == '/custom/tfsec'
        assert analyzer.checkov_path == '/custom/checkov'
    
    def test_init_without_config(self):
        """Test SecurityAnalyzer initialization without configuration."""
        analyzer = SecurityAnalyzer()
        
        assert analyzer.enable_external_tools is True
        assert analyzer.tfsec_path == 'tfsec'
        assert analyzer.checkov_path == 'checkov'
    
    def test_analyze_alias(self):
        """Test that analyze method is an alias for analyze_security."""
        tf_files = []
        
        with patch.object(self.analyzer, 'analyze_security') as mock_analyze:
            mock_analyze.return_value = MagicMock()
            result = self.analyzer.analyze(tf_files)
            
            mock_analyze.assert_called_once_with(tf_files)
            assert result == mock_analyze.return_value
    
    def test_check_hardcoded_secrets_aws_keys(self):
        """Test detection of hardcoded AWS access keys."""
        resource = Resource(
            type="aws_instance",
            name="test",
            provider="aws",
            configuration={
                "access_key": "AKIAIOSFODNN7EXAMPLE",
                "secret_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
            },
            line_number=10
        )
        
        ast = TerraformAST(resources=[resource])
        issues = self.analyzer.check_hardcoded_secrets(ast)
        
        assert len(issues) >= 1
        aws_key_issues = [i for i in issues if 'aws_access_key' in i.rule_id]
        assert len(aws_key_issues) == 1
        assert aws_key_issues[0].severity == Severity.CRITICAL
        assert aws_key_issues[0].category == Category.SECRETS
    
    def test_check_hardcoded_secrets_generic_api_key(self):
        """Test detection of generic API keys."""
        resource = Resource(
            type="aws_lambda_function",
            name="test",
            provider="aws",
            configuration={
                "environment": {
                    "variables": {
                        "API_KEY": "sk-1234567890abcdef1234567890abcdef"
                    }
                }
            },
            line_number=15
        )
        
        ast = TerraformAST(resources=[resource])
        issues = self.analyzer.check_hardcoded_secrets(ast)
        
        api_key_issues = [i for i in issues if 'generic_api_key' in i.rule_id]
        assert len(api_key_issues) >= 1
        assert api_key_issues[0].severity == Severity.CRITICAL
        assert api_key_issues[0].category == Category.SECRETS
    
    def test_check_hardcoded_secrets_high_entropy(self):
        """Test detection of high entropy strings."""
        resource = Resource(
            type="aws_instance",
            name="test",
            provider="aws",
            configuration={
                "user_data": "aB3dE6fG9hI2jK5lM8nO1pQ4rS7tU0vW3xY6zA9bC2dE5fG8hI1jK4lM7nO0pQ3rS6tU9vW2xY5zA8bC1dE4fG7hI0jK3lM6nO9pQ2rS5tU8vW1xY4zA7bC0dE3fG6hI9jK2lM5nO8pQ1rS4tU7vW0xY3zA6bC9dE2fG5hI8jK1lM4nO7pQ0rS3tU6vW9xY2zA5bC8dE1fG4hI7jK0lM3nO6pQ9rS2tU5vW8xY1zA4bC7dE0fG3hI6jK9lM2nO5pQ8rS1tU4vW7xY0zA3bC6dE9fG2hI5jK8lM1nO4pQ7rS0tU3vW6xY9zA2bC5dE8fG1hI4jK7lM0nO3pQ6rS9tU2vW5xY8zA1bC4dE7fG0hI3jK6lM9nO2pQ5rS8tU1vW4xY7zA0bC3dE6fG9hI2jK5lM8nO1pQ4rS7tU0vW3xY6zA9bC2dE5fG8hI1jK4lM7nO0pQ3rS6tU9vW2xY5zA8bC1dE4fG7hI0jK3lM6nO9pQ2rS5tU8vW1xY4zA7bC0dE3fG6hI9jK2lM5nO8pQ1rS4tU7vW0xY3zA6bC9dE2fG5hI8jK1lM4nO7pQ0rS3tU6vW9xY2zA5bC8dE1fG4hI7jK0lM3nO6pQ9rS2tU5vW8xY1zA4bC7dE0fG3hI6jK9lM2nO5pQ8rS1tU4vW7xY0zA3bC6dE9fG2hI5jK8lM1nO4pQ7rS0tU3vW6xY9zA2bC5dE8fG1hI4jK7lM0nO3pQ6rS9tU2vW5xY8zA1bC4dE7fG0hI3jK6lM9nO2pQ5rS8tU1vW4xY7zA0bC3dE6fG9hI2jK5lM8nO1pQ4rS7tU0vW3xY6zA9bC2dE5fG8hI1jK4lM7nO0pQ3rS6tU9vW2xY5zA8bC1dE4fG7hI0jK3lM6nO9pQ2rS5tU8vW1xY4zA7bC0dE3fG6hI9jK2lM5nO8pQ1rS4tU7vW0xY3zA6bC9dE2fG5hI8jK1lM4nO7pQ0rS3tU6vW9xY2zA5bC8dE1fG4hI7jK0lM3nO6pQ9rS2tU5vW8xY1zA4bC7dE0fG3hI6jK9lM2nO5pQ8rS1tU4vW7xY0zA3bC6dE9fG2hI5jK8lM1nO4pQ7rS0tU3vW6xY9zA2bC5dE8fG1hI4jK7lM0nO3pQ6rS9tU2vW5xY8zA1bC4dE7fG0hI3jK6lM9nO2pQ5rS8tU1vW4xY7zA0"
            },
            line_number=20
        )
        
        ast = TerraformAST(resources=[resource])
        issues = self.analyzer.check_hardcoded_secrets(ast)
        
        entropy_issues = [i for i in issues if 'high_entropy_string' in i.rule_id]
        assert len(entropy_issues) >= 1
        assert entropy_issues[0].severity == Severity.MEDIUM
        assert entropy_issues[0].category == Category.SECRETS
    
    def test_check_hardcoded_secrets_ignores_hashes(self):
        """Test that known hash patterns are not flagged as secrets."""
        resource = Resource(
            type="aws_instance",
            name="test",
            provider="aws",
            configuration={
                "ami": "ami-0123456789abcdef0",  # AMI ID
                "checksum": "d41d8cd98f00b204e9800998ecf8427e",  # MD5 hash
                "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"  # SHA256
            },
            line_number=25
        )
        
        ast = TerraformAST(resources=[resource])
        issues = self.analyzer.check_hardcoded_secrets(ast)
        
        # Should not flag these as high entropy secrets
        entropy_issues = [i for i in issues if 'high_entropy_string' in i.rule_id]
        assert len(entropy_issues) == 0
    
    def test_check_variable_secrets_insensitive_secret(self):
        """Test detection of secret variables not marked as sensitive."""
        variable = Variable(
            name="database_password",
            type="string",
            description="Database password",
            sensitive=False
        )
        
        ast = TerraformAST(variables=[variable])
        issues = self.analyzer.check_hardcoded_secrets(ast)
        
        insensitive_issues = [i for i in issues if 'insensitive_secret_variable' in i.rule_id]
        assert len(insensitive_issues) == 1
        assert insensitive_issues[0].severity == Severity.HIGH
        assert insensitive_issues[0].category == Category.SECRETS
    
    def test_check_variable_secrets_hardcoded_default(self):
        """Test detection of hardcoded secrets in variable defaults."""
        variable = Variable(
            name="api_key",
            type="string",
            default="sk-1234567890abcdef1234567890abcdef",
            sensitive=True
        )
        
        ast = TerraformAST(variables=[variable])
        issues = self.analyzer.check_hardcoded_secrets(ast)
        
        hardcoded_issues = [i for i in issues if 'hardcoded_generic_api_key_in_variable' in i.rule_id]
        assert len(hardcoded_issues) == 1
        assert hardcoded_issues[0].severity == Severity.CRITICAL
        assert hardcoded_issues[0].category == Category.SECRETS
    
    def test_validate_access_controls_overly_permissive_sg(self):
        """Test detection of overly permissive security groups."""
        resource = Resource(
            type="aws_security_group",
            name="test_sg",
            provider="aws",
            configuration={
                "ingress": [
                    {
                        "from_port": 22,
                        "to_port": 22,
                        "protocol": "tcp",
                        "cidr_blocks": ["0.0.0.0/0"]
                    }
                ]
            },
            line_number=30
        )
        
        issues = self.analyzer.validate_access_controls([resource])
        
        permissive_issues = [i for i in issues if 'overly_permissive_ingress' in i.rule_id]
        assert len(permissive_issues) == 1
        assert permissive_issues[0].severity == Severity.CRITICAL  # SSH port is insecure
        assert permissive_issues[0].category == Category.ACCESS_CONTROL
    
    def test_validate_access_controls_insecure_port(self):
        """Test detection of insecure port access."""
        resource = Resource(
            type="aws_security_group",
            name="test_sg",
            provider="aws",
            configuration={
                "ingress": [
                    {
                        "from_port": 23,  # Telnet
                        "to_port": 23,
                        "protocol": "tcp",
                        "cidr_blocks": ["10.0.0.0/8"]
                    }
                ]
            },
            line_number=35
        )
        
        issues = self.analyzer.validate_access_controls([resource])
        
        insecure_port_issues = [i for i in issues if 'insecure_port_access' in i.rule_id]
        assert len(insecure_port_issues) == 1
        assert insecure_port_issues[0].severity == Severity.HIGH
        assert insecure_port_issues[0].category == Category.NETWORK
    
    def test_validate_access_controls_wildcard_iam(self):
        """Test detection of wildcard IAM permissions."""
        policy_doc = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": "*",
                    "Resource": "*"
                }
            ]
        }
        
        resource = Resource(
            type="aws_iam_policy",
            name="test_policy",
            provider="aws",
            configuration={
                "policy": json.dumps(policy_doc)
            },
            line_number=40
        )
        
        issues = self.analyzer.validate_access_controls([resource])
        
        wildcard_action_issues = [i for i in issues if 'wildcard_iam_actions' in i.rule_id]
        wildcard_resource_issues = [i for i in issues if 'wildcard_iam_resources' in i.rule_id]
        
        assert len(wildcard_action_issues) == 1
        assert len(wildcard_resource_issues) == 1
        assert wildcard_action_issues[0].severity == Severity.HIGH
        assert wildcard_resource_issues[0].severity == Severity.HIGH
    
    def test_validate_access_controls_s3_public_access(self):
        """Test detection of S3 public access settings."""
        resource = Resource(
            type="aws_s3_bucket_public_access_block",
            name="test_bucket_pab",
            provider="aws",
            configuration={
                "block_public_acls": False,
                "block_public_policy": False,
                "ignore_public_acls": True,
                "restrict_public_buckets": True
            },
            line_number=45
        )
        
        issues = self.analyzer.validate_access_controls([resource])
        
        public_access_issues = [i for i in issues if 's3_public_access_enabled' in i.rule_id]
        assert len(public_access_issues) == 2  # Two settings are disabled
        assert all(issue.severity == Severity.HIGH for issue in public_access_issues)
    
    def test_check_encryption_settings_s3_missing(self):
        """Test detection of missing S3 encryption."""
        resource = Resource(
            type="aws_s3_bucket",
            name="test_bucket",
            provider="aws",
            configuration={
                "bucket": "my-test-bucket"
                # Missing server_side_encryption_configuration
            },
            line_number=50
        )
        
        issues = self.analyzer.check_encryption_settings([resource])
        
        encryption_issues = [i for i in issues if 's3_encryption_missing' in i.rule_id]
        assert len(encryption_issues) == 1
        assert encryption_issues[0].severity == Severity.HIGH
        assert encryption_issues[0].category == Category.ENCRYPTION
    
    def test_check_encryption_settings_ebs_unencrypted(self):
        """Test detection of unencrypted EBS volumes."""
        resource = Resource(
            type="aws_ebs_volume",
            name="test_volume",
            provider="aws",
            configuration={
                "availability_zone": "us-west-2a",
                "size": 20,
                "encrypted": False
            },
            line_number=55
        )
        
        issues = self.analyzer.check_encryption_settings([resource])
        
        encryption_issues = [i for i in issues if 'ebs_encryption_missing' in i.rule_id]
        assert len(encryption_issues) == 1
        assert encryption_issues[0].severity == Severity.HIGH
        assert encryption_issues[0].category == Category.ENCRYPTION
    
    def test_check_encryption_settings_rds_unencrypted(self):
        """Test detection of unencrypted RDS instances."""
        resource = Resource(
            type="aws_rds_instance",
            name="test_db",
            provider="aws",
            configuration={
                "engine": "mysql",
                "instance_class": "db.t3.micro",
                "storage_encrypted": False
            },
            line_number=60
        )
        
        issues = self.analyzer.check_encryption_settings([resource])
        
        encryption_issues = [i for i in issues if 'rds_storage_encryption_missing' in i.rule_id]
        assert len(encryption_issues) == 1
        assert encryption_issues[0].severity == Severity.HIGH
        assert encryption_issues[0].category == Category.ENCRYPTION
    
    def test_check_encryption_settings_http_listener(self):
        """Test detection of HTTP load balancer listeners."""
        resource = Resource(
            type="aws_lb_listener",
            name="test_listener",
            provider="aws",
            configuration={
                "load_balancer_arn": "arn:aws:elasticloadbalancing:...",
                "port": 80,
                "protocol": "HTTP"
            },
            line_number=65
        )
        
        issues = self.analyzer.check_encryption_settings([resource])
        
        http_issues = [i for i in issues if 'lb_http_listener' in i.rule_id]
        assert len(http_issues) == 1
        assert http_issues[0].severity == Severity.MEDIUM
        assert http_issues[0].category == Category.ENCRYPTION
    
    def test_analyze_network_security_public_ip(self):
        """Test detection of public IP assignments."""
        resource = Resource(
            type="aws_instance",
            name="test_instance",
            provider="aws",
            configuration={
                "ami": "ami-12345678",
                "instance_type": "t3.micro",
                "associate_public_ip_address": True
            },
            line_number=70
        )
        
        issues = self.analyzer.analyze_network_security([resource])
        
        public_ip_issues = [i for i in issues if 'ec2_public_ip' in i.rule_id]
        assert len(public_ip_issues) == 1
        assert public_ip_issues[0].severity == Severity.MEDIUM
        assert public_ip_issues[0].category == Category.NETWORK
    
    def test_analyze_network_security_insecure_protocol(self):
        """Test detection of insecure protocols."""
        resource = Resource(
            type="aws_lb_listener",
            name="test_listener",
            provider="aws",
            configuration={
                "load_balancer_arn": "arn:aws:elasticloadbalancing:...",
                "port": 21,
                "protocol": "ftp"
            },
            line_number=75
        )
        
        issues = self.analyzer.analyze_network_security([resource])
        
        insecure_protocol_issues = [i for i in issues if 'insecure_protocol' in i.rule_id]
        assert len(insecure_protocol_issues) == 1
        assert insecure_protocol_issues[0].severity == Severity.HIGH
        assert insecure_protocol_issues[0].category == Category.NETWORK
    
    def test_analyze_network_security_vpc_dns_disabled(self):
        """Test detection of VPC with DNS support disabled."""
        resource = Resource(
            type="aws_vpc",
            name="test_vpc",
            provider="aws",
            configuration={
                "cidr_block": "10.0.0.0/16",
                "enable_dns_support": False,
                "enable_dns_hostnames": False
            },
            line_number=80
        )
        
        issues = self.analyzer.analyze_network_security([resource])
        
        dns_issues = [i for i in issues if 'vpc_dns_support_disabled' in i.rule_id]
        assert len(dns_issues) == 1
        assert dns_issues[0].severity == Severity.LOW
        assert dns_issues[0].category == Category.NETWORK
    
    def test_calculate_entropy(self):
        """Test entropy calculation for strings."""
        # Low entropy string
        low_entropy = self.analyzer._calculate_entropy("aaaaaaaaaa")
        assert low_entropy < 1.0
        
        # High entropy string
        high_entropy = self.analyzer._calculate_entropy("aB3dE6fG9hI2jK5lM8nO1pQ4rS7tU0vW")
        assert high_entropy > 4.0
        
        # Empty string
        empty_entropy = self.analyzer._calculate_entropy("")
        assert empty_entropy == 0.0
    
    def test_is_likely_hash_or_id(self):
        """Test hash/ID detection."""
        # MD5 hash
        assert self.analyzer._is_likely_hash_or_id("d41d8cd98f00b204e9800998ecf8427e")
        
        # SHA1 hash
        assert self.analyzer._is_likely_hash_or_id("da39a3ee5e6b4b0d3255bfef95601890afd80709")
        
        # UUID
        assert self.analyzer._is_likely_hash_or_id("550e8400-e29b-41d4-a716-446655440000")
        
        # Not a hash
        assert not self.analyzer._is_likely_hash_or_id("this-is-not-a-hash")
    
    def test_generate_summary(self):
        """Test summary generation."""
        issues = [
            SecurityIssue(
                severity=Severity.CRITICAL,
                category=Category.SECRETS,
                description="Test issue 1",
                file_path="test.tf",
                line_number=1,
                recommendation="Fix it"
            ),
            SecurityIssue(
                severity=Severity.HIGH,
                category=Category.ACCESS_CONTROL,
                description="Test issue 2",
                file_path="test.tf",
                line_number=2,
                recommendation="Fix it"
            ),
            SecurityIssue(
                severity=Severity.MEDIUM,
                category=Category.ENCRYPTION,
                description="Test issue 3",
                file_path="test.tf",
                line_number=3,
                recommendation="Fix it"
            )
        ]
        
        summary = self.analyzer._generate_summary(issues)
        
        assert summary['total_issues'] == 3
        assert summary['critical'] == 1
        assert summary['high'] == 1
        assert summary['medium'] == 1
        assert summary['low'] == 0
        assert summary['by_category']['SECRETS'] == 1
        assert summary['by_category']['ACCESS_CONTROL'] == 1
        assert summary['by_category']['ENCRYPTION'] == 1
    
    def test_generate_recommendations(self):
        """Test recommendation generation."""
        issues = [
            SecurityIssue(
                severity=Severity.CRITICAL,
                category=Category.SECRETS,
                description="Hardcoded secret",
                file_path="test.tf",
                line_number=1,
                recommendation="Fix it"
            ),
            SecurityIssue(
                severity=Severity.HIGH,
                category=Category.ACCESS_CONTROL,
                description="Overly permissive",
                file_path="test.tf",
                line_number=2,
                recommendation="Fix it"
            )
        ]
        
        recommendations = self.analyzer._generate_recommendations(issues)
        
        assert len(recommendations) >= 4  # Category-specific + general recommendations
        
        # Check for category-specific recommendations
        secrets_rec = any("secrets management" in rec.lower() for rec in recommendations)
        access_rec = any("access control" in rec.lower() for rec in recommendations)
        
        assert secrets_rec
        assert access_rec
    
    @patch('subprocess.run')
    def test_run_external_tools_disabled(self, mock_subprocess):
        """Test that external tools are not run when disabled."""
        analyzer = SecurityAnalyzer({'enable_external_tools': False})
        tf_files = [
            TerraformFile(
                path="test.tf",
                cloud_provider="aws",
                deployment_type="single",
                fortigate_versions=["7.0"]
            )
        ]
        
        report = analyzer.analyze_security(tf_files)
        
        # subprocess should not be called
        mock_subprocess.assert_not_called()
    
    @patch('subprocess.run')
    def test_run_tfsec_success(self, mock_subprocess):
        """Test successful tfsec execution."""
        # Mock successful tfsec output
        tfsec_output = {
            "results": [
                {
                    "rule_id": "AWS001",
                    "severity": "HIGH",
                    "description": "S3 bucket is not encrypted",
                    "location": {
                        "filename": "test.tf",
                        "start_line": 10
                    },
                    "resolution": "Enable S3 bucket encryption",
                    "links": [{"cwe": "CWE-311"}]
                }
            ]
        }
        
        mock_subprocess.return_value.returncode = 0
        mock_subprocess.return_value.stdout = json.dumps(tfsec_output)
        
        issues = self.analyzer._run_tfsec("/test/dir")
        
        assert len(issues) == 1
        assert issues[0].rule_id == "AWS001"
        assert issues[0].severity == Severity.HIGH
        assert issues[0].cwe_id == "CWE-311"
    
    @patch('subprocess.run')
    def test_run_tfsec_failure(self, mock_subprocess):
        """Test tfsec execution failure."""
        mock_subprocess.side_effect = FileNotFoundError("tfsec not found")
        
        issues = self.analyzer._run_tfsec("/test/dir")
        
        # Should return empty list on failure
        assert issues == []
    
    @patch('subprocess.run')
    def test_run_checkov_success(self, mock_subprocess):
        """Test successful checkov execution."""
        # Mock successful checkov output
        checkov_output = {
            "results": {
                "failed_checks": [
                    {
                        "check_id": "CKV_AWS_20",
                        "check_name": "S3 Bucket has an ACL defined which allows public access",
                        "file_path": "test.tf",
                        "file_line_range": [15, 20],
                        "severity": "HIGH",
                        "guideline": "Remove public access from S3 bucket ACL"
                    }
                ]
            }
        }
        
        mock_subprocess.return_value.stdout = json.dumps(checkov_output)
        
        issues = self.analyzer._run_checkov("/test/dir")
        
        assert len(issues) == 1
        assert issues[0].rule_id == "CKV_AWS_20"
        assert issues[0].severity == Severity.HIGH
        assert issues[0].line_number == 15
    
    def test_analyze_security_comprehensive(self):
        """Test comprehensive security analysis."""
        # Create a Terraform file with multiple security issues
        resource = Resource(
            type="aws_security_group",
            name="test_sg",
            provider="aws",
            configuration={
                "ingress": [
                    {
                        "from_port": 22,
                        "to_port": 22,
                        "protocol": "tcp",
                        "cidr_blocks": ["0.0.0.0/0"]
                    }
                ]
            },
            line_number=10
        )
        
        variable = Variable(
            name="secret_key",
            type="string",
            sensitive=False
        )
        
        ast = TerraformAST(resources=[resource], variables=[variable])
        
        tf_file = TerraformFile(
            path="test.tf",
            cloud_provider="aws",
            deployment_type="single",
            fortigate_versions=["7.0"],
            ast=ast,
            resources=[resource]
        )
        
        # Disable external tools for this test
        analyzer = SecurityAnalyzer({'enable_external_tools': False})
        report = analyzer.analyze_security([tf_file])
        
        # Should find multiple issues
        assert len(report.issues) >= 2
        assert report.summary['total_issues'] >= 2
        assert len(report.recommendations) > 0
        
        # Check that file paths are set correctly
        for issue in report.issues:
            assert issue.file_path == "test.tf"
    
    def test_error_handling(self):
        """Test error handling in security analysis."""
        # Create a malformed resource that might cause errors
        resource = Resource(
            type="invalid_resource",
            name="test",
            provider="aws",
            configuration=None,  # This might cause issues
            line_number=1
        )
        
        tf_file = TerraformFile(
            path="test.tf",
            cloud_provider="aws",
            deployment_type="single",
            fortigate_versions=["7.0"],
            resources=[resource]
        )
        
        # Should not raise an exception
        report = self.analyzer.analyze_security([tf_file])
        
        # Should return a valid report even with errors
        assert isinstance(report, type(self.analyzer.analyze_security([])))