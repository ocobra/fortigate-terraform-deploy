# BGP Quick Check - FortiGate & Transit Gateway

## 🚀 Quick Start - 5 Minute BGP Setup

### 1. Configure FortiGate Primary (2 minutes)

```fortios
config router bgp
    set as 65200
    set router-id 10.0.2.10
    config neighbor
        edit "10.0.2.1"
            set remote-as 65321
            set interface "port2"
        next
    end
    config network
        edit 1
            set prefix 10.0.0.0 255.255.0.0
        next
    end
end
```

### 2. Configure FortiGate Backup (2 minutes)

```fortios
config router bgp
    set as 65200
    set router-id 10.0.2.74
    config neighbor
        edit "10.0.2.65"
            set remote-as 65321
            set interface "port2"
        next
    end
    config network
        edit 1
            set prefix 10.0.0.0 255.255.0.0
        next
    end
end
```

### 3. Verify BGP (1 minute)

```fortios
get router info bgp summary
```

**Expected**: `State/PfxRcd` shows `Established` and route count

---

## ✅ BGP Health Check Checklist

### Pre-Flight Checks

- [ ] FortiGate HA pair is operational
- [ ] Transit Gateway is created
- [ ] Transit Gateway attached to FortiGate VPC
- [ ] Inside subnets included in TGW attachment
- [ ] Security groups allow BGP (TCP 179)
- [ ] FortiGate can ping Transit Gateway (.1 of inside subnet)

### Configuration Checks

- [ ] BGP ASN configured on FortiGate (65200)
- [ ] BGP router-id set (FortiGate inside IP)
- [ ] BGP neighbor configured (TGW IP)
- [ ] BGP neighbor remote-as set (65321)
- [ ] BGP neighbor interface set (port2)
- [ ] Networks configured to advertise
- [ ] Route propagation enabled on TGW route table

### Verification Checks

- [ ] BGP state = **Established**
- [ ] Prefixes received > 0
- [ ] Prefixes advertised > 0
- [ ] Routes appear in FortiGate routing table
- [ ] Routes appear in TGW route table
- [ ] Traffic flows through FortiGate

---

## 🔍 One-Command Health Check

### On FortiGate

```fortios
get router info bgp summary
```

**Good Output**:
```
Neighbor        V    AS MsgRcvd MsgSent   TblVer  InQ OutQ Up/Down  State/PfxRcd
10.0.2.1        4 65321      45      42        5    0    0 00:15:23        3
                                                                      ↑
                                                                 Established!
```

**Bad Output**:
```
Neighbor        V    AS MsgRcvd MsgSent   TblVer  InQ OutQ Up/Down  State/PfxRcd
10.0.2.1        4 65321       0       0        0    0    0 00:05:23   Active
                                                                      ↑
                                                                   Not working!
```

### On AWS

```bash
aws ec2 search-transit-gateway-routes \
  --transit-gateway-route-table-id $TGW_RTB_ID \
  --filters "Name=type,Values=propagated" \
  --profile renaws --region us-east-1 \
  --query 'Routes[*].[DestinationCidrBlock,State]' \
  --output table
```

**Good Output**: Shows routes with State = `active`

---

## 🐛 Troubleshooting Decision Tree

### BGP State = Active or Connect

```
Is FortiGate able to ping Transit Gateway?
├─ NO → Check security groups, route tables, TGW attachment
└─ YES → Check BGP configuration
    ├─ Correct neighbor IP? (10.0.2.1 or 10.0.2.65)
    ├─ Correct remote-as? (65321)
    ├─ Correct interface? (port2)
    └─ Correct local AS? (65200)
```

### BGP State = Established, No Routes Received

```
Are routes being advertised from Transit Gateway?
├─ Check TGW route table has routes
├─ Check route propagation is enabled
└─ On FortiGate: get router info bgp neighbors <ip> received-routes
```

### BGP State = Established, Routes Not Advertised

