# Monitoring Module - CloudWatch and VPC Flow Logs

# CloudWatch Log Group for VPC Flow Logs
resource "aws_cloudwatch_log_group" "flow_logs" {
  count             = var.enable_flow_logs ? 1 : 0
  name              = "/aws/vpc/flowlogs/${var.vpc_id}"
  retention_in_days = var.log_retention_days

  tags = {
    Name        = "fortigate-vpc-flow-logs"
    Environment = var.environment
    Owner       = var.owner_tag
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
    Environment = var.environment
    Owner       = var.owner_tag
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
    Environment = var.environment
    Owner       = var.owner_tag
  }
}

# CloudWatch Log Group for FortiGate Instances
resource "aws_cloudwatch_log_group" "fortigate" {
  for_each          = toset(var.fortigate_instance_ids)
  name              = "/aws/ec2/fortigate/${each.value}"
  retention_in_days = var.log_retention_days

  tags = {
    Name        = "fortigate-instance-logs-${each.value}"
    Environment = var.environment
    Owner       = var.owner_tag
  }
}

# CloudWatch Alarms for FortiGate Instances
resource "aws_cloudwatch_metric_alarm" "fortigate_cpu" {
  for_each            = toset(var.fortigate_instance_ids)
  alarm_name          = "fortigate-${each.value}-high-cpu"
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
    InstanceId = each.value
  }

  tags = {
    Name        = "fortigate-cpu-alarm-${each.value}"
    Environment = var.environment
    Owner       = var.owner_tag
  }
}

resource "aws_cloudwatch_metric_alarm" "fortigate_status" {
  for_each            = toset(var.fortigate_instance_ids)
  alarm_name          = "fortigate-${each.value}-status-check"
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
    InstanceId = each.value
  }

  tags = {
    Name        = "fortigate-status-alarm-${each.value}"
    Environment = var.environment
    Owner       = var.owner_tag
  }
}
