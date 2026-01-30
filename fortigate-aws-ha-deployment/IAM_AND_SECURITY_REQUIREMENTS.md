# FortiGate AWS HA Deployment - IAM and Security Access Requirements

## Overview

This document specifies the exact IAM permissions and security access requirements for deploying and operating FortiGate HA pairs on AWS. It provides comprehensive IAM policy templates for third-party vendors and system administrators to set up appropriate access controls following the principle of least privilege.

## Table of Contents

1. [Required IAM Permissions](#required-iam-permissions)
2. [IAM Roles and Policies](#iam-roles-and-policies)
3. [AWS Secrets Manager Access](#aws-secrets-manager-access)
4. [Least-Privilege Principles](#least-privilege-principles)
5. [IAM Policy Templates](#iam-policy-templates)
6. [Third-Party Vendor Setup](#third-party-vendor-setup)
7. [Security Best Practices](#security-best-practices)

## Required IAM Permissions

### Bootstrap Phase Permissions

Before deploying the main FortiGate infrastructure, you must first run the bootstrap configuration to create the S3 bucket and DynamoDB table for Terraform state management. The bootstrap phase requires these additional permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "BootstrapS3Permissions",
      "Effect": "Allow",
      "Action": [
        "s3:CreateBucket",
        "s3:DeleteBucket",
        "s3:GetBucketVersioning",
        "s3:PutBucketVersioning",
        "s3:GetBucketEncryption",
        "s3:PutBucketEncryption",
        "s3:GetBucketPublicAccessBlock",
        "s3:PutBucketPublicAccessBlock",
        "s3:GetBucketPolicy",
        "s3:PutBucketPolicy",
        "s3:DeleteBucketPolicy"
      ],
      "Resource": [
        "arn:aws:s3:::*-fortigate-terraform-state"
      ]
    },
    {
      "Sid": "BootstrapDynamoDBPermissions",
      "Effect": "Allow",
      "Action": [
        "dynamodb:CreateTable",
        "dynamodb:DeleteTable",
        "dynamodb:DescribeTable",
        "dynamodb:UpdateTable",
        "dynamodb:TagResource",
        "dynamodb:UntagResource",
        "dynamodb:ListTagsOfResource"
      ],
      "Resource": [
        "arn:aws:dynamodb:*:*:table/fortigate-terraform-locks"
      ]
    }
  ]
}
```

### Core Deployment Permissions

The FortiGate deployment requires the following AWS service permissions:

#### EC2 Permissions
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "EC2InstanceManagement",
      "Effect": "Allow",
      "Action": [
        "ec2:RunInstances",
        "ec2:TerminateInstances",
        "ec2:StartInstances",
        "ec2:StopInstances",
        "ec2:RebootInstances",
        "ec2:DescribeInstances",
        "ec2:DescribeInstanceStatus",
        "ec2:DescribeInstanceAttribute",
        "ec2:ModifyInstanceAttribute",
        "ec2:GetConsoleOutput",
        "ec2:GetConsoleScreenshot"
      ],
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "ec2:ResourceTag/Project": "FortiGate-HA-Deployment"
        }
      }
    },
    {
      "Sid": "EC2NetworkManagement",
      "Effect": "Allow",
      "Action": [
        "ec2:CreateNetworkInterface",
        "ec2:DeleteNetworkInterface",
        "ec2:AttachNetworkInterface",
        "ec2:DetachNetworkInterface",
        "ec2:DescribeNetworkInterfaces",
        "ec2:ModifyNetworkInterfaceAttribute",
        "ec2:AssignPrivateIpAddresses",
        "ec2:UnassignPrivateIpAddresses"
      ],
      "Resource": "*"
    },
    {
      "Sid": "EC2SecurityGroups",
      "Effect": "Allow",
      "Action": [
        "ec2:CreateSecurityGroup",
        "ec2:DeleteSecurityGroup",
        "ec2:DescribeSecurityGroups",
        "ec2:AuthorizeSecurityGroupIngress",
        "ec2:AuthorizeSecurityGroupEgress",
        "ec2:RevokeSecurityGroupIngress",
        "ec2:RevokeSecurityGroupEgress",
        "ec2:CreateTags",
        "ec2:DeleteTags"
      ],
      "Resource": "*"
    },
    {
      "Sid": "EC2VPCManagement",
      "Effect": "Allow",
      "Action": [
        "ec2:DescribeVpcs",
        "ec2:DescribeSubnets",
        "ec2:DescribeRouteTables",
        "ec2:CreateRoute",
        "ec2:DeleteRoute",
        "ec2:ReplaceRoute",
        "ec2:DescribeInternetGateways",
        "ec2:DescribeNatGateways",
        "ec2:DescribeVpcEndpoints"
      ],
      "Resource": "*"
    },
    {
      "Sid": "EC2AMIAccess",
      "Effect": "Allow",
      "Action": [
        "ec2:DescribeImages",
        "ec2:DescribeSnapshots"
      ],
      "Resource": "*"
    },
    {
      "Sid": "EC2KeyPairs",
      "Effect": "Allow",
      "Action": [
        "ec2:DescribeKeyPairs",
        "ec2:CreateKeyPair",
        "ec2:DeleteKeyPair",
        "ec2:ImportKeyPair"
      ],
      "Resource": "*"
    }
  ]
}
```

#### Transit Gateway Permissions
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "TransitGatewayManagement",
      "Effect": "Allow",
      "Action": [
        "ec2:CreateTransitGateway",
        "ec2:DeleteTransitGateway",
        "ec2:DescribeTransitGateways",
        "ec2:ModifyTransitGateway",
        "ec2:CreateTransitGatewayVpcAttachment",
        "ec2:DeleteTransitGatewayVpcAttachment",
        "ec2:DescribeTransitGatewayVpcAttachments",
        "ec2:ModifyTransitGatewayVpcAttachment",
        "ec2:CreateTransitGatewayRouteTable",
        "ec2:DeleteTransitGatewayRouteTable",
        "ec2:DescribeTransitGatewayRouteTables",
        "ec2:AssociateTransitGatewayRouteTable",
        "ec2:DisassociateTransitGatewayRouteTable",
        "ec2:PropagateTransitGatewayRoute",
        "ec2:CreateTransitGatewayRoute",
        "ec2:DeleteTransitGatewayRoute",
        "ec2:ReplaceTransitGatewayRoute",
        "ec2:SearchTransitGatewayRoutes"
      ],
      "Resource": "*"
    }
  ]
}
```

#### CloudWatch and Logging Permissions
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "CloudWatchLogs",
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents",
        "logs:DescribeLogGroups",
        "logs:DescribeLogStreams",
        "logs:PutRetentionPolicy",
        "logs:DeleteLogGroup",
        "logs:DeleteLogStream"
      ],
      "Resource": [
        "arn:aws:logs:*:*:log-group:/aws/vpc/fortigate-*",
        "arn:aws:logs:*:*:log-group:/aws/ec2/fortigate/*"
      ]
    },
    {
      "Sid": "CloudWatchMetrics",
      "Effect": "Allow",
      "Action": [
        "cloudwatch:PutMetricData",
        "cloudwatch:GetMetricStatistics",
        "cloudwatch:ListMetrics",
        "cloudwatch:PutDashboard",
        "cloudwatch:GetDashboard",
        "cloudwatch:DeleteDashboard",
        "cloudwatch:ListDashboards",
        "cloudwatch:PutMetricAlarm",
        "cloudwatch:DeleteAlarms",
        "cloudwatch:DescribeAlarms"
      ],
      "Resource": "*"
    },
    {
      "Sid": "VPCFlowLogs",
      "Effect": "Allow",
      "Action": [
        "ec2:CreateFlowLogs",
        "ec2:DeleteFlowLogs",
        "ec2:DescribeFlowLogs"
      ],
      "Resource": "*"
    }
  ]
}
```

#### AWS Secrets Manager Permissions
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "SecretsManagerAccess",
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue",
        "secretsmanager:DescribeSecret"
      ],
      "Resource": [
        "arn:aws:secretsmanager:*:*:secret:fortigate/*"
      ]
    },
    {
      "Sid": "SecretsManagerManagement",
      "Effect": "Allow",
      "Action": [
        "secretsmanager:CreateSecret",
        "secretsmanager:UpdateSecret",
        "secretsmanager:DeleteSecret",
        "secretsmanager:PutSecretValue",
        "secretsmanager:TagResource",
        "secretsmanager:UntagResource"
      ],
      "Resource": [
        "arn:aws:secretsmanager:*:*:secret:fortigate/*"
      ],
      "Condition": {
        "StringEquals": {
          "secretsmanager:ResourceTag/Project": "FortiGate-HA-Deployment"
        }
      }
    }
  ]
}
```

#### S3 Permissions (for license storage and Terraform state)
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "S3TerraformState",
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject",
        "s3:ListBucket",
        "s3:GetBucketVersioning"
      ],
      "Resource": [
        "arn:aws:s3:::your-fortigate-terraform-state/*",
        "arn:aws:s3:::your-fortigate-terraform-state"
      ]
    },
    {
      "Sid": "S3LicenseStorage",
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::fortigate-licenses/*",
        "arn:aws:s3:::fortigate-licenses"
      ]
    }
  ]
}
```

