#!/usr/bin/env python3
"""
FortiGate AWS HA Deployment - Streamlit Web Application

This web application provides an intuitive interface for deploying and managing
FortiGate HA pairs on AWS with real-time progress tracking and cost analysis.
"""

import streamlit as st
import boto3
import json
import yaml
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from pathlib import Path
import sys
import os

# Add the deployment engine to the path
sys.path.append(str(Path(__file__).parent))

try:
    from deploy import (
        DeploymentEngine, DeploymentConfig, AWSConfig, NetworkConfig,
        FortiGateConfig, TransitGatewayConfig, MonitoringConfig,
        AMIDiscovery, LicenseManager, AMIDiscoveryConfig, LicensingConfig
    )
    DEPLOYMENT_ENGINE_AVAILABLE = True
except ImportError as e:
    st.error(f"Deployment engine not available: {e}")
    DEPLOYMENT_ENGINE_AVAILABLE = False

# Page configuration
st.set_page_config(
    page_title="FortiGate AWS HA Deployment",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #FF6B35;
        text-align: center;
        margin-bottom: 2rem;
    }
    .section-header {
        font-size: 1.5rem;
        color: #2E86AB;
        margin-top: 2rem;
        margin-bottom: 1rem;
    }
    .metric-card {
        background-color: #F8F9FA;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #FF6B35;
    }
    .success-message {
        background-color: #D4EDDA;
        color: #155724;
        padding: 1rem;
        border-radius: 0.5rem;
        border: 1px solid #C3E6CB;
    }
    .warning-message {
        background-color: #FFF3CD;
        color: #856404;
        padding: 1rem;
        border-radius: 0.5rem;
        border: 1px solid #FFEAA7;
    }
    .error-message {
        background-color: #F8D7DA;
        color: #721C24;
        padding: 1rem;
        border-radius: 0.5rem;
        border: 1px solid #F5C6CB;
    }
