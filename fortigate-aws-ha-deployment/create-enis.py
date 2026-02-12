#!/usr/bin/env python3
"""
Create Network Interfaces for FortiGate HA Deployment

This script creates 8 ENIs (4 for primary, 4 for backup FortiGate) with static IPs.

Usage:
    python3 create-enis.py --profile <aws-profile> --region <region> --account <account-id>
    python3 create-enis.py --profile default --region us-east-1 --account 678632990402
"""

import boto3
import json
import argparse
import sys
from typing import Dict, List, Tuple

# Subnet definitions - will be populated interactively
SUBNETS = {
    "primary": {
        "outside": None,
        "inside": None,
        "ha": None,
        "mgmt": None
    },
    "backup": {
        "outside": None,
        "inside": None,
        "ha": None,
        "mgmt": None
    }
}

# Tags
TAGS = [
    {"Key": "Project", "Value": "FortiGate-HA-Deployment"},
    {"Key": "ManagedBy", "Value": "Terraform"},
    {"Key": "Environment", "Value": "prod"},
    {"Key": "Owner", "Value": "NetworkTeam"}
]


def validate_subnet_id(subnet_id: str) -> bool:
    """Validate subnet ID format"""
    import re
    pattern = r'^subnet-[a-f0-9]{8,17}$'
    return bool(re.match(pattern, subnet_id))


def prompt_for_subnets() -> Dict:
    """Interactively prompt user for subnet IDs"""
    print("\n📋 Subnet Configuration")
    print("=" * 70)
    print("Please provide the subnet IDs for each FortiGate interface.")
    print("Subnet IDs should be in the format: subnet-xxxxxxxxx")
    print()
    
    subnets = {
        "primary": {},
        "backup": {}
    }
    
    # Prompt for Primary FortiGate subnets
    print("🔵 Primary FortiGate Subnets:")
    print("-" * 70)
    
    for interface_type in ["outside", "inside", "ha", "mgmt"]:
        while True:
            subnet_id = input(f"  {interface_type.capitalize():10} subnet ID: ").strip()
            if validate_subnet_id(subnet_id):
                subnets["primary"][interface_type] = subnet_id
                break
            else:
                print(f"  ❌ Invalid subnet ID format. Expected: subnet-xxxxxxxxx")
    
    print()
    
    # Prompt for Backup FortiGate subnets
    print("🟢 Backup FortiGate Subnets:")
    print("-" * 70)
    
    for interface_type in ["outside", "inside", "ha", "mgmt"]:
        while True:
            subnet_id = input(f"  {interface_type.capitalize():10} subnet ID: ").strip()
            if validate_subnet_id(subnet_id):
                subnets["backup"][interface_type] = subnet_id
                break
            else:
                print(f"  ❌ Invalid subnet ID format. Expected: subnet-xxxxxxxxx")
    
    print()
    
    # Display summary for confirmation
    print("📋 Subnet Summary:")
    print("-" * 70)
    print("\nPrimary FortiGate:")
    for interface_type, subnet_id in subnets["primary"].items():
        print(f"  {interface_type.capitalize():10} - {subnet_id}")
    
    print("\nBackup FortiGate:")
    for interface_type, subnet_id in subnets["backup"].items():
        print(f"  {interface_type.capitalize():10} - {subnet_id}")
    
    print()
    
    # Confirm
    while True:
        confirm = input("Is this configuration correct? (yes/no): ").strip().lower()
        if confirm in ['yes', 'y']:
            return subnets
        elif confirm in ['no', 'n']:
            print("\n🔄 Let's try again...\n")
            return prompt_for_subnets()
        else:
            print("Please enter 'yes' or 'no'")


def get_subnet_info(ec2_client, subnet_id: str) -> Dict:
    """Get subnet information including CIDR block"""
    response = ec2_client.describe_subnets(SubnetIds=[subnet_id])
    subnet = response['Subnets'][0]
    return {
        'subnet_id': subnet['SubnetId'],
        'cidr_block': subnet['CidrBlock'],
        'vpc_id': subnet['VpcId'],
        'availability_zone': subnet['AvailabilityZone']
    }


def calculate_static_ip(cidr_block: str, offset: int = 10) -> str:
    """Calculate a static IP address within the subnet CIDR"""
    import ipaddress
    network = ipaddress.IPv4Network(cidr_block)
    # Use the 10th IP in the subnet (avoiding gateway at .1)
    return str(network.network_address + offset)


