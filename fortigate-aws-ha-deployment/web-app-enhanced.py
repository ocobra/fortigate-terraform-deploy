#!/usr/bin/env python3
"""
FortiGate AWS HA Deployment - Enhanced Streamlit Web Application

This web application provides complete parity with deploy.py CLI functionality including:
- All deployment parameters from DEPLOYMENT-PARAMETERS-GUIDE.md
- ENI configuration support
- EIP failover configuration
- Backend configuration (local/S3)
- Configuration file import/export
- Plan-only mode
- Destroy functionality
- Skip validation option
- Real-time deployment tracking
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
from dataclasses import asdict

# Add the deployment engine to the path
sys.path.append(str(Path(__file__).parent))

try:
    from deploy import (
        DeploymentEngine, DeploymentConfig, AWSConfig, NetworkConfig,
        FortiGateConfig, TransitGatewayConfig, MonitoringConfig, BackendConfig,
        AMIDiscovery, LicenseManager, AMIDiscoveryConfig, LicensingConfig,
        ConfigurationValidator, TerraformManager
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
    .info-box {
        background-color: #D1ECF1;
        color: #0C5460;
        padding: 1rem;
        border-radius: 0.5rem;
        border: 1px solid #BEE5EB;
    }
</style>
""", unsafe_allow_html=True)
