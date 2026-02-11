# Monitoring Module Outputs

output "flow_logs_log_group_name" {
  description = "CloudWatch log group name for VPC Flow Logs"
  value       = var.enable_flow_logs ? aws_cloudwatch_log_group.flow_logs[0].name : null
}

output "flow_logs_log_group_arn" {
  description = "CloudWatch log group ARN for VPC Flow Logs"
  value       = var.enable_flow_logs ? aws_cloudwatch_log_group.flow_logs[0].arn : null
}

output "fortigate_log_groups" {
  description = "Map of FortiGate instance IDs to their CloudWatch log group names"
  value       = { for id, lg in aws_cloudwatch_log_group.fortigate : id => lg.name }
}

output "cpu_alarm_arns" {
  description = "Map of FortiGate instance IDs to their CPU alarm ARNs"
  value       = { for id, alarm in aws_cloudwatch_metric_alarm.fortigate_cpu : id => alarm.arn }
}

output "status_alarm_arns" {
  description = "Map of FortiGate instance IDs to their status check alarm ARNs"
  value       = { for id, alarm in aws_cloudwatch_metric_alarm.fortigate_status : id => alarm.arn }
}