**Note**: Replace `your-fortigate-terraform-state` with the actual S3 bucket name created during bootstrap setup.

#### DynamoDB Permissions (for Terraform state locking)
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DynamoDBStateLocking",
      "Effect": "Allow",
      "Action": [
        "dynamodb:GetItem",
        "dynamodb:PutItem",
        "dynamodb:DeleteItem",
        "dynamodb:DescribeTable"
      ],
      "Resource": [
        "arn:aws:dynamodb:*:*:table/fortigate-terraform-locks"
      ]
    }
  ]
}
```

**Note**: The DynamoDB table for state locking is created by the bootstrap configuration and is required for safe concurrent Terraform operations. The table name can be customized during bootstrap setup.

## IAM Roles and Policies

### 1. Terraform Execution Role

**Role Name**: `FortiGate-Terraform-Execution-Role`

**Trust Policy**:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::ACCOUNT-ID:user/terraform-user"
      },
      "Action": "sts:AssumeRole",
      "Condition": {
        "StringEquals": {
          "sts:ExternalId": "fortigate-deployment-external-id"
        }
      }
    }
  ]
}
```

**Attached Policies**:
- `FortiGate-EC2-Management-Policy`
- `FortiGate-TransitGateway-Policy`
- `FortiGate-CloudWatch-Policy`
- `FortiGate-SecretsManager-Policy`
- `FortiGate-S3-Policy`
- `FortiGate-DynamoDB-Policy`

