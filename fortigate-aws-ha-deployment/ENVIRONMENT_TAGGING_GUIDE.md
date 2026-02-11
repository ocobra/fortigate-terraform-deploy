# Environment Tagging Guide

## What is the "Environment" Field?

The **environment** field is a label used to tag and organize your AWS resources. It helps you identify which deployment stage or purpose a resource belongs to.

## Common Environment Values

### Standard Environments

- **`prod`** or **`production`** - Production environment (live, customer-facing)
- **`staging`** - Staging/pre-production environment (final testing before production)
- **`dev`** or **`development`** - Development environment (active development and testing)
- **`test`** or **`qa`** - Testing/QA environment (quality assurance testing)
- **`demo`** - Demo environment (for demonstrations and sales)
- **`sandbox`** - Sandbox environment (experimentation and learning)

### When the Script Prompts

```bash
Environment [prod]: 
```

You can enter any value that makes sense for your organization. Examples:
- `prod` - For production deployment
- `dev` - For development/testing
- `staging` - For pre-production staging
- `customer-demo` - For customer demonstrations
- `poc` - For proof-of-concept

## How Environment Tags Are Used

### 1. AWS Resource Tagging

All AWS resources created by the deployment will be tagged with your environment value:

```hcl
tags = {
  Project     = "FortiGate-HA-Deployment"
  Environment = "prod"              # Your environment value
  Owner       = "NetworkTeam"
  ManagedBy   = "Terraform"
}
```

This applies to:
- EC2 instances (FortiGate VMs)
- Network interfaces (ENIs)
- Security groups
- Transit Gateway attachments
- CloudWatch log groups
- VPC Flow Logs
- S3 buckets (for state management)
- DynamoDB tables (for state locking)

### 2. Resource Identification

Tags help you identify resources in the AWS Console:

**EC2 Console:**
```
Name: fortigate-primary
Environment: prod
Project: FortiGate-HA-Deployment
```

**Cost Explorer:**
- Filter costs by environment tag
- See how much each environment costs
- Track spending per deployment stage

### 3. IAM Policies and Access Control

You can create IAM policies that restrict access based on environment:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "ec2:*",
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "ec2:ResourceTag/Environment": "dev"
        }
      }
    }
  ]
}
```

This policy only allows actions on resources tagged with `Environment: dev`.

### 4. Cost Allocation

AWS Cost Allocation Tags allow you to:
- Track costs per environment
- Generate cost reports by environment
- Set budgets per environment
- Identify cost optimization opportunities

**Example Cost Breakdown:**
```
Environment: prod      - $2,500/month
Environment: staging   - $800/month
Environment: dev       - $400/month
```

### 5. Automation and Scripting

Scripts can filter resources by environment:

```bash
# List all prod FortiGate instances
aws ec2 describe-instances \
  --filters "Name=tag:Environment,Values=prod" \
            "Name=tag:Project,Values=FortiGate-HA-Deployment"

# Stop all dev environment instances (cost savings)
aws ec2 stop-instances \
  --instance-ids $(aws ec2 describe-instances \
    --filters "Name=tag:Environment,Values=dev" \
    --query 'Reservations[].Instances[].InstanceId' \
    --output text)
```

### 6. Multi-Environment Deployments

You can deploy multiple environments with different configurations:

**Production:**
```yaml
environment: prod
instance_type: c5.2xlarge  # Larger instances
enable_detailed_monitoring: true
log_retention_days: 90
```

**Development:**
```yaml
environment: dev
instance_type: c5.large    # Smaller instances
enable_detailed_monitoring: false
log_retention_days: 7
```

### 7. Terraform State Separation

Different environments can use separate state files:

```bash
# Production state
terraform init \
  -backend-config="key=fortigate-ha/prod/terraform.tfstate"

# Development state
terraform init \
  -backend-config="key=fortigate-ha/dev/terraform.tfstate"
```

This prevents accidental changes to production when working on development.

## Best Practices

### 1. Use Consistent Naming

Choose a naming convention and stick to it across your organization:

**Good:**
- `prod`, `staging`, `dev` (consistent, lowercase)
- `production`, `staging`, `development` (consistent, full names)

**Avoid:**
- Mixing styles: `prod`, `Staging`, `DEV`
- Inconsistent names: `production`, `stage`, `develop`

### 2. Document Your Environments

Create a document that defines what each environment is for:

```
prod       - Production environment, customer-facing
staging    - Pre-production testing, mirrors prod
dev        - Development and integration testing
sandbox    - Experimentation, no production data
```

### 3. Separate AWS Accounts (Advanced)

For large organizations, consider separate AWS accounts per environment:

```
AWS Organization
├── Production Account (111111111111)
│   └── Environment: prod
├── Staging Account (222222222222)
│   └── Environment: staging
└── Development Account (333333333333)
    └── Environment: dev
```

### 4. Use Environment-Specific Configurations

Create separate configuration files:

```
configs/
├── prod.yaml       # Production configuration
├── staging.yaml    # Staging configuration
└── dev.yaml        # Development configuration
```

Deploy with:
```bash
python deploy.py --config configs/prod.yaml
python deploy.py --config configs/dev.yaml
```

### 5. Implement Environment-Based Access Control

Restrict who can deploy to each environment:

- **Production**: Senior engineers only, requires approval
- **Staging**: All engineers, requires peer review
- **Development**: All engineers, self-service

### 6. Tag Everything

Ensure all resources are tagged:

```hcl
# Default tags applied to all resources
default_tags = {
  Project     = "FortiGate-HA-Deployment"
  Environment = var.environment
  Owner       = var.owner_tag
  ManagedBy   = "Terraform"
  CostCenter  = "Network-Security"
}
```

### 7. Monitor by Environment

Set up separate monitoring dashboards per environment:

- **Production Dashboard**: Real-time alerts, 24/7 monitoring
- **Staging Dashboard**: Daily checks, less critical alerts
- **Development Dashboard**: Basic monitoring, no alerts

## Example Deployment Scenarios

### Scenario 1: Production Deployment

```bash
python deploy.py

