# FortiGate Terraform Analysis System

A comprehensive codebase analysis tool designed to examine, understand, and improve FortiGate Terraform deployment repositories. The system combines multiple analysis techniques including static code analysis, security scanning, best practices validation, and architectural assessment to provide actionable insights and improvement recommendations.

## Features

- **Comprehensive Repository Analysis**: Scans and catalogs all Terraform configurations, Python scripts, and documentation files
- **Multi-Cloud Support**: Analyzes configurations across AWS, Azure, GCP, IBM, OCI, AliCloud, and OpenStack
- **Security Analysis**: Identifies security vulnerabilities, hardcoded secrets, and misconfigurations
- **Best Practices Validation**: Checks adherence to Terraform and cloud provider best practices
- **Architecture Mapping**: Maps system architecture, dependencies, and deployment patterns
- **Gap Detection**: Identifies missing functionality and configuration inconsistencies
- **Actionable Tasks**: Generates prioritized improvement tasks with detailed implementation steps
- **Multiple Report Formats**: Exports results in JSON, HTML, Markdown, and CSV formats

## Architecture

The system follows a modular architecture with distinct components:

```
fortigate_analysis/
├── models.py              # Core data models and structures
├── interfaces.py          # Abstract interfaces and protocols
├── scanner/               # Repository scanning components
├── parser/                # Code parsing components
├── analyzer/              # Analysis components
│   ├── security_analyzer.py
│   ├── best_practices_validator.py
│   ├── architecture_mapper.py
│   ├── gap_detector.py
│   └── analysis_engine.py
├── reporter/              # Report generation components
└── cli.py                 # Command-line interface
```

## Installation

### Prerequisites

- Python 3.8 or higher
- pip package manager

### Install from Source

```bash
# Clone the repository
git clone <repository-url>
cd fortigate-terraform-analysis

# Install in development mode
pip install -e ".[dev]"

# Set up pre-commit hooks
make pre-commit
```

### Install Dependencies

```bash
# Install core dependencies
pip install -r requirements.txt

# Or install with development dependencies
make install-dev
```

## Usage

### Command Line Interface

The system provides a comprehensive CLI for analysis operations:

```bash
# Analyze a FortiGate Terraform repository
fortigate-analysis analyze /path/to/repository

# Generate reports in multiple formats
fortigate-analysis analyze /path/to/repository --format json --format html

# Specify output directory
fortigate-analysis analyze /path/to/repository --output ./reports

# Use custom configuration
fortigate-analysis analyze /path/to/repository --config ./config.yaml

# List improvement tasks
fortigate-analysis tasks ./reports/analysis.json --priority HIGH

# Generate specific report format
fortigate-analysis report ./reports/analysis.json --format html
```

### Programmatic Usage

```python
from pathlib import Path
from fortigate_analysis import AnalysisEngine
from fortigate_analysis.scanner import RepositoryScanner
from fortigate_analysis.analyzer import SecurityAnalyzer

# Create analysis engine
engine = AnalysisEngine()

# Configure components
engine.set_scanner(RepositoryScanner())
engine.set_security_analyzer(SecurityAnalyzer())

# Perform analysis
report = engine.analyze_repository(Path("/path/to/repository"))

# Access results
print(f"Found {len(report.security_issues)} security issues")
print(f"Generated {len(report.improvement_tasks)} improvement tasks")
```

## Configuration

The system supports configuration files for customizing analysis behavior:

```yaml
# config.yaml
security:
  check_secrets: true
  check_encryption: true
  check_access_controls: true
  external_tools:
    - tfsec
    - checkov

best_practices:
  check_naming: true
  check_documentation: true
  check_module_structure: true
  naming_patterns:
    resource: "^[a-z][a-z0-9_]*$"
    variable: "^[a-z][a-z0-9_]*$"

output:
  formats: ["json", "html"]
  include_metrics: true
  detailed_recommendations: true
```

## Development

### Setting Up Development Environment

```bash
# Set up development environment
make dev-setup

# Run all tests
make test

# Run specific test types
make test-unit
make test-property
make test-integration

# Code quality checks
make lint
make type-check
make format

# Run all checks
make check
```

### Testing

The system uses a comprehensive testing strategy:

- **Unit Tests**: Test individual components and functions
- **Property-Based Tests**: Use Hypothesis to validate universal properties
- **Integration Tests**: Test end-to-end workflows

```bash
# Run all tests with coverage
pytest --cov=fortigate_analysis

# Run property-based tests with statistics
pytest -m property --hypothesis-show-statistics

# Run tests with specific markers
pytest -m "unit and not slow"
```

### Code Quality

The project maintains high code quality standards:

- **Black**: Code formatting
- **isort**: Import sorting
- **flake8**: Linting
- **mypy**: Type checking
- **pre-commit**: Git hooks for quality checks

## Core Components

### Models

Core data structures representing Terraform files, security issues, analysis reports, and improvement tasks.

### Scanner

Discovers and catalogs repository contents, categorizing files by cloud provider and deployment scenario.

### Parser

Parses Terraform configurations and Python scripts, extracting AST representations and metadata.

### Analyzers

- **SecurityAnalyzer**: Identifies vulnerabilities and misconfigurations
- **BestPracticesValidator**: Validates adherence to best practices
- **ArchitectureMapper**: Maps system architecture and relationships
- **GapDetector**: Identifies missing functionality and inconsistencies

### Reporters

- **ReportGenerator**: Creates comprehensive analysis reports
- **TaskGenerator**: Generates actionable improvement tasks

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Run the test suite and quality checks
6. Submit a pull request

### Development Workflow

```bash
# Create feature branch
git checkout -b feature/new-analyzer

# Make changes and add tests
# ...

# Run quality checks
make check

# Commit changes
git commit -m "Add new analyzer component"

# Push and create pull request
git push origin feature/new-analyzer
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For questions, issues, or contributions, please:

1. Check the documentation
2. Search existing issues
3. Create a new issue with detailed information
4. Follow the contributing guidelines

## Roadmap

- [ ] Enhanced security rule engine
- [ ] Integration with external security tools
- [ ] Web-based dashboard
- [ ] CI/CD pipeline integration
- [ ] Plugin system for custom analyzers
- [ ] Machine learning-based pattern detection