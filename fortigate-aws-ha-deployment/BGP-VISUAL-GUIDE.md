# BGP Visual Configuration Guide

## Network Topology

```
                    ┌─────────────────────────────────────────┐
                    │      AWS Transit Gateway (TGW)          │
                    │      ASN: 65321                          │
                    │      Router ID: Auto-assigned            │
                    └──────────────┬──────────────┬────────────┘
                                   │              │
                         BGP Peer  │              │  BGP Peer
                         10.0.2.1  │              │  10.0.2.65
                                   │              │
                    ┌──────────────┴──────────────┴────────────┐
                    │     Transit Gateway VPC Attachment       │
                    │     Subnets: inside-primary, inside-backup│
                    └──────────────┬──────────────┬────────────┘
                                   │              │
                    ┌──────────────┴──────────────┴────────────┐
                    │         FortiGate VPC                     │
                    │         10.0.0.0/16                       │
                    │                                           │
                    │  ┌─────────────────────────────────────┐ │
                    │  │    Inside Subnet (Primary)          │ │
                    │  │    10.0.2.0/26                      │ │
                    │  │    Gateway: 10.0.2.1                │ │
                    │  └──────────────┬──────────────────────┘ │
                    │                 │                         │
                    │  ┌──────────────┴──────────────────────┐ │
                    │  │   FortiGate Primary (Active)        │ │
                    │  │   ASN: 65200                        │ │
                    │  │   Router ID: 10.0.2.10              │ │
                    │  │                                     │ │
                    │  │   port1 (outside): 10.0.1.10       │ │
                    │  │   port2 (inside):  10.0.2.10 ◄─────┼─┼─ BGP Neighbor
                    │  │   port3 (ha):      10.0.3.10       │ │
                    │  │   port4 (mgmt):    10.0.4.10       │ │
                    │  └──────────────┬──────────────────────┘ │
                    │                 │ HA Sync                 │
                    │                 │                         │
                    │  ┌──────────────┴──────────────────────┐ │
                    │  │   FortiGate Backup (Standby)        │ │
                    │  │   ASN: 65200                        │ │
                    │  │   Router ID: 10.0.2.74              │ │
                    │  │                                     │ │
                    │  │   port1 (outside): 10.0.1.74       │ │
                    │  │   port2 (inside):  10.0.2.74 ◄─────┼─┼─ BGP Neighbor
                    │  │   port3 (ha):      10.0.3.74       │ │
                    │  │   port4 (mgmt):    10.0.4.74       │ │
                    │  └──────────────┬──────────────────────┘ │
                    │                 │                         │
                    │  ┌──────────────┴──────────────────────┐ │
                    │  │    Inside Subnet (Backup)           │ │
                    │  │    10.0.2.64/26                     │ │
                    │  │    Gateway: 10.0.2.65               │ │
                    │  └─────────────────────────────────────┘ │
                    └───────────────────────────────────────────┘
```

## BGP Session Flow

### Normal Operation (Primary Active)

```
┌──────────────────┐                    ┌──────────────────┐
│  Transit Gateway │                    │ FortiGate Primary│
│  ASN: 65321      │                    │ ASN: 65200       │
│  IP: 10.0.2.1    │                    │ IP: 10.0.2.10    │
└────────┬─────────┘                    └────────┬─────────┘
         │                                       │
         │  1. TCP SYN (port 179)               │
         │◄──────────────────────────────────────│
         │                                       │
         │  2. TCP SYN-ACK                      │
         │──────────────────────────────────────►│
         │                                       │
         │  3. BGP OPEN (AS 65200)              │
         │◄──────────────────────────────────────│
         │                                       │
         │  4. BGP OPEN (AS 65321)              │
         │──────────────────────────────────────►│
         │                                       │
         │  5. BGP KEEPALIVE                    │
         │◄─────────────────────────────────────►│
         │                                       │
         │  6. BGP UPDATE (routes)              │
         │◄─────────────────────────────────────►│
         │                                       │
         │  State: ESTABLISHED ✅                │
         │                                       │
         │  7. Periodic KEEPALIVE (every 30s)   │
         │◄─────────────────────────────────────►│
         │                                       │
```

### HA Failover Scenario

