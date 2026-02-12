# Streamlit Web Application Enhancement Specification

## Objective

Update the Streamlit web application (`web-app.py`) to have complete feature parity with the `deploy.py` CLI script, ensuring all 60+ parameters and deployment capabilities are available through the web interface.

## Current Gaps

### Missing Features from deploy.py:

1. **ENI Configuration** (8 parameters)
   - Primary/Backup ENI IDs for all 4 interfaces
   - Currently not captured in web form

2. **EIP Failover Configuration** (NEW)
   - enable_eip_failover toggle
   - Explanation of failover behavior
   - IAM role implications

3. **Backend Configuration**
   - S3 backend setup
   - DynamoDB table configuration
   - Local vs remote state selection
   - Bootstrap information display

4. **Advanced Options**
   - Skip validation mode
   - Plan-only mode (exists but needs enhancement)
   - Configuration file import/export
   - Save configuration functionality

5. **AMI Discovery**
   - List available versions
   - Auto-discovery with real AWS API calls
   - Version selection from discovered AMIs

6. **Licensing**
   - Complete BYOL configuration (Secrets Manager + S3)
   - License file validation
   - OnDemand marketplace subscription check
   - Reserved instance configuration

7. **Validation**
   - AWS resource validation (VPC, subnets, ENIs, EIPs)
   - Pre-deployment checks
   - Configuration validation
   - Real-time validation feedback

8. **Deployment Operations**
   - Real Terraform integration
   - Live log streaming
   - Progress tracking
   - Error handling and rollback
   - Destroy functionality

9. **Configuration Management**
   - Import YAML/JSON configuration
   - Export configuration to file
   - Load from terraform.tfvars
   - Configuration templates

10. **Documentation Integration**
    - Link to DEPLOYMENT-PARAMETERS-GUIDE.md
    - Context-sensitive help
    - Parameter descriptions
    - Validation rules display

## Required Enhancements

### 1. Complete Configuration Form

Add all missing parameters to match deploy.py:

```python
# ENI Configuration Section
st.markdown("### ENI Configuration (Pre-created)")
st.info("ENIs must be created using create-enis.py before deployment")

col1, col2 = st.columns(2)

with col1:
    st.markdown("**Primary FortiGate ENIs:**")
    primary_outside_eni = st.text_input("Outside ENI ID", key="pri_out_eni")
    primary_inside_eni = st.text_input("Inside ENI ID", key="pri_in_eni")
    primary_ha_eni = st.text_input("HA ENI ID", key="pri_ha_eni")
    primary_mgmt_eni = st.text_input("Management ENI ID", key="pri_mgmt_eni")

with col2:
    st.markdown("**Backup FortiGate ENIs:**")
    backup_outside_eni = st.text_input("Outside ENI ID", key="bak_out_eni")
    backup_inside_eni = st.text_input("Inside ENI ID", key="bak_in_eni")
    backup_ha_eni = st.text_input("HA ENI ID", key="bak_ha_eni")
    backup_mgmt_eni = st.text_input("Management ENI ID", key="bak_mgmt_eni")
```

### 2. EIP Failover Configuration

```python
# EIP Configuration Section
st.markdown("### Elastic IP Configuration")

allocate_eips = st.checkbox("Allocate Elastic IPs for outside interfaces", value=True)

if allocate_eips:
    use_existing_eips = st.checkbox("Use existing EIP allocation IDs")
    
    if use_existing_eips:
        col1, col2 = st.columns(2)
        with col1:
            primary_eip_id = st.text_input("Primary EIP Allocation ID (optional)")
        with col2:
            backup_eip_id = st.text_input("Backup EIP Allocation ID (optional)")
    
    # EIP Failover
    st.markdown("#### EIP Failover Configuration")
    st.info("""
    FortiGate HA can automatically manage EIP failover using AWS SDN connector.
    This requires IAM permissions and AWS SDN connector configuration.
    """)
    
    enable_eip_failover = st.checkbox("Enable FortiGate HA EIP failover", value=True)
    
    if enable_eip_failover:
        st.success("✅ EIP failover enabled - FortiGate will manage EIP associations")
        st.markdown("""
        - EIPs will be allocated but NOT statically associated
        - FortiGate HA will move EIPs during failover events
        - IAM role will be created with EC2 EIP management permissions
        """)
    else:
        st.warning("⚠️ EIP failover disabled - EIPs will be statically associated")
        st.markdown("Manual intervention required for EIP failover")
```

### 3. Backend Configuration

