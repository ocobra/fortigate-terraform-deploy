#!/usr/bin/env python3
"""
FortiGate AWS HA Deployment Script

Interactive deployment wrapper for FortiGate HA pair on AWS.
Integrates with FortiGate Terraform Analysis System for validation.
"""

import os
import sys
import json
import yaml
import click
import boto3
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from getpass import getpass

# Add the FortiGate analysis system to the path
sys.path.append(str(Path(__file__).parent.parent / "fortigate_analysis"))

try:
    from fortigate_analysis.analyzer.analysis_engine import AnalysisEngine
    from fortigate_analysis.scanner.repository_scanner import RepositoryScanner
    from fortigate_analysis.analyzer.security_analyzer import SecurityAnalyzer
    from fortigate_analysis.analyzer.best_practices_validator import BestPracticesValidator
    ANALYSIS_AVAILABLE = True
except ImportError:
    print("Warning: FortiGate Analysis System not available. Validation will be limited.")
    ANALYSIS_AVAILABLE = False


@dataclass
class AWSConfig:
    """AWS configuration parameters"""
    region: str
    profile: Optional[str] = None
    access_key_id: Optional[str] = None
    secret_access_key: Optional[str] = None


@dataclass
class NetworkConfig:
    """Network configuration parameters"""
    vpc_id: str
    availability_zones: List[str]
    outside_subnet_primary: str
    inside_subnet_primary: str
    ha_subnet_primary: str
    mgmt_subnet_primary: str
    outside_subnet_backup: str
    inside_subnet_backup: str
    ha_subnet_backup: str
    mgmt_subnet_backup: str
    mgmt_access_cidrs: List[str]


@dataclass
class AMIDiscoveryConfig:
    """AMI discovery configuration"""
    enabled: bool = True
    version: str = "7.4"
    license_type: str = "BYOL"  # BYOL, OnDemand, Reserved
    architecture: str = "x86_64"


@dataclass
class LicensingConfig:
    """FortiGate licensing configuration"""
    type: str = "BYOL"  # BYOL, OnDemand, Reserved
    primary_license_secret: Optional[str] = None
    backup_license_secret: Optional[str] = None
    license_s3_bucket: Optional[str] = None
    primary_license_s3_key: Optional[str] = None
    backup_license_s3_key: Optional[str] = None


@dataclass
class FortiGateConfig:
    """FortiGate configuration parameters"""
    ami_id: Optional[str]  # Can be None for auto-discovery
    ami_discovery: AMIDiscoveryConfig
    licensing: LicensingConfig
    instance_type: str
    key_pair_name: str
    admin_password: str
    ha_password: str
    hostname_primary: str = "fortigate-primary"
    hostname_backup: str = "fortigate-backup"


@dataclass
class TransitGatewayConfig:
    """Transit Gateway configuration parameters"""
    create_new: bool
    transit_gateway_id: Optional[str] = None
    bgp_asn: int = 65000
    transit_gateway_asn: int = 64512
    spoke_vpc_cidrs: List[str] = None


@dataclass
class MonitoringConfig:
    """Monitoring configuration parameters"""
    enable_flow_logs: bool = True
    log_retention_days: int = 30
    enable_detailed_monitoring: bool = True


@dataclass
class DeploymentConfig:
    """Complete deployment configuration"""
    aws: AWSConfig
    network: NetworkConfig
    fortigate: FortiGateConfig
    transit_gateway: TransitGatewayConfig
    monitoring: MonitoringConfig
    environment: str = "prod"
    owner_tag: str = "NetworkTeam"


class AMIDiscovery:
    """Discovers FortiGate AMIs in AWS Marketplace"""
    
    def __init__(self, aws_session: boto3.Session):
        self.aws_session = aws_session
        self.ec2 = aws_session.client('ec2')
        # Fortinet's AWS account ID for official AMIs
        self.fortinet_owner_id = "679593333241"
    
    def find_latest_ami(self, version: str, license_type: str, architecture: str = "x86_64") -> Optional[str]:
        """Find the latest FortiGate AMI matching criteria"""
        try:
            # Build AMI name pattern based on license type
            if license_type.upper() == "BYOL":
                name_pattern = f"FortiGate-VM64-AWS-{version}*-BYOL-*"
            elif license_type.upper() == "ONDEMAND":
                name_pattern = f"FortiGate-VM64-AWS-{version}*-OnDemand-*"
            elif license_type.upper() == "RESERVED":
                name_pattern = f"FortiGate-VM64-AWS-{version}*-Reserved-*"
            else:
                raise ValueError(f"Invalid license type: {license_type}")
            
            click.echo(f"🔍 Searching for FortiGate {version} {license_type} AMI...")
            
            response = self.ec2.describe_images(
                Owners=[self.fortinet_owner_id],
                Filters=[
                    {"Name": "name", "Values": [name_pattern]},
                    {"Name": "state", "Values": ["available"]},
                    {"Name": "architecture", "Values": [architecture]}
                ]
            )
            
            if not response['Images']:
                click.echo(f"❌ No FortiGate {version} {license_type} AMIs found")
                return None
            
            # Sort by creation date to get the latest
            images = sorted(response['Images'], key=lambda x: x['CreationDate'], reverse=True)
            latest_ami = images[0]
            
            click.echo(f"✅ Found AMI: {latest_ami['ImageId']} - {latest_ami['Name']}")
            click.echo(f"   Created: {latest_ami['CreationDate']}")
            click.echo(f"   Description: {latest_ami.get('Description', 'N/A')}")
            
            return latest_ami['ImageId']
            
        except Exception as e:
            click.echo(f"❌ Error discovering AMI: {e}")
            return None
    
    def list_available_versions(self) -> List[str]:
        """List available FortiGate versions"""
        try:
            response = self.ec2.describe_images(
                Owners=[self.fortinet_owner_id],
                Filters=[
                    {"Name": "name", "Values": ["FortiGate-VM64-AWS-*"]},
                    {"Name": "state", "Values": ["available"]}
                ]
            )
            
            versions = set()
            for image in response['Images']:
                name = image['Name']
                # Extract version from name (e.g., FortiGate-VM64-AWS-7.4.1-BYOL-20231201)
                parts = name.split('-')
                if len(parts) >= 4:
                    version_part = parts[3]
                    # Extract major.minor version (e.g., 7.4 from 7.4.1)
                    version_parts = version_part.split('.')
                    if len(version_parts) >= 2:
                        major_minor = f"{version_parts[0]}.{version_parts[1]}"
                        versions.add(major_minor)
            
            return sorted(list(versions), reverse=True)
            
        except Exception as e:
            click.echo(f"❌ Error listing versions: {e}")
            return []


