# Requirements Document

## Introduction

This document specifies the requirements for a FortiGate High Availability (HA) deployment system on AWS. The system will deploy a pair of FortiGate firewall VMs in a hub-and-spoke architecture using Transit Gateway, with comprehensive automation, validation, and monitoring capabilities.

## Glossary

- **FortiGate_System**: The complete HA deployment system including both primary and backup FortiGate VMs
- **Transit_Gateway**: AWS Transit Gateway service for routing traffic between VPCs
- **HA_Pair**: Primary and backup FortiGate instances configured for high availability
- **ENI**: Elastic Network Interface - AWS network interface attached to instances
- **Deployment_Engine**: The Terraform-based automation system for deploying infrastructure
- **Wrapper_Script**: Python script providing interactive deployment interface
- **Analysis_System**: FortiGate Terraform Analysis System for validation
- **Hub_VPC**: VPC containing the FortiGate instances
- **Spoke_VPC**: VPCs connected to Transit Gateway for inspection
- **BGP_Session**: Border Gateway Protocol session for dynamic route exchange
- **Web_Frontend**: Streamlit-based web application for deployment management
- **AMI_Discovery_System**: Automated system for discovering FortiGate AMIs from AWS Marketplace
- **License_Manager**: System for secure storage and retrieval of FortiGate license files
- **BYOL**: Bring Your Own License - licensing model where customer provides FortiGate licenses
- **OnDemand**: Pay-As-You-Go licensing model with hourly fees through AWS Marketplace
- **Reserved_Instance**: Long-term licensing commitment with upfront payment and reduced hourly rates
- **Secrets_Manager**: AWS Secrets Manager service for secure license storage
- **Marketplace_Integration**: Integration with AWS Marketplace for FortiGate AMI and licensing
- **AMI_Discovery_System**: Automated system for discovering FortiGate AMIs from AWS Marketplace
- **License_Manager**: System for secure storage and retrieval of FortiGate license files
- **BYOL**: Bring Your Own License - licensing model where customer provides FortiGate licenses
- **OnDemand**: Pay-As-You-Go licensing model with hourly fees through AWS Marketplace
- **Reserved_Instance**: Long-term licensing commitment with upfront payment and reduced hourly rates
- **Secrets_Manager**: AWS Secrets Manager service for secure license storage
- **Marketplace_Integration**: Integration with AWS Marketplace for FortiGate AMI and licensing

## Requirements

### Requirement 1: FortiGate HA Infrastructure Deployment

**User Story:** As a network administrator, I want to deploy a highly available FortiGate firewall pair on AWS, so that I can ensure continuous network security with automatic failover capabilities.

#### Acceptance Criteria

1. THE Deployment_Engine SHALL create two FortiGate VM instances in different AWS Availability Zones
2. WHEN deploying FortiGate instances, THE Deployment_Engine SHALL attach exactly four ENIs to each instance (OUTSIDE, INSIDE, HA, MGMT)
3. THE Deployment_Engine SHALL configure primary and backup roles for the HA_Pair with automatic failover capability
4. WHEN a primary FortiGate fails, THE HA_Pair SHALL automatically promote the backup to primary within 30 seconds
5. THE Deployment_Engine SHALL use pre-assigned VPC, subnets, and ENIs provided by external teams

### Requirement 2: Hub-and-Spoke Network Architecture

**User Story:** As a security architect, I want to implement a hub-and-spoke design with Transit Gateway, so that all spoke traffic is routed through FortiGates for centralized inspection.

#### Acceptance Criteria

