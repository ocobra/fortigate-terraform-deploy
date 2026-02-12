#!/usr/bin/env python3
"""
Minimal test for Tasks 3.2, 3.3, 3.4 - JSON import/export and validation
This test extracts only the necessary code to avoid streamlit dependency
"""

import sys
import json
import yaml
import re
import copy
from pathlib import Path
from dataclasses import asdict
from typing import Dict, Any, List, Tuple

# Add the deployment engine to the path
sys.path.append(str(Path(__file__).parent))

from deploy import (
    DeploymentConfig, AWSConfig, NetworkConfig,
    FortiGateConfig, TransitGatewayConfig, MonitoringConfig, BackendConfig,
    AMIDiscoveryConfig, LicensingConfig
)


class ConfigurationManager:
    """Minimal ConfigurationManager for testing"""
    
    def import_json(self, json_content: str) -> DeploymentConfig:
        """Parse JSON configuration file"""
        config_dict = json.loads(json_content)
        if not isinstance(config_dict, dict):
            raise ValueError("JSON content must be an object")
        
        aws_config = AWSConfig(**config_dict.get('aws', {}))
        network_dict = config_dict.get('network', {})
        network_config = NetworkConfig(**network_dict)
        
        fortigate_dict = config_dict.get('fortigate', {})
        ami_discovery_dict = fortigate_dict.get('ami_discovery', {})
        ami_discovery = AMIDiscoveryConfig(**ami_discovery_dict)
        licensing_dict = fortigate_dict.get('licensing', {})
        licensing = LicensingConfig(**licensing_dict)
        
        fortigate_config = FortiGateConfig(
            ami_id=fortigate_dict.get('ami_id'),
            ami_discovery=ami_discovery,
            licensing=licensing,
            instance_type=fortigate_dict.get('instance_type'),
            key_pair_name=fortigate_dict.get('key_pair_name'),
            admin_password=fortigate_dict.get('admin_password'),
            ha_password=fortigate_dict.get('ha_password'),