class LicenseManager:
    """Manages FortiGate license retrieval and application"""
    
    def __init__(self, aws_session: boto3.Session):
        self.aws_session = aws_session
        self.secrets_manager = aws_session.client('secretsmanager')
        self.s3 = aws_session.client('s3')
    
    def get_license_from_secrets_manager(self, secret_name: str) -> Optional[str]:
        """Retrieve license from AWS Secrets Manager"""
        try:
            click.echo(f"🔐 Retrieving license from Secrets Manager: {secret_name}")
            response = self.secrets_manager.get_secret_value(SecretId=secret_name)
            license_content = response['SecretString']
            click.echo(f"✅ License retrieved successfully")
            return license_content
        except Exception as e:
            click.echo(f"❌ Error retrieving license from Secrets Manager: {e}")
            return None
    
    def get_license_from_s3(self, bucket: str, key: str) -> Optional[str]:
        """Retrieve license from S3"""
        try:
            click.echo(f"📦 Retrieving license from S3: s3://{bucket}/{key}")
            response = self.s3.get_object(Bucket=bucket, Key=key)
            license_content = response['Body'].read().decode('utf-8')
            click.echo(f"✅ License retrieved successfully")
            return license_content
        except Exception as e:
            click.echo(f"❌ Error retrieving license from S3: {e}")
            return None
    
    def validate_license_format(self, license_content: str) -> bool:
        """Basic validation of license file format"""
        if not license_content:
            return False
        
        # Check for basic FortiGate license markers
        required_markers = ['-----BEGIN FGT VM LICENSE-----', '-----END FGT VM LICENSE-----']
        for marker in required_markers:
            if marker not in license_content:
                click.echo(f"❌ License validation failed: Missing {marker}")
                return False
        
        click.echo("✅ License format validation passed")
        return True


class ConfigurationValidator:
    """Validates deployment configuration parameters"""
    
    def __init__(self, aws_session: boto3.Session):
        self.aws_session = aws_session
        self.ec2 = aws_session.client('ec2')
    
    def validate_vpc(self, vpc_id: str) -> bool:
        """Validate VPC exists and is available"""
        try:
            response = self.ec2.describe_vpcs(VpcIds=[vpc_id])
            vpc = response['Vpcs'][0]
            if vpc['State'] != 'available':
                click.echo(f"❌ VPC {vpc_id} is not in available state: {vpc['State']}")
                return False
            click.echo(f"✅ VPC {vpc_id} validated successfully")
            return True
        except Exception as e:
            click.echo(f"❌ Error validating VPC {vpc_id}: {e}")
            return False
    
    def validate_subnets(self, subnet_ids: List[str], expected_azs: List[str]) -> bool:
        """Validate subnets exist and are in correct AZs"""
        try:
            response = self.ec2.describe_subnets(SubnetIds=subnet_ids)
            subnets = response['Subnets']
            
            if len(subnets) != len(subnet_ids):
                click.echo(f"❌ Not all subnets found. Expected {len(subnet_ids)}, found {len(subnets)}")
                return False
            
            subnet_azs = [subnet['AvailabilityZone'] for subnet in subnets]
            for az in expected_azs:
                if az not in subnet_azs:
                    click.echo(f"❌ No subnet found in availability zone {az}")
                    return False
            
            click.echo(f"✅ All {len(subnet_ids)} subnets validated successfully")
            return True
        except Exception as e:
            click.echo(f"❌ Error validating subnets: {e}")
            return False
    
    def validate_transit_gateway(self, tgw_id: str) -> bool:
        """Validate Transit Gateway exists and is available"""
        try:
            response = self.ec2.describe_transit_gateways(TransitGatewayIds=[tgw_id])
            tgw = response['TransitGateways'][0]
            if tgw['State'] != 'available':
                click.echo(f"❌ Transit Gateway {tgw_id} is not available: {tgw['State']}")
                return False
            click.echo(f"✅ Transit Gateway {tgw_id} validated successfully")
            return True
        except Exception as e:
            click.echo(f"❌ Error validating Transit Gateway {tgw_id}: {e}")
            return False
    
    def validate_ami(self, ami_id: str) -> bool:
        """Validate AMI exists and is available"""
        try:
            response = self.ec2.describe_images(ImageIds=[ami_id])
            if not response['Images']:
                click.echo(f"❌ AMI {ami_id} not found")
                return False
            
            image = response['Images'][0]
            if image['State'] != 'available':
                click.echo(f"❌ AMI {ami_id} is not available: {image['State']}")
                return False
            
            click.echo(f"✅ AMI {ami_id} validated successfully")
            return True
        except Exception as e:
            click.echo(f"❌ Error validating AMI {ami_id}: {e}")
            return False
    
    def validate_key_pair(self, key_name: str) -> bool:
        """Validate EC2 Key Pair exists"""
        try:
            response = self.ec2.describe_key_pairs(KeyNames=[key_name])
            if response['KeyPairs']:
                click.echo(f"✅ Key pair {key_name} validated successfully")
                return True
            return False
        except Exception as e:
            click.echo(f"❌ Error validating key pair {key_name}: {e}")
            return False


