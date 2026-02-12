# delete-enis.py - Quick Reference

## One-Line Commands

### Dry Run (Safe - No Deletion)
```bash
python3 delete-enis.py --profile renaws --region us-east-1 --tag "deployment-001" --dry-run
```

### Delete with Confirmation
```bash
python3 delete-enis.py --profile renaws --region us-east-1 --tag "deployment-001"
```

### Force Delete (No Confirmation)
```bash
python3 delete-enis.py --profile renaws --region us-east-1 --tag "deployment-001" --force
```

---

## What Gets Deleted

| Resource Type | Action |
|---------------|--------|
| **Elastic IPs** | Disassociated and released |
| **Network Interfaces** | Detached and deleted |
| **Security Groups** | Deleted (with retry logic) |

---

## Quick Workflow

```bash
# 1. See what will be deleted (DRY RUN)
python3 delete-enis.py --profile renaws --region us-east-1 --tag "deployment-001" --dry-run

# 2. Review the output

# 3. Delete resources
python3 delete-enis.py --profile renaws --region us-east-1 --tag "deployment-001"

# 4. Type "DELETE" when prompted
```

---

## Command Options

| Option | Required | Description |
|--------|----------|-------------|
| `--profile` | No | AWS profile name |
| `--region` | No | AWS region (default: us-east-1) |
| `--tag` | **YES** | CreatedBy tag value |
| `--dry-run` | No | List only, don't delete |
| `--force` | No | Skip confirmation |

---

## Safety Features

✅ Requires typing "DELETE" to confirm  
✅ Shows detailed resource list before deletion  
✅ Dry-run mode available  
✅ Tag-based filtering prevents accidents  
✅ Graceful error handling  

---

## Common Use Cases

### Test Deployment Cleanup
```bash
python3 delete-enis.py --profile renaws --region us-east-1 --tag "john-test"
```

### Multiple Deployments
```bash
# Delete deployment 1
python3 delete-enis.py --profile renaws --region us-east-1 --tag "deployment-001"

# Delete deployment 2
python3 delete-enis.py --profile renaws --region us-east-1 --tag "deployment-002"
```

### Automated Cleanup
```bash
#!/bin/bash
TAG="deployment-001"
python3 delete-enis.py --profile renaws --region us-east-1 --tag "$TAG" --force
```

---

## Troubleshooting

### No Resources Found
```bash
# List all CreatedBy tags
aws resourcegroupstaggingapi get-resources \
  --tag-filters "Key=CreatedBy" \
  --profile renaws --region us-east-1 \
  --query 'ResourceTagMappingList[*].Tags[?Key==`CreatedBy`].Value' \
  --output text | sort -u
```

### ENI In Use
```bash
# Terminate instance first
aws ec2 terminate-instances --instance-ids i-xxxxx --profile renaws --region us-east-1

# Then retry deletion
python3 delete-enis.py --profile renaws --region us-east-1 --tag "deployment-001"
```

### Security Group Dependencies
- Script automatically retries 3 times
- Wait 5-10 minutes and retry if needed
- Check for resources using the SG

---

## Before You Delete

- [ ] Ran dry-run first
- [ ] Verified correct tag value
- [ ] Reviewed resource list
- [ ] Terminated EC2 instances (if any)
- [ ] Ready to confirm deletion

---

## Example Output

```
🔍 Searching for resources with tag: CreatedBy=deployment-001
✅ Found 8 Network Interface(s)
✅ Found 2 Elastic IP(s)
✅ Found 3 Security Group(s)

📊 Summary: 13 resource(s) found

Type 'DELETE' (in capital letters) to confirm: DELETE

🗑️  Starting deletion process...
✅ Successfully deleted: 13 resource(s)
✅ All resources deleted successfully!
```

---

## Related Commands

### Create Resources
```bash
python3 create-enis.py --profile renaws --region us-east-1 --account 678632990402 \
  --allocate-eips --tag "deployment-001"
```

### List Resources by Tag
```bash
aws resourcegroupstaggingapi get-resources \
  --tag-filters "Key=CreatedBy,Values=deployment-001" \
  --profile renaws --region us-east-1
```

---

**Pro Tip**: Always use `--dry-run` first to verify what will be deleted!

**Documentation**: See [DELETE-RESOURCES-GUIDE.md](DELETE-RESOURCES-GUIDE.md) for complete guide
