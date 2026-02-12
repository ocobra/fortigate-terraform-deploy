# BGP Configuration Guide - FortiGate HA with AWS Transit Gateway

## Overview

This guide covers how to establish BGP sessions between your FortiGate HA pair and AWS Transit Gateway, and how to verify the sessions are working correctly.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     AWS Transit Gateway                      │
│                    ASN: 65321 (configurable)                 │
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │         Transit Gateway Attachment                  │    │
│  │         (VPC Attachment to FortiGate VPC)          │    │
│  └────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ BGP Peering
                            │
┌─────────────────────────────────────────────────────────────┐
│                    FortiGate HA Pair                         │
│                    ASN: 65200 (configurable)                 │
│                                                              │
│  ┌──────────────────────┐      ┌──────────────────────┐   │
│  │  FortiGate Primary   │      │  FortiGate Backup    │   │
│  │  Inside: 10.0.2.10   │◄────►│  Inside: 10.0.2.74   │   │
│  │  (Active BGP)        │  HA  │  (Standby BGP)       │   │
│  └──────────────────────┘      └──────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## Prerequisites

1. FortiGate HA pair deployed and operational
2. Transit Gateway created and attached to FortiGate VPC
3. Transit Gateway attachment includes the "inside" subnets
4. FortiGate instances have connectivity to Transit Gateway
5. BGP ASN numbers decided:
   - FortiGate ASN (default: 65200)
   - Transit Gateway ASN (default: 65321)

## Step 1: Verify Transit Gateway Attachment

### Using AWS CLI

```bash
# Get Transit Gateway attachment details
aws ec2 describe-transit-gateway-vpc-attachments \
  --filters "Name=vpc-id,Values=vpc-0e16490e6ab8422fb" \
  --profile renaws \
  --region us-east-1 \
  --query 'TransitGatewayVpcAttachments[*].[TransitGatewayAttachmentId,State,SubnetIds]' \
  --output table

# Expected output:
# tgw-attach-xxxxx | available | [subnet-inside-primary, subnet-inside-backup]
```

### Verify Attachment Includes Inside Subnets

The Transit Gateway attachment MUST include the FortiGate "inside" subnets where BGP peering will occur.

```bash
# Check which subnets are attached
aws ec2 describe-transit-gateway-vpc-attachments \
  --transit-gateway-attachment-ids tgw-attach-xxxxx \
  --profile renaws \
  --region us-east-1 \
  --query 'TransitGatewayVpcAttachments[0].SubnetIds'
```

## Step 2: Configure BGP on FortiGate Primary

### Access FortiGate CLI

```bash
# SSH to FortiGate Primary management interface
ssh admin@<primary-mgmt-ip>
```

### Configure BGP Router

```fortios
# Enter configuration mode
config router bgp
    set as 65200
    set router-id 10.0.2.10
    set ebgp-multipath enable
    set graceful-restart enable
    
    # Configure neighbor (Transit Gateway)
    config neighbor
        edit "10.0.2.1"
            set remote-as 65321
            set soft-reconfiguration enable
            set interface "port2"
            set connect-timer 10
            set advertisement-interval 5
            set link-down-failover enable
        next
    end
    
    # Configure network to advertise
    config network
        edit 1
            set prefix 10.0.0.0 255.255.0.0
        next
        edit 2
            set prefix 10.1.0.0 255.255.0.0
        next
        edit 3
            set prefix 10.2.0.0 255.255.0.0
        next
    end
    
    # Configure redistribute connected (optional)
    config redistribute "connected"
        set status enable
    end
    
    # Configure redistribute static (optional)
    config redistribute "static"
        set status enable
    end
end
```

### Key Configuration Parameters

- **AS**: Your FortiGate ASN (65200)
- **Router ID**: Primary FortiGate inside IP (10.0.2.10)
- **Neighbor**: Transit Gateway IP (typically .1 of inside subnet)
- **Remote AS**: Transit Gateway ASN (65321)
- **Interface**: Inside interface (port2)

## Step 3: Configure BGP on FortiGate Backup

### Access FortiGate Backup CLI

```bash
# SSH to FortiGate Backup management interface
ssh admin@<backup-mgmt-ip>
```

### Configure BGP Router