```
Time: T0 (Normal)
┌─────────────┐         ┌──────────────┐         ┌─────────────┐
│   Transit   │         │  FortiGate   │         │  FortiGate  │
│   Gateway   │◄───BGP──┤   Primary    │◄───HA───┤   Backup    │
│             │         │  (ACTIVE)    │         │  (STANDBY)  │
│  10.0.2.1   │         │  10.0.2.10   │         │  10.0.2.74  │
└─────────────┘         └──────────────┘         └─────────────┘
     ✅                        ✅                        ⏸️
  Established              BGP Active              BGP Idle


Time: T1 (Failover Triggered)
┌─────────────┐         ┌──────────────┐         ┌─────────────┐
│   Transit   │         │  FortiGate   │         │  FortiGate  │
│   Gateway   │    ❌    │   Primary    │    ❌    │   Backup    │
│             │         │  (FAILED)    │         │ (BECOMING   │
│  10.0.2.1   │         │  10.0.2.10   │         │  ACTIVE)    │
└─────────────┘         └──────────────┘         └─────────────┘
     ⏸️                        ❌                        🔄
  Waiting                  Down                   Transitioning


Time: T2 (30-60 seconds later)
┌─────────────┐         ┌──────────────┐         ┌─────────────┐
│   Transit   │         │  FortiGate   │         │  FortiGate  │
│   Gateway   │         │   Primary    │         │   Backup    │
│             │◄───BGP──┤  (STANDBY)   │◄───HA───┤  (ACTIVE)   │
│  10.0.2.65  │         │  10.0.2.10   │         │  10.0.2.74  │
└─────────────┘         └──────────────┘         └─────────────┘
     ✅                        ⏸️                        ✅
  Established              BGP Idle               BGP Active
```

## Configuration Comparison

### FortiGate Primary Configuration

```fortios
config router bgp
    set as 65200                    ← Same on both
    set router-id 10.0.2.10         ← Different (Primary IP)
    set ebgp-multipath enable       ← Same on both
    set graceful-restart enable     ← Same on both
    
    config neighbor
        edit "10.0.2.1"             ← Different (Primary subnet gateway)
            set remote-as 65321     ← Same on both
            set interface "port2"   ← Same on both
        next
    end
    
    config network
        edit 1
            set prefix 10.0.0.0 255.255.0.0  ← Same on both
        next
    end
end
```

### FortiGate Backup Configuration

```fortios
config router bgp
    set as 65200                    ← Same on both
    set router-id 10.0.2.74         ← Different (Backup IP)
    set ebgp-multipath enable       ← Same on both
    set graceful-restart enable     ← Same on both
    
    config neighbor
        edit "10.0.2.65"            ← Different (Backup subnet gateway)
            set remote-as 65321     ← Same on both
            set interface "port2"   ← Same on both
        next
    end
    
    config network
        edit 1
            set prefix 10.0.0.0 255.255.0.0  ← Same on both
        next
    end
end
```

## Route Advertisement Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    FortiGate Primary                         │
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │  Local Routes (Configured Networks)                │    │
│  │  - 10.0.0.0/16  (VPC CIDR)                        │    │
│  │  - 10.1.0.0/16  (Spoke VPC 1)                     │    │
│  │  - 10.2.0.0/16  (Spoke VPC 2)                     │    │
│  └────────────────┬───────────────────────────────────┘    │
│                   │                                          │
│                   ▼                                          │
│  ┌────────────────────────────────────────────────────┐    │
│  │  BGP Process                                       │    │
│  │  - Adds BGP attributes (AS-PATH, NEXT-HOP, etc.)  │    │
│  │  - Applies route-maps (if configured)             │    │
│  └────────────────┬───────────────────────────────────┘    │
│                   │                                          │
│                   ▼                                          │
│  ┌────────────────────────────────────────────────────┐    │
│  │  BGP UPDATE Message                                │    │
│  │  - Network: 10.0.0.0/16, AS-PATH: 65200          │    │
│  │  - Network: 10.1.0.0/16, AS-PATH: 65200          │    │
│  │  - Network: 10.2.0.0/16, AS-PATH: 65200          │    │
│  └────────────────┬───────────────────────────────────┘    │
└───────────────────┼──────────────────────────────────────────┘
                    │
                    │ BGP UPDATE
                    ▼
┌─────────────────────────────────────────────────────────────┐
│                  Transit Gateway                             │
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │  BGP Process                                       │    │
│  │  - Receives UPDATE                                 │    │
│  │  - Validates routes                                │    │
│  │  - Adds to BGP table                              │    │
│  └────────────────┬───────────────────────────────────┘    │
│                   │                                          │
│                   ▼                                          │
│  ┌────────────────────────────────────────────────────┐    │
│  │  Transit Gateway Route Table                       │    │
│  │  - 10.0.0.0/16 → FortiGate VPC Attachment        │    │
│  │  - 10.1.0.0/16 → FortiGate VPC Attachment        │    │
│  │  - 10.2.0.0/16 → FortiGate VPC Attachment        │    │
│  │  Type: propagated                                  │    │
│  └────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

## BGP State Machine

```
┌─────────┐
│  IDLE   │  ← Initial state, BGP disabled or waiting
└────┬────┘
     │ Start BGP
     ▼
┌─────────┐
│ CONNECT │  ← Attempting TCP connection to neighbor
└────┬────┘
     │ TCP connection established
     ▼
┌──────────┐
│ACTIVE    │  ← TCP failed, trying to re-establish
└────┬─────┘
     │ TCP connection successful
     ▼
┌──────────┐
│OPENSENT  │  ← Sent BGP OPEN message, waiting for reply
└────┬─────┘
     │ Received OPEN message
     ▼
┌────────────┐
│OPENCONFIRM │  ← Received OPEN, waiting for KEEPALIVE
└────┬───────┘
     │ Received KEEPALIVE
     ▼
┌──────────────┐
│ ESTABLISHED  │  ← ✅ BGP session is UP and working!
└──────┬───────┘
       │ Periodic KEEPALIVE exchange
       │ Route updates exchanged
       │
       │ If connection lost or error
       ▼
┌─────────┐
│  IDLE   │  ← Back to start
└─────────┘
```

