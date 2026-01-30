# FortiGate AWS HA Deployment - Monitoring and Troubleshooting Guide

## Overview

This comprehensive guide provides detailed instructions for monitoring, logging, and troubleshooting FortiGate AWS HA deployments. It covers VPC Flow Logs, CloudWatch monitoring, FortiGate-specific logging, network troubleshooting, and performance optimization.

## Table of Contents

1. [VPC Flow Logs Configuration](#vpc-flow-logs-configuration)
2. [CloudWatch Monitoring Setup](#cloudwatch-monitoring-setup)
3. [FortiGate Logging Configuration](#fortigate-logging-configuration)
4. [Network Troubleshooting](#network-troubleshooting)
5. [Performance Monitoring](#performance-monitoring)
6. [Common Issues and Solutions](#common-issues-and-solutions)
7. [Disaster Recovery](#disaster-recovery)
8. [Alerting and Notifications](#alerting-and-notifications)

## VPC Flow Logs Configuration

### Overview

VPC Flow Logs capture information about IP traffic going to and from network interfaces in your VPC. This is essential for troubleshooting connectivity issues and monitoring traffic patterns.

### Enabling VPC Flow Logs

#### 1. Enable Flow Logs for VPC

```bash
# Create VPC Flow Logs
aws ec2 create-flow-logs \
  --resource-type VPC \
  --resource-ids vpc-12345678 \
  --traffic-type ALL \
  --log-destination-type cloud-watch-logs \
  --log-group-name /aws/vpc/flowlogs \
  --deliver-logs-permission-arn arn:aws:iam::123456789012:role/flowlogsRole
```

#### 2. Enable Flow Logs for Subnets

```bash
# Enable for all FortiGate subnets
for subnet in subnet-outside1 subnet-inside1 subnet-ha1 subnet-mgmt1 subnet-outside2 subnet-inside2 subnet-ha2 subnet-mgmt2; do
  aws ec2 create-flow-logs \
    --resource-type Subnet \
    --resource-ids $subnet \
    --traffic-type ALL \
    --log-destination-type cloud-watch-logs \
    --log-group-name /aws/vpc/flowlogs/subnets
done
```

#### 3. Enable Flow Logs for ENIs

```bash
# Enable for FortiGate ENIs
aws ec2 create-flow-logs \
  --resource-type NetworkInterface \
  --resource-ids eni-fortigate1-outside eni-fortigate1-inside eni-fortigate1-ha eni-fortigate1-mgmt \
  --traffic-type ALL \
  --log-destination-type cloud-watch-logs \
  --log-group-name /aws/vpc/flowlogs/enis
```

### Flow Logs Analysis

#### Understanding Flow Log Format

```
version account-id interface-id srcaddr dstaddr srcport dstport protocol packets bytes windowstart windowend action flowlogstatus
```

Example log entry:
```
2 123456789012 eni-1235b8ca 172.31.16.139 172.31.16.21 20641 22 6 20 4249 1418530010 1418530070 ACCEPT OK
```

#### Common CloudWatch Insights Queries

**1. Top Talkers by Bytes:**
```sql
fields @timestamp, srcaddr, dstaddr, bytes
| filter action = "ACCEPT"
| stats sum(bytes) as total_bytes by srcaddr, dstaddr
| sort total_bytes desc
| limit 20
```

**2. Rejected Traffic Analysis:**
```sql
fields @timestamp, srcaddr, dstaddr, srcport, dstport, protocol
| filter action = "REJECT"
| stats count() as reject_count by srcaddr, dstaddr, dstport
| sort reject_count desc
| limit 50
```

**3. FortiGate Traffic Patterns:**
```sql
fields @timestamp, srcaddr, dstaddr, srcport, dstport, bytes
| filter srcaddr like /^10\./ or dstaddr like /^10\./
| stats sum(bytes) as internal_traffic by bin(5m)
| sort @timestamp desc
```

**4. BGP Traffic Monitoring:**
```sql
fields @timestamp, srcaddr, dstaddr, srcport, dstport
| filter (srcport = 179 or dstport = 179)
| stats count() as bgp_connections by srcaddr, dstaddr
| sort bgp_connections desc
```

**5. HA Heartbeat Traffic:**
```sql
fields @timestamp, srcaddr, dstaddr, protocol, bytes
| filter (srcaddr like /172\.31\.3\./ and dstaddr like /172\.31\.3\./) 
| stats sum(bytes) as ha_traffic by bin(1m)
| sort @timestamp desc
```

### Flow Logs Terraform Configuration

```hcl
# VPC Flow Logs
resource "aws_flow_log" "vpc_flow_log" {
  iam_role_arn    = aws_iam_role.flow_log_role.arn
  log_destination = aws_cloudwatch_log_group.vpc_flow_log.arn
  traffic_type    = "ALL"
  vpc_id          = var.vpc_id

  tags = {
    Name = "FortiGate-VPC-FlowLogs"
  }
}

resource "aws_cloudwatch_log_group" "vpc_flow_log" {
  name              = "/aws/vpc/fortigate-flowlogs"
  retention_in_days = 30

  tags = {
    Name = "FortiGate-VPC-FlowLogs"
  }
}

# IAM Role for Flow Logs
resource "aws_iam_role" "flow_log_role" {
  name = "fortigate-flowlogs-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "vpc-flow-logs.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy" "flow_log_policy" {
  name = "fortigate-flowlogs-policy"
  role = aws_iam_role.flow_log_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "logs:DescribeLogGroups",
          "logs:DescribeLogStreams"
        ]
        Effect   = "Allow"
        Resource = "*"
      }
    ]
  })
}
```

## CloudWatch Monitoring Setup

### CloudWatch Log Groups

The deployment creates several log groups for comprehensive monitoring:

#### 1. VPC Flow Logs
- **Log Group**: `/aws/vpc/fortigate-flowlogs`
- **Purpose**: Network traffic analysis
- **Retention**: 30 days

#### 2. FortiGate System Logs
- **Log Group**: `/aws/ec2/fortigate/system`
- **Purpose**: FortiGate system events and errors
- **Retention**: 90 days

#### 3. FortiGate Traffic Logs
- **Log Group**: `/aws/ec2/fortigate/traffic`
- **Purpose**: Security policy decisions and traffic flows
- **Retention**: 30 days

#### 4. FortiGate Event Logs
- **Log Group**: `/aws/ec2/fortigate/event`
- **Purpose**: Administrative events and configuration changes
- **Retention**: 90 days

### CloudWatch Metrics

#### Custom Metrics Configuration

```python
import boto3
import json
from datetime import datetime

cloudwatch = boto3.client('cloudwatch')

def put_custom_metric(metric_name, value, unit='Count', namespace='FortiGate/HA'):
    """Put custom metric to CloudWatch"""
    try:
        cloudwatch.put_metric_data(
            Namespace=namespace,
            MetricData=[
                {
                    'MetricName': metric_name,
                    'Value': value,
                    'Unit': unit,
                    'Timestamp': datetime.utcnow()
                }
            ]
        )
    except Exception as e:
        print(f"Error putting metric {metric_name}: {e}")

# Example usage
put_custom_metric('HAStatus', 1, 'Count')  # 1 = Active, 0 = Passive
put_custom_metric('BGPSessions', 2, 'Count')
put_custom_metric('ThroughputMbps', 150.5, 'Count/Second')
```

#### Key Metrics to Monitor

**1. FortiGate HA Status:**
- Primary/Secondary status
- HA sync status
- Failover events

**2. Network Performance:**
- Throughput (Mbps)
- Packet rate (PPS)
- Connection count
- Latency

**3. BGP Status:**
- BGP session state
- Route count
- BGP flaps

**4. System Health:**
- CPU utilization
- Memory usage
- Disk usage
- Temperature

### CloudWatch Dashboards

#### Main Dashboard Configuration

```json
{
  "widgets": [
    {
      "type": "metric",
      "properties": {
        "metrics": [
          ["AWS/EC2", "CPUUtilization", "InstanceId", "i-fortigate-primary"],
          [".", ".", ".", "i-fortigate-backup"]
        ],
        "period": 300,
        "stat": "Average",
        "region": "us-east-1",
        "title": "FortiGate CPU Utilization"
      }
    },
    {
      "type": "metric",
      "properties": {
        "metrics": [
          ["AWS/EC2", "NetworkIn", "InstanceId", "i-fortigate-primary"],
          [".", "NetworkOut", ".", "."],
          [".", "NetworkIn", ".", "i-fortigate-backup"],
          [".", "NetworkOut", ".", "."]
        ],
        "period": 300,
        "stat": "Average",
        "region": "us-east-1",
        "title": "Network Traffic"
      }
    },
    {
      "type": "log",
      "properties": {
        "query": "SOURCE '/aws/vpc/fortigate-flowlogs'\n| fields @timestamp, srcaddr, dstaddr, bytes\n| filter action = \"ACCEPT\"\n| stats sum(bytes) as total_bytes by bin(5m)\n| sort @timestamp desc",
        "region": "us-east-1",
        "title": "Traffic Volume Over Time"
      }
    }
  ]
}
```

#### Create Dashboard with AWS CLI

```bash
aws cloudwatch put-dashboard \
  --dashboard-name "FortiGate-HA-Monitoring" \
  --dashboard-body file://dashboard-config.json
```

### CloudWatch Alarms

#### Critical Alarms

**1. FortiGate Instance Health:**
```bash
aws cloudwatch put-metric-alarm \
  --alarm-name "FortiGate-Primary-StatusCheck" \
  --alarm-description "FortiGate primary instance status check" \
  --metric-name StatusCheckFailed \
  --namespace AWS/EC2 \
  --statistic Maximum \
  --period 60 \
  --threshold 1 \
  --comparison-operator GreaterThanOrEqualToThreshold \
  --dimensions Name=InstanceId,Value=i-fortigate-primary \
  --evaluation-periods 2 \
  --alarm-actions arn:aws:sns:us-east-1:123456789012:fortigate-alerts
```

**2. High CPU Usage:**
```bash
aws cloudwatch put-metric-alarm \
  --alarm-name "FortiGate-High-CPU" \
  --alarm-description "FortiGate high CPU utilization" \
  --metric-name CPUUtilization \
  --namespace AWS/EC2 \
  --statistic Average \
  --period 300 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold \
  --dimensions Name=InstanceId,Value=i-fortigate-primary \
  --evaluation-periods 2 \
  --alarm-actions arn:aws:sns:us-east-1:123456789012:fortigate-alerts
```

**3. BGP Session Down:**
```bash
aws cloudwatch put-metric-alarm \
  --alarm-name "FortiGate-BGP-Session-Down" \
  --alarm-description "BGP session is down" \
  --metric-name BGPSessions \
  --namespace FortiGate/HA \
  --statistic Average \
  --period 60 \
  --threshold 1 \
  --comparison-operator LessThanThreshold \
  --evaluation-periods 1 \
  --alarm-actions arn:aws:sns:us-east-1:123456789012:fortigate-alerts
```

## FortiGate Logging Configuration

### System Logging Setup

#### 1. Configure Syslog to CloudWatch

```bash
# FortiGate CLI commands
config log syslogd setting
    set status enable
    set server "cloudwatch-logs-endpoint"
    set port 514
    set facility local7
    set source-ip 10.0.1.10
    set format default
end

config log syslogd filter
    set severity information
    set forward-traffic enable
    set local-traffic enable
    set multicast-traffic enable
    set sniffer-traffic disable
    set anomaly enable
    set voip disable
end
```

#### 2. Traffic Logging Configuration

```bash
# Enable traffic logging
config log fortianalyzer setting
    set status enable
    set server "cloudwatch-logs-endpoint"
    set source-ip 10.0.1.10
end

# Configure traffic log filters
config log fortianalyzer filter
    set severity information
    set forward-traffic enable
    set local-traffic enable
    set multicast-traffic enable
    set sniffer-traffic disable
end
```

#### 3. Event Logging Configuration

```bash
# Configure event logging
config log eventfilter
    set event enable
    set system enable
    set vpn enable
    set user enable
    set router enable
    set wireless-activity enable
    set wan-opt enable
    set endpoint enable
    set ha enable
    set compliance-check enable
    set security-rating enable
end
```

### Log Analysis Queries

#### 1. Security Events

```sql
fields @timestamp, @message
| filter @message like /attack/
| stats count() as attack_count by bin(1h)
| sort @timestamp desc
```

#### 2. HA Events

```sql
fields @timestamp, @message
| filter @message like /HA/
| parse @message /HA (?<event_type>\w+)/
| stats count() as ha_events by event_type
| sort ha_events desc
```

#### 3. BGP Events

```sql
fields @timestamp, @message
| filter @message like /BGP/
| parse @message /BGP (?<bgp_event>\w+)/
| stats count() as bgp_events by bgp_event, bin(5m)
| sort @timestamp desc
```

#### 4. Traffic Analysis

```sql
fields @timestamp, @message
| filter @message like /traffic/
| parse @message /src=(?<src_ip>\S+) dst=(?<dst_ip>\S+) bytes=(?<bytes>\d+)/
| stats sum(bytes) as total_bytes by src_ip, dst_ip
| sort total_bytes desc
| limit 20
```

### Log Retention and Archiving

#### CloudWatch Logs Retention

```bash
# Set retention for different log groups
aws logs put-retention-policy \
  --log-group-name /aws/ec2/fortigate/system \
  --retention-in-days 90

aws logs put-retention-policy \
  --log-group-name /aws/ec2/fortigate/traffic \
  --retention-in-days 30

aws logs put-retention-policy \
  --log-group-name /aws/ec2/fortigate/event \
  --retention-in-days 90
```

#### S3 Archiving

```bash
# Export logs to S3 for long-term storage
aws logs create-export-task \
  --log-group-name /aws/ec2/fortigate/traffic \
  --from 1609459200000 \
  --to 1612137600000 \
  --destination fortigate-logs-archive \
  --destination-prefix traffic-logs/
```

## Network Troubleshooting

### BGP Troubleshooting

#### 1. Check BGP Status

```bash
# FortiGate CLI commands
get router info bgp summary
get router info bgp neighbors
get router info routing-table bgp
```

#### 2. BGP Debug Commands

```bash
# Enable BGP debugging
diagnose ip router bgp level info
diagnose ip router bgp show

# Check specific neighbor
diagnose ip router bgp neighbor 169.254.100.1
```

#### 3. Common BGP Issues

**Issue: BGP Session Not Establishing**
```bash
# Check BGP configuration
show router bgp
show router route-map

# Verify connectivity to BGP peer
execute ping 169.254.100.1

# Check security groups and NACLs
aws ec2 describe-security-groups --group-ids sg-12345678
```

**Issue: Routes Not Being Advertised**
```bash
# Check route advertisement
get router info bgp neighbors 169.254.100.1 advertised-routes
get router info bgp neighbors 169.254.100.1 received-routes

# Verify route-map configuration
show router route-map
```

### Routing Troubleshooting

#### 1. Route Table Analysis

```bash
# Check FortiGate routing table
get router info routing-table all

# Check specific routes
get router info routing-table details 0.0.0.0/0
get router info routing-table details 10.0.0.0/8
```

#### 2. AWS Route Table Verification

```bash
# Check VPC route tables
aws ec2 describe-route-tables --filters "Name=vpc-id,Values=vpc-12345678"

# Check Transit Gateway route tables
aws ec2 describe-transit-gateway-route-tables
aws ec2 search-transit-gateway-routes \
  --transit-gateway-route-table-id tgw-rtb-12345678 \
  --filters "Name=state,Values=active"
```

#### 3. Connectivity Testing

```bash
# Test connectivity from FortiGate
execute ping 8.8.8.8
execute traceroute 8.8.8.8

# Test from spoke VPCs
# (Run from EC2 instances in spoke VPCs)
ping 8.8.8.8
traceroute 8.8.8.8
```

### Traffic Flow Analysis

#### 1. Packet Capture

```bash
# FortiGate packet capture
diagnose sniffer packet any "host 10.0.1.100" 4 100
diagnose sniffer packet port1 "tcp port 80" 6 50
```

#### 2. Session Analysis

```bash
# Check active sessions
get system session list
get system session filter
get system session filter src 10.0.1.100
```

#### 3. Policy Analysis

```bash
# Check policy matches
diagnose firewall iprope lookup 10.0.1.100 80 10.0.2.100 8080 tcp
get firewall policy
```

### HA Troubleshooting

#### 1. HA Status Check

```bash
# Check HA status
get system ha status
get system ha peer

# Check HA synchronization
diagnose sys ha status
diagnose sys ha checksum cluster
```

#### 2. Common HA Issues

**Issue: HA Sync Failure**
```bash
# Check HA configuration
show system ha
show system interface

# Verify HA heartbeat
diagnose sys ha heartbeat
```

**Issue: Split Brain**
```bash
# Check HA priority and preemption
show system ha
get system ha status

# Verify network connectivity between HA peers
execute ping-options source 10.0.3.10
execute ping 10.0.3.11
```

## Performance Monitoring

### System Performance Metrics

#### 1. CPU and Memory Monitoring

```bash
# FortiGate system resources
get system performance status
get system performance top

# Detailed CPU information
diagnose hardware deviceinfo nic port1
diagnose sys top-summary
```

#### 2. Network Performance

```bash
# Interface statistics
get system interface physical
get system interface transceiver

# Traffic statistics
get system session stat
get firewall session list
```

#### 3. Throughput Testing

```bash
# iperf3 testing from spoke VPCs
# Server (in target VPC)
iperf3 -s

# Client (in source VPC)
iperf3 -c 10.0.2.100 -t 60 -P 4
```

### Performance Optimization

#### 1. FortiGate Optimization

```bash
# Enable hardware acceleration
config system npu
    set np6-cps-optimization enable
    set ipsec-dec-subengine-mask 0x3
end

# Optimize session settings
config system session-helper
    # Disable unnecessary helpers
end
```

#### 2. AWS Instance Optimization

```bash
# Enable SR-IOV
aws ec2 modify-instance-attribute \
  --instance-id i-fortigate-primary \
  --sriov-net-support simple

# Enable enhanced networking
aws ec2 modify-instance-attribute \
  --instance-id i-fortigate-primary \
  --ena-support
```

### Capacity Planning

#### 1. Traffic Analysis

```sql
# CloudWatch Insights query for capacity planning
fields @timestamp, bytes
| filter action = "ACCEPT"
| stats sum(bytes) as total_bytes by bin(1h)
| sort @timestamp desc
| limit 168  # 7 days of hourly data
```

#### 2. Resource Utilization Trends

```python
import boto3
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

def get_cpu_utilization(instance_id, days=7):
    cloudwatch = boto3.client('cloudwatch')
    
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(days=days)
    
    response = cloudwatch.get_metric_statistics(
        Namespace='AWS/EC2',
        MetricName='CPUUtilization',
        Dimensions=[
            {
                'Name': 'InstanceId',
                'Value': instance_id
            }
        ],
        StartTime=start_time,
        EndTime=end_time,
        Period=3600,  # 1 hour
        Statistics=['Average', 'Maximum']
    )
    
    return response['Datapoints']

# Generate capacity planning report
cpu_data = get_cpu_utilization('i-fortigate-primary')
# Plot and analyze trends
```

## Common Issues and Solutions

### Deployment Issues

#### 1. Terraform Apply Failures

**Issue: Resource already exists**
```bash
# Import existing resource
terraform import aws_instance.fortigate_primary i-12345678

# Or remove from state and recreate
terraform state rm aws_instance.fortigate_primary
terraform apply
```

**Issue: IAM permission denied**
```bash
# Check current permissions
aws sts get-caller-identity
aws iam simulate-principal-policy \
  --policy-source-arn arn:aws:iam::123456789012:user/terraform \
  --action-names ec2:RunInstances \
  --resource-arns "*"
```

#### 2. FortiGate Boot Issues

**Issue: FortiGate not accessible after deployment**
```bash
# Check instance status
aws ec2 describe-instance-status --instance-ids i-12345678

# Check system log
aws ec2 get-console-output --instance-id i-12345678

# Connect via serial console
aws ec2-instance-connect send-serial-console-ssh-public-key \
  --instance-id i-12345678 \
  --ssh-public-key file://~/.ssh/id_rsa.pub
```

### Operational Issues

#### 1. Traffic Not Flowing

**Symptoms:**
- Spoke VPCs cannot reach internet
- Traffic not appearing in FortiGate logs

**Troubleshooting Steps:**
```bash
# 1. Check route tables
aws ec2 describe-route-tables --filters "Name=vpc-id,Values=vpc-spoke1"

# 2. Verify Transit Gateway attachments
aws ec2 describe-transit-gateway-attachments

# 3. Check FortiGate routing
get router info routing-table all

# 4. Verify security policies
get firewall policy
```

#### 2. HA Failover Not Working

**Symptoms:**
- Primary FortiGate down but traffic not failing over
- Both FortiGates showing as primary

**Troubleshooting Steps:**
```bash
# 1. Check HA status on both units
get system ha status

# 2. Verify HA heartbeat connectivity
execute ping-options source 10.0.3.10
execute ping 10.0.3.11

# 3. Check HA configuration
show system ha

# 4. Force failover for testing
execute ha failover set 1
```

#### 3. Performance Issues

**Symptoms:**
- High latency
- Low throughput
- Packet drops

**Troubleshooting Steps:**
```bash
# 1. Check system resources
get system performance status
diagnose sys top

# 2. Analyze traffic patterns
get system session stat
diagnose sniffer packet any "host 10.0.1.100" 4 100

# 3. Check for bottlenecks
get system interface physical
diagnose hardware deviceinfo nic port1
```

### Security Issues

#### 1. Blocked Traffic

**Issue: Legitimate traffic being blocked**
```bash
# Check policy matches
diagnose firewall iprope lookup 10.0.1.100 80 10.0.2.100 8080 tcp

# Review security policies
get firewall policy
show firewall policy 1

# Check IPS signatures
diagnose ips anomaly list
```

#### 2. License Issues

**Issue: FortiGate license expired or invalid**
```bash
# Check license status
get system status
diagnose sys license

# Apply new license
execute restore vmlicense tftp license.lic 192.168.1.100
```

## Disaster Recovery

### Backup Procedures

#### 1. Configuration Backup

```bash
# Automated backup script
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/opt/fortigate-backups"

# Create backup directory
mkdir -p $BACKUP_DIR

# Backup FortiGate configuration
ssh admin@10.0.1.10 "execute backup config tftp fortigate-primary-$DATE.conf 192.168.1.100"
ssh admin@10.0.1.11 "execute backup config tftp fortigate-backup-$DATE.conf 192.168.1.100"

# Backup Terraform state
aws s3 cp terraform.tfstate s3://fortigate-backups/terraform/terraform-$DATE.tfstate

# Backup CloudWatch dashboards
aws cloudwatch get-dashboard --dashboard-name FortiGate-HA-Monitoring > $BACKUP_DIR/dashboard-$DATE.json
```

#### 2. Automated Backup with Lambda

```python
import boto3
import json
from datetime import datetime

def lambda_handler(event, context):
    """Automated FortiGate backup function"""
    
    # Backup Terraform state
    s3 = boto3.client('s3')
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Copy current state to backup location
    s3.copy_object(
        CopySource={'Bucket': 'terraform-state-bucket', 'Key': 'fortigate/terraform.tfstate'},
        Bucket='fortigate-backups',
        Key=f'terraform/terraform-{timestamp}.tfstate'
    )
    
    # Backup CloudWatch configuration
    cloudwatch = boto3.client('cloudwatch')
    dashboard = cloudwatch.get_dashboard(DashboardName='FortiGate-HA-Monitoring')
    
    s3.put_object(
        Bucket='fortigate-backups',
        Key=f'cloudwatch/dashboard-{timestamp}.json',
        Body=json.dumps(dashboard['DashboardBody'])
    )
    
    return {
        'statusCode': 200,
        'body': json.dumps(f'Backup completed: {timestamp}')
    }
```

### Recovery Procedures

#### 1. FortiGate Recovery

```bash
# Restore configuration
ssh admin@10.0.1.10 "execute restore config tftp fortigate-primary-backup.conf 192.168.1.100"

# Verify configuration
ssh admin@10.0.1.10 "get system status"
ssh admin@10.0.1.10 "get system ha status"
```

#### 2. Infrastructure Recovery

```bash
# Restore from Terraform state backup
aws s3 cp s3://fortigate-backups/terraform/terraform-20231201_120000.tfstate terraform.tfstate

# Verify and apply
terraform plan
terraform apply
```

### Business Continuity Planning

#### 1. RTO/RPO Targets

- **Recovery Time Objective (RTO)**: 15 minutes
- **Recovery Point Objective (RPO)**: 1 hour
- **Maximum Tolerable Downtime**: 30 minutes

#### 2. Escalation Procedures

**Level 1 - Automated Response:**
- CloudWatch alarms trigger SNS notifications
- Lambda functions attempt automatic remediation
- Slack/Teams notifications sent to on-call team

**Level 2 - Manual Intervention:**
- Network operations team investigates
- Follow troubleshooting runbooks
- Escalate to Level 3 if not resolved in 15 minutes

**Level 3 - Expert Support:**
- Senior network engineers engaged
- Vendor support contacted if needed
- Management notification for extended outages

## Alerting and Notifications

### SNS Topic Configuration

```bash
# Create SNS topic for FortiGate alerts
aws sns create-topic --name fortigate-alerts

# Subscribe email addresses
aws sns subscribe \
  --topic-arn arn:aws:sns:us-east-1:123456789012:fortigate-alerts \
  --protocol email \
  --notification-endpoint ops-team@company.com

# Subscribe Slack webhook
aws sns subscribe \
  --topic-arn arn:aws:sns:us-east-1:123456789012:fortigate-alerts \
  --protocol https \
  --notification-endpoint https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK
```

### Alert Categories

#### 1. Critical Alerts (Immediate Response)
- FortiGate instance failure
- HA failover events
- Complete connectivity loss
- Security breaches

#### 2. Warning Alerts (Response within 1 hour)
- High CPU/memory usage
- BGP session flaps
- Performance degradation
- License expiration warnings

#### 3. Informational Alerts (Daily review)
- Configuration changes
- Routine maintenance events
- Capacity utilization reports
- Security event summaries

### Custom Alert Scripts

```python
import boto3
import json

def send_custom_alert(severity, message, details=None):
    """Send custom alert to SNS topic"""
    sns = boto3.client('sns')
    
    alert_data = {
        'severity': severity,
        'timestamp': datetime.utcnow().isoformat(),
        'message': message,
        'details': details or {}
    }
    
    sns.publish(
        TopicArn='arn:aws:sns:us-east-1:123456789012:fortigate-alerts',
        Subject=f'FortiGate Alert - {severity}',
        Message=json.dumps(alert_data, indent=2)
    )

# Example usage
send_custom_alert(
    'CRITICAL',
    'FortiGate Primary Instance Unreachable',
    {
        'instance_id': 'i-12345678',
        'last_seen': '2023-12-01T10:30:00Z',
        'health_check_status': 'FAILED'
    }
)
```

This comprehensive monitoring and troubleshooting guide provides the foundation for maintaining a robust FortiGate AWS HA deployment with proper visibility, alerting, and recovery procedures.