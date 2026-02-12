# Design Document: Streamlit Web Application Enhancement

## Overview

This design document specifies the architecture and implementation approach for enhancing the Streamlit web application to achieve complete feature parity with the deploy.py CLI script. The enhanced application will provide a comprehensive, user-friendly web interface for deploying and managing FortiGate HA pairs on AWS.

### Design Goals

1. **Complete Feature Parity**: Support all 60+ parameters and features from deploy.py
2. **Real AWS Integration**: Use boto3 for actual AWS API validation and resource discovery
3. **Terraform Integration**: Execute real Terraform commands with live output streaming
4. **User Experience**: Provide intuitive UI with clear feedback and error handling
5. **Configuration Management**: Support import/export of deployment configurations
6. **Reusability**: Leverage existing DeploymentEngine and related classes from deploy.py
7. **Maintainability**: Organize code into logical modules with clear separation of concerns

### Key Design Decisions

1. **Reuse Existing Infrastructure**: Import and use DeploymentEngine, ConfigurationValidator, AMIDiscovery, LicenseManager, and TerraformManager from deploy.py rather than reimplementing
2. **Session State Management**: Use Streamlit's session_state for preserving configuration across page navigation
3. **Multi-Page Architecture**: Organize functionality into logical pages (Configuration, AMI Discovery, Licensing, Deployment, etc.)
4. **Real-Time Streaming**: Use subprocess with real-time output capture for Terraform command execution
5. **Validation Strategy**: Provide both real-time validation and skip-validation option for limited-permission scenarios
6. **Configuration Serialization**: Support both YAML and JSON for configuration import/export

## Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Streamlit Web Application                 │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ Configuration│  │ AMI Discovery│  │  Licensing   │     │
│  │     Page     │  │     Page     │  │     Page     │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │  Deployment  │  │  Monitoring  │  │     Cost     │     │
│  │     Page     │  │     Page     │  │   Analysis   │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
├─────────────────────────────────────────────────────────────┤
│                   Session State Manager                      │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │Configuration │  │   Validation │  │     AWS      │     │
│  │   Manager    │  │    Engine    │  │   Session    │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │  Deployment  │  │  Terraform   │  │     AMI      │     │
│  │    Engine    │  │   Manager    │  │  Discovery   │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│  ┌──────────────┐  ┌──────────────┐                        │
│  │   License    │  │     Cost     │                        │
│  │   Manager    │  │  Calculator  │                        │
│  └──────────────┘  └──────────────┘                        │
├─────────────────────────────────────────────────────────────┤
│                    External Dependencies                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │    boto3     │  │  Terraform   │  │     YAML     │     │
│  │   (AWS SDK)  │  │     CLI      │  │     JSON     │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
```

### Component Interaction Flow

```
User Input → Streamlit UI → Session State → Configuration Manager
                                                      ↓
                                            Validation Engine
                                                      ↓
                                              AWS Session (boto3)
                                                      ↓
                                            Deployment Engine
                                                      ↓
                                            Terraform Manager
                                                      ↓
                                              AWS Resources
```

## Components and Interfaces

### 1. Session State Manager

**Purpose**: Centralized management of application state across page navigation

**Interface**:
```python
def initialize_session_state() -> None:
    """Initialize all session state variables with default values"""

def get_config() -> Optional[DeploymentConfig]:
    """Retrieve current deployment configuration from session state"""

def set_config(config: DeploymentConfig) -> None:
    """Store deployment configuration in session state"""

def clear_config() -> None:
    """Clear all configuration from session state"""

def get_deployment_status() -> str:
    """Get current deployment status"""

def set_deployment_status(status: str) -> None:
    """Update deployment status"""

def get_deployment_logs() -> List[str]:
    """Retrieve deployment log entries"""

def add_deployment_log(message: str) -> None:
    """Add a log entry to deployment logs"""
