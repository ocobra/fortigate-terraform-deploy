#!/usr/bin/env python3
"""
FortiGate AWS HA Deployment - Enhanced Streamlit Web Application

This web application provides complete parity with deploy.py CLI functionality including:
- All 60+ deployment parameters from DEPLOYMENT-PARAMETERS-GUIDE.md
- ENI configuration support (8 ENI IDs)
- EIP failover configuration
- Backend configuration (local/S3)
- Configuration file import/export (YAML/JSON)
- Plan-only mode
- Destroy functionality
- Skip validation option
- Real-time deployment tracking
- AMI discovery integration
- Licensing configuration (BYOL, OnDemand, Reserved)
- Cost analysis and comparison
"""

import streamlit as st
import boto3
import json
import yaml
import re
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from pathlib import Path
import sys
import os
import time
from dataclasses import asdict
from typing import Optional, Dict, Any, List, Tuple, Callable
import subprocess

# Add the deployment engine to the path
sys.path.append(str(Path(__file__).parent))

# Import all required classes from deploy.py
try:
    from deploy import (
        # Configuration dataclasses
        DeploymentConfig, AWSConfig, NetworkConfig,
        FortiGateConfig, TransitGatewayConfig, MonitoringConfig, BackendConfig,
        AMIDiscoveryConfig, LicensingConfig,
        # Manager classes
        DeploymentEngine, AMIDiscovery, LicenseManager,
        ConfigurationValidator, TerraformManager
    )
    DEPLOYMENT_ENGINE_AVAILABLE = True
except ImportError as e:
    st.error(f"⚠️ Deployment engine not available: {e}")
    st.info("Please ensure deploy.py is in the same directory as this application.")
    DEPLOYMENT_ENGINE_AVAILABLE = False

# ============================================================================
# PAGE CONFIGURATION
# ============================================================================

st.set_page_config(
    page_title="FortiGate AWS HA Deployment",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'https://docs.fortinet.com/product/fortigate',
        'Report a bug': None,
        'About': "FortiGate AWS HA Deployment - Enhanced Web Application v2.0"
    }
)

# ============================================================================
# CUSTOM CSS STYLING
# ============================================================================

st.markdown("""
<style>
    /* Main headers */
    .main-header {
        font-size: 2.5rem;
        color: #FF6B35;
        text-align: center;
        margin-bottom: 2rem;
        font-weight: 600;
    }
    
    /* Section headers */
    .section-header {
        font-size: 1.5rem;
        color: #2E86AB;
        margin-top: 2rem;
        margin-bottom: 1rem;
        font-weight: 500;
    }
    
    /* Metric cards */
    .metric-card {
        background-color: #F8F9FA;
        padding: 1.5rem;
        border-radius: 0.5rem;
        border-left: 4px solid #FF6B35;
        margin-bottom: 1rem;
    }
    
    /* Success messages */
    .success-message {
        background-color: #D4EDDA;
        color: #155724;
        padding: 1rem;
        border-radius: 0.5rem;
        border: 1px solid #C3E6CB;
        margin: 1rem 0;
    }
    
    /* Warning messages */
    .warning-message {
        background-color: #FFF3CD;
        color: #856404;
        padding: 1rem;
        border-radius: 0.5rem;
        border: 1px solid #FFEAA7;
        margin: 1rem 0;
    }
    
    /* Error messages */
    .error-message {
        background-color: #F8D7DA;
        color: #721C24;
        padding: 1rem;
        border-radius: 0.5rem;
        border: 1px solid #F5C6CB;
        margin: 1rem 0;
    }
    
    /* Info boxes */
    .info-box {
        background-color: #D1ECF1;
        color: #0C5460;
        padding: 1rem;
        border-radius: 0.5rem;
        border: 1px solid #BEE5EB;
        margin: 1rem 0;
    }
    
    /* Required field indicator */
    .required-field {
        color: #DC3545;
        font-weight: bold;
    }
    
    /* Optional field indicator */
    .optional-field {
        color: #6C757D;
        font-style: italic;
    }
    
    /* Progress bar styling */
    .stProgress > div > div > div > div {
        background-color: #FF6B35;
    }
    
    /* Button styling */
    .stButton > button {
        border-radius: 0.5rem;
        font-weight: 500;
    }
</style>
""", unsafe_allow_html=True)


# ============================================================================
# SESSION STATE MANAGEMENT
# ============================================================================

def initialize_session_state() -> None:
    """
    Initialize all session state variables with default values.
    
    This function ensures consistent state across page navigation and provides
    a centralized location for all session state variable initialization. It
    follows the idempotent pattern - safe to call multiple times.
    
    State Variables:
        deployment_config (Optional[DeploymentConfig]): Complete deployment configuration
            object containing all parameters for FortiGate HA deployment. None until
            user configures or imports a configuration.
        
        deployment_status (str): Current deployment status. Valid values:
            - 'not_started': No deployment initiated
            - 'planning': Generating Terraform plan
            - 'validating': Validating AWS resources and configuration
            - 'deploying': Executing Terraform apply
            - 'deployed': Deployment completed successfully
            - 'failed': Deployment failed with errors
            - 'destroying': Executing Terraform destroy
        
        deployment_logs (List[str]): Chronological list of deployment log messages
            for display in the UI. Includes Terraform output, validation messages,
            and status updates.
        
        aws_session (Optional[boto3.Session]): Authenticated AWS session for API
            calls. None until AWS credentials are provided and validated.
        
        validation_results (Dict[str, bool]): Cache of AWS resource validation
            results to avoid repeated API calls. Keys are resource identifiers
            (e.g., 'vpc_id', 'subnet_1'), values are validation status.
        
        ami_discovery_result (Optional[Dict]): Results from AMI discovery operation.
            Contains discovered AMI details including ID, name, description, and
            creation date. None until discovery is performed.
        
        cost_analysis (Optional[Dict]): Cost analysis results comparing licensing
            models (BYOL, OnDemand, Reserved). Contains monthly costs, total costs,
            and recommendations. None until analysis is performed.
        
        terraform_output (str): Accumulated Terraform command output for display
            in the log viewer. Updated in real-time during Terraform operations.
        
        skip_validation (bool): Flag to skip AWS resource validation. Useful for
            limited-permission scenarios where validation API calls may fail but
            deployment should still proceed.
        
        current_page (str): Currently active page in the application. Used for
            navigation state management.
    
    Requirements:
        - Requirement 12.1: Store configuration parameters in session state
        - Requirement 12.2: Preserve configuration across page navigation
    
    Example:
        >>> initialize_session_state()
        >>> st.session_state.deployment_status
        'not_started'
        >>> st.session_state.deployment_logs
        []
    """
    # Deployment configuration - complete configuration object
    if 'deployment_config' not in st.session_state:
        st.session_state.deployment_config = None
    
    # Deployment status tracking - current state of deployment workflow
    if 'deployment_status' not in st.session_state:
        st.session_state.deployment_status = 'not_started'
    
    # Deployment logs - chronological list of log messages
    if 'deployment_logs' not in st.session_state:
        st.session_state.deployment_logs = []
    
    # AWS session - authenticated boto3 session for API calls
    if 'aws_session' not in st.session_state:
        st.session_state.aws_session = None
    
    # Validation results cache - avoid repeated API calls
    if 'validation_results' not in st.session_state:
        st.session_state.validation_results = {}
    
    # AMI discovery results - discovered FortiGate AMIs
    if 'ami_discovery_result' not in st.session_state:
        st.session_state.ami_discovery_result = None
    
    # Cost analysis results - licensing model cost comparison
    if 'cost_analysis' not in st.session_state:
        st.session_state.cost_analysis = None
    
    # Terraform output - accumulated command output for display
    if 'terraform_output' not in st.session_state:
        st.session_state.terraform_output = ""
    
    # Skip validation flag - bypass AWS resource validation
    if 'skip_validation' not in st.session_state:
        st.session_state.skip_validation = False
    
    # Current page - active page for navigation state
    if 'current_page' not in st.session_state:
        st.session_state.current_page = 'home'


def get_config() -> Optional[DeploymentConfig]:
    """
    Retrieve current deployment configuration from session state.
    
    This function provides safe access to the deployment configuration stored
    in session state. It ensures session state is initialized before access
    and returns None if no configuration has been set.
    
    Returns:
        Optional[DeploymentConfig]: The current deployment configuration object,
            or None if no configuration has been loaded or created.
    
    Requirements:
        - Requirement 12.1: Store configuration parameters in session state
        - Requirement 12.3: Display previously entered values when returning to page
    
    Example:
        >>> config = get_config()
        >>> if config:
        ...     print(f"Region: {config.aws_config.region}")
        ... else:
        ...     print("No configuration loaded")
    """
    initialize_session_state()
    return st.session_state.deployment_config


def set_config(config: DeploymentConfig) -> None:
    """
    Store deployment configuration in session state.
    
    This function safely stores a deployment configuration object in session
    state, making it available across page navigation and subsequent operations.
    It ensures session state is initialized before storing the configuration.
    
    Args:
        config (DeploymentConfig): Complete deployment configuration object
            containing all parameters for FortiGate HA deployment.
    
    Requirements:
        - Requirement 12.1: Store configuration parameters in session state
        - Requirement 12.2: Preserve configuration across page navigation
        - Requirement 12.4: Update session state when importing configuration
    
    Example:
        >>> from deploy import DeploymentConfig, AWSConfig
        >>> aws_config = AWSConfig(region="us-east-1", profile="default")
        >>> config = DeploymentConfig(aws_config=aws_config, ...)
        >>> set_config(config)
    """
    initialize_session_state()
    st.session_state.deployment_config = config


def get_deployment_status() -> str:
    """
    Get current deployment status from session state.
    
    This function provides safe access to the deployment status, which tracks
    the current state of the deployment workflow. The status is used to control
    UI elements and workflow progression.
    
    Returns:
        str: Current deployment status. Valid values:
            - 'not_started': No deployment initiated
            - 'planning': Generating Terraform plan
            - 'validating': Validating AWS resources and configuration
            - 'deploying': Executing Terraform apply
            - 'deployed': Deployment completed successfully
            - 'failed': Deployment failed with errors
            - 'destroying': Executing Terraform destroy
    
    Requirements:
        - Requirement 12.6: Preserve deployment status in session state
        - Requirement 10.3: Display current operation name during deployment
    
    Example:
        >>> status = get_deployment_status()
        >>> if status == 'deployed':
        ...     print("Deployment is complete")
        >>> elif status == 'deploying':
        ...     print("Deployment in progress")
    """
    initialize_session_state()
    return st.session_state.deployment_status


def set_deployment_status(status: str) -> None:
    """
    Update deployment status in session state.
    
    This function safely updates the deployment status, which controls the
    deployment workflow state machine. It validates that the status is one
    of the allowed values before updating.
    
    Args:
        status (str): New deployment status. Must be one of:
            - 'not_started': No deployment initiated
            - 'planning': Generating Terraform plan
            - 'validating': Validating AWS resources and configuration
            - 'deploying': Executing Terraform apply
            - 'deployed': Deployment completed successfully
            - 'failed': Deployment failed with errors
            - 'destroying': Executing Terraform destroy
    
    Raises:
        ValueError: If status is not one of the valid values.
    
    Requirements:
        - Requirement 12.6: Preserve deployment status in session state
        - Requirement 10.3: Display current operation name during deployment
    
    Example:
        >>> set_deployment_status('deploying')
        >>> set_deployment_status('deployed')
    """
    valid_statuses = {
        'not_started', 'planning', 'validating', 
        'deploying', 'deployed', 'failed', 'destroying'
    }
    
    if status not in valid_statuses:
        raise ValueError(
            f"Invalid deployment status: {status}. "
            f"Must be one of: {', '.join(sorted(valid_statuses))}"
        )
    
    initialize_session_state()
    st.session_state.deployment_status = status


def get_deployment_logs() -> List[str]:
    """
    Retrieve deployment log entries from session state.
    
    This function provides safe access to the deployment logs, which contain
    chronological messages about deployment progress, Terraform output, and
    validation results. The logs are displayed in the UI for user visibility.
    
    Returns:
        List[str]: List of deployment log messages in chronological order.
            Returns empty list if no logs have been added.
    
    Requirements:
        - Requirement 12.7: Preserve deployment results in session state
        - Requirement 10.4: Stream Terraform logs in real-time
    
    Example:
        >>> logs = get_deployment_logs()
        >>> for log in logs:
        ...     print(log)
    """
    initialize_session_state()
    return st.session_state.deployment_logs


def add_deployment_log(message: str) -> None:
    """
    Add a log entry to deployment logs in session state.
    
    This function appends a new log message to the deployment logs with a
    timestamp. The logs are used for real-time display during deployment
    operations and for troubleshooting after completion.
    
    Args:
        message (str): Log message to add. Should be a single line of text
            describing a deployment event, status update, or output.
    
    Requirements:
        - Requirement 12.7: Preserve deployment results in session state
        - Requirement 10.4: Stream Terraform logs in real-time
        - Requirement 10.10: Provide log download button for troubleshooting
    
    Example:
        >>> add_deployment_log("Starting Terraform initialization...")
        >>> add_deployment_log("Terraform init completed successfully")
        >>> add_deployment_log("ERROR: VPC not found")
    """
    initialize_session_state()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {message}"
    st.session_state.deployment_logs.append(log_entry)


def clear_deployment_logs() -> None:
    """
    Clear all deployment log entries from session state.
    
    This function removes all log entries from the deployment logs. It should
    be called at the start of a new deployment operation to ensure logs from
    previous operations don't interfere with current operation tracking.
    
    Requirements:
        - Requirement 12.7: Preserve deployment results in session state
        - Requirement 10.4: Stream Terraform logs in real-time
    
    Example:
        >>> clear_deployment_logs()
        >>> add_deployment_log("Starting new deployment...")
        >>> logs = get_deployment_logs()
        >>> len(logs)
        1
    """
    initialize_session_state()
    st.session_state.deployment_logs = []


# ============================================================================
# CONFIGURATION MANAGER
# ============================================================================