### 2. FortiGate Instance Role

**Role Name**: `FortiGate-Instance-Role`

**Trust Policy**:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "ec2.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

**Instance Profile**: `FortiGate-Instance-Profile`

**Attached Policy**:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "FortiGateInstancePermissions",
      "Effect": "Allow",
      "Action": [
        "ec2:DescribeInstances",
        "ec2:DescribeNetworkInterfaces",
        "ec2:DescribeRouteTables",
        "ec2:CreateRoute",
        "ec2:DeleteRoute",
        "ec2:ReplaceRoute",
        "secretsmanager:GetSecretValue",
        "logs:CreateLogStream",
        "logs:PutLogEvents",
        "cloudwatch:PutMetricData"
      ],
      "Resource": "*"
    }
  ]
}
```

### 3. VPC Flow Logs Role

**Role Name**: `FortiGate-VPC-FlowLogs-Role`

**Trust Policy**:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "vpc-flow-logs.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

**Attached Policy**:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents",
        "logs:DescribeLogGroups",
        "logs:DescribeLogStreams"
      ],
      "Resource": "*"
    }
  ]
}
```

## AWS Secrets Manager Access

### License Storage Requirements

For BYOL deployments, FortiGate licenses must be stored securely in AWS Secrets Manager:

#### Secret Structure
```json
{
  "SecretName": "fortigate/primary/license",
  "Description": "FortiGate Primary Instance License",
  "SecretString": "-----BEGIN FGT VM LICENSE-----\n[LICENSE CONTENT]\n-----END FGT VM LICENSE-----",
  "Tags": [
    {
      "Key": "Project",
      "Value": "FortiGate-HA-Deployment"
    },
    {
      "Key": "Environment",
      "Value": "production"
    },
    {
      "Key": "Instance",
      "Value": "primary"
    }
  ]
}
```