```

**State Variables**:
- `deployment_config`: DeploymentConfig object
- `deployment_status`: str (not_started, planning, validating, deploying, deployed, failed, destroying)
- `deployment_logs`: List[str]
- `aws_session`: Optional[boto3.Session]
- `validation_results`: Dict[str, bool]
- `ami_discovery_result`: Optional[Dict]
- `cost_analysis`: Optional[Dict]
- `terraform_output`: str
- `skip_validation`: bool

### 2. Configuration Manager

**Purpose**: Handle configuration import, export, and validation

**Interface**:
```python
class ConfigurationManager:
    def import_yaml(self, file_content: str) -> DeploymentConfig:
        """Parse YAML configuration file and create DeploymentConfig"""
    
    def import_json(self, file_content: str) -> DeploymentConfig:
        """Parse JSON configuration file and create DeploymentConfig"""
    
    def export_yaml(self, config: DeploymentConfig, redact_sensitive: bool = True) -> str:
        """Export configuration to YAML format"""
    
    def export_json(self, config: DeploymentConfig, redact_sensitive: bool = True) -> str:
        """Export configuration to JSON format"""
    
    def validate_config(self, config: DeploymentConfig) -> Tuple[bool, List[str]]:
        """Validate configuration completeness and format"""
    
    def redact_sensitive_data(self, config_dict: Dict) -> Dict:
        """Remove sensitive data from configuration dictionary"""
```

**Implementation Notes**:
- Use dataclasses.asdict() to convert DeploymentConfig to dictionary
- Redact passwords, access keys, and secret names when exporting
- Validate required fields before allowing deployment
- Support partial configurations for incremental building

### 3. AWS Integration Layer

**Purpose**: Provide AWS API integration for validation and discovery

**Interface**:
```python
class AWSIntegrationManager:
    def __init__(self, aws_config: AWSConfig):
        """Initialize with AWS credentials"""
    
    def create_session(self) -> boto3.Session:
        """Create authenticated AWS session"""
    
    def validate_vpc(self, vpc_id: str) -> Tuple[bool, str]:
        """Validate VPC exists and return status message"""
    
    def validate_subnets(self, subnet_ids: List[str], expected_azs: List[str]) -> Tuple[bool, str]:
        """Validate subnets exist in correct AZs"""
    
    def validate_enis(self, eni_ids: List[str]) -> Tuple[bool, str]:
        """Validate ENIs exist and are available"""
    
    def validate_eips(self, eip_allocation_ids: List[str]) -> Tuple[bool, str]:
        """Validate EIP allocations exist"""
    
    def validate_transit_gateway(self, tgw_id: str) -> Tuple[bool, str]:
        """Validate Transit Gateway exists"""
    
    def validate_ami(self, ami_id: str) -> Tuple[bool, str]:
        """Validate AMI exists and is available"""
    
    def validate_key_pair(self, key_name: str) -> Tuple[bool, str]:
        """Validate EC2 key pair exists"""
    
    def discover_amis(self, version: str, license_type: str, architecture: str) -> List[Dict]:
        """Discover FortiGate AMIs matching criteria"""
    
    def list_fortigate_versions(self) -> List[str]:
        """List available FortiGate versions"""
    
    def test_secrets_manager_access(self, secret_name: str) -> Tuple[bool, str]:
        """Test access to Secrets Manager secret"""
    
    def test_s3_access(self, bucket: str, key: str) -> Tuple[bool, str]:
        """Test access to S3 object"""
```

**Implementation Notes**:
- Reuse ConfigurationValidator from deploy.py
- Reuse AMIDiscovery from deploy.py
- Reuse LicenseManager from deploy.py
- Wrap exceptions and return user-friendly error messages
- Cache validation results in session state to avoid repeated API calls

### 4. Terraform Integration Layer

**Purpose**: Execute Terraform commands and stream output

**Interface**:
```python
class TerraformIntegrationManager:
    def __init__(self, terraform_dir: Path, backend_config: BackendConfig):
        """Initialize with Terraform directory and backend configuration"""
    
    def configure_backend(self) -> Tuple[bool, str]:
        """Configure Terraform backend (local or S3)"""
    
    def generate_tfvars(self, config: DeploymentConfig) -> Tuple[bool, str]:
        """Generate terraform.tfvars file"""
    
    def init(self, callback: Callable[[str], None]) -> Tuple[bool, str]:
        """Run terraform init with output streaming"""
    
    def plan(self, callback: Callable[[str], None]) -> Tuple[bool, str]:
        """Run terraform plan with output streaming"""
    
    def apply(self, callback: Callable[[str], None]) -> Tuple[bool, str]:
        """Run terraform apply with output streaming"""
    
    def destroy(self, callback: Callable[[str], None]) -> Tuple[bool, str]:
        """Run terraform destroy with output streaming"""
    
    def get_outputs(self) -> Dict[str, Any]:
        """Retrieve Terraform outputs after successful apply"""
