#!/usr/bin/env python3
"""
Delete Network Interfaces and Associated Resources for FortiGate HA Deployment

This script deletes all resources created by create-enis.py by finding them
using the CreatedBy tag.

Usage:
    python3 delete-enis.py --profile <aws-profile> --region <region> --tag <tag-value>
    python3 delete-enis.py --profile renaws --region us-east-1 --tag "deployment-001"
"""

import boto3
import argparse
import sys
import time
from typing import List, Dict, Tuple

def confirm_deletion(resource_count: int, tag_value: str) -> bool:
    """Ask user to confirm deletion"""
    print("\n" + "=" * 70)
    print("⚠️  WARNING: DESTRUCTIVE OPERATION")
    print("=" * 70)
    print(f"\nYou are about to DELETE {resource_count} resources with tag:")
    print(f"  CreatedBy = {tag_value}")
    print("\nThis action CANNOT be undone!")
    print("\nResources that will be deleted:")
    print("  - Network Interfaces (ENIs)")
    print("  - Elastic IPs (EIPs)")
    print("  - Security Groups")
    print("\n" + "=" * 70)
    
    response = input("\nType 'DELETE' (in capital letters) to confirm: ").strip()
    return response == "DELETE"


def get_resources_by_tag(session: boto3.Session, tag_value: str) -> Dict[str, List]:
    """Get all resources with the specified CreatedBy tag"""
    ec2_client = session.client('ec2')
    
    resources = {
        'enis': [],
        'eips': [],
        'security_groups': []
    }
    
    print(f"\n🔍 Searching for resources with tag: CreatedBy={tag_value}")
    print("-" * 70)
    
    # Find ENIs
    try:
        eni_response = ec2_client.describe_network_interfaces(
            Filters=[
                {'Name': 'tag:CreatedBy', 'Values': [tag_value]}
            ]
        )
        resources['enis'] = eni_response.get('NetworkInterfaces', [])
        print(f"✅ Found {len(resources['enis'])} Network Interface(s)")
    except Exception as e:
        print(f"⚠️  Error finding ENIs: {e}")
    
    # Find EIPs
    try:
        eip_response = ec2_client.describe_addresses(
            Filters=[
                {'Name': 'tag:CreatedBy', 'Values': [tag_value]}
            ]
        )
        resources['eips'] = eip_response.get('Addresses', [])
        print(f"✅ Found {len(resources['eips'])} Elastic IP(s)")
    except Exception as e:
        print(f"⚠️  Error finding EIPs: {e}")
    
    # Find Security Groups
    try:
        sg_response = ec2_client.describe_security_groups(
            Filters=[
                {'Name': 'tag:CreatedBy', 'Values': [tag_value]}
            ]
        )
        resources['security_groups'] = sg_response.get('SecurityGroups', [])
        print(f"✅ Found {len(resources['security_groups'])} Security Group(s)")
    except Exception as e:
        print(f"⚠️  Error finding Security Groups: {e}")
    
    return resources


def display_resources(resources: Dict[str, List]) -> None:
    """Display detailed information about resources to be deleted"""
    print("\n📋 Resource Details:")
    print("=" * 70)
    
    # Display ENIs
    if resources['enis']:
        print("\n🔌 Network Interfaces (ENIs):")
        print("-" * 70)
        for eni in resources['enis']:
            eni_id = eni['NetworkInterfaceId']
            description = eni.get('Description', 'N/A')
            private_ip = eni.get('PrivateIpAddress', 'N/A')
            status = eni.get('Status', 'N/A')
            attachment = eni.get('Attachment', {})
            attached_to = attachment.get('InstanceId', 'Not attached')
            
            print(f"  • {eni_id}")
            print(f"    Description: {description}")
            print(f"    Private IP: {private_ip}")
            print(f"    Status: {status}")
            print(f"    Attached to: {attached_to}")
            
            # Check for associated EIP
            if eni.get('Association'):
                public_ip = eni['Association'].get('PublicIp', 'N/A')
                print(f"    Public IP: {public_ip}")
            print()
    
    # Display EIPs
    if resources['eips']:
        print("\n🌐 Elastic IPs (EIPs):")
        print("-" * 70)
        for eip in resources['eips']:
            allocation_id = eip.get('AllocationId', 'N/A')
            public_ip = eip.get('PublicIp', 'N/A')
            association_id = eip.get('AssociationId', 'Not associated')
            eni_id = eip.get('NetworkInterfaceId', 'N/A')
            
            print(f"  • {allocation_id}")
            print(f"    Public IP: {public_ip}")
            print(f"    Associated with: {eni_id}")
            print(f"    Association ID: {association_id}")
            print()
    
    # Display Security Groups
    if resources['security_groups']:
        print("\n🔒 Security Groups:")
        print("-" * 70)
        for sg in resources['security_groups']:
            sg_id = sg['GroupId']
            sg_name = sg.get('GroupName', 'N/A')
            description = sg.get('Description', 'N/A')
            vpc_id = sg.get('VpcId', 'N/A')
            
            print(f"  • {sg_id}")
            print(f"    Name: {sg_name}")
            print(f"    Description: {description}")
            print(f"    VPC: {vpc_id}")
            print()


