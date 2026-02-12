# Cleanup Scripts Parameterization Update

## Summary

All cleanup scripts and documentation have been updated to accept AWS profile and region as command-line parameters instead of using hardcoded values.

## Changes Made

### 1. Scripts Updated

#### force-cleanup.sh
- Added `--profile` parameter (required)
- Added `--region` parameter (optional, defaults to us-east-1)
- Added usage help with `--help` flag
- Validates required parameters before execution
- Passes profile to all AWS CLI commands and Terraform

#### check-stuck-resources.sh
- Added `--profile` parameter (required)
- Added `--region` parameter (optional, defaults to us-east-1)
- Added usage help with `--help` flag
- Validates required parameters before execution

### 2. Documentation Updated

#### CLEANUP-SUMMARY.md
- Updated quick fix command to include parameters
- Updated verification commands to include profile/region
- Updated next steps with parameterized commands

#### MANUAL-CLEANUP-STEPS.md
- Updated all AWS CLI commands to include profile and region
- Updated quick reference section

#### TERRAFORM-DESTROY-TROUBLESHOOTING.md
- Updated script invocation examples
- Updated quick reference commands

## Usage Examples

### Force Cleanup Script
```bash
cd fortigate-aws-ha-deployment
./force-cleanup.sh --profile renaws --region us-east-1
```

### Check Resources Script
```bash
cd fortigate-aws-ha-deployment
./check-stuck-resources.sh --profile renaws --region us-east-1
```

### Get Help
```bash
./force-cleanup.sh --help
./check-stuck-resources.sh --help
```

## Benefits

1. **No Hardcoded Credentials**: Scripts can be used with any AWS profile
2. **Reusable**: Same scripts work across different AWS accounts/profiles
3. **Flexible**: Region can be changed without editing scripts
4. **Safe**: Requires explicit profile specification, preventing accidental operations
5. **Clear**: Help text guides users on proper usage

## Testing

Both scripts have been validated:
- ✅ Bash syntax check passed
- ✅ Help output displays correctly
- ✅ Parameter parsing works as expected
- ✅ Scripts are executable

## Next Steps

To use the cleanup scripts:

1. Ensure AWS CLI is configured with your profile:
   ```bash
   aws configure --profile renaws
   ```

2. Run the force cleanup:
   ```bash
   ./force-cleanup.sh --profile renaws --region us-east-1
   ```

3. Verify cleanup:
   ```bash
   ./check-stuck-resources.sh --profile renaws --region us-east-1
   ```

## Files Modified

- `force-cleanup.sh` - Added parameter parsing
- `check-stuck-resources.sh` - Added parameter parsing
- `CLEANUP-SUMMARY.md` - Updated all command examples
- `MANUAL-CLEANUP-STEPS.md` - Updated all command examples
- `TERRAFORM-DESTROY-TROUBLESHOOTING.md` - Updated script invocations

---

**Status**: Complete ✅
**Date**: 2026-02-12