```

**Implementation Notes**:
- Reuse TerraformManager from deploy.py as base
- Add real-time output streaming using subprocess.Popen with stdout/stderr pipes
- Use threading to avoid blocking Streamlit UI during long operations
- Parse Terraform output to extract progress information
- Handle Terraform state locking conflicts gracefully

### 5. Deployment Orchestrator

**Purpose**: Coordinate the deployment workflow

**Interface**:
```python
class DeploymentOrchestrator:
    def __init__(self, config: DeploymentConfig, skip_validation: bool = False):
        """Initialize with deployment configuration"""
    
    def validate_configuration(self, progress_callback: Callable[[str], None]) -> Tuple[bool, List[str]]:
        """Validate all configuration parameters"""
    
    def plan_deployment(self, progress_callback: Callable[[str], None]) -> Tuple[bool, str]:
        """Generate Terraform plan"""
    
    def execute_deployment(self, progress_callback: Callable[[str], None]) -> Tuple[bool, str]:
        """Execute full deployment"""
    
    def destroy_deployment(self, progress_callback: Callable[[str], None]) -> Tuple[bool, str]:
        """Destroy existing deployment"""
    
    def get_deployment_summary(self) -> Dict[str, Any]:
        """Get summary of deployed resources"""
```

**Implementation Notes**:
- Reuse DeploymentEngine from deploy.py as base
- Add progress callbacks for UI updates
- Implement proper error handling and rollback
- Track deployment state for resume capability

### 6. Cost Calculator

**Purpose**: Calculate and compare costs for different licensing models

**Interface**:
```python
class CostCalculator:
    def calculate_byol_cost(self, instance_type: str, duration_months: int, 
                           usage_pattern: str, region: str) -> Dict[str, float]:
        """Calculate BYOL licensing costs"""
    
    def calculate_ondemand_cost(self, instance_type: str, duration_months: int,
                               usage_pattern: str, region: str) -> Dict[str, float]:
        """Calculate OnDemand licensing costs"""
    
    def calculate_reserved_cost(self, instance_type: str, duration_months: int,
                               usage_pattern: str, region: str, term: str) -> Dict[str, float]:
        """Calculate Reserved Instance costs"""
    
    def compare_licensing_models(self, instance_type: str, duration_months: int,
                                usage_pattern: str, region: str) -> Dict[str, Dict]:
        """Compare all licensing models and return cost breakdown"""
    
    def get_recommended_model(self, duration_months: int) -> str:
        """Get recommended licensing model based on duration"""
```

**Implementation Notes**:
- Use AWS Pricing API for accurate EC2 costs
- Use hardcoded FortiGate license costs (updated periodically)
- Support different usage patterns (24/7, business hours, intermittent)
- Calculate total cost of ownership including data transfer

### 7. UI Components

**Purpose**: Reusable UI components for consistent interface

**Interface**:
```python
def render_parameter_section(title: str, parameters: Dict[str, Any], 
                            help_text: Dict[str, str]) -> Dict[str, Any]:
    """Render a section of related parameters with help text"""

def render_validation_status(resource_type: str, is_valid: bool, 
                            message: str) -> None:
    """Display validation status with appropriate styling"""

def render_progress_bar(progress: float, status: str) -> None:
    """Display deployment progress bar with status"""

def render_log_viewer(logs: List[str], auto_scroll: bool = True) -> None:
    """Display scrollable log viewer with real-time updates"""

def render_cost_comparison_chart(cost_data: Dict) -> None:
    """Display cost comparison chart using Plotly"""

def render_configuration_summary(config: DeploymentConfig) -> None:
    """Display read-only summary of configuration"""

def render_error_message(error: str, remediation: Optional[str] = None) -> None:
    """Display error message with optional remediation steps"""

def render_success_message(message: str, details: Optional[Dict] = None) -> None:
    """Display success message with optional details"""
```

## Data Models

### Configuration Data Classes

All data classes are imported from deploy.py:
- `AWSConfig`: AWS credentials and region
- `NetworkConfig`: VPC, subnets, ENIs, EIPs
- `FortiGateConfig`: AMI, instance type, passwords
- `AMIDiscoveryConfig`: AMI discovery settings
- `LicensingConfig`: License type and sources
- `TransitGatewayConfig`: TGW settings and BGP
- `MonitoringConfig`: Logging and monitoring
- `BackendConfig`: Terraform backend settings
- `DeploymentConfig`: Complete configuration

### Additional Data Models

```python
@dataclass
class ValidationResult:
    """Result of configuration validation"""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    validated_resources: Dict[str, bool]

@dataclass
class DeploymentProgress:
    """Deployment progress tracking"""
    status: str  # planning, validating, deploying, deployed, failed
    progress_percent: float
    current_operation: str
    elapsed_time: float
    estimated_remaining: Optional[float]
    logs: List[str]

