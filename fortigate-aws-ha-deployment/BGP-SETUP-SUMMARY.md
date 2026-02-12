# BGP Setup Summary - Quick Reference

## 📚 Documentation Overview

Three comprehensive guides have been created to help you establish and verify BGP sessions between your FortiGate HA pair and AWS Transit Gateway:

### 1. BGP-CONFIGURATION-GUIDE.md (Complete Guide)
**Purpose**: Comprehensive step-by-step configuration guide

**Contents**:
- Architecture overview
- Prerequisites checklist
- Detailed configuration steps for both FortiGates
- Transit Gateway configuration
- Verification procedures
- Troubleshooting common issues
- Monitoring and maintenance

**When to use**: First-time setup, detailed troubleshooting, reference documentation

### 2. BGP-QUICK-CHECK.md (Quick Reference)
**Purpose**: Fast health checks and troubleshooting

**Contents**:
- 5-minute quick start
- One-command health checks
- Troubleshooting decision tree
- Quick fixes
- Status indicators

**When to use**: Daily operations, quick status checks, rapid troubleshooting

### 3. BGP-VISUAL-GUIDE.md (Visual Reference)
**Purpose**: Visual diagrams and flowcharts

**Contents**:
- Network topology diagrams
- BGP session flow
- HA failover scenarios
- Route advertisement flow
- BGP state machine
- Verification workflow

**When to use**: Understanding architecture, explaining to others, visual troubleshooting

---

## 🚀 Quick Start (5 Minutes)

### Step 1: Configure FortiGate Primary

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

### Step 2: Configure FortiGate Backup

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

### Step 3: Verify

```fortios
get router info bgp summary
```

**Expected**: State shows `Established` with route count > 0

---

## ✅ Success Checklist

- [ ] FortiGate Primary BGP state = Established
- [ ] FortiGate Backup BGP state = Idle (if standby) or Established (if active)
- [ ] Prefixes received > 0
- [ ] Prefixes advertised > 0
- [ ] Routes visible in FortiGate routing table
- [ ] Routes visible in Transit Gateway route table
- [ ] Traffic flows through FortiGate
- [ ] HA failover maintains BGP connectivity

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
```
✅ State shows route count (3) = Established and working

**Bad Output**:
```
Neighbor        V    AS MsgRcvd MsgSent   TblVer  InQ OutQ Up/Down  State/PfxRcd
10.0.2.1        4 65321       0       0        0    0    0 00:05:23   Active
```
❌ State shows "Active" = Not working

### On AWS

```bash
aws ec2 search-transit-gateway-routes \
  --transit-gateway-route-table-id $TGW_RTB_ID \
  --filters "Name=type,Values=propagated" \
  --profile renaws --region us-east-1
```

✅ Should show routes with State = `active`

---

## 🎯 Key Configuration Values

| Parameter | Primary | Backup | Notes |
|-----------|---------|--------|-------|
| **FortiGate ASN** | 65200 | 65200 | Same on both |
| **Router ID** | 10.0.2.10 | 10.0.2.74 | Different (inside IP) |
| **BGP Neighbor** | 10.0.2.1 | 10.0.2.65 | Different (TGW gateway) |
| **Remote ASN** | 65321 | 65321 | Same on both |
| **Interface** | port2 | port2 | Same on both |
| **Networks** | 10.0.0.0/16 | 10.0.0.0/16 | Same on both |

---

## 🐛 Common Issues & Quick Fixes

### Issue: BGP State = Active

**Quick Fix**:
```fortios
# Test connectivity
execute ping 10.0.2.1

# If ping fails, check:
# 1. Security groups allow BGP (TCP 179)
# 2. Transit Gateway attachment is available
# 3. Inside subnets are attached to TGW
```

### Issue: BGP Established but No Routes

**Quick Fix**:
```bash
# Enable route propagation on AWS
aws ec2 enable-transit-gateway-route-table-propagation \
  --transit-gateway-route-table-id $TGW_RTB_ID \
  --transit-gateway-attachment-id tgw-attach-xxxxx \
  --profile renaws --region us-east-1
