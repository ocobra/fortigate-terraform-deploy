# Implementation Plan: Streamlit Web Application Enhancement

## Overview

This implementation plan breaks down the enhancement of the Streamlit web application into discrete, manageable coding tasks. Each task builds on previous work and includes specific requirements references. The plan follows a phased approach to ensure incremental progress with validation at each step.

## Tasks

- [x] 1. Set up project structure and core infrastructure
  - Create enhanced web application file structure
  - Set up Python virtual environment with all dependencies
  - Configure Streamlit app settings and page configuration
  - _Requirements: All (foundation)_

- [ ] 2. Implement Session State Manager
  - [x] 2.1 Create session state initialization function
    - Define all session state variables with default values
    - Initialize deployment_config, deployment_status, deployment_logs, aws_session, etc.
    - _Requirements: 12.1, 12.2_
  
  - [x] 2.2 Implement session state getter and setter functions
    - Create functions to safely get/set configuration in session state
    - Create functions to manage deployment status and logs
    - _Requirements: 12.1, 12.2, 12.3_
  
  - [ ]* 2.3 Write property test for session state persistence
    - **Property 24: Session State Persistence Across Navigation**
    - **Validates: Requirements 12.1, 12.2, 12.3**

- [ ] 3. Implement Configuration Manager
  - [x] 3.1 Create ConfigurationManager class with YAML import/export
    - Implement import_yaml() to parse YAML and create DeploymentConfig
    - Implement export_yaml() to serialize DeploymentConfig to YAML
    - _Requirements: 2.1, 2.3_
  
  - [x] 3.2 Add JSON import/export functionality
    - Implement import_json() to parse JSON and create DeploymentConfig
    - Implement export_json() to serialize DeploymentConfig to JSON
    - _Requirements: 2.2, 2.4_
  
  - [x] 3.3 Implement sensitive data redaction
    - Create redact_sensitive_data() function
    - Redact passwords, access keys, and secret names
    - _Requirements: 2.5_
  
  - [x] 3.4 Add configuration validation
    - Implement validate_config() to check required fields
    - Validate parameter formats and types
    - _Requirements: 2.6_
  
  - [ ]* 3.5 Write property test for YAML round-trip
    - **Property 1: Configuration Round-Trip Preservation**
    - **Validates: Requirements 2.1, 2.3, 2.7**
  
  - [ ]* 3.6 Write property test for JSON round-trip
    - **Property 2: JSON Configuration Round-Trip Preservation**
    - **Validates: Requirements 2.2, 2.4, 2.7**
  
  - [ ]* 3.7 Write property test for sensitive data redaction
    - **Property 3: Sensitive Data Redaction**
    - **Validates: Requirements 2.5**
  
  - [ ]* 3.8 Write property test for invalid configuration rejection
    - **Property 4: Invalid Configuration Rejection**
    - **Validates: Requirements 2.6**


- [ ] 4. Implement AWS Integration Layer
  - [x] 4.1 Create AWSIntegrationManager class
    - Initialize with AWS credentials
    - Create authenticated boto3 session
    - Integrate ConfigurationValidator from deploy.py
    - _Requirements: 3.1_
  
  - [x] 4.2 Implement resource validation methods
    - Add validate_vpc() method
    - Add validate_subnets() method
    - Add validate_enis() method
    - Add validate_eips() method
    - Add validate_transit_gateway() method
    - Add validate_ami() method
    - Add validate_key_pair() method
    - _Requirements: 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8_
  
  - [x] 4.3 Integrate AMI Discovery functionality
    - Import AMIDiscovery class from deploy.py
    - Implement discover_amis() wrapper method
    - Implement list_fortigate_versions() method
    - _Requirements: 4.1, 4.2, 4.3, 4.4_
  
  - [x] 4.4 Integrate License Manager functionality
    - Import LicenseManager class from deploy.py
    - Implement test_secrets_manager_access() method
    - Implement test_s3_access() method
    - _Requirements: 5.10_
  
  - [ ]* 4.5 Write property test for AWS resource validation
    - **Property 6: AWS Resource Validation Correctness**
    - **Validates: Requirements 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 3.9**
  
  - [ ]* 4.6 Write property test for AMI discovery filtering
    - **Property 7: AMI Discovery Filtering**
    - **Validates: Requirements 4.2, 4.3, 4.4**
  
  - [ ]* 4.7 Write property test for AMI discovery result completeness
    - **Property 8: AMI Discovery Result Completeness**
    - **Validates: Requirements 4.5, 4.6, 4.7**