class TerraformManager:
    """Manages Terraform operations"""
    
    def __init__(self, terraform_dir: Path):
        self.terraform_dir = terraform_dir
        self.tfvars_file = terraform_dir / "terraform.tfvars"
    
    def init(self, backend_config: Optional[Dict[str, str]] = None) -> bool:
        """Initialize Terraform"""
        cmd = ["terraform", "init"]
        
        if backend_config:
            for key, value in backend_config.items():
                cmd.extend(["-backend-config", f"{key}={value}"])
        
        return self._run_terraform_command(cmd)
    
    def plan(self, var_file: Optional[str] = None) -> bool:
        """Generate Terraform plan"""
        cmd = ["terraform", "plan"]
        
        if var_file:
            cmd.extend(["-var-file", var_file])
        
        cmd.extend(["-out", "tfplan"])
        
        return self._run_terraform_command(cmd)
    
    def apply(self, plan_file: str = "tfplan") -> bool:
        """Apply Terraform plan"""
        cmd = ["terraform", "apply", plan_file]
        return self._run_terraform_command(cmd)
    
    def destroy(self, var_file: Optional[str] = None) -> bool:
        """Destroy Terraform-managed resources"""
        cmd = ["terraform", "destroy", "-auto-approve"]
        
        if var_file:
            cmd.extend(["-var-file", var_file])
        
        return self._run_terraform_command(cmd)
    
    def _run_terraform_command(self, cmd: List[str]) -> bool:
        """Run a Terraform command"""
        try:
            click.echo(f"Running: {' '.join(cmd)}")
            result = subprocess.run(
                cmd,
                cwd=self.terraform_dir,
                check=True,
                capture_output=False
            )
            return result.returncode == 0
        except subprocess.CalledProcessError as e:
            click.echo(f"❌ Terraform command failed: {e}")
            return False
    
    def generate_tfvars(self, config: DeploymentConfig) -> None:
        """Generate terraform.tfvars file from configuration"""
        tfvars_content = f"""# FortiGate HA Deployment Configuration
# Generated by deploy.py

# AWS Configuration
aws_region = "{config.aws.region}"
environment = "{config.environment}"
owner_tag = "{config.owner_tag}"

# Network Configuration
vpc_id = "{config.network.vpc_id}"
availability_zones = {json.dumps(config.network.availability_zones)}

# Subnet Configuration
outside_subnet_primary = "{config.network.outside_subnet_primary}"
inside_subnet_primary = "{config.network.inside_subnet_primary}"
ha_subnet_primary = "{config.network.ha_subnet_primary}"
mgmt_subnet_primary = "{config.network.mgmt_subnet_primary}"

outside_subnet_backup = "{config.network.outside_subnet_backup}"
inside_subnet_backup = "{config.network.inside_subnet_backup}"
ha_subnet_backup = "{config.network.ha_subnet_backup}"
mgmt_subnet_backup = "{config.network.mgmt_subnet_backup}"

# FortiGate Configuration
fortigate_ami_id = "{config.fortigate.ami_id}"
instance_type = "{config.fortigate.instance_type}"
key_pair_name = "{config.fortigate.key_pair_name}"
admin_password = "{config.fortigate.admin_password}"
ha_password = "{config.fortigate.ha_password}"
fortigate_hostname_primary = "{config.fortigate.hostname_primary}"
fortigate_hostname_backup = "{config.fortigate.hostname_backup}"

# Transit Gateway Configuration
create_transit_gateway = {str(config.transit_gateway.create_new).lower()}
existing_transit_gateway_id = "{config.transit_gateway.transit_gateway_id or ''}"
transit_gateway_asn = {config.transit_gateway.transit_gateway_asn}
bgp_asn = {config.transit_gateway.bgp_asn}
spoke_vpc_cidrs = {json.dumps(config.transit_gateway.spoke_vpc_cidrs or [])}

# Security Configuration
mgmt_access_cidrs = {json.dumps(config.network.mgmt_access_cidrs)}

# Monitoring Configuration
enable_flow_logs = {str(config.monitoring.enable_flow_logs).lower()}
log_retention_days = {config.monitoring.log_retention_days}
enable_detailed_monitoring = {str(config.monitoring.enable_detailed_monitoring).lower()}
"""
        
        with open(self.tfvars_file, 'w') as f:
            f.write(tfvars_content)
        
        click.echo(f"✅ Generated Terraform variables file: {self.tfvars_file}")