def disassociate_and_release_eips(ec2_client, eips: List[Dict]) -> Tuple[int, int]:
    """Disassociate and release Elastic IPs"""
    success_count = 0
    error_count = 0
    
    if not eips:
        return success_count, error_count
    
    print("\n🌐 Disassociating and Releasing Elastic IPs...")
    print("-" * 70)
    
    for eip in eips:
        allocation_id = eip.get('AllocationId')
        public_ip = eip.get('PublicIp', 'N/A')
        association_id = eip.get('AssociationId')
        
        try:
            # Disassociate if associated
            if association_id:
                print(f"  Disassociating EIP {public_ip} ({allocation_id})...")
                ec2_client.disassociate_address(AssociationId=association_id)
                print(f"  ✅ Disassociated")
                time.sleep(1)  # Wait a bit before releasing
            
            # Release the EIP
            print(f"  Releasing EIP {public_ip} ({allocation_id})...")
            ec2_client.release_address(AllocationId=allocation_id)
            print(f"  ✅ Released EIP: {allocation_id}")
            success_count += 1
            
        except Exception as e:
            print(f"  ❌ Error with EIP {allocation_id}: {e}")
            error_count += 1
    
    return success_count, error_count


def delete_enis(ec2_client, enis: List[Dict]) -> Tuple[int, int]:
    """Delete Network Interfaces"""
    success_count = 0
    error_count = 0
    
    if not enis:
        return success_count, error_count
    
    print("\n🔌 Deleting Network Interfaces...")
    print("-" * 70)
    
    for eni in enis:
        eni_id = eni['NetworkInterfaceId']
        description = eni.get('Description', 'N/A')
        attachment = eni.get('Attachment', {})
        
        try:
            # Detach if attached to an instance
            if attachment and attachment.get('AttachmentId'):
                attachment_id = attachment['AttachmentId']
                instance_id = attachment.get('InstanceId', 'N/A')
                print(f"  Detaching ENI {eni_id} from instance {instance_id}...")
                
                try:
                    ec2_client.detach_network_interface(
                        AttachmentId=attachment_id,
                        Force=True
                    )
                    print(f"  ✅ Detached")
                    
                    # Wait for detachment to complete
                    print(f"  ⏳ Waiting for detachment to complete...")
                    waiter = ec2_client.get_waiter('network_interface_available')
                    waiter.wait(
                        NetworkInterfaceIds=[eni_id],
                        WaiterConfig={'Delay': 5, 'MaxAttempts': 20}
                    )
                except Exception as detach_error:
                    print(f"  ⚠️  Detachment warning: {detach_error}")
                    time.sleep(10)  # Wait a bit longer
            
            # Delete the ENI
            print(f"  Deleting ENI {eni_id} ({description})...")
            ec2_client.delete_network_interface(NetworkInterfaceId=eni_id)
            print(f"  ✅ Deleted ENI: {eni_id}")
            success_count += 1
            
        except Exception as e:
            print(f"  ❌ Error deleting ENI {eni_id}: {e}")
            error_count += 1
    
    return success_count, error_count


def delete_security_groups(ec2_client, security_groups: List[Dict]) -> Tuple[int, int]:
    """Delete Security Groups"""
    success_count = 0
    error_count = 0
    
    if not security_groups:
        return success_count, error_count
    
    print("\n🔒 Deleting Security Groups...")
    print("-" * 70)
    
    # Try multiple times as security groups may have dependencies
    max_attempts = 3
    remaining_sgs = security_groups.copy()
    
    for attempt in range(max_attempts):
        if not remaining_sgs:
            break
        
        if attempt > 0:
            print(f"\n  Retry attempt {attempt + 1}/{max_attempts}...")
            time.sleep(5)  # Wait before retry
        
        still_remaining = []
        
        for sg in remaining_sgs:
            sg_id = sg['GroupId']
            sg_name = sg.get('GroupName', 'N/A')
            
            try:
                print(f"  Deleting Security Group {sg_id} ({sg_name})...")
                ec2_client.delete_security_group(GroupId=sg_id)
                print(f"  ✅ Deleted Security Group: {sg_id}")
                success_count += 1
                
            except ec2_client.exceptions.ClientError as e:
                error_code = e.response['Error']['Code']
                
                if error_code == 'DependencyViolation':
                    print(f"  ⚠️  Security Group {sg_id} has dependencies, will retry...")
                    still_remaining.append(sg)
                else:
                    print(f"  ❌ Error deleting Security Group {sg_id}: {e}")
                    error_count += 1
            except Exception as e:
                print(f"  ❌ Error deleting Security Group {sg_id}: {e}")
                error_count += 1
        
        remaining_sgs = still_remaining
    
    # Report any remaining security groups
    if remaining_sgs:
        print(f"\n  ⚠️  {len(remaining_sgs)} Security Group(s) could not be deleted due to dependencies:")
        for sg in remaining_sgs:
            print(f"    • {sg['GroupId']} ({sg.get('GroupName', 'N/A')})")
        error_count += len(remaining_sgs)
    
    return success_count, error_count