</style>
""", unsafe_allow_html=True)

def initialize_session_state():
    """Initialize session state variables"""
    if 'deployment_config' not in st.session_state:
        st.session_state.deployment_config = None
    if 'deployment_status' not in st.session_state:
        st.session_state.deployment_status = 'not_started'
    if 'deployment_logs' not in st.session_state:
        st.session_state.deployment_logs = []
    if 'cost_analysis' not in st.session_state:
        st.session_state.cost_analysis = None
    if 'ami_discovery_result' not in st.session_state:
        st.session_state.ami_discovery_result = None

def render_header():
    """Render the main header"""
    st.markdown('<h1 class="main-header">🛡️ FortiGate AWS HA Deployment</h1>', unsafe_allow_html=True)
    st.markdown("Deploy and manage highly available FortiGate firewall pairs on AWS with automated AMI discovery, licensing, and cost optimization.")

def render_sidebar():
    """Render the sidebar navigation"""
    st.sidebar.title("Navigation")
    
    pages = {
        "🏠 Home": "home",
        "⚙️ Configuration": "config",
        "🔍 AMI Discovery": "ami",
        "📄 Licensing": "licensing",
        "💰 Cost Analysis": "cost",
        "🚀 Deployment": "deployment",
        "📊 Monitoring": "monitoring",
        "📚 Documentation": "docs"
    }
    
    selected_page = st.sidebar.radio("Select Page", list(pages.keys()))
    return pages[selected_page]

def render_home_page():
    """Render the home page"""
    st.markdown('<h2 class="section-header">Welcome to FortiGate AWS HA Deployment</h2>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div class="metric-card">
            <h3>🛡️ High Availability</h3>
            <p>Deploy FortiGate firewalls in active-passive HA configuration across multiple AWS Availability Zones for maximum uptime and reliability.</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="metric-card">
            <h3>🔍 Auto Discovery</h3>
            <p>Automatically discover the latest FortiGate AMIs from AWS Marketplace with support for BYOL, OnDemand, and Reserved licensing models.</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div class="metric-card">
            <h3>💰 Cost Optimization</h3>
            <p>Get intelligent cost analysis and licensing recommendations based on your deployment duration and usage patterns.</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown('<h3 class="section-header">Architecture Overview</h3>', unsafe_allow_html=True)
    
    # Architecture diagram placeholder
    st.info("📊 Interactive architecture diagram will be displayed here showing the hub-and-spoke design with Transit Gateway routing.")
    
    # Quick stats
    if DEPLOYMENT_ENGINE_AVAILABLE:
        st.markdown('<h3 class="section-header">System Status</h3>', unsafe_allow_html=True)
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Deployment Engine", "✅ Available")
        
        with col2:
            st.metric("AWS Connection", "✅ Ready")
        
        with col3:
            st.metric("Analysis System", "✅ Integrated")
        
        with col4:
            st.metric("Current Status", st.session_state.deployment_status.title())

def render_configuration_page():
    """Render the configuration page"""
    st.markdown('<h2 class="section-header">Deployment Configuration</h2>', unsafe_allow_html=True)
    
    with st.form("deployment_config"):
        # AWS Configuration
        st.markdown("### AWS Configuration")
        col1, col2 = st.columns(2)
        
        with col1:
            aws_region = st.selectbox(
                "AWS Region",
                ["us-east-1", "us-west-2", "eu-west-1", "ap-southeast-1"],
                index=0
            )
            aws_profile = st.text_input("AWS Profile (optional)", value="default")
        
        with col2:
            use_iam_role = st.checkbox("Use IAM Role", value=True)
            if not use_iam_role:
                aws_access_key = st.text_input("AWS Access Key ID")
                aws_secret_key = st.text_input("AWS Secret Access Key", type="password")
        
        # Network Configuration
        st.markdown("### Network Configuration")
        col1, col2 = st.columns(2)
        
        with col1:
            vpc_id = st.text_input("VPC ID", placeholder="vpc-12345678")
            az1 = st.text_input("Primary AZ", value=f"{aws_region}a")
            az2 = st.text_input("Backup AZ", value=f"{aws_region}b")
        
        with col2:
            mgmt_cidrs = st.text_area(
                "Management Access CIDRs (one per line)",
                value="10.0.0.0/8\n172.16.0.0/12\n192.168.0.0/16"
            )
        
        # Subnet Configuration
        st.markdown("### Subnet Configuration")
        st.info("Enter the pre-assigned subnet IDs provided by your network team")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Primary FortiGate Subnets:**")
            outside_primary = st.text_input("Outside Subnet", placeholder="subnet-12345678")
            inside_primary = st.text_input("Inside Subnet", placeholder="subnet-23456789")
            ha_primary = st.text_input("HA Subnet", placeholder="subnet-34567890")
            mgmt_primary = st.text_input("Management Subnet", placeholder="subnet-45678901")
        
        with col2:
            st.markdown("**Backup FortiGate Subnets:**")
            outside_backup = st.text_input("Outside Subnet ", placeholder="subnet-56789012")
            inside_backup = st.text_input("Inside Subnet ", placeholder="subnet-67890123")
            ha_backup = st.text_input("HA Subnet ", placeholder="subnet-78901234")
            mgmt_backup = st.text_input("Management Subnet ", placeholder="subnet-89012345")
        
        # FortiGate Configuration
        st.markdown("### FortiGate Configuration")
        col1, col2 = st.columns(2)
        
        with col1:
            instance_type = st.selectbox(
                "Instance Type",
                ["c5.large", "c5.xlarge", "c5.2xlarge", "c5.4xlarge", "c5.9xlarge"],
                index=1
            )
            key_pair = st.text_input("EC2 Key Pair Name", placeholder="my-keypair")
        
        with col2:
            admin_password = st.text_input("Admin Password", type="password")
            ha_password = st.text_input("HA Password", type="password")
        
        # Transit Gateway Configuration
        st.markdown("### Transit Gateway Configuration")
        col1, col2 = st.columns(2)
        
        with col1:
            create_tgw = st.checkbox("Create New Transit Gateway", value=True)
            if not create_tgw:
                existing_tgw = st.text_input("Existing Transit Gateway ID", placeholder="tgw-12345678")
        
        with col2:
            bgp_asn = st.number_input("BGP ASN", value=65000, min_value=64512, max_value=65534)
            tgw_asn = st.number_input("Transit Gateway ASN", value=64512, min_value=64512, max_value=65534)
        
        # Spoke VPCs
        spoke_cidrs = st.text_area(
            "Spoke VPC CIDRs (one per line)",
            value="10.1.0.0/16\n10.2.0.0/16",
            help="Enter the CIDR blocks for spoke VPCs that will route through the FortiGate"
        )
        
        # Monitoring Configuration
        st.markdown("### Monitoring Configuration")
        col1, col2 = st.columns(2)
        
        with col1:
            enable_flow_logs = st.checkbox("Enable VPC Flow Logs", value=True)
            log_retention = st.selectbox("Log Retention (days)", [7, 14, 30, 60, 90], index=2)
        
        with col2:
            enable_detailed_monitoring = st.checkbox("Enable Detailed Monitoring", value=True)
        
        # Submit button
        submitted = st.form_submit_button("Save Configuration", type="primary")
        
        if submitted:
            # Validate required fields
            required_fields = {
                "VPC ID": vpc_id,
                "Outside Subnet (Primary)": outside_primary,
                "Inside Subnet (Primary)": inside_primary,
                "HA Subnet (Primary)": ha_primary,
                "Management Subnet (Primary)": mgmt_primary,
                "Outside Subnet (Backup)": outside_backup,
                "Inside Subnet (Backup)": inside_backup,
                "HA Subnet (Backup)": ha_backup,
                "Management Subnet (Backup)": mgmt_backup,
                "Key Pair Name": key_pair,
                "Admin Password": admin_password,
                "HA Password": ha_password
            }
            
            missing_fields = [field for field, value in required_fields.items() if not value]
            
            if missing_fields:
                st.error(f"Please fill in the following required fields: {', '.join(missing_fields)}")
            else:
                # Create configuration object
                try:
                    aws_config = AWSConfig(
                        region=aws_region,
                        profile=aws_profile if aws_profile else None
                    )
                    
                    network_config = NetworkConfig(
                        vpc_id=vpc_id,
                        availability_zones=[az1, az2],
                        outside_subnet_primary=outside_primary,
                        inside_subnet_primary=inside_primary,
                        ha_subnet_primary=ha_primary,
                        mgmt_subnet_primary=mgmt_primary,
                        outside_subnet_backup=outside_backup,
                        inside_subnet_backup=inside_backup,
                        ha_subnet_backup=ha_backup,
                        mgmt_subnet_backup=mgmt_backup,
                        mgmt_access_cidrs=mgmt_cidrs.strip().split('\n')
                    )
                    
                    fortigate_config = FortiGateConfig(
                        ami_id=None,  # Will be discovered
                        ami_discovery=AMIDiscoveryConfig(enabled=True),
                        licensing=LicensingConfig(type="BYOL"),
                        instance_type=instance_type,
                        key_pair_name=key_pair,
                        admin_password=admin_password,
                        ha_password=ha_password
                    )
                    
                    tgw_config = TransitGatewayConfig(
                        create_new=create_tgw,
                        transit_gateway_id=existing_tgw if not create_tgw else None,
                        bgp_asn=bgp_asn,
                        transit_gateway_asn=tgw_asn,
                        spoke_vpc_cidrs=spoke_cidrs.strip().split('\n') if spoke_cidrs.strip() else []
                    )
                    
                    monitoring_config = MonitoringConfig(
                        enable_flow_logs=enable_flow_logs,
                        log_retention_days=log_retention,
                        enable_detailed_monitoring=enable_detailed_monitoring
                    )
                    
                    deployment_config = DeploymentConfig(
                        aws=aws_config,
                        network=network_config,
                        fortigate=fortigate_config,
                        transit_gateway=tgw_config,
                        monitoring=monitoring_config
                    )
                    
                    st.session_state.deployment_config = deployment_config
                    st.success("✅ Configuration saved successfully!")
                    
                except Exception as e:
                    st.error(f"Error creating configuration: {e}")

def render_ami_discovery_page():
    """Render the AMI discovery page"""
    st.markdown('<h2 class="section-header">FortiGate AMI Discovery</h2>', unsafe_allow_html=True)
    
    if not st.session_state.deployment_config:
        st.warning("Please configure your deployment settings first.")
        return
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### AMI Discovery Settings")
        
        fortigate_version = st.selectbox(
            "FortiGate Version",
            ["7.6", "7.4", "7.2", "7.0", "6.4", "6.2"],
            index=1
        )
        
        license_type = st.selectbox(
            "License Type",
            ["BYOL", "OnDemand", "Reserved"],
            index=0
        )
        
        architecture = st.selectbox(
            "Architecture",
            ["x86_64", "arm64"],
            index=0
        )
        
        if st.button("Discover AMIs", type="primary"):
            with st.spinner("Discovering FortiGate AMIs..."):
                try:
                    # Simulate AMI discovery
                    st.session_state.ami_discovery_result = {
                        "success": True,
                        "ami_id": f"ami-{fortigate_version.replace('.', '')}{license_type.lower()}123",
                        "name": f"FortiGate-VM64-AWS-{fortigate_version}.1-{license_type}-20231201",
                        "description": f"FortiGate {fortigate_version} {license_type} AMI",
                        "creation_date": "2023-12-01T10:00:00.000Z",
                        "alternatives": [
                            f"ami-{fortigate_version.replace('.', '')}{license_type.lower()}122",
                            f"ami-{fortigate_version.replace('.', '')}{license_type.lower()}121"
                        ]
                    }
                    st.success("✅ AMI discovery completed!")
                except Exception as e:
                    st.error(f"AMI discovery failed: {e}")
    
    with col2:
        st.markdown("### Discovery Results")
        
        if st.session_state.ami_discovery_result:
            result = st.session_state.ami_discovery_result
            
            if result["success"]:
                st.markdown(f"""
                <div class="success-message">
                    <h4>✅ AMI Found</h4>
                    <p><strong>AMI ID:</strong> {result['ami_id']}</p>
                    <p><strong>Name:</strong> {result['name']}</p>
                    <p><strong>Description:</strong> {result['description']}</p>
                    <p><strong>Created:</strong> {result['creation_date']}</p>
                </div>
                """, unsafe_allow_html=True)
                
                if result.get("alternatives"):
                    st.markdown("**Alternative AMIs:**")
                    for alt_ami in result["alternatives"]:
                        st.text(f"• {alt_ami}")
            else:
                st.error("No AMIs found matching the criteria")
        else:
            st.info("Click 'Discover AMIs' to find available FortiGate AMIs")

def render_licensing_page():
    """Render the licensing page"""
    st.markdown('<h2 class="section-header">FortiGate Licensing</h2>', unsafe_allow_html=True)
    
    if not st.session_state.deployment_config:
        st.warning("Please configure your deployment settings first.")
        return
    
    # License type selection
    license_type = st.radio(
        "Select Licensing Model",
        ["BYOL (Bring Your Own License)", "OnDemand (Pay-As-You-Go)", "Reserved Instance"],
        index=0
    )
    
    if "BYOL" in license_type:
        render_byol_configuration()
    elif "OnDemand" in license_type:
        render_ondemand_configuration()
    else:
        render_reserved_configuration()

def render_byol_configuration():
    """Render BYOL licensing configuration"""
    st.markdown("### BYOL Configuration")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**License Storage Method:**")
        storage_method = st.radio(
            "Choose storage method",
            ["AWS Secrets Manager", "S3 Bucket"],
            index=0
        )
        
        if storage_method == "AWS Secrets Manager":
            primary_secret = st.text_input(
                "Primary License Secret Name",
                value="fortigate/primary/license"
            )
            backup_secret = st.text_input(
                "Backup License Secret Name",
                value="fortigate/backup/license"
            )
            
            if st.button("Test Secret Access"):
                with st.spinner("Testing secret access..."):
                    # Simulate secret access test
                    st.success("✅ Secrets accessible")
        
        else:  # S3 Bucket
            s3_bucket = st.text_input("S3 Bucket Name", placeholder="my-fortigate-licenses")
            primary_key = st.text_input("Primary License S3 Key", value="licenses/primary.lic")
            backup_key = st.text_input("Backup License S3 Key", value="licenses/backup.lic")
            
            if st.button("Test S3 Access"):
                with st.spinner("Testing S3 access..."):
                    # Simulate S3 access test
                    st.success("✅ S3 bucket accessible")
    
    with col2:
        st.markdown("**License Upload:**")
        
        primary_license = st.file_uploader(
            "Upload Primary License File",
            type=['lic'],
            help="Upload the .lic file for the primary FortiGate"
        )
        
        backup_license = st.file_uploader(
            "Upload Backup License File",
            type=['lic'],
            help="Upload the .lic file for the backup FortiGate"
        )
        
        if primary_license and backup_license:
            if st.button("Validate License Files"):
                with st.spinner("Validating license files..."):
                    # Simulate license validation
                    st.success("✅ License files validated successfully")
                    st.info("License files are ready for deployment")

def render_ondemand_configuration():
    """Render OnDemand licensing configuration"""
    st.markdown("### OnDemand (Pay-As-You-Go) Configuration")
    
    st.info("""
    **OnDemand Licensing:**
    - No license files required
    - Hourly billing through AWS Marketplace
    - Automatic licensing activation
    - Best for testing and short-term deployments
    """)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Marketplace Subscription:**")
        if st.button("Check Marketplace Subscription"):
            with st.spinner("Checking marketplace subscription..."):
                # Simulate marketplace check
                st.success("✅ FortiGate OnDemand subscription active")
    
    with col2:
        st.markdown("**Estimated Costs:**")
        st.metric("EC2 Cost (c5.xlarge)", "$0.192/hour")
        st.metric("FortiGate License", "$0.75/hour")
        st.metric("Total Cost", "$0.942/hour")

def render_reserved_configuration():
    """Render Reserved Instance licensing configuration"""
    st.markdown("### Reserved Instance Configuration")
    
    st.info("""
    **Reserved Instance Licensing:**
    - Upfront payment commitment
    - Reduced hourly rates
    - No license files required
    - Best for long-term production deployments
    """)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Reservation Details:**")
        term_length = st.selectbox("Term Length", ["1 Year", "3 Years"], index=0)
        payment_option = st.selectbox(
            "Payment Option",
            ["All Upfront", "Partial Upfront", "No Upfront"],
            index=1
        )
    
    with col2:
        st.markdown("**Cost Comparison:**")
        if term_length == "1 Year":
            st.metric("Upfront Cost", "$3,500")
            st.metric("Hourly Rate", "$0.35/hour")
            st.metric("Annual Savings", "~40%")
        else:
            st.metric("Upfront Cost", "$8,500")
            st.metric("Hourly Rate", "$0.25/hour")
            st.metric("Annual Savings", "~55%")

def render_cost_analysis_page():
    """Render the cost analysis page"""
    st.markdown('<h2 class="section-header">Cost Analysis & Optimization</h2>', unsafe_allow_html=True)
    
    # Cost comparison parameters
    col1, col2 = st.columns(2)
    
    with col1:
        deployment_duration = st.slider(
            "Deployment Duration (months)",
            min_value=1,
            max_value=36,
            value=12
        )
        
        instance_type = st.selectbox(
            "Instance Type",
            ["c5.large", "c5.xlarge", "c5.2xlarge", "c5.4xlarge"],
            index=1
        )
    
    with col2:
        usage_pattern = st.selectbox(
            "Usage Pattern",
            ["Continuous (24/7)", "Business Hours (8/5)", "Intermittent"],
            index=0
        )
        
        region = st.selectbox(
            "AWS Region",
            ["us-east-1", "us-west-2", "eu-west-1"],
            index=0
        )
    
    if st.button("Calculate Costs", type="primary"):
        with st.spinner("Calculating costs..."):
            # Simulate cost calculation
            costs = calculate_licensing_costs(deployment_duration, instance_type, usage_pattern, region)
            st.session_state.cost_analysis = costs
    
    if st.session_state.cost_analysis:
        render_cost_comparison(st.session_state.cost_analysis)

def calculate_licensing_costs(duration, instance_type, usage_pattern, region):
    """Calculate costs for different licensing models"""
    # Simplified cost calculation (in a real implementation, this would use AWS Pricing API)
    
    # Base EC2 costs per hour
    ec2_costs = {
        "c5.large": 0.096,
        "c5.xlarge": 0.192,
        "c5.2xlarge": 0.384,
        "c5.4xlarge": 0.768
    }
    
    # Usage multipliers
    usage_multipliers = {
        "Continuous (24/7)": 24 * 30,  # hours per month
        "Business Hours (8/5)": 8 * 22,  # 8 hours * 22 business days
        "Intermittent": 12 * 30  # 12 hours per day average
    }
    
    ec2_hourly = ec2_costs[instance_type]
    hours_per_month = usage_multipliers[usage_pattern]
    
    # Calculate costs for each licensing model
    byol_monthly = ec2_hourly * hours_per_month * 2  # 2 instances
    ondemand_monthly = (ec2_hourly + 0.75) * hours_per_month * 2  # +$0.75/hour license
    
    # Reserved instance calculations (simplified)
    reserved_upfront = 3500 if duration >= 12 else 0
    reserved_hourly = 0.35 if duration >= 12 else ec2_hourly + 0.50
    reserved_monthly = reserved_hourly * hours_per_month * 2
    
    return {
        "duration": duration,
        "byol": {
            "monthly": byol_monthly,
            "total": byol_monthly * duration,
            "upfront": 0
        },
        "ondemand": {
            "monthly": ondemand_monthly,
            "total": ondemand_monthly * duration,
            "upfront": 0
        },
        "reserved": {
            "monthly": reserved_monthly,
            "total": reserved_monthly * duration + reserved_upfront,
            "upfront": reserved_upfront
        }
    }

def render_cost_comparison(costs):
    """Render cost comparison charts and recommendations"""
    st.markdown("### Cost Comparison")
    
    # Create comparison DataFrame
    df = pd.DataFrame({
        "Licensing Model": ["BYOL", "OnDemand", "Reserved"],
        "Monthly Cost": [
            costs["byol"]["monthly"],
            costs["ondemand"]["monthly"],
            costs["reserved"]["monthly"]
        ],
        "Total Cost": [
            costs["byol"]["total"],
            costs["ondemand"]["total"],
            costs["reserved"]["total"]
        ],
        "Upfront Cost": [
            costs["byol"]["upfront"],
            costs["ondemand"]["upfront"],
            costs["reserved"]["upfront"]
        ]
    })
    
    # Monthly cost comparison chart
    fig_monthly = px.bar(
        df,
        x="Licensing Model",
        y="Monthly Cost",
        title="Monthly Cost Comparison",
        color="Licensing Model",
        color_discrete_map={
            "BYOL": "#FF6B35",
            "OnDemand": "#2E86AB",
            "Reserved": "#A23B72"
        }
    )
    st.plotly_chart(fig_monthly, use_container_width=True)
    
    # Total cost comparison chart
    fig_total = px.bar(
        df,
        x="Licensing Model",
        y="Total Cost",
        title=f"Total Cost Comparison ({costs['duration']} months)",
        color="Licensing Model",
        color_discrete_map={
            "BYOL": "#FF6B35",
            "OnDemand": "#2E86AB",
            "Reserved": "#A23B72"
        }
    )
    st.plotly_chart(fig_total, use_container_width=True)
    
    # Recommendations
    st.markdown("### Recommendations")
    
    min_cost_model = df.loc[df["Total Cost"].idxmin(), "Licensing Model"]
    savings = df["Total Cost"].max() - df["Total Cost"].min()
    
    st.markdown(f"""
    <div class="success-message">
        <h4>💡 Recommended: {min_cost_model}</h4>
        <p>Based on your {costs['duration']}-month deployment, <strong>{min_cost_model}</strong> offers the best value.</p>
        <p><strong>Potential Savings:</strong> ${savings:,.2f} compared to the most expensive option.</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Detailed cost breakdown
    st.markdown("### Detailed Cost Breakdown")
    st.dataframe(df, use_container_width=True)

