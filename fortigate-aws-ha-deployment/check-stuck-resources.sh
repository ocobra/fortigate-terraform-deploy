#!/bin/bash
# Quick diagnostic script to check stuck resources

# Parse command line arguments
PROFILE=""
REGION="us-east-1"

usage() {
  echo "Usage: $0 --profile <aws-profile> [--region <region>]"
  echo ""
  echo "Options:"
  echo "  --profile    AWS CLI profile name (required)"
  echo "  --region     AWS region (default: us-east-1)"
  echo ""
  echo "Example:"
  echo "  $0 --profile renaws --region us-east-1"
  exit 1
}

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --profile)
      PROFILE="$2"
      shift 2
      ;;
    --region)
      REGION="$2"
      shift 2
      ;;
    -h|--help)
      usage
      ;;
    *)
      echo "Unknown option: $1"
      usage
      ;;
  esac
done

# Validate required parameters
if [ -z "$PROFILE" ]; then
  echo "❌ Error: --profile is required"
  echo ""
  usage
fi

echo "🔍 Checking FortiGate HA Deployment Resources"
echo "=============================================="
echo ""

# Check EC2 Instances
echo "1️⃣  EC2 Instances:"
echo "-------------------"
aws ec2 describe-instances \
  --filters "Name=tag:Project,Values=FortiGate-HA-Deployment" \
  --profile "$PROFILE" \
  --region "$REGION" \
  --query 'Reservations[*].Instances[*].[InstanceId,State.Name,InstanceType,LaunchTime]' \
  --output table

echo ""

# Check stuck ENIs
echo "2️⃣  Stuck ENI Status:"
echo "-------------------"
STUCK_ENIS=(
  "eni-0da299fdba89d33e2"
  "eni-064c240470d3aefe7"
  "eni-0fbad7c4b511cb7de"
  "eni-04a1e3207a4b64483"
  "eni-015c428cd8c554b24"
  "eni-096b6da8014d797bd"
)

for eni in "${STUCK_ENIS[@]}"; do
  echo ""
  echo "ENI: $eni"
  aws ec2 describe-network-interfaces \
    --network-interface-ids "$eni" \
    --profile "$PROFILE" \
    --region "$REGION" \
    --query 'NetworkInterfaces[0].[Status,Attachment.InstanceId,Attachment.Status,Attachment.DeleteOnTermination]' \
    --output table 2>/dev/null || echo "  ❌ ENI not found or error"
done

echo ""
echo ""

# Check all ENIs with the project tag
echo "3️⃣  All Project ENIs:"
echo "-------------------"
aws ec2 describe-network-interfaces \
  --filters "Name=tag:Project,Values=FortiGate-HA-Deployment" \
  --profile "$PROFILE" \
  --region "$REGION" \
  --query 'NetworkInterfaces[*].[NetworkInterfaceId,Status,Attachment.InstanceId,Attachment.Status]' \
  --output table

echo ""
echo "=============================================="
echo "✅ Diagnostic complete"