- [ ] 5. Implement Terraform Integration Layer
  - [x] 5.1 Create TerraformIntegrationManager class
    - Initialize with terraform directory and backend config
    - Import TerraformManager from deploy.py as base
    - _Requirements: 7.1, 7.2, 7.3_
  
  - [x] 5.2 Implement backend configuration
    - Add configure_backend() method for local and S3 backends
    - Generate backend.tf file for S3 backend
    - _Requirements: 6.1, 6.2, 6.11_
  
  - [x] 5.3 Implement tfvars generation
    - Add generate_tfvars() method
    - Convert DeploymentConfig to terraform.tfvars format
    - _Requirements: 7.7_
  
  - [x] 5.4 Implement Terraform command execution with output streaming
    - Add init() method with real-time output callback
    - Add plan() method with real-time output callback
    - Add apply() method with real-time output callback
    - Add destroy() method with real-time output callback
    - Use subprocess.Popen with stdout/stderr pipes
    - _Requirements: 7.1, 7.2, 7.3, 7.4_
  
  - [x] 5.5 Implement output extraction
    - Add get_outputs() method to retrieve Terraform outputs
    - Parse terraform output command results
    - _Requirements: 10.8_
  
  - [ ]* 5.6 Write property test for tfvars generation
    - **Property 12: Terraform Variables File Generation**
    - **Validates: Requirements 7.7**
  
  - [ ]* 5.7 Write property test for backend configuration file generation
    - **Property 13: Backend Configuration File Generation**
    - **Validates: Requirements 7.8**
  
  - [ ]* 5.8 Write property test for command execution sequence
    - **Property 14: Terraform Command Execution Sequence**
    - **Validates: Requirements 7.1, 7.2, 7.3**
  
  - [ ]* 5.9 Write property test for output streaming
    - **Property 15: Terraform Output Streaming**
    - **Validates: Requirements 7.4, 7.5, 7.6**

- [ ] 6. Implement Deployment Orchestrator
  - [x] 6.1 Create DeploymentOrchestrator class
    - Initialize with DeploymentConfig and skip_validation flag
    - Import DeploymentEngine from deploy.py as base
    - _Requirements: 7.1, 7.2, 7.3_
  
  - [x] 6.2 Implement validation workflow
    - Add validate_configuration() with progress callbacks
    - Integrate AWS resource validation
    - Handle skip_validation option
    - _Requirements: 3.1, 3.10_
  
  - [x] 6.3 Implement plan workflow
    - Add plan_deployment() with progress callbacks
    - Execute Terraform init and plan
    - Save plan file
    - _Requirements: 8.1, 8.2, 8.8, 8.10_
  
  - [x] 6.4 Implement deployment workflow
    - Add execute_deployment() with progress callbacks
    - Execute full deployment sequence
    - Track progress and status
    - _Requirements: 7.1, 7.2, 7.3, 10.1, 10.2, 10.3_
  
  - [x] 6.5 Implement destroy workflow
    - Add destroy_deployment() with progress callbacks
    - Execute Terraform destroy
    - Handle confirmation requirement
    - _Requirements: 9.2, 9.3, 9.4, 9.5, 9.6_
  
  - [ ]* 6.6 Write property test for deployment status consistency
    - **Property 20: Deployment Status Consistency**
    - **Validates: Requirements 10.3**

- [ ] 7. Implement Cost Calculator
  - [x] 7.1 Create CostCalculator class
    - Implement calculate_byol_cost() method
    - Implement calculate_ondemand_cost() method
    - Implement calculate_reserved_cost() method
    - Use AWS Pricing API or hardcoded pricing data
    - _Requirements: 14.1, 14.2, 14.3_
  
  - [x] 7.2 Implement cost comparison
    - Add compare_licensing_models() method
    - Calculate costs for all licensing models
    - Determine recommended model based on duration
    - _Requirements: 14.7, 14.8, 14.9_
  
  - [ ]* 7.3 Write property test for cost calculation consistency
    - **Property 27: Cost Calculation Consistency**
    - **Validates: Requirements 14.1, 14.2, 14.3, 14.4, 14.5, 14.6**
  
  - [ ]* 7.4 Write property test for cost comparison completeness
    - **Property 28: Cost Comparison Completeness**
    - **Validates: Requirements 14.7, 14.8**