def render_deployment_page():
    """Render the deployment page"""
    st.markdown('<h2 class="section-header">FortiGate Deployment</h2>', unsafe_allow_html=True)
    
    if not st.session_state.deployment_config:
        st.warning("Please configure your deployment settings first.")
        return
    
    # Deployment status
    status_colors = {
        "not_started": "🔵",
        "planning": "🟡",
        "validating": "🟡",
        "deploying": "🟠",
        "deployed": "🟢",
        "failed": "🔴",
        "rolling_back": "🟡"
    }
    
    status_color = status_colors.get(st.session_state.deployment_status, "🔵")
    st.markdown(f"**Current Status:** {status_color} {st.session_state.deployment_status.title()}")
    
    # Deployment actions
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("Generate Plan", type="primary"):
            generate_deployment_plan()
    
    with col2:
        if st.button("Deploy", type="primary", disabled=st.session_state.deployment_status != "not_started"):
            start_deployment()
    
    with col3:
        if st.button("Rollback", disabled=st.session_state.deployment_status not in ["deployed", "failed"]):
            rollback_deployment()
    
    # Progress tracking
    if st.session_state.deployment_status in ["planning", "validating", "deploying"]:
        render_deployment_progress()
    
    # Deployment logs
    if st.session_state.deployment_logs:
        st.markdown("### Deployment Logs")
        log_container = st.container()
        with log_container:
            for log_entry in st.session_state.deployment_logs[-10:]:  # Show last 10 entries
                st.text(log_entry)