#### Required Secrets
1. **Primary License**: `fortigate/primary/license`
2. **Backup License**: `fortigate/backup/license`
3. **Admin Password**: `fortigate/admin/password`
4. **HA Password**: `fortigate/ha/password`

#### Access Permissions
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "FortiGateLicenseAccess",
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue"
      ],
      "Resource": [
        "arn:aws:secretsmanager:*:*:secret:fortigate/primary/license-*",
        "arn:aws:secretsmanager:*:*:secret:fortigate/backup/license-*",
        "arn:aws:secretsmanager:*:*:secret:fortigate/admin/password-*",
        "arn:aws:secretsmanager:*:*:secret:fortigate/ha/password-*"
      ]
    }
  ]
}
```

### Encryption Requirements

All secrets must be encrypted using AWS KMS:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "KMSKeyAccess",
      "Effect": "Allow",
      "Action": [
        "kms:Decrypt",
        "kms:DescribeKey"
      ],
      "Resource": [
        "arn:aws:kms:*:*:key/fortigate-secrets-key-id"
      ]
    }
  ]
}
```

## Least-Privilege Principles

### Implementation Guidelines

1. **Resource-Specific Permissions**: Limit permissions to specific resources using ARNs and conditions
2. **Conditional Access**: Use IAM conditions to restrict access based on tags, time, or source IP
3. **Temporary Credentials**: Use IAM roles instead of long-term access keys
4. **Regular Auditing**: Implement regular access reviews and permission audits

### Resource Tagging Strategy

All resources must be tagged for proper access control:

```json
{
  "Tags": [
    {
      "Key": "Project",
      "Value": "FortiGate-HA-Deployment"
    },
    {
      "Key": "Environment",
      "Value": "production|staging|development"
    },
    {
      "Key": "Owner",
      "Value": "network-team"
    },
    {
      "Key": "CostCenter",
      "Value": "infrastructure"
    },
    {
      "Key": "Backup",
      "Value": "required"
    }
  ]
}
```

### Conditional Access Examples

**Time-Based Access**:
```json
{
  "Condition": {
    "DateGreaterThan": {
      "aws:CurrentTime": "2023-01-01T00:00:00Z"
    },
    "DateLessThan": {
      "aws:CurrentTime": "2024-01-01T00:00:00Z"
    }
  }
}
```

**IP-Based Access**:
```json
{
  "Condition": {
    "IpAddress": {
      "aws:SourceIp": [
        "203.0.113.0/24",
        "198.51.100.0/24"
      ]
    }
  }
}
```

**MFA Requirement**:
```json
{
  "Condition": {
    "Bool": {
      "aws:MultiFactorAuthPresent": "true"
    },
    "NumericLessThan": {
      "aws:MultiFactorAuthAge": "3600"
    }
  }
}
```

## IAM Policy Templates

