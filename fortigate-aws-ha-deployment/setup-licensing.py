#!/usr/bin/env python3
"""
FortiGate Licensing Setup Script

Helper script to set up FortiGate licenses in AWS Secrets Manager or S3.
"""

import os
import sys
import boto3
import click
from pathlib import Path
from typing import Optional


class LicenseSetup:
    """Helper class for setting up FortiGate licenses"""
    
    def __init__(self, aws_session: boto3.Session):
        self.aws_session = aws_session
        self.secrets_manager = aws_session.client('secretsmanager')
        self.s3 = aws_session.client('s3')
    
    def upload_license_to_secrets_manager(self, license_file: Path, secret_name: str) -> bool:
        """Upload license file to AWS Secrets Manager"""
        try:
            with open(license_file, 'r') as f:
                license_content = f.read()
            
            # Validate license format
            if not self._validate_license_format(license_content):
                return False
            
            # Create or update secret
            try:
                self.secrets_manager.create_secret(
                    Name=secret_name,
                    Description=f"FortiGate license file from {license_file.name}",
                    SecretString=license_content
                )
                click.echo(f"✅ Created secret: {secret_name}")
            except self.secrets_manager.exceptions.ResourceExistsException:
                # Update existing secret
                self.secrets_manager.update_secret(
                    SecretId=secret_name,
                    SecretString=license_content
                )
                click.echo(f"✅ Updated secret: {secret_name}")
            
            return True
            
        except Exception as e:
            click.echo(f"❌ Error uploading license to Secrets Manager: {e}")
            return False
    
    def upload_license_to_s3(self, license_file: Path, bucket: str, key: str) -> bool:
        """Upload license file to S3"""
        try:
            with open(license_file, 'r') as f:
                license_content = f.read()
            
            # Validate license format
            if not self._validate_license_format(license_content):
                return False
            
            # Upload to S3
            self.s3.put_object(
                Bucket=bucket,
                Key=key,
                Body=license_content,
                ContentType='text/plain',
                ServerSideEncryption='AES256'
            )
            
            click.echo(f"✅ Uploaded license to s3://{bucket}/{key}")
            return True
            
        except Exception as e:
            click.echo(f"❌ Error uploading license to S3: {e}")
            return False
    
    def _validate_license_format(self, license_content: str) -> bool:
        """Validate FortiGate license file format"""
        required_markers = ['-----BEGIN FGT VM LICENSE-----', '-----END FGT VM LICENSE-----']
        
        for marker in required_markers:
            if marker not in license_content:
                click.echo(f"❌ Invalid license format: Missing {marker}")
                return False
        
        click.echo("✅ License format validation passed")
        return True
    
    def create_s3_bucket(self, bucket_name: str, region: str) -> bool:
        """Create S3 bucket for license storage"""
        try:
            if region == 'us-east-1':
                self.s3.create_bucket(Bucket=bucket_name)
            else:
                self.s3.create_bucket(
                    Bucket=bucket_name,
                    CreateBucketConfiguration={'LocationConstraint': region}
                )
            
            # Enable encryption
            self.s3.put_bucket_encryption(
                Bucket=bucket_name,
                ServerSideEncryptionConfiguration={
                    'Rules': [{
                        'ApplyServerSideEncryptionByDefault': {
                            'SSEAlgorithm': 'AES256'
                        }
                    }]
                }
            )
            
            # Block public access
            self.s3.put_public_access_block(
                Bucket=bucket_name,
                PublicAccessBlockConfiguration={
                    'BlockPublicAcls': True,
                    'IgnorePublicAcls': True,
                    'BlockPublicPolicy': True,
                    'RestrictPublicBuckets': True
                }
            )
            
            click.echo(f"✅ Created S3 bucket: {bucket_name}")
            return True
            
        except Exception as e:
            click.echo(f"❌ Error creating S3 bucket: {e}")
            return False


@click.group()
def cli():
    """FortiGate Licensing Setup Tool"""
    pass


@cli.command()
@click.option("--primary-license", required=True, type=click.Path(exists=True), 
              help="Path to primary FortiGate license file")
@click.option("--backup-license", required=True, type=click.Path(exists=True), 
              help="Path to backup FortiGate license file")
@click.option("--primary-secret", default="fortigate/primary/license", 
              help="Secret name for primary license")
@click.option("--backup-secret", default="fortigate/backup/license", 
              help="Secret name for backup license")
@click.option("--region", default="us-east-1", help="AWS region")
@click.option("--profile", help="AWS profile to use")
def secrets_manager(primary_license: str, backup_license: str, primary_secret: str, 
                   backup_secret: str, region: str, profile: Optional[str]):
    """Upload FortiGate licenses to AWS Secrets Manager"""
    
    click.echo("🔐 Setting up FortiGate licenses in AWS Secrets Manager")
    click.echo("=" * 60)
    
    # Initialize AWS session
    if profile:
        session = boto3.Session(profile_name=profile, region_name=region)
    else:
        session = boto3.Session(region_name=region)
    
    setup = LicenseSetup(session)
    
    # Upload primary license
    click.echo(f"\n📄 Uploading primary license: {primary_license}")
    if not setup.upload_license_to_secrets_manager(Path(primary_license), primary_secret):
        sys.exit(1)
    
    # Upload backup license
    click.echo(f"\n📄 Uploading backup license: {backup_license}")
    if not setup.upload_license_to_secrets_manager(Path(backup_license), backup_secret):
        sys.exit(1)
    
    click.echo(f"\n✅ License setup completed successfully!")
    click.echo(f"\nConfiguration for deployment:")
    click.echo(f"  licensing:")
    click.echo(f"    type: BYOL")
    click.echo(f"    primary_license_secret: {primary_secret}")
    click.echo(f"    backup_license_secret: {backup_secret}")