1. THE Deployment_Engine SHALL configure Transit_Gateway as the central routing hub for all spoke traffic
2. THE Deployment_Engine SHALL support both creating new Transit_Gateway and using existing pre-created Transit_Gateway
3. WHEN using existing Transit_Gateway, THE Deployment_Engine SHALL validate that the Transit_Gateway exists and is accessible
4. WHEN spoke traffic is destined for the internet, THE Transit_Gateway SHALL route it through the FortiGate_System for inspection
5. THE FortiGate_System SHALL establish eBGP sessions with Transit_Gateway for dynamic route exchange
6. THE Transit_Gateway SHALL advertise all spoke VPC subnet routes to the FortiGate_System via BGP
7. THE FortiGate_System SHALL advertise default route (0.0.0.0/0) to Transit_Gateway via BGP
8. WHEN primary FortiGate fails, THE BGP_Session SHALL failover to backup FortiGate automatically
4. THE Transit_Gateway SHALL advertise all spoke VPC subnet routes to the FortiGate_System via BGP
5. THE FortiGate_System SHALL advertise default route (0.0.0.0/0) to Transit_Gateway via BGP
6. WHEN primary FortiGate fails, THE BGP_Session SHALL failover to backup FortiGate automatically

### Requirement 3: Traffic Flow Management

**User Story:** As a network engineer, I want to ensure proper traffic flow from internal subnets through the firewall to the internet, so that all traffic is inspected and secured.

#### Acceptance Criteria

1. THE FortiGate_System SHALL enforce the traffic flow: INTERNAL VPC subnet → TRANSIT GATEWAY → FORTIGATE Firewall → INTERNET
2. WHEN traffic originates from internal subnets, THE FortiGate_System SHALL inspect it before allowing internet access
3. THE FortiGate_System SHALL block traffic that does not follow the defined flow path
4. WHEN return traffic arrives from the internet, THE FortiGate_System SHALL route it back to the originating internal subnet
5. THE FortiGate_System SHALL maintain session state for bidirectional traffic flows

### Requirement 4: Comprehensive Logging and Monitoring

**User Story:** As a security operations engineer, I want comprehensive logging from both VPC Flow Logs and FortiGate systems, so that I can troubleshoot issues and maintain security visibility.

#### Acceptance Criteria

1. THE Deployment_Engine SHALL enable VPC Flow Logs for all network interfaces and subnets
2. THE FortiGate_System SHALL generate detailed security logs for all inspected traffic
3. THE Deployment_Engine SHALL configure CloudWatch log groups for centralized log collection
4. WHEN security events occur, THE FortiGate_System SHALL log them with timestamps, source, destination, and action taken
5. THE Deployment_Engine SHALL create CloudWatch dashboards for monitoring FortiGate health and traffic metrics

### Requirement 5: Idempotent Deployment with Rollback

**User Story:** As a DevOps engineer, I want idempotent deployments with rollback capability, so that I can safely deploy and recover from failed deployments.

#### Acceptance Criteria

1. THE Deployment_Engine SHALL support multiple executions without creating duplicate resources
2. WHEN a deployment fails, THE Deployment_Engine SHALL provide rollback capability to the previous stable state
3. THE Deployment_Engine SHALL maintain Terraform state consistency across deployment attempts
4. THE Deployment_Engine SHALL validate resource state before making changes
5. WHEN rolling back, THE Deployment_Engine SHALL restore all resources to their previous configuration

### Requirement 6: Interactive Deployment Interface

**User Story:** As a system administrator, I want an interactive wrapper script for deployment parameters, so that I can easily configure and deploy the FortiGate system without manual Terraform commands.

#### Acceptance Criteria

1. THE Wrapper_Script SHALL prompt users interactively for all required deployment parameters
2. THE Wrapper_Script SHALL validate user inputs before proceeding with deployment
3. THE Wrapper_Script SHALL generate Terraform plans without automatic execution
4. WHEN invalid parameters are provided, THE Wrapper_Script SHALL display clear error messages and re-prompt
5. THE Wrapper_Script SHALL save user configurations for future deployments

### Requirement 7: Integration with Analysis System

**User Story:** As a security engineer, I want integration with the FortiGate Terraform Analysis System, so that I can validate configurations before deployment.

#### Acceptance Criteria