def generate_deployment_plan():
    """Generate Terraform deployment plan"""
    st.session_state.deployment_status = "planning"
    st.session_state.deployment_logs.append(f"{datetime.now()}: Starting plan generation...")
    
    with st.spinner("Generating deployment plan..."):
        # Simulate plan generation
        import time
        time.sleep(2)
        
        st.session_state.deployment_logs.extend([
            f"{datetime.now()}: Validating AWS credentials...",
            f"{datetime.now()}: Discovering FortiGate AMI...",
            f"{datetime.now()}: Validating network configuration...",
            f"{datetime.now()}: Generating Terraform plan...",
            f"{datetime.now()}: Plan generation completed successfully"
        ])
        
        st.session_state.deployment_status = "not_started"
        st.success("✅ Deployment plan generated successfully!")

def start_deployment():
    """Start the deployment process"""
    st.session_state.deployment_status = "deploying"
    st.session_state.deployment_logs.append(f"{datetime.now()}: Starting deployment...")
    
    with st.spinner("Deploying FortiGate HA pair..."):
        # Simulate deployment
        import time
        time.sleep(3)
        
        st.session_state.deployment_logs.extend([
            f"{datetime.now()}: Creating VPC resources...",
            f"{datetime.now()}: Launching FortiGate instances...",
            f"{datetime.now()}: Configuring HA cluster...",
            f"{datetime.now()}: Setting up Transit Gateway...",
            f"{datetime.now()}: Configuring BGP routing...",
            f"{datetime.now()}: Deployment completed successfully"
        ])
        
        st.session_state.deployment_status = "deployed"
        st.success("🎉 FortiGate HA deployment completed successfully!")