@dataclass
class CostAnalysis:
    """Cost analysis results"""
    byol_monthly: float
    byol_total: float
    ondemand_monthly: float
    ondemand_total: float
    reserved_monthly: float
    reserved_total: float
    reserved_upfront: float
    recommended_model: str
    savings_vs_most_expensive: float
```

## Page Implementations

### 1. Configuration Page

**Purpose**: Collect all deployment parameters

**Layout**:
- Tabs for parameter categories (AWS, Network, FortiGate, Transit Gateway, Monitoring, Backend)
- Each tab contains related parameters with inline validation
- Import/Export buttons at top
- Save Configuration button at bottom
- Configuration summary sidebar

**Key Features**:
- Real-time format validation
- Required field indicators
- Default value suggestions
- Context-sensitive help tooltips
- Import from YAML/JSON
- Export to YAML/JSON with sensitive data redaction

### 2. AMI Discovery Page

**Purpose**: Discover and select FortiGate AMIs

**Layout**:
- Discovery criteria form (version, license type, architecture)
- Discover button
- Results display with AMI details
- Alternative AMIs list
- Version list button

**Key Features**:
- Real AWS Marketplace query
- Display AMI metadata (name, description, creation date)
- Auto-populate AMI ID in configuration
- List all available FortiGate versions

### 3. Licensing Page

**Purpose**: Configure FortiGate licensing

**Layout**:
- License type selector (BYOL, OnDemand, Reserved)
- BYOL configuration (Secrets Manager or S3)
- License file upload
- Test access buttons
- Cost implications display

**Key Features**:
- Support multiple license sources
- Validate license file format
- Test Secrets Manager/S3 access
- Display cost comparison

### 4. Deployment Page

**Purpose**: Execute and monitor deployments

**Layout**:
- Action buttons (Plan, Deploy, Destroy)
- Progress bar and status
- Real-time log viewer
- Deployment summary
- Resource outputs

**Key Features**:
- Plan-only mode
- Real Terraform execution
- Live output streaming
- Progress tracking
- Error handling with remediation

### 5. Monitoring Page

**Purpose**: Monitor deployed resources

**Layout**:
- Health status cards
- Traffic charts
- Event log
- Resource details

**Key Features**:
- Real-time metrics (if deployed)
- Historical data visualization
- Event timeline
- Quick links to AWS Console

### 6. Cost Analysis Page

**Purpose**: Analyze and compare costs

**Layout**:
- Cost calculation parameters
- Licensing model comparison chart
- Detailed cost breakdown table
- Recommendations

**Key Features**:
- Interactive cost calculator
- Visual cost comparison
- Savings analysis
- Duration-based recommendations

## Error Handling

### Error Categories

1. **Configuration Errors**: Missing or invalid parameters
2. **AWS API Errors**: Resource not found, permission denied
3. **Terraform Errors**: Plan/apply failures, state conflicts
4. **Network Errors**: Connection timeouts, API unavailable
5. **File Errors**: Invalid configuration file format

### Error Handling Strategy

```python
def handle_error(error: Exception, context: str) -> Tuple[str, Optional[str]]:
    """
    Convert exception to user-friendly message with remediation
    
    Returns:
        Tuple of (error_message, remediation_steps)
    """
    if isinstance(error, boto3.exceptions.ClientError):
        return handle_aws_error(error)
    elif isinstance(error, subprocess.CalledProcessError):
        return handle_terraform_error(error)
    elif isinstance(error, yaml.YAMLError):
        return handle_yaml_error(error)
    elif isinstance(error, json.JSONDecodeError):
        return handle_json_error(error)
    else:
        return handle_generic_error(error, context)