## Verification Workflow

```
┌─────────────────────────────────────────────────────────────┐
│                  Verification Steps                          │
└─────────────────────────────────────────────────────────────┘

Step 1: Check FortiGate BGP Status
┌──────────────────────────────────────┐
│ get router info bgp summary          │
│                                      │
│ Expected:                            │
│ Neighbor: 10.0.2.1                  │
│ State: Established ✅                │
│ PfxRcd: > 0                         │
└──────────────────────────────────────┘
                │
                ▼
Step 2: Check Received Routes
┌──────────────────────────────────────┐
│ get router info bgp neighbors        │
│ 10.0.2.1 received-routes            │
│                                      │
│ Expected:                            │
│ Routes from Transit Gateway          │
│ (Spoke VPC CIDRs)                   │
└──────────────────────────────────────┘
                │
                ▼
Step 3: Check Advertised Routes
┌──────────────────────────────────────┐
│ get router info bgp neighbors        │
│ 10.0.2.1 advertised-routes          │
│                                      │
│ Expected:                            │
│ Routes advertised to TGW             │
│ (Your configured networks)           │
└──────────────────────────────────────┘
                │
                ▼
Step 4: Check Routing Table
┌──────────────────────────────────────┐
│ get router info routing-table bgp    │
│                                      │
│ Expected:                            │
│ BGP routes in routing table          │
│ Next-hop: 10.0.2.1                  │
└──────────────────────────────────────┘
                │
                ▼
Step 5: Check AWS Transit Gateway
┌──────────────────────────────────────┐
│ aws ec2 search-transit-gateway-      │
│ routes --filters Type=propagated     │
│                                      │
│ Expected:                            │
│ Routes from FortiGate                │
│ State: active                        │
└──────────────────────────────────────┘
                │
                ▼
Step 6: Test Traffic Flow
┌──────────────────────────────────────┐
│ Ping from spoke VPC to FortiGate VPC │
│ or vice versa                        │
│                                      │
│ Expected:                            │
│ Traffic flows through FortiGate      │
│ Packets visible in FortiGate logs    │
└──────────────────────────────────────┘
```

## Common BGP States Visual

### ✅ Healthy State

```
FortiGate                    Transit Gateway
┌──────────┐                ┌──────────┐
│   BGP    │◄──KEEPALIVE───►│   BGP    │
│ Router   │                │ Router   │
│          │◄───UPDATE─────►│          │
│ State:   │                │ State:   │
│ESTABLISH │                │ESTABLISH │
└──────────┘                └──────────┘
    ✅                          ✅
```

### ⚠️ Warning State (Active)

```
FortiGate                    Transit Gateway
┌──────────┐                ┌──────────┐
│   BGP    │────TCP SYN────►│   BGP    │
│ Router   │                │ Router   │
│          │◄───NO REPLY────│          │
│ State:   │                │ State:   │
│ ACTIVE   │                │  IDLE    │
└──────────┘                └──────────┘
    ⚠️                          ❌
```

### ❌ Critical State (Idle)

```
FortiGate                    Transit Gateway
┌──────────┐                ┌──────────┐
│   BGP    │                │   BGP    │
│ Router   │    NO TRAFFIC  │ Router   │
│          │                │          │
│ State:   │                │ State:   │
│  IDLE    │                │  IDLE    │
└──────────┘                └──────────┘
    ❌                          ❌
```

## Quick Reference Table

| Component | Value | Location |
|-----------|-------|----------|
| **FortiGate Primary** | | |
| ASN | 65200 | config router bgp → set as |
| Router ID | 10.0.2.10 | config router bgp → set router-id |
| BGP Neighbor | 10.0.2.1 | config router bgp → config neighbor |
| Interface | port2 | config router bgp → config neighbor → set interface |
| **FortiGate Backup** | | |
| ASN | 65200 | config router bgp → set as |
| Router ID | 10.0.2.74 | config router bgp → set router-id |
| BGP Neighbor | 10.0.2.65 | config router bgp → config neighbor |
| Interface | port2 | config router bgp → config neighbor → set interface |
| **Transit Gateway** | | |
| ASN | 65321 | TGW configuration |
| Primary Peer IP | 10.0.2.1 | Inside subnet gateway |
| Backup Peer IP | 10.0.2.65 | Inside subnet gateway |

---

**Pro Tip**: Save this diagram and refer to it when troubleshooting BGP issues. The visual representation helps identify where the problem might be in the BGP session establishment process.
