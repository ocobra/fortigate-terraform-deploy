#!/bin/bash
# Force cleanup script for stuck Terraform destroy
# This script handles ENIs that won't detach and instances that won't terminate

set -e

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

echo "🚨 FortiGate HA Deployment - Force Cleanup"
echo "=========================================="
echo "AWS Profile: $PROFILE"
echo "AWS Region:  $REGION"
echo ""

# Step 1: Check and terminate EC2 instances
echo "Step 1: Checking EC2 instances..."
INSTANCES=$(aws ec2 describe-instances \
  --filters "Name=tag:Project,Values=FortiGate-HA-Deployment" "Name=instance-state-name,Values=running,stopped,stopping" \
  --profile "$PROFILE" \
  --region "$REGION" \
  --query 'Reservations[*].Instances[*].InstanceId' \
  --output text)

if [ -n "$INSTANCES" ]; then
  echo "Found instances: $INSTANCES"
  echo "Terminating instances..."
  aws ec2 terminate-instances \
    --instance-ids $INSTANCES \
    --profile "$PROFILE" \
    --region "$REGION"
  
  echo "Waiting for instances to terminate (this may take 2-3 minutes)..."
  aws ec2 wait instance-terminated \
    --instance-ids $INSTANCES \
    --profile "$PROFILE" \
    --region "$REGION" || echo "⚠️  Wait timed out, continuing anyway..."
  
  echo "✅ Instances terminated"
else
  echo "✅ No running instances found"
fi

echo ""

# Step 2: Force detach stuck ENIs
echo "Step 2: Force detaching stuck ENIs..."
STUCK_ENIS=(
  "eni-0da299fdba89d33e2"
  "eni-064c240470d3aefe7"
  "eni-0fbad7c4b511cb7de"
  "eni-04a1e3207a4b64483"
  "eni-015c428cd8c554b24"
  "eni-096b6da8014d797bd"
)

for eni in "${STUCK_ENIS[@]}"; do
  echo "Processing $eni..."
  
  # Check if ENI exists and get attachment info
  ATTACH_INFO=$(aws ec2 describe-network-interfaces \
    --network-interface-ids "$eni" \
    --profile "$PROFILE" \
    --region "$REGION" \
    --query 'NetworkInterfaces[0].Attachment' \
    --output json 2>/dev/null || echo "null")
  
  if [ "$ATTACH_INFO" != "null" ] && [ "$ATTACH_INFO" != "" ]; then
    ATTACH_ID=$(echo "$ATTACH_INFO" | jq -r '.AttachmentId // empty')
    ATTACH_STATUS=$(echo "$ATTACH_INFO" | jq -r '.Status // empty')
    
    if [ -n "$ATTACH_ID" ] && [ "$ATTACH_STATUS" != "detached" ]; then
      echo "  Forcing detachment of $eni (attachment: $ATTACH_ID)..."
      aws ec2 detach-network-interface \
        --attachment-id "$ATTACH_ID" \
        --force \
        --profile "$PROFILE" \
        --region "$REGION" 2>/dev/null || echo "  ⚠️  Detach failed or already detached"
      
      sleep 2
    else
      echo "  ✅ Already detached or no attachment found"
    fi
  else
    echo "  ℹ️  ENI not found (may already be deleted)"
  fi
done

echo ""
echo "⏳ Waiting 30 seconds for detachments to complete..."
sleep 30

echo ""

# Step 3: Retry Terraform destroy
echo "Step 3: Retrying Terraform destroy..."
cd "$(dirname "$0")/terraform"

echo "Setting AWS credentials..."
export AWS_PROFILE="$PROFILE"
export AWS_REGION="$REGION"

echo "Running: terraform destroy -var='aws_profile=$PROFILE' -auto-approve"
terraform destroy -var="aws_profile=$PROFILE" -auto-approve

echo ""
echo "✅ Cleanup complete!"
echo ""
echo "📋 Next steps:"
echo "  1. Verify all resources are deleted in AWS Console"
echo "  2. If ENIs still exist, they can be manually deleted"
echo "  3. Run terraform state list to check for remaining state"
