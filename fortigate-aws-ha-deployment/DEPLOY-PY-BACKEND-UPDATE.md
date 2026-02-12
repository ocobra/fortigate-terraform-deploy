# deploy.py Backend Configuration Update

## Summary

Updated the `deploy.py` script to support both local and S3 backend configurations for Terraform state management, with integration to the existing bootstrap infrastructure.

## Changes Made

### 1. New Data Classes

Added `BackendConfig` dataclass to handle backend configuration:

```python
@dataclass
class BackendConfig:
    """Terraform backend configuration"""
    backend_type: str = "local"  # local or s3
    # S3 backend options
    s3_bucket: Optional[str] = None
    s3_key: Optional[str] = None
    s3_region: Optional[str] = None
    dynamodb_table: Optional[str] = None
    encrypt: bool = True
    # Additional S3 options
    s3_profile: Optional[str] = None
    kms_key_id: Optional[str] = None
```

### 2. Updated TerraformManager Class

Enhanced `TerraformManager` to handle backend configuration:

**New Methods:**
- `configure_backend()` - Generates `backend.tf` file for S3 backend or removes it for local backend
- Updated `init()` - Added `reconfigure` parameter for backend switching

**Features:**
- Automatically generates `backend.tf` with S3 configuration
- Supports KMS encryption
- Supports AWS profile for backend authentication
- Removes `backend.tf` when using local backend

### 3. New Interactive Prompts

Added `prompt_backend_config()` function that prompts users for:
- Backend type (local or s3)
- S3 bucket name (from bootstrap output)
- S3 key path
- S3 region
- DynamoDB table name
- Encryption options
- AWS profile for backend
- KMS key ID (optional)

### 4. Command-Line Options

Added new CLI options:

```bash
--backend [local|s3]           # Backend type
--s3-bucket TEXT               # S3 bucket name
--s3-key TEXT                  # S3 state file key
--s3-region TEXT               # S3 bucket region
--dynamodb-table TEXT          # DynamoDB table name
--bootstrap-info               # Show bootstrap setup info
```

### 5. Bootstrap Integration

The script now references the existing `terraform/bootstrap/` directory:

- Prompts mention bootstrap setup
- `--bootstrap-info` flag shows complete bootstrap instructions
- Validates that S3 bucket and DynamoDB table exist (created by bootstrap)

### 6. Updated DeploymentConfig

Added `backend` field to `DeploymentConfig` dataclass to include backend configuration in the deployment configuration.

## Usage Examples

### 1. Show Bootstrap Information

```bash
python3 deploy.py --bootstrap-info
```

Output:
```
📦 Terraform State Management Bootstrap
==================================================

Before using S3 backend, you must first create the S3 bucket and DynamoDB table.

Steps:
1. Navigate to bootstrap directory:
   cd terraform/bootstrap

2. Copy and configure variables:
   cp terraform.tfvars.example terraform.tfvars
   # Edit terraform.tfvars with your values

3. Run bootstrap:
   terraform init
   terraform plan
   terraform apply

4. Note the outputs (bucket name and DynamoDB table)

5. Use those values when deploying with --backend=s3
```

### 2. Deploy with Local Backend (Default)

```bash
# Interactive mode
python3 deploy.py

# Explicit
python3 deploy.py --backend=local
```

### 3. Deploy with S3 Backend

```bash
python3 deploy.py \
  --backend=s3 \
  --s3-bucket=my-company-fortigate-terraform-state \
  --s3-region=us-east-1 \
  --dynamodb-table=fortigate-terraform-locks
```

### 4. Deploy with Custom S3 Key

```bash
python3 deploy.py \
  --backend=s3 \
  --s3-bucket=my-company-fortigate-terraform-state \
  --s3-key=fortigate-ha/prod/terraform.tfstate \
  --s3-region=us-east-1 \
  --dynamodb-table=fortigate-terraform-locks
```

### 5. Interactive Backend Configuration

When running without `--backend` option, the script will prompt:

```
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

## Backend Configuration Flow

### Local Backend Flow

1. User selects `local` backend (or default)
2. Script removes `backend.tf` if it exists
3. Terraform uses default local backend
4. State stored in `terraform/terraform.tfstate`

### S3 Backend Flow

1. User provides S3 backend configuration
2. Script validates required parameters
3. Script generates `terraform/backend.tf`:
   ```hcl
   terraform {
     backend "s3" {
       bucket         = "my-bucket"
       key            = "fortigate-ha/terraform.tfstate"
       region         = "us-east-1"
       dynamodb_table = "fortigate-terraform-locks"
       encrypt        = true
       profile        = "renaws"  # optional
       kms_key_id     = "..."     # optional
     }
   }
   ```
4. Script runs `terraform init -reconfigure`
5. Terraform migrates state to S3 (if switching from local)
6. State stored in S3 with DynamoDB locking

## Generated backend.tf Example

When using S3 backend, the script generates:

```hcl
# Terraform Backend Configuration
# Generated by deploy.py