### Complete Deployment Policy Template

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "FortiGateDeploymentPolicy",
      "Effect": "Allow",
      "Action": [
        "ec2:RunInstances",
        "ec2:TerminateInstances",
        "ec2:StartInstances",
        "ec2:StopInstances",
        "ec2:RebootInstances",
        "ec2:DescribeInstances",
        "ec2:DescribeInstanceStatus",
        "ec2:DescribeImages",
        "ec2:DescribeSnapshots",
        "ec2:DescribeKeyPairs",
        "ec2:CreateKeyPair",
        "ec2:DeleteKeyPair",
        "ec2:ImportKeyPair",
        "ec2:CreateNetworkInterface",
        "ec2:DeleteNetworkInterface",
        "ec2:AttachNetworkInterface",
        "ec2:DetachNetworkInterface",
        "ec2:DescribeNetworkInterfaces",
        "ec2:ModifyNetworkInterfaceAttribute",
        "ec2:CreateSecurityGroup",
        "ec2:DeleteSecurityGroup",
        "ec2:DescribeSecurityGroups",
        "ec2:AuthorizeSecurityGroupIngress",
        "ec2:AuthorizeSecurityGroupEgress",
        "ec2:RevokeSecurityGroupIngress",
        "ec2:RevokeSecurityGroupEgress",
        "ec2:DescribeVpcs",
        "ec2:DescribeSubnets",
        "ec2:DescribeRouteTables",
        "ec2:CreateRoute",
        "ec2:DeleteRoute",
        "ec2:ReplaceRoute",
        "ec2:CreateTransitGateway",
        "ec2:DeleteTransitGateway",
        "ec2:DescribeTransitGateways",
        "ec2:ModifyTransitGateway",
        "ec2:CreateTransitGatewayVpcAttachment",
        "ec2:DeleteTransitGatewayVpcAttachment",
        "ec2:DescribeTransitGatewayVpcAttachments",
        "ec2:CreateTransitGatewayRouteTable",
        "ec2:DeleteTransitGatewayRouteTable",
        "ec2:DescribeTransitGatewayRouteTables",
        "ec2:AssociateTransitGatewayRouteTable",
        "ec2:DisassociateTransitGatewayRouteTable",
        "ec2:CreateTransitGatewayRoute",
        "ec2:DeleteTransitGatewayRoute",
        "ec2:SearchTransitGatewayRoutes",
        "ec2:CreateFlowLogs",
        "ec2:DeleteFlowLogs",
        "ec2:DescribeFlowLogs",
        "ec2:CreateTags",
        "ec2:DeleteTags",
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents",
        "logs:DescribeLogGroups",
        "logs:DescribeLogStreams",
        "logs:PutRetentionPolicy",
        "logs:DeleteLogGroup",
        "cloudwatch:PutMetricData",
        "cloudwatch:GetMetricStatistics",
        "cloudwatch:ListMetrics",
        "cloudwatch:PutDashboard",
        "cloudwatch:GetDashboard",
        "cloudwatch:DeleteDashboard",
        "cloudwatch:PutMetricAlarm",
        "cloudwatch:DeleteAlarms",
        "cloudwatch:DescribeAlarms",
        "secretsmanager:GetSecretValue",
        "secretsmanager:DescribeSecret",
        "secretsmanager:CreateSecret",
        "secretsmanager:UpdateSecret",
        "secretsmanager:DeleteSecret",
        "secretsmanager:PutSecretValue",
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject",
        "s3:ListBucket",
        "dynamodb:GetItem",
        "dynamodb:PutItem",
        "dynamodb:DeleteItem",
        "dynamodb:DescribeTable",
        "kms:Decrypt",
        "kms:DescribeKey",
        "iam:PassRole",
        "iam:GetRole",
        "iam:CreateRole",
        "iam:DeleteRole",
        "iam:AttachRolePolicy",
        "iam:DetachRolePolicy",
        "iam:CreateInstanceProfile",
        "iam:DeleteInstanceProfile",
        "iam:AddRoleToInstanceProfile",
        "iam:RemoveRoleFromInstanceProfile"
      ],
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "aws:RequestedRegion": [
            "us-east-1",
            "us-west-2",
            "eu-west-1",
            "ap-southeast-1"
          ]
        }
      }
    }
  ]
}
```

### Read-Only Monitoring Policy

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "FortiGateMonitoringReadOnly",
      "Effect": "Allow",
      "Action": [
        "ec2:DescribeInstances",
        "ec2:DescribeInstanceStatus",
        "ec2:DescribeNetworkInterfaces",
        "ec2:DescribeSecurityGroups",
        "ec2:DescribeVpcs",
        "ec2:DescribeSubnets",
        "ec2:DescribeRouteTables",
        "ec2:DescribeTransitGateways",
        "ec2:DescribeTransitGatewayVpcAttachments",
        "ec2:DescribeTransitGatewayRouteTables",
        "ec2:SearchTransitGatewayRoutes",
        "ec2:DescribeFlowLogs",
        "logs:DescribeLogGroups",
        "logs:DescribeLogStreams",
        "logs:GetLogEvents",
        "logs:StartQuery",
        "logs:StopQuery",
        "logs:GetQueryResults",
        "cloudwatch:GetMetricStatistics",
        "cloudwatch:ListMetrics",
        "cloudwatch:GetDashboard",
        "cloudwatch:ListDashboards",
        "cloudwatch:DescribeAlarms",
        "cloudwatch:GetMetricData"
      ],
      "Resource": "*"
    }
  ]
}
```

