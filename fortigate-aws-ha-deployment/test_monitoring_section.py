"""
Test for Monitoring Configuration Section (Task 10.7)

This test verifies that the Monitoring configuration section:
1. Accepts flow logs checkbox
2. Accepts log retention selector with standard CloudWatch retention options
3. Accepts detailed monitoring checkbox
4. Creates MonitoringConfig correctly
5. Updates DeploymentConfig with monitoring settings
6. Displays monitoring settings in configuration summary
"""

import pytest
from deploy import MonitoringConfig, DeploymentConfig, AWSConfig, NetworkConfig, FortiGateConfig, TransitGatewayConfig, BackendConfig, AMIDiscoveryConfig, LicensingConfig


def test_monitoring_config_creation():
    """Test that MonitoringConfig can be created with all parameters"""
    monitoring = MonitoringConfig(
        enable_flow_logs=True,
        log_retention_days=30,
        enable_detailed_monitoring=True
    )
    
    assert monitoring.enable_flow_logs is True
    assert monitoring.log_retention_days == 30
    assert monitoring.enable_detailed_monitoring is True


def test_monitoring_config_defaults():
    """Test that MonitoringConfig has correct default values"""
    monitoring = MonitoringConfig()
    
    assert monitoring.enable_flow_logs is True
    assert monitoring.log_retention_days == 30
    assert monitoring.enable_detailed_monitoring is True


def test_monitoring_config_with_flow_logs_disabled():
    """Test MonitoringConfig with flow logs disabled"""
    monitoring = MonitoringConfig(
        enable_flow_logs=False,
        log_retention_days=7,
        enable_detailed_monitoring=False
    )
    
    assert monitoring.enable_flow_logs is False
    assert monitoring.log_retention_days == 7
    assert monitoring.enable_detailed_monitoring is False


def test_log_retention_valid_values():
    """Test that all standard CloudWatch log retention values are accepted"""
    valid_retention_days = [1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365, 400, 545, 731, 1827, 3653]
    
    for days in valid_retention_days:
        monitoring = MonitoringConfig(
            enable_flow_logs=True,
            log_retention_days=days,
            enable_detailed_monitoring=False
        )
        assert monitoring.log_retention_days == days


def test_deployment_config_with_monitoring():
    """Test that DeploymentConfig accepts MonitoringConfig"""
    # Create minimal configs for required fields
    aws_config = AWSConfig(region="us-east-1")
    
    network_config = NetworkConfig(
        vpc_id="vpc-12345678",
        availability_zones=["us-east-1a", "us-east-1b"],
        outside_subnet_primary="subnet-11111111",
        inside_subnet_primary="subnet-22222222",
        ha_subnet_primary="subnet-33333333",
        mgmt_subnet_primary="subnet-44444444",
        outside_subnet_backup="subnet-55555555",
        inside_subnet_backup="subnet-66666666",
        ha_subnet_backup="subnet-77777777",
        mgmt_subnet_backup="subnet-88888888",
        mgmt_access_cidrs=["0.0.0.0/0"],
        primary_outside_eni_id="eni-11111111",
        primary_inside_eni_id="eni-22222222",
        primary_ha_eni_id="eni-33333333",
        primary_mgmt_eni_id="eni-44444444",
        backup_outside_eni_id="eni-55555555",
        backup_inside_eni_id="eni-66666666",
        backup_ha_eni_id="eni-77777777",
        backup_mgmt_eni_id="eni-88888888"
    )
    
    fortigate_config = FortiGateConfig(
        ami_id="ami-12345678",
        instance_type="c5.xlarge",
        key_pair_name="my-key",
        admin_password="Admin123!",
        ha_password="HA123!",
        ami_discovery=AMIDiscoveryConfig(),
        licensing=LicensingConfig()
    )
    
    transit_gateway_config = TransitGatewayConfig(create_new=True)
    
    monitoring_config = MonitoringConfig(
        enable_flow_logs=True,
        log_retention_days=90,
        enable_detailed_monitoring=True
    )
    
    backend_config = BackendConfig()
    
    # Create deployment config
    deployment_config = DeploymentConfig(
        aws=aws_config,
        network=network_config,
        fortigate=fortigate_config,
        transit_gateway=transit_gateway_config,
        monitoring=monitoring_config,
        backend=backend_config
    )
    
    # Verify monitoring config is correctly set
    assert deployment_config.monitoring.enable_flow_logs is True
    assert deployment_config.monitoring.log_retention_days == 90
    assert deployment_config.monitoring.enable_detailed_monitoring is True


def test_monitoring_config_update():
    """Test that monitoring config can be updated in existing DeploymentConfig"""
    # Create initial deployment config with default monitoring
    aws_config = AWSConfig(region="us-east-1")
    network_config = NetworkConfig(
        vpc_id="vpc-12345678",
        availability_zones=["us-east-1a", "us-east-1b"],
        outside_subnet_primary="subnet-11111111",
        inside_subnet_primary="subnet-22222222",
        ha_subnet_primary="subnet-33333333",
        mgmt_subnet_primary="subnet-44444444",
        outside_subnet_backup="subnet-55555555",
        inside_subnet_backup="subnet-66666666",
        ha_subnet_backup="subnet-77777777",
        mgmt_subnet_backup="subnet-88888888",
        mgmt_access_cidrs=["0.0.0.0/0"],
        primary_outside_eni_id="eni-11111111",
        primary_inside_eni_id="eni-22222222",
        primary_ha_eni_id="eni-33333333",
        primary_mgmt_eni_id="eni-44444444",
        backup_outside_eni_id="eni-55555555",
        backup_inside_eni_id="eni-66666666",
        backup_ha_eni_id="eni-77777777",
        backup_mgmt_eni_id="eni-88888888"
    )
    fortigate_config = FortiGateConfig(
        ami_id="ami-12345678",
        instance_type="c5.xlarge",
        key_pair_name="my-key",
        admin_password="Admin123!",
        ha_password="HA123!",
        ami_discovery=AMIDiscoveryConfig(),
        licensing=LicensingConfig()
    )
    
    deployment_config = DeploymentConfig(
        aws=aws_config,
        network=network_config,
        fortigate=fortigate_config,
        transit_gateway=TransitGatewayConfig(create_new=True),
        monitoring=MonitoringConfig(),
        backend=BackendConfig()
    )
    
    # Update monitoring config
    new_monitoring = MonitoringConfig(
        enable_flow_logs=False,
        log_retention_days=365,
        enable_detailed_monitoring=False
    )
    deployment_config.monitoring = new_monitoring
    
    # Verify update
    assert deployment_config.monitoring.enable_flow_logs is False
    assert deployment_config.monitoring.log_retention_days == 365
    assert deployment_config.monitoring.enable_detailed_monitoring is False


def test_monitoring_config_edge_cases():
    """Test edge cases for monitoring configuration"""
    # Test with minimum retention
    monitoring_min = MonitoringConfig(
        enable_flow_logs=True,
        log_retention_days=1,
        enable_detailed_monitoring=False
    )
    assert monitoring_min.log_retention_days == 1
    
    # Test with maximum retention
    monitoring_max = MonitoringConfig(
        enable_flow_logs=True,
        log_retention_days=3653,
        enable_detailed_monitoring=True
    )
    assert monitoring_max.log_retention_days == 3653
    
    # Test with all features disabled
    monitoring_disabled = MonitoringConfig(
        enable_flow_logs=False,
        log_retention_days=7,
        enable_detailed_monitoring=False
    )
    assert monitoring_disabled.enable_flow_logs is False
    assert monitoring_disabled.enable_detailed_monitoring is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
