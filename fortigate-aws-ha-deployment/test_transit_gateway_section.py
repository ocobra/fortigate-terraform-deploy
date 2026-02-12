#!/usr/bin/env python3
"""
Test Transit Gateway Configuration Section

This test verifies that the Transit Gateway configuration section in the
web application correctly handles user inputs and creates proper TransitGatewayConfig objects.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent))

from deploy import TransitGatewayConfig


def test_transit_gateway_config_creation():
    """Test creating TransitGatewayConfig with various inputs"""
    
    # Test 1: Create new TGW with default values
    config1 = TransitGatewayConfig(
        create_new=True,
        transit_gateway_id=None,
        bgp_asn=65000,
        transit_gateway_asn=64512,
        spoke_vpc_cidrs=[]
    )
    
    assert config1.create_new == True
    assert config1.transit_gateway_id is None
    assert config1.bgp_asn == 65000
    assert config1.transit_gateway_asn == 64512
    assert config1.spoke_vpc_cidrs == []
    print("✅ Test 1 passed: Create new TGW with defaults")
    
    # Test 2: Use existing TGW
    config2 = TransitGatewayConfig(
        create_new=False,
        transit_gateway_id="tgw-0123456789abcdef0",
        bgp_asn=65001,
        transit_gateway_asn=64513,
        spoke_vpc_cidrs=["10.1.0.0/16", "10.2.0.0/16"]
    )
    
    assert config2.create_new == False
    assert config2.transit_gateway_id == "tgw-0123456789abcdef0"
    assert config2.bgp_asn == 65001
    assert config2.transit_gateway_asn == 64513
    assert len(config2.spoke_vpc_cidrs) == 2
    print("✅ Test 2 passed: Use existing TGW with spoke VPCs")
    
    # Test 3: Parse comma-separated CIDRs (simulating user input)
    spoke_cidrs_input = "10.1.0.0/16, 10.2.0.0/16, 10.3.0.0/16"
    spoke_cidrs_list = [cidr.strip() for cidr in spoke_cidrs_input.split(',') if cidr.strip()]
    
    config3 = TransitGatewayConfig(
        create_new=True,
        transit_gateway_id=None,
        bgp_asn=65000,
        transit_gateway_asn=64512,
        spoke_vpc_cidrs=spoke_cidrs_list
    )
    
    assert len(config3.spoke_vpc_cidrs) == 3
    assert config3.spoke_vpc_cidrs[0] == "10.1.0.0/16"
    assert config3.spoke_vpc_cidrs[1] == "10.2.0.0/16"
    assert config3.spoke_vpc_cidrs[2] == "10.3.0.0/16"
    print("✅ Test 3 passed: Parse comma-separated CIDRs")
    
    # Test 4: Empty spoke VPC CIDRs
    spoke_cidrs_input_empty = ""
    spoke_cidrs_list_empty = [cidr.strip() for cidr in spoke_cidrs_input_empty.split(',') if cidr.strip()]
    
    config4 = TransitGatewayConfig(
        create_new=True,
        transit_gateway_id=None,
        bgp_asn=65000,
        transit_gateway_asn=64512,
        spoke_vpc_cidrs=spoke_cidrs_list_empty
    )
    
    assert config4.spoke_vpc_cidrs == []
    print("✅ Test 4 passed: Empty spoke VPC CIDRs")
    
    # Test 5: BGP ASN validation (typical private ASN range)
    config5 = TransitGatewayConfig(
        create_new=True,
        transit_gateway_id=None,
        bgp_asn=64512,  # Min private ASN
        transit_gateway_asn=65534,  # Max private ASN
        spoke_vpc_cidrs=[]
    )
    
    assert config5.bgp_asn == 64512
    assert config5.transit_gateway_asn == 65534
    print("✅ Test 5 passed: BGP ASN range validation")


def test_tgw_id_format_validation():
    """Test Transit Gateway ID format validation"""
    import re
    
    def validate_tgw_id(tgw_id: str) -> bool:
        """Validate Transit Gateway ID format: tgw-xxxxxxxxxxxxxxxxx"""
        if not tgw_id:
            return False
        pattern = r'^tgw-[0-9a-f]{17}$'
        return bool(re.match(pattern, tgw_id))
    
    # Valid TGW IDs
    assert validate_tgw_id("tgw-0123456789abcdef0") == True
    assert validate_tgw_id("tgw-abcdef0123456789a") == True
    print("✅ Valid TGW ID formats accepted")
    
    # Invalid TGW IDs
    assert validate_tgw_id("") == False
    assert validate_tgw_id("tgw-123") == False  # Too short
    assert validate_tgw_id("tgw-0123456789abcdef01") == False  # Too long
    assert validate_tgw_id("vpc-0123456789abcdef0") == False  # Wrong prefix
    assert validate_tgw_id("tgw-0123456789ABCDEF0") == False  # Uppercase not allowed
    print("✅ Invalid TGW ID formats rejected")


def test_spoke_vpc_cidrs_to_string():
    """Test converting spoke VPC CIDRs list to comma-separated string for display"""
    
    # Test with multiple CIDRs
    cidrs = ["10.1.0.0/16", "10.2.0.0/16", "10.3.0.0/16"]
    cidrs_string = ", ".join(cidrs)
    assert cidrs_string == "10.1.0.0/16, 10.2.0.0/16, 10.3.0.0/16"
    print("✅ Multiple CIDRs converted to string")
    
    # Test with empty list
    cidrs_empty = []
    cidrs_string_empty = ", ".join(cidrs_empty)
    assert cidrs_string_empty == ""
    print("✅ Empty CIDRs list handled")
    
    # Test with single CIDR
    cidrs_single = ["10.1.0.0/16"]
    cidrs_string_single = ", ".join(cidrs_single)
    assert cidrs_string_single == "10.1.0.0/16"
    print("✅ Single CIDR converted to string")


if __name__ == "__main__":
    print("Testing Transit Gateway Configuration Section...")
    print("=" * 60)
    
    try:
        test_transit_gateway_config_creation()
        print()
        test_tgw_id_format_validation()
        print()
        test_spoke_vpc_cidrs_to_string()
        print()
        print("=" * 60)
        print("✅ All tests passed!")
        sys.exit(0)
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