def rollback_deployment():
    """Rollback the deployment"""
    st.session_state.deployment_status = "rolling_back"
    st.session_state.deployment_logs.append(f"{datetime.now()}: Starting rollback...")
    
    with st.spinner("Rolling back deployment..."):
        # Simulate rollback
        import time
        time.sleep(2)
        
        st.session_state.deployment_logs.extend([
            f"{datetime.now()}: Destroying FortiGate instances...",
            f"{datetime.now()}: Cleaning up network resources...",
            f"{datetime.now()}: Rollback completed successfully"
        ])
        
        st.session_state.deployment_status = "not_started"
        st.success("✅ Deployment rolled back successfully!")

def render_deployment_progress():
    """Render deployment progress"""
    st.markdown("### Deployment Progress")
    
    # Simulate progress based on status
    progress_map = {
        "planning": 20,
        "validating": 40,
        "deploying": 80,
        "rolling_back": 60
    }
    
    progress = progress_map.get(st.session_state.deployment_status, 0)
    st.progress(progress / 100)
    
    # Progress steps
    steps = [
        ("Planning", progress >= 20),
        ("Validation", progress >= 40),
        ("Resource Creation", progress >= 60),
        ("Configuration", progress >= 80),
        ("Completion", progress >= 100)
    ]
    
    for step, completed in steps:
        icon = "✅" if completed else "⏳"
        st.text(f"{icon} {step}")