# When prompted:
Environment [prod]: prod
Owner tag [NetworkTeam]: NetworkOps
```

**Result:** All resources tagged with `Environment: prod`

### Scenario 2: Development Environment

```bash
python deploy.py --config dev-config.yaml

# dev-config.yaml contains:
# environment: dev
# instance_type: c5.large  # Smaller for cost savings
```

**Result:** All resources tagged with `Environment: dev`

### Scenario 3: Customer Demo

```bash
python deploy.py

# When prompted:
Environment [prod]: customer-demo
Owner tag [NetworkTeam]: SalesEngineering
```

**Result:** All resources tagged with `Environment: customer-demo`

## Viewing Environment Tags

### AWS Console

1. **EC2 Dashboard:**
   - Select an instance
   - Click **Tags** tab
   - See `Environment: prod`

2. **Resource Groups:**
   - Create a resource group filtered by `Environment: prod`
   - View all resources in that environment

3. **Cost Explorer:**
   - Group costs by tag: `Environment`
   - See cost breakdown per environment

### AWS CLI

```bash
# List all resources with environment tag
aws resourcegroupstaggingapi get-resources \
  --tag-filters Key=Environment,Values=prod

# Get specific resource tags
aws ec2 describe-instances \
  --instance-ids i-1234567890abcdef0 \
  --query 'Reservations[0].Instances[0].Tags'
```

### Terraform

```bash
# View outputs including environment
terraform output

# Output includes:
# environment = "prod"
```

## Changing Environment Tags

### Before Deployment

Simply change the value when prompted or in your configuration file.

### After Deployment

To change tags on existing resources:

```bash
# Update tags on EC2 instances
aws ec2 create-tags \
  --resources i-1234567890abcdef0 \
  --tags Key=Environment,Value=staging

# Or use Terraform
# Update terraform.tfvars:
# environment = "staging"
# Then run:
terraform apply
```

## Environment-Specific Considerations

### Production Environment

- **High Availability**: Use larger instance types
- **Monitoring**: Enable detailed monitoring and alerting
- **Logging**: Longer retention periods (90+ days)
- **Backups**: Automated daily backups
- **Change Control**: Require approval for changes
- **Cost**: Higher costs for reliability

### Staging Environment

- **Mirror Production**: Similar configuration to prod
- **Testing**: Used for final testing before prod deployment
- **Monitoring**: Standard monitoring
- **Logging**: Medium retention (30 days)
- **Cost**: Moderate costs

### Development Environment

- **Cost Optimization**: Smaller instance types
- **Flexibility**: Easier to make changes
- **Monitoring**: Basic monitoring
- **Logging**: Short retention (7 days)
- **Automation**: Auto-shutdown during off-hours
- **Cost**: Lower costs

## Troubleshooting

### Issue: Wrong Environment Tag Applied

**Problem:** Deployed with wrong environment tag (e.g., `dev` instead of `prod`)

**Solution:**

1. **Update tags on existing resources:**
   ```bash
   # Get all resource IDs
   aws resourcegroupstaggingapi get-resources \
     --tag-filters Key=Environment,Values=dev \
     --query 'ResourceTagMappingList[].ResourceARN'
   
   # Update tags (example for EC2)
   aws ec2 create-tags \
     --resources i-xxx i-yyy \
     --tags Key=Environment,Value=prod
   ```

2. **Or redeploy with correct environment:**
   ```bash
   # Update configuration
   # environment = "prod"
   
   # Redeploy
   terraform apply
   ```

### Issue: Can't Find Resources by Environment

**Problem:** Resources not showing up when filtering by environment tag

**Solution:**

1. **Verify tags were applied:**
   ```bash
   aws ec2 describe-instances \
     --instance-ids i-1234567890abcdef0 \
     --query 'Reservations[0].Instances[0].Tags'
   ```

2. **Check for typos in tag values:**
   - `prod` vs `Prod` vs `production`

3. **Ensure tags were propagated:**
   - Some resources take time to show tags
   - Refresh the console or wait a few minutes

## Summary

The **environment** field is a simple but powerful organizational tool that:

- ✅ Tags all AWS resources for easy identification
- ✅ Enables cost tracking and allocation
- ✅ Supports access control and security policies
- ✅ Facilitates automation and scripting
- ✅ Helps manage multiple deployment stages
- ✅ Improves resource organization and governance

**Quick Answer:** When the script asks for "Environment", enter a label that describes the purpose of this deployment (e.g., `prod`, `dev`, `staging`). This label will be applied as a tag to all AWS resources created by the deployment.

## Additional Resources

- [AWS Tagging Best Practices](https://docs.aws.amazon.com/general/latest/gr/aws_tagging.html)
- [AWS Cost Allocation Tags](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/cost-alloc-tags.html)
- [Terraform Resource Tagging](https://www.terraform.io/docs/language/meta-arguments/tags.html)
- [Main README](README.md)
- [Usage Guide](USAGE.md)