```fortios
# Enter configuration mode
config router bgp
    set as 65200
    set router-id 10.0.2.74
    set ebgp-multipath enable
    set graceful-restart enable
    
    # Configure neighbor (Transit Gateway)
    config neighbor
        edit "10.0.2.65"
            set remote-as 65321
            set soft-reconfiguration enable
            set interface "port2"
            set connect-timer 10
            set advertisement-interval 5
            set link-down-failover enable
        next
    end
    
    # Configure network to advertise (same as primary)
    config network
        edit 1
            set prefix 10.0.0.0 255.255.0.0
        next
        edit 2
            set prefix 10.1.0.0 255.255.0.0
        next
        edit 3
            set prefix 10.2.0.0 255.255.0.0
        next
    end
    
    # Configure redistribute connected (optional)
    config redistribute "connected"
        set status enable
    end
    
    # Configure redistribute static (optional)
    config redistribute "static"
        set status enable
    end
end
```

### Key Differences from Primary

- **Router ID**: Backup FortiGate inside IP (10.0.2.74)
- **Neighbor**: Transit Gateway IP in backup subnet (10.0.2.65)

## Step 4: Configure Transit Gateway Route Table

### Enable BGP Propagation

```bash
# Get Transit Gateway route table ID
TGW_RTB_ID=$(aws ec2 describe-transit-gateway-route-tables \
  --filters "Name=transit-gateway-id,Values=tgw-0c0228dc5dffa8fa9" \
  --profile renaws \
  --region us-east-1 \
  --query 'TransitGatewayRouteTables[0].TransitGatewayRouteTableId' \
  --output text)

# Enable route propagation for FortiGate VPC attachment
aws ec2 enable-transit-gateway-route-table-propagation \
  --transit-gateway-route-table-id $TGW_RTB_ID \
  --transit-gateway-attachment-id tgw-attach-xxxxx \
  --profile renaws \
  --region us-east-1
```

### Add Static Routes (if needed)

```bash
# Add static route to FortiGate VPC through attachment
aws ec2 create-transit-gateway-route \
  --destination-cidr-block 10.0.0.0/16 \
  --transit-gateway-route-table-id $TGW_RTB_ID \
  --transit-gateway-attachment-id tgw-attach-xxxxx \
  --profile renaws \
  --region us-east-1
```

## Step 5: Verify BGP Sessions

### On FortiGate - Check BGP Summary

```fortios
# Check BGP summary
get router info bgp summary

# Expected output:
# BGP router identifier 10.0.2.10, local AS number 65200
# BGP table version is 5
# 
# Neighbor        V    AS MsgRcvd MsgSent   TblVer  InQ OutQ Up/Down  State/PfxRcd
# 10.0.2.1        4 65321      45      42        5    0    0 00:15:23        3
```

### On FortiGate - Check BGP Neighbors

```fortios
# Check BGP neighbor details
get router info bgp neighbors 10.0.2.1

# Expected output shows:
# - BGP state: Established
# - BGP uptime
# - Prefixes received
# - Prefixes advertised
```

### On FortiGate - Check BGP Routes

```fortios
# Check received routes from Transit Gateway
get router info bgp network

# Check routing table
get router info routing-table all

# Check specific BGP routes
get router info bgp neighbors 10.0.2.1 routes
```

### Using AWS CLI - Check Transit Gateway Routes

```bash
# Get Transit Gateway route table
aws ec2 describe-transit-gateway-route-tables \
  --filters "Name=transit-gateway-id,Values=tgw-0c0228dc5dffa8fa9" \
  --profile renaws \
  --region us-east-1

# Search for routes from FortiGate
aws ec2 search-transit-gateway-routes \
  --transit-gateway-route-table-id $TGW_RTB_ID \
  --filters "Name=type,Values=propagated" \
  --profile renaws \
  --region us-east-1 \
  --query 'Routes[*].[DestinationCidrBlock,State,Type]' \
  --output table
```

### Using AWS Console

1. Go to VPC Dashboard → Transit Gateways
2. Select your Transit Gateway
3. Click "Route Tables" tab
4. Select the route table
5. Click "Routes" tab
6. Look for routes with Type = "propagated" from FortiGate attachment

## Step 6: Test BGP Session Status

### FortiGate CLI Commands