```

### Error Display

- Use Streamlit's error, warning, and info message boxes
- Display error message prominently
- Show remediation steps when available
- Provide links to relevant documentation
- Include error details in expandable section
- Log full error details for debugging

## Testing Strategy

### Unit Testing

- Test configuration import/export with various formats
- Test validation logic for each parameter type
- Test cost calculation algorithms
- Test error handling for different error types
- Test session state management
- Test data model serialization/deserialization

### Integration Testing

- Test AWS API integration with mock boto3 responses
- Test Terraform execution with mock subprocess
- Test end-to-end configuration flow
- Test deployment workflow with mocked external dependencies

### Property-Based Testing

Property-based tests will validate universal properties across generated inputs using Hypothesis library. Each test will run a minimum of 100 iterations.



## Correctness Properties

A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.

### Property 1: Configuration Round-Trip Preservation

*For any* valid DeploymentConfig object, exporting to YAML then importing back should produce an equivalent configuration (excluding redacted sensitive fields).

**Validates: Requirements 2.1, 2.3, 2.7**

### Property 2: JSON Configuration Round-Trip Preservation

*For any* valid DeploymentConfig object, exporting to JSON then importing back should produce an equivalent configuration (excluding redacted sensitive fields).

**Validates: Requirements 2.2, 2.4, 2.7**

### Property 3: Sensitive Data Redaction

*For any* DeploymentConfig object containing sensitive data (passwords, access keys, secret names), exporting the configuration should not include those sensitive values in the output.

**Validates: Requirements 2.5**

### Property 4: Invalid Configuration Rejection

*For any* configuration file with invalid parameters (wrong types, missing required fields, invalid formats), importing should fail with specific validation errors identifying the problematic fields.

**Validates: Requirements 2.6**

### Property 5: Parameter Acceptance Completeness

*For any* valid set of deployment parameters (AWS config, network config, FortiGate config, etc.), the Web_Application should accept and store all parameters without loss or corruption.

**Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9, 1.10, 1.11**

### Property 6: AWS Resource Validation Correctness

*For any* AWS resource ID (VPC, subnet, ENI, EIP, Transit Gateway, AMI, key pair), validation should return success if the resource exists and is in a valid state, and return failure with a descriptive error message otherwise.

**Validates: Requirements 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 3.9**

### Property 7: AMI Discovery Filtering

*For any* combination of FortiGate version, license type, and architecture, AMI discovery should return only AMIs that match all specified criteria.

**Validates: Requirements 4.2, 4.3, 4.4**

### Property 8: AMI Discovery Result Completeness

*For any* successful AMI discovery operation, the result should include AMI ID, name, description, and creation date.

**Validates: Requirements 4.5, 4.6, 4.7**

### Property 9: Licensing Configuration Acceptance

*For any* valid licensing configuration (BYOL with Secrets Manager, BYOL with S3, OnDemand, or Reserved), the Web_Application should accept and store the configuration correctly.

**Validates: Requirements 5.1, 5.2, 5.3, 5.4, 5.5, 5.6**

### Property 10: License File Format Validation

*For any* uploaded file, license validation should accept files with valid FortiGate license markers and reject files without proper format.

**Validates: Requirements 5.8**

### Property 11: Backend Configuration Acceptance

*For any* valid backend configuration (local or S3 with all required parameters), the Web_Application should accept and store the configuration correctly.

**Validates: Requirements 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7, 6.8, 6.9**

### Property 12: Terraform Variables File Generation

*For any* valid DeploymentConfig object, generating terraform.tfvars should produce a valid HCL file that Terraform can parse without errors.

**Validates: Requirements 7.7**

### Property 13: Backend Configuration File Generation

*For any* S3 backend configuration, generating backend.tf should produce a valid Terraform backend configuration file.

**Validates: Requirements 7.8**

### Property 14: Terraform Command Execution Sequence

*For any* deployment operation, Terraform commands should execute in the correct sequence: init → plan → apply, with each step completing before the next begins.

**Validates: Requirements 7.1, 7.2, 7.3**

### Property 15: Terraform Output Streaming

*For any* Terraform command execution, output logs should be captured and made available for display, with non-empty output for operations that produce output.

**Validates: Requirements 7.4, 7.5, 7.6**

### Property 16: Plan-Only Mode Isolation

*For any* plan-only operation, only the Terraform plan command should execute, and the apply command should not be invoked.

**Validates: Requirements 8.2**

### Property 17: Plan File Persistence

*For any* successful plan generation, a plan file should be created and saved to disk for later application.

**Validates: Requirements 8.8**

### Property 18: Destroy Confirmation Requirement

*For any* destroy operation, the operation should not proceed unless explicit user confirmation is provided.

**Validates: Requirements 9.2, 9.3**

### Property 19: Deployment Progress Monotonicity

*For any* deployment operation, progress percentage should be monotonically increasing (never decrease) until completion or failure.

**Validates: Requirements 10.1, 10.2**

### Property 20: Deployment Status Consistency

*For any* deployment operation, the deployment status should accurately reflect the current state and transition through valid states only (not_started → planning → validating → deploying → deployed/failed).

**Validates: Requirements 10.3**

### Property 21: Resource Output Extraction

*For any* successful deployment, Terraform outputs should be extracted and displayed, including all created resource IDs.

**Validates: Requirements 10.8**

### Property 22: Error Message Completeness

*For any* error condition (validation, AWS API, Terraform), the error message should include the error type, affected resource/parameter, and a description of what went wrong.

**Validates: Requirements 11.1, 11.2, 11.4, 11.5, 11.6**

### Property 23: Help Text Availability

*For any* configuration parameter field in the UI, context-sensitive help text should be available (either as tooltip, help icon, or expandable section).

**Validates: Requirements 1.12, 11.11**

### Property 24: Session State Persistence Across Navigation

*For any* configuration parameter entered by the user, the value should persist in session state when navigating to a different page and returning.

**Validates: Requirements 12.1, 12.2, 12.3**

### Property 25: Session State Update on Import

*For any* configuration file import operation, all parameters from the file should be loaded into session state and reflected in the UI.

**Validates: Requirements 12.4**

### Property 26: Sensitive Data Cleanup

*For any* deployment operation that completes (success or failure), sensitive data (passwords, access keys) should be cleared from session state.

**Validates: Requirements 12.8**

### Property 27: Cost Calculation Consistency

*For any* set of cost calculation parameters (instance type, duration, usage pattern, region), the calculated costs should be consistent across multiple calculations with the same inputs.

**Validates: Requirements 14.1, 14.2, 14.3, 14.4, 14.5, 14.6**

### Property 28: Cost Comparison Completeness

*For any* cost analysis operation, results should include costs for all three licensing models (BYOL, OnDemand, Reserved) with monthly and total costs.

**Validates: Requirements 14.7, 14.8**

### Property 29: Validation Skip Option Availability

*For any* deployment configuration, the option to skip AWS validation should be available and functional, allowing deployment to proceed without AWS API validation.

**Validates: Requirements 3.10**

### Property 30: Configuration Clear Warning

*For any* clear configuration operation when unsaved changes exist, a warning should be displayed before clearing.

**Validates: Requirements 12.10**



## Error Handling

### Error Handling Principles

1. **User-Friendly Messages**: Convert technical errors to clear, actionable messages
2. **Context Preservation**: Include relevant context (resource IDs, parameter names) in error messages
3. **Remediation Guidance**: Provide suggested next steps when possible
4. **Graceful Degradation**: Allow operations to continue when non-critical errors occur
5. **Comprehensive Logging**: Log all errors with full details for debugging

### Error Categories and Handling

#### 1. Configuration Errors

**Examples**:
- Missing required parameters
- Invalid parameter formats
- Incompatible parameter combinations

**Handling**:
```python
def handle_configuration_error(error: ValidationError) -> None:
    st.error(f"Configuration Error: {error.parameter}")
    st.write(f"**Issue**: {error.message}")
    st.write(f"**Expected**: {error.expected_format}")
    if error.remediation:
        st.info(f"**How to fix**: {error.remediation}")