class DeploymentEngine:
    """Main deployment orchestrator"""
    
    def __init__(self, config: DeploymentConfig):
        self.config = config
        self.terraform_dir = Path(__file__).parent / "terraform"
        self.terraform = TerraformManager(self.terraform_dir)
        
        # Initialize AWS session
        if config.aws.profile:
            self.aws_session = boto3.Session(profile_name=config.aws.profile)
        else:
            self.aws_session = boto3.Session(
                aws_access_key_id=config.aws.access_key_id,
                aws_secret_access_key=config.aws.secret_access_key,
                region_name=config.aws.region
            )
        
        self.validator = ConfigurationValidator(self.aws_session)
        self.ami_discovery = AMIDiscovery(self.aws_session)
        self.license_manager = LicenseManager(self.aws_session)
    
    def resolve_ami_id(self) -> bool:
        """Resolve AMI ID through discovery or validation"""
        if self.config.fortigate.ami_discovery.enabled and not self.config.fortigate.ami_id:
            click.echo("🔍 Auto-discovering FortiGate AMI...")
            
            ami_id = self.ami_discovery.find_latest_ami(
                version=self.config.fortigate.ami_discovery.version,
                license_type=self.config.fortigate.ami_discovery.license_type,
                architecture=self.config.fortigate.ami_discovery.architecture
            )
            
            if not ami_id:
                click.echo("❌ Failed to discover suitable AMI")
                return False
            
            # Update configuration with discovered AMI
            self.config.fortigate.ami_id = ami_id
            click.echo(f"✅ Using discovered AMI: {ami_id}")
        
        elif self.config.fortigate.ami_id:
            # Validate manually specified AMI
            if not self.validator.validate_ami(self.config.fortigate.ami_id):
                return False
            click.echo(f"✅ Using specified AMI: {self.config.fortigate.ami_id}")
        
        else:
            click.echo("❌ No AMI specified and auto-discovery disabled")
            return False
        
        return True
    
    def validate_licensing(self) -> bool:
        """Validate licensing configuration"""
        if self.config.fortigate.licensing.type.upper() == "BYOL":
            click.echo("🔐 Validating BYOL licensing configuration...")
            
            # Check if license sources are configured
            has_secrets = (self.config.fortigate.licensing.primary_license_secret and 
                          self.config.fortigate.licensing.backup_license_secret)
            has_s3 = (self.config.fortigate.licensing.license_s3_bucket and
                     self.config.fortigate.licensing.primary_license_s3_key and
                     self.config.fortigate.licensing.backup_license_s3_key)
            
            if not has_secrets and not has_s3:
                click.echo("❌ BYOL licensing requires license file sources (Secrets Manager or S3)")
                return False
            
            # Validate license retrieval
            if has_secrets:
                primary_license = self.license_manager.get_license_from_secrets_manager(
                    self.config.fortigate.licensing.primary_license_secret
                )
                backup_license = self.license_manager.get_license_from_secrets_manager(
                    self.config.fortigate.licensing.backup_license_secret
                )
                
                if not primary_license or not backup_license:
                    click.echo("❌ Failed to retrieve licenses from Secrets Manager")
                    return False
                
                if not (self.license_manager.validate_license_format(primary_license) and
                       self.license_manager.validate_license_format(backup_license)):
                    click.echo("❌ License format validation failed")
                    return False
            
            elif has_s3:
                primary_license = self.license_manager.get_license_from_s3(
                    self.config.fortigate.licensing.license_s3_bucket,
                    self.config.fortigate.licensing.primary_license_s3_key
                )
                backup_license = self.license_manager.get_license_from_s3(
                    self.config.fortigate.licensing.license_s3_bucket,
                    self.config.fortigate.licensing.backup_license_s3_key
                )
                
                if not primary_license or not backup_license:
                    click.echo("❌ Failed to retrieve licenses from S3")
                    return False
                
                if not (self.license_manager.validate_license_format(primary_license) and
                       self.license_manager.validate_license_format(backup_license)):
                    click.echo("❌ License format validation failed")
                    return False
            
            click.echo("✅ BYOL licensing configuration validated")
        
        elif self.config.fortigate.licensing.type.upper() in ["ONDEMAND", "RESERVED"]:
            click.echo(f"✅ Using {self.config.fortigate.licensing.type} licensing (no license files required)")
        
        else:
            click.echo(f"❌ Invalid licensing type: {self.config.fortigate.licensing.type}")
            return False
        
        return True
    
    def validate_configuration(self, skip_validation: bool = False) -> bool:
        """Validate all configuration parameters"""
        if skip_validation:
            click.echo("⚠️  Skipping AWS validation (--skip-validation flag set)")
            click.echo("⚠️  Terraform will validate resources during deployment")
            
            # Still need to set AMI ID if using discovery
            if self.config.fortigate.ami_discovery.enabled and not self.config.fortigate.ami_id:
                click.echo("❌ AMI ID required when skipping validation with auto-discovery disabled")
                click.echo("💡 Provide AMI ID manually or remove --skip-validation flag")
                return False
            
            # Basic checks that don't require AWS API
            if not self.config.fortigate.ami_id:
                click.echo("❌ AMI ID is required")
                return False
            
            click.echo("✅ Basic configuration checks passed (AWS validation skipped)")
            return True
        
        click.echo("🔍 Validating deployment configuration...")
        
        # Resolve AMI ID first
        if not self.resolve_ami_id():
            return False
        
        # Validate licensing
        if not self.validate_licensing():
            return False
        
        # Validate VPC
        if not self.validator.validate_vpc(self.config.network.vpc_id):
            return False
        
        # Validate subnets
        all_subnets = [
            self.config.network.outside_subnet_primary,
            self.config.network.inside_subnet_primary,
            self.config.network.ha_subnet_primary,
            self.config.network.mgmt_subnet_primary,
            self.config.network.outside_subnet_backup,
            self.config.network.inside_subnet_backup,
            self.config.network.ha_subnet_backup,
            self.config.network.mgmt_subnet_backup,
        ]
        
        if not self.validator.validate_subnets(all_subnets, self.config.network.availability_zones):
            return False
        
        # Validate Transit Gateway if using existing
        if not self.config.transit_gateway.create_new:
            if not self.config.transit_gateway.transit_gateway_id:
                click.echo("❌ Transit Gateway ID required when not creating new Transit Gateway")
                return False
            if not self.validator.validate_transit_gateway(self.config.transit_gateway.transit_gateway_id):
                return False
        
        # Validate Key Pair
        if not self.validator.validate_key_pair(self.config.fortigate.key_pair_name):
            return False
        
        click.echo("✅ All configuration parameters validated successfully")
        return True
    
    def run_analysis_validation(self) -> bool:
        """Run FortiGate Terraform Analysis System validation"""
        if not ANALYSIS_AVAILABLE:
            click.echo("⚠️  FortiGate Analysis System not available, skipping validation")
            return True
        
        click.echo("🔍 Running FortiGate Terraform Analysis validation...")
        
        try:
            # Generate tfvars file for analysis
            self.terraform.generate_tfvars(self.config)
            
            # Initialize analysis engine
            engine = AnalysisEngine()
            engine.set_scanner(RepositoryScanner())
            engine.set_security_analyzer(SecurityAnalyzer())
            engine.set_best_practices_validator(BestPracticesValidator())
            
            # Analyze the terraform directory
            report = engine.analyze_repository(self.terraform_dir)
            
            # Check for critical issues
            critical_issues = [
                issue for issue in report.security_issues 
                if issue.severity.value == 'CRITICAL'
            ]
            
            if critical_issues:
                click.echo(f"❌ Found {len(critical_issues)} critical security issues:")
                for issue in critical_issues[:5]:  # Show first 5
                    click.echo(f"  • {issue.description}")
                    click.echo(f"    File: {issue.file_path}:{issue.line_number}")
                    click.echo(f"    Recommendation: {issue.recommendation}")
                return False
            
            click.echo(f"✅ Analysis completed successfully")
            click.echo(f"  • Security issues: {len(report.security_issues)}")
            click.echo(f"  • Best practice violations: {len(report.best_practice_violations)}")
            
            return True
            
        except Exception as e:
            click.echo(f"⚠️  Analysis validation failed: {e}")
            return True  # Don't fail deployment on analysis errors
    
    def plan(self) -> bool:
        """Generate deployment plan"""
        click.echo("📋 Generating Terraform deployment plan...")
        
        # Generate tfvars file
        self.terraform.generate_tfvars(self.config)
        
        # Initialize Terraform
        if not self.terraform.init():
            return False
        
        # Generate plan
        return self.terraform.plan(str(self.terraform.tfvars_file))
    
    def deploy(self, skip_validation: bool = False) -> bool:
        """Execute deployment"""
        click.echo("🚀 Starting FortiGate HA deployment...")
        
        # Validate configuration
        if not self.validate_configuration(skip_validation=skip_validation):
            return False
        
        # Run analysis validation (skip if validation is disabled)
        if not skip_validation:
            if not self.run_analysis_validation():
                return False
        else:
            click.echo("⚠️  Skipping analysis validation")
        
        # Generate plan
        if not self.plan():
            return False
        
        # Confirm deployment
        if not click.confirm("Do you want to proceed with the deployment?"):
            click.echo("Deployment cancelled by user")
            return False
        
        # Apply plan
        return self.terraform.apply()
    
    def destroy(self) -> bool:
        """Destroy deployment"""
        click.echo("💥 Destroying FortiGate HA deployment...")
        
        # Generate tfvars file
        self.terraform.generate_tfvars(self.config)
        
        # Confirm destruction
        if not click.confirm("Are you sure you want to destroy all resources? This cannot be undone!"):
            click.echo("Destruction cancelled by user")
            return False
        
        return self.terraform.destroy(str(self.terraform.tfvars_file))


