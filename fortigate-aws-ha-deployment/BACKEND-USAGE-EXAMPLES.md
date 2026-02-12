# Backend Configuration Usage Examples

## Quick Start Examples

### 1. Check Bootstrap Information

Before using S3 backend, check the bootstrap setup instructions:

```bash
python3 deploy.py --bootstrap-info
```

### 2. Deploy with Local Backend (Development/Testing)

**Default behavior** - no additional options needed:

```bash
python3 deploy.py
```

Or explicitly specify local backend:

```bash
python3 deploy.py --backend=local
```

### 3. Deploy with S3 Backend (Production)

**Prerequisites**: Run bootstrap first (see bootstrap-info output)

```bash
python3 deploy.py \
  --backend=s3 \
  --s3-bucket=my-company-fortigate-terraform-state \
  --s3-region=us-east-1 \
  --dynamodb-table=fortigate-terraform-locks
```

### 4. Deploy with Custom S3 Key (Multi-Environment)

Separate state files by environment:

**Production:**
```bash
python3 deploy.py \
  --backend=s3 \
  --s3-bucket=my-company-fortigate-terraform-state \
  --s3-key=fortigate-ha/prod/terraform.tfstate \
  --s3-region=us-east-1 \
  --dynamodb-table=fortigate-terraform-locks
```

**Staging:**
```bash
python3 deploy.py \
  --backend=s3 \
  --s3-bucket=my-company-fortigate-terraform-state \
  --s3-key=fortigate-ha/staging/terraform.tfstate \
  --s3-region=us-east-1 \
  --dynamodb-table=fortigate-terraform-locks
```

**Development:**
```bash
python3 deploy.py \
  --backend=s3 \
  --s3-bucket=my-company-fortigate-terraform-state \
  --s3-key=fortigate-ha/dev/terraform.tfstate \
  --s3-region=us-east-1 \
  --dynamodb-table=fortigate-terraform-locks
```

## Complete Workflow Examples

### Example 1: First-Time Production Deployment with S3 Backend

**Step 1: Run Bootstrap**

```bash
cd terraform/bootstrap

# Configure variables
cp terraform.tfvars.example terraform.tfvars
nano terraform.tfvars  # Edit with your values

# Run bootstrap
terraform init
terraform plan
terraform apply

# Note the outputs
# s3_bucket_name = "my-company-fortigate-terraform-state"
# dynamodb_table_name = "fortigate-terraform-locks"

cd ../..
```

**Step 2: Deploy FortiGate with S3 Backend**

```bash
python3 deploy.py \
  --backend=s3 \
  --s3-bucket=my-company-fortigate-terraform-state \
  --s3-region=us-east-1 \
  --dynamodb-table=fortigate-terraform-locks
```

The script will:
1. Prompt for AWS credentials
2. Prompt for network configuration
3. Prompt for FortiGate configuration
4. Generate backend.tf with S3 configuration
5. Initialize Terraform with S3 backend
6. Generate and apply deployment plan

### Example 2: Development Deployment with Local Backend

For quick testing without S3 setup:

```bash
python3 deploy.py --backend=local
```

Or just:

```bash
python3 deploy.py
```

### Example 3: Plan-Only with S3 Backend

Review changes without applying:

```bash
python3 deploy.py \
  --plan-only \
  --backend=s3 \
  --s3-bucket=my-company-fortigate-terraform-state \
  --s3-region=us-east-1 \
  --dynamodb-table=fortigate-terraform-locks
```

### Example 4: Destroy with S3 Backend

Remove all resources:

```bash
python3 deploy.py \
  --destroy \
  --backend=s3 \
  --s3-bucket=my-company-fortigate-terraform-state \
  --s3-region=us-east-1 \
  --dynamodb-table=fortigate-terraform-locks
```

### Example 5: Using Configuration File with S3 Backend

**Create config.yaml:**

```yaml
aws:
  region: us-east-1
  profile: renaws

backend:
  backend_type: s3
  s3_bucket: my-company-fortigate-terraform-state
  s3_key: fortigate-ha/prod/terraform.tfstate
  s3_region: us-east-1
  dynamodb_table: fortigate-terraform-locks
  encrypt: true
  s3_profile: renaws

network:
  vpc_id: vpc-0e16490e6ab8422fb
  availability_zones:
    - us-east-1a
    - us-east-1b
  # ... rest of network config

fortigate:
  instance_type: c5.xlarge
  # ... rest of fortigate config

# ... rest of configuration
```

**Deploy using config file:**

```bash
python3 deploy.py --config=config.yaml
```

## Interactive Mode Examples

### Example 6: Interactive with Backend Prompts

Run without backend options to be prompted:

```bash
python3 deploy.py
```

You'll see:

```
🛡️  FortiGate AWS HA Deployment
==================================================

🔧 AWS Configuration
==================================================
AWS Region [us-east-1]: 
Use AWS profile? [Y/n]: y
AWS Profile name [default]: renaws

🌐 Network Configuration
==================================================
VPC ID (pre-assigned): vpc-0e16490e6ab8422fb
...

💾 Terraform Backend Configuration
==================================================
Backend type [local/s3] (local): s3

📦 S3 Backend Configuration
Note: S3 bucket and DynamoDB table should be created using terraform/bootstrap/

S3 bucket name (from bootstrap output): my-company-fortigate-terraform-state
S3 state file key [fortigate-ha/terraform.tfstate]: 
S3 bucket region [us-east-1]: 
DynamoDB table name (from bootstrap output) [fortigate-terraform-locks]: 
Encrypt state file? [Y/n]: y
Use AWS profile for backend? [Y/n]: y
AWS profile name [default]: renaws
```