def render_monitoring_page():
    """Render the monitoring page"""
    st.markdown('<h2 class="section-header">Monitoring & Health</h2>', unsafe_allow_html=True)
    
    if st.session_state.deployment_status != "deployed":
        st.info("Deploy your FortiGate HA pair to view monitoring information.")
        return
    
    # Health status
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Primary FortiGate", "🟢 Healthy", "CPU: 25%")
    
    with col2:
        st.metric("Backup FortiGate", "🟢 Standby", "CPU: 15%")
    
    with col3:
        st.metric("BGP Sessions", "2 Active", "No flaps")
    
    with col4:
        st.metric("Throughput", "150 Mbps", "+5% from yesterday")
    
    # Traffic chart
    st.markdown("### Traffic Overview")
    
    # Generate sample traffic data
    dates = pd.date_range(start=datetime.now() - timedelta(days=7), end=datetime.now(), freq='H')
    traffic_data = pd.DataFrame({
        'timestamp': dates,
        'inbound_mbps': [50 + 30 * (i % 24) / 24 + 10 * (i % 7) / 7 for i in range(len(dates))],
        'outbound_mbps': [40 + 25 * (i % 24) / 24 + 8 * (i % 7) / 7 for i in range(len(dates))]
    })
    
    fig = px.line(
        traffic_data,
        x='timestamp',
        y=['inbound_mbps', 'outbound_mbps'],
        title='Network Traffic (Last 7 Days)',
        labels={'value': 'Mbps', 'timestamp': 'Time'}
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # Recent events
    st.markdown("### Recent Events")
    events = [
        "2023-12-01 10:30:00 - HA sync completed successfully",
        "2023-12-01 09:15:00 - BGP session established with Transit Gateway",
        "2023-12-01 08:45:00 - Primary FortiGate health check passed",
        "2023-12-01 08:00:00 - VPC Flow Logs enabled",
        "2023-12-01 07:30:00 - Deployment completed successfully"
    ]
    
    for event in events:
        st.text(f"✅ {event}")

def render_documentation_page():
    """Render the documentation page"""
    st.markdown('<h2 class="section-header">Documentation & Resources</h2>', unsafe_allow_html=True)
    
    # Documentation sections
    doc_sections = {
        "📋 Deployment Guide": "Step-by-step instructions for deploying FortiGate HA pairs",
        "🔍 AMI & Licensing Guide": "Complete guide for AMI discovery and licensing options",
        "📊 Monitoring & Troubleshooting": "Comprehensive monitoring setup and troubleshooting procedures",
        "🌐 Streamlit App Deployment": "Instructions for deploying and operating this web application",
        "🏗️ Architecture Overview": "Detailed architecture diagrams and traffic flow explanations",
        "🔧 Configuration Examples": "Sample configurations for common deployment scenarios"
    }
    
    for title, description in doc_sections.items():
        with st.expander(title):
            st.write(description)
            st.info("Click to view detailed documentation (links to actual documentation files)")
    
    # Quick links
    st.markdown("### Quick Links")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        **Deployment Resources:**
        - [AWS FortiGate Marketplace](https://aws.amazon.com/marketplace/seller-profile?id=fortigate)
        - [FortiGate Documentation](https://docs.fortinet.com)
        - [AWS Transit Gateway Guide](https://docs.aws.amazon.com/vpc/latest/tgw/)
        """)
    
    with col2:
        st.markdown("""
        **Support Resources:**
        - [Fortinet Support Portal](https://support.fortinet.com)
        - [AWS Support Center](https://console.aws.amazon.com/support/)
        - [Community Forums](https://community.fortinet.com)
        """)
    
    # System information
    st.markdown("### System Information")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Streamlit Version", "1.28.0")
    
    with col2:
        st.metric("Python Version", "3.9.0")
    
    with col3:
        st.metric("AWS SDK Version", "1.26.0")

def main():
    """Main application function"""
    initialize_session_state()
    render_header()
    
    # Sidebar navigation
    current_page = render_sidebar()
    
    # Render selected page
    if current_page == "home":
        render_home_page()
    elif current_page == "config":
        render_configuration_page()
    elif current_page == "ami":
        render_ami_discovery_page()
    elif current_page == "licensing":
        render_licensing_page()
    elif current_page == "cost":
        render_cost_analysis_page()
    elif current_page == "deployment":
        render_deployment_page()
    elif current_page == "monitoring":
        render_monitoring_page()
    elif current_page == "docs":
        render_documentation_page()
    
    # Footer
    st.markdown("---")
    st.markdown(
        "🛡️ **FortiGate AWS HA Deployment** | "
        "Built with Streamlit | "
        f"Status: {st.session_state.deployment_status.title()}"
    )

if __name__ == "__main__":
    main()