- [x] 8. Checkpoint - Ensure all backend components work
  - Ensure all tests pass, ask the user if questions arise.


- [ ] 9. Implement UI Components and Base Layout
  - [x] 9.1 Create main application structure
    - Set up Streamlit page configuration
    - Create sidebar navigation
    - Implement page routing logic
    - Add custom CSS styling
    - _Requirements: 13.1, 13.2, 13.3, 13.11_
  
  - [x] 9.2 Create reusable UI component functions
    - Implement render_parameter_section()
    - Implement render_validation_status()
    - Implement render_progress_bar()
    - Implement render_log_viewer()
    - Implement render_error_message()
    - Implement render_success_message()
    - _Requirements: 11.8, 11.9, 11.10_
  
  - [x] 9.3 Implement help text system
    - Create help text dictionary for all parameters
    - Add tooltip rendering function
    - Integrate help text with parameter inputs
    - _Requirements: 1.12, 11.11_
  
  - [ ]* 9.4 Write property test for help text availability
    - **Property 23: Help Text Availability**
    - **Validates: Requirements 1.12, 11.11**

- [ ] 10. Implement Configuration Page
  - [x] 10.1 Create AWS configuration section
    - Add region selector
    - Add profile input
    - Add access key inputs (conditional)
    - Add environment and owner tag inputs
    - _Requirements: 1.1_
  
  - [x] 10.2 Create Network configuration section
    - Add VPC ID input with validation
    - Add availability zone inputs
    - Add subnet ID inputs for primary and backup (8 total)
    - Add management CIDR inputs
    - _Requirements: 1.2_
  
  - [x] 10.3 Create ENI configuration section
    - Add 8 ENI ID inputs (4 primary, 4 backup)
    - Add inline validation for ENI ID format
    - _Requirements: 1.3_
  
  - [x] 10.4 Create EIP configuration section
    - Add allocate_eips checkbox
    - Add EIP allocation ID inputs (conditional)
    - Add enable_eip_failover checkbox
    - _Requirements: 1.4_
  
  - [x] 10.5 Create FortiGate configuration section
    - Add AMI ID input
    - Add instance type selector
    - Add key pair name input
    - Add password inputs (admin and HA)
    - Add hostname inputs
    - _Requirements: 1.5_
  
  - [x] 10.6 Create Transit Gateway configuration section
    - Add create new TGW checkbox
    - Add existing TGW ID input (conditional)
    - Add BGP ASN inputs
    - Add spoke VPC CIDR inputs
    - _Requirements: 1.8_
  
  - [x] 10.7 Create Monitoring configuration section
    - Add flow logs checkbox
    - Add log retention selector
    - Add detailed monitoring checkbox
    - _Requirements: 1.9_
  
  - [x] 10.8 Create Backend configuration section
    - Add backend type selector (local/S3)
    - Add S3 backend parameters (conditional)
    - Add bootstrap instructions display
    - _Requirements: 1.10, 6.10_
  
  - [x] 10.9 Implement configuration import/export
    - Add file upload widget for YAML/JSON
    - Add export buttons for YAML/JSON
    - Integrate ConfigurationManager
    - Handle import errors gracefully
    - _Requirements: 2.1, 2.2, 2.3, 2.4_
  
  - [x] 10.10 Add configuration validation and save
    - Add "Save Configuration" button
    - Validate all required fields
    - Update session state with configuration
    - Display validation errors inline
    - _Requirements: 1.1-1.11, 13.4, 13.5, 13.9_
  
  - [ ]* 10.11 Write property test for parameter acceptance
    - **Property 5: Parameter Acceptance Completeness**
    - **Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9, 1.10, 1.11**

- [ ] 11. Implement AMI Discovery Page
  - [x] 11.1 Create AMI discovery form
    - Add FortiGate version selector
    - Add license type selector
    - Add architecture selector
    - Add "Discover AMIs" button
    - _Requirements: 4.2, 4.3, 4.4_
  
  - [x] 11.2 Implement AMI discovery execution
    - Call AWSIntegrationManager.discover_amis()
    - Display loading spinner during discovery
    - Handle discovery errors
    - _Requirements: 4.1_
  
  - [x] 11.3 Display discovery results
    - Show latest AMI with metadata (ID, name, description, date)
    - Show alternative AMIs list
    - Add button to auto-populate AMI ID in configuration
    - _Requirements: 4.5, 4.6, 4.7_
  
  - [x] 11.4 Add version listing functionality
    - Add "List All Versions" button
    - Display available FortiGate versions
    - _Requirements: 4.9_
  
  - [ ]* 11.5 Write unit test for AMI discovery UI flow
    - Test discovery button triggers API call
    - Test results display correctly
    - _Requirements: 4.1, 4.5, 4.6, 4.7_

