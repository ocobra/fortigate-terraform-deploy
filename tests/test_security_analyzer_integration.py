"""
Integration tests for SecurityAnalyzer with real Terraform configurations.

These tests demonstrate the SecurityAnalyzer working with realistic
Terraform configurations that might be found in FortiGate deployments.
"""

import pytest
from pathlib import Path
import tempfile
import os

from fortigate_analysis.analyzer.security_analyzer import SecurityAnalyzer
from fortigate_analysis.parser.code_parser import CodeParser
from fortigate_analysis.models import TerraformFile, Severity, Category


class TestSecurityAnalyzerIntegration:
    """Integration tests for SecurityAnalyzer with real configurations."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.analyzer = SecurityAnalyzer({'enable_external_tools': False})
        self.parser = CodeParser()
    
    def test_analyze_fortigate_aws_configuration(self):
        """Test analysis of a realistic FortiGate AWS configuration."""
        terraform_content = '''
# FortiGate AWS deployment with security issues
resource "aws_vpc" "fortigate_vpc" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true
  
  tags = {
    Name = "FortiGate VPC"
  }
}

resource "aws_security_group" "fortigate_sg" {
  name_prefix = "fortigate-"
  vpc_id      = aws_vpc.fortigate_vpc.id
  
  # Overly permissive SSH access
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  # Insecure HTTP management
  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  # Secure HTTPS management
  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/16"]
  }
  
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_instance" "fortigate" {
  ami                         = "ami-12345678"
  instance_type              = "c5.large"
  subnet_id                   = aws_subnet.public.id
  vpc_security_group_ids      = [aws_security_group.fortigate_sg.id]
  associate_public_ip_address = true
  
  # Hardcoded credentials - security issue
  user_data = base64encode(templatefile("${path.module}/fortigate-config.tpl", {
    admin_password = "SuperSecretPassword123!"
    license_key    = "FGVM02TM23001234-license-key-here"
  }))
  
  tags = {
    Name = "FortiGate Firewall"
  }
}

resource "aws_ebs_volume" "fortigate_logs" {
  availability_zone = aws_instance.fortigate.availability_zone
  size              = 100
  type              = "gp3"
  encrypted         = false  # Security issue - unencrypted storage
  
  tags = {
    Name = "FortiGate Logs"
  }
}

resource "aws_s3_bucket" "fortigate_backups" {
  bucket = "fortigate-backups-${random_id.bucket_suffix.hex}"
  
  tags = {
    Name = "FortiGate Configuration Backups"
  }
}

# Missing encryption configuration for S3 bucket

resource "aws_iam_policy" "fortigate_policy" {
  name = "fortigate-policy"
  
  # Overly permissive IAM policy
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = "*"
        Resource = "*"
      }
    ]
  })
}

variable "api_key" {
  description = "API key for external service"
  type        = string
  default     = "sk-1234567890abcdef1234567890abcdef"
  # Missing sensitive = true
}

variable "database_password" {
  description = "Database password"
  type        = string
  # Missing sensitive = true - security issue
}
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.tf', delete=False) as f:
            f.write(terraform_content)
            temp_file = f.name
        
        try:
            # Parse the Terraform file
            ast = self.parser.parse_terraform_file(Path(temp_file))
            
            # Create TerraformFile object
            tf_file = TerraformFile(
                path=temp_file,
                cloud_provider="aws",
                deployment_type="single",
                fortigate_versions=["7.0"],
                ast=ast,
                resources=ast.resources if ast else []
            )
            
            # Analyze security
            report = self.analyzer.analyze_security([tf_file])
            
            # Verify we found multiple security issues
            assert len(report.issues) >= 4
            
            # Check for specific security issues
            issue_types = [issue.rule_id for issue in report.issues]
            
            # Should find overly permissive security group
            assert any('overly_permissive_ingress' in rule_id for rule_id in issue_types)
            
            # Should find unencrypted EBS volume
            assert any('ebs_encryption_missing' in rule_id for rule_id in issue_types)
            
            # Should find missing S3 encryption
            assert any('s3_encryption_missing' in rule_id for rule_id in issue_types)
            
            # Should find insensitive secret variables
            assert any('insensitive_secret_variable' in rule_id for rule_id in issue_types)
            
            # Should find hardcoded secrets in variable defaults
            assert any('hardcoded_generic_api_key_in_variable' in rule_id for rule_id in issue_types)
            
            # Check severity distribution
            critical_issues = [i for i in report.issues if i.severity == Severity.CRITICAL]
            high_issues = [i for i in report.issues if i.severity == Severity.HIGH]
            
            assert len(critical_issues) >= 1  # SSH access + hardcoded secrets
            assert len(high_issues) >= 2      # encryption, variables
            
            # Check categories
            categories = [issue.category for issue in report.issues]
            assert Category.SECRETS in categories
            assert Category.ACCESS_CONTROL in categories
            assert Category.ENCRYPTION in categories
            
            # Verify summary
            assert report.summary['total_issues'] == len(report.issues)
            assert report.summary['critical'] >= 2
            assert report.summary['high'] >= 3
            
            # Verify recommendations
            assert len(report.recommendations) > 0
            assert any('secrets management' in rec.lower() for rec in report.recommendations)
            assert any('access control' in rec.lower() for rec in report.recommendations)
            assert any('encryption' in rec.lower() for rec in report.recommendations)
            
        finally:
            # Clean up temporary file
            os.unlink(temp_file)
    
    def test_analyze_secure_fortigate_configuration(self):
        """Test analysis of a secure FortiGate configuration with minimal issues."""
        terraform_content = '''
# Secure FortiGate AWS deployment
resource "aws_vpc" "fortigate_vpc" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true
  
  tags = {
    Name = "FortiGate VPC"
  }
}

resource "aws_security_group" "fortigate_sg" {
  name_prefix = "fortigate-"
  vpc_id      = aws_vpc.fortigate_vpc.id
  
  # Restricted SSH access
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/16"]  # Only from VPC
  }
  
  # Secure HTTPS management only
  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/16"]
  }
  
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_instance" "fortigate" {
  ami                         = "ami-12345678"
  instance_type              = "c5.large"
  subnet_id                   = aws_subnet.private.id
  vpc_security_group_ids      = [aws_security_group.fortigate_sg.id]
  associate_public_ip_address = false  # No public IP
  
  # Use secure configuration without hardcoded secrets
  user_data = base64encode(templatefile("${path.module}/fortigate-config.tpl", {
    admin_password = var.admin_password
    license_key    = var.license_key
  }))
  
  tags = {
    Name = "FortiGate Firewall"
  }
}

resource "aws_ebs_volume" "fortigate_logs" {
  availability_zone = aws_instance.fortigate.availability_zone
  size              = 100
  type              = "gp3"
  encrypted         = true  # Encrypted storage
  kms_key_id        = aws_kms_key.fortigate.arn
  
  tags = {
    Name = "FortiGate Logs"
  }
}

resource "aws_s3_bucket" "fortigate_backups" {
  bucket = "fortigate-backups-${random_id.bucket_suffix.hex}"
  
  tags = {
    Name = "FortiGate Configuration Backups"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "fortigate_backups" {
  bucket = aws_s3_bucket.fortigate_backups.id
  
  rule {
    apply_server_side_encryption_by_default {
      kms_master_key_id = aws_kms_key.fortigate.arn
      sse_algorithm     = "aws:kms"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "fortigate_backups" {
  bucket = aws_s3_bucket.fortigate_backups.id
  
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

variable "admin_password" {
  description = "FortiGate admin password"
  type        = string
  sensitive   = true
}

variable "license_key" {
  description = "FortiGate license key"
  type        = string
  sensitive   = true
}
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.tf', delete=False) as f:
            f.write(terraform_content)
            temp_file = f.name
        
        try:
            # Parse the Terraform file
            ast = self.parser.parse_terraform_file(Path(temp_file))
            
            # Create TerraformFile object
            tf_file = TerraformFile(
                path=temp_file,
                cloud_provider="aws",
                deployment_type="single",
                fortigate_versions=["7.0"],
                ast=ast,
                resources=ast.resources if ast else []
            )
            
            # Analyze security
            report = self.analyzer.analyze_security([tf_file])
            
            # Should have some security issues but they should be mostly low/medium severity
            # The enhanced multi-cloud validation will detect more issues
            assert len(report.issues) <= 10  # Allow for enhanced multi-cloud security checks
            
            # Check that we don't have any critical issues
            critical_issues = [i for i in report.issues if i.severity == Severity.CRITICAL]
            assert len(critical_issues) == 0
            
            # Most issues should be medium or low severity
            high_issues = [i for i in report.issues if i.severity == Severity.HIGH]
            assert len(high_issues) <= 2  # Allow for some high severity issues like encryption
            
            # Should not have critical issues
            critical_issues = [i for i in report.issues if i.severity == Severity.CRITICAL]
            assert len(critical_issues) == 0
            
            # Verify summary shows good security posture
            assert report.summary.get('critical', 0) == 0
            
        finally:
            # Clean up temporary file
            os.unlink(temp_file)
    
    def test_analyze_multi_cloud_configuration(self):
        """Test analysis of multi-cloud FortiGate configuration."""
        terraform_content = '''
# Multi-cloud FortiGate deployment with mixed security posture

# AWS Resources
resource "aws_security_group" "aws_fortigate_sg" {
  name = "aws-fortigate-sg"
  
  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/8"]  # Somewhat permissive
  }
}

# Azure Resources
resource "azurerm_network_security_rule" "azure_fortigate_rule" {
  name                       = "allow-https"
  priority                   = 100
  direction                  = "Inbound"
  access                     = "Allow"
  protocol                   = "Tcp"
  source_port_range          = "*"
  destination_port_range     = "443"
  source_address_prefix      = "0.0.0.0/0"  # Overly permissive
  destination_address_prefix = "*"
}

# GCP Resources
resource "google_compute_firewall" "gcp_fortigate_firewall" {
  name    = "gcp-fortigate-firewall"
  network = "default"
  
  allow {
    protocol = "tcp"
    ports    = ["22", "443"]
  }
  
  source_ranges = ["0.0.0.0/0"]  # Overly permissive
}

# Common issues across clouds
variable "shared_secret" {
  description = "Shared secret for VPN"
  type        = string
  default     = "my-super-secret-key-123"  # Hardcoded secret
  # Missing sensitive = true
}
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.tf', delete=False) as f:
            f.write(terraform_content)
            temp_file = f.name
        
        try:
            # Parse the Terraform file
            ast = self.parser.parse_terraform_file(Path(temp_file))
            
            # Create TerraformFile object
            tf_file = TerraformFile(
                path=temp_file,
                cloud_provider="multi",
                deployment_type="multi-cloud",
                fortigate_versions=["7.0"],
                ast=ast,
                resources=ast.resources if ast else []
            )
            
            # Analyze security
            report = self.analyzer.analyze_security([tf_file])
            
            # Should find issues across different cloud providers
            assert len(report.issues) >= 2
            
            # Check for cloud-specific issues
            issue_descriptions = [issue.description for issue in report.issues]
            
            # Should find firewall/security group issues
            firewall_issues = [desc for desc in issue_descriptions if 
                             'firewall' in desc.lower() or 'security group' in desc.lower() or 'security rule' in desc.lower()]
            assert len(firewall_issues) >= 1  # At least GCP firewall issue
            
            # Should find variable issues
            variable_issues = [issue for issue in report.issues if 'variable' in issue.rule_id]
            assert len(variable_issues) >= 1
            
        finally:
            # Clean up temporary file
            os.unlink(temp_file)
    
    def test_error_handling_with_malformed_terraform(self):
        """Test error handling with malformed Terraform configuration."""
        malformed_content = '''
# Malformed Terraform that should not crash the analyzer
resource "aws_instance" "test" {
  ami = "ami-12345"
  # Missing closing brace and other syntax errors
  
resource "aws_security_group" "malformed" {
  ingress {
    from_port = 22
    # Missing other required fields
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.tf', delete=False) as f:
            f.write(malformed_content)
            temp_file = f.name
        
        try:
            # Parse the Terraform file (may fail)
            try:
                ast = self.parser.parse_terraform_file(Path(temp_file))
            except:
                ast = None
            
            # Create TerraformFile object
            tf_file = TerraformFile(
                path=temp_file,
                cloud_provider="aws",
                deployment_type="single",
                fortigate_versions=["7.0"],
                ast=ast,
                resources=ast.resources if ast else []
            )
            
            # Analyze security - should not crash
            report = self.analyzer.analyze_security([tf_file])
            
            # Should return a valid report even with errors
            assert isinstance(report.issues, list)
            assert isinstance(report.summary, dict)
            assert isinstance(report.recommendations, list)
            
        finally:
            # Clean up temporary file
            os.unlink(temp_file)