def prompt_aws_config() -> AWSConfig:
    """Prompt user for AWS configuration"""
    click.echo("\n🔧 AWS Configuration")
    click.echo("=" * 50)
    
    region = click.prompt("AWS Region", default="us-east-1")
    
    use_profile = click.confirm("Use AWS profile?", default=True)
    
    if use_profile:
        profile = click.prompt("AWS Profile name", default="default")
        return AWSConfig(region=region, profile=profile)
    else:
        access_key = click.prompt("AWS Access Key ID")
        secret_key = getpass("AWS Secret Access Key: ")
        return AWSConfig(
            region=region,
            access_key_id=access_key,
            secret_access_key=secret_key
        )


def prompt_network_config() -> NetworkConfig:
    """Prompt user for network configuration"""
    click.echo("\n🌐 Network Configuration")
    click.echo("=" * 50)
    
    vpc_id = click.prompt("VPC ID (pre-assigned)")
    
    click.echo("\nAvailability Zones (need 2 for HA):")
    az1 = click.prompt("Primary AZ", default="us-east-1a")
    az2 = click.prompt("Backup AZ", default="us-east-1b")
    
    click.echo("\nSubnet IDs (pre-assigned by network team):")
    click.echo("Primary FortiGate subnets:")
    outside_primary = click.prompt("  Outside subnet ID")
    inside_primary = click.prompt("  Inside subnet ID")
    ha_primary = click.prompt("  HA subnet ID")
    mgmt_primary = click.prompt("  Management subnet ID")
    
    click.echo("Backup FortiGate subnets:")
    outside_backup = click.prompt("  Outside subnet ID")
    inside_backup = click.prompt("  Inside subnet ID")
    ha_backup = click.prompt("  HA subnet ID")
    mgmt_backup = click.prompt("  Management subnet ID")
    
    click.echo("\nManagement Access:")
    mgmt_cidrs_input = click.prompt("Management access CIDRs (comma-separated)", default="10.0.0.0/8")
    mgmt_cidrs = [cidr.strip() for cidr in mgmt_cidrs_input.split(",")]
    
    return NetworkConfig(
        vpc_id=vpc_id,
        availability_zones=[az1, az2],
        outside_subnet_primary=outside_primary,
        inside_subnet_primary=inside_primary,
        ha_subnet_primary=ha_primary,
        mgmt_subnet_primary=mgmt_primary,
        outside_subnet_backup=outside_backup,
        inside_subnet_backup=inside_backup,
        ha_subnet_backup=ha_backup,
        mgmt_subnet_backup=mgmt_backup,
        mgmt_access_cidrs=mgmt_cidrs
    )