```

#### 2. AWS API Errors

**Examples**:
- Resource not found
- Permission denied
- Rate limiting
- Network timeouts

**Handling**:
```python
def handle_aws_error(error: ClientError) -> None:
    error_code = error.response['Error']['Code']
    error_message = error.response['Error']['Message']
    
    if error_code == 'ResourceNotFoundException':
        st.error(f"AWS Resource Not Found")
        st.write(f"**Resource**: {extract_resource_id(error)}")
        st.write(f"**Message**: {error_message}")
        st.info("**How to fix**: Verify the resource ID is correct and exists in the selected region")
    elif error_code == 'UnauthorizedOperation':
        st.error(f"AWS Permission Denied")
        st.write(f"**Operation**: {extract_operation(error)}")
        st.write(f"**Message**: {error_message}")
        st.info("**How to fix**: Check IAM permissions or use --skip-validation option")
    # ... handle other error codes
```

#### 3. Terraform Errors

**Examples**:
- Plan/apply failures
- State locking conflicts
- Resource creation errors
- Invalid configuration

**Handling**:
```python
def handle_terraform_error(error: subprocess.CalledProcessError) -> None:
    output = error.output.decode('utf-8')
    
    # Parse Terraform error output
    error_lines = extract_error_lines(output)
    
    st.error("Terraform Execution Failed")
    st.write(f"**Exit Code**: {error.returncode}")
    
    with st.expander("Error Details"):
        st.code(output, language="text")
    
    # Provide context-specific remediation
    if "state lock" in output.lower():
        st.info("**How to fix**: Another Terraform operation may be in progress. Wait for it to complete or manually release the state lock.")
    elif "invalid configuration" in output.lower():
        st.info("**How to fix**: Review the configuration parameters and ensure all required fields are provided correctly.")
