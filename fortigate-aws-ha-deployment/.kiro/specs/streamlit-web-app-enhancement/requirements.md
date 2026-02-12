# Requirements Document

## Introduction

This document specifies the requirements for enhancing the Streamlit web application to achieve complete feature parity with the deploy.py CLI script. The enhanced web application will provide a comprehensive, user-friendly interface for deploying and managing FortiGate HA pairs on AWS, supporting all 60+ deployment parameters, real AWS API integration, Terraform deployment execution, and advanced features like configuration import/export and live deployment tracking.

## Glossary

- **Web_Application**: The Streamlit-based web interface for FortiGate deployment
- **CLI_Script**: The deploy.py command-line interface script
- **Deployment_Engine**: The backend system that orchestrates FortiGate HA deployment
- **Configuration_Object**: A structured data object containing all deployment parameters
- **ENI**: Elastic Network Interface - AWS network interface resource
- **EIP**: Elastic IP - AWS static public IP address
- **AMI**: Amazon Machine Image - VM template for EC2 instances
- **Transit_Gateway**: AWS Transit Gateway for hub-and-spoke network architecture
- **Terraform**: Infrastructure-as-code tool for AWS resource provisioning
- **Backend_Configuration**: Terraform state management configuration (local or S3)
- **Property_Test**: Automated test that validates universal properties across generated inputs
- **AWS_Session**: Authenticated connection to AWS API services
- **Validation_Engine**: Component that validates AWS resources and configuration parameters

## Requirements

### Requirement 1: Complete Parameter Support

**User Story:** As a network engineer, I want the web application to support all deployment parameters from the CLI script, so that I have the same capabilities in both interfaces.

#### Acceptance Criteria

1. THE Web_Application SHALL accept all AWS configuration parameters (region, profile, access keys)
2. THE Web_Application SHALL accept all network configuration parameters (VPC, subnets, AZs, CIDRs)
3. THE Web_Application SHALL accept all 8 ENI IDs (4 per FortiGate instance)
4. THE Web_Application SHALL accept EIP configuration (allocate_eips, EIP IDs, enable_eip_failover)
5. THE Web_Application SHALL accept all FortiGate configuration parameters (AMI, instance type, passwords, hostnames)
6. THE Web_Application SHALL accept AMI discovery configuration (version, license type, architecture)
7. THE Web_Application SHALL accept licensing configuration (BYOL, OnDemand, Reserved with secret/S3 sources)
8. THE Web_Application SHALL accept Transit Gateway configuration (create new or existing, BGP ASNs, spoke CIDRs)
9. THE Web_Application SHALL accept monitoring configuration (flow logs, retention, detailed monitoring)
10. THE Web_Application SHALL accept backend configuration (local or S3 with bucket, key, DynamoDB table)
11. THE Web_Application SHALL accept environment and owner tags
12. THE Web_Application SHALL provide context-sensitive help for each parameter

### Requirement 2: Configuration Import and Export

**User Story:** As a deployment manager, I want to import and export deployment configurations, so that I can reuse settings across multiple deployments.

#### Acceptance Criteria

1. WHEN a user uploads a YAML configuration file, THE Web_Application SHALL parse and load all parameters
2. WHEN a user uploads a JSON configuration file, THE Web_Application SHALL parse and load all parameters
3. WHEN a user clicks export configuration, THE Web_Application SHALL generate a YAML file with current parameters
4. WHEN a user clicks export configuration, THE Web_Application SHALL generate a JSON file with current parameters
5. WHEN exporting configuration, THE Web_Application SHALL redact sensitive data (passwords, access keys)
6. IF a configuration file contains invalid parameters, THEN THE Web_Application SHALL display specific validation errors
7. THE Web_Application SHALL preserve all parameter values during import/export round-trip operations

### Requirement 3: Real AWS API Integration

**User Story:** As a security admin, I want the web application to validate AWS resources using real API calls, so that I can catch configuration errors before deployment.

#### Acceptance Criteria