1. THE Wrapper_Script SHALL integrate with the existing FortiGate Terraform Analysis System
2. WHEN generating deployment plans, THE Wrapper_Script SHALL run analysis validation automatically
3. THE Analysis_System SHALL validate FortiGate configurations against security best practices
4. WHEN validation fails, THE Wrapper_Script SHALL display analysis results and prevent deployment
5. THE Analysis_System SHALL generate reports on configuration compliance and security posture
6. THE Deployment_Engine SHALL leverage best practices identified by the FortiGate Terraform Analysis project

### Requirement 8: Security Configuration Management

**User Story:** As a security administrator, I want proper security groups and NACLs configured, so that network access is controlled according to security policies.

#### Acceptance Criteria

1. THE Deployment_Engine SHALL create security groups with least-privilege access rules
2. THE Deployment_Engine SHALL configure Network ACLs for additional layer of security
3. WHEN creating security rules, THE Deployment_Engine SHALL follow the principle of deny-by-default
4. THE Deployment_Engine SHALL allow only necessary ports and protocols for FortiGate operation
5. THE Deployment_Engine SHALL create separate security groups for management and data plane traffic

### Requirement 9: Terraform State Management

**User Story:** As a DevOps engineer, I want proper Terraform state management, so that multiple team members can collaborate safely on infrastructure changes.

#### Acceptance Criteria

1. THE Deployment_Engine SHALL use remote state backend for Terraform state storage
2. THE Deployment_Engine SHALL implement state locking to prevent concurrent modifications
3. THE Deployment_Engine SHALL backup state files before making changes
4. WHEN state corruption occurs, THE Deployment_Engine SHALL provide state recovery mechanisms
5. THE Deployment_Engine SHALL encrypt state files both in transit and at rest

### Requirement 10: Configuration Parsing and Validation

**User Story:** As a network engineer, I want the system to parse and validate FortiGate configurations, so that I can ensure configurations are correct before deployment.

#### Acceptance Criteria

1. THE Analysis_System SHALL parse Terraform configuration files for FortiGate resources
2. THE Analysis_System SHALL validate FortiGate configuration syntax and parameters
3. WHEN parsing configuration files, THE Analysis_System SHALL detect missing required parameters
4. THE Analysis_System SHALL validate network interface configurations against AWS constraints
5. THE Analysis_System SHALL generate configuration reports with recommendations for improvements

### Requirement 12: Web-Based Deployment Frontend

**User Story:** As a system administrator, I want a web-based frontend for the deployment system, so that I can manage FortiGate deployments through an intuitive graphical interface.

#### Acceptance Criteria

1. THE Web_Frontend SHALL provide a Streamlit-based web application for deployment management
2. THE Web_Frontend SHALL allow users to input deployment parameters through web forms
3. THE Web_Frontend SHALL display deployment progress and status in real-time
4. THE Web_Frontend SHALL integrate with the Python deployment scripts as a backend
5. THE Web_Frontend SHALL provide visualization of the deployed architecture and traffic flows

### Requirement 14: IAM and Security Access Requirements

**User Story:** As a security administrator, I want to specify the exact IAM permissions and security access requirements for third-party vendors, so that they can set up the landing zone with appropriate access controls.

#### Acceptance Criteria

1. THE Deployment_Engine SHALL document all required IAM permissions for FortiGate deployment
2. THE Deployment_Engine SHALL specify IAM roles and policies needed for Terraform execution
3. THE Deployment_Engine SHALL define access requirements for AWS Secrets Manager for keys and passwords
4. THE Deployment_Engine SHALL specify minimum required permissions following least-privilege principle
5. THE Documentation SHALL provide IAM policy templates for third-party vendor setup

### Requirement 16: Code Repository Integration

**User Story:** As a project manager, I want instructions for uploading the deployed code to customer repositories, so that customers can maintain and version control their FortiGate deployment code.

#### Acceptance Criteria