```
Are networks configured in BGP?
├─ Check: config router bgp → config network
├─ Check: get router info bgp neighbors <ip> advertised-routes
└─ Try: execute router clear bgp all
```

---

## 📊 Monitoring Commands

### Every 5 Minutes

```fortios
# Quick status check
get router info bgp summary | grep -A1 Neighbor
```

### Every Hour

```fortios
# Detailed neighbor check
get router info bgp neighbors 10.0.2.1 | grep -E "BGP state|Prefixes|Up/Down"
```

### Daily

```bash
# AWS side check
aws ec2 search-transit-gateway-routes \
  --transit-gateway-route-table-id $TGW_RTB_ID \
  --filters "Name=state,Values=active" \
  --profile renaws --region us-east-1 \
  --query 'length(Routes[?Type==`propagated`])'
```

---

## 🔧 Quick Fixes

### Reset BGP Session

```fortios
execute router clear bgp all
```

Wait 30 seconds, then check:
```fortios
get router info bgp summary
```

### Re-advertise Routes

```fortios
execute router clear bgp all soft out
```

### Force BGP Restart

```fortios
execute router restart
```

---

## 📱 Status Indicators

### BGP Session Health

| Indicator | Status | Action |
|-----------|--------|--------|
| State = Established | ✅ Healthy | None |
| State = Active | ⚠️ Warning | Check connectivity |
| State = Idle | ❌ Critical | Check configuration |
| Prefixes > 0 | ✅ Healthy | None |
| Prefixes = 0 | ⚠️ Warning | Check route propagation |
| Up/Down < 5 min | ⚠️ Warning | Session just started |
| Up/Down > 1 hour | ✅ Healthy | Stable session |

### HA Status with BGP

| Scenario | Primary BGP | Backup BGP | Status |
|----------|-------------|------------|--------|
| Normal | Established | Idle/Connect | ✅ Correct |
| Failover | Idle/Connect | Established | ✅ Correct |
| Both Active | Established | Established | ⚠️ Check HA |
| Both Idle | Idle | Idle | ❌ Problem |

---

## 🎯 Success Criteria

Your BGP setup is working correctly when:

1. ✅ `get router info bgp summary` shows `Established`
2. ✅ Prefixes received > 0
3. ✅ Prefixes advertised > 0
4. ✅ `get router info routing-table bgp` shows routes
5. ✅ AWS TGW route table shows propagated routes
6. ✅ Traffic flows through FortiGate
7. ✅ HA failover maintains BGP connectivity

---

## 📞 Emergency Commands

### If BGP is completely broken:

```fortios
# 1. Check basic connectivity
execute ping 10.0.2.1

# 2. Check interface status
get system interface port2

# 3. Check routing to TGW
get router info routing-table details 10.0.2.1

# 4. Check HA status
get system ha status

# 5. Enable debug
diagnose debug application bgpd -1
diagnose debug enable

# 6. Watch for errors (Ctrl+C to stop)
# Look for connection errors, authentication issues, etc.

# 7. Disable debug
diagnose debug disable
diagnose debug reset
```

### If you need to start over:

```fortios
# Remove BGP configuration
config router bgp
    delete neighbor "10.0.2.1"
end

# Wait 30 seconds

# Re-add configuration
config router bgp
    config neighbor
        edit "10.0.2.1"
            set remote-as 65321
            set interface "port2"
        next
    end
end
```

---

## 🔗 Quick Links

- Full Guide: [BGP-CONFIGURATION-GUIDE.md](BGP-CONFIGURATION-GUIDE.md)
- Deployment: [DEPLOY-NOW.md](DEPLOY-NOW.md)
- Troubleshooting: See "Common Issues" in BGP-CONFIGURATION-GUIDE.md

---

**Remember**: 
- Only the **active** FortiGate should have BGP session in Established state
- After HA failover, wait 30-60 seconds for BGP to re-establish
- Always check both FortiGate and AWS sides when troubleshooting