1. WHEN a user provides AWS credentials, THE Web_Application SHALL establish an authenticated AWS session
2. WHEN a user enters a VPC ID, THE Web_Application SHALL validate it exists and is available
3. WHEN a user enters subnet IDs, THE Web_Application SHALL validate they exist in the correct availability zones
4. WHEN a user enters ENI IDs, THE Web_Application SHALL validate they exist and are available
5. WHEN a user enters EIP allocation IDs, THE Web_Application SHALL validate they exist
6. WHEN a user enters a Transit Gateway ID, THE Web_Application SHALL validate it exists and is available
7. WHEN a user enters an AMI ID, THE Web_Application SHALL validate it exists and is available
8. WHEN a user enters a key pair name, THE Web_Application SHALL validate it exists in the region
9. IF validation fails for any resource, THEN THE Web_Application SHALL display a clear error message with the resource ID
10. THE Web_Application SHALL provide an option to skip validation for limited-permission scenarios

### Requirement 4: AMI Discovery Integration

**User Story:** As a network engineer, I want the web application to discover FortiGate AMIs automatically, so that I don't need to manually find AMI IDs.

#### Acceptance Criteria

1. WHEN a user enables AMI discovery, THE Web_Application SHALL query AWS Marketplace for FortiGate AMIs
2. WHEN discovering AMIs, THE Web_Application SHALL filter by FortiGate version (7.6, 7.4, 7.2, etc.)
3. WHEN discovering AMIs, THE Web_Application SHALL filter by license type (BYOL, OnDemand, Reserved)
4. WHEN discovering AMIs, THE Web_Application SHALL filter by architecture (x86_64, arm64)
5. WHEN AMI discovery succeeds, THE Web_Application SHALL display the latest matching AMI with metadata
6. WHEN AMI discovery succeeds, THE Web_Application SHALL display alternative AMI options
7. WHEN AMI discovery succeeds, THE Web_Application SHALL auto-populate the AMI ID field
8. IF no matching AMIs are found, THEN THE Web_Application SHALL display a helpful error message
9. THE Web_Application SHALL provide a button to list all available FortiGate versions

### Requirement 5: Licensing Configuration

**User Story:** As a deployment manager, I want to configure FortiGate licensing through the web interface, so that I can manage BYOL, OnDemand, and Reserved licensing models.

#### Acceptance Criteria

1. THE Web_Application SHALL support BYOL licensing with AWS Secrets Manager integration
2. THE Web_Application SHALL support BYOL licensing with S3 bucket integration
3. THE Web_Application SHALL support OnDemand licensing without license files
4. THE Web_Application SHALL support Reserved Instance licensing without license files
5. WHEN BYOL is selected with Secrets Manager, THE Web_Application SHALL accept secret names for primary and backup licenses
6. WHEN BYOL is selected with S3, THE Web_Application SHALL accept bucket name and S3 keys for license files
7. WHEN BYOL is selected, THE Web_Application SHALL provide license file upload functionality
8. WHEN license files are uploaded, THE Web_Application SHALL validate the license file format
9. THE Web_Application SHALL display cost implications for each licensing model
10. THE Web_Application SHALL provide a test button to verify license access (Secrets Manager or S3)

### Requirement 6: Backend Configuration

**User Story:** As a DevOps engineer, I want to configure Terraform backend settings, so that I can use S3 remote state for team collaboration.

#### Acceptance Criteria

1. THE Web_Application SHALL support local backend configuration
2. THE Web_Application SHALL support S3 backend configuration with all required parameters
3. WHEN S3 backend is selected, THE Web_Application SHALL accept S3 bucket name
4. WHEN S3 backend is selected, THE Web_Application SHALL accept S3 key path
5. WHEN S3 backend is selected, THE Web_Application SHALL accept S3 region
6. WHEN S3 backend is selected, THE Web_Application SHALL accept DynamoDB table name for locking
7. WHEN S3 backend is selected, THE Web_Application SHALL accept encryption settings
8. WHEN S3 backend is selected, THE Web_Application SHALL accept optional KMS key ID
9. WHEN S3 backend is selected, THE Web_Application SHALL accept optional AWS profile
10. THE Web_Application SHALL display bootstrap setup instructions for S3 backend
11. THE Web_Application SHALL validate S3 backend configuration before deployment

### Requirement 7: Terraform Deployment Integration

**User Story:** As a network engineer, I want to execute Terraform deployments from the web interface, so that I can deploy FortiGate without using the command line.

#### Acceptance Criteria