## CI/CD Pipeline Examples

### Example 7: GitLab CI/CD with S3 Backend

```yaml
# .gitlab-ci.yml
deploy_production:
  stage: deploy
  script:
    - python3 deploy.py \
        --config=config-prod.yaml \
        --backend=s3 \
        --s3-bucket=${TF_STATE_BUCKET} \
        --s3-key=fortigate-ha/prod/terraform.tfstate \
        --s3-region=us-east-1 \
        --dynamodb-table=${TF_LOCK_TABLE}
  only:
    - main
  environment:
    name: production
```

### Example 8: GitHub Actions with S3 Backend

```yaml
# .github/workflows/deploy.yml
name: Deploy FortiGate HA

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Configure AWS Credentials
        uses: aws-actions/configure-aws-credentials@v1
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-1
      
      - name: Deploy FortiGate
        run: |
          python3 deploy.py \
            --config=config-prod.yaml \
            --backend=s3 \
            --s3-bucket=${{ secrets.TF_STATE_BUCKET }} \
            --s3-key=fortigate-ha/prod/terraform.tfstate \
            --s3-region=us-east-1 \
            --dynamodb-table=${{ secrets.TF_LOCK_TABLE }}
```

## Migration Examples

### Example 9: Migrate from Local to S3 Backend

**Current state**: Using local backend

**Step 1: Run bootstrap** (if not already done)

```bash
cd terraform/bootstrap
terraform init
terraform apply
cd ../..
```

**Step 2: Deploy with S3 backend**

```bash
python3 deploy.py \
  --backend=s3 \
  --s3-bucket=my-company-fortigate-terraform-state \
  --s3-region=us-east-1 \
  --dynamodb-table=fortigate-terraform-locks
```

Terraform will prompt:

```
Do you want to copy existing state to the new backend?
  Pre-existing state was found while migrating the previous "local" backend to the
  newly configured "s3" backend. No existing state was found in the newly
  configured "s3" backend. Do you want to copy this state to the new "s3"
  backend? Enter "yes" to copy and "no" to start with an empty state.

  Enter a value: yes
```

Type `yes` to migrate state.

**Step 3: Verify migration**

```bash
# Check state in S3
aws s3 ls s3://my-company-fortigate-terraform-state/fortigate-ha/ --profile renaws

# Should show: terraform.tfstate
```

### Example 10: Migrate from S3 to Local Backend

**Current state**: Using S3 backend

```bash
python3 deploy.py --backend=local
```

Terraform will prompt to migrate state back to local. Type `yes` to confirm.

## Troubleshooting Examples

### Example 11: Check Current Backend Configuration

```bash
cd terraform
terraform show
```

### Example 12: Force Unlock State

If state is locked and operation failed:

```bash
# Get lock ID from error message
# Then manually remove lock

aws dynamodb delete-item \
  --table-name fortigate-terraform-locks \
  --key '{"LockID":{"S":"my-bucket/fortigate-ha/terraform.tfstate-md5"}}' \
  --profile renaws \
  --region us-east-1
```

### Example 13: Verify S3 Backend Setup

```bash
# Check S3 bucket exists
aws s3 ls s3://my-company-fortigate-terraform-state --profile renaws

# Check DynamoDB table exists
aws dynamodb describe-table \
  --table-name fortigate-terraform-locks \
  --profile renaws \
  --region us-east-1

# Check state file
aws s3 ls s3://my-company-fortigate-terraform-state/fortigate-ha/ --profile renaws
```

## Best Practice Examples

### Example 14: Production Deployment with All Options

```bash
python3 deploy.py \
  --backend=s3 \
  --s3-bucket=my-company-fortigate-terraform-state \
  --s3-key=fortigate-ha/prod/terraform.tfstate \
  --s3-region=us-east-1 \
  --dynamodb-table=fortigate-terraform-locks \
  --config=config-prod.yaml \
  --save-config=config-prod-backup.yaml
```

### Example 15: Multi-Region Deployment

**US East:**
```bash
python3 deploy.py \
  --backend=s3 \
  --s3-bucket=my-company-fortigate-terraform-state \
  --s3-key=fortigate-ha/us-east-1/terraform.tfstate \
  --s3-region=us-east-1 \
  --dynamodb-table=fortigate-terraform-locks \
  --config=config-us-east-1.yaml
```

**US West:**
```bash
python3 deploy.py \
  --backend=s3 \
  --s3-bucket=my-company-fortigate-terraform-state \
  --s3-key=fortigate-ha/us-west-2/terraform.tfstate \
  --s3-region=us-east-1 \
  --dynamodb-table=fortigate-terraform-locks \
  --config=config-us-west-2.yaml
```

## Summary

### Local Backend (Development)
```bash
python3 deploy.py --backend=local
```

### S3 Backend (Production)
```bash
python3 deploy.py \
  --backend=s3 \
  --s3-bucket=<bucket-name> \
  --s3-region=<region> \
  --dynamodb-table=<table-name>
```

### Show Bootstrap Info
```bash
python3 deploy.py --bootstrap-info
```

---

**For complete documentation, see:**
- BACKEND-CONFIGURATION-GUIDE.md - Comprehensive guide
- DEPLOY-PY-BACKEND-UPDATE.md - Technical details
- terraform/bootstrap/README.md - Bootstrap setup