## Third-Party Vendor Setup

### Vendor Onboarding Process

1. **Create Vendor-Specific IAM User**:
```bash
aws iam create-user --user-name fortigate-vendor-user
aws iam attach-user-policy --user-name fortigate-vendor-user --policy-arn arn:aws:iam::ACCOUNT-ID:policy/FortiGate-Vendor-Policy
```

2. **Generate Access Keys**:
```bash
aws iam create-access-key --user-name fortigate-vendor-user
```

3. **Set Up MFA Requirement**:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowViewAccountInfo",
      "Effect": "Allow",
      "Action": [
        "iam:GetAccountPasswordPolicy",
        "iam:ListVirtualMFADevices"
      ],
      "Resource": "*"
    },
    {
      "Sid": "AllowManageOwnPasswords",
      "Effect": "Allow",
      "Action": [
        "iam:ChangePassword",
        "iam:GetUser"
      ],
      "Resource": "arn:aws:iam::*:user/${aws:username}"
    },
    {
      "Sid": "AllowManageOwnMFA",
      "Effect": "Allow",
      "Action": [
        "iam:CreateVirtualMFADevice",
        "iam:DeleteVirtualMFADevice",
        "iam:EnableMFADevice",
        "iam:ListMFADevices",
        "iam:ResyncMFADevice"
      ],
      "Resource": [
        "arn:aws:iam::*:mfa/${aws:username}",
        "arn:aws:iam::*:user/${aws:username}"
      ]
    },
    {
      "Sid": "DenyAllExceptUnlessMFAAuthenticated",
      "Effect": "Deny",
      "NotAction": [
        "iam:CreateVirtualMFADevice",
        "iam:EnableMFADevice",
        "iam:GetUser",
        "iam:ListMFADevices",
        "iam:ListVirtualMFADevices",
        "iam:ResyncMFADevice",
        "sts:GetSessionToken"
      ],
      "Resource": "*",
      "Condition": {
        "BoolIfExists": {
          "aws:MultiFactorAuthPresent": "false"
        }
      }
    }
  ]
}
```

### Vendor Policy Template

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "FortiGateVendorAccess",
      "Effect": "Allow",
      "Action": [
        "ec2:RunInstances",
        "ec2:TerminateInstances",
        "ec2:DescribeInstances",
        "ec2:DescribeImages",
        "ec2:CreateSecurityGroup",
        "ec2:DeleteSecurityGroup",
        "ec2:DescribeSecurityGroups",
        "ec2:AuthorizeSecurityGroupIngress",
        "ec2:AuthorizeSecurityGroupEgress",
        "ec2:CreateNetworkInterface",
        "ec2:DeleteNetworkInterface",
        "ec2:AttachNetworkInterface",
        "ec2:DetachNetworkInterface",
        "ec2:DescribeNetworkInterfaces",
        "ec2:CreateTransitGateway",
        "ec2:DeleteTransitGateway",
        "ec2:DescribeTransitGateways",
        "ec2:CreateTransitGatewayVpcAttachment",
        "ec2:DeleteTransitGatewayVpcAttachment",
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents",
        "cloudwatch:PutMetricData",
        "secretsmanager:GetSecretValue",
        "s3:GetObject",
        "s3:PutObject",
        "iam:PassRole"
      ],
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "aws:RequestedRegion": ["us-east-1", "us-west-2"],
          "ec2:ResourceTag/Project": "FortiGate-HA-Deployment"
        },
        "DateGreaterThan": {
          "aws:CurrentTime": "2023-01-01T00:00:00Z"
        },
        "DateLessThan": {
          "aws:CurrentTime": "2024-12-31T23:59:59Z"
        },
        "IpAddress": {
          "aws:SourceIp": ["203.0.113.0/24"]
        }
      }
    }
  ]
}
```