def get_or_create_security_groups(ec2_client, vpc_id: str) -> Dict[str, str]:
    """Get or create security groups for FortiGate interfaces"""
    security_groups = {}
    
    # Define security group configurations
    sg_configs = {
        "mgmt": {
            "name": "fortigate-mgmt-sg",
            "description": "Security group for FortiGate management interface",
            "ingress": [
                {"protocol": "tcp", "port": 443, "cidr": "10.0.0.0/8"},
                {"protocol": "tcp", "port": 22, "cidr": "10.0.0.0/8"}
            ]
        },
        "data": {
            "name": "fortigate-data-sg",
            "description": "Security group for FortiGate data plane interfaces",
            "ingress": [
                {"protocol": "-1", "port": -1, "cidr": "0.0.0.0/0"}
            ]
        },
        "ha": {
            "name": "fortigate-ha-sg",
            "description": "Security group for FortiGate HA synchronization",
            "ingress": [
                {"protocol": "-1", "port": -1, "cidr": "0.0.0.0/0"}
            ]
        }
    }
    
    for sg_type, config in sg_configs.items():
        # Check if security group exists
        try:
            response = ec2_client.describe_security_groups(
                Filters=[
                    {"Name": "group-name", "Values": [config["name"]]},
                    {"Name": "vpc-id", "Values": [vpc_id]}
                ]
            )
            
            if response['SecurityGroups']:
                sg_id = response['SecurityGroups'][0]['GroupId']
                print(f"✅ Using existing security group: {config['name']} ({sg_id})")
                security_groups[sg_type] = sg_id
            else:
                # Create security group
                response = ec2_client.create_security_group(
                    GroupName=config["name"],
                    Description=config["description"],
                    VpcId=vpc_id
                )
                sg_id = response['GroupId']
                print(f"✅ Created security group: {config['name']} ({sg_id})")
                
                # Add ingress rules
                for rule in config["ingress"]:
                    if rule["protocol"] == "-1":
                        ec2_client.authorize_security_group_ingress(
                            GroupId=sg_id,
                            IpPermissions=[{
                                'IpProtocol': '-1',
                                'IpRanges': [{'CidrIp': rule["cidr"]}]
                            }]
                        )
                    else:
                        ec2_client.authorize_security_group_ingress(
                            GroupId=sg_id,
                            IpPermissions=[{
                                'IpProtocol': rule["protocol"],
                                'FromPort': rule["port"],
                                'ToPort': rule["port"],
                                'IpRanges': [{'CidrIp': rule["cidr"]}]
                            }]
                        )
                
                # Tag security group
                ec2_client.create_tags(Resources=[sg_id], Tags=TAGS)
                security_groups[sg_type] = sg_id
                
        except Exception as e:
            print(f"❌ Error with security group {config['name']}: {e}")
            raise
    
    return security_groups


def create_network_interface(
    ec2_client,
    subnet_id: str,
    private_ip: str,
    security_group_ids: List[str],
    description: str,
    interface_type: str,
    fortigate_type: str
) -> str:
    """Create a network interface with static IP"""
    try:
        response = ec2_client.create_network_interface(
            SubnetId=subnet_id,
            PrivateIpAddress=private_ip,
            Description=description,
            Groups=security_group_ids
        )
        
        eni_id = response['NetworkInterface']['NetworkInterfaceId']
        
        # Disable source/dest check for routing
        ec2_client.modify_network_interface_attribute(
            NetworkInterfaceId=eni_id,
            SourceDestCheck={'Value': False}
        )
        
        # Tag the ENI
        tags = TAGS + [
            {"Key": "Name", "Value": f"fortigate-{fortigate_type}-{interface_type}"},
            {"Key": "Interface", "Value": interface_type},
            {"Key": "FortiGateRole", "Value": fortigate_type}
        ]
        ec2_client.create_tags(Resources=[eni_id], Tags=tags)
        
        print(f"✅ Created ENI: {eni_id} ({description}) - IP: {private_ip}")
        return eni_id
        
    except Exception as e:
        print(f"❌ Error creating ENI for {description}: {e}")
        raise