def prompt_fortigate_config(aws_session: Optional[boto3.Session]) -> FortiGateConfig:
    """Prompt user for FortiGate configuration"""
    click.echo("\n🛡️  FortiGate Configuration")
    click.echo("=" * 50)
    
    # AMI Discovery Configuration
    click.echo("\nAMI Configuration:")
    use_auto_discovery = click.confirm("Auto-discover FortiGate AMI?", default=True)
    
    ami_id = None
    ami_discovery_config = None
    
    if use_auto_discovery:
        if aws_session is None:
            click.echo("❌ Auto-discovery requires AWS credentials (not available with --skip-validation)")
            click.echo("💡 Please provide AMI ID manually")
            use_auto_discovery = False
            ami_id = click.prompt("FortiGate AMI ID")
            license_type = click.prompt(
                "License type", 
                type=click.Choice(['BYOL', 'OnDemand', 'Reserved'], case_sensitive=False),
                default="BYOL"
            )
            ami_discovery_config = AMIDiscoveryConfig(
                enabled=False,
                version="7.4",
                license_type=license_type,
                architecture="x86_64"
            )
        else:
            # Show available versions
            ami_discovery = AMIDiscovery(aws_session)
            available_versions = ami_discovery.list_available_versions()
            
            if available_versions:
                click.echo(f"Available FortiGate versions: {', '.join(available_versions)}")
                version = click.prompt("FortiGate version", default=available_versions[0])
            else:
                version = click.prompt("FortiGate version", default="7.4")
            
            license_type = click.prompt(
                "License type", 
                type=click.Choice(['BYOL', 'OnDemand', 'Reserved'], case_sensitive=False),
                default="BYOL"
            )
            
            ami_discovery_config = AMIDiscoveryConfig(
                enabled=True,
                version=version,
                license_type=license_type,
                architecture="x86_64"
            )
    else:
        ami_id = click.prompt("FortiGate AMI ID")
        license_type = click.prompt(
            "License type", 
            type=click.Choice(['BYOL', 'OnDemand', 'Reserved'], case_sensitive=False),
            default="BYOL"
        )
        
        ami_discovery_config = AMIDiscoveryConfig(
            enabled=False,
            version="7.4",
            license_type=license_type,
            architecture="x86_64"
        )
    
    # Licensing Configuration
    click.echo(f"\nLicensing Configuration ({license_type}):")
    licensing_config = None
    
    if license_type.upper() == "BYOL":
        license_source = click.prompt(
            "License source",
            type=click.Choice(['secrets-manager', 's3'], case_sensitive=False),
            default="secrets-manager"
        )
        
        if license_source == "secrets-manager":
            primary_secret = click.prompt("Primary FortiGate license secret name", default="fortigate/primary/license")
            backup_secret = click.prompt("Backup FortiGate license secret name", default="fortigate/backup/license")
            
            licensing_config = LicensingConfig(
                type="BYOL",
                primary_license_secret=primary_secret,
                backup_license_secret=backup_secret
            )
        else:  # s3
            bucket = click.prompt("S3 bucket name")
            primary_key = click.prompt("Primary license S3 key", default="licenses/fortigate-primary.lic")
            backup_key = click.prompt("Backup license S3 key", default="licenses/fortigate-backup.lic")
            
            licensing_config = LicensingConfig(
                type="BYOL",
                license_s3_bucket=bucket,
                primary_license_s3_key=primary_key,
                backup_license_s3_key=backup_key
            )
    else:
        licensing_config = LicensingConfig(type=license_type)
    
    # Instance Configuration
    click.echo("\nInstance Configuration:")
    instance_type = click.prompt("Instance type", default="c5.xlarge")
    key_pair = click.prompt("EC2 Key Pair name")
    
    admin_password = getpass("Admin password (min 8 chars): ")
    while len(admin_password) < 8:
        click.echo("Password must be at least 8 characters long")
        admin_password = getpass("Admin password (min 8 chars): ")
    
    ha_password = getpass("HA synchronization password (min 8 chars): ")
    while len(ha_password) < 8:
        click.echo("Password must be at least 8 characters long")
        ha_password = getpass("HA synchronization password (min 8 chars): ")
    
    hostname_primary = click.prompt("Primary hostname", default="fortigate-primary")
    hostname_backup = click.prompt("Backup hostname", default="fortigate-backup")
    
    return FortiGateConfig(
        ami_id=ami_id,
        ami_discovery=ami_discovery_config,
        licensing=licensing_config,
        instance_type=instance_type,
        key_pair_name=key_pair,
        admin_password=admin_password,
        ha_password=ha_password,
        hostname_primary=hostname_primary,
        hostname_backup=hostname_backup
    )