1. THE Documentation SHALL provide step-by-step instructions for uploading code to GitHub repositories
2. THE Documentation SHALL provide step-by-step instructions for uploading code to AWS CodeCommit repositories
3. THE Documentation SHALL include repository structure recommendations for customer maintenance
4. THE Documentation SHALL specify which files and directories should be included in customer repositories
5. THE Documentation SHALL provide guidance on setting up CI/CD pipelines for ongoing deployments

### Requirement 17: AMI Discovery and Selection

**User Story:** As a deployment engineer, I want automatic discovery of FortiGate AMIs from AWS Marketplace, so that I can deploy with the latest available AMI without manual lookup.

#### Acceptance Criteria

1. THE AMI_Discovery_System SHALL automatically discover FortiGate AMIs from AWS Marketplace using Fortinet's official AWS account ID (679593333241)
2. WHEN discovering AMIs, THE AMI_Discovery_System SHALL support filtering by FortiGate version (6.2, 6.4, 7.0, 7.2, 7.4, 7.6)
3. WHEN discovering AMIs, THE AMI_Discovery_System SHALL support filtering by license type (BYOL, OnDemand, Reserved)
4. WHEN discovering AMIs, THE AMI_Discovery_System SHALL support filtering by architecture (x86_64, arm64)
5. THE AMI_Discovery_System SHALL return the latest available AMI matching the specified criteria sorted by creation date
6. WHEN no AMI matches the criteria, THE AMI_Discovery_System SHALL return an error with available alternatives
7. THE AMI_Discovery_System SHALL validate that discovered AMIs are in "available" state before returning them
8. THE AMI_Discovery_System SHALL support manual AMI specification to override automatic discovery

### Requirement 18: License Management and Storage

**User Story:** As a security administrator, I want secure storage and retrieval of FortiGate licenses, so that BYOL deployments can access licenses without exposing sensitive data.

#### Acceptance Criteria

1. THE License_Manager SHALL support storing FortiGate license files in AWS Secrets Manager with encryption at rest
2. THE License_Manager SHALL support storing FortiGate license files in S3 buckets with server-side encryption
3. WHEN storing licenses in Secrets Manager, THE License_Manager SHALL create separate secrets for primary and backup FortiGate licenses
4. WHEN storing licenses in S3, THE License_Manager SHALL apply server-side encryption (AES256) and block public access
5. THE License_Manager SHALL validate FortiGate license file format before storage
6. THE License_Manager SHALL retrieve license files during deployment and apply them to FortiGate instances
7. WHEN license retrieval fails, THE License_Manager SHALL provide clear error messages and prevent deployment
8. THE License_Manager SHALL support IAM role-based access for license retrieval without requiring access keys

### Requirement 19: AWS Marketplace Integration

**User Story:** As a procurement manager, I want integration with AWS Marketplace for FortiGate licensing, so that I can use OnDemand and Reserved instance pricing models.

#### Acceptance Criteria

1. THE Deployment_Engine SHALL support BYOL (Bring Your Own License) AMIs for customers with existing FortiGate licenses
2. THE Deployment_Engine SHALL support OnDemand (Pay-As-You-Go) AMIs for customers wanting hourly licensing
3. THE Deployment_Engine SHALL support Reserved Instance AMIs for customers with long-term commitments
4. WHEN using OnDemand or Reserved AMIs, THE Deployment_Engine SHALL not require license file configuration
5. THE Deployment_Engine SHALL validate AWS Marketplace subscription status for OnDemand and Reserved AMIs
6. WHEN marketplace subscription is missing, THE Deployment_Engine SHALL provide clear instructions for subscription
7. THE Deployment_Engine SHALL document cost implications for each licensing model in deployment output

### Requirement 20: Cost Optimization and Licensing Model Selection

**User Story:** As a financial analyst, I want clear cost information for different licensing models, so that I can make informed decisions about FortiGate deployment costs.

#### Acceptance Criteria