def main():
    """Main execution function"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description='Create Network Interfaces for FortiGate HA Deployment',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Using AWS profile
  python3 create-enis.py --profile myprofile --region us-east-1 --account 678632990402
  
  # Using default profile
  python3 create-enis.py --region us-east-1 --account 678632990402
  
  # Using environment variables (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
  python3 create-enis.py --region us-east-1 --account 678632990402
        """
    )
    parser.add_argument(
        '--profile',
        type=str,
        help='AWS CLI profile name (optional, uses default credentials if not specified)'
    )
    parser.add_argument(
        '--region',
        type=str,
        default='us-east-1',
        help='AWS region (default: us-east-1)'
    )
    parser.add_argument(
        '--account',
        type=str,
        required=True,
        help='AWS account ID (required)'
    )
    parser.add_argument(
        '--subnet-file',
        type=str,
        help='JSON file with subnet IDs (optional, will prompt if not provided)'
    )
    
    args = parser.parse_args()
    
    print("🚀 Creating Network Interfaces for FortiGate HA Deployment")
    print("=" * 70)
    print(f"Region: {args.region}")
    print(f"Account: {args.account}")
    if args.profile:
        print(f"Profile: {args.profile}")
    print()
    
    # Initialize boto3 session and client
    try:
        if args.profile:
            session = boto3.Session(profile_name=args.profile, region_name=args.region)
            print(f"✅ Using AWS profile: {args.profile}")
        else:
            session = boto3.Session(region_name=args.region)
            print("✅ Using default AWS credentials")
        
        ec2_client = session.client('ec2')
        
        # Verify credentials by getting caller identity
        sts_client = session.client('sts')
        identity = sts_client.get_caller_identity()
        print(f"✅ Authenticated as: {identity['Arn']}")
        print(f"✅ Account ID: {identity['Account']}")
        
        if identity['Account'] != args.account:
            print(f"⚠️  WARNING: Authenticated account ({identity['Account']}) differs from specified account ({args.account})")
            response = input("Continue anyway? (yes/no): ")
            if response.lower() != 'yes':
                print("❌ Operation cancelled")
                return
        
        print()
        
    except Exception as e:
        print(f"❌ Error authenticating with AWS: {e}")
        print("\nTroubleshooting:")
        print("  1. Check your AWS credentials are configured:")
        print("     - Run 'aws configure' to set up credentials")
        print("     - Or set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables")
        print("  2. If using --profile, ensure the profile exists in ~/.aws/credentials")
        print("  3. Verify your credentials have EC2 permissions")
        return
    
    # Get subnet IDs - either from file or interactive prompt
    if args.subnet_file:
        try:
            print(f"📂 Loading subnet configuration from: {args.subnet_file}")
            with open(args.subnet_file, 'r') as f:
                subnet_config = json.load(f)
            
            # Validate the structure
            if 'primary' not in subnet_config or 'backup' not in subnet_config:
                print("❌ Invalid subnet file format. Expected 'primary' and 'backup' keys.")
                return
            
            SUBNETS['primary'] = subnet_config['primary']
            SUBNETS['backup'] = subnet_config['backup']
            print("✅ Subnet configuration loaded successfully")
            print()
            
        except FileNotFoundError:
            print(f"❌ Subnet file not found: {args.subnet_file}")
            return
        except json.JSONDecodeError:
            print(f"❌ Invalid JSON format in subnet file: {args.subnet_file}")
            return
    else:
        # Interactive prompt for subnet IDs
        subnet_config = prompt_for_subnets()
        SUBNETS['primary'] = subnet_config['primary']
        SUBNETS['backup'] = subnet_config['backup']
        
        # Optionally save the configuration
        save_config = input("Would you like to save this subnet configuration to a file? (yes/no): ").strip().lower()
        if save_config in ['yes', 'y']:
            config_file = input("Enter filename (default: subnet-config.json): ").strip() or "subnet-config.json"
            try:
                with open(config_file, 'w') as f:
                    json.dump(subnet_config, f, indent=2)
                print(f"✅ Subnet configuration saved to: {config_file}")
                print(f"   You can reuse it with: --subnet-file {config_file}")
            except Exception as e:
                print(f"⚠️  Could not save configuration: {e}")
        print()
    
    # Get VPC ID from first subnet
    try:
        first_subnet = get_subnet_info(ec2_client, SUBNETS["primary"]["outside"])
        vpc_id = first_subnet['vpc_id']
        print(f"VPC ID: {vpc_id}")
        print()
    except Exception as e:
        print(f"❌ Error getting subnet information: {e}")
        print("\nPlease verify:")
        print("  1. The subnet IDs are correct")
        print("  2. The subnets exist in the specified region")
        print("  3. Your credentials have permission to describe subnets")
        return
    
    # Get or create security groups
    try:
        print("🔒 Setting up security groups...")
        security_groups = get_or_create_security_groups(ec2_client, vpc_id)
        print()
    except Exception as e:
        print(f"❌ Error setting up security groups: {e}")
        print("\nPlease verify your credentials have permission to:")
        print("  1. Describe security groups")
        print("  2. Create security groups")
        print("  3. Authorize security group ingress rules")
        return
    
    # Store created ENI IDs
    eni_ids = {}
    
    # Create ENIs for Primary FortiGate
    print("🔧 Creating ENIs for Primary FortiGate...")
    for interface_type, subnet_id in SUBNETS["primary"].items():
        subnet_info = get_subnet_info(ec2_client, subnet_id)
        static_ip = calculate_static_ip(subnet_info['cidr_block'])
        
        # Determine security groups for this interface
        if interface_type == "mgmt":
            sg_ids = [security_groups["mgmt"]]
        elif interface_type == "ha":
            sg_ids = [security_groups["ha"]]
        else:  # outside, inside
            sg_ids = [security_groups["data"]]
        
        description = f"FortiGate Primary {interface_type.upper()} interface"
        
        eni_id = create_network_interface(
            ec2_client,
            subnet_id,
            static_ip,
            sg_ids,
            description,
            interface_type,
            "primary"
        )
        
        eni_ids[f"primary_{interface_type}"] = {
            "eni_id": eni_id,
            "private_ip": static_ip,
            "subnet_id": subnet_id,
            "az": subnet_info['availability_zone']
        }
    
    print()
    
    # Create ENIs for Backup FortiGate
    print("🔧 Creating ENIs for Backup FortiGate...")
    for interface_type, subnet_id in SUBNETS["backup"].items():
        subnet_info = get_subnet_info(ec2_client, subnet_id)
        static_ip = calculate_static_ip(subnet_info['cidr_block'])
        
        # Determine security groups for this interface
        if interface_type == "mgmt":
            sg_ids = [security_groups["mgmt"]]
        elif interface_type == "ha":
            sg_ids = [security_groups["ha"]]
        else:  # outside, inside
            sg_ids = [security_groups["data"]]
        
        description = f"FortiGate Backup {interface_type.upper()} interface"
        
        eni_id = create_network_interface(
            ec2_client,
            subnet_id,
            static_ip,
            sg_ids,
            description,
            interface_type,
            "backup"
        )
        
        eni_ids[f"backup_{interface_type}"] = {
            "eni_id": eni_id,
            "private_ip": static_ip,
            "subnet_id": subnet_id,
            "az": subnet_info['availability_zone']
        }
    
    print()
    print("=" * 70)
    print("✅ All ENIs created successfully!")
    print()
    
    # Print summary
    print("📋 ENI Summary:")
    print("-" * 70)
    print("\nPrimary FortiGate ENIs:")
    for interface_type in ["outside", "inside", "ha", "mgmt"]:
        key = f"primary_{interface_type}"
        info = eni_ids[key]
        print(f"  {interface_type.upper():10} - {info['eni_id']} - {info['private_ip']}")
    
    print("\nBackup FortiGate ENIs:")
    for interface_type in ["outside", "inside", "ha", "mgmt"]:
        key = f"backup_{interface_type}"
        info = eni_ids[key]
        print(f"  {interface_type.upper():10} - {info['eni_id']} - {info['private_ip']}")
    
    print()
    print("-" * 70)
    
    # Save ENI IDs to file for Terraform
    output_file = "eni-ids.json"
    with open(output_file, 'w') as f:
        json.dump(eni_ids, f, indent=2)
    print(f"💾 ENI details saved to: {output_file}")
    
    # Generate Terraform variable snippet
    print()
    print("📝 Terraform Variables (add to terraform.tfvars):")
    print("-" * 70)
    print(f'primary_outside_eni_id = "{eni_ids["primary_outside"]["eni_id"]}"')
    print(f'primary_inside_eni_id  = "{eni_ids["primary_inside"]["eni_id"]}"')
    print(f'primary_ha_eni_id      = "{eni_ids["primary_ha"]["eni_id"]}"')
    print(f'primary_mgmt_eni_id    = "{eni_ids["primary_mgmt"]["eni_id"]}"')
    print()
    print(f'backup_outside_eni_id  = "{eni_ids["backup_outside"]["eni_id"]}"')
    print(f'backup_inside_eni_id   = "{eni_ids["backup_inside"]["eni_id"]}"')
    print(f'backup_ha_eni_id       = "{eni_ids["backup_ha"]["eni_id"]}"')
    print(f'backup_mgmt_eni_id     = "{eni_ids["backup_mgmt"]["eni_id"]}"')
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⚠️  Operation cancelled by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