terraform {
  backend "s3" {
    bucket         = "my-company-fortigate-terraform-state"
    key            = "fortigate-ha/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "fortigate-terraform-locks"
    encrypt        = true
    profile        = "renaws"
  }
}
```

## Benefits

### 1. Flexibility
- Choose between local and S3 backend based on needs
- Easy switching between backends
- Support for multiple environments with different state files

### 2. Production-Ready
- S3 backend with DynamoDB locking for production
- State versioning and backup
- Encrypted state storage
- Team collaboration support

### 3. Integration
- Seamless integration with existing bootstrap infrastructure
- References bootstrap outputs
- Consistent with existing documentation

### 4. User-Friendly
- Interactive prompts guide users through configuration
- Clear error messages and validation
- Bootstrap information readily available

### 5. Automation-Friendly
- Command-line options for CI/CD pipelines
- Configuration file support
- Non-interactive mode support

## Migration Path

### From Local to S3

1. Run bootstrap to create S3 bucket and DynamoDB table
2. Run deploy.py with S3 backend options
3. Terraform automatically migrates state

```bash
# Step 1: Bootstrap (one-time)
cd terraform/bootstrap
terraform init
terraform apply

# Step 2: Deploy with S3 backend
cd ../..
python3 deploy.py \
  --backend=s3 \
  --s3-bucket=my-bucket \
  --s3-region=us-east-1
```

### From S3 to Local

Simply run with local backend:

```bash
python3 deploy.py --backend=local
```

Terraform will prompt to migrate state back to local.

## Error Handling

### Missing S3 Bucket

```
❌ --s3-bucket is required when using --backend=s3
💡 Run with --bootstrap-info to see setup instructions
```

### Invalid Backend Configuration

```
❌ S3 backend requires: bucket, key, region, and dynamodb_table
```

### State Lock Conflicts

Terraform will show:
```
Error acquiring the state lock
```

User can manually remove lock from DynamoDB if needed.

## Documentation

Created comprehensive documentation:

1. **BACKEND-CONFIGURATION-GUIDE.md** - Complete guide covering:
   - Backend options comparison
   - Bootstrap setup instructions
   - Usage examples
   - Switching between backends
   - Troubleshooting
   - Best practices

2. **DEPLOY-PY-BACKEND-UPDATE.md** (this file) - Technical summary of changes

## Testing

### Test Scenarios

1. ✅ Deploy with local backend (default)
2. ✅ Deploy with S3 backend via CLI options
3. ✅ Deploy with S3 backend via interactive prompts
4. ✅ Switch from local to S3 backend
5. ✅ Switch from S3 to local backend
6. ✅ Show bootstrap information
7. ✅ Error handling for missing S3 bucket
8. ✅ Backend configuration in config file

### Validation

- Backend.tf file generated correctly for S3
- Backend.tf removed for local backend
- Terraform init runs with correct parameters
- State migration works correctly
- DynamoDB locking functions properly

## Files Modified

1. **deploy.py**
   - Added `BackendConfig` dataclass
   - Updated `TerraformManager` class
   - Added `prompt_backend_config()` function
   - Added CLI options for backend configuration
   - Added `--bootstrap-info` handler
   - Updated `DeploymentConfig` to include backend

## Files Created

1. **BACKEND-CONFIGURATION-GUIDE.md** - User guide
2. **DEPLOY-PY-BACKEND-UPDATE.md** - Technical summary

## Next Steps

### For Users

1. Review BACKEND-CONFIGURATION-GUIDE.md
2. Run bootstrap if using S3 backend
3. Use deploy.py with desired backend option

### For Production Deployments

1. Always use S3 backend with DynamoDB locking
2. Separate state files by environment
3. Enable versioning and encryption
4. Restrict access to state bucket

## Quick Reference

```bash
# Show bootstrap info
python3 deploy.py --bootstrap-info

# Local backend (default)
python3 deploy.py --backend=local

# S3 backend
python3 deploy.py \
  --backend=s3 \
  --s3-bucket=my-bucket \
  --s3-region=us-east-1 \
  --dynamodb-table=my-locks-table

# Interactive mode (prompts for backend)
python3 deploy.py
```

---

**Status**: Complete ✅
**Date**: 2026-02-12
**Impact**: High - Enables production-ready state management
**Breaking Changes**: None - Backward compatible (defaults to local backend)

