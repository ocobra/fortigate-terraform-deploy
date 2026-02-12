#!/bin/bash
# Cleanup orphaned CloudWatch Log Groups and VPC Flow Logs
# This script removes CloudWatch resources that may not be tracked by Terraform

set -e

# Parse command line arguments
PROFILE=""
REGION="us-east-1"
DRY_RUN=false

usage() {
  echo "Usage: $0 --profile <aws-profile> [--region <region>] [--dry-run]"
  echo ""
  echo "Options:"
  echo "  --profile    AWS CLI profile name (required)"
  echo "  --region     AWS region (default: us-east-1)"
  echo "  --dry-run    List resources without deleting them"
  echo ""
  echo "Example:"
  echo "  $0 --profile renaws --region us-east-1"
  echo "  $0 --profile renaws --region us-east-1 --dry-run"
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
    --dry-run)
      DRY_RUN=true
      shift
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

echo "🧹 CloudWatch Logs Cleanup for FortiGate HA Deployment"
echo "=========================================="
echo "AWS Profile: $PROFILE"
echo "AWS Region:  $REGION"
if [ "$DRY_RUN" = true ]; then
  echo "Mode:        DRY RUN (no resources will be deleted)"
fi
echo ""

# Get VPC ID from terraform.tfvars
VPC_ID=$(grep "^vpc_id" "$(dirname "$0")/terraform/terraform.tfvars" 2>/dev/null | cut -d'"' -f2 || echo "")

if [ -z "$VPC_ID" ]; then
  echo "⚠️  Warning: Could not determine VPC ID from terraform.tfvars"
  echo "   Will search for all FortiGate-related log groups"
  echo ""
fi

# Step 1: Find and delete VPC Flow Logs
echo "Step 1: Checking VPC Flow Logs..."
echo "-----------------------------------"

if [ -n "$VPC_ID" ]; then
  FLOW_LOGS=$(aws ec2 describe-flow-logs \
    --profile "$PROFILE" \
    --region "$REGION" \
    --filter "Name=resource-id,Values=$VPC_ID" \
    --query 'FlowLogs[*].FlowLogId' \
    --output text)
  
  if [ -n "$FLOW_LOGS" ]; then
    echo "Found VPC Flow Logs: $FLOW_LOGS"
    
    if [ "$DRY_RUN" = false ]; then
      for flow_log in $FLOW_LOGS; do
        echo "  Deleting VPC Flow Log: $flow_log"
        aws ec2 delete-flow-logs \
          --flow-log-ids "$flow_log" \
          --profile "$PROFILE" \
          --region "$REGION"
        echo "  ✅ Deleted"
      done
    else
      echo "  [DRY RUN] Would delete: $FLOW_LOGS"
    fi
  else
    echo "✅ No VPC Flow Logs found"
  fi
else
  echo "⚠️  Skipping VPC Flow Logs (VPC ID not found)"
fi

echo ""

# Step 2: Find and delete CloudWatch Log Groups
echo "Step 2: Checking CloudWatch Log Groups..."
echo "-----------------------------------"

# Search for log groups related to FortiGate or the VPC
LOG_GROUPS=$(aws logs describe-log-groups \
  --profile "$PROFILE" \
  --region "$REGION" \
  --query 'logGroups[?contains(logGroupName, `fortigate`) || contains(logGroupName, `flowlogs`)].logGroupName' \
  --output text)

if [ -n "$LOG_GROUPS" ]; then
  echo "Found CloudWatch Log Groups:"
  for log_group in $LOG_GROUPS; do
    echo "  • $log_group"
    
    # Get log group details
    RETENTION=$(aws logs describe-log-groups \
      --log-group-name-prefix "$log_group" \
      --profile "$PROFILE" \
      --region "$REGION" \
      --query 'logGroups[0].retentionInDays' \
      --output text)
    
    # Get tags
    TAGS=$(aws logs list-tags-log-group \
      --log-group-name "$log_group" \
      --profile "$PROFILE" \
      --region "$REGION" \
      --query 'tags' \
      --output json 2>/dev/null || echo "{}")
    
    echo "    Retention: ${RETENTION:-None}"
    echo "    Tags: $TAGS"
    
    if [ "$DRY_RUN" = false ]; then
      echo "    Deleting..."
      aws logs delete-log-group \
        --log-group-name "$log_group" \
        --profile "$PROFILE" \
        --region "$REGION"
      echo "    ✅ Deleted"
    else
      echo "    [DRY RUN] Would delete this log group"
    fi
    echo ""
  done
else
  echo "✅ No CloudWatch Log Groups found"
fi

echo ""

# Step 3: Find and delete CloudWatch Alarms
echo "Step 3: Checking CloudWatch Alarms..."
echo "-----------------------------------"

ALARMS=$(aws cloudwatch describe-alarms \
  --profile "$PROFILE" \
  --region "$REGION" \
  --query 'MetricAlarms[?contains(AlarmName, `fortigate`)].AlarmName' \
  --output text)

if [ -n "$ALARMS" ]; then
  echo "Found CloudWatch Alarms:"
  for alarm in $ALARMS; do
    echo "  • $alarm"
  done
  
  if [ "$DRY_RUN" = false ]; then
    echo "  Deleting alarms..."
    aws cloudwatch delete-alarms \
      --alarm-names $ALARMS \
      --profile "$PROFILE" \
      --region "$REGION"
    echo "  ✅ Deleted all alarms"
  else
    echo "  [DRY RUN] Would delete these alarms"
  fi
else
  echo "✅ No CloudWatch Alarms found"
fi

echo ""

# Step 4: Find and delete IAM Roles for Flow Logs
echo "Step 4: Checking IAM Roles for Flow Logs..."
echo "-----------------------------------"

FLOW_LOG_ROLES=$(aws iam list-roles \
  --profile "$PROFILE" \
  --query 'Roles[?contains(RoleName, `fortigate-flow-logs`)].RoleName' \
  --output text)

if [ -n "$FLOW_LOG_ROLES" ]; then
  echo "Found IAM Roles:"
  for role in $FLOW_LOG_ROLES; do
    echo "  • $role"
    
    if [ "$DRY_RUN" = false ]; then
      # Delete inline policies first
      POLICIES=$(aws iam list-role-policies \
        --role-name "$role" \
        --profile "$PROFILE" \
        --query 'PolicyNames' \
        --output text)
      
      if [ -n "$POLICIES" ]; then
        for policy in $POLICIES; do
          echo "    Deleting inline policy: $policy"
          aws iam delete-role-policy \
            --role-name "$role" \
            --policy-name "$policy" \
            --profile "$PROFILE"
        done
      fi
      
      # Delete the role
      echo "    Deleting role..."
      aws iam delete-role \
        --role-name "$role" \
        --profile "$PROFILE"
      echo "    ✅ Deleted"
    else
      echo "    [DRY RUN] Would delete this role"
    fi
  done
else
  echo "✅ No IAM Roles found"
fi

echo ""
echo "=========================================="
if [ "$DRY_RUN" = true ]; then
  echo "✅ DRY RUN completed - no resources were deleted"
  echo ""
  echo "To actually delete these resources, run without --dry-run:"
  echo "  $0 --profile $PROFILE --region $REGION"
else
  echo "✅ Cleanup complete!"
  echo ""
  echo "📋 Next steps:"
  echo "  1. Verify all resources are deleted in AWS Console"
  echo "  2. Check CloudWatch Logs console"
  echo "  3. Check VPC Flow Logs in VPC console"
fi
echo ""