@cli.command()
@click.option("--primary-license", required=True, type=click.Path(exists=True), 
              help="Path to primary FortiGate license file")
@click.option("--backup-license", required=True, type=click.Path(exists=True), 
              help="Path to backup FortiGate license file")
@click.option("--bucket", required=True, help="S3 bucket name")
@click.option("--primary-key", default="licenses/fortigate-primary.lic", 
              help="S3 key for primary license")
@click.option("--backup-key", default="licenses/fortigate-backup.lic", 
              help="S3 key for backup license")
@click.option("--create-bucket", is_flag=True, help="Create S3 bucket if it doesn't exist")
@click.option("--region", default="us-east-1", help="AWS region")
@click.option("--profile", help="AWS profile to use")
def s3(primary_license: str, backup_license: str, bucket: str, primary_key: str, 
       backup_key: str, create_bucket: bool, region: str, profile: Optional[str]):
    """Upload FortiGate licenses to S3"""
    
    click.echo("📦 Setting up FortiGate licenses in S3")
    click.echo("=" * 40)
    
    # Initialize AWS session
    if profile:
        session = boto3.Session(profile_name=profile, region_name=region)
    else:
        session = boto3.Session(region_name=region)
    
    setup = LicenseSetup(session)
    
    # Create bucket if requested
    if create_bucket:
        click.echo(f"\n🪣 Creating S3 bucket: {bucket}")
        if not setup.create_s3_bucket(bucket, region):
            sys.exit(1)
    
    # Upload primary license
    click.echo(f"\n📄 Uploading primary license: {primary_license}")
    if not setup.upload_license_to_s3(Path(primary_license), bucket, primary_key):
        sys.exit(1)
    
    # Upload backup license
    click.echo(f"\n📄 Uploading backup license: {backup_license}")
    if not setup.upload_license_to_s3(Path(backup_license), bucket, backup_key):
        sys.exit(1)
    
    click.echo(f"\n✅ License setup completed successfully!")
    click.echo(f"\nConfiguration for deployment:")
    click.echo(f"  licensing:")
    click.echo(f"    type: BYOL")
    click.echo(f"    license_s3_bucket: {bucket}")
    click.echo(f"    primary_license_s3_key: {primary_key}")
    click.echo(f"    backup_license_s3_key: {backup_key}")


@cli.command()
@click.option("--region", default="us-east-1", help="AWS region")
@click.option("--profile", help="AWS profile to use")
def list_amis(region: str, profile: Optional[str]):
    """List available FortiGate AMIs"""
    
    click.echo("🔍 Listing available FortiGate AMIs")
    click.echo("=" * 40)
    
    # Initialize AWS session
    if profile:
        session = boto3.Session(profile_name=profile, region_name=region)
    else:
        session = boto3.Session(region_name=region)
    
    ec2 = session.client('ec2')
    fortinet_owner_id = "679593333241"
    
    try:
        response = ec2.describe_images(
            Owners=[fortinet_owner_id],
            Filters=[
                {"Name": "name", "Values": ["FortiGate-VM64-AWS-*"]},
                {"Name": "state", "Values": ["available"]}
            ]
        )
        
        # Group by version and license type
        amis_by_version = {}
        for image in response['Images']:
            name = image['Name']
            parts = name.split('-')
            if len(parts) >= 5:
                version = parts[3]
                license_type = parts[4]
                
                if version not in amis_by_version:
                    amis_by_version[version] = {}
                
                if license_type not in amis_by_version[version]:
                    amis_by_version[version][license_type] = []
                
                amis_by_version[version][license_type].append({
                    'ami_id': image['ImageId'],
                    'name': image['Name'],
                    'created': image['CreationDate']
                })
        
        # Display results
        for version in sorted(amis_by_version.keys(), reverse=True):
            click.echo(f"\n📋 FortiGate {version}:")
            for license_type in sorted(amis_by_version[version].keys()):
                click.echo(f"  {license_type}:")
                # Sort by creation date, show latest first
                amis = sorted(amis_by_version[version][license_type], 
                            key=lambda x: x['created'], reverse=True)
                for ami in amis[:3]:  # Show top 3 most recent
                    click.echo(f"    {ami['ami_id']} - {ami['name']}")
                    click.echo(f"      Created: {ami['created']}")
        
    except Exception as e:
        click.echo(f"❌ Error listing AMIs: {e}")
        sys.exit(1)


@cli.command()
def iam_policy():
    """Generate IAM policy for FortiGate deployment"""
    
    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "secretsmanager:GetSecretValue"
                ],
                "Resource": [
                    "arn:aws:secretsmanager:*:*:secret:fortigate/*"
                ]
            },
            {
                "Effect": "Allow",
                "Action": [
                    "s3:GetObject"
                ],
                "Resource": [
                    "arn:aws:s3:::your-license-bucket/licenses/*"
                ]
            },
            {
                "Effect": "Allow",
                "Action": [
                    "ec2:DescribeImages",
                    "ec2:DescribeInstances",
                    "ec2:DescribeVpcs",
                    "ec2:DescribeSubnets",
                    "ec2:DescribeTransitGateways",
                    "ec2:DescribeKeyPairs"
                ],
                "Resource": "*"
            }
        ]
    }
    
    click.echo("📋 IAM Policy for FortiGate Deployment:")
    click.echo("=" * 45)
    
    import json
    click.echo(json.dumps(policy, indent=2))
    
    click.echo("\n💡 Usage:")
    click.echo("1. Create an IAM policy with the above JSON")
    click.echo("2. Attach the policy to your deployment user/role")
    click.echo("3. Update S3 bucket name in the policy if using S3 for licenses")


if __name__ == "__main__":
    cli()