```fortios
# 1. Check BGP summary (most important)
get router info bgp summary

# 2. Check BGP neighbor state
get router info bgp neighbors 10.0.2.1 | grep "BGP state"
# Should show: BGP state = Established

# 3. Check received routes
get router info bgp neighbors 10.0.2.1 received-routes

# 4. Check advertised routes
get router info bgp neighbors 10.0.2.1 advertised-routes

# 5. Check BGP statistics
diagnose ip router bgp all

# 6. Check routing table for BGP routes
get router info routing-table bgp
```

### Expected BGP States

| State | Meaning |
|-------|---------|
| **Established** | ✅ BGP session is UP and working |
| Active | Trying to establish connection |
| Connect | TCP connection in progress |
| Idle | BGP is disabled or waiting to start |
| OpenSent | Sent OPEN message, waiting for reply |
| OpenConfirm | Received OPEN, waiting for KEEPALIVE |

### Troubleshooting Commands

```fortios
# Debug BGP
diagnose debug application bgpd -1
diagnose debug enable

# Check BGP events
diagnose ip router bgp level info
diagnose ip router bgp all

# Check interface status
get system interface physical

# Check routing
get router info routing-table details 10.0.2.1

# Ping Transit Gateway
execute ping 10.0.2.1
```

## Step 7: Verify HA BGP Behavior

### Check Active FortiGate

```fortios
# On both FortiGates, check HA status
get system ha status

# Expected output shows:
# - Which is Master (active)
# - Which is Slave (standby)
# - HA sync status
```

### Verify Only Active FortiGate Has BGP Session

```fortios
# On Primary (if active)
get router info bgp summary
# Should show: Neighbor state = Established

# On Backup (if standby)
get router info bgp summary
# Should show: Neighbor state = Idle or Connect
# (Standby FortiGate may not have active BGP session)
```

### Test HA Failover

```fortios
# On Primary FortiGate, trigger failover
execute ha failover set 1

# Wait 30 seconds, then check BGP on Backup
get router info bgp summary
# Should now show: Neighbor state = Established
```

## Common Issues and Solutions

### Issue 1: BGP State Stuck in "Active" or "Connect"

**Symptoms**:
```
Neighbor        V    AS MsgRcvd MsgSent   TblVer  InQ OutQ Up/Down  State/PfxRcd
10.0.2.1        4 65321       0       0        0    0    0 00:05:23   Active
```

**Causes**:
- No network connectivity to Transit Gateway
- Security group blocking BGP (TCP port 179)
- Wrong neighbor IP address
- Transit Gateway attachment not in "available" state

**Solutions**:
```bash
# 1. Test connectivity
execute ping 10.0.2.1

# 2. Check security group allows BGP
aws ec2 describe-security-groups \
  --group-ids sg-xxxxx \
  --profile renaws \
  --region us-east-1 \
  --query 'SecurityGroups[0].IpPermissions[?FromPort==`179`]'

# 3. Verify Transit Gateway attachment
aws ec2 describe-transit-gateway-vpc-attachments \
  --filters "Name=vpc-id,Values=vpc-0e16490e6ab8422fb" \
  --profile renaws \
  --region us-east-1

# 4. Check route table has route to Transit Gateway
get router info routing-table all
```

### Issue 2: BGP Session Established but No Routes

**Symptoms**:
```
BGP state = Established
Prefixes received: 0
```

**Causes**:
- Transit Gateway not advertising routes
- Route propagation not enabled
- No routes in Transit Gateway route table

**Solutions**:
```bash
# 1. Enable route propagation
aws ec2 enable-transit-gateway-route-table-propagation \
  --transit-gateway-route-table-id $TGW_RTB_ID \
  --transit-gateway-attachment-id tgw-attach-xxxxx \
  --profile renaws \
  --region us-east-1

# 2. Check Transit Gateway routes
aws ec2 search-transit-gateway-routes \
  --transit-gateway-route-table-id $TGW_RTB_ID \
  --filters "Name=state,Values=active" \
  --profile renaws \
  --region us-east-1

# 3. On FortiGate, check soft-reconfiguration
config router bgp
    config neighbor
        edit "10.0.2.1"
            set soft-reconfiguration enable
        next
    end
end
```

### Issue 3: Routes Not Advertised to Transit Gateway

**Symptoms**:
- BGP session established
- FortiGate shows routes in BGP table
- Transit Gateway doesn't receive routes

**Causes**:
- Network not configured in BGP
- Route-map filtering routes
- Redistribute not enabled