```

#### 4. File Format Errors

**Examples**:
- Invalid YAML/JSON syntax
- Missing required fields in config file
- Unsupported file format

**Handling**:
```python
def handle_file_format_error(error: Exception, file_type: str) -> None:
    st.error(f"Invalid {file_type.upper()} File Format")
    
    if isinstance(error, yaml.YAMLError):
        st.write(f"**Line**: {error.problem_mark.line if hasattr(error, 'problem_mark') else 'Unknown'}")
        st.write(f"**Issue**: {error.problem}")
    elif isinstance(error, json.JSONDecodeError):
        st.write(f"**Line**: {error.lineno}")
        st.write(f"**Column**: {error.colno}")
        st.write(f"**Issue**: {error.msg}")
    
    st.info("**How to fix**: Validate your configuration file syntax using an online validator")
```

### Error Recovery Strategies

1. **Retry with Backoff**: For transient network errors
2. **Fallback Options**: Offer alternative approaches (e.g., skip validation)
3. **Partial Success**: Continue with successful operations when possible
4. **State Preservation**: Save progress before operations that might fail
5. **Rollback Support**: Provide destroy functionality to clean up failed deployments

## Testing Strategy

### Dual Testing Approach

The testing strategy employs both unit tests and property-based tests for comprehensive coverage:

- **Unit Tests**: Verify specific examples, edge cases, and error conditions
- **Property Tests**: Verify universal properties across all inputs

Both approaches are complementary and necessary for ensuring correctness.

### Unit Testing Focus

Unit tests should focus on:

1. **Specific Examples**: Concrete test cases that demonstrate correct behavior
   - Example: Test importing a specific YAML configuration file
   - Example: Test cost calculation for c5.xlarge with 12-month duration

2. **Edge Cases**: Boundary conditions and special scenarios
   - Empty configuration files
   - Maximum parameter values
   - Minimum parameter values
   - Special characters in strings

3. **Error Conditions**: Specific error scenarios
   - Invalid AWS credentials
   - Missing required parameters
   - Terraform state lock conflicts
   - Network timeouts

4. **Integration Points**: Component interactions
   - Session state updates after configuration import
   - AWS session creation from credentials
   - Terraform command execution flow

### Property-Based Testing Focus

Property tests should focus on:

1. **Universal Properties**: Rules that hold for all valid inputs
   - Configuration round-trip preservation
   - Parameter acceptance completeness
   - Validation correctness
   - Cost calculation consistency

2. **Invariants**: Properties that remain constant
   - Session state persistence across navigation
   - Progress monotonicity during deployment
   - Error message completeness

3. **Metamorphic Properties**: Relationships between operations
   - Export then import yields equivalent configuration
   - Multiple cost calculations with same inputs yield same results

### Property-Based Testing Configuration

- **Library**: Hypothesis for Python
- **Minimum Iterations**: 100 per property test
- **Test Tagging**: Each test must reference its design document property
- **Tag Format**: `# Feature: streamlit-web-app-enhancement, Property N: [property text]`

### Test Organization

```
tests/
├── unit/
│   ├── test_configuration_manager.py
│   ├── test_aws_integration.py
│   ├── test_terraform_integration.py
│   ├── test_cost_calculator.py
│   ├── test_session_state.py
│   └── test_ui_components.py
├── property/
│   ├── test_configuration_properties.py
│   ├── test_validation_properties.py
│   ├── test_deployment_properties.py
│   └── test_cost_properties.py
├── integration/
│   ├── test_deployment_workflow.py
│   ├── test_configuration_import_export.py
│   └── test_aws_validation_flow.py
└── fixtures/
    ├── sample_configs/
    ├── mock_aws_responses/
    └── terraform_outputs/
```

### Example Property Test

```python
from hypothesis import given, strategies as st
import hypothesis

# Feature: streamlit-web-app-enhancement, Property 1: Configuration Round-Trip Preservation
@given(deployment_config=deployment_config_strategy())
@hypothesis.settings(max_examples=100)
def test_yaml_configuration_round_trip(deployment_config):
    """
    For any valid DeploymentConfig, exporting to YAML then importing
    should produce an equivalent configuration (excluding sensitive fields)
    """
    config_manager = ConfigurationManager()
    
    # Export to YAML
    yaml_content = config_manager.export_yaml(deployment_config, redact_sensitive=False)
    
    # Import from YAML
    imported_config = config_manager.import_yaml(yaml_content)
    
    # Compare (excluding sensitive fields that might be redacted)
    assert configs_equivalent(deployment_config, imported_config, 
                             exclude_fields=['admin_password', 'ha_password', 
                                           'access_key_id', 'secret_access_key'])
```