```python
# Backend Configuration Section
st.markdown("### Terraform Backend Configuration")

backend_type = st.radio(
    "Backend Type",
    ["Local (terraform.tfstate)", "S3 (Remote State)"],
    index=0
)

if "S3" in backend_type:
    st.info("S3 backend requires bootstrap setup. Run terraform/bootstrap first.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        s3_bucket = st.text_input("S3 Bucket Name", help="From bootstrap output")
        s3_key = st.text_input("S3 State File Key", value="fortigate-ha/terraform.tfstate")
        s3_region = st.text_input("S3 Bucket Region", value=aws_region)
    
    with col2:
        dynamodb_table = st.text_input("DynamoDB Table", value="fortigate-terraform-locks")
        encrypt = st.checkbox("Encrypt state file", value=True)
        
        use_kms = st.checkbox("Use KMS encryption")
        if use_kms:
            kms_key_id = st.text_input("KMS Key ID or ARN")
    
    if st.button("Show Bootstrap Instructions"):
        st.code("""
        cd terraform/bootstrap
        cp terraform.tfvars.example terraform.tfvars
        # Edit terraform.tfvars
        terraform init
        terraform apply
        # Note the outputs for S3 bucket and DynamoDB table
        """, language="bash")
```

### 4. Configuration Import/Export

```python
# Configuration Management
st.markdown("### Configuration Management")

col1, col2, col3 = st.columns(3)

with col1:
    uploaded_file = st.file_uploader(
        "Import Configuration",
        type=['yaml', 'yml', 'json'],
        help="Load configuration from YAML or JSON file"
    )
    
    if uploaded_file:
        if st.button("Load Configuration"):
            load_configuration_from_file(uploaded_file)

with col2:
    if st.button("Export Configuration"):
        export_configuration_to_file()

with col3:
    if st.button("Load from terraform.tfvars"):
        load_from_tfvars()
```

### 5. Advanced Options

```python
# Advanced Options
with st.expander("Advanced Options"):
    skip_validation = st.checkbox(
        "Skip AWS validation",
        help="Skip AWS API validation checks (Terraform will still validate)"
    )
    
    plan_only = st.checkbox(
        "Plan only (do not deploy)",
        help="Generate Terraform plan without applying changes"
    )
    
    auto_approve = st.checkbox(
        "Auto-approve deployment",
        value=False,
        help="Skip confirmation prompt before deployment"
    )
```

### 6. Real AMI Discovery

```python
def discover_ami_real(aws_session, version, license_type, architecture):
    """Real AMI discovery using AWS API"""
    try:
        ami_discovery = AMIDiscovery(aws_session)
        ami_id = ami_discovery.find_latest_ami(version, license_type, architecture)
        
        if ami_id:
            # Get AMI details
            ec2 = aws_session.client('ec2')
            response = ec2.describe_images(ImageIds=[ami_id])
            
            if response['Images']:
                image = response['Images'][0]
                return {
                    "success": True,
                    "ami_id": ami_id,
                    "name": image['Name'],
                    "description": image.get('Description', 'N/A'),
                    "creation_date": image['CreationDate'],
                    "state": image['State']
                }
        
        return {"success": False, "error": "No AMI found"}
    
    except Exception as e:
        return {"success": False, "error": str(e)}

def list_available_versions_real(aws_session):
    """List available FortiGate versions using AWS API"""
    try:
        ami_discovery = AMIDiscovery(aws_session)
        versions = ami_discovery.list_available_versions()
        return versions
    except Exception as e:
        st.error(f"Error listing versions: {e}")
        return []
```

### 7. Real Validation

```python
def validate_configuration_real(config, aws_session):
    """Real configuration validation using AWS API"""
    validator = ConfigurationValidator(aws_session)
    
    validation_results = {
        "vpc": False,
        "subnets": False,
        "enis": False,
        "eips": False,
        "tgw": False,
        "ami": False,
        "key_pair": False
    }
    
    with st.spinner("Validating configuration..."):
        # Validate VPC
        if validator.validate_vpc(config.network.vpc_id):
            validation_results["vpc"] = True
            st.success(f"✅ VPC {config.network.vpc_id} validated")
        else:
            st.error(f"❌ VPC {config.network.vpc_id} validation failed")
        
        # Validate subnets
        all_subnets = [
            config.network.outside_subnet_primary,
            config.network.inside_subnet_primary,
            # ... all 8 subnets
        ]
        
        if validator.validate_subnets(all_subnets, config.network.availability_zones):
            validation_results["subnets"] = True
            st.success("✅ All subnets validated")
        else:
            st.error("❌ Subnet validation failed")
        
        # Validate ENIs
        all_enis = [
            config.network.primary_outside_eni_id,
            # ... all 8 ENIs
        ]
        
        if validator.validate_enis(all_enis):
            validation_results["enis"] = True
            st.success("✅ All ENIs validated")
        else:
            st.error("❌ ENI validation failed")
        
        # ... continue for other resources
    
    return validation_results
```