```

### Issue: Routes Not Advertised

**Quick Fix**:
```fortios
# Clear BGP session to re-advertise
execute router clear bgp all soft out
```

---

## 📊 Monitoring Commands

### Daily Health Check

```fortios
# Quick status
get router info bgp summary

# Detailed check
get router info bgp neighbors 10.0.2.1 | grep -E "BGP state|Prefixes"
```

### Weekly Verification

```bash
# Check AWS side
aws ec2 search-transit-gateway-routes \
  --transit-gateway-route-table-id $TGW_RTB_ID \
  --filters "Name=state,Values=active" \
  --profile renaws --region us-east-1 \
  --query 'length(Routes[?Type==`propagated`])'
```

---

## 🔧 Emergency Commands

### If BGP is Broken

```fortios
# 1. Check connectivity
execute ping 10.0.2.1

# 2. Check interface
get system interface port2

# 3. Enable debug
diagnose debug application bgpd -1
diagnose debug enable

# 4. Watch for errors (Ctrl+C to stop)

# 5. Disable debug
diagnose debug disable
diagnose debug reset
```

### Reset BGP Session

```fortios
execute router clear bgp all
```

Wait 30 seconds, then verify:
```fortios
get router info bgp summary
```

---

## 📱 Status Indicators

| Indicator | Meaning | Action |
|-----------|---------|--------|
| State = Established | ✅ Working | None |
| State = Active | ⚠️ Problem | Check connectivity |
| State = Idle | ❌ Critical | Check configuration |
| Prefixes > 0 | ✅ Routes exchanged | None |
| Prefixes = 0 | ⚠️ No routes | Check propagation |

---

## 🎓 Understanding BGP States

```
IDLE → CONNECT → ACTIVE → OPENSENT → OPENCONFIRM → ESTABLISHED
  ↑                                                        │
  └────────────────────────────────────────────────────────┘
                    (If connection lost)
```

**Target State**: ESTABLISHED ✅

---

## 🔗 Related Documentation

- **Full Configuration**: [BGP-CONFIGURATION-GUIDE.md](BGP-CONFIGURATION-GUIDE.md)
- **Quick Checks**: [BGP-QUICK-CHECK.md](BGP-QUICK-CHECK.md)
- **Visual Diagrams**: [BGP-VISUAL-GUIDE.md](BGP-VISUAL-GUIDE.md)
- **Deployment Guide**: [DEPLOY-NOW.md](DEPLOY-NOW.md)
- **EIP Support**: [EIP-SUPPORT-SUMMARY.md](EIP-SUPPORT-SUMMARY.md)

---

## 💡 Pro Tips

1. **Only the active FortiGate should have BGP in Established state**
   - Primary active → Primary BGP Established, Backup BGP Idle
   - After failover → Backup BGP Established, Primary BGP Idle

2. **After HA failover, wait 30-60 seconds for BGP to re-establish**
   - BGP needs time to detect failover and establish new session

3. **Always check both FortiGate and AWS sides when troubleshooting**
   - FortiGate: `get router info bgp summary`
   - AWS: `aws ec2 search-transit-gateway-routes`

4. **Use graceful restart to minimize downtime during failover**
   ```fortios
   config router bgp
       set graceful-restart enable
   end
   ```

5. **Monitor BGP session uptime**
   - Stable sessions should show uptime > 1 hour
   - Frequent resets indicate network issues

---

## 📞 Need Help?

1. Check the comprehensive guide: [BGP-CONFIGURATION-GUIDE.md](BGP-CONFIGURATION-GUIDE.md)
2. Review common issues section
3. Enable BGP debugging: `diagnose debug application bgpd -1`
4. Check FortiGate logs: `execute log display`
5. Verify Transit Gateway attachment state
6. Ensure security groups allow BGP (TCP 179)

---

## ✨ Summary

BGP between FortiGate and Transit Gateway enables:
- Dynamic routing between FortiGate VPC and spoke VPCs
- Automatic route propagation
- High availability with HA failover
- Scalable network architecture

**Key Success Metric**: `get router info bgp summary` shows `Established` with routes

**Next Steps**:
1. Configure BGP on both FortiGates
2. Verify BGP sessions are established
3. Test traffic flow through FortiGate
4. Test HA failover with BGP
5. Set up monitoring and alerts

Good luck with your BGP configuration! 🚀