def prompt_transit_gateway_config() -> TransitGatewayConfig:
    """Prompt user for Transit Gateway configuration"""
    click.echo("\n🌉 Transit Gateway Configuration")
    click.echo("=" * 50)
    
    create_new = click.confirm("Create new Transit Gateway?", default=False)
    
    tgw_id = None
    if not create_new:
        tgw_id = click.prompt("Existing Transit Gateway ID")
    
    bgp_asn = click.prompt("FortiGate BGP ASN", default=65000, type=int)
    tgw_asn = click.prompt("Transit Gateway ASN", default=64512, type=int)
    
    spoke_cidrs_input = click.prompt("Spoke VPC CIDRs (comma-separated)", default="10.1.0.0/16,10.2.0.0/16")
    spoke_cidrs = [cidr.strip() for cidr in spoke_cidrs_input.split(",")]
    
    return TransitGatewayConfig(
        create_new=create_new,
        transit_gateway_id=tgw_id,
        bgp_asn=bgp_asn,
        transit_gateway_asn=tgw_asn,
        spoke_vpc_cidrs=spoke_cidrs
    )


def prompt_monitoring_config() -> MonitoringConfig:
    """Prompt user for monitoring configuration"""
    click.echo("\n📊 Monitoring Configuration")
    click.echo("=" * 50)
    
    enable_flow_logs = click.confirm("Enable VPC Flow Logs?", default=True)
    log_retention = click.prompt("Log retention days", default=30, type=int)
    detailed_monitoring = click.confirm("Enable detailed EC2 monitoring?", default=True)
    
    return MonitoringConfig(
        enable_flow_logs=enable_flow_logs,
        log_retention_days=log_retention,
        enable_detailed_monitoring=detailed_monitoring
    )