1. WHEN a user clicks deploy, THE Web_Application SHALL execute Terraform init command
2. WHEN a user clicks deploy, THE Web_Application SHALL execute Terraform plan command
3. WHEN a user clicks deploy, THE Web_Application SHALL execute Terraform apply command
4. WHEN Terraform commands execute, THE Web_Application SHALL stream output logs in real-time
5. WHEN Terraform execution completes, THE Web_Application SHALL display success or failure status
6. IF Terraform execution fails, THEN THE Web_Application SHALL display error messages with context
7. THE Web_Application SHALL generate terraform.tfvars file from configuration parameters
8. THE Web_Application SHALL generate backend.tf file for S3 backend configuration
9. THE Web_Application SHALL handle Terraform state locking conflicts gracefully
10. THE Web_Application SHALL provide progress indicators during long-running operations

### Requirement 8: Plan-Only Mode

**User Story:** As a deployment manager, I want to generate Terraform plans without applying them, so that I can review changes before deployment.

#### Acceptance Criteria

1. THE Web_Application SHALL provide a "Plan Only" button separate from the "Deploy" button
2. WHEN a user clicks "Plan Only", THE Web_Application SHALL execute Terraform plan without apply
3. WHEN plan generation completes, THE Web_Application SHALL display the plan output
4. WHEN plan generation completes, THE Web_Application SHALL highlight resource additions in green
5. WHEN plan generation completes, THE Web_Application SHALL highlight resource changes in yellow
6. WHEN plan generation completes, THE Web_Application SHALL highlight resource deletions in red
7. WHEN plan generation completes, THE Web_Application SHALL display resource count summary
8. THE Web_Application SHALL save the plan file for later application
9. THE Web_Application SHALL provide an option to apply a saved plan
10. THE Web_Application SHALL validate configuration before generating plan

### Requirement 9: Destroy Functionality

**User Story:** As a system administrator, I want to destroy FortiGate deployments from the web interface, so that I can clean up resources without using the CLI.

#### Acceptance Criteria

1. THE Web_Application SHALL provide a "Destroy" button for deployed resources
2. WHEN a user clicks "Destroy", THE Web_Application SHALL display a confirmation dialog
3. WHEN a user confirms destruction, THE Web_Application SHALL execute Terraform destroy command
4. WHEN destruction executes, THE Web_Application SHALL stream output logs in real-time
5. WHEN destruction completes, THE Web_Application SHALL display success or failure status
6. IF destruction fails, THEN THE Web_Application SHALL display error messages with recovery options
7. THE Web_Application SHALL disable the "Destroy" button when no deployment exists
8. THE Web_Application SHALL require explicit confirmation with typed verification text
9. THE Web_Application SHALL display estimated time for destruction operation
10. THE Web_Application SHALL provide progress indicators during destruction

### Requirement 10: Live Deployment Tracking

**User Story:** As a network engineer, I want to see real-time deployment progress, so that I can monitor the deployment status and identify issues quickly.

#### Acceptance Criteria

1. WHEN deployment starts, THE Web_Application SHALL display a progress bar
2. WHEN deployment progresses, THE Web_Application SHALL update progress percentage
3. WHEN deployment progresses, THE Web_Application SHALL display current operation name
4. WHEN deployment progresses, THE Web_Application SHALL stream Terraform logs in real-time
5. WHEN deployment progresses, THE Web_Application SHALL display elapsed time
6. WHEN deployment progresses, THE Web_Application SHALL display estimated remaining time
7. WHEN deployment completes, THE Web_Application SHALL display completion summary
8. WHEN deployment completes, THE Web_Application SHALL display created resource IDs
9. IF deployment fails, THEN THE Web_Application SHALL display failure point and error details
10. THE Web_Application SHALL provide a log download button for troubleshooting

### Requirement 11: Error Handling and User Feedback

**User Story:** As a user, I want clear error messages and guidance, so that I can resolve issues without external help.

#### Acceptance Criteria