- [ ] 12. Implement Licensing Page
  - [x] 12.1 Create license type selector
    - Add radio buttons for BYOL, OnDemand, Reserved
    - Show/hide relevant sections based on selection
    - _Requirements: 5.1, 5.2, 5.3, 5.4_
  
  - [x] 12.2 Implement BYOL configuration
    - Add license source selector (Secrets Manager / S3)
    - Add Secrets Manager secret name inputs
    - Add S3 bucket and key inputs
    - Add license file upload widgets
    - _Requirements: 5.5, 5.6, 5.7_
  
  - [x] 12.3 Add license validation
    - Implement license file format validation
    - Add "Test Access" buttons for Secrets Manager and S3
    - Display validation results
    - _Requirements: 5.8, 5.10_
  
  - [x] 12.4 Display cost implications
    - Show cost comparison for selected licensing model
    - Link to Cost Analysis page
    - _Requirements: 5.9_
  
  - [ ]* 12.5 Write property test for licensing configuration acceptance
    - **Property 9: Licensing Configuration Acceptance**
    - **Validates: Requirements 5.1, 5.2, 5.3, 5.4, 5.5, 5.6**
  
  - [ ]* 12.6 Write property test for license file validation
    - **Property 10: License File Format Validation**
    - **Validates: Requirements 5.8**

- [ ] 13. Implement Deployment Page
  - [x] 13.1 Create deployment action buttons
    - Add "Plan Only" button
    - Add "Deploy" button
    - Add "Destroy" button
    - Implement button state management (enable/disable based on status)
    - _Requirements: 8.1, 9.1_
  
  - [x] 13.2 Implement plan-only workflow
    - Execute plan workflow when "Plan Only" clicked
    - Display plan output with syntax highlighting
    - Highlight additions (green), changes (yellow), deletions (red)
    - Save plan file
    - _Requirements: 8.2, 8.3, 8.4, 8.5, 8.6, 8.7, 8.8_
  
  - [x] 13.3 Implement deployment workflow
    - Execute deployment workflow when "Deploy" clicked
    - Show progress bar with percentage
    - Display current operation name
    - Stream Terraform logs in real-time
    - Show elapsed and estimated remaining time
    - _Requirements: 7.1, 7.2, 7.3, 10.1, 10.2, 10.3, 10.4, 10.5, 10.6_
  
  - [x] 13.4 Implement destroy workflow
    - Show confirmation dialog when "Destroy" clicked
    - Require typed verification text
    - Execute destroy workflow after confirmation
    - Stream destroy logs
    - _Requirements: 9.2, 9.3, 9.4, 9.5, 9.6, 9.8_
  
  - [x] 13.5 Display deployment results
    - Show deployment summary on completion
    - Display created resource IDs from Terraform outputs
    - Show failure point and errors on failure
    - Add log download button
    - _Requirements: 10.7, 10.8, 10.9, 10.10_
  
  - [ ]* 13.6 Write property test for plan-only mode isolation
    - **Property 16: Plan-Only Mode Isolation**
    - **Validates: Requirements 8.2**
  
  - [ ]* 13.7 Write property test for destroy confirmation requirement
    - **Property 18: Destroy Confirmation Requirement**
    - **Validates: Requirements 9.2, 9.3**
  
  - [ ]* 13.8 Write property test for deployment progress monotonicity
    - **Property 19: Deployment Progress Monotonicity**
    - **Validates: Requirements 10.1, 10.2**
  
  - [ ]* 13.9 Write property test for resource output extraction
    - **Property 21: Resource Output Extraction**
    - **Validates: Requirements 10.8**

- [x] 14. Checkpoint - Ensure core deployment functionality works
  - Ensure all tests pass, ask the user if questions arise.


