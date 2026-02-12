# Monitoring Module - CloudWatch and VPC Flow Logs

# CloudWatch Log Group for VPC Flow Logs
resource "aws_cloudwatch_log_group" "flow_logs" {
  count             = var.enable_flow_logs ? 1 : 0
  name              = "/aws/vpc/flowlogs/${var.vpc_id}"
  retention_in_days = var.log_retention_days

  tags = {
    Name        = "fortigate-vpc-flow-logs"
    Project     = "FortiGate-HA-Deployment"
    Environment = var.environment
    Owner       = var.owner_tag
    ManagedBy   = "Terraform"
  }
}

# IAM Role for VPC Flow Logs
resource "aws_iam_role" "flow_logs" {
  count = var.enable_flow_logs ? 1 : 0
  name_prefix = "fortigate-flow-logs-"

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

  tags = {
    Name        = "fortigate-flow-logs-role"
    Project     = "FortiGate-HA-Deployment"
    Environment = var.environment
    Owner       = var.owner_tag
    ManagedBy   = "Terraform"
  }
}

# IAM Policy for VPC Flow Logs
resource "aws_iam_role_policy" "flow_logs" {
  count = var.enable_flow_logs ? 1 : 0
  name_prefix = "fortigate-flow-logs-"
  role  = aws_iam_role.flow_logs[0].id

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
        Effect = "Allow"
        Resource = "*"
      }
    ]
  })
}

# VPC Flow Logs
resource "aws_flow_log" "vpc" {
  count                = var.enable_flow_logs ? 1 : 0
  vpc_id               = var.vpc_id
  traffic_type         = "ALL"
  iam_role_arn         = aws_iam_role.flow_logs[0].arn
  log_destination_type = "cloud-watch-logs"
  log_destination      = aws_cloudwatch_log_group.flow_logs[0].arn

  tags = {
    Name        = "fortigate-vpc-flow-logs"
    Project     = "FortiGate-HA-Deployment"
    Environment = var.environment
    Owner       = var.owner_tag
    ManagedBy   = "Terraform"
  }
}

# CloudWatch Log Group for FortiGate Instances
resource "aws_cloudwatch_log_group" "fortigate" {
  count             = length(var.fortigate_instance_ids)
  name              = "/aws/ec2/fortigate/${var.fortigate_instance_ids[count.index]}"
  retention_in_days = var.log_retention_days

  tags = {
    Name        = "fortigate-instance-logs-${var.fortigate_instance_ids[count.index]}"
    Project     = "FortiGate-HA-Deployment"
    Environment = var.environment
    Owner       = var.owner_tag
    ManagedBy   = "Terraform"
  }
}

# CloudWatch Alarms for FortiGate Instances - CPU
resource "aws_cloudwatch_metric_alarm" "fortigate_cpu" {
  count               = length(var.fortigate_instance_ids)
  alarm_name          = "fortigate-${var.fortigate_instance_ids[count.index]}-high-cpu"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/EC2"
  period              = "300"
  statistic           = "Average"
  threshold           = "80"
  alarm_description   = "This metric monitors FortiGate CPU utilization"
  alarm_actions       = []

  dimensions = {
    InstanceId = var.fortigate_instance_ids[count.index]
  }

  tags = {
    Name        = "fortigate-cpu-alarm-${var.fortigate_instance_ids[count.index]}"
    Project     = "FortiGate-HA-Deployment"
    Environment = var.environment
    Owner       = var.owner_tag
    ManagedBy   = "Terraform"
  }
}

# CloudWatch Alarms for FortiGate Instances - Status Check
resource "aws_cloudwatch_metric_alarm" "fortigate_status" {
  count               = length(var.fortigate_instance_ids)
  alarm_name          = "fortigate-${var.fortigate_instance_ids[count.index]}-status-check"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "StatusCheckFailed"
  namespace           = "AWS/EC2"
  period              = "60"
  statistic           = "Maximum"
  threshold           = "0"
  alarm_description   = "This metric monitors FortiGate instance status"
  alarm_actions       = []

  dimensions = {
    InstanceId = var.fortigate_instance_ids[count.index]
  }

  tags = {
    Name        = "fortigate-status-alarm-${var.fortigate_instance_ids[count.index]}"
    Project     = "FortiGate-HA-Deployment"
    Environment = var.environment
    Owner       = var.owner_tag
    ManagedBy   = "Terraform"
  }
}