**Solutions**:
```fortios
# 1. Check advertised routes
get router info bgp neighbors 10.0.2.1 advertised-routes

# 2. Add networks to advertise
config router bgp
    config network
        edit 1
            set prefix 10.0.0.0 255.255.0.0
        next
    end
end

# 3. Enable redistribute
config router bgp
    config redistribute "connected"
        set status enable
    end
    config redistribute "static"
        set status enable
    end
end

# 4. Clear BGP session to re-advertise
execute router clear bgp all
```

### Issue 4: BGP Session Flapping

**Symptoms**:
- BGP session goes up and down repeatedly
- "Up/Down" time keeps resetting

**Causes**:
- Network instability
- HA failover occurring
- Keepalive/hold timer mismatch

**Solutions**:
```fortios
# 1. Increase timers
config router bgp
    config neighbor
        edit "10.0.2.1"
            set keep-alive-timer 30
            set holdtime-timer 90
        next
    end
end

# 2. Enable graceful restart
config router bgp
    set graceful-restart enable
end

# 3. Check HA status
get system ha status

# 4. Monitor BGP events
diagnose debug application bgpd -1
diagnose debug enable
```

## Monitoring and Maintenance

### Regular Health Checks

```bash
# Create monitoring script
cat > check-bgp.sh << 'EOF'
#!/bin/bash
# Check BGP status on FortiGate

echo "=== BGP Summary ==="
ssh admin@<fortigate-ip> "get router info bgp summary"

echo ""
echo "=== BGP Neighbor State ==="
ssh admin@<fortigate-ip> "get router info bgp neighbors 10.0.2.1 | grep 'BGP state'"

echo ""
echo "=== Received Routes Count ==="
ssh admin@<fortigate-ip> "get router info bgp neighbors 10.0.2.1 | grep 'Prefixes received'"

echo ""
echo "=== HA Status ==="
ssh admin@<fortigate-ip> "get system ha status | grep Mode"
EOF

chmod +x check-bgp.sh
./check-bgp.sh
```

### CloudWatch Alarms (Optional)

Create CloudWatch alarms for Transit Gateway metrics:
- BytesIn/BytesOut
- PacketsIn/PacketsOut
- PacketDropCountBlackhole

### Logging

```fortios
# Enable BGP logging
config log memory filter
    set router enable
end

# View logs
execute log filter category 0
execute log display
```

## Quick Reference Card

### Essential Commands

| Task | Command |
|------|---------|
| Check BGP status | `get router info bgp summary` |
| Check neighbor state | `get router info bgp neighbors <ip>` |
| Check received routes | `get router info bgp neighbors <ip> received-routes` |
| Check advertised routes | `get router info bgp neighbors <ip> advertised-routes` |
| Check routing table | `get router info routing-table bgp` |
| Clear BGP session | `execute router clear bgp all` |
| Debug BGP | `diagnose debug application bgpd -1` |
| Check HA status | `get system ha status` |

### Expected Values

| Parameter | Value |
|-----------|-------|
| FortiGate ASN | 65200 (configurable) |
| Transit Gateway ASN | 65321 (configurable) |
| BGP State | **Established** |
| Neighbor IP (Primary) | 10.0.2.1 (inside subnet gateway) |
| Neighbor IP (Backup) | 10.0.2.65 (inside subnet gateway) |
| Interface | port2 (inside interface) |

## Next Steps

1. ✅ Verify BGP sessions are established
2. ✅ Confirm routes are being exchanged
3. ✅ Test traffic flow through FortiGate
4. ✅ Test HA failover with BGP
5. ✅ Set up monitoring and alerts
6. ✅ Document your specific BGP configuration

## Additional Resources

- [FortiGate BGP Configuration Guide](https://docs.fortinet.com/document/fortigate/latest/administration-guide/399023/bgp)
- [AWS Transit Gateway BGP](https://docs.aws.amazon.com/vpc/latest/tgw/tgw-bgp.html)
- [FortiGate HA with BGP](https://docs.fortinet.com/document/fortigate/latest/administration-guide/954635/ha-with-bgp)

---

**Need Help?**
- Check FortiGate logs: `execute log display`
- Enable BGP debugging: `diagnose debug application bgpd -1`
- Verify Transit Gateway attachment state
- Check security groups allow BGP (TCP 179)
- Ensure inside subnets are attached to Transit Gateway