- [ ] 15. Implement Cost Analysis Page
  - [x] 15.1 Create cost calculation parameter inputs
    - Add deployment duration slider
    - Add instance type selector
    - Add usage pattern selector
    - Add region selector
    - Add "Calculate Costs" button
    - _Requirements: 14.1, 14.2, 14.3_
  
  - [x] 15.2 Implement cost calculation and display
    - Call CostCalculator.compare_licensing_models()
    - Display cost comparison charts using Plotly
    - Show monthly and total costs for each model
    - Highlight recommended licensing model
    - _Requirements: 14.7, 14.8, 14.9_
  
  - [x] 15.3 Add detailed cost breakdown
    - Display cost breakdown table
    - Show EC2 costs, license costs, data transfer costs
    - Calculate and display savings vs most expensive option
    - _Requirements: 14.10, 14.11_
  
  - [ ]* 15.4 Write unit test for cost analysis UI
    - Test cost calculation triggers correctly
    - Test chart rendering with sample data
    - _Requirements: 14.7, 14.8_

- [ ] 16. Implement Monitoring Page
  - [x] 16.1 Create health status display
    - Show primary FortiGate status
    - Show backup FortiGate status
    - Show BGP session status
    - Show throughput metrics
    - _Requirements: (monitoring display)_
  
  - [x] 16.2 Add traffic visualization
    - Create traffic chart using Plotly
    - Display historical traffic data
    - _Requirements: (monitoring display)_
  
  - [x] 16.3 Add event log display
    - Show recent deployment events
    - Display event timestamps
    - _Requirements: (monitoring display)_
  
  - [ ]* 16.4 Write unit test for monitoring page
    - Test status display with mock data
    - Test chart rendering
    - _Requirements: (monitoring display)_

- [ ] 17. Implement Documentation Page
  - [x] 17.1 Create documentation sections
    - Add deployment guide section
    - Add AMI & licensing guide section
    - Add monitoring & troubleshooting section
    - Add architecture overview section
    - Add configuration examples section
    - _Requirements: 15.1, 15.2, 15.3, 15.4, 15.5_
  
  - [x] 17.2 Add external documentation links
    - Link to FortiGate documentation
    - Link to AWS documentation
    - Link to support resources
    - _Requirements: 15.6, 15.7_
  
  - [x] 17.3 Add FAQ section
    - Create expandable FAQ items
    - Cover common questions and issues
    - _Requirements: 15.9_
  
  - [ ]* 17.4 Write unit test for documentation page
    - Test all sections render correctly
    - Test links are valid
    - _Requirements: 15.1-15.10_

- [ ] 18. Implement Error Handling
  - [x] 18.1 Create error handling utility functions
    - Implement handle_configuration_error()
    - Implement handle_aws_error()
    - Implement handle_terraform_error()
    - Implement handle_file_format_error()
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5, 11.6, 11.7_
  
  - [x] 18.2 Integrate error handling throughout application
    - Add try-catch blocks around AWS API calls
    - Add try-catch blocks around Terraform operations
    - Add try-catch blocks around file operations
    - Display user-friendly error messages
    - _Requirements: 11.1-11.7_
  
  - [x] 18.3 Add remediation guidance
    - Include remediation steps in error messages
    - Add links to relevant documentation
    - _Requirements: 11.3, 11.12_
  
  - [ ]* 18.4 Write property test for error message completeness
    - **Property 22: Error Message Completeness**
    - **Validates: Requirements 11.1, 11.2, 11.4, 11.5, 11.6**

- [ ] 19. Implement Session State Management Features
  - [x] 19.1 Add configuration clear functionality
    - Create "Clear Configuration" button
    - Implement clear_config() function
    - Add warning dialog for unsaved changes
    - _Requirements: 12.9, 12.10_
  
  - [x] 19.2 Implement sensitive data cleanup
    - Clear passwords from session state after deployment
    - Clear access keys from session state after deployment
    - _Requirements: 12.8_
  
  - [x] 19.3 Add session state persistence validation
    - Ensure configuration persists across page navigation
    - Ensure deployment status persists
    - Ensure logs persist
    - _Requirements: 12.1, 12.2, 12.3, 12.6, 12.7_
  
  - [ ]* 19.4 Write property test for session state update on import
    - **Property 25: Session State Update on Import**
    - **Validates: Requirements 12.4**
  
  - [ ]* 19.5 Write property test for sensitive data cleanup
    - **Property 26: Sensitive Data Cleanup**
    - **Validates: Requirements 12.8**
  
  - [ ]* 19.6 Write property test for configuration clear warning
    - **Property 30: Configuration Clear Warning**
    - **Validates: Requirements 12.10**