### Example Unit Test

```python
def test_invalid_vpc_id_validation():
    """Test that invalid VPC ID format is rejected with clear error"""
    aws_manager = AWSIntegrationManager(test_aws_config)
    
    invalid_vpc_id = "invalid-vpc-id"
    is_valid, message = aws_manager.validate_vpc(invalid_vpc_id)
    
    assert not is_valid
    assert "invalid-vpc-id" in message
    assert "format" in message.lower()
```

### Mock Strategy

For testing without actual AWS resources:

1. **boto3 Mocking**: Use `moto` library for mocking AWS services
2. **Terraform Mocking**: Mock subprocess calls to Terraform
3. **File System Mocking**: Use temporary directories for file operations
4. **Session State Mocking**: Create isolated session state for each test

### Continuous Integration

- Run unit tests on every commit
- Run property tests on pull requests
- Run integration tests nightly
- Maintain minimum 80% code coverage
- Fail builds on any test failures

## Implementation Notes

### Phase 1: Core Infrastructure (Week 1)

1. Set up project structure and dependencies
2. Implement Session State Manager
3. Implement Configuration Manager with import/export
4. Create base UI layout and navigation

### Phase 2: AWS Integration (Week 2)

1. Implement AWS Integration Layer
2. Add resource validation functionality
3. Implement AMI Discovery integration
4. Add License Manager integration

### Phase 3: Configuration UI (Week 3)

1. Implement Configuration Page with all parameters
2. Add real-time validation
3. Implement AMI Discovery Page
4. Implement Licensing Page

### Phase 4: Deployment Integration (Week 4)

1. Implement Terraform Integration Layer
2. Add deployment orchestration
3. Implement Deployment Page with progress tracking
4. Add plan-only and destroy functionality

### Phase 5: Additional Features (Week 5)

1. Implement Cost Analysis Page
2. Add Monitoring Page
3. Implement Documentation Page
4. Add error handling and user feedback

### Phase 6: Testing and Polish (Week 6)

1. Write comprehensive unit tests
2. Write property-based tests
3. Perform integration testing
4. UI/UX refinements
5. Documentation updates

### Dependencies

**Python Packages**:
- `streamlit>=1.28.0`: Web application framework
- `boto3>=1.26.0`: AWS SDK
- `pyyaml>=6.0`: YAML parsing
- `plotly>=5.14.0`: Interactive charts
- `pandas>=2.0.0`: Data manipulation
- `hypothesis>=6.82.0`: Property-based testing
- `pytest>=7.4.0`: Testing framework
- `moto>=4.1.0`: AWS mocking for tests

**External Tools**:
- Terraform CLI (>=1.5.0)
- AWS CLI (for credential management)

### Deployment Considerations

1. **Streamlit Cloud**: Can be deployed to Streamlit Cloud for easy access
2. **Docker**: Containerize for consistent deployment
3. **AWS EC2**: Deploy on EC2 instance for private access
4. **Authentication**: Add authentication layer for production use
5. **Secrets Management**: Use environment variables for sensitive configuration

### Security Considerations

1. **Credential Handling**: Never log or display AWS credentials
2. **Session Isolation**: Ensure session state is isolated between users
3. **Input Validation**: Validate all user inputs before processing
4. **Terraform State**: Protect Terraform state files (use S3 with encryption)
5. **HTTPS**: Use HTTPS for production deployments
6. **Audit Logging**: Log all deployment operations for audit trail

### Performance Considerations

1. **Caching**: Cache AWS API responses to reduce latency
2. **Async Operations**: Use threading for long-running Terraform operations
3. **Lazy Loading**: Load heavy components only when needed
4. **Session State Size**: Minimize session state size to improve performance
5. **Output Streaming**: Stream Terraform output incrementally to avoid memory issues

## Conclusion

This design provides a comprehensive blueprint for enhancing the Streamlit web application to achieve complete feature parity with the deploy.py CLI script. By reusing existing infrastructure, implementing proper error handling, and following best practices for testing and security, the enhanced application will provide a robust, user-friendly interface for FortiGate HA deployments on AWS.

The modular architecture allows for incremental development and testing, while the property-based testing strategy ensures correctness across a wide range of inputs. The design prioritizes user experience with clear feedback, comprehensive error handling, and intuitive navigation.