1. WHEN a validation error occurs, THE Web_Application SHALL display the specific parameter that failed
2. WHEN a validation error occurs, THE Web_Application SHALL display the reason for failure
3. WHEN a validation error occurs, THE Web_Application SHALL display suggested remediation steps
4. WHEN an AWS API error occurs, THE Web_Application SHALL display the AWS error message
5. WHEN an AWS API error occurs, THE Web_Application SHALL display the affected resource
6. WHEN a Terraform error occurs, THE Web_Application SHALL display the Terraform error output
7. WHEN a Terraform error occurs, THE Web_Application SHALL highlight the problematic configuration
8. THE Web_Application SHALL display success messages with green styling
9. THE Web_Application SHALL display warning messages with yellow styling
10. THE Web_Application SHALL display error messages with red styling
11. THE Web_Application SHALL provide contextual help tooltips for all parameters
12. THE Web_Application SHALL provide links to relevant documentation for errors

### Requirement 12: Session State Management

**User Story:** As a user, I want my configuration to persist during my session, so that I don't lose work when navigating between pages.

#### Acceptance Criteria

1. WHEN a user enters configuration parameters, THE Web_Application SHALL store them in session state
2. WHEN a user navigates between pages, THE Web_Application SHALL preserve configuration parameters
3. WHEN a user returns to a configuration page, THE Web_Application SHALL display previously entered values
4. WHEN a user imports a configuration file, THE Web_Application SHALL update session state
5. WHEN a user exports a configuration file, THE Web_Application SHALL use current session state
6. WHEN deployment starts, THE Web_Application SHALL preserve deployment status in session state
7. WHEN deployment completes, THE Web_Application SHALL preserve deployment results in session state
8. THE Web_Application SHALL clear sensitive data (passwords) from session state after deployment
9. THE Web_Application SHALL provide a "Clear Configuration" button to reset session state
10. THE Web_Application SHALL warn users before clearing configuration with unsaved changes

### Requirement 13: User Interface Organization

**User Story:** As a user, I want an intuitive and organized interface, so that I can easily find and configure all parameters.

#### Acceptance Criteria

1. THE Web_Application SHALL organize parameters into logical sections (AWS, Network, FortiGate, etc.)
2. THE Web_Application SHALL use expandable sections for parameter groups
3. THE Web_Application SHALL use tabs for major configuration categories
4. THE Web_Application SHALL display required parameters with visual indicators
5. THE Web_Application SHALL display optional parameters with visual indicators
6. THE Web_Application SHALL use appropriate input widgets (text, select, checkbox, file upload)
7. THE Web_Application SHALL provide default values for optional parameters
8. THE Web_Application SHALL validate input formats in real-time
9. THE Web_Application SHALL display validation errors inline with input fields
10. THE Web_Application SHALL provide a configuration summary view before deployment
11. THE Web_Application SHALL use consistent styling and color scheme
12. THE Web_Application SHALL be responsive and work on different screen sizes

### Requirement 14: Cost Analysis Integration

**User Story:** As a deployment manager, I want to see cost estimates for different licensing models, so that I can make informed decisions.

#### Acceptance Criteria

1. THE Web_Application SHALL calculate monthly costs for BYOL licensing
2. THE Web_Application SHALL calculate monthly costs for OnDemand licensing
3. THE Web_Application SHALL calculate monthly costs for Reserved Instance licensing
4. WHEN calculating costs, THE Web_Application SHALL include EC2 instance costs
5. WHEN calculating costs, THE Web_Application SHALL include FortiGate license costs
6. WHEN calculating costs, THE Web_Application SHALL include data transfer costs
7. THE Web_Application SHALL display cost comparison charts for licensing models
8. THE Web_Application SHALL display total cost projections for deployment duration
9. THE Web_Application SHALL highlight the most cost-effective licensing model
10. THE Web_Application SHALL allow users to adjust deployment duration for cost analysis
11. THE Web_Application SHALL display cost breakdowns by resource type

### Requirement 15: Documentation and Help

**User Story:** As a new user, I want access to documentation and help, so that I can learn how to use the application effectively.

#### Acceptance Criteria

1. THE Web_Application SHALL provide a documentation page with deployment guides
2. THE Web_Application SHALL provide parameter reference documentation
3. THE Web_Application SHALL provide architecture diagrams
4. THE Web_Application SHALL provide troubleshooting guides
5. THE Web_Application SHALL provide example configurations
6. THE Web_Application SHALL provide links to external FortiGate documentation
7. THE Web_Application SHALL provide links to AWS documentation
8. THE Web_Application SHALL provide tooltips for all input fields
9. THE Web_Application SHALL provide a FAQ section
10. THE Web_Application SHALL provide contact information for support