- [ ] 20. Implement Validation Features
  - [x] 20.1 Add skip validation option
    - Add "Skip AWS Validation" checkbox in configuration
    - Store skip_validation flag in session state
    - Pass flag to DeploymentOrchestrator
    - _Requirements: 3.10_
  
  - [x] 20.2 Implement real-time validation
    - Add validation on parameter input change
    - Display validation status inline
    - Cache validation results
    - _Requirements: 3.2-3.8, 13.8_
  
  - [x] 20.3 Add validation result display
    - Show validation status for each resource type
    - Use color coding (green/red) for status
    - Display validation error messages
    - _Requirements: 3.9_
  
  - [ ]* 20.4 Write property test for validation skip option
    - **Property 29: Validation Skip Option Availability**
    - **Validates: Requirements 3.10**

- [ ] 21. Add Backend Configuration Features
  - [x] 21.1 Implement S3 backend validation
    - Validate S3 bucket exists
    - Validate DynamoDB table exists
    - Test S3 and DynamoDB access
    - _Requirements: 6.11_
  
  - [x] 21.2 Add bootstrap instructions display
    - Show bootstrap setup steps when S3 backend selected
    - Provide example commands
    - Link to bootstrap documentation
    - _Requirements: 6.10_
  
  - [ ]* 21.3 Write property test for backend configuration acceptance
    - **Property 11: Backend Configuration Acceptance**
    - **Validates: Requirements 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7, 6.8, 6.9**

- [ ] 22. Implement Plan File Management
  - [x] 22.1 Add plan file persistence
    - Save plan file after generation
    - Store plan file path in session state
    - _Requirements: 8.8_
  
  - [x] 22.2 Add apply saved plan functionality
    - Add "Apply Saved Plan" button (conditional)
    - Execute apply with saved plan file
    - _Requirements: 8.9_
  
  - [ ]* 22.3 Write property test for plan file persistence
    - **Property 17: Plan File Persistence**
    - **Validates: Requirements 8.8**

- [ ] 23. Add UI Polish and Refinements
  - [x] 23.1 Implement configuration summary view
    - Create read-only configuration summary
    - Display before deployment
    - Show all key parameters
    - _Requirements: 13.1_
  
  - [x] 23.2 Add input validation indicators
    - Show required field indicators (*)
    - Show optional field indicators
    - Display format hints
    - _Requirements: 13.4, 13.5_
  
  - [x] 23.3 Implement responsive design
    - Test on different screen sizes
    - Adjust layout for mobile/tablet
    - _Requirements: 13.12_
  
  - [ ]* 23.4 Write unit tests for UI components
    - Test parameter section rendering
    - Test validation status display
    - Test progress bar display
    - _Requirements: 13.1-13.12_

- [ ] 24. Write Integration Tests
  - [ ]* 24.1 Write integration test for configuration import/export workflow
    - Test full import → modify → export → import cycle
    - Verify configuration preservation
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.7_
  
  - [ ]* 24.2 Write integration test for deployment workflow
    - Test configuration → validation → plan → deploy sequence
    - Mock AWS and Terraform calls
    - Verify state transitions
    - _Requirements: 7.1, 7.2, 7.3, 10.1, 10.2, 10.3_
  
  - [ ]* 24.3 Write integration test for destroy workflow
    - Test destroy confirmation → execution → completion
    - Mock Terraform destroy
    - Verify state cleanup
    - _Requirements: 9.2, 9.3, 9.4, 9.5, 9.6_

- [ ] 25. Final Testing and Documentation
  - [ ]* 25.1 Run all unit tests and ensure 80%+ coverage
    - Execute pytest with coverage report
    - Fix any failing tests
    - _Requirements: All_
  
  - [ ]* 25.2 Run all property tests with 100 iterations
    - Execute Hypothesis tests
    - Verify all properties hold
    - _Requirements: All testable properties_
  
  - [ ] 25.3 Create user documentation
    - Write README for web application
    - Document all features and parameters
    - Add screenshots and examples
    - _Requirements: 15.1-15.10_
  
  - [ ] 25.4 Create deployment guide
    - Document how to run the web application
    - Document dependencies and setup
    - Document configuration options
    - _Requirements: 15.1_

- [ ] 26. Final Checkpoint - Complete application ready for use
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional property-based and unit tests that can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation at key milestones
- Property tests validate universal correctness properties with 100+ iterations
- Unit tests validate specific examples and edge cases
- Integration tests validate end-to-end workflows
- The implementation reuses existing infrastructure from deploy.py to minimize duplication