### 8. Real Deployment Integration

```python
def deploy_real(config, plan_only=False, skip_validation=False):
    """Real deployment using DeploymentEngine"""
    try:
        engine = DeploymentEngine(config)
        
        if plan_only:
            st.info("Generating Terraform plan...")
            success = engine.plan()
            
            if success:
                st.success("✅ Plan generated successfully!")
                st.info("Review the plan in terraform/tfplan")
            else:
                st.error("❌ Plan generation failed")
            
            return success
        
        else:
            st.info("Starting deployment...")
            success = engine.deploy(skip_validation=skip_validation)
            
            if success:
                st.success("🎉 Deployment completed successfully!")
                display_deployment_outputs()
            else:
                st.error("❌ Deployment failed")
            
            return success
    
    except Exception as e:
        st.error(f"Deployment error: {e}")
        return False

def destroy_real(config):
    """Real destroy using DeploymentEngine"""
    try:
        engine = DeploymentEngine(config)
        
        st.warning("⚠️ This will destroy all FortiGate resources!")
        
        if st.button("Confirm Destroy", type="primary"):
            with st.spinner("Destroying resources..."):
                success = engine.destroy()
                
                if success:
                    st.success("✅ Resources destroyed successfully")
                else:
                    st.error("❌ Destroy failed")
                
                return success
    
    except Exception as e:
        st.error(f"Destroy error: {e}")
        return False
```

### 9. Live Log Streaming

```python
def stream_terraform_logs():
    """Stream Terraform logs in real-time"""
    log_placeholder = st.empty()
    
    # Monitor terraform log file
    log_file = Path("terraform/terraform.log")
    
    if log_file.exists():
        with open(log_file, 'r') as f:
            logs = f.readlines()
            
            # Display last 50 lines
            log_placeholder.code('\n'.join(logs[-50:]), language="log")
```

### 10. Context-Sensitive Help

```python
def show_parameter_help(parameter_name):
    """Show help for specific parameter"""
    help_text = {
        "vpc_id": """
        **VPC ID**: Pre-existing VPC where FortiGate instances will be deployed
        - Format: vpc-[a-z0-9]{8,17}
        - Must exist in the target region
        - Example: vpc-0e16490e6ab8422fb
        """,
        "enable_eip_failover": """
        **EIP Failover**: Enable automatic EIP failover using AWS SDN connector
        - When enabled: IAM role created, EIPs allocated but not associated
        - When disabled: EIPs statically associated, manual failover required
        - Requires: IAM permissions for EC2 EIP management
        """,
        # ... add all parameters
    }
    
    if parameter_name in help_text:
        st.info(help_text[parameter_name])
```

## Implementation Plan

### Phase 1: Core Parameters (Week 1)
- Add all 60+ parameters to configuration form
- Implement ENI configuration section
- Add EIP failover configuration
- Add backend configuration

### Phase 2: Configuration Management (Week 1)
- Implement configuration import/export
- Add terraform.tfvars loading
- Add configuration validation
- Add configuration templates

### Phase 3: Real Integration (Week 2)
- Integrate real AMI discovery
- Implement real validation
- Connect to DeploymentEngine
- Add live log streaming

### Phase 4: Advanced Features (Week 2)
- Add plan-only mode
- Implement destroy functionality
- Add skip validation option
- Implement rollback capability

### Phase 5: Polish & Documentation (Week 3)
- Add context-sensitive help
- Improve error handling
- Add progress indicators
- Update documentation

## Testing Checklist

- [ ] All 60+ parameters captured
- [ ] Configuration import/export works
- [ ] AMI discovery functional
- [ ] Validation checks work
- [ ] Deployment succeeds
- [ ] Plan-only mode works
- [ ] Destroy functionality works
- [ ] Error handling robust
- [ ] Help text comprehensive
- [ ] UI responsive and intuitive

## Success Criteria

1. **Feature Parity**: All deploy.py capabilities available in web app
2. **Usability**: Easier to use than CLI for most users
3. **Reliability**: Same success rate as CLI deployment
4. **Documentation**: Clear help text for all parameters
5. **Performance**: Responsive UI with real-time feedback

## Related Documentation

- DEPLOYMENT-PARAMETERS-GUIDE.md - Complete parameter reference
- deploy.py - CLI implementation to match
- ROOT-LEVEL-INTEGRATION-COMPLETE.md - EIP failover details
- STATE_MANAGEMENT_GUIDE.md - Backend configuration

## Notes

- Maintain backward compatibility with existing configurations
- Ensure all validations match deploy.py behavior
- Provide clear error messages and recovery options
- Add tooltips and help text for all parameters
- Support both interactive and batch deployment modes