@click.command()
@click.option("--config", "-c", type=click.Path(exists=True), help="Configuration file path")
@click.option("--plan-only", is_flag=True, help="Generate plan only, do not deploy")
@click.option("--destroy", is_flag=True, help="Destroy existing deployment")
@click.option("--save-config", type=click.Path(), help="Save configuration to file")
@click.option("--auto-discover-ami", is_flag=True, help="Auto-discover FortiGate AMI")
@click.option("--license-type", type=click.Choice(['BYOL', 'OnDemand', 'Reserved']), help="License type for AMI discovery")
@click.option("--fortigate-version", default="7.4", help="FortiGate version for AMI discovery")
@click.option("--list-versions", is_flag=True, help="List available FortiGate versions and exit")
@click.option("--skip-validation", is_flag=True, help="Skip AWS API validation (use when credentials are limited)")
def main(config: Optional[str], plan_only: bool, destroy: bool, save_config: Optional[str], 
         auto_discover_ami: bool, license_type: Optional[str], fortigate_version: str, 
         list_versions: bool, skip_validation: bool):
    """FortiGate AWS HA Deployment Script"""
    
    click.echo("🛡️  FortiGate AWS HA Deployment")
    click.echo("=" * 50)
    
    # Show warning if skip-validation is used
    if skip_validation:
        click.echo("⚠️  WARNING: AWS validation is disabled")
        click.echo("⚠️  Terraform will validate resources during deployment")
        click.echo("⚠️  Ensure your configuration is correct!")
        click.echo()
    
    # Handle list-versions option
    if list_versions:
        if skip_validation:
            click.echo("❌ Cannot list versions with --skip-validation (requires AWS API access)")
            sys.exit(1)
        
        try:
            session = boto3.Session()
            ami_discovery = AMIDiscovery(session)
            versions = ami_discovery.list_available_versions()
            
            if versions:
                click.echo("Available FortiGate versions:")
                for version in versions:
                    click.echo(f"  • {version}")
            else:
                click.echo("No FortiGate versions found")
            
            return
        except Exception as e:
            click.echo(f"❌ Error listing versions: {e}")
            sys.exit(1)
    
    # Handle auto-discover-ami option
    if auto_discover_ami and not config:
        if skip_validation:
            click.echo("❌ Cannot auto-discover AMI with --skip-validation (requires AWS API access)")
            click.echo("💡 Find AMI ID manually using AWS Console and provide it when prompted")
            sys.exit(1)
        
        try:
            session = boto3.Session()
            ami_discovery = AMIDiscovery(session)
            
            ami_id = ami_discovery.find_latest_ami(
                version=fortigate_version,
                license_type=license_type or "BYOL",
                architecture="x86_64"
            )
            
            if ami_id:
                click.echo(f"✅ Discovered AMI: {ami_id}")
                click.echo("Use this AMI ID in your configuration file or interactive session")
            else:
                click.echo("❌ No suitable AMI found")
            
            return
        except Exception as e:
            click.echo(f"❌ Error discovering AMI: {e}")
            sys.exit(1)
    
    # Load or prompt for configuration
    if config:
        click.echo(f"Loading configuration from {config}")
        with open(config, 'r') as f:
            if config.endswith('.yaml') or config.endswith('.yml'):
                config_data = yaml.safe_load(f)
            else:
                config_data = json.load(f)
        
        # Convert to DeploymentConfig (simplified for demo)
        deployment_config = DeploymentConfig(**config_data)
    else:
        # Interactive prompts
        aws_config = prompt_aws_config()
        network_config = prompt_network_config()
        
        # Create session for FortiGate config prompts (only if not skipping validation)
        if skip_validation:
            fortigate_config = prompt_fortigate_config(None)
        else:
            fortigate_config = prompt_fortigate_config(
                boto3.Session(profile_name=aws_config.profile) if aws_config.profile 
                else boto3.Session(region_name=aws_config.region)
            )
        
        tgw_config = prompt_transit_gateway_config()
        monitoring_config = prompt_monitoring_config()
        
        environment = click.prompt("Environment", default="prod")
        owner_tag = click.prompt("Owner tag", default="NetworkTeam")
        
        deployment_config = DeploymentConfig(
            aws=aws_config,
            network=network_config,
            fortigate=fortigate_config,
            transit_gateway=tgw_config,
            monitoring=monitoring_config,
            environment=environment,
            owner_tag=owner_tag
        )
    
    # Save configuration if requested
    if save_config:
        config_dict = asdict(deployment_config)
        # Remove sensitive data
        config_dict['fortigate']['admin_password'] = "***REDACTED***"
        config_dict['fortigate']['ha_password'] = "***REDACTED***"
        
        with open(save_config, 'w') as f:
            if save_config.endswith('.yaml') or save_config.endswith('.yml'):
                yaml.dump(config_dict, f, default_flow_style=False)
            else:
                json.dump(config_dict, f, indent=2)
        click.echo(f"✅ Configuration saved to {save_config}")
    
    # Initialize deployment engine
    engine = DeploymentEngine(deployment_config)
    
    try:
        if destroy:
            success = engine.destroy()
        elif plan_only:
            success = engine.plan()
        else:
            success = engine.deploy(skip_validation=skip_validation)
        
        if success:
            click.echo("✅ Operation completed successfully!")
            if not destroy and not plan_only:
                click.echo("\n🎉 FortiGate HA deployment completed!")
                click.echo("Next steps:")
                click.echo("1. Verify FortiGate instances are running")
                click.echo("2. Check HA status via management interface")
                click.echo("3. Verify BGP sessions with Transit Gateway")
                click.echo("4. Test traffic flow from spoke VPCs")
        else:
            click.echo("❌ Operation failed!")
            sys.exit(1)
            
    except KeyboardInterrupt:
        click.echo("\n⚠️  Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()