def main():
    """Main execution function"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description='Delete all resources created by create-enis.py using CreatedBy tag',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Delete resources with specific tag
  python3 delete-enis.py --profile renaws --region us-east-1 --tag "deployment-001"
  
  # Dry run (list resources without deleting)
  python3 delete-enis.py --profile renaws --region us-east-1 --tag "deployment-001" --dry-run
  
  # Force deletion without confirmation
  python3 delete-enis.py --profile renaws --region us-east-1 --tag "deployment-001" --force
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
        '--tag',
        type=str,
        required=True,
        help='CreatedBy tag value to identify resources to delete (required)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='List resources without deleting them'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='Skip confirmation prompt (dangerous!)'
    )
    
    args = parser.parse_args()
    
    print("🗑️  FortiGate HA Deployment - Resource Cleanup")
    print("=" * 70)
    print(f"Region: {args.region}")
    if args.profile:
        print(f"Profile: {args.profile}")
    print(f"Tag: CreatedBy={args.tag}")
    if args.dry_run:
        print("Mode: DRY RUN (no resources will be deleted)")
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
        
        # Verify credentials
        sts_client = session.client('sts')
        identity = sts_client.get_caller_identity()
        print(f"✅ Authenticated as: {identity['Arn']}")
        print(f"✅ Account ID: {identity['Account']}")
        print()
        
    except Exception as e:
        print(f"❌ Error authenticating with AWS: {e}")
        print("\nTroubleshooting:")
        print("  1. Check your AWS credentials are configured")
        print("  2. If using --profile, ensure the profile exists")
        print("  3. Verify your credentials have EC2 permissions")
        return 1
    
    # Get resources by tag
    resources = get_resources_by_tag(session, args.tag)
    
    # Calculate total resources
    total_resources = (
        len(resources['enis']) +
        len(resources['eips']) +
        len(resources['security_groups'])
    )
    
    if total_resources == 0:
        print("\n✅ No resources found with the specified tag.")
        print(f"   Tag: CreatedBy={args.tag}")
        print("\nPossible reasons:")
        print("  1. Resources were already deleted")
        print("  2. Wrong tag value specified")
        print("  3. Resources are in a different region")
        print("  4. Resources don't have the CreatedBy tag")
        return 0
    
    # Display resources
    display_resources(resources)
    
    print(f"\n📊 Summary: {total_resources} resource(s) found")
    print(f"  • {len(resources['enis'])} Network Interface(s)")
    print(f"  • {len(resources['eips'])} Elastic IP(s)")
    print(f"  • {len(resources['security_groups'])} Security Group(s)")
    
    # Dry run mode - just list resources
    if args.dry_run:
        print("\n✅ DRY RUN completed - no resources were deleted")
        return 0
    
    # Confirm deletion
    if not args.force:
        if not confirm_deletion(total_resources, args.tag):
            print("\n❌ Deletion cancelled by user")
            return 0
    else:
        print("\n⚠️  FORCE mode enabled - skipping confirmation")
    
    # Perform deletion
    print("\n🗑️  Starting deletion process...")
    print("=" * 70)
    
    total_success = 0
    total_errors = 0
    
    # Step 1: Disassociate and release EIPs
    if resources['eips']:
        success, errors = disassociate_and_release_eips(ec2_client, resources['eips'])
        total_success += success
        total_errors += errors
    
    # Step 2: Delete ENIs
    if resources['enis']:
        success, errors = delete_enis(ec2_client, resources['enis'])
        total_success += success
        total_errors += errors
    
    # Step 3: Delete Security Groups
    if resources['security_groups']:
        success, errors = delete_security_groups(ec2_client, resources['security_groups'])
        total_success += success
        total_errors += errors
    
    # Final summary
    print("\n" + "=" * 70)
    print("🏁 Deletion Summary")
    print("=" * 70)
    print(f"✅ Successfully deleted: {total_success} resource(s)")
    if total_errors > 0:
        print(f"❌ Failed to delete: {total_errors} resource(s)")
        print("\nNote: Some resources may have dependencies or be in use.")
        print("      Wait a few minutes and try again, or delete manually.")
        return 1
    else:
        print("✅ All resources deleted successfully!")
        return 0


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⚠️  Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