1. THE Deployment_Engine SHALL provide cost estimates for BYOL deployments (EC2 costs only)
2. THE Deployment_Engine SHALL provide cost estimates for OnDemand deployments (EC2 + licensing costs)
3. THE Deployment_Engine SHALL provide cost estimates for Reserved Instance deployments (upfront + reduced hourly costs)
4. THE Deployment_Engine SHALL recommend optimal licensing model based on deployment duration and usage patterns
5. WHEN deployment duration exceeds 6 months, THE Deployment_Engine SHALL recommend Reserved Instance licensing
6. WHEN deployment is for testing or short-term use, THE Deployment_Engine SHALL recommend OnDemand licensing
7. WHEN customer has existing licenses, THE Deployment_Engine SHALL recommend BYOL licensing
8. THE Deployment_Engine SHALL display cost comparison between licensing models during configuration

### Requirement 21: Security Requirements for License Storage and Access

**User Story:** As a security officer, I want secure handling of FortiGate licenses with proper access controls, so that license data is protected according to security policies.

#### Acceptance Criteria

1. THE License_Manager SHALL encrypt all license data in transit using TLS 1.2 or higher
2. THE License_Manager SHALL encrypt all license data at rest using AWS managed encryption keys
3. THE License_Manager SHALL implement least-privilege IAM policies for license access
4. THE License_Manager SHALL support IAM roles instead of access keys for license retrieval
5. THE License_Manager SHALL log all license access attempts to CloudTrail for audit purposes
6. THE License_Manager SHALL validate license file integrity before application to FortiGate instances
7. WHEN using S3 for license storage, THE License_Manager SHALL enable S3 bucket versioning for license file history
8. THE License_Manager SHALL support automatic license rotation and update mechanisms

### Requirement 22: Streamlit Web Application Deployment

**User Story:** As a system administrator, I want clear instructions for deploying and operating the Streamlit web application, so that I can provide a web-based interface for FortiGate deployments.

#### Acceptance Criteria

1. THE Documentation SHALL provide step-by-step instructions for installing Streamlit application dependencies
2. THE Documentation SHALL include instructions for configuring the Streamlit application environment
3. THE Documentation SHALL provide commands for starting and stopping the Streamlit application
4. THE Documentation SHALL include instructions for deploying the Streamlit app on different platforms (local, Docker, cloud)
5. THE Documentation SHALL specify network requirements and port configurations for the Streamlit application
6. THE Documentation SHALL include instructions for securing the Streamlit application with authentication
7. THE Documentation SHALL provide troubleshooting steps for common Streamlit deployment issues
8. THE Documentation SHALL include instructions for scaling and load balancing the Streamlit application

### Requirement 23: Monitoring and Troubleshooting Guide

**User Story:** As a network operations engineer, I want detailed monitoring and troubleshooting documentation, so that I can effectively monitor FortiGate deployments and resolve issues quickly.

#### Acceptance Criteria

1. THE Documentation SHALL provide comprehensive VPC Flow Logs configuration and analysis instructions
2. THE Documentation SHALL document all CloudWatch log groups, metrics, and dashboards created by the deployment
3. THE Documentation SHALL include step-by-step troubleshooting procedures for common deployment and operational issues
4. THE Documentation SHALL provide CloudWatch query examples for analyzing FortiGate traffic and performance
5. THE Documentation SHALL document FortiGate-specific logging configuration and log analysis procedures
6. THE Documentation SHALL include network troubleshooting procedures for BGP, routing, and connectivity issues
7. THE Documentation SHALL provide performance monitoring and alerting configuration guidance
8. THE Documentation SHALL include disaster recovery and backup procedures for FortiGate configurations

### Requirement 24: Documentation and Usage Examples

**User Story:** As a new team member, I want comprehensive documentation and usage examples, so that I can understand and use the deployment system effectively.

#### Acceptance Criteria

1. THE Deployment_Engine SHALL include comprehensive README documentation
2. THE Documentation SHALL provide step-by-step deployment instructions
3. THE Documentation SHALL include example configurations for common scenarios
4. THE Documentation SHALL explain troubleshooting procedures for common issues
5. THE Documentation SHALL include architecture diagrams showing traffic flows and component relationships