class ConfigurationManager:
    """
    Manages configuration import, export, and serialization for deployment configurations.
    
    This class handles conversion between DeploymentConfig objects and YAML/JSON formats,
    supporting configuration persistence and sharing. It properly handles nested dataclass
    structures and provides error handling for invalid configuration files.
    
    Requirements:
        - Requirement 2.1: Parse YAML configuration files
        - Requirement 2.3: Generate YAML configuration files
        - Requirement 2.5: Redact sensitive data when exporting
        - Requirement 2.6: Validate configuration files
        - Requirement 2.7: Preserve all parameter values during round-trip
    """
    
    def import_yaml(self, yaml_content: str) -> DeploymentConfig:
        """
        Parse YAML configuration file and create DeploymentConfig object.
        
        This method parses YAML content and reconstructs the complete DeploymentConfig
        object with all nested dataclasses. It handles the conversion from dictionary
        format to the proper dataclass instances.
        
        Args:
            yaml_content: String containing YAML configuration data
            
        Returns:
            DeploymentConfig: Fully populated configuration object
            
        Raises:
            yaml.YAMLError: If YAML syntax is invalid
            KeyError: If required configuration fields are missing
            TypeError: If configuration values have incorrect types
            ValueError: If configuration values are invalid
            
        Requirements:
            - Requirement 2.1: Parse YAML and load all parameters
            - Requirement 2.7: Preserve all parameter values during import
            
        Example:
            >>> manager = ConfigurationManager()
            >>> yaml_str = '''
            ... aws:
            ...   region: us-east-1
            ...   profile: default
            ... '''
            >>> config = manager.import_yaml(yaml_str)
            >>> config.aws.region
            'us-east-1'
        """
        try:
            # Parse YAML content
            config_dict = yaml.safe_load(yaml_content)
            
            if not isinstance(config_dict, dict):
                raise ValueError("YAML content must be a dictionary")
            
            # Reconstruct nested dataclass objects
            aws_config = AWSConfig(**config_dict.get('aws', {}))
            
            network_dict = config_dict.get('network', {})
            network_config = NetworkConfig(**network_dict)
            
            fortigate_dict = config_dict.get('fortigate', {})
            # Handle nested AMIDiscoveryConfig
            ami_discovery_dict = fortigate_dict.get('ami_discovery', {})
            ami_discovery = AMIDiscoveryConfig(**ami_discovery_dict)
            
            # Handle nested LicensingConfig
            licensing_dict = fortigate_dict.get('licensing', {})
            licensing = LicensingConfig(**licensing_dict)
            
            # Create FortiGateConfig with nested objects
            fortigate_config = FortiGateConfig(
                ami_id=fortigate_dict.get('ami_id'),
                ami_discovery=ami_discovery,
                licensing=licensing,
                instance_type=fortigate_dict.get('instance_type'),
                key_pair_name=fortigate_dict.get('key_pair_name'),
                admin_password=fortigate_dict.get('admin_password'),
                ha_password=fortigate_dict.get('ha_password'),
                hostname_primary=fortigate_dict.get('hostname_primary', 'fortigate-primary'),
                hostname_backup=fortigate_dict.get('hostname_backup', 'fortigate-backup')
            )
            
            transit_gateway_dict = config_dict.get('transit_gateway', {})
            transit_gateway_config = TransitGatewayConfig(**transit_gateway_dict)
            
            monitoring_dict = config_dict.get('monitoring', {})
            monitoring_config = MonitoringConfig(**monitoring_dict)
            
            backend_dict = config_dict.get('backend', {})
            backend_config = BackendConfig(**backend_dict)
            
            # Create complete DeploymentConfig
            deployment_config = DeploymentConfig(
                aws=aws_config,
                network=network_config,
                fortigate=fortigate_config,
                transit_gateway=transit_gateway_config,
                monitoring=monitoring_config,
                backend=backend_config,
                environment=config_dict.get('environment', 'prod'),
                owner_tag=config_dict.get('owner_tag', 'NetworkTeam')
            )
            
            return deployment_config
            
        except yaml.YAMLError as e:
            raise yaml.YAMLError(f"Invalid YAML syntax: {str(e)}")
        except KeyError as e:
            raise KeyError(f"Missing required configuration field: {str(e)}")
        except TypeError as e:
            raise TypeError(f"Invalid configuration value type: {str(e)}")
        except Exception as e:
            raise ValueError(f"Failed to parse configuration: {str(e)}")
    
    def export_yaml(self, config: DeploymentConfig, redact_sensitive: bool = True) -> str:
        """
        Serialize DeploymentConfig object to YAML format.
        
        This method converts a DeploymentConfig object to YAML string format,
        properly handling nested dataclass structures. Optionally redacts sensitive
        data like passwords and access keys.
        
        Args:
            config: DeploymentConfig object to serialize
            redact_sensitive: If True, replace sensitive values with '[REDACTED]'
            
        Returns:
            str: YAML-formatted configuration string
            
        Requirements:
            - Requirement 2.3: Generate YAML file with current parameters
            - Requirement 2.5: Redact sensitive data when exporting
            - Requirement 2.7: Preserve all parameter values during export
            
        Example:
            >>> manager = ConfigurationManager()
            >>> config = DeploymentConfig(...)
            >>> yaml_str = manager.export_yaml(config, redact_sensitive=True)
            >>> 'admin_password: [REDACTED]' in yaml_str
            True
        """
        try:
            # Convert dataclass to dictionary
            config_dict = asdict(config)
            
            # Redact sensitive data if requested
            if redact_sensitive:
                config_dict = self._redact_sensitive_data(config_dict)
            
            # Convert to YAML with proper formatting
            yaml_content = yaml.dump(
                config_dict,
                default_flow_style=False,
                sort_keys=False,
                allow_unicode=True,
                indent=2
            )
            
            return yaml_content
            
        except Exception as e:
            raise ValueError(f"Failed to export configuration to YAML: {str(e)}")

    def import_json(self, json_content: str) -> DeploymentConfig:
        """
        Parse JSON configuration file and create DeploymentConfig object.

        This method parses JSON content and reconstructs the complete DeploymentConfig
        object with all nested dataclasses. It handles the conversion from dictionary
        format to the proper dataclass instances.

        Args:
            json_content: String containing JSON configuration data

        Returns:
            DeploymentConfig: Fully populated configuration object

        Raises:
            json.JSONDecodeError: If JSON syntax is invalid
            KeyError: If required configuration fields are missing
            TypeError: If configuration values have incorrect types
            ValueError: If configuration values are invalid

        Requirements:
            - Requirement 2.2: Parse JSON and load all parameters
            - Requirement 2.7: Preserve all parameter values during import

        Example:
            >>> manager = ConfigurationManager()
            >>> json_str = '{"aws": {"region": "us-east-1", "profile": "default"}}'
            >>> config = manager.import_json(json_str)
            >>> config.aws.region
            'us-east-1'
        """
        try:
            # Parse JSON content
            config_dict = json.loads(json_content)

            if not isinstance(config_dict, dict):
                raise ValueError("JSON content must be an object")

            # Reconstruct nested dataclass objects
            aws_config = AWSConfig(**config_dict.get('aws', {}))

            network_dict = config_dict.get('network', {})
            network_config = NetworkConfig(**network_dict)

            fortigate_dict = config_dict.get('fortigate', {})
            # Handle nested AMIDiscoveryConfig
            ami_discovery_dict = fortigate_dict.get('ami_discovery', {})
            ami_discovery = AMIDiscoveryConfig(**ami_discovery_dict)

            # Handle nested LicensingConfig
            licensing_dict = fortigate_dict.get('licensing', {})
            licensing = LicensingConfig(**licensing_dict)

            # Create FortiGateConfig with nested objects
            fortigate_config = FortiGateConfig(
                ami_id=fortigate_dict.get('ami_id'),
                ami_discovery=ami_discovery,
                licensing=licensing,
                instance_type=fortigate_dict.get('instance_type'),
                key_pair_name=fortigate_dict.get('key_pair_name'),
                admin_password=fortigate_dict.get('admin_password'),
                ha_password=fortigate_dict.get('ha_password'),
                hostname_primary=fortigate_dict.get('hostname_primary', 'fortigate-primary'),
                hostname_backup=fortigate_dict.get('hostname_backup', 'fortigate-backup')
            )

            transit_gateway_dict = config_dict.get('transit_gateway', {})
            transit_gateway_config = TransitGatewayConfig(**transit_gateway_dict)

            monitoring_dict = config_dict.get('monitoring', {})
            monitoring_config = MonitoringConfig(**monitoring_dict)

            backend_dict = config_dict.get('backend', {})
            backend_config = BackendConfig(**backend_dict)

            # Create complete DeploymentConfig
            deployment_config = DeploymentConfig(
                aws=aws_config,
                network=network_config,
                fortigate=fortigate_config,
                transit_gateway=transit_gateway_config,
                monitoring=monitoring_config,
                backend=backend_config,
                environment=config_dict.get('environment', 'prod'),
                owner_tag=config_dict.get('owner_tag', 'NetworkTeam')
            )

            return deployment_config

        except json.JSONDecodeError as e:
            raise json.JSONDecodeError(f"Invalid JSON syntax: {str(e)}", e.doc, e.pos)
        except KeyError as e:
            raise KeyError(f"Missing required configuration field: {str(e)}")
        except TypeError as e:
            raise TypeError(f"Invalid configuration value type: {str(e)}")
        except Exception as e:
            raise ValueError(f"Failed to parse configuration: {str(e)}")

    def export_json(self, config: DeploymentConfig, redact_sensitive: bool = True) -> str:
        """
        Serialize DeploymentConfig object to JSON format.

        This method converts a DeploymentConfig object to JSON string format,
        properly handling nested dataclass structures. Optionally redacts sensitive
        data like passwords and access keys.

        Args:
            config: DeploymentConfig object to serialize
            redact_sensitive: If True, replace sensitive values with '[REDACTED]'

        Returns:
            str: JSON-formatted configuration string

        Requirements:
            - Requirement 2.4: Generate JSON file with current parameters
            - Requirement 2.5: Redact sensitive data when exporting
            - Requirement 2.7: Preserve all parameter values during export

        Example:
            >>> manager = ConfigurationManager()
            >>> config = DeploymentConfig(...)
            >>> json_str = manager.export_json(config, redact_sensitive=True)
            >>> '"admin_password": "[REDACTED]"' in json_str
            True
        """
        try:
            # Convert dataclass to dictionary
            config_dict = asdict(config)

            # Redact sensitive data if requested
            if redact_sensitive:
                config_dict = self._redact_sensitive_data(config_dict)

            # Convert to JSON with proper formatting
            json_content = json.dumps(
                config_dict,
                indent=2,
                ensure_ascii=False
            )

            return json_content

        except Exception as e:
            raise ValueError(f"Failed to export configuration to JSON: {str(e)}")

    
    def _redact_sensitive_data(self, config_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Remove sensitive data from configuration dictionary.
        
        This method recursively traverses the configuration dictionary and replaces
        sensitive values (passwords, access keys, secret names) with '[REDACTED]'.
        
        Args:
            config_dict: Configuration dictionary to redact
            
        Returns:
            Dict: Configuration dictionary with sensitive values redacted
            
        Requirements:
            - Requirement 2.5: Redact passwords, access keys, and secret names
            
        Sensitive Fields:
            - admin_password
            - ha_password
            - access_key_id
            - secret_access_key
            - primary_license_secret
            - backup_license_secret
        """
        # List of sensitive field names to redact
        sensitive_fields = {
            'admin_password',
            'ha_password',
            'access_key_id',
            'secret_access_key',
            'primary_license_secret',
            'backup_license_secret'
        }
        
        # Create a deep copy to avoid modifying the original
        import copy
        redacted_dict = copy.deepcopy(config_dict)
        
        # Recursively redact sensitive fields
        def redact_recursive(d: Dict[str, Any]) -> None:
            for key, value in d.items():
                if key in sensitive_fields and value is not None:
                    d[key] = '[REDACTED]'
                elif isinstance(value, dict):
                    redact_recursive(value)
        
        redact_recursive(redacted_dict)
        return redacted_dict

    def validate_config(self, config: DeploymentConfig) -> Tuple[bool, List[str]]:
        """
        Validate configuration completeness and format.

        This method checks that all required fields are present and have valid formats.
        It validates parameter types, formats, and logical consistency.

        Args:
            config: DeploymentConfig object to validate

        Returns:
            Tuple[bool, List[str]]: (is_valid, list_of_error_messages)
                - is_valid: True if configuration is valid, False otherwise
                - list_of_error_messages: List of validation error messages (empty if valid)

        Requirements:
            - Requirement 2.6: Validate configuration files and display specific errors

        Example:
            >>> manager = ConfigurationManager()
            >>> config = DeploymentConfig(...)
            >>> is_valid, errors = manager.validate_config(config)
            >>> if not is_valid:
            ...     for error in errors:
            ...         print(error)
        """
        errors = []

        # Validate AWS configuration
        if not config.aws.region:
            errors.append("AWS region is required")

        # Validate region format (e.g., us-east-1, eu-west-2)
        if config.aws.region and not re.match(r'^[a-z]{2}-[a-z]+-\d+$', config.aws.region):
            errors.append(f"Invalid AWS region format: {config.aws.region}")

        # Validate network configuration
        if not config.network.vpc_id:
            errors.append("VPC ID is required")
        elif not re.match(r'^vpc-[a-f0-9]{8,17}$', config.network.vpc_id):
            errors.append(f"Invalid VPC ID format: {config.network.vpc_id}")

        if not config.network.availability_zones or len(config.network.availability_zones) < 2:
            errors.append("At least two availability zones are required")

        # Validate subnet IDs (8 required)
        subnet_fields = [
            ('outside_subnet_primary', 'Primary outside subnet'),
            ('inside_subnet_primary', 'Primary inside subnet'),
            ('ha_subnet_primary', 'Primary HA subnet'),
            ('mgmt_subnet_primary', 'Primary management subnet'),
            ('outside_subnet_backup', 'Backup outside subnet'),
            ('inside_subnet_backup', 'Backup inside subnet'),
            ('ha_subnet_backup', 'Backup HA subnet'),
            ('mgmt_subnet_backup', 'Backup management subnet')
        ]

        for field_name, display_name in subnet_fields:
            subnet_id = getattr(config.network, field_name)
            if not subnet_id:
                errors.append(f"{display_name} ID is required")
            elif not re.match(r'^subnet-[a-f0-9]{8,17}$', subnet_id):
                errors.append(f"Invalid {display_name} ID format: {subnet_id}")

        # Validate ENI IDs (8 required)
        eni_fields = [
            ('primary_outside_eni_id', 'Primary outside ENI'),
            ('primary_inside_eni_id', 'Primary inside ENI'),
            ('primary_ha_eni_id', 'Primary HA ENI'),
            ('primary_mgmt_eni_id', 'Primary management ENI'),
            ('backup_outside_eni_id', 'Backup outside ENI'),
            ('backup_inside_eni_id', 'Backup inside ENI'),
            ('backup_ha_eni_id', 'Backup HA ENI'),
            ('backup_mgmt_eni_id', 'Backup management ENI')
        ]

        for field_name, display_name in eni_fields:
            eni_id = getattr(config.network, field_name)
            if not eni_id:
                errors.append(f"{display_name} ID is required")
            elif not re.match(r'^eni-[a-f0-9]{8,17}$', eni_id):
                errors.append(f"Invalid {display_name} ID format: {eni_id}")

        # Validate EIP configuration
        if config.network.allocate_eips:
            if config.network.enable_eip_failover:
                # If EIP failover is enabled, we need EIP allocation IDs
                if not config.network.primary_outside_eip_id:
                    errors.append("Primary outside EIP allocation ID is required when EIP failover is enabled")
                elif not re.match(r'^eipalloc-[a-f0-9]{8,17}$', config.network.primary_outside_eip_id):
                    errors.append(f"Invalid primary outside EIP allocation ID format: {config.network.primary_outside_eip_id}")

                if not config.network.backup_outside_eip_id:
                    errors.append("Backup outside EIP allocation ID is required when EIP failover is enabled")
                elif not re.match(r'^eipalloc-[a-f0-9]{8,17}$', config.network.backup_outside_eip_id):
                    errors.append(f"Invalid backup outside EIP allocation ID format: {config.network.backup_outside_eip_id}")

        # Validate FortiGate configuration
        if not config.fortigate.ami_id and not config.fortigate.ami_discovery.enabled:
            errors.append("Either AMI ID or AMI discovery must be configured")

        if config.fortigate.ami_id and not re.match(r'^ami-[a-f0-9]{8,17}$', config.fortigate.ami_id):
            errors.append(f"Invalid AMI ID format: {config.fortigate.ami_id}")

        if not config.fortigate.instance_type:
            errors.append("FortiGate instance type is required")

        if not config.fortigate.key_pair_name:
            errors.append("EC2 key pair name is required")

        if not config.fortigate.admin_password:
            errors.append("FortiGate admin password is required")
        elif len(config.fortigate.admin_password) < 8:
            errors.append("FortiGate admin password must be at least 8 characters")

        if not config.fortigate.ha_password:
            errors.append("FortiGate HA password is required")
        elif len(config.fortigate.ha_password) < 8:
            errors.append("FortiGate HA password must be at least 8 characters")

        # Validate licensing configuration
        if config.fortigate.licensing.type == 'BYOL':
            has_secrets = (config.fortigate.licensing.primary_license_secret and 
                          config.fortigate.licensing.backup_license_secret)
            has_s3 = (config.fortigate.licensing.license_s3_bucket and
                     config.fortigate.licensing.primary_license_s3_key and
                     config.fortigate.licensing.backup_license_s3_key)
            
            if not has_secrets and not has_s3:
                errors.append("BYOL licensing requires either Secrets Manager secrets or S3 bucket configuration")
            
            if has_secrets:
                # Validate secrets are not empty
                if not config.fortigate.licensing.primary_license_secret.strip():
                    errors.append("Primary license secret name cannot be empty")
                if not config.fortigate.licensing.backup_license_secret.strip():
                    errors.append("Backup license secret name cannot be empty")
            
            if has_s3:
                # Validate S3 configuration
                if not config.fortigate.licensing.license_s3_bucket.strip():
                    errors.append("License S3 bucket cannot be empty")
                if not config.fortigate.licensing.primary_license_s3_key.strip():
                    errors.append("Primary license S3 key cannot be empty")
                if not config.fortigate.licensing.backup_license_s3_key.strip():
                    errors.append("Backup license S3 key cannot be empty")

        # Validate Transit Gateway configuration
        if config.transit_gateway.create_new:
            if not config.transit_gateway.transit_gateway_asn:
                errors.append("Transit Gateway ASN is required when creating new Transit Gateway")
            elif not (64512 <= config.transit_gateway.transit_gateway_asn <= 65534 or
                     4200000000 <= config.transit_gateway.transit_gateway_asn <= 4294967294):
                errors.append(f"Invalid Transit Gateway ASN: {config.transit_gateway.transit_gateway_asn}. Must be in range 64512-65534 or 4200000000-4294967294")
        else:
            if not config.transit_gateway.transit_gateway_id:
                errors.append("Transit Gateway ID is required when not creating new")
            elif not re.match(r'^tgw-[a-f0-9]{8,17}$', config.transit_gateway.transit_gateway_id):
                errors.append(f"Invalid Transit Gateway ID format: {config.transit_gateway.transit_gateway_id}")

        if config.transit_gateway.bgp_asn:
            if not (64512 <= config.transit_gateway.bgp_asn <= 65534 or
                   4200000000 <= config.transit_gateway.bgp_asn <= 4294967294):
                errors.append(f"Invalid FortiGate BGP ASN: {config.transit_gateway.bgp_asn}. Must be in range 64512-65534 or 4200000000-4294967294")

        # Validate backend configuration
        if config.backend.backend_type == 's3':
            if not config.backend.s3_bucket:
                errors.append("S3 bucket is required for S3 backend")
            if not config.backend.s3_key:
                errors.append("S3 key is required for S3 backend")
            if not config.backend.s3_region:
                errors.append("S3 region is required for S3 backend")
            if not config.backend.dynamodb_table:
                errors.append("DynamoDB table is required for S3 backend state locking")

        # Return validation result
        is_valid = len(errors) == 0
        return is_valid, errors



class AWSIntegrationManager:
    """
    Manages AWS API integration for resource validation and discovery.
    
    This class wraps ConfigurationValidator, AMIDiscovery, and LicenseManager
    from deploy.py to provide AWS resource validation, AMI discovery, and
    license management functionality for the Streamlit web application.
    
    Requirements:
        - Requirement 3.1: AWS session creation
        - Requirements 3.2-3.9: Resource validation
        - Requirements 4.1-4.4: AMI discovery
        - Requirement 5.10: License manager integration
    """
    
    def __init__(self, aws_config: AWSConfig):
        """
        Initialize AWS Integration Manager with AWS credentials.
        
        Args:
            aws_config: AWSConfig object containing region, profile, and credentials
            
        Requirements:
            - Requirement 3.1: Create authenticated AWS session
        """
        self.aws_config = aws_config
        self.aws_session = None
        self.validator = None
        self.ami_discovery = None
        self.license_manager = None
        
    def create_session(self) -> Tuple[bool, str]:
        """
        Create authenticated AWS session.
        
        Returns:
            Tuple[bool, str]: (success, message)
                - success: True if session created successfully
                - message: Success or error message
                
        Requirements:
            - Requirement 3.1: Establish authenticated AWS session
        """
        try:
            # Create boto3 session with provided credentials
            if self.aws_config.access_key_id and self.aws_config.secret_access_key:
                self.aws_session = boto3.Session(
                    aws_access_key_id=self.aws_config.access_key_id,
                    aws_secret_access_key=self.aws_config.secret_access_key,
                    region_name=self.aws_config.region
                )
            elif self.aws_config.profile:
                self.aws_session = boto3.Session(
                    profile_name=self.aws_config.profile,
                    region_name=self.aws_config.region
                )
            else:
                # Use default credentials
                self.aws_session = boto3.Session(region_name=self.aws_config.region)
            
            # Test the session by making a simple API call
            sts = self.aws_session.client('sts')
            identity = sts.get_caller_identity()
            
            # Initialize helper classes
            self.validator = ConfigurationValidator(self.aws_session)
            self.ami_discovery = AMIDiscovery(self.aws_session)
            self.license_manager = LicenseManager(self.aws_session)
            
            return True, f"AWS session created successfully for account {identity['Account']}"
            
        except Exception as e:
            return False, f"Failed to create AWS session: {str(e)}"
    
    def validate_vpc(self, vpc_id: str) -> Tuple[bool, str]:
        """
        Validate VPC exists and is available.
        
        Args:
            vpc_id: VPC ID to validate
            
        Returns:
            Tuple[bool, str]: (is_valid, message)
                - is_valid: True if VPC is valid
                - message: Validation result message
                
        Requirements:
            - Requirement 3.2: Validate VPC exists and is available
        """
        if not self.validator:
            return False, "AWS session not initialized. Please create session first."
        
        try:
            is_valid = self.validator.validate_vpc(vpc_id)
            if is_valid:
                return True, f"VPC {vpc_id} is valid and available"
            else:
                return False, f"VPC {vpc_id} validation failed"
        except Exception as e:
            return False, f"Error validating VPC {vpc_id}: {str(e)}"
    
    def validate_subnets(self, subnet_ids: List[str], expected_azs: List[str]) -> Tuple[bool, str]:
        """
        Validate subnets exist in correct availability zones.
        
        Args:
            subnet_ids: List of subnet IDs to validate
            expected_azs: List of expected availability zones
            
        Returns:
            Tuple[bool, str]: (is_valid, message)
                - is_valid: True if all subnets are valid
                - message: Validation result message
                
        Requirements:
            - Requirement 3.3: Validate subnets exist in correct AZs
        """
        if not self.validator:
            return False, "AWS session not initialized. Please create session first."
        
        try:
            is_valid = self.validator.validate_subnets(subnet_ids, expected_azs)
            if is_valid:
                return True, f"All {len(subnet_ids)} subnets validated successfully"
            else:
                return False, f"Subnet validation failed"
        except Exception as e:
            return False, f"Error validating subnets: {str(e)}"
    
    def validate_enis(self, eni_ids: List[str]) -> Tuple[bool, str]:
        """
        Validate ENIs exist and are available.
        
        Args:
            eni_ids: List of ENI IDs to validate
            
        Returns:
            Tuple[bool, str]: (is_valid, message)
                - is_valid: True if all ENIs are valid
                - message: Validation result message
                
        Requirements:
            - Requirement 3.4: Validate ENIs exist and are available
        """
        if not self.validator:
            return False, "AWS session not initialized. Please create session first."
        
        try:
            is_valid = self.validator.validate_enis(eni_ids)
            if is_valid:
                return True, f"All {len(eni_ids)} ENIs validated successfully"
            else:
                return False, f"ENI validation failed"
        except Exception as e:
            return False, f"Error validating ENIs: {str(e)}"
    
    def validate_eips(self, eip_allocation_ids: List[str]) -> Tuple[bool, str]:
        """
        Validate EIP allocations exist.
        
        Args:
            eip_allocation_ids: List of EIP allocation IDs to validate
            
        Returns:
            Tuple[bool, str]: (is_valid, message)
                - is_valid: True if all EIPs are valid
                - message: Validation result message
                
        Requirements:
            - Requirement 3.5: Validate EIP allocations exist
        """
        if not self.validator:
            return False, "AWS session not initialized. Please create session first."
        
        try:
            is_valid = self.validator.validate_eip_allocations(eip_allocation_ids)
            if is_valid:
                return True, f"All {len(eip_allocation_ids)} EIP allocations validated successfully"
            else:
                return False, f"EIP allocation validation failed"
        except Exception as e:
            return False, f"Error validating EIP allocations: {str(e)}"
    
    def validate_transit_gateway(self, tgw_id: str) -> Tuple[bool, str]:
        """
        Validate Transit Gateway exists and is available.
        
        Args:
            tgw_id: Transit Gateway ID to validate
            
        Returns:
            Tuple[bool, str]: (is_valid, message)
                - is_valid: True if Transit Gateway is valid
                - message: Validation result message
                
        Requirements:
            - Requirement 3.6: Validate Transit Gateway exists and is available
        """
        if not self.validator:
            return False, "AWS session not initialized. Please create session first."
        
        try:
            is_valid = self.validator.validate_transit_gateway(tgw_id)
            if is_valid:
                return True, f"Transit Gateway {tgw_id} is valid and available"
            else:
                return False, f"Transit Gateway {tgw_id} validation failed"
        except Exception as e:
            return False, f"Error validating Transit Gateway {tgw_id}: {str(e)}"
    
    def validate_ami(self, ami_id: str) -> Tuple[bool, str]:
        """
        Validate AMI exists and is available.
        
        Args:
            ami_id: AMI ID to validate
            
        Returns:
            Tuple[bool, str]: (is_valid, message)
                - is_valid: True if AMI is valid
                - message: Validation result message
                
        Requirements:
            - Requirement 3.7: Validate AMI exists and is available
        """
        if not self.validator:
            return False, "AWS session not initialized. Please create session first."
        
        try:
            is_valid = self.validator.validate_ami(ami_id)
            if is_valid:
                return True, f"AMI {ami_id} is valid and available"
            else:
                return False, f"AMI {ami_id} validation failed"
        except Exception as e:
            return False, f"Error validating AMI {ami_id}: {str(e)}"
    
    def validate_key_pair(self, key_name: str) -> Tuple[bool, str]:
        """
        Validate EC2 key pair exists.
        
        Args:
            key_name: Key pair name to validate
            
        Returns:
            Tuple[bool, str]: (is_valid, message)
                - is_valid: True if key pair exists
                - message: Validation result message
                
        Requirements:
            - Requirement 3.8: Validate key pair exists in region
        """
        if not self.validator:
            return False, "AWS session not initialized. Please create session first."
        
        try:
            is_valid = self.validator.validate_key_pair(key_name)
            if is_valid:
                return True, f"Key pair '{key_name}' exists in region"
            else:
                return False, f"Key pair '{key_name}' not found"
        except Exception as e:
            return False, f"Error validating key pair '{key_name}': {str(e)}"
    
    def discover_amis(self, version: str, license_type: str, architecture: str = "x86_64") -> Tuple[bool, Optional[Dict], str]:
        """
        Discover FortiGate AMIs matching criteria.
        
        Args:
            version: FortiGate version (e.g., "7.6", "7.4")
            license_type: License type ("BYOL", "OnDemand", "Reserved")
            architecture: CPU architecture (default: "x86_64")
            
        Returns:
            Tuple[bool, Optional[Dict], str]: (success, ami_info, message)
                - success: True if AMI discovered
                - ami_info: Dictionary with AMI details (id, name, description, date)
                - message: Success or error message
                
        Requirements:
            - Requirement 4.1: Query AWS Marketplace for FortiGate AMIs
            - Requirement 4.2: Filter by FortiGate version
            - Requirement 4.3: Filter by license type
            - Requirement 4.4: Filter by architecture
        """
        if not self.ami_discovery:
            return False, None, "AWS session not initialized. Please create session first."
        
        try:
            ami_id = self.ami_discovery.find_latest_ami(version, license_type, architecture)
            
            if ami_id:
                # Get AMI details
                ec2 = self.aws_session.client('ec2')
                response = ec2.describe_images(ImageIds=[ami_id])
                
                if response['Images']:
                    image = response['Images'][0]
                    ami_info = {
                        'id': image['ImageId'],
                        'name': image['Name'],
                        'description': image.get('Description', 'N/A'),
                        'creation_date': image['CreationDate'],
                        'architecture': image['Architecture']
                    }
                    return True, ami_info, f"Found AMI: {ami_id}"
                else:
                    return False, None, f"AMI {ami_id} details not found"
            else:
                return False, None, f"No FortiGate {version} {license_type} AMI found"
                
        except Exception as e:
            return False, None, f"Error discovering AMIs: {str(e)}"
    
    def list_fortigate_versions(self) -> Tuple[bool, List[str], str]:
        """
        List available FortiGate versions.
        
        Returns:
            Tuple[bool, List[str], str]: (success, versions, message)
                - success: True if versions retrieved
                - versions: List of available FortiGate versions
                - message: Success or error message
                
        Requirements:
            - Requirement 4.9: List all available FortiGate versions
        """
        if not self.ami_discovery:
            return False, [], "AWS session not initialized. Please create session first."
        
        try:
            versions = self.ami_discovery.list_available_versions()
            if versions:
                return True, versions, f"Found {len(versions)} FortiGate versions"
            else:
                return False, [], "No FortiGate versions found"
        except Exception as e:
            return False, [], f"Error listing FortiGate versions: {str(e)}"
    
    def test_secrets_manager_access(self, secret_name: str) -> Tuple[bool, str]:
        """
        Test access to AWS Secrets Manager secret.
        
        Args:
            secret_name: Name of the secret to test
            
        Returns:
            Tuple[bool, str]: (success, message)
                - success: True if secret is accessible
                - message: Success or error message
                
        Requirements:
            - Requirement 5.10: Test Secrets Manager access
        """
        if not self.license_manager:
            return False, "AWS session not initialized. Please create session first."
        
        try:
            license_content = self.license_manager.get_license_from_secrets_manager(secret_name)
            if license_content:
                # Validate license format
                is_valid = self.license_manager.validate_license_format(license_content)
                if is_valid:
                    return True, f"Secret '{secret_name}' is accessible and contains valid license"
                else:
                    return False, f"Secret '{secret_name}' is accessible but license format is invalid"
            else:
                return False, f"Failed to retrieve secret '{secret_name}'"
        except Exception as e:
            return False, f"Error accessing secret '{secret_name}': {str(e)}"
    
    def test_s3_access(self, bucket: str, key: str) -> Tuple[bool, str]:
        """
        Test access to S3 object.
        
        Args:
            bucket: S3 bucket name
            key: S3 object key
            
        Returns:
            Tuple[bool, str]: (success, message)
                - success: True if object is accessible
                - message: Success or error message
                
        Requirements:
            - Requirement 5.10: Test S3 access
        """
        if not self.license_manager:
            return False, "AWS session not initialized. Please create session first."
        
        try:
            license_content = self.license_manager.get_license_from_s3(bucket, key)
            if license_content:
                # Validate license format
                is_valid = self.license_manager.validate_license_format(license_content)
                if is_valid:
                    return True, f"S3 object s3://{bucket}/{key} is accessible and contains valid license"
                else:
                    return False, f"S3 object s3://{bucket}/{key} is accessible but license format is invalid"
            else:
                return False, f"Failed to retrieve S3 object s3://{bucket}/{key}"
        except Exception as e:
            return False, f"Error accessing S3 object s3://{bucket}/{key}: {str(e)}"


# ============================================================================
# TERRAFORM INTEGRATION MANAGER
# ============================================================================

class TerraformIntegrationManager:
    """
    Manages Terraform operations with real-time output streaming.
    
    This class wraps the TerraformManager from deploy.py and adds
    real-time output streaming capabilities for the web interface.
    
    Requirements:
        - Requirements 7.1, 7.2, 7.3: Terraform operations (init, plan, apply, destroy)
        - Requirements 6.1, 6.2, 6.11: Backend configuration
        - Requirement 7.7: tfvars generation
        - Requirements 7.4, 7.5, 7.6: Command execution and streaming
        - Requirement 10.8: Output extraction
    """
    
    def __init__(self, terraform_dir: Path, backend_config: BackendConfig):
        """
        Initialize TerraformIntegrationManager.
        
        Args:
            terraform_dir: Path to Terraform directory
            backend_config: Backend configuration (local or S3)
        """
        self.terraform_dir = terraform_dir
        self.backend_config = backend_config
        self.tfvars_file = terraform_dir / "terraform.tfvars"
        self.backend_tf_file = terraform_dir / "backend.tf"
        self.plan_file = terraform_dir / "tfplan"
    
    def configure_backend(self) -> Tuple[bool, str]:
        """
        Configure Terraform backend (local or S3).
        
        Returns:
            Tuple[bool, str]: (success, message)
                - success: True if backend configured successfully
                - message: Success or error message
        
        Requirements:
            - Requirement 6.1: Support local backend configuration
            - Requirement 6.2: Support S3 backend configuration
            - Requirement 6.11: Validate S3 backend configuration
        """
        try:
            if self.backend_config.backend_type == "s3":
                # Validate S3 backend configuration
                if not all([
                    self.backend_config.s3_bucket,
                    self.backend_config.s3_key,
                    self.backend_config.s3_region,
                    self.backend_config.dynamodb_table
                ]):
                    return False, "S3 backend requires: bucket, key, region, and dynamodb_table"
                
                # Generate backend.tf file
                backend_content = f'''# Terraform Backend Configuration
# Generated by web-app-enhanced.py

terraform {{
  backend "s3" {{
    bucket         = "{self.backend_config.s3_bucket}"
    key            = "{self.backend_config.s3_key}"
    region         = "{self.backend_config.s3_region}"
    dynamodb_table = "{self.backend_config.dynamodb_table}"
    encrypt        = {str(self.backend_config.encrypt).lower()}
'''
                
                if self.backend_config.s3_profile:
                    backend_content += f'    profile        = "{self.backend_config.s3_profile}"\n'
                
                if self.backend_config.kms_key_id:
                    backend_content += f'    kms_key_id     = "{self.backend_config.kms_key_id}"\n'
                
                backend_content += '''  }
}
'''
                
                with open(self.backend_tf_file, 'w') as f:
                    f.write(backend_content)
                
                message = f"S3 backend configured successfully:\n"
                message += f"  - Bucket: {self.backend_config.s3_bucket}\n"
                message += f"  - Key: {self.backend_config.s3_key}\n"
                message += f"  - DynamoDB Table: {self.backend_config.dynamodb_table}"
                
                return True, message
                
            else:  # local backend
                # Remove backend.tf if it exists (to use default local backend)
                if self.backend_tf_file.exists():
                    self.backend_tf_file.unlink()
                
                return True, "Local backend configured (terraform.tfstate)"
        
        except Exception as e:
            return False, f"Error configuring backend: {str(e)}"
    
    def generate_tfvars(self, config: DeploymentConfig) -> Tuple[bool, str]:
        """
        Generate terraform.tfvars file from DeploymentConfig.
        
        Args:
            config: Deployment configuration
            
        Returns:
            Tuple[bool, str]: (success, message)
                - success: True if tfvars generated successfully
                - message: Success or error message
        
        Requirements:
            - Requirement 7.7: Generate terraform.tfvars file
        """
        try:
            tfvars_content = f"""# FortiGate HA Deployment Configuration
# Generated by web-app-enhanced.py

# AWS Configuration
aws_region = "{config.aws.region}"
environment = "{config.environment}"
owner_tag = "{config.owner_tag}"

# Network Configuration
vpc_id = "{config.network.vpc_id}"
availability_zones = {json.dumps(config.network.availability_zones)}

# Subnet Configuration
outside_subnet_primary = "{config.network.outside_subnet_primary}"
inside_subnet_primary = "{config.network.inside_subnet_primary}"
ha_subnet_primary = "{config.network.ha_subnet_primary}"
mgmt_subnet_primary = "{config.network.mgmt_subnet_primary}"

outside_subnet_backup = "{config.network.outside_subnet_backup}"
inside_subnet_backup = "{config.network.inside_subnet_backup}"
ha_subnet_backup = "{config.network.ha_subnet_backup}"
mgmt_subnet_backup = "{config.network.mgmt_subnet_backup}"

# ENI Configuration (Pre-created by Network Team)
primary_outside_eni_id = "{config.network.primary_outside_eni_id}"
primary_inside_eni_id = "{config.network.primary_inside_eni_id}"
primary_ha_eni_id = "{config.network.primary_ha_eni_id}"
primary_mgmt_eni_id = "{config.network.primary_mgmt_eni_id}"

backup_outside_eni_id = "{config.network.backup_outside_eni_id}"
backup_inside_eni_id = "{config.network.backup_inside_eni_id}"
backup_ha_eni_id = "{config.network.backup_ha_eni_id}"
backup_mgmt_eni_id = "{config.network.backup_mgmt_eni_id}"

# Elastic IP Configuration (for internet routing)
allocate_eips = {str(config.network.allocate_eips).lower()}
primary_outside_eip_id = "{config.network.primary_outside_eip_id or ''}"
backup_outside_eip_id = "{config.network.backup_outside_eip_id or ''}"

# EIP Failover Configuration
enable_eip_failover = {str(config.network.enable_eip_failover).lower()}

# FortiGate Configuration
fortigate_ami_id = "{config.fortigate.ami_id}"
instance_type = "{config.fortigate.instance_type}"
key_pair_name = "{config.fortigate.key_pair_name}"
admin_password = "{config.fortigate.admin_password}"
ha_password = "{config.fortigate.ha_password}"
fortigate_hostname_primary = "{config.fortigate.hostname_primary}"
fortigate_hostname_backup = "{config.fortigate.hostname_backup}"

# Transit Gateway Configuration
create_transit_gateway = {str(config.transit_gateway.create_new).lower()}
existing_transit_gateway_id = "{config.transit_gateway.transit_gateway_id or ''}"
transit_gateway_asn = {config.transit_gateway.transit_gateway_asn}
bgp_asn = {config.transit_gateway.bgp_asn}
spoke_vpc_cidrs = {json.dumps(config.transit_gateway.spoke_vpc_cidrs or [])}

# Security Configuration
mgmt_access_cidrs = {json.dumps(config.network.mgmt_access_cidrs)}

# Monitoring Configuration
enable_flow_logs = {str(config.monitoring.enable_flow_logs).lower()}
log_retention_days = {config.monitoring.log_retention_days}
enable_detailed_monitoring = {str(config.monitoring.enable_detailed_monitoring).lower()}
"""
            
            with open(self.tfvars_file, 'w') as f:
                f.write(tfvars_content)
            
            return True, f"Generated Terraform variables file: {self.tfvars_file}"
        
        except Exception as e:
            return False, f"Error generating tfvars: {str(e)}"
    
    def init(self, callback: Optional[Callable[[str], None]] = None) -> Tuple[bool, str]:
        """
        Run terraform init with real-time output streaming.
        
        Args:
            callback: Optional callback function for streaming output
            
        Returns:
            Tuple[bool, str]: (success, output)
                - success: True if init succeeded
                - output: Complete command output
        
        Requirements:
            - Requirement 7.1: Execute Terraform init command
            - Requirement 7.4: Stream output logs in real-time
        """
        cmd = ["terraform", "init", "-no-color"]
        return self._run_terraform_command(cmd, callback)
    
    def plan(self, callback: Optional[Callable[[str], None]] = None) -> Tuple[bool, str]:
        """
        Run terraform plan with real-time output streaming.
        
        Args:
            callback: Optional callback function for streaming output
            
        Returns:
            Tuple[bool, str]: (success, output)
                - success: True if plan succeeded
                - output: Complete command output
        
        Requirements:
            - Requirement 7.2: Execute Terraform plan command
            - Requirement 7.4: Stream output logs in real-time
        """
        cmd = ["terraform", "plan", "-no-color", "-out=tfplan"]
        return self._run_terraform_command(cmd, callback)
    
    def apply(self, callback: Optional[Callable[[str], None]] = None) -> Tuple[bool, str]:
        """
        Run terraform apply with real-time output streaming.
        
        Args:
            callback: Optional callback function for streaming output
            
        Returns:
            Tuple[bool, str]: (success, output)
                - success: True if apply succeeded
                - output: Complete command output
        
        Requirements:
            - Requirement 7.3: Execute Terraform apply command
            - Requirement 7.4: Stream output logs in real-time
        """
        cmd = ["terraform", "apply", "-no-color", "-auto-approve", "tfplan"]
        return self._run_terraform_command(cmd, callback)
    
    def destroy(self, callback: Optional[Callable[[str], None]] = None) -> Tuple[bool, str]:
        """
        Run terraform destroy with real-time output streaming.
        
        Args:
            callback: Optional callback function for streaming output
            
        Returns:
            Tuple[bool, str]: (success, output)
                - success: True if destroy succeeded
                - output: Complete command output
        
        Requirements:
            - Requirement 9.3: Execute Terraform destroy command
            - Requirement 9.4: Stream output logs in real-time
        """
        cmd = ["terraform", "destroy", "-no-color", "-auto-approve"]
        return self._run_terraform_command(cmd, callback)
    
    def get_outputs(self) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        """
        Retrieve Terraform outputs after successful apply.
        
        Returns:
            Tuple[bool, Optional[Dict], str]: (success, outputs, message)
                - success: True if outputs retrieved successfully
                - outputs: Dictionary of output values
                - message: Success or error message
        
        Requirements:
            - Requirement 10.8: Extract Terraform outputs
        """
        try:
            cmd = ["terraform", "output", "-json"]
            result = subprocess.run(
                cmd,
                cwd=self.terraform_dir,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                outputs = json.loads(result.stdout)
                # Extract values from Terraform output format
                output_values = {}
                for key, value in outputs.items():
                    if isinstance(value, dict) and 'value' in value:
                        output_values[key] = value['value']
                    else:
                        output_values[key] = value
                
                return True, output_values, "Outputs retrieved successfully"
            else:
                return False, None, f"Failed to retrieve outputs: {result.stderr}"
        
        except subprocess.TimeoutExpired:
            return False, None, "Timeout retrieving outputs"
        except json.JSONDecodeError as e:
            return False, None, f"Failed to parse output JSON: {str(e)}"
        except Exception as e:
            return False, None, f"Error retrieving outputs: {str(e)}"
    
    def _run_terraform_command(self, cmd: List[str], 
                               callback: Optional[Callable[[str], None]] = None) -> Tuple[bool, str]:
        """
        Run a Terraform command with real-time output streaming.
        
        Args:
            cmd: Command and arguments to execute
            callback: Optional callback function for streaming output
            
        Returns:
            Tuple[bool, str]: (success, output)
                - success: True if command succeeded
                - output: Complete command output
        
        Requirements:
            - Requirements 7.4, 7.5, 7.6: Command execution and streaming
        """
        try:
            output_lines = []
            
            # Start the process
            process = subprocess.Popen(
                cmd,
                cwd=self.terraform_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            # Stream output in real-time
            if process.stdout:
                for line in process.stdout:
                    line = line.rstrip()
                    output_lines.append(line)
                    if callback:
                        callback(line)
            
            # Wait for process to complete
            return_code = process.wait()
            
            # Combine all output
            full_output = '\n'.join(output_lines)
            
            if return_code == 0:
                return True, full_output
            else:
                return False, full_output
        
        except FileNotFoundError:
            error_msg = "Terraform CLI not found. Please install Terraform."
            if callback:
                callback(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"Error executing Terraform command: {str(e)}"
            if callback:
                callback(error_msg)
            return False, error_msg


# ============================================================================
# DEPLOYMENT ORCHESTRATOR
# ============================================================================

class DeploymentOrchestrator:
    """
    Orchestrates the complete deployment workflow including validation, planning,
    deployment, and destruction operations.
    
    This class wraps the DeploymentEngine from deploy.py and provides progress
    callbacks for UI integration. It manages the complete lifecycle of a FortiGate
    HA deployment.
    
    Requirements:
        - Requirements 7.1, 7.2, 7.3: Terraform operations
        - Requirements 3.1, 3.10: AWS resource validation
        - Requirements 8.1, 8.2, 8.8, 8.10: Plan workflow
        - Requirements 10.1, 10.2, 10.3: Deployment tracking
        - Requirements 9.2, 9.3, 9.4, 9.5, 9.6: Destroy workflow
    """
    
    def __init__(self, config: DeploymentConfig, skip_validation: bool = False):
        """
        Initialize the deployment orchestrator.
        
        Args:
            config: Complete deployment configuration
            skip_validation: If True, skip AWS resource validation
        """
        self.config = config
        self.skip_validation = skip_validation
        self.deployment_engine = None
        
        # Initialize deployment engine if available
        if DEPLOYMENT_ENGINE_AVAILABLE:
            try:
                self.deployment_engine = DeploymentEngine(config)
            except Exception as e:
                raise RuntimeError(f"Failed to initialize deployment engine: {e}")
    
    def validate_configuration(self, 
                              progress_callback: Optional[Callable[[str, float], None]] = None) -> Tuple[bool, List[str]]:
        """
        Validate the deployment configuration and AWS resources.
        
        This method performs comprehensive validation including:
        - Configuration parameter validation
        - AWS resource existence and accessibility checks
        - Network configuration validation
        - Permission validation
        
        Args:
            progress_callback: Optional callback function(message: str, progress: float)
                             where progress is 0.0 to 1.0
        
        Returns:
            Tuple[bool, List[str]]: (success, error_messages)
                - success: True if validation passed
                - error_messages: List of validation errors (empty if success)
        
        Requirements:
            - Requirements 3.1: AWS resource validation
            - Requirements 3.10: Validation error reporting
        """
        if self.skip_validation:
            if progress_callback:
                progress_callback("⚠️ Validation skipped by user request", 1.0)
            return True, []
        
        errors = []
        
        try:
            if progress_callback:
                progress_callback("🔍 Validating configuration parameters...", 0.1)
            
            # Validate configuration using ConfigurationValidator
            validator = ConfigurationValidator(self.config)
            
            if progress_callback:
                progress_callback("🔍 Validating AWS credentials...", 0.2)
            
            # Validate AWS session
            try:
                session = boto3.Session(
                    region_name=self.config.aws.region,
                    profile_name=self.config.aws.profile if self.config.aws.profile else None
                )
                sts = session.client('sts')
                sts.get_caller_identity()
            except Exception as e:
                errors.append(f"AWS credentials validation failed: {e}")
                return False, errors
            
            if progress_callback:
                progress_callback("🔍 Validating VPC and network resources...", 0.4)
            
            # Validate VPC
            vpc_valid, vpc_error = validator.validate_vpc()
            if not vpc_valid:
                errors.append(f"VPC validation failed: {vpc_error}")
            
            if progress_callback:
                progress_callback("🔍 Validating subnets...", 0.5)
            
            # Validate subnets
            subnet_valid, subnet_error = validator.validate_subnets()
            if not subnet_valid:
                errors.append(f"Subnet validation failed: {subnet_error}")
            
            if progress_callback:
                progress_callback("🔍 Validating ENIs...", 0.6)
            
            # Validate ENIs
            eni_valid, eni_error = validator.validate_enis()
            if not eni_valid:
                errors.append(f"ENI validation failed: {eni_error}")
            
            if progress_callback:
                progress_callback("🔍 Validating EIPs...", 0.7)
            
            # Validate EIPs if provided
            if self.config.network.eip_allocation_ids:
                eip_valid, eip_error = validator.validate_eips()
                if not eip_valid:
                    errors.append(f"EIP validation failed: {eip_error}")
            
            if progress_callback:
                progress_callback("🔍 Validating Transit Gateway...", 0.8)
            
            # Validate Transit Gateway if using existing
            if self.config.transit_gateway and not self.config.transit_gateway.create_new:
                tgw_valid, tgw_error = validator.validate_transit_gateway()
                if not tgw_valid:
                    errors.append(f"Transit Gateway validation failed: {tgw_error}")
            
            if progress_callback:
                progress_callback("🔍 Validating AMI...", 0.9)
            
            # Validate AMI
            ami_valid, ami_error = validator.validate_ami()
            if not ami_valid:
                errors.append(f"AMI validation failed: {ami_error}")
            
            if progress_callback:
                progress_callback("🔍 Validating key pair...", 0.95)
            
            # Validate key pair
            key_valid, key_error = validator.validate_key_pair()
            if not key_valid:
                errors.append(f"Key pair validation failed: {key_error}")
            
            if errors:
                if progress_callback:
                    progress_callback(f"❌ Validation failed with {len(errors)} error(s)", 1.0)
                return False, errors
            
            if progress_callback:
                progress_callback("✅ Validation completed successfully", 1.0)
            
            return True, []
        
        except Exception as e:
            errors.append(f"Validation error: {str(e)}")
            if progress_callback:
                progress_callback(f"❌ Validation error: {str(e)}", 1.0)
            return False, errors
    
    def plan_deployment(self, 
                       progress_callback: Optional[Callable[[str, float], None]] = None) -> Tuple[bool, str]:
        """
        Generate a Terraform plan for the deployment.
        
        This method:
        1. Initializes Terraform backend
        2. Generates terraform.tfvars
        3. Runs terraform plan
        4. Saves the plan file
        
        Args:
            progress_callback: Optional callback function(message: str, progress: float)
        
        Returns:
            Tuple[bool, str]: (success, plan_output)
                - success: True if plan generation succeeded
                - plan_output: Terraform plan output
        
        Requirements:
            - Requirements 8.1, 8.2: Plan generation
            - Requirements 8.8, 8.10: Plan file saving
        """
        try:
            if progress_callback:
                progress_callback("📋 Initializing Terraform...", 0.1)
            
            # Initialize Terraform integration
            tf_manager = TerraformIntegrationManager(
                terraform_dir="terraform",
                backend_config=self.config.backend
            )
            
            # Configure backend
            if progress_callback:
                progress_callback("📋 Configuring Terraform backend...", 0.2)
            
            backend_success, backend_msg = tf_manager.configure_backend()
            if not backend_success:
                return False, f"Backend configuration failed: {backend_msg}"
            
            # Generate tfvars
            if progress_callback:
                progress_callback("📋 Generating terraform.tfvars...", 0.3)
            
            tfvars_success, tfvars_msg = tf_manager.generate_tfvars(self.config)
            if not tfvars_success:
                return False, f"tfvars generation failed: {tfvars_msg}"
            
            # Run terraform init
            if progress_callback:
                progress_callback("📋 Running terraform init...", 0.4)
            
            def init_callback(line: str):
                if progress_callback:
                    progress_callback(f"  {line}", 0.5)
            
            init_success, init_output = tf_manager.init(callback=init_callback)
            if not init_success:
                return False, f"Terraform init failed:\n{init_output}"
            
            # Run terraform plan
            if progress_callback:
                progress_callback("📋 Running terraform plan...", 0.6)
            
            plan_output_lines = []
            
            def plan_callback(line: str):
                plan_output_lines.append(line)
                if progress_callback:
                    progress_callback(f"  {line}", 0.8)
            
            plan_success, plan_output = tf_manager.plan(callback=plan_callback)
            
            if progress_callback:
                progress_callback("✅ Plan generation completed", 1.0)
            
            return plan_success, plan_output
        
        except Exception as e:
            error_msg = f"Plan generation error: {str(e)}"
            if progress_callback:
                progress_callback(f"❌ {error_msg}", 1.0)
            return False, error_msg
    
    def execute_deployment(self, 
                          progress_callback: Optional[Callable[[str, float], None]] = None) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Execute the full deployment workflow.
        
        This method:
        1. Validates configuration (unless skipped)
        2. Initializes Terraform
        3. Generates plan
        4. Applies the deployment
        5. Extracts outputs
        
        Args:
            progress_callback: Optional callback function(message: str, progress: float)
        
        Returns:
            Tuple[bool, str, Dict]: (success, output, terraform_outputs)
                - success: True if deployment succeeded
                - output: Complete deployment output
                - terraform_outputs: Dictionary of Terraform outputs
        
        Requirements:
            - Requirements 7.1, 7.2, 7.3: Terraform operations
            - Requirements 10.1, 10.2, 10.3: Deployment tracking
        """
        try:
            # Step 1: Validation
            if not self.skip_validation:
                if progress_callback:
                    progress_callback("🔍 Validating configuration...", 0.05)
                
                valid, errors = self.validate_configuration(progress_callback)
                if not valid:
                    error_msg = "Validation failed:\n" + "\n".join(errors)
                    return False, error_msg, {}
            
            # Step 2: Initialize Terraform
            if progress_callback:
                progress_callback("🚀 Initializing deployment...", 0.2)
            
            tf_manager = TerraformIntegrationManager(
                terraform_dir="terraform",
                backend_config=self.config.backend
            )
            
            # Configure backend
            backend_success, backend_msg = tf_manager.configure_backend()
            if not backend_success:
                return False, f"Backend configuration failed: {backend_msg}", {}
            
            # Generate tfvars
            if progress_callback:
                progress_callback("🚀 Generating configuration files...", 0.3)
            
            tfvars_success, tfvars_msg = tf_manager.generate_tfvars(self.config)
            if not tfvars_success:
                return False, f"tfvars generation failed: {tfvars_msg}", {}
            
            # Run terraform init
            if progress_callback:
                progress_callback("🚀 Initializing Terraform...", 0.4)
            
            def init_callback(line: str):
                if progress_callback:
                    progress_callback(f"  {line}", 0.45)
            
            init_success, init_output = tf_manager.init(callback=init_callback)
            if not init_success:
                return False, f"Terraform init failed:\n{init_output}", {}
            
            # Step 3: Apply deployment
            if progress_callback:
                progress_callback("🚀 Applying deployment...", 0.5)
            
            apply_output_lines = []
            
            def apply_callback(line: str):
                apply_output_lines.append(line)
                if progress_callback:
                    # Progress from 0.5 to 0.9 during apply
                    progress_callback(f"  {line}", 0.5 + (len(apply_output_lines) * 0.001))
            
            apply_success, apply_output = tf_manager.apply(callback=apply_callback)
            
            if not apply_success:
                return False, f"Terraform apply failed:\n{apply_output}", {}
            
            # Step 4: Extract outputs
            if progress_callback:
                progress_callback("🚀 Extracting deployment outputs...", 0.95)
            
            outputs_success, outputs = tf_manager.get_outputs()
            
            if progress_callback:
                progress_callback("✅ Deployment completed successfully", 1.0)
            
            return True, apply_output, outputs if outputs_success else {}
        
        except Exception as e:
            error_msg = f"Deployment error: {str(e)}"
            if progress_callback:
                progress_callback(f"❌ {error_msg}", 1.0)
            return False, error_msg, {}
    
    def destroy_deployment(self, 
                          progress_callback: Optional[Callable[[str, float], None]] = None) -> Tuple[bool, str]:
        """
        Destroy the deployed infrastructure.
        
        This method:
        1. Initializes Terraform (if needed)
        2. Runs terraform destroy
        3. Tracks progress
        
        Args:
            progress_callback: Optional callback function(message: str, progress: float)
        
        Returns:
            Tuple[bool, str]: (success, output)
                - success: True if destroy succeeded
                - output: Terraform destroy output
        
        Requirements:
            - Requirements 9.2, 9.3, 9.4, 9.5, 9.6: Destroy workflow
        """
        try:
            if progress_callback:
                progress_callback("🗑️ Initializing destroy operation...", 0.1)
            
            tf_manager = TerraformIntegrationManager(
                terraform_dir="terraform",
                backend_config=self.config.backend
            )
            
            # Ensure Terraform is initialized
            if progress_callback:
                progress_callback("🗑️ Checking Terraform initialization...", 0.2)
            
            def init_callback(line: str):
                if progress_callback:
                    progress_callback(f"  {line}", 0.3)
            
            init_success, init_output = tf_manager.init(callback=init_callback)
            if not init_success:
                return False, f"Terraform init failed:\n{init_output}"
            
            # Run terraform destroy
            if progress_callback:
                progress_callback("🗑️ Destroying infrastructure...", 0.4)
            
            destroy_output_lines = []
            
            def destroy_callback(line: str):
                destroy_output_lines.append(line)
                if progress_callback:
                    progress_callback(f"  {line}", 0.4 + (len(destroy_output_lines) * 0.001))
            
            destroy_success, destroy_output = tf_manager.destroy(callback=destroy_callback)
            
            if progress_callback:
                if destroy_success:
                    progress_callback("✅ Infrastructure destroyed successfully", 1.0)
                else:
                    progress_callback("❌ Destroy operation failed", 1.0)
            
            return destroy_success, destroy_output
        
        except Exception as e:
            error_msg = f"Destroy error: {str(e)}"
            if progress_callback:
                progress_callback(f"❌ {error_msg}", 1.0)
            return False, error_msg


# ============================================================================
# COST CALCULATOR
# ============================================================================

class CostCalculator:
    """
    Calculates and compares costs for different FortiGate licensing models.
    
    This class provides cost estimation for:
    - BYOL (Bring Your Own License)
    - OnDemand (Pay-as-you-go)
    - Reserved Instances (1-year and 3-year terms)
    
    Requirements:
        - Requirements 14.1, 14.2, 14.3: Cost calculation for each model
        - Requirements 14.7, 14.8, 14.9: Cost comparison and recommendations
    """
    
    # Pricing data (USD per hour) - These are approximate values
    # In production, these should be fetched from AWS Pricing API
    PRICING_DATA = {
        # EC2 instance pricing (us-east-1, approximate)
        'instance_types': {
            't2.small': 0.023,
            't3.small': 0.0208,
            't3.medium': 0.0416,
            't3.large': 0.0832,
            'c5.large': 0.085,
            'c5.xlarge': 0.17,
            'c5.2xlarge': 0.34,
            'c5.4xlarge': 0.68,
            'c5n.large': 0.108,
            'c5n.xlarge': 0.216,
            'c5n.2xlarge': 0.432,
            'c5n.4xlarge': 0.864,
        },
        # FortiGate OnDemand pricing (additional cost per hour)
        'fortigate_ondemand': {
            't2.small': 0.15,
            't3.small': 0.15,
            't3.medium': 0.30,
            't3.large': 0.60,
            'c5.large': 0.60,
            'c5.xlarge': 1.20,
            'c5.2xlarge': 2.40,
            'c5.4xlarge': 4.80,
            'c5n.large': 0.60,
            'c5n.xlarge': 1.20,
            'c5n.2xlarge': 2.40,
            'c5n.4xlarge': 4.80,
        },
        # Reserved instance discounts (percentage off on-demand)
        'reserved_discounts': {
            '1year_no_upfront': 0.30,  # 30% discount
            '1year_partial_upfront': 0.35,  # 35% discount
            '1year_all_upfront': 0.40,  # 40% discount
            '3year_no_upfront': 0.45,  # 45% discount
            '3year_partial_upfront': 0.50,  # 50% discount
            '3year_all_upfront': 0.55,  # 55% discount
        }
    }
    
    def __init__(self, instance_type: str, region: str = 'us-east-1'):
        """
        Initialize the cost calculator.
        
        Args:
            instance_type: EC2 instance type (e.g., 'c5.xlarge')
            region: AWS region (default: 'us-east-1')
        """
        self.instance_type = instance_type
        self.region = region
        
        # Get base instance cost
        self.instance_cost_per_hour = self.PRICING_DATA['instance_types'].get(
            instance_type, 0.17  # Default to c5.xlarge pricing
        )
        
        # Get FortiGate OnDemand cost
        self.fortigate_ondemand_cost_per_hour = self.PRICING_DATA['fortigate_ondemand'].get(
            instance_type, 1.20  # Default to c5.xlarge pricing
        )
    
    def calculate_byol_cost(self, duration_hours: int, num_instances: int = 2) -> Dict[str, float]:
        """
        Calculate cost for BYOL (Bring Your Own License) model.
        
        With BYOL, you only pay for EC2 instance costs. License costs are
        separate and not included in this calculation.
        
        Args:
            duration_hours: Deployment duration in hours
            num_instances: Number of instances (default: 2 for HA pair)
        
        Returns:
            Dict with cost breakdown:
                - instance_cost: Total EC2 instance cost
                - license_cost: 0 (license purchased separately)
                - total_cost: Total cost
                - cost_per_hour: Hourly cost
        
        Requirements:
            - Requirements 14.1: BYOL cost calculation
        """
        instance_cost = self.instance_cost_per_hour * duration_hours * num_instances
        
        return {
            'instance_cost': round(instance_cost, 2),
            'license_cost': 0.0,  # License purchased separately
            'total_cost': round(instance_cost, 2),
            'cost_per_hour': round(self.instance_cost_per_hour * num_instances, 2),
            'duration_hours': duration_hours,
            'num_instances': num_instances
        }
    
    def calculate_ondemand_cost(self, duration_hours: int, num_instances: int = 2) -> Dict[str, float]:
        """
        Calculate cost for OnDemand (Pay-as-you-go) model.
        
        With OnDemand, you pay for both EC2 instances and FortiGate licensing
        on an hourly basis.
        
        Args:
            duration_hours: Deployment duration in hours
            num_instances: Number of instances (default: 2 for HA pair)
        
        Returns:
            Dict with cost breakdown:
                - instance_cost: Total EC2 instance cost
                - license_cost: Total FortiGate license cost
                - total_cost: Total cost
                - cost_per_hour: Hourly cost
        
        Requirements:
            - Requirements 14.2: OnDemand cost calculation
        """
        instance_cost = self.instance_cost_per_hour * duration_hours * num_instances
        license_cost = self.fortigate_ondemand_cost_per_hour * duration_hours * num_instances
        total_cost = instance_cost + license_cost
        
        return {
            'instance_cost': round(instance_cost, 2),
            'license_cost': round(license_cost, 2),
            'total_cost': round(total_cost, 2),
            'cost_per_hour': round((self.instance_cost_per_hour + self.fortigate_ondemand_cost_per_hour) * num_instances, 2),
            'duration_hours': duration_hours,
            'num_instances': num_instances
        }
    
    def calculate_reserved_cost(self, duration_hours: int, term: str = '1year',
                               payment_option: str = 'no_upfront', 
                               num_instances: int = 2) -> Dict[str, float]:
        """
        Calculate cost for Reserved Instance model.
        
        With Reserved Instances, you commit to a 1-year or 3-year term and
        receive a discount on both EC2 and FortiGate costs.
        
        Args:
            duration_hours: Deployment duration in hours
            term: '1year' or '3year'
            payment_option: 'no_upfront', 'partial_upfront', or 'all_upfront'
            num_instances: Number of instances (default: 2 for HA pair)
        
        Returns:
            Dict with cost breakdown:
                - instance_cost: Total EC2 instance cost (discounted)
                - license_cost: Total FortiGate license cost (discounted)
                - total_cost: Total cost
                - cost_per_hour: Hourly cost
                - discount_percentage: Discount applied
        
        Requirements:
            - Requirements 14.3: Reserved instance cost calculation
        """
        # Get discount rate
        discount_key = f"{term}_{payment_option}"
        discount_rate = self.PRICING_DATA['reserved_discounts'].get(discount_key, 0.30)
        
        # Calculate discounted costs
        discounted_instance_cost_per_hour = self.instance_cost_per_hour * (1 - discount_rate)
        discounted_license_cost_per_hour = self.fortigate_ondemand_cost_per_hour * (1 - discount_rate)
        
        instance_cost = discounted_instance_cost_per_hour * duration_hours * num_instances
        license_cost = discounted_license_cost_per_hour * duration_hours * num_instances
        total_cost = instance_cost + license_cost
        
        return {
            'instance_cost': round(instance_cost, 2),
            'license_cost': round(license_cost, 2),
            'total_cost': round(total_cost, 2),
            'cost_per_hour': round((discounted_instance_cost_per_hour + discounted_license_cost_per_hour) * num_instances, 2),
            'duration_hours': duration_hours,
            'num_instances': num_instances,
            'discount_percentage': round(discount_rate * 100, 1),
            'term': term,
            'payment_option': payment_option
        }
    
    def compare_licensing_models(self, duration_hours: int, 
                                num_instances: int = 2) -> Dict[str, Any]:
        """
        Compare costs across all licensing models and provide recommendation.
        
        This method calculates costs for:
        - BYOL (assuming license already owned)
        - OnDemand
        - Reserved 1-year (all payment options)
        - Reserved 3-year (all payment options)
        
        Args:
            duration_hours: Deployment duration in hours
            num_instances: Number of instances (default: 2 for HA pair)
        
        Returns:
            Dict with:
                - byol: BYOL cost breakdown
                - ondemand: OnDemand cost breakdown
                - reserved_1year_*: Reserved 1-year cost breakdowns
                - reserved_3year_*: Reserved 3-year cost breakdowns
                - recommended: Recommended model based on duration
                - comparison_chart_data: Data for visualization
        
        Requirements:
            - Requirements 14.7, 14.8: Cost comparison
            - Requirements 14.9: Recommendation logic
        """
        # Calculate all costs
        byol = self.calculate_byol_cost(duration_hours, num_instances)
        ondemand = self.calculate_ondemand_cost(duration_hours, num_instances)
        
        reserved_1year_no = self.calculate_reserved_cost(duration_hours, '1year', 'no_upfront', num_instances)
        reserved_1year_partial = self.calculate_reserved_cost(duration_hours, '1year', 'partial_upfront', num_instances)
        reserved_1year_all = self.calculate_reserved_cost(duration_hours, '1year', 'all_upfront', num_instances)
        
        reserved_3year_no = self.calculate_reserved_cost(duration_hours, '3year', 'no_upfront', num_instances)
        reserved_3year_partial = self.calculate_reserved_cost(duration_hours, '3year', 'partial_upfront', num_instances)
        reserved_3year_all = self.calculate_reserved_cost(duration_hours, '3year', 'all_upfront', num_instances)
        
        # Determine recommendation based on duration
        duration_days = duration_hours / 24
        
        if duration_days < 30:
            recommended = 'ondemand'
            recommendation_reason = "OnDemand is most cost-effective for short-term deployments (< 1 month)"
        elif duration_days < 180:
            recommended = 'byol'
            recommendation_reason = "BYOL is recommended for medium-term deployments (1-6 months) if you have licenses"
        elif duration_days < 365:
            recommended = 'reserved_1year_all_upfront'
            recommendation_reason = "1-year Reserved Instance with all upfront payment offers best value for 6-12 month deployments"
        else:
            recommended = 'reserved_3year_all_upfront'
            recommendation_reason = "3-year Reserved Instance with all upfront payment offers maximum savings for long-term deployments"
        
        # Prepare comparison data for charts
        comparison_data = {
            'Model': ['BYOL', 'OnDemand', 'Reserved 1Y (No Upfront)', 'Reserved 1Y (All Upfront)', 
                     'Reserved 3Y (No Upfront)', 'Reserved 3Y (All Upfront)'],
            'Total Cost': [
                byol['total_cost'],
                ondemand['total_cost'],
                reserved_1year_no['total_cost'],
                reserved_1year_all['total_cost'],
                reserved_3year_no['total_cost'],
                reserved_3year_all['total_cost']
            ],
            'Cost Per Hour': [
                byol['cost_per_hour'],
                ondemand['cost_per_hour'],
                reserved_1year_no['cost_per_hour'],
                reserved_1year_all['cost_per_hour'],
                reserved_3year_no['cost_per_hour'],
                reserved_3year_all['cost_per_hour']
            ]
        }
        
        return {
            'byol': byol,
            'ondemand': ondemand,
            'reserved_1year_no_upfront': reserved_1year_no,
            'reserved_1year_partial_upfront': reserved_1year_partial,
            'reserved_1year_all_upfront': reserved_1year_all,
            'reserved_3year_no_upfront': reserved_3year_no,
            'reserved_3year_partial_upfront': reserved_3year_partial,
            'reserved_3year_all_upfront': reserved_3year_all,
            'recommended': recommended,
            'recommendation_reason': recommendation_reason,
            'comparison_data': comparison_data,
            'duration_hours': duration_hours,
            'duration_days': round(duration_days, 1),
            'num_instances': num_instances,
            'instance_type': self.instance_type
        }


# ============================================================================
# MAIN APPLICATION
# ============================================================================

def main():
    """Main application entry point"""
    # Initialize session state
    initialize_session_state()
    
    # Render header
    st.markdown('<h1 class="main-header">🛡️ FortiGate AWS HA Deployment</h1>', unsafe_allow_html=True)
    
    # Check if deployment engine is available
    if not DEPLOYMENT_ENGINE_AVAILABLE:
        st.error("⚠️ Deployment engine is not available. Please check the installation.")
        st.stop()
    
    # Render sidebar navigation
    st.sidebar.title("📋 Navigation")
    
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
    
    selected_page = st.sidebar.radio("Select Page", list(pages.keys()), key="page_selector")
    st.session_state.current_page = pages[selected_page]
    
    # Render deployment status in sidebar
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📊 Status")
    
    status_icons = {
        "not_started": "⚪",
        "planning": "🟡",
        "validating": "🟡",
        "deploying": "🟠",
        "deployed": "🟢",
        "failed": "🔴",
        "destroying": "🟠"
    }
    
    status_icon = status_icons.get(st.session_state.deployment_status, "⚪")
    st.sidebar.markdown(f"{status_icon} **{st.session_state.deployment_status.replace('_', ' ').title()}**")
    
    # Render configuration status
    if st.session_state.deployment_config:
        st.sidebar.success("✅ Configuration loaded")
    else:
        st.sidebar.warning("⚠️ No configuration")
    
    # Render the selected page
    if st.session_state.current_page == "home":
        render_home_page()
    elif st.session_state.current_page == "config":
        render_configuration_page()
    elif st.session_state.current_page == "ami":
        render_ami_discovery_page()
    elif st.session_state.current_page == "licensing":
        render_licensing_page()
    elif st.session_state.current_page == "cost":
        render_cost_analysis_page()
    elif st.session_state.current_page == "deployment":
        render_deployment_page()
    elif st.session_state.current_page == "monitoring":
        render_monitoring_page()
    elif st.session_state.current_page == "docs":
        render_documentation_page()


# ============================================================================
# HELP TEXT SYSTEM
# ============================================================================

# Comprehensive help text dictionary for all deployment parameters
HELP_TEXT = {
    # AWS Configuration
    'aws_region': """
    **AWS Region**: The AWS region where your FortiGate HA pair will be deployed.
    
    Choose a region close to your users for optimal performance. Common regions:
    - us-east-1: US East (N. Virginia)
    - us-west-2: US West (Oregon)
    - eu-west-1: Europe (Ireland)
    - ap-southeast-1: Asia Pacific (Singapore)
    """,
    
    'aws_profile': """
    **AWS Profile**: The AWS CLI profile to use for authentication.
    
    If you have multiple AWS accounts configured in ~/.aws/credentials, specify
    the profile name here. Leave empty to use the default profile or IAM role.
    """,
    
    'environment': """
    **Environment Tag**: A tag to identify the deployment environment.
    
    Common values: dev, staging, prod, test
    This tag is applied to all AWS resources for organization and cost tracking.
    """,
    
    'owner': """
    **Owner Tag**: Identifies the owner or team responsible for this deployment.
    
    Example: security-team, network-ops, john.doe@company.com
    This tag helps with resource management and accountability.
    """,
    
    # Network Configuration
    'vpc_id': """
    **VPC ID**: The ID of the existing VPC where FortiGate will be deployed.
    
    Format: vpc-xxxxxxxxxxxxxxxxx
    The VPC must already exist and have appropriate CIDR blocks configured.
    """,
    
    'availability_zones': """
    **Availability Zones**: Two AZs for high availability deployment.
    
    Example: us-east-1a, us-east-1b
    FortiGate instances will be deployed across these AZs for redundancy.
    Each AZ must have the required subnets configured.
    """,
    
    'subnet_ids': """
    **Subnet IDs**: Eight subnet IDs for the FortiGate HA deployment.
    
    Required subnets (4 per AZ):
    1. Public subnet (for internet-facing traffic)
    2. Private subnet (for internal traffic)
    3. HA sync subnet (for HA synchronization)
    4. Management subnet (for administrative access)
    
    Format: subnet-xxxxxxxxxxxxxxxxx
    """,
    
    'management_cidr': """
    **Management CIDR**: IP address range allowed to access FortiGate management interface.
    
    Format: x.x.x.x/x (e.g., 10.0.0.0/8, 203.0.113.0/24)
    
    Security best practice: Restrict this to your organization's IP ranges only.
    Avoid using 0.0.0.0/0 (all IPs) in production environments.
    """,
    
    # ENI Configuration
    'eni_ids': """
    **ENI IDs**: Pre-created Elastic Network Interface IDs for FortiGate instances.
    
    Eight ENIs are required (4 per instance):
    - Primary Instance: port1, port2, port3, port4
    - Backup Instance: port1, port2, port3, port4
    
    Format: eni-xxxxxxxxxxxxxxxxx
    
    ENIs must be created in advance using the create-enis.py script or manually.
    They must be in the correct subnets and availability zones.
    """,
    
    # EIP Configuration
    'allocate_eips': """
    **Allocate EIPs**: Whether to allocate new Elastic IP addresses.
    
    - If enabled: New EIPs will be allocated and associated with FortiGate instances
    - If disabled: You must provide existing EIP allocation IDs
    
    EIPs provide static public IP addresses for internet connectivity.
    """,
    
    'eip_allocation_ids': """
    **EIP Allocation IDs**: Existing Elastic IP allocation IDs to use.
    
    Format: eipalloc-xxxxxxxxxxxxxxxxx
    
    Required when "Allocate EIPs" is disabled. Provide allocation IDs for:
    - Primary instance public interface
    - Backup instance public interface (if applicable)
    """,
    
    'enable_eip_failover': """
    **Enable EIP Failover**: Automatic EIP reassignment during HA failover.
    
    When enabled:
    - EIPs automatically move to the active FortiGate during failover
    - Requires Lambda function and IAM roles (deployed automatically)
    - Provides seamless failover with no IP address changes
    
    Recommended for production deployments requiring high availability.
    """,
    
    # FortiGate Configuration
    'ami_id': """
    **AMI ID**: The Amazon Machine Image ID for FortiGate.
    
    Format: ami-xxxxxxxxxxxxxxxxx
    
    Use the AMI Discovery page to find the appropriate AMI for your:
    - FortiGate version (e.g., 7.4.1, 7.2.5)
    - Licensing model (BYOL, OnDemand)
    - Region
    
    Ensure the AMI matches your licensing and version requirements.
    """,
    
    'instance_type': """
    **Instance Type**: EC2 instance type for FortiGate instances.
    
    Recommended types:
    - c5.xlarge: Good balance of performance and cost (4 vCPU, 8 GB RAM)
    - c5.2xlarge: Higher performance (8 vCPU, 16 GB RAM)
    - c5n.xlarge: Network-optimized (4 vCPU, 10.5 GB RAM, 25 Gbps network)
    
    Consider your throughput requirements when selecting instance type.
    Larger instances support higher network throughput.
    """,
    
    'key_pair_name': """
    **Key Pair Name**: EC2 key pair for SSH access to FortiGate instances.
    
    The key pair must already exist in the selected AWS region.
    You'll need the private key file (.pem) to SSH into the instances.
    
    Used for emergency access and troubleshooting.
    """,
    
    'admin_password': """
    **Admin Password**: Password for the FortiGate admin user.
    
    Requirements:
    - Minimum 8 characters
    - Mix of uppercase, lowercase, numbers, and special characters recommended
    
    This password is used to log into the FortiGate web interface and CLI.
    Store securely - it provides full administrative access.
    """,
    
    'ha_password': """
    **HA Password**: Password for HA synchronization between FortiGate instances.
    
    Requirements:
    - Minimum 8 characters
    - Must match on both FortiGate instances
    
    Used to authenticate HA cluster members. Keep this secure and different
    from the admin password.
    """,
    
    'primary_hostname': """
    **Primary Hostname**: Hostname for the primary FortiGate instance.
    
    Example: fortigate-primary, fgt-prod-01
    
    This hostname appears in the FortiGate CLI prompt and system information.
    Use a descriptive name that identifies the instance role and environment.
    """,
    
    'backup_hostname': """
    **Backup Hostname**: Hostname for the backup FortiGate instance.
    
    Example: fortigate-backup, fgt-prod-02
    
    This hostname appears in the FortiGate CLI prompt and system information.
    Should complement the primary hostname for easy identification.
    """,
    
    # Transit Gateway Configuration
    'create_new_tgw': """
    **Create New Transit Gateway**: Whether to create a new AWS Transit Gateway.
    
    Transit Gateway enables connectivity between:
    - FortiGate VPC and spoke VPCs
    - Multiple VPCs through a central hub
    - On-premises networks via VPN or Direct Connect
    
    - If enabled: A new Transit Gateway will be created
    - If disabled: Provide an existing Transit Gateway ID
    """,
    
    'existing_tgw_id': """
    **Existing Transit Gateway ID**: ID of an existing Transit Gateway to use.
    
    Format: tgw-xxxxxxxxxxxxxxxxx
    
    Required when "Create New Transit Gateway" is disabled.
    The Transit Gateway must be in the same region and accessible from your VPC.
    """,
    
    'tgw_bgp_asn': """
    **Transit Gateway BGP ASN**: BGP Autonomous System Number for the Transit Gateway.
    
    Default: 64512 (private ASN range: 64512-65534)
    
    **Note**: Reserved for future use. Current implementation uses static routing.
    Choose a unique ASN that doesn't conflict with your existing network.
    """,
    
    'fortigate_bgp_asn': """
    **FortiGate BGP ASN**: BGP Autonomous System Number for FortiGate instances.
    
    Default: 65000 (private ASN range: 64512-65534)
    
    **Note**: Reserved for future use. Current implementation uses static routing with:
    - Default route (0.0.0.0/0) to Internet
    - RFC 1918 routes to Transit Gateway
    """,
    
    'spoke_vpc_cidrs': """
    **Spoke VPC CIDRs**: CIDR blocks of spoke VPCs that will route through FortiGate.
    
    Format: Comma-separated list (e.g., 10.1.0.0/16, 10.2.0.0/16)
    
    These networks are routed through FortiGate for inspection via static routes.
    FortiGate will inspect and secure traffic to/from these networks.
    """,
    
    # Monitoring Configuration
    'enable_flow_logs': """
    **Enable Flow Logs**: Enable VPC Flow Logs for network traffic analysis.
    
    Flow Logs capture information about IP traffic:
    - Source and destination IPs
    - Ports and protocols
    - Packet and byte counts
    - Accept/reject decisions
    
    Useful for security analysis, troubleshooting, and compliance.
    Logs are stored in CloudWatch Logs.
    """,
    
    'flow_logs_retention_days': """
    **Flow Logs Retention**: Number of days to retain flow logs in CloudWatch.
    
    Options: 1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365, 400, 545, 731, 1827, 3653
    
    Longer retention enables historical analysis but increases storage costs.
    Consider your compliance requirements and budget.
    """,
    
    'enable_detailed_monitoring': """
    **Enable Detailed Monitoring**: Enable detailed CloudWatch monitoring for EC2 instances.
    
    Standard monitoring: 5-minute intervals (free)
    Detailed monitoring: 1-minute intervals (additional cost)
    
    Detailed monitoring provides:
    - Faster detection of issues
    - More granular performance data
    - Better auto-scaling responsiveness
    
    Recommended for production environments.
    """,
    
    # Backend Configuration
    'backend_type': """
    **Backend Type**: Terraform state backend storage location.
    
    Options:
    - **local**: State stored locally (default, simple but not recommended for teams)
    - **s3**: State stored in S3 bucket (recommended for production and teams)
    
    S3 backend provides:
    - State locking (prevents concurrent modifications)
    - State versioning (enables rollback)
    - Team collaboration (shared state)
    - Encryption at rest
    """,
    
    's3_bucket': """
    **S3 Bucket**: S3 bucket name for Terraform state storage.
    
    The bucket must:
    - Already exist in your AWS account
    - Be in the same region as your deployment
    - Have versioning enabled (recommended)
    - Have encryption enabled (recommended)
    
    Example: my-terraform-state-bucket
    """,
    
    's3_key': """
    **S3 Key**: S3 object key (path) for the Terraform state file.
    
    Example: fortigate/prod/terraform.tfstate
    
    Use a descriptive path that identifies:
    - Project/application
    - Environment
    - Component
    
    This allows multiple deployments to share the same bucket.
    """,
    
    's3_region': """
    **S3 Region**: AWS region where the S3 bucket is located.
    
    Should match your deployment region for optimal performance.
    The bucket must exist in this region.
    """,
    
    'dynamodb_table': """
    **DynamoDB Table**: DynamoDB table name for Terraform state locking.
    
    The table must:
    - Already exist in your AWS account
    - Have a primary key named "LockID" (String type)
    - Be in the same region as your S3 bucket
    
    State locking prevents concurrent Terraform operations that could corrupt state.
    Essential for team environments.
    
    Example: terraform-state-lock
    """,
    
    # Licensing Configuration
    'licensing_model': """
    **Licensing Model**: FortiGate licensing model.
    
    Options:
    - **BYOL** (Bring Your Own License): Use existing FortiGate licenses
      - Lower hourly cost (EC2 only)
      - Requires license files or Flex VM tokens
      - Best for long-term deployments
    
    - **OnDemand** (Pay-as-you-go): Hourly licensing included
      - Higher hourly cost
      - No upfront license purchase
      - Best for short-term or variable workloads
    
    - **Reserved**: Commit to 1 or 3 years for discounted rates
      - Significant cost savings (30-55% off OnDemand)
      - Requires upfront commitment
      - Best for stable, long-term deployments
    """,
    
    'license_source': """
    **License Source**: Where BYOL license files are stored.
    
    Options:
    - **s3**: License files stored in S3 bucket
    - **secrets_manager**: License content stored in AWS Secrets Manager
    
    S3 is simpler for file-based licenses.
    Secrets Manager provides better security and access control.
    """,
    
    'license_s3_bucket': """
    **License S3 Bucket**: S3 bucket containing FortiGate license files.
    
    The bucket must contain:
    - primary_license.lic: License file for primary instance
    - backup_license.lic: License file for backup instance
    
    Bucket must be accessible from the FortiGate instances (IAM role permissions).
    """,
    
    'license_secret_names': """
    **License Secret Names**: AWS Secrets Manager secret names for licenses.
    
    Provide two secret names:
    - Primary instance license secret
    - Backup instance license secret
    
    Each secret should contain the license file content as plain text.
    Secrets must be in the same region as the deployment.
    """,
}


def get_help_text(parameter_key: str) -> str:
    """
    Get help text for a parameter.
    
    Args:
        parameter_key: Parameter identifier
    
    Returns:
        Help text string, or empty string if not found
    
    Requirements:
        - Requirements 1.12, 11.11: Help text availability
    """
    return HELP_TEXT.get(parameter_key, "")


def render_parameter_with_help(label: str, parameter_key: str, 
                               widget_type: str = "text_input", **kwargs):
    """
    Render a parameter input with integrated help text.
    
    Args:
        label: Parameter label
        parameter_key: Key for help text lookup
        widget_type: Streamlit widget type (text_input, number_input, selectbox, etc.)
        **kwargs: Additional arguments passed to the widget
    
    Returns:
        Widget value
    
    Requirements:
        - Requirements 1.12, 11.11: Help text integration
    """
    # Get help text
    help_text = get_help_text(parameter_key)
    
    # Render widget with help
    if widget_type == "text_input":
        return st.text_input(label, help=help_text, **kwargs)
    elif widget_type == "number_input":
        return st.number_input(label, help=help_text, **kwargs)
    elif widget_type == "selectbox":
        return st.selectbox(label, help=help_text, **kwargs)
    elif widget_type == "checkbox":
        return st.checkbox(label, help=help_text, **kwargs)
    elif widget_type == "text_area":
        return st.text_area(label, help=help_text, **kwargs)
    elif widget_type == "multiselect":
        return st.multiselect(label, help=help_text, **kwargs)
    else:
        st.warning(f"Unknown widget type: {widget_type}")
        return None


# ============================================================================
# REUSABLE UI COMPONENTS
# ============================================================================

def render_parameter_section(title: str, description: str = "", 
                            help_text: str = "", required: bool = False):
    """
    Render a parameter section header with optional description and help text.
    
    Args:
        title: Section title
        description: Optional description text
        help_text: Optional help text (shown as info box)
        required: If True, shows required indicator
    
    Requirements:
        - Requirements 11.8, 11.9: Consistent UI components
    """
    # Render title with required indicator
    if required:
        st.markdown(f'<h3 class="section-header">{title} <span class="required-field">*</span></h3>', 
                   unsafe_allow_html=True)
    else:
        st.markdown(f'<h3 class="section-header">{title}</h3>', unsafe_allow_html=True)
    
    # Render description if provided
    if description:
        st.markdown(description)
    
    # Render help text if provided
    if help_text:
        with st.expander("ℹ️ Help"):
            st.info(help_text)


def render_validation_status(validation_results: Dict[str, Tuple[bool, str]]):
    """
    Render validation status for multiple resources.
    
    Args:
        validation_results: Dict mapping resource name to (success, message) tuple
    
    Requirements:
        - Requirements 11.9: Validation status display
    """
    st.markdown('<h3 class="section-header">Validation Results</h3>', unsafe_allow_html=True)
    
    all_valid = all(result[0] for result in validation_results.values())
    
    if all_valid:
        st.success("✅ All validations passed")
    else:
        st.error("❌ Some validations failed")
    
    # Show details in expandable section
    with st.expander("View Details"):
        for resource, (success, message) in validation_results.items():
            if success:
                st.markdown(f"✅ **{resource}**: {message}")
            else:
                st.markdown(f"❌ **{resource}**: {message}")


def render_progress_bar(progress: float, message: str = ""):
    """
    Render a progress bar with optional message.
    
    Args:
        progress: Progress value from 0.0 to 1.0
        message: Optional progress message
    
    Requirements:
        - Requirements 11.10: Progress tracking display
    """
    if message:
        st.text(message)
    st.progress(progress)


def render_log_viewer(logs: List[str], title: str = "Deployment Logs", 
                     max_lines: int = 100):
    """
    Render a log viewer with scrollable output.
    
    Args:
        logs: List of log messages
        title: Log viewer title
        max_lines: Maximum number of lines to display
    
    Requirements:
        - Requirements 11.10: Log display
    """
    st.markdown(f'<h3 class="section-header">{title}</h3>', unsafe_allow_html=True)
    
    # Show only the last max_lines
    display_logs = logs[-max_lines:] if len(logs) > max_lines else logs
    
    # Create a scrollable text area
    log_text = "\n".join(display_logs)
    st.text_area(
        "Logs",
        value=log_text,
        height=400,
        disabled=True,
        label_visibility="collapsed"
    )
    
    # Show line count
    if len(logs) > max_lines:
        st.caption(f"Showing last {max_lines} of {len(logs)} lines")
    else:
        st.caption(f"Total lines: {len(logs)}")


def render_error_message(message: str, details: Optional[List[str]] = None):
    """
    Render an error message with optional details.
    
    Args:
        message: Main error message
        details: Optional list of detailed error messages
    
    Requirements:
        - Requirements 11.8: Error message display
    """
    st.markdown(f'<div class="error-message">❌ {message}</div>', unsafe_allow_html=True)
    
    if details:
        with st.expander("View Error Details"):
            for detail in details:
                st.markdown(f"• {detail}")


def render_success_message(message: str, details: Optional[Dict[str, Any]] = None):
    """
    Render a success message with optional details.
    
    Args:
        message: Main success message
        details: Optional dictionary of additional details
    
    Requirements:
        - Requirements 11.8: Success message display
    """
    st.markdown(f'<div class="success-message">✅ {message}</div>', unsafe_allow_html=True)
    
    if details:
        with st.expander("View Details"):
            for key, value in details.items():
                st.markdown(f"**{key}**: {value}")


def render_info_box(message: str, title: str = "Information"):
    """
    Render an information box.
    
    Args:
        message: Information message
        title: Box title
    
    Requirements:
        - Requirements 11.8: Information display
    """
    st.markdown(f'<div class="info-box"><strong>{title}</strong><br/>{message}</div>', 
               unsafe_allow_html=True)


def render_warning_box(message: str, title: str = "Warning"):
    """
    Render a warning box.
    
    Args:
        message: Warning message
        title: Box title
    
    Requirements:
        - Requirements 11.8: Warning display
    """
    st.markdown(f'<div class="warning-message"><strong>{title}</strong><br/>{message}</div>', 
               unsafe_allow_html=True)


def render_metric_card(label: str, value: str, delta: Optional[str] = None):
    """
    Render a metric card.
    
    Args:
        label: Metric label
        value: Metric value
        delta: Optional delta/change value
    
    Requirements:
        - Requirements 11.9: Metric display
    """
    if delta:
        st.metric(label=label, value=value, delta=delta)
    else:
        st.metric(label=label, value=value)


# ============================================================================
# PAGE RENDERING FUNCTIONS (Placeholders)
# ============================================================================

def render_home_page():
    """Render the home page"""
    st.markdown('<h2 class="section-header">Welcome to FortiGate AWS HA Deployment</h2>', unsafe_allow_html=True)
    
    st.markdown("""
    This enhanced web application provides complete feature parity with the deploy.py CLI script,
    offering an intuitive interface for deploying and managing FortiGate HA pairs on AWS.
    """)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div class="metric-card">
            <h3>🛡️ High Availability</h3>
            <p>Deploy FortiGate firewalls in active-passive HA configuration across multiple 
            AWS Availability Zones for maximum uptime and reliability.</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="metric-card">
            <h3>🔍 Auto Discovery</h3>
            <p>Automatically discover the latest FortiGate AMIs from AWS Marketplace with 
            support for BYOL, OnDemand, and Reserved licensing models.</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div class="metric-card">
            <h3>💰 Cost Optimization</h3>
            <p>Get intelligent cost analysis and licensing recommendations based on your 
            deployment duration and usage patterns.</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown('<h3 class="section-header">Key Features</h3>', unsafe_allow_html=True)
    
    features = [
        "✅ Support for all 60+ deployment parameters",
        "✅ ENI configuration with 8 pre-created network interfaces",
        "✅ EIP failover configuration for internet routing",
        "✅ Configuration import/export (YAML/JSON)",
        "✅ Real AWS API validation",
        "✅ AMI discovery and licensing management",
        "✅ Terraform backend configuration (local/S3)",
        "✅ Plan-only mode for review before deployment",
        "✅ Real-time deployment tracking",
        "✅ Cost analysis and comparison"
    ]
    
    col1, col2 = st.columns(2)
    
    with col1:
        for feature in features[:5]:
            st.markdown(feature)
    
    with col2:
        for feature in features[5:]:
            st.markdown(feature)
    
    st.markdown('<h3 class="section-header">Getting Started</h3>', unsafe_allow_html=True)
    
    st.markdown("""
    1. **Configure** your deployment parameters in the Configuration page
    2. **Discover** the appropriate FortiGate AMI for your needs
    3. **Configure** licensing (BYOL, OnDemand, or Reserved)
    4. **Analyze** costs and select the optimal licensing model
    5. **Deploy** your FortiGate HA pair with real-time tracking
    """)


def render_configuration_page():
    """
    Render the configuration page with all deployment parameters.
    
    This page collects all deployment parameters organized into logical sections:
    - AWS Configuration (region, credentials, tags)
    - Network Configuration (VPC, subnets, ENIs, EIPs)
    - FortiGate Configuration (AMI, instance type, passwords)
    - Transit Gateway Configuration
    - Monitoring Configuration
    - Backend Configuration
    
    Requirements:
        - Requirement 1.1: Accept all AWS configuration parameters
        - Requirement 1.2: Accept all network configuration parameters
        - Requirement 1.3: Accept all 8 ENI IDs
        - Requirement 1.4: Accept EIP configuration
        - Requirement 1.5: Accept all FortiGate configuration parameters
        - Requirement 1.8: Accept Transit Gateway configuration
        - Requirement 1.9: Accept monitoring configuration
        - Requirement 1.10: Accept backend configuration
        - Requirement 1.11: Accept environment and owner tags
        - Requirement 1.12: Provide context-sensitive help for each parameter
    """
    st.markdown('<h2 class="section-header">⚙️ Deployment Configuration</h2>', unsafe_allow_html=True)
    
    # Initialize session state
    initialize_session_state()
    
    # Get current configuration if exists
    current_config = get_config()
    
    # Configuration import/export section
    st.markdown('<h3 class="section-header">📁 Configuration Management</h3>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        uploaded_file = st.file_uploader(
            "Import Configuration",
            type=['yaml', 'yml', 'json'],
            help="Upload a YAML or JSON configuration file to load all parameters"
        )
        
        if uploaded_file is not None:
            try:
                file_content = uploaded_file.read().decode('utf-8')
                config_manager = ConfigurationManager()
                
                if uploaded_file.name.endswith(('.yaml', '.yml')):
                    imported_config = config_manager.import_yaml(file_content)
                else:
                    imported_config = config_manager.import_json(file_content)
                
                set_config(imported_config)
                st.success(f"✅ Configuration imported from {uploaded_file.name}")
                st.rerun()
            except Exception as e:
                render_error_message(f"Failed to import configuration: {str(e)}")
    
    with col2:
        if current_config:
            config_manager = ConfigurationManager()
            yaml_content = config_manager.export_yaml(current_config, redact_sensitive=True)
            st.download_button(
                label="Export YAML",
                data=yaml_content,
                file_name=f"fortigate-config-{datetime.now().strftime('%Y%m%d-%H%M%S')}.yaml",
                mime="text/yaml"
            )
    
    with col3:
        if current_config:
            config_manager = ConfigurationManager()
            json_content = config_manager.export_json(current_config, redact_sensitive=True)
            st.download_button(
                label="Export JSON",
                data=json_content,
                file_name=f"fortigate-config-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json",
                mime="application/json"
            )
    
    st.markdown("---")
    
    # ========================================================================
    # AWS CONFIGURATION SECTION
    # ========================================================================
    
    render_parameter_section(
        "☁️ AWS Configuration",
        description="Configure AWS credentials, region, and resource tags.",
        required=True
    )
    
    # Get current AWS config values if they exist
    current_aws = current_config.aws if current_config else None
    
    # Region selector
    aws_regions = [
        'us-east-1', 'us-east-2', 'us-west-1', 'us-west-2',
        'eu-west-1', 'eu-west-2', 'eu-west-3', 'eu-central-1',
        'ap-southeast-1', 'ap-southeast-2', 'ap-northeast-1', 'ap-northeast-2',
        'ap-south-1', 'sa-east-1', 'ca-central-1'
    ]
    
    default_region_index = 0
    if current_aws and current_aws.region in aws_regions:
        default_region_index = aws_regions.index(current_aws.region)
    
    aws_region = render_parameter_with_help(
        "AWS Region",
        "aws_region",
        widget_type="selectbox",
        options=aws_regions,
        index=default_region_index
    )
    
    # AWS Profile input
    aws_profile = render_parameter_with_help(
        "AWS Profile (optional)",
        "aws_profile",
        widget_type="text_input",
        value=current_aws.profile if current_aws and current_aws.profile else "",
        placeholder="default"
    )
    
    # Credential method selection
    st.markdown("**Authentication Method**")
    use_access_keys = st.checkbox(
        "Use Access Keys (instead of profile/IAM role)",
        value=bool(current_aws and current_aws.access_key_id),
        help="Enable this to provide AWS access keys directly. Leave unchecked to use AWS profile or IAM role."
    )
    
    # Conditional access key inputs
    aws_access_key_id = None
    aws_secret_access_key = None
    
    if use_access_keys:
        col1, col2 = st.columns(2)
        
        with col1:
            aws_access_key_id = render_parameter_with_help(
                "AWS Access Key ID",
                "aws_access_key_id",
                widget_type="text_input",
                value=current_aws.access_key_id if current_aws and current_aws.access_key_id else "",
                type="password",
                placeholder="AKIAIOSFODNN7EXAMPLE"
            )
        
        with col2:
            aws_secret_access_key = render_parameter_with_help(
                "AWS Secret Access Key",
                "aws_secret_access_key",
                widget_type="text_input",
                value=current_aws.secret_access_key if current_aws and current_aws.secret_access_key else "",
                type="password",
                placeholder="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
            )
    
    # Environment and Owner tags
    st.markdown("**Resource Tags**")
    
    col1, col2 = st.columns(2)
    
    with col1:
        environment = render_parameter_with_help(
            "Environment",
            "environment",
            widget_type="text_input",
            value=current_config.environment if current_config else "prod",
            placeholder="prod"
        )
    
    with col2:
        owner_tag = render_parameter_with_help(
            "Owner Tag",
            "owner_tag",
            widget_type="text_input",
            value=current_config.owner_tag if current_config else "NetworkTeam",
            placeholder="NetworkTeam"
        )
    
    st.markdown("---")
    
    # ========================================================================
    # NETWORK CONFIGURATION SECTION
    # ========================================================================
    
    render_parameter_section(
        "🌐 Network Configuration",
        description="Configure VPC, availability zones, subnets, and management access.",
        required=True
    )
    
    # Get current network config values if they exist
    current_network = current_config.network if current_config else None
    
    # VPC ID input
    vpc_id = render_parameter_with_help(
        "VPC ID",
        "vpc_id",
        widget_type="text_input",
        value=current_network.vpc_id if current_network else "",
        placeholder="vpc-0123456789abcdef0"
    )
    
    # Availability Zone inputs
    st.markdown("**Availability Zones**")
    col1, col2 = st.columns(2)
    
    # Extract AZs from list if they exist
    current_az1 = current_network.availability_zones[0] if current_network and current_network.availability_zones else ""
    current_az2 = current_network.availability_zones[1] if current_network and len(current_network.availability_zones) > 1 else ""
    
    with col1:
        availability_zone_1 = render_parameter_with_help(
            "Primary Availability Zone",
            "availability_zone_1",
            widget_type="text_input",
            value=current_az1,
            placeholder="us-east-1a"
        )
    
    with col2:
        availability_zone_2 = render_parameter_with_help(
            "Backup Availability Zone",
            "availability_zone_2",
            widget_type="text_input",
            value=current_az2,
            placeholder="us-east-1b"
        )
    
    # Subnet ID inputs - Primary AZ
    st.markdown(f"**Primary AZ Subnets ({availability_zone_1 or 'Not set'})**")
    col1, col2 = st.columns(2)
    
    with col1:
        public_subnet_1 = render_parameter_with_help(
            "Public Subnet",
            "public_subnet_1",
            widget_type="text_input",
            value=current_network.outside_subnet_primary if current_network else "",
            placeholder="subnet-0123456789abcdef0"
        )
        
        private_subnet_1 = render_parameter_with_help(
            "Private Subnet",
            "private_subnet_1",
            widget_type="text_input",
            value=current_network.inside_subnet_primary if current_network else "",
            placeholder="subnet-0123456789abcdef1"
        )
    
    with col2:
        hasync_subnet_1 = render_parameter_with_help(
            "HA Sync Subnet",
            "hasync_subnet_1",
            widget_type="text_input",
            value=current_network.ha_subnet_primary if current_network else "",
            placeholder="subnet-0123456789abcdef2"
        )
        
        mgmt_subnet_1 = render_parameter_with_help(
            "Management Subnet",
            "mgmt_subnet_1",
            widget_type="text_input",
            value=current_network.mgmt_subnet_primary if current_network else "",
            placeholder="subnet-0123456789abcdef3"
        )
    
    # Subnet ID inputs - Backup AZ
    st.markdown(f"**Backup AZ Subnets ({availability_zone_2 or 'Not set'})**")
    col1, col2 = st.columns(2)
    
    with col1:
        public_subnet_2 = render_parameter_with_help(
            "Public Subnet",
            "public_subnet_2",
            widget_type="text_input",
            value=current_network.outside_subnet_backup if current_network else "",
            placeholder="subnet-0123456789abcdef4"
        )
        
        private_subnet_2 = render_parameter_with_help(
            "Private Subnet",
            "private_subnet_2",
            widget_type="text_input",
            value=current_network.inside_subnet_backup if current_network else "",
            placeholder="subnet-0123456789abcdef5"
        )
    
    with col2:
        hasync_subnet_2 = render_parameter_with_help(
            "HA Sync Subnet",
            "hasync_subnet_2",
            widget_type="text_input",
            value=current_network.ha_subnet_backup if current_network else "",
            placeholder="subnet-0123456789abcdef6"
        )
        
        mgmt_subnet_2 = render_parameter_with_help(
            "Management Subnet",
            "mgmt_subnet_2",
            widget_type="text_input",
            value=current_network.mgmt_subnet_backup if current_network else "",
            placeholder="subnet-0123456789abcdef7"
        )
    
    # Management CIDR input
    st.markdown("**Management Access**")
    current_mgmt_cidr = current_network.mgmt_access_cidrs[0] if current_network and current_network.mgmt_access_cidrs else "0.0.0.0/0"
    mgmt_cidr = render_parameter_with_help(
        "Management CIDR",
        "mgmt_cidr",
        widget_type="text_input",
        value=current_mgmt_cidr,
        placeholder="0.0.0.0/0"
    )
    
    st.markdown("---")
    
    # ========================================================================
    # ENI CONFIGURATION SECTION
    # ========================================================================
    
    render_parameter_section(
        "🔌 ENI Configuration",
        description="Configure Elastic Network Interface (ENI) IDs for FortiGate instances. ENIs must be pre-created in the appropriate subnets.",
        required=True
    )
    
    st.info("ℹ️ ENI IDs must follow the format: eni-xxxxxxxxxxxxxxxxx (17 hexadecimal characters after 'eni-')")
    
    # Helper function to validate ENI ID format
    def validate_eni_id(eni_id: str) -> bool:
        """Validate ENI ID format: eni-xxxxxxxxxxxxxxxxx"""
        if not eni_id:
            return True  # Empty is valid (optional)
        pattern = r'^eni-[0-9a-f]{17}$'
        return bool(re.match(pattern, eni_id))
    
    # Primary Instance ENIs
    st.markdown("**Primary FortiGate Instance ENIs**")
    st.markdown("_Port assignments: Port1=Public/Outside, Port2=Private/Inside, Port3=HA Sync, Port4=Management_")
    
    col1, col2 = st.columns(2)
    
    with col1:
        primary_port1_eni = render_parameter_with_help(
            "Port 1 ENI (Public/Outside)",
            "primary_port1_eni",
            widget_type="text_input",
            value=current_network.primary_outside_eni_id if current_network else "",
            placeholder="eni-0123456789abcdef0"
        )
        
        if primary_port1_eni and not validate_eni_id(primary_port1_eni):
            st.error("❌ Invalid ENI ID format. Expected: eni-xxxxxxxxxxxxxxxxx")
        
        primary_port2_eni = render_parameter_with_help(
            "Port 2 ENI (Private/Inside)",
            "primary_port2_eni",
            widget_type="text_input",
            value=current_network.primary_inside_eni_id if current_network else "",
            placeholder="eni-0123456789abcdef1"
        )
        
        if primary_port2_eni and not validate_eni_id(primary_port2_eni):
            st.error("❌ Invalid ENI ID format. Expected: eni-xxxxxxxxxxxxxxxxx")
    
    with col2:
        primary_port3_eni = render_parameter_with_help(
            "Port 3 ENI (HA Sync)",
            "primary_port3_eni",
            widget_type="text_input",
            value=current_network.primary_ha_eni_id if current_network else "",
            placeholder="eni-0123456789abcdef2"
        )
        
        if primary_port3_eni and not validate_eni_id(primary_port3_eni):
            st.error("❌ Invalid ENI ID format. Expected: eni-xxxxxxxxxxxxxxxxx")
        
        primary_port4_eni = render_parameter_with_help(
            "Port 4 ENI (Management)",
            "primary_port4_eni",
            widget_type="text_input",
            value=current_network.primary_mgmt_eni_id if current_network else "",
            placeholder="eni-0123456789abcdef3"
        )
        
        if primary_port4_eni and not validate_eni_id(primary_port4_eni):
            st.error("❌ Invalid ENI ID format. Expected: eni-xxxxxxxxxxxxxxxxx")
    
    # Backup Instance ENIs
    st.markdown("**Backup FortiGate Instance ENIs**")
    st.markdown("_Port assignments: Port1=Public/Outside, Port2=Private/Inside, Port3=HA Sync, Port4=Management_")
    
    col1, col2 = st.columns(2)
    
    with col1:
        backup_port1_eni = render_parameter_with_help(
            "Port 1 ENI (Public/Outside)",
            "backup_port1_eni",
            widget_type="text_input",
            value=current_network.backup_outside_eni_id if current_network else "",
            placeholder="eni-0123456789abcdef4"
        )
        
        if backup_port1_eni and not validate_eni_id(backup_port1_eni):
            st.error("❌ Invalid ENI ID format. Expected: eni-xxxxxxxxxxxxxxxxx")
        
        backup_port2_eni = render_parameter_with_help(
            "Port 2 ENI (Private/Inside)",
            "backup_port2_eni",
            widget_type="text_input",
            value=current_network.backup_inside_eni_id if current_network else "",
            placeholder="eni-0123456789abcdef5"
        )
        
        if backup_port2_eni and not validate_eni_id(backup_port2_eni):
            st.error("❌ Invalid ENI ID format. Expected: eni-xxxxxxxxxxxxxxxxx")
    
    with col2:
        backup_port3_eni = render_parameter_with_help(
            "Port 3 ENI (HA Sync)",
            "backup_port3_eni",
            widget_type="text_input",
            value=current_network.backup_ha_eni_id if current_network else "",
            placeholder="eni-0123456789abcdef6"
        )
        
        if backup_port3_eni and not validate_eni_id(backup_port3_eni):
            st.error("❌ Invalid ENI ID format. Expected: eni-xxxxxxxxxxxxxxxxx")
        
        backup_port4_eni = render_parameter_with_help(
            "Port 4 ENI (Management)",
            "backup_port4_eni",
            widget_type="text_input",
            value=current_network.backup_mgmt_eni_id if current_network else "",
            placeholder="eni-0123456789abcdef7"
        )
        
        if backup_port4_eni and not validate_eni_id(backup_port4_eni):
            st.error("❌ Invalid ENI ID format. Expected: eni-xxxxxxxxxxxxxxxxx")
    
    st.markdown("---")
    
    # ========================================================================
    # EIP CONFIGURATION SECTION
    # ========================================================================
    
    render_parameter_section(
        "🌍 EIP Configuration",
        description="Configure Elastic IP (EIP) addresses for FortiGate instances. EIPs provide static public IP addresses for high availability.",
        required=True
    )
    
    st.info("ℹ️ EIP Allocation IDs must follow the format: eipalloc-xxxxxxxxxxxxxxxxx (17 hexadecimal characters after 'eipalloc-')")
    
    # Helper function to validate EIP allocation ID format
    def validate_eip_id(eip_id: str) -> bool:
        """Validate EIP allocation ID format: eipalloc-xxxxxxxxxxxxxxxxx"""
        if not eip_id:
            return True  # Empty is valid (optional)
        pattern = r'^eipalloc-[0-9a-f]{17}$'
        return bool(re.match(pattern, eip_id))
    
    # Allocate EIPs checkbox
    allocate_eips = st.checkbox(
        "Allocate new EIPs automatically",
        value=current_network.allocate_eips if current_network else True,
        help="If checked, Terraform will allocate new Elastic IPs automatically. If unchecked, you must provide existing EIP allocation IDs."
    )
    
    # Conditional EIP allocation ID inputs (shown only when allocate_eips is False)
    primary_eip_id = None
    backup_eip_id = None
    
    if not allocate_eips:
        st.markdown("**Existing EIP Allocation IDs**")
        st.markdown("_Provide pre-allocated EIP allocation IDs for the FortiGate instances_")
        
        col1, col2 = st.columns(2)
        
        with col1:
            primary_eip_id = render_parameter_with_help(
                "Primary FortiGate EIP Allocation ID",
                "primary_eip_id",
                widget_type="text_input",
                value=current_network.primary_outside_eip_id if current_network else "",
                placeholder="eipalloc-0123456789abcdef0"
            )
            
            if primary_eip_id and not validate_eip_id(primary_eip_id):
                st.error("❌ Invalid EIP allocation ID format. Expected: eipalloc-xxxxxxxxxxxxxxxxx")
        
        with col2:
            backup_eip_id = render_parameter_with_help(
                "Backup FortiGate EIP Allocation ID",
                "backup_eip_id",
                widget_type="text_input",
                value=current_network.backup_outside_eip_id if current_network else "",
                placeholder="eipalloc-0123456789abcdef1"
            )
            
            if backup_eip_id and not validate_eip_id(backup_eip_id):
                st.error("❌ Invalid EIP allocation ID format. Expected: eipalloc-xxxxxxxxxxxxxxxxx")
    
    # Enable EIP failover checkbox
    enable_eip_failover = st.checkbox(
        "Enable EIP Failover",
        value=current_network.enable_eip_failover if current_network else True,
        help="Enable automatic EIP failover between primary and backup FortiGate instances during HA events."
    )
    
    st.markdown("---")
    
    # ========================================================================
    # FORTIGATE CONFIGURATION SECTION
    # ========================================================================
    
    render_parameter_section(
        "🛡️ FortiGate Configuration",
        description="Configure FortiGate instance settings including AMI, instance type, credentials, and hostnames.",
        required=True
    )
    
    # Get current FortiGate config values if they exist
    current_fortigate = current_config.fortigate if current_config else None
    
    # AMI ID input
    st.markdown("**AMI Configuration**")
    ami_id = render_parameter_with_help(
        "FortiGate AMI ID",
        "ami_id",
        widget_type="text_input",
        value=current_fortigate.ami_id if current_fortigate and current_fortigate.ami_id else "",
        placeholder="ami-0123456789abcdef0"
    )
    
    # Helper function to validate AMI ID format
    def validate_ami_id(ami_id_val: str) -> bool:
        """Validate AMI ID format: ami-xxxxxxxxxxxxxxxxx"""
        if not ami_id_val:
            return True  # Empty is valid (optional)
        pattern = r'^ami-[0-9a-f]{17}$'
        return bool(re.match(pattern, ami_id_val))
    
    if ami_id and not validate_ami_id(ami_id):
        st.error("❌ Invalid AMI ID format. Expected: ami-xxxxxxxxxxxxxxxxx (17 hexadecimal characters)")
    
    st.info("💡 Tip: Use the AMI Discovery page to automatically find the latest FortiGate AMI for your region.")
    
    # Instance Type selector
    st.markdown("**Instance Configuration**")
    
    instance_types = [
        'c5.xlarge', 'c5.2xlarge', 'c5.4xlarge', 'c5.9xlarge',
        'c5n.xlarge', 'c5n.2xlarge', 'c5n.4xlarge', 'c5n.9xlarge',
        'c6i.xlarge', 'c6i.2xlarge', 'c6i.4xlarge', 'c6i.8xlarge',
        'm5.xlarge', 'm5.2xlarge', 'm5.4xlarge', 'm5.8xlarge'
    ]
    
    default_instance_index = 0
    if current_fortigate and current_fortigate.instance_type in instance_types:
        default_instance_index = instance_types.index(current_fortigate.instance_type)
    
    instance_type = render_parameter_with_help(
        "Instance Type",
        "instance_type",
        widget_type="selectbox",
        options=instance_types,
        index=default_instance_index
    )
    
    # Key Pair Name input
    key_pair_name = render_parameter_with_help(
        "EC2 Key Pair Name",
        "key_pair_name",
        widget_type="text_input",
        value=current_fortigate.key_pair_name if current_fortigate else "",
        placeholder="my-keypair"
    )
    
    # Password inputs
    st.markdown("**FortiGate Credentials**")
    st.markdown("_Passwords must be at least 8 characters long and contain uppercase, lowercase, and numbers_")
    
    col1, col2 = st.columns(2)
    
    with col1:
        admin_password = render_parameter_with_help(
            "Admin Password",
            "admin_password",
            widget_type="text_input",
            value=current_fortigate.admin_password if current_fortigate else "",
            type="password",
            placeholder="Enter admin password"
        )
        
        # Password strength validation
        if admin_password:
            if len(admin_password) < 8:
                st.warning("⚠️ Password should be at least 8 characters long")
            elif not (any(c.isupper() for c in admin_password) and 
                     any(c.islower() for c in admin_password) and 
                     any(c.isdigit() for c in admin_password)):
                st.warning("⚠️ Password should contain uppercase, lowercase, and numbers")
    
    with col2:
        ha_password = render_parameter_with_help(
            "HA Password",
            "ha_password",
            widget_type="text_input",
            value=current_fortigate.ha_password if current_fortigate else "",
            type="password",
            placeholder="Enter HA password"
        )
        
        # Password strength validation
        if ha_password:
            if len(ha_password) < 8:
                st.warning("⚠️ Password should be at least 8 characters long")
            elif not (any(c.isupper() for c in ha_password) and 
                     any(c.islower() for c in ha_password) and 
                     any(c.isdigit() for c in ha_password)):
                st.warning("⚠️ Password should contain uppercase, lowercase, and numbers")
    
    # Hostname inputs
    st.markdown("**Hostnames**")
    
    col1, col2 = st.columns(2)
    
    with col1:
        hostname_primary = render_parameter_with_help(
            "Primary FortiGate Hostname",
            "hostname_primary",
            widget_type="text_input",
            value=current_fortigate.hostname_primary if current_fortigate else "fortigate-primary",
            placeholder="fortigate-primary"
        )
    
    with col2:
        hostname_backup = render_parameter_with_help(
            "Backup FortiGate Hostname",
            "hostname_backup",
            widget_type="text_input",
            value=current_fortigate.hostname_backup if current_fortigate else "fortigate-backup",
            placeholder="fortigate-backup"
        )
    
    st.markdown("---")
    
    # ========================================================================
    # TRANSIT GATEWAY CONFIGURATION SECTION
    # ========================================================================
    
    render_parameter_section(
        "🌐 Transit Gateway Configuration",
        description="Configure AWS Transit Gateway for hub-and-spoke network architecture. Current implementation uses static routing with BGP ASNs reserved for future use.",
        required=False
    )
    
    # Get current Transit Gateway config values if they exist
    current_tgw = current_config.transit_gateway if current_config else None
    
    # Create new TGW checkbox
    create_new_tgw = st.checkbox(
        "Create new Transit Gateway",
        value=current_tgw.create_new if current_tgw else True,
        help="If checked, Terraform will create a new Transit Gateway. If unchecked, you must provide an existing Transit Gateway ID."
    )
    
    # Conditional existing TGW ID input (shown only when create_new_tgw is False)
    existing_tgw_id = None
    
    if not create_new_tgw:
        st.markdown("**Existing Transit Gateway**")
        st.info("ℹ️ Transit Gateway IDs must follow the format: tgw-xxxxxxxxxxxxxxxxx (17 hexadecimal characters after 'tgw-')")
        
        existing_tgw_id = render_parameter_with_help(
            "Transit Gateway ID",
            "existing_tgw_id",
            widget_type="text_input",
            value=current_tgw.transit_gateway_id if current_tgw else "",
            placeholder="tgw-0123456789abcdef0"
        )
        
        # Helper function to validate TGW ID format
        def validate_tgw_id(tgw_id: str) -> bool:
            """Validate Transit Gateway ID format: tgw-xxxxxxxxxxxxxxxxx"""
            if not tgw_id:
                return False  # Required when not creating new
            pattern = r'^tgw-[0-9a-f]{17}$'
            return bool(re.match(pattern, tgw_id))
        
        if existing_tgw_id and not validate_tgw_id(existing_tgw_id):
            st.error("❌ Invalid Transit Gateway ID format. Expected: tgw-xxxxxxxxxxxxxxxxx (17 hexadecimal characters)")
        elif not existing_tgw_id:
            st.warning("⚠️ Transit Gateway ID is required when not creating a new Transit Gateway")
    
    # BGP ASN inputs
    st.markdown("**Routing Configuration**")
    st.info("""
ℹ️ **Current Implementation**: FortiGate uses static routing for Transit Gateway connectivity.

**Static Routes Configured**:
- Default route (0.0.0.0/0) → Internet via outside interface
- RFC 1918 routes (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16) → Transit Gateway via inside interface

**BGP ASNs**: Reserved for future use if dynamic routing is implemented.
""")
    
    col1, col2 = st.columns(2)
    
    with col1:
        fortigate_bgp_asn = render_parameter_with_help(
            "FortiGate BGP ASN",
            "fortigate_bgp_asn",
            widget_type="number_input",
            value=current_tgw.bgp_asn if current_tgw else 65000,
            min_value=64512,
            max_value=65534,
            step=1,
            help="Reserved for future BGP implementation. Current deployment uses static routing."
        )
    
    with col2:
        tgw_bgp_asn = render_parameter_with_help(
            "Transit Gateway BGP ASN",
            "tgw_bgp_asn",
            widget_type="number_input",
            value=current_tgw.transit_gateway_asn if current_tgw else 64512,
            min_value=64512,
            max_value=65534,
            step=1,
            help="Reserved for future BGP implementation. Current deployment uses static routing."
        )
    
    # Spoke VPC CIDRs text area
    st.markdown("**Spoke VPC Configuration**")
    
    # Convert list to comma-separated string for display
    current_spoke_cidrs = ""
    if current_tgw and current_tgw.spoke_vpc_cidrs:
        current_spoke_cidrs = ", ".join(current_tgw.spoke_vpc_cidrs)
    
    spoke_vpc_cidrs_input = render_parameter_with_help(
        "Spoke VPC CIDRs (comma-separated)",
        "spoke_vpc_cidrs",
        widget_type="text_area",
        value=current_spoke_cidrs,
        placeholder="10.1.0.0/16, 10.2.0.0/16, 10.3.0.0/16",
        height=100
    )
    
    st.markdown("---")
    
    # ========================================================================
    # MONITORING CONFIGURATION SECTION
    # ========================================================================
    
    render_parameter_section(
        "📊 Monitoring Configuration",
        description="Configure VPC Flow Logs and CloudWatch monitoring for network traffic analysis and instance metrics.",
        required=False
    )
    
    # Add logging capabilities clarification
    st.info("""
ℹ️ **Logging Capabilities**:

**Enabled by Default**:
- **VPC Flow Logs**: Network traffic metadata → CloudWatch Logs
- **EC2 Detailed Monitoring**: Instance metrics (CPU, network, disk) → CloudWatch Metrics

**FortiGate Application Logs**:
- Available via FortiGate web GUI (System > Log & Report)
- Not automatically sent to CloudWatch (requires additional infrastructure)

**For Centralized FortiGate Logging**: Deploy a syslog forwarder EC2 instance or use FortiAnalyzer.
""")
    
    # Get current Monitoring config values if they exist
    current_monitoring = current_config.monitoring if current_config else None
    
    # Enable Flow Logs checkbox
    enable_flow_logs = st.checkbox(
        "Enable VPC Flow Logs",
        value=current_monitoring.enable_flow_logs if current_monitoring else True,
        help="Enable VPC Flow Logs to capture information about IP traffic going to and from network interfaces in your VPC."
    )
    
    # Log retention selector
    log_retention_options = [1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365, 400, 545, 731, 1827, 3653]
    
    # Find the index of the current value or default to 7 days
    default_retention = current_monitoring.log_retention_days if current_monitoring else 7
    try:
        default_retention_index = log_retention_options.index(default_retention)
    except ValueError:
        # If current value is not in the list, default to 7 days
        default_retention_index = log_retention_options.index(7)
    
    log_retention_days = render_parameter_with_help(
        "Log Retention (days)",
        "flow_logs_retention_days",
        widget_type="selectbox",
        options=log_retention_options,
        index=default_retention_index
    )
    
    # Enable Detailed Monitoring checkbox
    enable_detailed_monitoring = st.checkbox(
        "Enable Detailed CloudWatch Monitoring",
        value=current_monitoring.enable_detailed_monitoring if current_monitoring else False,
        help="Enable detailed CloudWatch monitoring for EC2 instances (1-minute intervals instead of 5-minute intervals)."
    )
    
    st.markdown("---")
    
    # ========================================================================
    # BACKEND CONFIGURATION SECTION
    # ========================================================================
    
    render_parameter_section(
        "💾 Backend Configuration",
        description="Configure Terraform backend for state management. Use S3 backend for team collaboration and state locking.",
        required=False
    )
    
    # Get current Backend config values if they exist
    current_backend = current_config.backend if current_config else None
    
    # Backend type selector
    backend_type_options = ["local", "s3"]
    default_backend_index = 0
    if current_backend and current_backend.backend_type == "s3":
        default_backend_index = 1
    
    backend_type = st.radio(
        "Backend Type",
        options=backend_type_options,
        index=default_backend_index,
        help="Select 'local' to store Terraform state locally, or 's3' to store state in AWS S3 with DynamoDB locking for team collaboration.",
        horizontal=True
    )
    
    # Conditional S3 backend parameters (shown only when backend_type is "s3")
    s3_bucket = None
    s3_key = None
    s3_region = None
    dynamodb_table = None
    encrypt = True
    s3_profile = None
    kms_key_id = None
    
    if backend_type == "s3":
        st.markdown("**S3 Backend Configuration**")
        
        # Bootstrap instructions info box
        st.info("""
        ℹ️ **S3 Backend Setup Instructions**
        
        Before using S3 backend, you need to create the S3 bucket and DynamoDB table:
        
        1. Navigate to the `terraform/bootstrap/` directory
        2. Run `terraform init` to initialize the bootstrap configuration
        3. Run `terraform apply` to create the S3 bucket and DynamoDB table
        4. Note the output values (bucket name and DynamoDB table name)
        5. Use those values in the configuration below
        
        The bootstrap creates:
        - S3 bucket with versioning and encryption enabled
        - DynamoDB table for state locking
        - Proper IAM policies for state management
        """)
        
        # S3 bucket name
        s3_bucket = render_parameter_with_help(
            "S3 Bucket Name",
            "s3_bucket",
            widget_type="text_input",
            value=current_backend.s3_bucket if current_backend else "",
            placeholder="fortigate-terraform-state-bucket"
        )
        
        # S3 key (state file path)
        s3_key = render_parameter_with_help(
            "S3 Key (State File Path)",
            "s3_key",
            widget_type="text_input",
            value=current_backend.s3_key if current_backend else "fortigate-ha/terraform.tfstate",
            placeholder="fortigate-ha/terraform.tfstate"
        )
        
        # S3 region
        col1, col2 = st.columns(2)
        
        with col1:
            s3_region = render_parameter_with_help(
                "S3 Bucket Region",
                "s3_region",
                widget_type="text_input",
                value=current_backend.s3_region if current_backend else aws_region,
                placeholder="us-east-1"
            )
        
        with col2:
            # DynamoDB table name
            dynamodb_table = render_parameter_with_help(
                "DynamoDB Table Name",
                "dynamodb_table",
                widget_type="text_input",
                value=current_backend.dynamodb_table if current_backend else "fortigate-terraform-locks",
                placeholder="fortigate-terraform-locks"
            )
        
        # Encryption settings
        st.markdown("**Encryption Settings**")
        
        col1, col2 = st.columns(2)
        
        with col1:
            encrypt = st.checkbox(
                "Encrypt State File",
                value=current_backend.encrypt if current_backend else True,
                help="Enable server-side encryption for the Terraform state file in S3."
            )
        
        with col2:
            use_kms = st.checkbox(
                "Use KMS Encryption",
                value=bool(current_backend and current_backend.kms_key_id),
                help="Use AWS KMS for state file encryption instead of default S3 encryption."
            )
        
        # Conditional KMS key ID input
        if use_kms:
            kms_key_id = render_parameter_with_help(
                "KMS Key ID or ARN",
                "kms_key_id",
                widget_type="text_input",
                value=current_backend.kms_key_id if current_backend else "",
                placeholder="arn:aws:kms:us-east-1:123456789012:key/12345678-1234-1234-1234-123456789012"
            )
        
        # Optional AWS profile for backend
        st.markdown("**Backend Authentication**")
        
        use_backend_profile = st.checkbox(
            "Use AWS Profile for Backend",
            value=bool(current_backend and current_backend.s3_profile),
            help="Specify a different AWS profile for backend operations (optional)."
        )
        
        if use_backend_profile:
            s3_profile = render_parameter_with_help(
                "Backend AWS Profile",
                "s3_profile",
                widget_type="text_input",
                value=current_backend.s3_profile if current_backend else "default",
                placeholder="default"
            )
    else:
        # Local backend info
        st.info("""
        ℹ️ **Local Backend**
        
        Using local backend will store the Terraform state file (`terraform.tfstate`) in the `terraform/` directory.
        
        **Note:** Local backend is suitable for:
        - Single-user deployments
        - Testing and development
        - Environments where S3 is not available
        
        **Not recommended for:**
        - Team collaboration (no state locking)
        - Production deployments (no state backup)
        - CI/CD pipelines (state not shared)
        """)
    
    st.markdown("---")
    
    # ========================================================================
    # SAVE CONFIGURATION BUTTON
    # ========================================================================
    
    st.markdown('<h3 class="section-header">💾 Save Configuration</h3>', unsafe_allow_html=True)
    
    if st.button("Save Configuration", type="primary"):
        try:
            # Validate required fields
            validation_errors = []
            
            # AWS validation
            if not aws_region:
                validation_errors.append("AWS Region is required")
            
            # Network validation
            if not vpc_id:
                validation_errors.append("VPC ID is required")
            if not availability_zone_1 or not availability_zone_2:
                validation_errors.append("Both Availability Zones are required")
            
            # FortiGate validation
            if not ami_id:
                validation_errors.append("FortiGate AMI ID is required")
            if not instance_type:
                validation_errors.append("Instance Type is required")
            if not key_pair_name:
                validation_errors.append("EC2 Key Pair Name is required")
            if not admin_password:
                validation_errors.append("Admin Password is required")
            if not ha_password:
                validation_errors.append("HA Password is required")
            
            # Backend validation (S3 backend specific)
            if backend_type == "s3":
                if not s3_bucket:
                    validation_errors.append("S3 Bucket Name is required for S3 backend")
                if not s3_key:
                    validation_errors.append("S3 Key (State File Path) is required for S3 backend")
                if not s3_region:
                    validation_errors.append("S3 Bucket Region is required for S3 backend")
                if not dynamodb_table:
                    validation_errors.append("DynamoDB Table Name is required for S3 backend")
            
            # Display validation errors if any
            if validation_errors:
                st.error("❌ Please fix the following errors:")
                for error in validation_errors:
                    st.error(f"  • {error}")
                return
            
            # Create AWS config object
            aws_config = AWSConfig(
                region=aws_region,
                profile=aws_profile if aws_profile else None,
                access_key_id=aws_access_key_id if use_access_keys else None,
                secret_access_key=aws_secret_access_key if use_access_keys else None
            )
            
            # Create Network config object
            network_config = NetworkConfig(
                vpc_id=vpc_id,
                availability_zones=[availability_zone_1, availability_zone_2],
                outside_subnet_primary=public_subnet_1,
                inside_subnet_primary=private_subnet_1,
                ha_subnet_primary=hasync_subnet_1,
                mgmt_subnet_primary=mgmt_subnet_1,
                outside_subnet_backup=public_subnet_2,
                inside_subnet_backup=private_subnet_2,
                ha_subnet_backup=hasync_subnet_2,
                mgmt_subnet_backup=mgmt_subnet_2,
                mgmt_access_cidrs=[mgmt_cidr] if mgmt_cidr else ["0.0.0.0/0"],
                # ENI IDs
                primary_outside_eni_id=primary_port1_eni,
                primary_inside_eni_id=primary_port2_eni,
                primary_ha_eni_id=primary_port3_eni,
                primary_mgmt_eni_id=primary_port4_eni,
                backup_outside_eni_id=backup_port1_eni,
                backup_inside_eni_id=backup_port2_eni,
                backup_ha_eni_id=backup_port3_eni,
                backup_mgmt_eni_id=backup_port4_eni,
                # EIP configuration
                allocate_eips=allocate_eips,
                primary_outside_eip_id=primary_eip_id if not allocate_eips else None,
                backup_outside_eip_id=backup_eip_id if not allocate_eips else None,
                enable_eip_failover=enable_eip_failover
            )
            
            # Create FortiGate config object
            fortigate_config = FortiGateConfig(
                ami_id=ami_id,
                ami_discovery=AMIDiscoveryConfig(
                    enabled=False,
                    version="7.6",
                    license_type="byol",
                    architecture="x86_64"
                ),
                licensing=LicensingConfig(
                    type="BYOL",
                    primary_license_secret=None,
                    backup_license_secret=None,
                    license_s3_bucket=None,
                    primary_license_s3_key=None,
                    backup_license_s3_key=None
                ),
                instance_type=instance_type,
                key_pair_name=key_pair_name,
                admin_password=admin_password,
                ha_password=ha_password,
                hostname_primary=hostname_primary,
                hostname_backup=hostname_backup
            )
            
            # Parse spoke VPC CIDRs from comma-separated string
            spoke_vpc_cidrs_list = []
            if spoke_vpc_cidrs_input:
                spoke_vpc_cidrs_list = [cidr.strip() for cidr in spoke_vpc_cidrs_input.split(',') if cidr.strip()]
            
            # Create Transit Gateway config object
            transit_gateway_config = TransitGatewayConfig(
                create_new=create_new_tgw,
                transit_gateway_id=existing_tgw_id if not create_new_tgw else None,
                bgp_asn=fortigate_bgp_asn,
                transit_gateway_asn=tgw_bgp_asn,
                spoke_vpc_cidrs=spoke_vpc_cidrs_list
            )
            
            # Create Monitoring config object
            monitoring_config = MonitoringConfig(
                enable_flow_logs=enable_flow_logs,
                log_retention_days=log_retention_days,
                enable_detailed_monitoring=enable_detailed_monitoring
            )
            
            # Create Backend config object
            backend_config = BackendConfig(
                backend_type=backend_type,
                s3_bucket=s3_bucket if backend_type == "s3" else None,
                s3_key=s3_key if backend_type == "s3" else None,
                s3_region=s3_region if backend_type == "s3" else None,
                dynamodb_table=dynamodb_table if backend_type == "s3" else None,
                encrypt=encrypt if backend_type == "s3" else True,
                kms_key_id=kms_key_id if backend_type == "s3" and use_kms else None,
                s3_profile=s3_profile if backend_type == "s3" and use_backend_profile else None
            )
            
            # Create or update deployment config
            if current_config:
                # Update existing config
                current_config.aws = aws_config
                current_config.network = network_config
                current_config.fortigate = fortigate_config
                current_config.transit_gateway = transit_gateway_config
                current_config.monitoring = monitoring_config
                current_config.backend = backend_config
                current_config.environment = environment
                current_config.owner_tag = owner_tag
                set_config(current_config)
            else:
                # Create new config
                new_config = DeploymentConfig(
                    aws=aws_config,
                    network=network_config,
                    fortigate=fortigate_config,
                    transit_gateway=transit_gateway_config,
                    monitoring=monitoring_config,
                    backend=backend_config,
                    environment=environment,
                    owner_tag=owner_tag
                )
                set_config(new_config)
            
            render_success_message("Configuration saved successfully!")
            
        except Exception as e:
            render_error_message(f"Failed to save configuration: {str(e)}")
    
    # Show current configuration summary
    if current_config:
        st.markdown('<h3 class="section-header">📋 Current Configuration Summary</h3>', unsafe_allow_html=True)
        
        with st.expander("View Configuration Summary"):
            # Get availability zones from list
            primary_az = current_config.network.availability_zones[0] if current_config.network.availability_zones else 'Not set'
            backup_az = current_config.network.availability_zones[1] if len(current_config.network.availability_zones) > 1 else 'Not set'
            
            # Get management CIDR from list
            mgmt_cidr_display = current_config.network.mgmt_access_cidrs[0] if current_config.network.mgmt_access_cidrs else 'Not set'
            
            st.markdown(f"""
            **AWS Configuration:**
            - Region: {current_config.aws.region}
            - Profile: {current_config.aws.profile or 'Not set'}
            - Using Access Keys: {'Yes' if current_config.aws.access_key_id else 'No'}
            
            **Network Configuration:**
            - VPC ID: {current_config.network.vpc_id or 'Not set'}
            - Primary AZ: {primary_az}
            - Backup AZ: {backup_az}
            - Public Subnets: {current_config.network.outside_subnet_primary or 'Not set'}, {current_config.network.outside_subnet_backup or 'Not set'}
            - Private Subnets: {current_config.network.inside_subnet_primary or 'Not set'}, {current_config.network.inside_subnet_backup or 'Not set'}
            - HA Sync Subnets: {current_config.network.ha_subnet_primary or 'Not set'}, {current_config.network.ha_subnet_backup or 'Not set'}
            - Management Subnets: {current_config.network.mgmt_subnet_primary or 'Not set'}, {current_config.network.mgmt_subnet_backup or 'Not set'}
            - Management CIDR: {mgmt_cidr_display}
            
            **ENI Configuration:**
            - Primary Port 1 (Public): {current_config.network.primary_outside_eni_id or 'Not set'}
            - Primary Port 2 (Private): {current_config.network.primary_inside_eni_id or 'Not set'}
            - Primary Port 3 (HA Sync): {current_config.network.primary_ha_eni_id or 'Not set'}
            - Primary Port 4 (Management): {current_config.network.primary_mgmt_eni_id or 'Not set'}
            - Backup Port 1 (Public): {current_config.network.backup_outside_eni_id or 'Not set'}
            - Backup Port 2 (Private): {current_config.network.backup_inside_eni_id or 'Not set'}
            - Backup Port 3 (HA Sync): {current_config.network.backup_ha_eni_id or 'Not set'}
            - Backup Port 4 (Management): {current_config.network.backup_mgmt_eni_id or 'Not set'}
            
            **EIP Configuration:**
            - Allocate EIPs Automatically: {'Yes' if current_config.network.allocate_eips else 'No'}
            - Primary EIP Allocation ID: {current_config.network.primary_outside_eip_id or 'Auto-allocate' if current_config.network.allocate_eips else 'Not set'}
            - Backup EIP Allocation ID: {current_config.network.backup_outside_eip_id or 'Auto-allocate' if current_config.network.allocate_eips else 'Not set'}
            - Enable EIP Failover: {'Yes' if current_config.network.enable_eip_failover else 'No'}
            
            **FortiGate Configuration:**
            - AMI ID: {current_config.fortigate.ami_id or 'Not set'}
            - Instance Type: {current_config.fortigate.instance_type or 'Not set'}
            - Key Pair Name: {current_config.fortigate.key_pair_name or 'Not set'}
            - Admin Password: {'[SET]' if current_config.fortigate.admin_password else 'Not set'}
            - HA Password: {'[SET]' if current_config.fortigate.ha_password else 'Not set'}
            - Primary Hostname: {current_config.fortigate.hostname_primary or 'Not set'}
            - Backup Hostname: {current_config.fortigate.hostname_backup or 'Not set'}
            
            **Transit Gateway Configuration:**
            - Create New TGW: {'Yes' if current_config.transit_gateway.create_new else 'No'}
            - Transit Gateway ID: {current_config.transit_gateway.transit_gateway_id or ('Will be created' if current_config.transit_gateway.create_new else 'Not set')}
            - FortiGate BGP ASN: {current_config.transit_gateway.bgp_asn}
            - Transit Gateway BGP ASN: {current_config.transit_gateway.transit_gateway_asn}
            - Spoke VPC CIDRs: {', '.join(current_config.transit_gateway.spoke_vpc_cidrs) if current_config.transit_gateway.spoke_vpc_cidrs else 'None'}
            
            **Monitoring Configuration:**
            - Enable Flow Logs: {'Yes' if current_config.monitoring.enable_flow_logs else 'No'}
            - Log Retention: {current_config.monitoring.log_retention_days} days
            - Detailed Monitoring: {'Yes' if current_config.monitoring.enable_detailed_monitoring else 'No'}
            
            **Backend Configuration:**
            - Backend Type: {current_config.backend.backend_type.upper()}
            {f'''- S3 Bucket: {current_config.backend.s3_bucket}
            - S3 Key: {current_config.backend.s3_key}
            - S3 Region: {current_config.backend.s3_region}
            - DynamoDB Table: {current_config.backend.dynamodb_table}
            - Encryption: {'Yes' if current_config.backend.encrypt else 'No'}
            - KMS Key ID: {current_config.backend.kms_key_id or 'Not set'}
            - Backend Profile: {current_config.backend.s3_profile or 'Not set'}''' if current_config.backend.backend_type == 's3' else '- State File: terraform/terraform.tfstate (local)'}
            
            **Tags:**
            - Environment: {current_config.environment}
            - Owner: {current_config.owner_tag}
            """)


def render_ami_discovery_page():
    """
    Render the AMI discovery page.
    
    This page allows users to discover FortiGate AMIs from AWS Marketplace
    by specifying version, license type, and architecture. It displays
    discovered AMI details and provides functionality to auto-populate
    the AMI ID in the configuration.
    
    Requirements:
        - Requirement 4.1: Query AWS Marketplace for FortiGate AMIs
        - Requirement 4.2: Filter by FortiGate version
        - Requirement 4.3: Filter by license type
        - Requirement 4.4: Filter by architecture
        - Requirement 4.5: Display latest matching AMI with metadata
        - Requirement 4.6: Display alternative AMI options
        - Requirement 4.7: Auto-populate AMI ID field
        - Requirement 4.9: List all available FortiGate versions
    """
    st.markdown('<h2 class="section-header">🔍 AMI Discovery</h2>', unsafe_allow_html=True)
    
    st.markdown("""
    Discover FortiGate AMIs from AWS Marketplace by specifying your requirements.
    The system will find the latest matching AMI and display its details.
    """)
    
    # Check if AWS session exists
    if st.session_state.aws_session is None:
        st.warning("⚠️ AWS session not initialized. Please configure AWS credentials in the Configuration page first.")
        if st.button("Go to Configuration Page"):
            st.session_state.current_page = 'configuration'
            st.rerun()
        return
    
    # Task 11.1: Create AMI discovery form
    st.markdown("### Discovery Criteria")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # FortiGate version selector
        version = st.selectbox(
            "FortiGate Version",
            options=["7.6", "7.4", "7.2", "7.0", "6.4"],
            index=0,
            help="Select the FortiGate version to discover. Newer versions include latest features and security updates."
        )
    
    with col2:
        # License type selector
        license_type = st.selectbox(
            "License Type",
            options=["BYOL", "OnDemand", "Reserved"],
            index=0,
            help="""
            - BYOL: Bring Your Own License (requires existing FortiGate license)
            - OnDemand: Pay-as-you-go licensing (billed hourly)
            - Reserved: Reserved instance licensing (requires commitment)
            """
        )
    
    with col3:
        # Architecture selector
        architecture = st.selectbox(
            "Architecture",
            options=["x86_64", "arm64"],
            index=0,
            help="CPU architecture. x86_64 is standard, arm64 (Graviton) offers better price/performance."
        )
    
    # Action buttons
    col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 2])
    
    with col_btn1:
        discover_button = st.button("🔍 Discover AMIs", type="primary", use_container_width=True)
    
    with col_btn2:
        list_versions_button = st.button("📋 List All Versions", use_container_width=True)
    
    # Task 11.4: Add version listing functionality
    if list_versions_button:
        with st.spinner("Retrieving available FortiGate versions..."):
            try:
                # Get AWS config from session state
                config = st.session_state.deployment_config
                if config and config.aws_config:
                    aws_manager = AWSIntegrationManager(config.aws_config)
                    aws_manager.aws_session = st.session_state.aws_session
                    aws_manager.ami_discovery = AMIDiscovery(st.session_state.aws_session)
                    
                    success, versions, message = aws_manager.list_fortigate_versions()
                    
                    if success and versions:
                        st.success(f"✅ {message}")
                        st.markdown("### Available FortiGate Versions")
                        
                        # Display versions in a nice format
                        version_cols = st.columns(5)
                        for idx, ver in enumerate(versions):
                            with version_cols[idx % 5]:
                                st.markdown(f"**{ver}**")
                    else:
                        st.error(f"❌ {message}")
                else:
                    st.error("❌ AWS configuration not found. Please configure AWS settings first.")
            except Exception as e:
                st.error(f"❌ Error listing versions: {str(e)}")
    
    # Task 11.2: Implement AMI discovery execution
    if discover_button:
        with st.spinner(f"Discovering FortiGate {version} {license_type} AMIs..."):
            try:
                # Get AWS config from session state
                config = st.session_state.deployment_config
                if config and config.aws_config:
                    aws_manager = AWSIntegrationManager(config.aws_config)
                    aws_manager.aws_session = st.session_state.aws_session
                    aws_manager.ami_discovery = AMIDiscovery(st.session_state.aws_session)
                    
                    # Call discover_amis
                    success, ami_info, message = aws_manager.discover_amis(version, license_type, architecture)
                    
                    if success and ami_info:
                        # Store result in session state
                        st.session_state.ami_discovery_result = ami_info
                        st.success(f"✅ {message}")
                    else:
                        st.session_state.ami_discovery_result = None
                        st.error(f"❌ {message}")
                        st.info("""
                        **Troubleshooting Tips:**
                        - Verify your AWS credentials have permissions to describe EC2 images
                        - Check if the selected version and license type combination is available in your region
                        - Try a different version or license type
                        """)
                else:
                    st.error("❌ AWS configuration not found. Please configure AWS settings first.")
            except Exception as e:
                st.session_state.ami_discovery_result = None
                st.error(f"❌ Error during AMI discovery: {str(e)}")
    
    # Task 11.3: Display discovery results
    if st.session_state.ami_discovery_result:
        st.markdown("---")
        st.markdown("### 🎯 Discovery Results")
        
        ami_info = st.session_state.ami_discovery_result
        
        # Display latest AMI details in a nice card format
        st.markdown("#### Latest Matching AMI")
        
        col_info1, col_info2 = st.columns([2, 1])
        
        with col_info1:
            st.markdown(f"""
            <div style="background-color: #f0f2f6; padding: 20px; border-radius: 10px; border-left: 5px solid #4CAF50;">
                <h4 style="margin-top: 0;">📦 {ami_info['name']}</h4>
                <p><strong>AMI ID:</strong> <code>{ami_info['id']}</code></p>
                <p><strong>Description:</strong> {ami_info['description']}</p>
                <p><strong>Architecture:</strong> {ami_info['architecture']}</p>
                <p><strong>Creation Date:</strong> {ami_info['creation_date']}</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col_info2:
            st.markdown("#### Actions")
            
            # Auto-populate button
            if st.button("✅ Use This AMI", type="primary", use_container_width=True):
                # Update the AMI ID in the deployment config
                if st.session_state.deployment_config:
                    if st.session_state.deployment_config.fortigate_config:
                        st.session_state.deployment_config.fortigate_config.ami_id = ami_info['id']
                        st.success(f"✅ AMI ID updated to {ami_info['id']}")
                        st.info("💡 Go to the Configuration page to review and save your settings.")
                    else:
                        st.warning("⚠️ FortiGate configuration not initialized. Please configure FortiGate settings first.")
                else:
                    st.warning("⚠️ Deployment configuration not initialized. Please configure settings first.")
            
            # Copy to clipboard helper
            st.markdown(f"""
            <div style="margin-top: 10px;">
                <small>💡 <strong>Tip:</strong> Click "Use This AMI" to automatically populate the AMI ID in your configuration.</small>
            </div>
            """, unsafe_allow_html=True)
        
        # Display alternative AMIs section (placeholder for future enhancement)
        with st.expander("🔄 Alternative AMIs"):
            st.info("""
            **Alternative AMI Discovery**
            
            To find alternative AMIs:
            - Try different versions (e.g., 7.4 instead of 7.6)
            - Try different license types (BYOL, OnDemand, Reserved)
            - Try different architectures (x86_64, arm64)
            
            Each combination may yield different AMIs optimized for specific use cases.
            """)
    
    # Help section
    st.markdown("---")
    with st.expander("ℹ️ Help & Information"):
        st.markdown("""
        ### About AMI Discovery
        
        The AMI Discovery feature helps you find the correct FortiGate Amazon Machine Image (AMI) 
        for your deployment without manually searching AWS Marketplace.
        
        **How it works:**
        1. Select your desired FortiGate version, license type, and architecture
        2. Click "Discover AMIs" to search AWS Marketplace
        3. Review the discovered AMI details
        4. Click "Use This AMI" to auto-populate your configuration
        
        **Version Selection:**
        - **7.6**: Latest version with newest features
        - **7.4**: Stable LTS version (recommended for production)
        - **7.2**: Previous LTS version
        - **7.0**: Older stable version
        - **6.4**: Legacy version
        
        **License Types:**
        - **BYOL**: Bring Your Own License - Use existing FortiGate licenses
        - **OnDemand**: Pay-as-you-go - Hourly billing with no upfront commitment
        - **Reserved**: Reserved Instance - Discounted pricing with commitment
        
        **Architecture:**
        - **x86_64**: Standard Intel/AMD processors (most common)
        - **arm64**: AWS Graviton processors (better price/performance ratio)
        
        **Troubleshooting:**
        - Ensure AWS credentials are configured with EC2 describe permissions
        - Verify the selected region supports the desired FortiGate version
        - Check AWS Marketplace for availability in your region
        """)
    
    # Additional information
    st.markdown("---")
    st.markdown("""
    <div style="background-color: #e3f2fd; padding: 15px; border-radius: 5px; border-left: 4px solid #2196F3;">
        <strong>💡 Pro Tip:</strong> After discovering an AMI, you can validate it in the Configuration page 
        to ensure it's accessible in your AWS account and region.
    </div>
    """, unsafe_allow_html=True)


def render_licensing_page():
    """
    Render the licensing configuration page.
    
    This page allows users to:
    - Select license type (BYOL, OnDemand, Reserved)
    - Configure BYOL license sources (Secrets Manager, S3, or file upload)
    - Test access to license sources
    - View cost implications for different licensing models
    
    Requirements:
        - Requirements 5.1-5.4: License type selection
        - Requirements 5.5-5.7: BYOL configuration
        - Requirements 5.8, 5.10: License validation
        - Requirement 5.9: Cost implications display
    """
    st.markdown('<h2 class="section-header">📄 Licensing Configuration</h2>', unsafe_allow_html=True)
    
    # Initialize session state for licensing if not exists
    if 'licensing_config' not in st.session_state:
        st.session_state.licensing_config = {
            'type': 'BYOL',
            'license_source': 'secrets_manager',
            'primary_license_secret': '',
            'backup_license_secret': '',
            'license_s3_bucket': '',
            'primary_license_s3_key': '',
            'backup_license_s3_key': '',
            'primary_license_file': None,
            'backup_license_file': None
        }
    
    # Task 12.1: Create license type selector
    st.markdown("### License Type Selection")
    st.markdown("Select the FortiGate licensing model for your deployment:")
    
    license_type = st.radio(
        "License Type",
        options=['BYOL', 'OnDemand', 'Reserved'],
        index=['BYOL', 'OnDemand', 'Reserved'].index(st.session_state.licensing_config['type']),
        help="""
        - **BYOL (Bring Your Own License)**: Use your existing FortiGate licenses. Requires license files.
        - **OnDemand**: Pay-as-you-go licensing. No license files needed.
        - **Reserved**: Reserved instance licensing. No license files needed.
        """,
        horizontal=True
    )
    st.session_state.licensing_config['type'] = license_type
    
    # Task 12.2: Implement BYOL configuration
    if license_type == 'BYOL':
        st.markdown("---")
        st.markdown("### BYOL License Configuration")
        st.info("💡 For BYOL deployments, you need to provide FortiGate license files for both primary and backup instances.")
        
        # License source selector
        license_source = st.radio(
            "License Source",
            options=['secrets_manager', 's3', 'file_upload'],
            format_func=lambda x: {
                'secrets_manager': '🔐 AWS Secrets Manager',
                's3': '📦 S3 Bucket',
                'file_upload': '📁 File Upload'
            }[x],
            index=['secrets_manager', 's3', 'file_upload'].index(st.session_state.licensing_config['license_source']),
            help="Choose where your license files are stored or upload them directly",
            horizontal=True
        )
        st.session_state.licensing_config['license_source'] = license_source
        
        # Secrets Manager configuration
        if license_source == 'secrets_manager':
            st.markdown("#### AWS Secrets Manager Configuration")
            col1, col2 = st.columns(2)
            
            with col1:
                primary_secret = st.text_input(
                    "Primary License Secret Name",
                    value=st.session_state.licensing_config['primary_license_secret'],
                    help="Name of the AWS Secrets Manager secret containing the primary FortiGate license",
                    placeholder="fortigate-primary-license"
                )
                st.session_state.licensing_config['primary_license_secret'] = primary_secret
            
            with col2:
                backup_secret = st.text_input(
                    "Backup License Secret Name",
                    value=st.session_state.licensing_config['backup_license_secret'],
                    help="Name of the AWS Secrets Manager secret containing the backup FortiGate license",
                    placeholder="fortigate-backup-license"
                )
                st.session_state.licensing_config['backup_license_secret'] = backup_secret
            
            # Task 12.3: Add license validation - Test Secrets Manager access
            st.markdown("#### Test Secrets Manager Access")
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("🧪 Test Primary Secret Access", disabled=not primary_secret):
                    if 'aws_integration' in st.session_state and st.session_state.aws_integration:
                        with st.spinner("Testing access to primary secret..."):
                            success, message = st.session_state.aws_integration.test_secrets_manager_access(primary_secret)
                            if success:
                                st.success(message)
                            else:
                                st.error(message)
                    else:
                        st.warning("⚠️ Please configure AWS credentials in the Configuration page first")
            
            with col2:
                if st.button("🧪 Test Backup Secret Access", disabled=not backup_secret):
                    if 'aws_integration' in st.session_state and st.session_state.aws_integration:
                        with st.spinner("Testing access to backup secret..."):
                            success, message = st.session_state.aws_integration.test_secrets_manager_access(backup_secret)
                            if success:
                                st.success(message)
                            else:
                                st.error(message)
                    else:
                        st.warning("⚠️ Please configure AWS credentials in the Configuration page first")
        
        # S3 configuration
        elif license_source == 's3':
            st.markdown("#### S3 Bucket Configuration")
            
            s3_bucket = st.text_input(
                "S3 Bucket Name",
                value=st.session_state.licensing_config['license_s3_bucket'],
                help="Name of the S3 bucket containing license files",
                placeholder="my-fortigate-licenses"
            )
            st.session_state.licensing_config['license_s3_bucket'] = s3_bucket
            
            col1, col2 = st.columns(2)
            
            with col1:
                primary_s3_key = st.text_input(
                    "Primary License S3 Key",
                    value=st.session_state.licensing_config['primary_license_s3_key'],
                    help="S3 object key for the primary FortiGate license file",
                    placeholder="licenses/primary.lic"
                )
                st.session_state.licensing_config['primary_license_s3_key'] = primary_s3_key
            
            with col2:
                backup_s3_key = st.text_input(
                    "Backup License S3 Key",
                    value=st.session_state.licensing_config['backup_license_s3_key'],
                    help="S3 object key for the backup FortiGate license file",
                    placeholder="licenses/backup.lic"
                )
                st.session_state.licensing_config['backup_license_s3_key'] = backup_s3_key
            
            # Task 12.3: Add license validation - Test S3 access
            st.markdown("#### Test S3 Access")
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("🧪 Test Primary License Access", disabled=not (s3_bucket and primary_s3_key)):
                    if 'aws_integration' in st.session_state and st.session_state.aws_integration:
                        with st.spinner("Testing access to primary license..."):
                            success, message = st.session_state.aws_integration.test_s3_access(s3_bucket, primary_s3_key)
                            if success:
                                st.success(message)
                            else:
                                st.error(message)
                    else:
                        st.warning("⚠️ Please configure AWS credentials in the Configuration page first")
            
            with col2:
                if st.button("🧪 Test Backup License Access", disabled=not (s3_bucket and backup_s3_key)):
                    if 'aws_integration' in st.session_state and st.session_state.aws_integration:
                        with st.spinner("Testing access to backup license..."):
                            success, message = st.session_state.aws_integration.test_s3_access(s3_bucket, backup_s3_key)
                            if success:
                                st.success(message)
                            else:
                                st.error(message)
                    else:
                        st.warning("⚠️ Please configure AWS credentials in the Configuration page first")
        
        # File upload configuration
        elif license_source == 'file_upload':
            st.markdown("#### License File Upload")
            st.info("📤 Upload FortiGate license files (.lic format) for both primary and backup instances")
            
            col1, col2 = st.columns(2)
            
            with col1:
                primary_file = st.file_uploader(
                    "Primary License File",
                    type=['lic'],
                    help="Upload the license file for the primary FortiGate instance",
                    key="primary_license_upload"
                )
                if primary_file:
                    st.session_state.licensing_config['primary_license_file'] = primary_file
                    st.success(f"✅ Uploaded: {primary_file.name}")
            
            with col2:
                backup_file = st.file_uploader(
                    "Backup License File",
                    type=['lic'],
                    help="Upload the license file for the backup FortiGate instance",
                    key="backup_license_upload"
                )
                if backup_file:
                    st.session_state.licensing_config['backup_license_file'] = backup_file
                    st.success(f"✅ Uploaded: {backup_file.name}")
    
    elif license_type == 'OnDemand':
        st.markdown("---")
        st.info("✅ OnDemand licensing selected. No license files are required. FortiGate licensing is included in the hourly instance cost.")
    
    elif license_type == 'Reserved':
        st.markdown("---")
        st.info("✅ Reserved Instance licensing selected. No license files are required. You'll receive discounted pricing based on your reservation term.")
    
    # Task 12.4: Display cost implications
    st.markdown("---")
    st.markdown("### 💰 Cost Implications")
    
    # Get instance type from session state or use default
    instance_type = 'c5.xlarge'
    if 'fortigate_config' in st.session_state and st.session_state.fortigate_config.get('instance_type'):
        instance_type = st.session_state.fortigate_config['instance_type']
    
    # Cost comparison parameters
    col1, col2 = st.columns(2)
    with col1:
        duration_days = st.slider(
            "Deployment Duration (days)",
            min_value=1,
            max_value=1095,  # 3 years
            value=30,
            help="Estimated deployment duration for cost comparison"
        )
    
    with col2:
        st.metric("Instance Type", instance_type, help="Instance type from FortiGate configuration")
    
    # Calculate costs
    duration_hours = duration_days * 24
    calculator = CostCalculator(instance_type)
    comparison = calculator.compare_licensing_models(duration_hours)
    
    # Display cost comparison
    st.markdown("#### Cost Comparison")
    
    # Create comparison table
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("**BYOL**")
        byol_cost = comparison['byol']
        st.metric(
            "Total Cost",
            f"${byol_cost['total_cost']:,.2f}",
            help="EC2 instance costs only. License costs are separate."
        )
        st.caption(f"${byol_cost['cost_per_hour']:.2f}/hour")
        st.caption("⚠️ License costs not included")
    
    with col2:
        st.markdown("**OnDemand**")
        ondemand_cost = comparison['ondemand']
        st.metric(
            "Total Cost",
            f"${ondemand_cost['total_cost']:,.2f}",
            help="Includes EC2 and FortiGate licensing costs"
        )
        st.caption(f"${ondemand_cost['cost_per_hour']:.2f}/hour")
        st.caption("✅ All costs included")
    
    with col3:
        st.markdown("**Reserved (1Y All Upfront)**")
        reserved_cost = comparison['reserved_1year_all_upfront']
        st.metric(
            "Total Cost",
            f"${reserved_cost['total_cost']:,.2f}",
            help="Discounted pricing with 1-year commitment"
        )
        st.caption(f"${reserved_cost['cost_per_hour']:.2f}/hour")
        st.caption(f"💰 {reserved_cost['discount_percentage']}% discount")
    
    # Recommendation
    st.markdown("#### 💡 Recommendation")
    st.info(f"**{comparison['recommendation_reason']}**")
    
    # Link to Cost Analysis page
    st.markdown("---")
    st.markdown("#### 📊 Detailed Cost Analysis")
    st.markdown(
        "For a comprehensive cost breakdown and comparison of all licensing models, "
        "visit the **[Cost Analysis](/Cost_Analysis)** page."
    )
    
    # Save configuration button
    st.markdown("---")
    if st.button("💾 Save Licensing Configuration", type="primary"):
        # Update deployment config with licensing settings
        if 'deployment_config' not in st.session_state:
            st.session_state.deployment_config = {}
        
        # Create LicensingConfig object
        licensing_config = {
            'type': st.session_state.licensing_config['type'],
            'primary_license_secret': st.session_state.licensing_config.get('primary_license_secret'),
            'backup_license_secret': st.session_state.licensing_config.get('backup_license_secret'),
            'license_s3_bucket': st.session_state.licensing_config.get('license_s3_bucket'),
            'primary_license_s3_key': st.session_state.licensing_config.get('primary_license_s3_key'),
            'backup_license_s3_key': st.session_state.licensing_config.get('backup_license_s3_key')
        }
        
        st.session_state.deployment_config['licensing'] = licensing_config
        st.success("✅ Licensing configuration saved successfully!")
        st.info("💡 Proceed to the Deployment page to deploy your FortiGate HA pair.")


def render_cost_analysis_page():
    """
    Render the cost analysis page with cost calculation and comparison.
    
    This page allows users to:
    - Configure cost calculation parameters (duration, instance type, region)
    - Calculate costs for different licensing models
    - View cost comparison charts
    - See detailed cost breakdowns
    - Get licensing recommendations
    
    Requirements:
        - Requirements 14.1-14.11: Cost analysis and comparison
    """
    st.markdown('<h2 class="section-header">💰 Cost Analysis</h2>', unsafe_allow_html=True)
    
    st.markdown("""
    Compare costs across different FortiGate licensing models to make informed decisions.
    This analysis includes EC2 instance costs, FortiGate licensing costs, and provides
    recommendations based on your deployment duration.
    """)
    
    # Task 15.1: Create cost calculation parameter inputs
    st.markdown("### Cost Calculation Parameters")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Duration slider (1-1095 days = 3 years)
        duration_days = st.slider(
            "Deployment Duration (days)",
            min_value=1,
            max_value=1095,
            value=365,
            step=1,
            help="Select the expected deployment duration. This affects the cost comparison and recommendation."
        )
        
        # Instance type selector
        instance_types = [
            't2.small', 't3.small', 't3.medium', 't3.large',
            'c5.large', 'c5.xlarge', 'c5.2xlarge', 'c5.4xlarge',
            'c5n.large', 'c5n.xlarge', 'c5n.2xlarge', 'c5n.4xlarge'
        ]
        
        instance_type = st.selectbox(
            "Instance Type",
            options=instance_types,
            index=instance_types.index('c5.xlarge') if 'c5.xlarge' in instance_types else 0,
            help="Select the EC2 instance type for your FortiGate deployment."
        )
    
    with col2:
        # Usage pattern selector
        usage_pattern = st.selectbox(
            "Usage Pattern",
            options=['24/7 (Continuous)', 'Business Hours (8x5)', 'Intermittent'],
            index=0,
            help="Select the expected usage pattern. This affects the total hours calculation."
        )
        
        # Region selector
        regions = [
            'us-east-1', 'us-east-2', 'us-west-1', 'us-west-2',
            'eu-west-1', 'eu-central-1', 'ap-southeast-1', 'ap-northeast-1'
        ]
        
        region = st.selectbox(
            "AWS Region",
            options=regions,
            index=0,
            help="Select the AWS region for deployment. Pricing may vary by region."
        )
    
    # Calculate button
    calculate_button = st.button("🔍 Calculate Costs", type="primary", use_container_width=True)
    
    # Calculate duration in hours based on usage pattern
    if usage_pattern == '24/7 (Continuous)':
        duration_hours = duration_days * 24
    elif usage_pattern == 'Business Hours (8x5)':
        # 8 hours/day * 5 days/week = 40 hours/week
        duration_hours = int((duration_days / 7) * 40)
    else:  # Intermittent
        # Assume 4 hours/day average
        duration_hours = duration_days * 4
    
    # Task 15.2 & 15.3: Implement cost calculation and display
    if calculate_button or st.session_state.get('cost_analysis_calculated', False):
        # Mark as calculated to persist results
        st.session_state['cost_analysis_calculated'] = True
        
        with st.spinner("Calculating costs..."):
            # Initialize cost calculator
            calculator = CostCalculator(instance_type=instance_type, region=region)
            
            # Compare all licensing models
            comparison = calculator.compare_licensing_models(
                duration_hours=duration_hours,
                num_instances=2  # HA pair
            )
            
            st.success("✅ Cost calculation complete!")
            
            # Display summary metrics
            st.markdown("### Cost Summary")
            
            metric_cols = st.columns(4)
            
            with metric_cols[0]:
                st.metric(
                    "Duration",
                    f"{duration_days} days",
                    f"{duration_hours:,} hours"
                )
            
            with metric_cols[1]:
                st.metric(
                    "Instance Type",
                    instance_type,
                    f"2 instances (HA)"
                )
            
            with metric_cols[2]:
                st.metric(
                    "Recommended Model",
                    comparison['recommended'].replace('_', ' ').title(),
                    "Best value"
                )
            
            with metric_cols[3]:
                # Calculate savings vs most expensive
                all_costs = [
                    comparison['byol']['total_cost'],
                    comparison['ondemand']['total_cost'],
                    comparison['reserved_1year_no_upfront']['total_cost'],
                    comparison['reserved_1year_all_upfront']['total_cost'],
                    comparison['reserved_3year_no_upfront']['total_cost'],
                    comparison['reserved_3year_all_upfront']['total_cost']
                ]
                max_cost = max(all_costs)
                recommended_cost = comparison[comparison['recommended']]['total_cost']
                savings = max_cost - recommended_cost
                savings_percent = (savings / max_cost * 100) if max_cost > 0 else 0
                
                st.metric(
                    "Potential Savings",
                    f"${savings:,.2f}",
                    f"{savings_percent:.1f}% vs most expensive"
                )
            
            # Display recommendation
            st.info(f"💡 **Recommendation:** {comparison['recommendation_reason']}")
            
            # Task 15.2: Display cost comparison charts using Plotly
            st.markdown("### Cost Comparison")
            
            # Prepare data for charts
            models = [
                'BYOL',
                'OnDemand',
                'Reserved 1Y\n(No Upfront)',
                'Reserved 1Y\n(All Upfront)',
                'Reserved 3Y\n(No Upfront)',
                'Reserved 3Y\n(All Upfront)'
            ]
            
            total_costs = [
                comparison['byol']['total_cost'],
                comparison['ondemand']['total_cost'],
                comparison['reserved_1year_no_upfront']['total_cost'],
                comparison['reserved_1year_all_upfront']['total_cost'],
                comparison['reserved_3year_no_upfront']['total_cost'],
                comparison['reserved_3year_all_upfront']['total_cost']
            ]
            
            monthly_costs = [cost / (duration_days / 30) for cost in total_costs]
            
            # Create bar chart for total costs
            import plotly.graph_objects as go
            
            fig_bar = go.Figure()
            
            # Highlight recommended model
            colors = ['lightblue' if i != models.index(comparison['recommended'].replace('_', ' ').title().replace('\n', ' ')) 
                     else 'green' for i in range(len(models))]
            
            fig_bar.add_trace(go.Bar(
                x=models,
                y=total_costs,
                marker_color=colors,
                text=[f'${cost:,.2f}' for cost in total_costs],
                textposition='outside',
                hovertemplate='<b>%{x}</b><br>Total Cost: $%{y:,.2f}<extra></extra>'
            ))
            
            fig_bar.update_layout(
                title=f"Total Cost Comparison ({duration_days} days)",
                xaxis_title="Licensing Model",
                yaxis_title="Total Cost (USD)",
                height=400,
                showlegend=False,
                hovermode='x'
            )
            
            st.plotly_chart(fig_bar, use_container_width=True)
            
            # Create line chart showing cost over time
            time_periods = list(range(0, duration_days + 1, max(1, duration_days // 10)))
            
            fig_line = go.Figure()
            
            # Calculate cumulative costs for each model
            for model_name, model_key in [
                ('BYOL', 'byol'),
                ('OnDemand', 'ondemand'),
                ('Reserved 1Y (All Upfront)', 'reserved_1year_all_upfront'),
                ('Reserved 3Y (All Upfront)', 'reserved_3year_all_upfront')
            ]:
                model_data = comparison[model_key]
                cost_per_day = model_data['total_cost'] / duration_days
                cumulative_costs = [cost_per_day * day for day in time_periods]
                
                fig_line.add_trace(go.Scatter(
                    x=time_periods,
                    y=cumulative_costs,
                    mode='lines+markers',
                    name=model_name,
                    hovertemplate=f'<b>{model_name}</b><br>Day: %{{x}}<br>Cost: $%{{y:,.2f}}<extra></extra>'
                ))
            
            fig_line.update_layout(
                title="Cumulative Cost Over Time",
                xaxis_title="Days",
                yaxis_title="Cumulative Cost (USD)",
                height=400,
                hovermode='x unified'
            )
            
            st.plotly_chart(fig_line, use_container_width=True)
            
            # Task 15.3: Add detailed cost breakdown
            st.markdown("### Detailed Cost Breakdown")
            
            # Create breakdown table
            breakdown_data = []
            
            for model_name, model_key in [
                ('BYOL', 'byol'),
                ('OnDemand', 'ondemand'),
                ('Reserved 1Y (No Upfront)', 'reserved_1year_no_upfront'),
                ('Reserved 1Y (All Upfront)', 'reserved_1year_all_upfront'),
                ('Reserved 3Y (No Upfront)', 'reserved_3year_no_upfront'),
                ('Reserved 3Y (All Upfront)', 'reserved_3year_all_upfront')
            ]:
                model_data = comparison[model_key]
                
                # Calculate monthly costs
                monthly_ec2 = model_data['instance_cost'] / (duration_days / 30)
                monthly_license = model_data['license_cost'] / (duration_days / 30)
                monthly_total = model_data['total_cost'] / (duration_days / 30)
                
                # Calculate savings vs OnDemand
                savings_vs_ondemand = comparison['ondemand']['total_cost'] - model_data['total_cost']
                savings_percent = (savings_vs_ondemand / comparison['ondemand']['total_cost'] * 100) if comparison['ondemand']['total_cost'] > 0 else 0
                
                breakdown_data.append({
                    'Licensing Model': model_name,
                    'EC2 Cost (Monthly)': f"${monthly_ec2:,.2f}",
                    'License Cost (Monthly)': f"${monthly_license:,.2f}",
                    'Total Cost (Monthly)': f"${monthly_total:,.2f}",
                    'Total Cost': f"${model_data['total_cost']:,.2f}",
                    'Savings vs OnDemand': f"${savings_vs_ondemand:,.2f} ({savings_percent:+.1f}%)"
                })
            
            import pandas as pd
            df_breakdown = pd.DataFrame(breakdown_data)
            
            # Highlight recommended row
            def highlight_recommended(row):
                if comparison['recommended'].replace('_', ' ').lower() in row['Licensing Model'].lower():
                    return ['background-color: #90EE90'] * len(row)
                return [''] * len(row)
            
            st.dataframe(
                df_breakdown.style.apply(highlight_recommended, axis=1),
                use_container_width=True,
                hide_index=True
            )
            
            # Additional cost details
            st.markdown("### Cost Components")
            
            detail_cols = st.columns(3)
            
            with detail_cols[0]:
                st.markdown("**EC2 Instance Costs**")
                st.write(f"Instance Type: {instance_type}")
                st.write(f"Number of Instances: 2 (HA pair)")
                st.write(f"Duration: {duration_hours:,} hours")
                st.write(f"Base EC2 Rate: ${calculator.instance_cost_per_hour:.4f}/hour per instance")
            
            with detail_cols[1]:
                st.markdown("**FortiGate License Costs**")
                st.write(f"OnDemand Rate: ${calculator.fortigate_ondemand_cost_per_hour:.4f}/hour per instance")
                st.write(f"BYOL: License purchased separately")
                st.write(f"Reserved: Discounted rates apply")
            
            with detail_cols[2]:
                st.markdown("**Additional Considerations**")
                st.write("• Data transfer costs not included")
                st.write("• EBS storage costs not included")
                st.write("• Prices are approximate (us-east-1)")
                st.write("• Actual costs may vary by region")
            
            # Discount information for reserved instances
            st.markdown("### Reserved Instance Discounts")
            
            discount_info = """
            Reserved Instances offer significant savings for long-term deployments:
            
            **1-Year Term:**
            - No Upfront: 30% discount
            - Partial Upfront: 35% discount
            - All Upfront: 40% discount
            
            **3-Year Term:**
            - No Upfront: 45% discount
            - Partial Upfront: 50% discount
            - All Upfront: 55% discount
            
            *Note: Discounts apply to both EC2 and FortiGate licensing costs.*
            """
            
            st.info(discount_info)
            
            # Export option
            st.markdown("### Export Analysis")
            
            export_col1, export_col2 = st.columns(2)
            
            with export_col1:
                # Prepare export data
                export_data = {
                    'analysis_date': pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'parameters': {
                        'duration_days': duration_days,
                        'duration_hours': duration_hours,
                        'instance_type': instance_type,
                        'usage_pattern': usage_pattern,
                        'region': region,
                        'num_instances': 2
                    },
                    'recommendation': {
                        'model': comparison['recommended'],
                        'reason': comparison['recommendation_reason']
                    },
                    'costs': {
                        'byol': comparison['byol'],
                        'ondemand': comparison['ondemand'],
                        'reserved_1year_all_upfront': comparison['reserved_1year_all_upfront'],
                        'reserved_3year_all_upfront': comparison['reserved_3year_all_upfront']
                    }
                }
                
                import json
                export_json = json.dumps(export_data, indent=2)
                
                st.download_button(
                    label="📥 Download Analysis (JSON)",
                    data=export_json,
                    file_name=f"fortigate_cost_analysis_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json"
                )
            
            with export_col2:
                # CSV export
                csv_data = df_breakdown.to_csv(index=False)
                
                st.download_button(
                    label="📥 Download Breakdown (CSV)",
                    data=csv_data,
                    file_name=f"fortigate_cost_breakdown_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
    
    else:
        st.info("👆 Configure the parameters above and click 'Calculate Costs' to see the cost analysis.")


def render_deployment_page():
    """
    Render the deployment page with full deployment workflow functionality.
    
    This page provides:
    - Plan Only: Generate Terraform plan without applying
    - Deploy: Execute full deployment with progress tracking
    - Destroy: Destroy deployed infrastructure with confirmation
    - Real-time log streaming
    - Deployment results and outputs
    
    Requirements:
        - Requirements 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7, 8.8: Plan-only workflow
        - Requirements 7.1, 7.2, 7.3, 10.1, 10.2, 10.3, 10.4, 10.5, 10.6: Deployment workflow
        - Requirements 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.8: Destroy workflow
        - Requirements 10.7, 10.8, 10.9, 10.10: Deployment results
    """
    st.markdown('<h2 class="section-header">🚀 Deployment</h2>', unsafe_allow_html=True)
    
    # Check if configuration is available
    if st.session_state.deployment_config is None:
        st.warning("⚠️ No deployment configuration found. Please configure your deployment first.")
        st.info("👉 Go to the **Configuration** page to set up your deployment parameters.")
        return
    
    config = st.session_state.deployment_config
    
    # Display configuration summary
    with st.expander("📋 Configuration Summary", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**AWS Configuration**")
            st.text(f"Region: {config.aws.region}")
            st.text(f"Environment: {config.environment}")
            st.text(f"Owner: {config.owner_tag}")
            
            st.markdown("**Network Configuration**")
            st.text(f"VPC: {config.network.vpc_id}")
            st.text(f"AZs: {', '.join(config.network.availability_zones)}")
        
        with col2:
            st.markdown("**FortiGate Configuration**")
            st.text(f"AMI: {config.fortigate.ami_id}")
            st.text(f"Instance Type: {config.fortigate.instance_type}")
            st.text(f"Key Pair: {config.fortigate.key_pair_name}")
            
            st.markdown("**Backend Configuration**")
            st.text(f"Type: {config.backend.backend_type}")
            if config.backend.backend_type == "s3":
                st.text(f"Bucket: {config.backend.s3_bucket}")
    
    st.markdown("---")
    
    # Action buttons
    st.markdown("### Deployment Actions")
    
    col1, col2, col3 = st.columns(3)
    
    # Determine button states based on deployment status
    status = st.session_state.deployment_status
    
    # Plan Only button
    with col1:
        plan_disabled = status in ['planning', 'deploying', 'destroying']
        if st.button("📋 Plan Only", disabled=plan_disabled, use_container_width=True, type="secondary"):
            st.session_state.deployment_status = 'planning'
            st.session_state.deployment_logs = []
            st.session_state.terraform_output = ""
            st.rerun()
    
    # Deploy button
    with col2:
        deploy_disabled = status in ['planning', 'deploying', 'destroying']
        if st.button("🚀 Deploy", disabled=deploy_disabled, use_container_width=True, type="primary"):
            st.session_state.deployment_status = 'deploying'
            st.session_state.deployment_logs = []
            st.session_state.terraform_output = ""
            st.rerun()
    
    # Destroy button
    with col3:
        destroy_disabled = status in ['planning', 'deploying', 'destroying', 'not_started']
        if st.button("🗑️ Destroy", disabled=destroy_disabled, use_container_width=True, type="secondary"):
            # Show confirmation dialog
            st.session_state.show_destroy_confirmation = True
            st.rerun()
    
    st.markdown("---")
    
    # Handle destroy confirmation dialog
    if hasattr(st.session_state, 'show_destroy_confirmation') and st.session_state.show_destroy_confirmation:
        st.error("⚠️ **WARNING: This will destroy all deployed infrastructure!**")
        st.markdown("This action cannot be undone. All FortiGate instances, network resources, and configurations will be permanently deleted.")
        
        st.markdown("**To confirm, type:** `DESTROY` (in capital letters)")
        confirmation_text = st.text_input("Confirmation", key="destroy_confirmation_input")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ Confirm Destroy", type="primary", disabled=(confirmation_text != "DESTROY")):
                st.session_state.deployment_status = 'destroying'
                st.session_state.deployment_logs = []
                st.session_state.terraform_output = ""
                st.session_state.show_destroy_confirmation = False
                st.rerun()
        
        with col2:
            if st.button("❌ Cancel"):
                st.session_state.show_destroy_confirmation = False
                st.rerun()
        
        st.markdown("---")
    
    # Execute workflows based on status
    if status == 'planning':
        execute_plan_workflow(config)
    elif status == 'deploying':
        execute_deployment_workflow(config)
    elif status == 'destroying':
        execute_destroy_workflow(config)
    elif status == 'deployed':
        display_deployment_results()
    elif status == 'failed':
        display_failure_results()
    
    # Display logs if available
    if st.session_state.deployment_logs or st.session_state.terraform_output:
        st.markdown("---")
        st.markdown("### 📜 Deployment Logs")
        
        # Log download button
        if st.session_state.terraform_output:
            log_content = "\n".join(st.session_state.deployment_logs) + "\n\n" + st.session_state.terraform_output
            st.download_button(
                label="💾 Download Logs",
                data=log_content,
                file_name=f"deployment_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                mime="text/plain"
            )
        
        # Display logs in scrollable container
        log_container = st.container()
        with log_container:
            if st.session_state.deployment_logs:
                for log in st.session_state.deployment_logs:
                    st.text(log)
            
            if st.session_state.terraform_output:
                st.code(st.session_state.terraform_output, language="text")


def execute_plan_workflow(config: DeploymentConfig):
    """
    Execute the plan-only workflow.
    
    This workflow:
    1. Validates configuration (unless skipped)
    2. Generates Terraform plan
    3. Displays plan output with syntax highlighting
    4. Saves plan file for later application
    
    Requirements:
        - Requirements 8.2, 8.3, 8.4, 8.5, 8.6, 8.7, 8.8: Plan workflow
    """
    st.markdown("### 📋 Generating Terraform Plan")
    
    # Progress tracking
    progress_bar = st.progress(0.0)
    status_text = st.empty()
    
    # Create orchestrator
    orchestrator = DeploymentOrchestrator(
        config=config,
        skip_validation=st.session_state.skip_validation
    )
    
    # Progress callback
    def progress_callback(message: str, progress: float):
        status_text.text(message)
        progress_bar.progress(min(progress, 1.0))
        st.session_state.deployment_logs.append(message)
    
    try:
        # Execute plan
        success, plan_output = orchestrator.plan_deployment(progress_callback=progress_callback)
        
        st.session_state.terraform_output = plan_output
        
        if success:
            st.session_state.deployment_status = 'not_started'  # Reset to allow deploy
            progress_bar.progress(1.0)
            status_text.text("✅ Plan generation completed successfully")
            
            st.success("✅ **Plan Generated Successfully**")
            
            # Parse and display plan summary
            display_plan_summary(plan_output)
            
            # Display full plan output with syntax highlighting
            st.markdown("#### 📄 Full Plan Output")
            with st.expander("View Complete Plan", expanded=False):
                # Highlight additions, changes, deletions
                highlighted_plan = highlight_terraform_plan(plan_output)
                st.code(highlighted_plan, language="text")
            
            st.info("💡 **Tip:** Review the plan carefully. When ready, click **Deploy** to apply these changes.")
        
        else:
            st.session_state.deployment_status = 'failed'
            progress_bar.progress(1.0)
            status_text.text("❌ Plan generation failed")
            
            st.error("❌ **Plan Generation Failed**")
            st.markdown("**Error Details:**")
            st.code(plan_output, language="text")
            
            # Provide remediation guidance
            st.markdown("**Troubleshooting Steps:**")
            st.markdown("1. Check that all required parameters are configured correctly")
            st.markdown("2. Verify AWS credentials have necessary permissions")
            st.markdown("3. Ensure Terraform is installed and accessible")
            st.markdown("4. Review the error details above for specific issues")
    
    except Exception as e:
        st.session_state.deployment_status = 'failed'
        progress_bar.progress(1.0)
        status_text.text(f"❌ Error: {str(e)}")
        
        st.error(f"❌ **Unexpected Error:** {str(e)}")
        st.session_state.deployment_logs.append(f"ERROR: {str(e)}")


def execute_deployment_workflow(config: DeploymentConfig):
    """
    Execute the full deployment workflow.
    
    This workflow:
    1. Validates configuration (unless skipped)
    2. Initializes Terraform
    3. Generates and applies deployment
    4. Tracks progress with real-time updates
    5. Extracts and displays outputs
    
    Requirements:
        - Requirements 7.1, 7.2, 7.3: Terraform operations
        - Requirements 10.1, 10.2, 10.3, 10.4, 10.5, 10.6: Deployment tracking
    """
    st.markdown("### 🚀 Deploying Infrastructure")
    
    # Progress tracking
    progress_bar = st.progress(0.0)
    status_text = st.empty()
    elapsed_time_text = st.empty()
    
    # Track start time
    start_time = time.time()
    
    # Create orchestrator
    orchestrator = DeploymentOrchestrator(
        config=config,
        skip_validation=st.session_state.skip_validation
    )
    
    # Progress callback
    def progress_callback(message: str, progress: float):
        status_text.text(message)
        progress_bar.progress(min(progress, 1.0))
        st.session_state.deployment_logs.append(message)
        
        # Update elapsed time
        elapsed = time.time() - start_time
        elapsed_time_text.text(f"⏱️ Elapsed Time: {format_elapsed_time(elapsed)}")
    
    try:
        # Execute deployment
        success, output, terraform_outputs = orchestrator.execute_deployment(progress_callback=progress_callback)
        
        st.session_state.terraform_output = output
        
        if success:
            st.session_state.deployment_status = 'deployed'
            st.session_state.terraform_outputs = terraform_outputs
            progress_bar.progress(1.0)
            
            elapsed = time.time() - start_time
            status_text.text(f"✅ Deployment completed successfully in {format_elapsed_time(elapsed)}")
            
            st.success(f"✅ **Deployment Completed Successfully** (in {format_elapsed_time(elapsed)})")
            
            # Display deployment summary
            display_deployment_summary(terraform_outputs)
        
        else:
            st.session_state.deployment_status = 'failed'
            progress_bar.progress(1.0)
            
            elapsed = time.time() - start_time
            status_text.text(f"❌ Deployment failed after {format_elapsed_time(elapsed)}")
            
            st.error(f"❌ **Deployment Failed** (after {format_elapsed_time(elapsed)})")
            st.markdown("**Error Details:**")
            st.code(output, language="text")
            
            # Provide remediation guidance
            st.markdown("**Troubleshooting Steps:**")
            st.markdown("1. Review the error details above to identify the failure point")
            st.markdown("2. Check AWS service quotas and limits")
            st.markdown("3. Verify all resources are available in the selected region")
            st.markdown("4. Check CloudWatch logs for additional details")
            st.markdown("5. Consider running **Plan Only** first to validate the configuration")
    
    except Exception as e:
        st.session_state.deployment_status = 'failed'
        progress_bar.progress(1.0)
        
        elapsed = time.time() - start_time
        status_text.text(f"❌ Error after {format_elapsed_time(elapsed)}: {str(e)}")
        
        st.error(f"❌ **Unexpected Error:** {str(e)}")
        st.session_state.deployment_logs.append(f"ERROR: {str(e)}")


def execute_destroy_workflow(config: DeploymentConfig):
    """
    Execute the destroy workflow.
    
    This workflow:
    1. Confirms user intent (already done in UI)
    2. Initializes Terraform
    3. Executes terraform destroy
    4. Tracks progress with real-time updates
    
    Requirements:
        - Requirements 9.2, 9.3, 9.4, 9.5, 9.6: Destroy workflow
    """
    st.markdown("### 🗑️ Destroying Infrastructure")
    
    st.warning("⚠️ **Destruction in progress...** This may take several minutes.")
    
    # Progress tracking
    progress_bar = st.progress(0.0)
    status_text = st.empty()
    elapsed_time_text = st.empty()
    
    # Track start time
    start_time = time.time()
    
    # Create orchestrator
    orchestrator = DeploymentOrchestrator(
        config=config,
        skip_validation=True  # Skip validation for destroy
    )
    
    # Progress callback
    def progress_callback(message: str, progress: float):
        status_text.text(message)
        progress_bar.progress(min(progress, 1.0))
        st.session_state.deployment_logs.append(message)
        
        # Update elapsed time
        elapsed = time.time() - start_time
        elapsed_time_text.text(f"⏱️ Elapsed Time: {format_elapsed_time(elapsed)}")
    
    try:
        # Execute destroy
        success, output = orchestrator.destroy_deployment(progress_callback=progress_callback)
        
        st.session_state.terraform_output = output
        
        if success:
            st.session_state.deployment_status = 'not_started'
            st.session_state.terraform_outputs = {}
            progress_bar.progress(1.0)
            
            elapsed = time.time() - start_time
            status_text.text(f"✅ Infrastructure destroyed successfully in {format_elapsed_time(elapsed)}")
            
            st.success(f"✅ **Infrastructure Destroyed Successfully** (in {format_elapsed_time(elapsed)})")
            st.info("All resources have been removed. You can now deploy a new configuration.")
        
        else:
            st.session_state.deployment_status = 'failed'
            progress_bar.progress(1.0)
            
            elapsed = time.time() - start_time
            status_text.text(f"❌ Destroy operation failed after {format_elapsed_time(elapsed)}")
            
            st.error(f"❌ **Destroy Operation Failed** (after {format_elapsed_time(elapsed)})")
            st.markdown("**Error Details:**")
            st.code(output, language="text")
            
            # Provide remediation guidance
            st.markdown("**Troubleshooting Steps:**")
            st.markdown("1. Review the error details to identify which resources failed to destroy")
            st.markdown("2. Check AWS Console for resources that may be in use or protected")
            st.markdown("3. Manually delete problematic resources through AWS Console")
            st.markdown("4. Try running destroy again after manual cleanup")
            st.markdown("5. Check for dependencies that may prevent resource deletion")
    
    except Exception as e:
        st.session_state.deployment_status = 'failed'
        progress_bar.progress(1.0)
        
        elapsed = time.time() - start_time
        status_text.text(f"❌ Error after {format_elapsed_time(elapsed)}: {str(e)}")
        
        st.error(f"❌ **Unexpected Error:** {str(e)}")
        st.session_state.deployment_logs.append(f"ERROR: {str(e)}")


def display_deployment_results():
    """
    Display deployment results and outputs.
    
    Requirements:
        - Requirements 10.7, 10.8: Deployment summary and outputs
    """
    st.markdown("### ✅ Deployment Completed")
    
    st.success("🎉 **Your FortiGate HA deployment is ready!**")
    
    # Display Terraform outputs if available
    if hasattr(st.session_state, 'terraform_outputs') and st.session_state.terraform_outputs:
        st.markdown("#### 📊 Deployment Outputs")
        
        outputs = st.session_state.terraform_outputs
        
        # Display key outputs in a structured format
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Primary FortiGate**")
            if 'primary_fortigate_id' in outputs:
                st.text(f"Instance ID: {outputs['primary_fortigate_id']}")
            if 'primary_fortigate_private_ip' in outputs:
                st.text(f"Private IP: {outputs['primary_fortigate_private_ip']}")
            if 'primary_fortigate_public_ip' in outputs:
                st.text(f"Public IP: {outputs['primary_fortigate_public_ip']}")
        
        with col2:
            st.markdown("**Backup FortiGate**")
            if 'backup_fortigate_id' in outputs:
                st.text(f"Instance ID: {outputs['backup_fortigate_id']}")
            if 'backup_fortigate_private_ip' in outputs:
                st.text(f"Private IP: {outputs['backup_fortigate_private_ip']}")
            if 'backup_fortigate_public_ip' in outputs:
                st.text(f"Public IP: {outputs['backup_fortigate_public_ip']}")
        
        # Display all outputs in expandable section
        with st.expander("📋 All Terraform Outputs", expanded=False):
            for key, value in outputs.items():
                st.text(f"{key}: {value}")
    
    # Next steps
    st.markdown("#### 🎯 Next Steps")
    st.markdown("1. **Access FortiGate Management:** Use the public IPs above to access the FortiGate web interface")
    st.markdown("2. **Configure Policies:** Set up security policies and routing rules")
    st.markdown("3. **Monitor Status:** Check the Monitoring page for health status and metrics")
    st.markdown("4. **Test Connectivity:** Verify traffic flow through the FortiGate instances")
    
    # Management links
    if hasattr(st.session_state, 'terraform_outputs') and st.session_state.terraform_outputs:
        outputs = st.session_state.terraform_outputs
        if 'primary_fortigate_public_ip' in outputs:
            primary_ip = outputs['primary_fortigate_public_ip']
            st.markdown(f"**Primary FortiGate Console:** `https://{primary_ip}`")
        if 'backup_fortigate_public_ip' in outputs:
            backup_ip = outputs['backup_fortigate_public_ip']
            st.markdown(f"**Backup FortiGate Console:** `https://{backup_ip}`")


def display_failure_results():
    """
    Display failure information and recovery options.
    
    Requirements:
        - Requirements 10.9: Failure handling
    """
    st.markdown("### ❌ Deployment Failed")
    
    st.error("**The deployment encountered errors and could not complete.**")
    
    st.markdown("#### 🔍 What Happened?")
    st.markdown("Review the deployment logs below to identify the failure point and error details.")
    
    st.markdown("#### 🛠️ Recovery Options")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Option 1: Fix and Retry**")
        st.markdown("1. Review error details in logs")
        st.markdown("2. Update configuration to fix issues")
        st.markdown("3. Run **Plan Only** to validate")
        st.markdown("4. Click **Deploy** to retry")
    
    with col2:
        st.markdown("**Option 2: Clean Up**")
        st.markdown("1. Click **Destroy** to remove partial deployment")
        st.markdown("2. Verify all resources are cleaned up")
        st.markdown("3. Start fresh with new configuration")
    
    # Reset button
    if st.button("🔄 Reset Deployment Status", type="secondary"):
        st.session_state.deployment_status = 'not_started'
        st.rerun()


def display_plan_summary(plan_output: str):
    """
    Parse and display a summary of the Terraform plan.
    
    Extracts resource counts and displays them in a user-friendly format.
    
    Requirements:
        - Requirements 8.7: Display resource count summary
    """
    st.markdown("#### 📊 Plan Summary")
    
    # Parse plan output for resource counts
    add_count = plan_output.count("# ") if "+ " in plan_output else 0
    change_count = plan_output.count("~") if "~" in plan_output else 0
    destroy_count = plan_output.count("-") if "- " in plan_output else 0
    
    # Try to extract actual counts from plan summary line
    import re
    summary_match = re.search(r'Plan: (\d+) to add, (\d+) to change, (\d+) to destroy', plan_output)
    if summary_match:
        add_count = int(summary_match.group(1))
        change_count = int(summary_match.group(2))
        destroy_count = int(summary_match.group(3))
    
    # Display counts with color coding
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(label="➕ Resources to Add", value=add_count)
    
    with col2:
        st.metric(label="🔄 Resources to Change", value=change_count)
    
    with col3:
        st.metric(label="➖ Resources to Destroy", value=destroy_count)
    
    total_changes = add_count + change_count + destroy_count
    if total_changes == 0:
        st.info("ℹ️ No changes detected. Infrastructure is up to date.")
    else:
        st.info(f"📝 Total changes: **{total_changes}** resource(s)")


def display_deployment_summary(terraform_outputs: Dict[str, Any]):
    """
    Display a summary of the deployment with key information.
    
    Requirements:
        - Requirements 10.7, 10.8: Deployment summary and resource IDs
    """
    st.markdown("#### 📊 Deployment Summary")
    
    # Count resources
    resource_count = len(terraform_outputs)
    
    st.info(f"✅ Successfully deployed **{resource_count}** resource output(s)")
    
    # Display key resources
    if terraform_outputs:
        st.markdown("**Key Resources:**")
        
        # FortiGate instances
        if 'primary_fortigate_id' in terraform_outputs:
            st.text(f"✓ Primary FortiGate: {terraform_outputs['primary_fortigate_id']}")
        if 'backup_fortigate_id' in terraform_outputs:
            st.text(f"✓ Backup FortiGate: {terraform_outputs['backup_fortigate_id']}")
        
        # Network resources
        if 'transit_gateway_id' in terraform_outputs:
            st.text(f"✓ Transit Gateway: {terraform_outputs['transit_gateway_id']}")
        
        # Management access
        if 'primary_fortigate_public_ip' in terraform_outputs:
            st.text(f"✓ Primary Management IP: {terraform_outputs['primary_fortigate_public_ip']}")
        if 'backup_fortigate_public_ip' in terraform_outputs:
            st.text(f"✓ Backup Management IP: {terraform_outputs['backup_fortigate_public_ip']}")


def highlight_terraform_plan(plan_output: str) -> str:
    """
    Add visual highlighting to Terraform plan output.
    
    Note: Since st.code doesn't support color highlighting, we add
    text markers to help identify additions, changes, and deletions.
    
    Requirements:
        - Requirements 8.4, 8.5, 8.6: Highlight plan changes
    """
    # This is a simplified version - actual color highlighting
    # would require custom HTML rendering
    lines = plan_output.split('\n')
    highlighted = []
    
    for line in lines:
        if line.strip().startswith('+') and not line.strip().startswith('+++'):
            highlighted.append(f"[ADD] {line}")
        elif line.strip().startswith('-') and not line.strip().startswith('---'):
            highlighted.append(f"[DEL] {line}")
        elif line.strip().startswith('~'):
            highlighted.append(f"[CHG] {line}")
        else:
            highlighted.append(line)
    
    return '\n'.join(highlighted)


def format_elapsed_time(seconds: float) -> str:
    """
    Format elapsed time in a human-readable format.
    
    Args:
        seconds: Elapsed time in seconds
    
    Returns:
        Formatted time string (e.g., "2m 30s")
    """
    if seconds < 60:
        return f"{int(seconds)}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h {minutes}m"


def render_monitoring_page():
    """Render the monitoring page with health status, traffic visualization, and event logs"""
    st.markdown('<h2 class="section-header">📊 Monitoring</h2>', unsafe_allow_html=True)
    
    # Note about placeholder data
    st.info("🔄 This page displays placeholder data. Future integration with AWS CloudWatch will provide real-time metrics.")
    
    # Health Status Section
    st.markdown("### 🏥 Health Status")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div style="padding: 20px; background-color: #d4edda; border-radius: 10px; border-left: 5px solid #28a745;">
            <h4 style="margin: 0; color: #155724;">Primary FortiGate</h4>
            <p style="margin: 5px 0; font-size: 24px; font-weight: bold; color: #155724;">✓ Healthy</p>
            <p style="margin: 5px 0; color: #155724;">Instance: i-0abc123def456</p>
            <p style="margin: 5px 0; color: #155724;">Uptime: 15d 7h 23m</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div style="padding: 20px; background-color: #d4edda; border-radius: 10px; border-left: 5px solid #28a745;">
            <h4 style="margin: 0; color: #155724;">Backup FortiGate</h4>
            <p style="margin: 5px 0; font-size: 24px; font-weight: bold; color: #155724;">✓ Healthy</p>
            <p style="margin: 5px 0; color: #155724;">Instance: i-0def456ghi789</p>
            <p style="margin: 5px 0; color: #155724;">Uptime: 15d 7h 23m</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div style="padding: 20px; background-color: #d4edda; border-radius: 10px; border-left: 5px solid #28a745;">
            <h4 style="margin: 0; color: #155724;">BGP Sessions</h4>
            <p style="margin: 5px 0; font-size: 24px; font-weight: bold; color: #155724;">2/2 Up</p>
            <p style="margin: 5px 0; color: #155724;">Primary: Established</p>
            <p style="margin: 5px 0; color: #155724;">Backup: Established</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Throughput Metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(label="Current Throughput", value="1.2 Gbps", delta="0.3 Gbps")
    
    with col2:
        st.metric(label="Active Connections", value="15,432", delta="1,234")
    
    with col3:
        st.metric(label="CPU Usage", value="45%", delta="-5%")
    
    with col4:
        st.metric(label="Memory Usage", value="62%", delta="2%")
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Traffic Visualization
    st.markdown("### 📈 Traffic Visualization")
    
    # Generate sample traffic data
    import pandas as pd
    import plotly.graph_objects as go
    from datetime import datetime, timedelta
    
    # Create sample data for the last 24 hours
    now = datetime.now()
    timestamps = [now - timedelta(hours=23-i) for i in range(24)]
    
    # Sample traffic data (in Gbps)
    inbound_traffic = [0.8 + 0.4 * (i % 6) / 6 + 0.2 * ((i + 3) % 4) / 4 for i in range(24)]
    outbound_traffic = [0.6 + 0.3 * (i % 5) / 5 + 0.15 * ((i + 2) % 3) / 3 for i in range(24)]
    
    # Create the traffic chart
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=timestamps,
        y=inbound_traffic,
        mode='lines',
        name='Inbound Traffic',
        line=dict(color='#1f77b4', width=2),
        fill='tozeroy',
        fillcolor='rgba(31, 119, 180, 0.2)'
    ))
    
    fig.add_trace(go.Scatter(
        x=timestamps,
        y=outbound_traffic,
        mode='lines',
        name='Outbound Traffic',
        line=dict(color='#ff7f0e', width=2),
        fill='tozeroy',
        fillcolor='rgba(255, 127, 14, 0.2)'
    ))
    
    fig.update_layout(
        title='Network Traffic (Last 24 Hours)',
        xaxis_title='Time',
        yaxis_title='Traffic (Gbps)',
        hovermode='x unified',
        height=400,
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Event Log Display
    st.markdown("### 📋 Recent Deployment Events")
    
    # Sample event data
    events = [
        {
            "timestamp": (now - timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S"),
            "event": "Health Check Passed",
            "severity": "info",
            "details": "Primary FortiGate health check successful"
        },
        {
            "timestamp": (now - timedelta(hours=4)).strftime("%Y-%m-%d %H:%M:%S"),
            "event": "BGP Session Established",
            "severity": "success",
            "details": "BGP session with Transit Gateway established"
        },
        {
            "timestamp": (now - timedelta(hours=6)).strftime("%Y-%m-%d %H:%M:%S"),
            "event": "Configuration Update",
            "severity": "info",
            "details": "FortiGate configuration synchronized"
        },
        {
            "timestamp": (now - timedelta(hours=12)).strftime("%Y-%m-%d %H:%M:%S"),
            "event": "Health Check Passed",
            "severity": "info",
            "details": "Backup FortiGate health check successful"
        },
        {
            "timestamp": (now - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S"),
            "event": "Deployment Completed",
            "severity": "success",
            "details": "FortiGate HA deployment completed successfully"
        },
        {
            "timestamp": (now - timedelta(days=1, hours=1)).strftime("%Y-%m-%d %H:%M:%S"),
            "event": "Resource Creation",
            "severity": "info",
            "details": "Transit Gateway attachment created"
        },
        {
            "timestamp": (now - timedelta(days=1, hours=2)).strftime("%Y-%m-%d %H:%M:%S"),
            "event": "Resource Creation",
            "severity": "info",
            "details": "EC2 instances launched"
        },
        {
            "timestamp": (now - timedelta(days=1, hours=3)).strftime("%Y-%m-%d %H:%M:%S"),
            "event": "Deployment Started",
            "severity": "info",
            "details": "FortiGate HA deployment initiated"
        }
    ]
    
    # Display events in a styled table
    for event in events:
        severity_colors = {
            "success": "#d4edda",
            "info": "#d1ecf1",
            "warning": "#fff3cd",
            "error": "#f8d7da"
        }
        
        severity_icons = {
            "success": "✓",
            "info": "ℹ",
            "warning": "⚠",
            "error": "✗"
        }
        
        color = severity_colors.get(event["severity"], "#e2e3e5")
        icon = severity_icons.get(event["severity"], "•")
        
        st.markdown(f"""
        <div style="padding: 15px; margin-bottom: 10px; background-color: {color}; border-radius: 5px; border-left: 4px solid #007bff;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <strong>{icon} {event['event']}</strong>
                    <p style="margin: 5px 0 0 0; color: #666;">{event['details']}</p>
                </div>
                <div style="text-align: right; color: #666; font-size: 0.9em;">
                    {event['timestamp']}
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Additional Information
    with st.expander("ℹ️ About Monitoring Integration"):
        st.markdown("""
        ### Future CloudWatch Integration
        
        This monitoring page currently displays placeholder data for demonstration purposes. 
        In a production deployment, this page would integrate with:
        
        - **AWS CloudWatch Metrics**: Real-time CPU, memory, and network metrics
        - **FortiGate API**: Health status, BGP session state, and active connections
        - **VPC Flow Logs**: Detailed traffic analysis and security insights
        - **CloudWatch Logs**: System logs and security events
        - **AWS Systems Manager**: Instance status and patch compliance
        
        ### Implementing Real Monitoring
        
        To implement real monitoring, you would need to:
        
        1. Enable CloudWatch detailed monitoring on FortiGate instances
        2. Configure FortiGate to send logs to CloudWatch
        3. Set up CloudWatch dashboards for visualization
        4. Use boto3 to query CloudWatch metrics and logs
        5. Implement FortiGate API integration for device-specific metrics
        
        ### Recommended Metrics to Monitor
        
        - Instance health and availability
        - CPU and memory utilization
        - Network throughput (bytes in/out)
        - Active connections and sessions
        - BGP session status
        - VPN tunnel status
        - Security events and threats detected
        - Configuration sync status
        """)
    
    # Quick Actions
    st.markdown("### ⚡ Quick Actions")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("🔄 Refresh Metrics", use_container_width=True):
            st.success("Metrics refreshed!")
            st.rerun()
    
    with col2:
        if st.button("📊 View CloudWatch", use_container_width=True):
            st.info("This would open AWS CloudWatch console")
    
    with col3:
        if st.button("🔍 View Logs", use_container_width=True):
            st.info("This would open CloudWatch Logs")
    
    with col4:
        if st.button("⚙️ FortiGate Console", use_container_width=True):
            st.info("This would open FortiGate management console")


def render_documentation_page():
    """
    Render the documentation page with comprehensive guides and resources.

    This page provides:
    - Deployment guide with step-by-step instructions
    - AMI & licensing guide
    - Monitoring & troubleshooting section
    - Architecture overview
    - Configuration examples
    - External documentation links
    - FAQ section

    Requirements:
        - Requirements 15.1-15.10: Documentation and help resources
    """
    st.markdown('<h2 class="section-header">📚 Documentation</h2>', unsafe_allow_html=True)

    st.markdown("""
    Welcome to the FortiGate AWS HA Deployment documentation. This guide will help you
    understand, configure, and deploy FortiGate HA pairs on AWS.
    """)

    # Create tabs for different documentation sections
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "🚀 Deployment Guide",
        "🔍 AMI & Licensing",
        "📊 Monitoring",
        "🏗️ Architecture",
        "⚙️ Configuration Examples",
        "❓ FAQ"
    ])

    # Tab 1: Deployment Guide
    with tab1:
        st.markdown("### Deployment Guide")

        st.markdown("""
        Follow these steps to deploy a FortiGate HA pair on AWS:

        #### Step 1: Prerequisites

        Before you begin, ensure you have:
        - AWS account with appropriate permissions
        - AWS CLI configured with credentials
        - Terraform installed (version 1.0 or later)
        - FortiGate licenses (for BYOL deployments)
        - VPC with appropriate subnets configured
        - ENIs pre-created in the correct subnets

        #### Step 2: Configuration

        1. Navigate to the **Configuration** page
        2. Configure AWS settings (region, profile, credentials)
        3. Configure network settings (VPC, subnets, ENIs, EIPs)
        4. Configure FortiGate settings (AMI, instance type, passwords)
        5. Configure Transit Gateway (if needed)
        6. Configure monitoring options
        7. Configure backend (local or S3)
        8. Save your configuration

        #### Step 3: AMI Discovery

        1. Navigate to the **AMI Discovery** page
        2. Select FortiGate version, license type, and architecture
        3. Click "Discover AMIs"
        4. Review the discovered AMI details
        5. Click "Use This AMI" to auto-populate the configuration

        #### Step 4: Licensing

        1. Navigate to the **Licensing** page
        2. Select your licensing model (BYOL, OnDemand, or Reserved)
        3. For BYOL: Configure license source (Secrets Manager, S3, or file upload)
        4. Test access to license sources
        5. Review cost implications
        6. Save licensing configuration

        #### Step 5: Cost Analysis

        1. Navigate to the **Cost Analysis** page
        2. Configure cost parameters (duration, instance type, usage pattern)
        3. Click "Calculate Costs"
        4. Review cost comparison charts
        5. Review detailed cost breakdown
        6. Note the recommended licensing model

        #### Step 6: Deployment

        1. Navigate to the **Deployment** page
        2. Review configuration summary
        3. (Optional) Click "Plan Only" to preview changes
        4. Click "Deploy" to start deployment
        5. Monitor progress in real-time
        6. Review deployment results and resource IDs
        7. Access FortiGate management console

        #### Step 7: Post-Deployment

        1. Log into FortiGate management console
        2. Verify HA status
        3. Configure security policies
        4. Test connectivity
        5. Monitor deployment on the **Monitoring** page

        #### Step 8: Cleanup (Optional)

        1. Navigate to the **Deployment** page
        2. Click "Destroy"
        3. Type "DESTROY" to confirm
        4. Click "Confirm Destroy"
        5. Monitor destruction progress
        """)

    # Tab 2: AMI & Licensing Guide
    with tab2:
        st.markdown("### AMI & Licensing Guide")

        st.markdown("""
        #### FortiGate AMI Selection

        **AMI Discovery Process:**
        - The AMI Discovery page queries AWS Marketplace for FortiGate AMIs
        - Filter by version (7.6, 7.4, 7.2, 7.0, 6.4)
        - Filter by license type (BYOL, OnDemand)
        - Filter by architecture (x86_64, arm64)

        **Version Selection Guidelines:**
        - **7.6**: Latest features and security updates (recommended for new deployments)
        - **7.4**: Stable release with proven track record
        - **7.2**: Long-term support release
        - **7.0**: Mature release for conservative deployments
        - **6.4**: Legacy support (not recommended for new deployments)

        **Architecture Selection:**
        - **x86_64**: Standard architecture, widest compatibility
        - **arm64**: AWS Graviton processors, better price/performance ratio

        #### Licensing Models

        **BYOL (Bring Your Own License):**
        - Use existing FortiGate licenses
        - Lower hourly cost (EC2 only)
        - Requires license files or Flex VM tokens
        - Best for: Long-term deployments, existing license holders
        - License sources: AWS Secrets Manager, S3, or file upload

        **OnDemand (Pay-as-you-go):**
        - Hourly licensing included in instance cost
        - No upfront license purchase
        - Higher hourly cost
        - Best for: Short-term deployments, testing, variable workloads
        - No license files required

        **Reserved Instances:**
        - Commit to 1-year or 3-year term
        - Significant cost savings (30-55% off OnDemand)
        - Payment options: No Upfront, Partial Upfront, All Upfront
        - Best for: Stable, long-term production deployments
        - No license files required

        #### License Management

        **AWS Secrets Manager:**
        - Store license content as secrets
        - Secure access control with IAM
        - Automatic rotation support
        - Recommended for production deployments

        **S3 Bucket:**
        - Store license files in S3
        - Simple file-based approach
        - IAM-based access control
        - Good for development/testing

        **File Upload:**
        - Upload license files directly through web interface
        - Convenient for one-time deployments
        - Files stored temporarily during deployment
        - Not recommended for production
        """)

    # Tab 3: Monitoring & Troubleshooting
    with tab3:
        st.markdown("### Monitoring & Troubleshooting")

        st.markdown("""
        #### Monitoring Resources

        **FortiGate Management Console:**
        - Access via public IP or management subnet
        - Default username: admin
        - Password: Set during configuration
        - Monitor HA status, policies, logs, and performance

        **AWS CloudWatch:**
        - EC2 instance metrics (CPU, network, disk)
        - VPC Flow Logs (if enabled)
        - Custom metrics from FortiGate
        - Set up alarms for critical metrics

        **Monitoring Page:**
        - View health status of primary and backup instances
        - Monitor BGP session status
        - View traffic visualization
        - Review recent deployment events

        #### Common Issues & Solutions

        **Issue: Deployment fails during Terraform apply**
        - Check AWS credentials and permissions
        - Verify VPC and subnet configuration
        - Ensure ENIs are in correct subnets and availability zones
        - Review Terraform logs for specific errors

        **Issue: FortiGate instances not accessible**
        - Verify security group rules allow management access
        - Check management CIDR configuration
        - Ensure EIPs are properly associated
        - Verify key pair is correct

        **Issue: HA synchronization not working**
        - Verify HA subnet connectivity
        - Check HA password matches on both instances
        - Ensure HA port (port3) is configured correctly
        - Review FortiGate HA logs

        **Issue: BGP sessions not establishing**
        - Verify Transit Gateway attachment is active
        - Check BGP ASN configuration
        - Ensure route tables are configured correctly
        - Review FortiGate BGP configuration

        **Issue: License validation fails**
        - Verify license files are valid and not expired
        - Check Secrets Manager or S3 access permissions
        - Ensure license matches FortiGate model and version
        - Contact Fortinet support for license issues

        #### Troubleshooting Commands

        **SSH into FortiGate:**
        ```bash
        ssh -i /path/to/keypair.pem admin@<fortigate-ip>
        ```

        **Check HA status:**
        ```
        get system ha status
        ```

        **Check BGP status:**
        ```
        get router info bgp summary
        ```

        **View system resources:**
        ```
        get system performance status
        ```

        **Check license status:**
        ```
        get system status
        ```
        """)

    # Tab 4: Architecture Overview
    with tab4:
        st.markdown("### Architecture Overview")

        st.markdown("""
        #### High-Level Architecture

        The FortiGate HA deployment creates a highly available security architecture:

        ```
        ┌─────────────────────────────────────────────────────────────┐
        │                         AWS Cloud                            │
        │                                                              │
        │  ┌────────────────────────────────────────────────────────┐ │
        │  │                    VPC (10.0.0.0/16)                   │ │
        │  │                                                         │ │
        │  │  ┌──────────────────┐      ┌──────────────────┐      │ │
        │  │  │  Availability    │      │  Availability    │      │ │
        │  │  │  Zone A          │      │  Zone B          │      │ │
        │  │  │                  │      │                  │      │ │
        │  │  │  ┌────────────┐  │      │  ┌────────────┐  │      │ │
        │  │  │  │ FortiGate  │  │      │  │ FortiGate  │  │      │ │
        │  │  │  │ Primary    │◄─┼──────┼─►│ Backup     │  │      │ │
        │  │  │  │ (Active)   │  │      │  │ (Standby)  │  │      │ │
        │  │  │  └────────────┘  │      │  └────────────┘  │      │ │
        │  │  │                  │      │                  │      │ │
        │  │  │  4 ENIs:         │      │  4 ENIs:         │      │ │
        │  │  │  - Public        │      │  - Public        │      │ │
        │  │  │  - Private       │      │  - Private       │      │ │
        │  │  │  - HA Sync       │      │  - HA Sync       │      │ │
        │  │  │  - Management    │      │  - Management    │      │ │
        │  │  └──────────────────┘      └──────────────────┘      │ │
        │  │                                                         │ │
        │  │  ┌──────────────────────────────────────────────────┐ │ │
        │  │  │          Transit Gateway (Optional)              │ │ │
        │  │  │          - BGP Routing                           │ │ │
        │  │  │          - Spoke VPC Connectivity                │ │ │
        │  │  └──────────────────────────────────────────────────┘ │ │
        │  └─────────────────────────────────────────────────────────┘ │
        └─────────────────────────────────────────────────────────────┘
        ```

        #### Components

        **FortiGate Instances:**
        - Two EC2 instances in different availability zones
        - Active-Passive HA configuration
        - Automatic failover with EIP reassignment
        - 4 network interfaces per instance

        **Network Interfaces (ENIs):**
        - **Port 1 (Public/Outside)**: Internet-facing traffic
        - **Port 2 (Private/Inside)**: Internal network traffic
        - **Port 3 (HA Sync)**: HA synchronization and heartbeat
        - **Port 4 (Management)**: Administrative access

        **Elastic IPs (EIPs):**
        - Static public IP addresses
        - Automatic failover during HA events
        - Lambda function for EIP reassignment

        **Transit Gateway (Optional):**
        - Central hub for VPC connectivity
        - BGP routing with FortiGate
        - Spoke VPC attachments
        - Dynamic route propagation

        **Monitoring:**
        - VPC Flow Logs (optional)
        - CloudWatch metrics
        - FortiGate logging

        #### Traffic Flow

        **Inbound Traffic:**
        1. Internet → EIP → FortiGate Port 1 (Public)
        2. FortiGate inspects and applies policies
        3. FortiGate Port 2 (Private) → Internal resources

        **Outbound Traffic:**
        1. Internal resources → FortiGate Port 2 (Private)
        2. FortiGate inspects and applies policies
        3. FortiGate Port 1 (Public) → Internet

        **HA Synchronization:**
        1. Configuration sync via Port 3 (HA Sync)
        2. Heartbeat monitoring
        3. Automatic failover on primary failure
        4. EIP reassignment to backup instance

        #### Security Considerations

        - Management access restricted by CIDR
        - Security groups control traffic flow
        - IAM roles for AWS API access
        - Encrypted EBS volumes
        - VPC Flow Logs for audit trail
        - FortiGate security policies
        """)

    # Tab 5: Configuration Examples
    with tab5:
        st.markdown("### Configuration Examples")

        st.markdown("""
        #### Example 1: Basic BYOL Deployment

        ```yaml
        aws:
          region: us-east-1
          profile: default
          environment: prod
          owner_tag: security-team

        network:
          vpc_id: vpc-0123456789abcdef0
          availability_zones:
            - us-east-1a
            - us-east-1b
          subnets:
            primary:
              public: subnet-0123456789abcdef0
              private: subnet-0123456789abcdef1
              ha_sync: subnet-0123456789abcdef2
              management: subnet-0123456789abcdef3
            backup:
              public: subnet-0123456789abcdef4
              private: subnet-0123456789abcdef5
              ha_sync: subnet-0123456789abcdef6
              management: subnet-0123456789abcdef7
          enis:
            primary: [eni-01, eni-02, eni-03, eni-04]
            backup: [eni-05, eni-06, eni-07, eni-08]
          eips:
            allocate: true
            enable_failover: true

        fortigate:
          ami_id: ami-0123456789abcdef0
          instance_type: c5.xlarge
          key_pair_name: my-keypair
          admin_password: <secure-password>
          ha_password: <secure-password>
          hostname_primary: fortigate-primary
          hostname_backup: fortigate-backup

        licensing:
          type: BYOL
          source: secrets_manager
          primary_secret: fortigate-primary-license
          backup_secret: fortigate-backup-license

        transit_gateway:
          create_new: true
          bgp_asn: 65000
          transit_gateway_asn: 64512
          spoke_vpc_cidrs:
            - 10.1.0.0/16
            - 10.2.0.0/16

        monitoring:
          enable_flow_logs: true
          log_retention_days: 30
          enable_detailed_monitoring: true

        backend:
          type: s3
          s3_bucket: my-terraform-state
          s3_key: fortigate/prod/terraform.tfstate
          s3_region: us-east-1
          dynamodb_table: terraform-state-lock
        ```

        #### Example 2: OnDemand Development Deployment

        ```yaml
        aws:
          region: us-west-2
          profile: dev
          environment: dev
          owner_tag: dev-team

        network:
          vpc_id: vpc-0abcdef123456789
          # ... (similar network config)

        fortigate:
          ami_id: ami-0abcdef123456789
          instance_type: t3.medium
          key_pair_name: dev-keypair
          admin_password: <secure-password>
          ha_password: <secure-password>

        licensing:
          type: OnDemand

        transit_gateway:
          create_new: false

        monitoring:
          enable_flow_logs: false
          enable_detailed_monitoring: false

        backend:
          type: local
        ```

        #### Example 3: Reserved Instance Production Deployment

        ```yaml
        aws:
          region: eu-west-1
          profile: production
          environment: prod
          owner_tag: network-ops

        fortigate:
          ami_id: ami-0123456789abcdef0
          instance_type: c5n.2xlarge
          key_pair_name: prod-keypair

        licensing:
          type: Reserved
          term: 3year
          payment_option: all_upfront

        transit_gateway:
          create_new: true
          bgp_asn: 65000
          transit_gateway_asn: 64512
          spoke_vpc_cidrs:
            - 10.10.0.0/16
            - 10.20.0.0/16
            - 10.30.0.0/16

        monitoring:
          enable_flow_logs: true
          log_retention_days: 365
          enable_detailed_monitoring: true

        backend:
          type: s3
          s3_bucket: prod-terraform-state
          s3_key: fortigate/prod/terraform.tfstate
          s3_region: eu-west-1
          dynamodb_table: prod-terraform-locks
          encrypt: true
        ```
        """)

    # Tab 6: FAQ
    with tab6:
        st.markdown("### Frequently Asked Questions")

        with st.expander("❓ What are the prerequisites for deployment?"):
            st.markdown("""
            - AWS account with appropriate IAM permissions
            - AWS CLI configured with credentials
            - Terraform installed (version 1.0+)
            - VPC with subnets in two availability zones
            - Pre-created ENIs in the correct subnets
            - FortiGate licenses (for BYOL deployments)
            - EC2 key pair for SSH access
            """)

        with st.expander("❓ How long does deployment take?"):
            st.markdown("""
            Typical deployment time:
            - Terraform init: 1-2 minutes
            - Terraform plan: 1-2 minutes
            - Terraform apply: 10-15 minutes
            - Total: 15-20 minutes

            Factors affecting deployment time:
            - AWS region responsiveness
            - Number of resources being created
            - Transit Gateway attachment (adds 5-10 minutes)
            """)

        with st.expander("❓ What instance types are recommended?"):
            st.markdown("""
            **Development/Testing:**
            - t3.medium: Low cost, suitable for testing
            - t3.large: Better performance for dev environments

            **Production:**
            - c5.xlarge: Good balance of performance and cost
            - c5.2xlarge: Higher throughput requirements
            - c5n.xlarge: Network-optimized, 25 Gbps network
            - c5n.2xlarge: High-performance networking

            **Considerations:**
            - Network throughput requirements
            - Number of concurrent connections
            - Security policy complexity
            - Budget constraints
            """)

        with st.expander("❓ How does HA failover work?"):
            st.markdown("""
            **Automatic Failover Process:**
            1. Primary FortiGate failure detected via heartbeat
            2. Backup FortiGate promotes itself to active
            3. Lambda function triggered by CloudWatch event
            4. EIP reassigned from primary to backup
            5. Traffic flows through backup instance
            6. Configuration remains synchronized

            **Failover Time:**
            - Detection: 5-10 seconds
            - EIP reassignment: 10-20 seconds
            - Total: 15-30 seconds

            **Session Handling:**
            - Active sessions may be interrupted
            - New sessions established with backup
            - Session sync can be configured in FortiGate
            """)

        with st.expander("❓ What are the cost differences between licensing models?"):
            st.markdown("""
            **BYOL (Bring Your Own License):**
            - Lowest hourly cost (EC2 only)
            - Requires upfront license purchase
            - Best for long-term deployments
            - Example: $0.17/hour for c5.xlarge (EC2 only)

            **OnDemand:**
            - Higher hourly cost (EC2 + licensing)
            - No upfront costs
            - Best for short-term or variable workloads
            - Example: $1.37/hour for c5.xlarge (EC2 + FortiGate)

            **Reserved Instances:**
            - Significant discounts (30-55%)
            - Requires 1-year or 3-year commitment
            - Best for stable, long-term deployments
            - Example: $0.82/hour for c5.xlarge (40% discount)

            Use the Cost Analysis page for detailed comparisons.
            """)

        with st.expander("❓ Can I use existing ENIs?"):
            st.markdown("""
            Yes, this deployment requires pre-created ENIs. Benefits:
            - Persistent network interfaces
            - Consistent IP addresses
            - Easier troubleshooting
            - Better control over network configuration

            Use the create-enis.py script to create ENIs:
            ```bash
            python3 create-enis.py --config config.yaml
            ```

            ENIs must be:
            - In the correct subnets
            - In the correct availability zones
            - Not attached to any instances
            - Have appropriate security groups
            """)

        with st.expander("❓ How do I access FortiGate after deployment?"):
            st.markdown("""
            **Web Interface:**
            1. Get the management IP from deployment outputs
            2. Open browser: https://<management-ip>
            3. Username: admin
            4. Password: Set during configuration
            5. Accept self-signed certificate warning

            **SSH Access:**
            ```bash
            ssh -i /path/to/keypair.pem admin@<management-ip>
            ```

            **Security:**
            - Management access restricted by CIDR
            - Use VPN or bastion host for production
            - Change default password immediately
            - Enable MFA for admin access
            """)

        with st.expander("❓ What happens if deployment fails?"):
            st.markdown("""
            **Automatic Handling:**
            - Terraform tracks all created resources
            - Partial deployments can be cleaned up
            - State file maintains resource inventory

            **Recovery Options:**
            1. **Fix and Retry**: Correct the issue and redeploy
            2. **Clean Up**: Run terraform destroy to remove resources
            3. **Manual Cleanup**: Remove resources via AWS console

            **Common Failure Causes:**
            - Insufficient IAM permissions
            - Invalid resource IDs (VPC, subnets, ENIs)
            - Resource limits exceeded
            - Network configuration errors

            **Troubleshooting:**
            - Review deployment logs
            - Check Terraform error messages
            - Verify AWS resource configuration
            - Contact support if needed
            """)

        with st.expander("❓ How do I update FortiGate configuration?"):
            st.markdown("""
            **Via Web Interface:**
            1. Log into FortiGate management console
            2. Navigate to desired configuration section
            3. Make changes and apply
            4. Changes sync to backup automatically

            **Via Terraform:**
            1. Update configuration in web app
            2. Export configuration to YAML
            3. Run terraform plan to preview changes
            4. Run terraform apply to apply changes

            **Best Practices:**
            - Test changes in development first
            - Back up configuration before changes
            - Document all changes
            - Use version control for Terraform configs
            - Schedule changes during maintenance windows
            """)

        with st.expander("❓ Can I deploy in multiple regions?"):
            st.markdown("""
            Yes, you can deploy in multiple regions:

            **Approach 1: Separate Deployments**
            - Create separate configurations for each region
            - Use different S3 backend keys
            - Manage each deployment independently

            **Approach 2: Multi-Region Terraform**
            - Use Terraform workspaces
            - Parameterize region-specific values
            - Share common configuration

            **Considerations:**
            - Each region needs its own VPC and subnets
            - ENIs must be created in each region
            - AMI IDs differ by region
            - Licensing applies per deployment
            - Cost multiplies by number of regions
            """)

    # External Documentation Links
    st.markdown("---")
    st.markdown("### 🔗 External Resources")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("""
        **FortiGate Documentation**
        - [FortiGate Administration Guide](https://docs.fortinet.com/product/fortigate)
        - [FortiGate AWS Deployment Guide](https://docs.fortinet.com/document/fortigate-public-cloud/latest/aws-administration-guide)
        - [FortiGate HA Configuration](https://docs.fortinet.com/document/fortigate/latest/administration-guide/98277/ha)
        - [FortiGate CLI Reference](https://docs.fortinet.com/document/fortigate/latest/cli-reference)
        """)

    with col2:
        st.markdown("""
        **AWS Documentation**
        - [AWS VPC Documentation](https://docs.aws.amazon.com/vpc/)
        - [AWS Transit Gateway](https://docs.aws.amazon.com/vpc/latest/tgw/)
        - [AWS EC2 Documentation](https://docs.aws.amazon.com/ec2/)
        - [AWS CloudWatch](https://docs.aws.amazon.com/cloudwatch/)
        """)

    with col3:
        st.markdown("""
        **Support Resources**
        - [Fortinet Support Portal](https://support.fortinet.com/)
        - [FortiGate Community](https://community.fortinet.com/)
        - [AWS Support](https://aws.amazon.com/support/)
        - [Terraform Documentation](https://www.terraform.io/docs/)
        """)


# ============================================================================
# APPLICATION ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    main()