### Cross-Account Access Setup

For third-party vendors requiring cross-account access:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::VENDOR-ACCOUNT-ID:root"
      },
      "Action": "sts:AssumeRole",
      "Condition": {
        "StringEquals": {
          "sts:ExternalId": "unique-external-id-for-vendor"
        },
        "Bool": {
          "aws:MultiFactorAuthPresent": "true"
        }
      }
    }
  ]
}
```

## Security Best Practices

### 1. Access Key Management

- **Rotate Access Keys**: Implement 90-day rotation policy
- **Use IAM Roles**: Prefer roles over long-term access keys
- **Monitor Key Usage**: Track access key usage with CloudTrail

### 2. Multi-Factor Authentication

- **Enforce MFA**: Require MFA for all privileged operations
- **Hardware Tokens**: Use hardware MFA devices for production access
- **Emergency Access**: Maintain break-glass procedures

### 3. Network Security

- **VPC Endpoints**: Use VPC endpoints for AWS service access
- **Security Groups**: Implement least-privilege network access
- **Network ACLs**: Add additional layer of network security

### 4. Monitoring and Auditing

- **CloudTrail**: Enable CloudTrail for all API calls
- **Config Rules**: Implement AWS Config for compliance monitoring
- **Access Analyzer**: Use IAM Access Analyzer for permission reviews

### 5. Encryption

- **Data at Rest**: Encrypt all data using AWS KMS
- **Data in Transit**: Use TLS 1.2+ for all communications
- **Key Management**: Implement proper key rotation policies

## Compliance and Governance

### Required Compliance Checks

1. **SOC 2 Type II**: Implement controls for security and availability
2. **ISO 27001**: Follow information security management standards
3. **PCI DSS**: If processing payment data, implement PCI requirements
4. **GDPR**: Ensure data protection compliance for EU data

### Governance Framework

1. **Policy Reviews**: Quarterly IAM policy reviews
2. **Access Certification**: Semi-annual access certification process
3. **Incident Response**: Defined procedures for security incidents
4. **Change Management**: Formal change approval process

### Audit Requirements

1. **Access Logs**: Maintain 90-day access log retention
2. **Permission Changes**: Log all IAM permission modifications
3. **Resource Access**: Monitor all resource access patterns
4. **Compliance Reports**: Generate monthly compliance reports

## Support and Maintenance

### Regular Maintenance Tasks

1. **Policy Updates**: Review and update policies quarterly
2. **Access Reviews**: Conduct monthly access reviews
3. **Key Rotation**: Rotate access keys every 90 days
4. **Security Patches**: Apply security updates within 30 days

### Emergency Procedures

1. **Incident Response**: 24/7 security incident response
2. **Access Revocation**: Immediate access revocation procedures
3. **Forensic Analysis**: Detailed logging for forensic investigation
4. **Recovery Procedures**: Documented disaster recovery processes

### Contact Information

- **Security Team**: security@company.com
- **IAM Administrator**: iam-admin@company.com
- **Emergency Contact**: +1-555-SECURITY
- **Vendor Support**: vendor-support@company.com

---

This document provides comprehensive IAM and security access requirements for FortiGate AWS HA deployments. Regular reviews and updates ensure continued security and compliance with organizational policies.