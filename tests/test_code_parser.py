"""
Unit tests for the CodeParser class.

Tests cover HCL parsing, Python parsing, error handling, and edge cases.
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, mock_open

from fortigate_analysis.parser.code_parser import CodeParser, ParsingError, ParsingContext
from fortigate_analysis.models import TerraformAST, Variable, Resource, Output, Module


class TestParsingContext:
    """Test the ParsingContext class."""
    
    def test_parsing_context_initialization(self):
        """Test ParsingContext initialization."""
        context = ParsingContext("/test/file.tf")
        assert context.file_path == "/test/file.tf"
        assert context.current_block is None
        assert context.current_line is None
        assert context.errors == []
        assert context.warnings == []
    
    def test_add_error(self):
        """Test adding errors to parsing context."""
        context = ParsingContext("/test/file.tf")
        context.add_error("Test error", 10)
        
        assert len(context.errors) == 1
        error = context.errors[0]
        assert error["message"] == "Test error"
        assert error["line_number"] == 10
        assert error["file_path"] == "/test/file.tf"
    
    def test_add_warning(self):
        """Test adding warnings to parsing context."""
        context = ParsingContext("/test/file.tf")
        context.add_warning("Test warning", 5)
        
        assert len(context.warnings) == 1
        warning = context.warnings[0]
        assert warning["message"] == "Test warning"
        assert warning["line_number"] == 5
        assert warning["file_path"] == "/test/file.tf"


class TestCodeParser:
    """Test the CodeParser class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.parser = CodeParser()
    
    def test_initialization(self):
        """Test CodeParser initialization."""
        parser = CodeParser()
        assert parser.encoding_detection is True
        assert parser.max_file_size == 10 * 1024 * 1024
        
        # Test with custom config
        config = {"encoding_detection": False, "max_file_size": 1024}
        parser = CodeParser(config)
        assert parser.encoding_detection is False
        assert parser.max_file_size == 1024
    
    def test_detect_encoding(self):
        """Test encoding detection."""
        with tempfile.NamedTemporaryFile(mode='wb', delete=False) as f:
            f.write("test content".encode('utf-8'))
            temp_path = Path(f.name)
        
        try:
            encoding = self.parser._detect_encoding(temp_path)
            assert encoding in ['utf-8', 'ascii']  # Both are valid for simple text
        finally:
            temp_path.unlink()
    
    def test_read_file_safely_success(self):
        """Test successful file reading."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, encoding='utf-8') as f:
            f.write("test content")
            temp_path = Path(f.name)
        
        try:
            content = self.parser._read_file_safely(temp_path)
            assert content == "test content"
        finally:
            temp_path.unlink()
    
    def test_read_file_safely_large_file(self):
        """Test file size limit enforcement."""
        parser = CodeParser({"max_file_size": 10})  # Very small limit
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, encoding='utf-8') as f:
            f.write("a" * 20)  # Larger than limit
            temp_path = Path(f.name)
        
        try:
            with pytest.raises(ParsingError) as exc_info:
                parser._read_file_safely(temp_path)
            assert "File too large" in str(exc_info.value)
        finally:
            temp_path.unlink()
    
    @patch('fortigate_analysis.parser.code_parser.hcl2')
    def test_parse_terraform_file_success(self, mock_hcl2):
        """Test successful Terraform file parsing."""
        # Mock HCL2 parsing
        mock_hcl2.loads.return_value = {
            'variable': {
                'test_var': {
                    'type': 'string',
                    'description': 'Test variable',
                    'default': 'test_value'
                }
            },
            'resource': {
                'aws_instance': {
                    'test_instance': {
                        'ami': 'ami-12345',
                        'instance_type': 't2.micro'
                    }
                }
            },
            'output': {
                'test_output': {
                    'value': '${aws_instance.test_instance.id}',
                    'description': 'Test output'
                }
            },
            'module': {
                'test_module': {
                    'source': './modules/test',
                    'version': '1.0.0',
                    'var1': 'value1'
                }
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.tf', delete=False) as f:
            f.write("# Test terraform file")
            temp_path = Path(f.name)
        
        try:
            ast = self.parser.parse_terraform_file(temp_path)
            
            assert isinstance(ast, TerraformAST)
            assert len(ast.variables) == 1
            assert ast.variables[0].name == 'test_var'
            assert ast.variables[0].type == 'string'
            
            assert len(ast.resources) == 1
            assert ast.resources[0].type == 'aws_instance'
            assert ast.resources[0].name == 'test_instance'
            assert ast.resources[0].provider == 'aws'
            
            assert len(ast.outputs) == 1
            assert ast.outputs[0].name == 'test_output'
            
            assert len(ast.modules) == 1
            assert ast.modules[0].name == 'test_module'
            assert ast.modules[0].source == './modules/test'
            
        finally:
            temp_path.unlink()
    
    @patch('fortigate_analysis.parser.code_parser.hcl2', None)
    def test_parse_terraform_file_no_hcl2(self):
        """Test Terraform parsing when HCL2 is not available."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.tf', delete=False) as f:
            f.write("# Test terraform file")
            temp_path = Path(f.name)
        
        try:
            with pytest.raises(ParsingError) as exc_info:
                self.parser.parse_terraform_file(temp_path)
            assert "python-hcl2 library not available" in str(exc_info.value)
        finally:
            temp_path.unlink()
    
    @patch('fortigate_analysis.parser.code_parser.hcl2')
    def test_parse_terraform_file_syntax_error(self, mock_hcl2):
        """Test Terraform parsing with syntax errors."""
        mock_hcl2.loads.side_effect = Exception("Invalid HCL syntax")
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.tf', delete=False) as f:
            f.write("invalid hcl content")
            temp_path = Path(f.name)
        
        try:
            ast = self.parser.parse_terraform_file(temp_path)
            # Should return empty AST instead of raising exception
            assert isinstance(ast, TerraformAST)
            assert len(ast.variables) == 0
            assert len(ast.resources) == 0
        finally:
            temp_path.unlink()
    
    def test_parse_python_file_success(self):
        """Test successful Python file parsing with enhanced capabilities."""
        python_content = '''
import os
from pathlib import Path
import boto3
from terraform import Terraform

# Configuration constants
TERRAFORM_CONFIG = {
    "region": "us-west-2",
    "instance_type": "t2.micro"
}

AWS_REGIONS = ["us-west-2", "us-east-1"]

class TerraformDeployment:
    """Manages Terraform deployments for AWS infrastructure."""
    
    def __init__(self, config_path: str):
        self.config_path = config_path
        self.terraform_config = {}
    
    @property
    def is_configured(self) -> bool:
        return bool(self.terraform_config)
    
    def configure_aws_provider(self, region: str = "us-west-2"):
        """Configure AWS provider for Terraform."""
        self.terraform_config["provider"] = {
            "aws": {"region": region}
        }
    
    async def deploy_infrastructure(self, plan_file: str):
        """Deploy infrastructure using Terraform plan."""
        # terraform apply logic here
        pass

def setup_terraform_environment(terraform_dir: str, aws_region: str):
    """Set up Terraform environment for deployment."""
    # Setup logic here
    return True

@staticmethod
def validate_terraform_config(config: dict) -> bool:
    """Validate Terraform configuration."""
    return "provider" in config

if __name__ == "__main__":
    # terraform init
    # terraform plan
    # terraform apply
    deployment = TerraformDeployment("./terraform")
    deployment.configure_aws_provider("us-west-2")
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(python_content)
            temp_path = Path(f.name)
        
        try:
            result = self.parser.parse_python_file(temp_path)
            
            # Check basic structure
            assert 'functions' in result
            assert 'imports' in result
            assert 'classes' in result
            assert 'constants' in result
            assert 'configuration_patterns' in result
            assert 'terraform_patterns' in result
            assert 'file_info' in result
            
            # Check enhanced function information
            functions = result['functions']
            assert len(functions) >= 4  # __init__, configure_aws_provider, deploy_infrastructure, setup_terraform_environment, validate_terraform_config
            
            # Find specific functions and check enhanced info
            configure_func = next((f for f in functions if f['name'] == 'configure_aws_provider'), None)
            assert configure_func is not None
            assert configure_func['uses_terraform_patterns'] is True
            assert len(configure_func['args']) >= 1  # self parameter
            
            deploy_func = next((f for f in functions if f['name'] == 'deploy_infrastructure'), None)
            assert deploy_func is not None
            assert deploy_func['is_async'] is True
            
            # Check enhanced import information
            imports = result['imports']
            assert len(imports) >= 4
            
            # Check for Terraform-related imports
            terraform_imports = [imp for imp in imports if imp.get('is_terraform_related', False)]
            assert len(terraform_imports) >= 2  # boto3 and terraform
            
            # Check for cloud provider imports
            cloud_imports = [imp for imp in imports if imp.get('is_cloud_provider', False)]
            assert len(cloud_imports) >= 1  # boto3
            
            # Check enhanced class information
            classes = result['classes']
            assert len(classes) == 1
            terraform_class = classes[0]
            assert terraform_class['name'] == 'TerraformDeployment'
            assert terraform_class['is_terraform_related'] is True
            assert terraform_class['is_configuration_class'] is True
            assert len(terraform_class['methods']) >= 3
            
            # Check constants
            constants = result['constants']
            assert len(constants) >= 2
            terraform_config_const = next((c for c in constants if c['name'] == 'TERRAFORM_CONFIG'), None)
            assert terraform_config_const is not None
            assert terraform_config_const['is_configuration'] is True
            assert terraform_config_const['type'] == 'dict'
            
            # Check configuration patterns
            config_patterns = result['configuration_patterns']
            assert len(config_patterns) > 0
            
            # Check Terraform patterns
            terraform_patterns = result['terraform_patterns']
            assert len(terraform_patterns) > 0
            
            # Check file info
            file_info = result['file_info']
            assert file_info['has_main_block'] is True
            assert file_info['has_terraform_imports'] is True
            assert file_info['script_type'] == 'terraform_automation_script'
            
        finally:
            temp_path.unlink()
    
    def test_parse_python_file_syntax_error(self):
        """Test Python parsing with syntax errors."""
        python_content = '''
def invalid_function(
    # Missing closing parenthesis and colon
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(python_content)
            temp_path = Path(f.name)
        
        try:
            result = self.parser.parse_python_file(temp_path)
            
            assert 'errors' in result
            assert len(result['errors']) > 0
            assert 'Python syntax error' in result['errors'][0]['message']
            
            # Should still return empty lists for other components
            assert result['functions'] == []
            assert result['imports'] == []
            assert result['classes'] == []
            assert result['constants'] == []
            assert result['configuration_patterns'] == []
            assert result['terraform_patterns'] == []
            
        finally:
            temp_path.unlink()
    
    def test_parse_python_terraform_patterns(self):
        """Test detection of Terraform-specific patterns in Python files."""
        python_content = '''
import terraform
from boto3 import client

def terraform_deploy(region="us-west-2"):
    """Deploy infrastructure using Terraform."""
    # terraform init
    # terraform plan -out=plan.tfplan
    # terraform apply plan.tfplan
    pass

def setup_aws_resources(aws_config):
    """Setup AWS resources for deployment."""
    pass

class TerraformConfig:
    """Configuration class for Terraform deployments."""
    
    def __init__(self):
        self.provider_config = {}
        self.terraform_vars = {}
    
    def load_tfvars(self, tfvars_file):
        """Load variables from .tfvars file."""
        pass

# Configuration constants
TERRAFORM_WORKSPACE = "production"
AWS_REGION = "us-west-2"
PROVIDER_CONFIGS = {
    "aws": {"region": "us-west-2"},
    "azurerm": {"location": "West US 2"}
}
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(python_content)
            temp_path = Path(f.name)
        
        try:
            result = self.parser.parse_python_file(temp_path)
            
            # Check Terraform patterns
            terraform_patterns = result['terraform_patterns']
            assert len(terraform_patterns) > 0
            
            # Should detect terraform command references
            command_patterns = [p for p in terraform_patterns if p['type'] == 'terraform_command']
            assert len(command_patterns) > 0
            
            # Should detect terraform function patterns
            function_patterns = [p for p in terraform_patterns if p['type'] == 'terraform_function']
            assert len(function_patterns) > 0
            
            # Check configuration patterns
            config_patterns = result['configuration_patterns']
            assert len(config_patterns) > 0
            
            # Should detect configuration class
            class_patterns = [p for p in config_patterns if p['type'] == 'configuration_class']
            assert len(class_patterns) > 0
            
            # Check enhanced imports
            imports = result['imports']
            terraform_imports = [imp for imp in imports if imp.get('is_terraform_related', False)]
            assert len(terraform_imports) >= 2  # terraform and boto3
            
            # Check constants
            constants = result['constants']
            terraform_constants = [c for c in constants if c.get('is_terraform_related', False)]
            assert len(terraform_constants) >= 2  # TERRAFORM_WORKSPACE, AWS_REGION
            
            config_constants = [c for c in constants if c.get('is_configuration', False)]
            assert len(config_constants) >= 1  # PROVIDER_CONFIGS
            
        finally:
            temp_path.unlink()
    
    def test_parse_python_configuration_patterns(self):
        """Test detection of configuration patterns in Python files."""
        python_content = '''
from dataclasses import dataclass
from pydantic import BaseModel
import yaml
import configparser

@dataclass
class DeploymentConfig:
    """Configuration for deployment."""
    region: str
    instance_type: str
    key_name: str

class SettingsModel(BaseModel):
    """Pydantic model for settings."""
    terraform_version: str = "1.0.0"
    aws_profile: str = "default"

def load_configuration(config_file: str):
    """Load configuration from file."""
    with open(config_file) as f:
        return yaml.safe_load(f)

def setup_environment_config():
    """Setup environment configuration."""
    config = configparser.ConfigParser()
    config.read('deployment.ini')
    return config

# Configuration variables
deployment_settings = {
    "terraform": {
        "version": "1.0.0",
        "workspace": "production"
    },
    "aws": {
        "region": "us-west-2",
        "profile": "default"
    }
}

CONFIG_FILE_PATH = "/etc/deployment/config.yaml"
TERRAFORM_STATE_BUCKET = "my-terraform-state"
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(python_content)
            temp_path = Path(f.name)
        
        try:
            result = self.parser.parse_python_file(temp_path)
            
            # Check classes
            classes = result['classes']
            config_classes = [c for c in classes if c.get('is_configuration_class', False)]
            assert len(config_classes) >= 2  # DeploymentConfig, SettingsModel
            
            # Check for structured configuration patterns
            config_patterns = result['configuration_patterns']
            structured_patterns = [p for p in config_patterns if p['type'] == 'structured_configuration']
            assert len(structured_patterns) >= 2  # dataclass and BaseModel decorators
            
            # Check configuration imports
            imports = result['imports']
            config_imports = [imp for imp in imports if imp.get('is_configuration', False)]
            assert len(config_imports) >= 3  # yaml, configparser, and others
            
            # Check configuration variables
            dict_patterns = [p for p in config_patterns if p['type'] == 'configuration_dict']
            assert len(dict_patterns) >= 1  # deployment_settings
            
            # Check constants
            constants = result['constants']
            config_constants = [c for c in constants if c.get('is_configuration', False)]
            assert len(config_constants) >= 2  # CONFIG_FILE_PATH, TERRAFORM_STATE_BUCKET
            
        finally:
            temp_path.unlink()
    
    def test_parse_python_async_functions(self):
        """Test parsing of async functions."""
        python_content = '''
import asyncio
import aiohttp

async def deploy_async(config):
    """Async deployment function."""
    async with aiohttp.ClientSession() as session:
        await session.post('/deploy', json=config)

async def provision_resources():
    """Provision cloud resources asynchronously."""
    await asyncio.sleep(1)
    return True

def sync_function():
    """Regular synchronous function."""
    return "sync"
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(python_content)
            temp_path = Path(f.name)
        
        try:
            result = self.parser.parse_python_file(temp_path)
            
            functions = result['functions']
            assert len(functions) == 3
            
            # Check async functions
            async_functions = [f for f in functions if f.get('is_async', False)]
            assert len(async_functions) == 2
            
            deploy_func = next((f for f in functions if f['name'] == 'deploy_async'), None)
            assert deploy_func is not None
            assert deploy_func['is_async'] is True
            
            sync_func = next((f for f in functions if f['name'] == 'sync_function'), None)
            assert sync_func is not None
            assert sync_func['is_async'] is False
            
        finally:
            temp_path.unlink()
    
    def test_parse_python_complex_functions(self):
        """Test parsing of complex functions with detailed analysis."""
        python_content = '''
from typing import Dict, List, Optional
import boto3

def complex_terraform_function(
    region: str,
    instance_type: str = "t2.micro",
    *args,
    **kwargs
) -> Dict[str, str]:
    """
    Complex function with type annotations and various parameters.
    
    Args:
        region: AWS region
        instance_type: EC2 instance type
        *args: Additional arguments
        **kwargs: Additional keyword arguments
    
    Returns:
        Dictionary with deployment results
    """
    # Complex logic with multiple branches
    if region.startswith("us-"):
        config = {"provider": "aws"}
        if instance_type == "t2.micro":
            config["tier"] = "free"
        else:
            config["tier"] = "paid"
    else:
        config = {"provider": "unknown"}
    
    # Loop for additional complexity
    for arg in args:
        if isinstance(arg, str):
            config[f"arg_{len(config)}"] = arg
    
    # External calls
    ec2 = boto3.client('ec2', region_name=region)
    instances = ec2.describe_instances()
    
    try:
        # Error handling
        result = process_instances(instances)
    except Exception as e:
        result = {"error": str(e)}
    
    return result

@property
def terraform_version(self) -> str:
    """Property decorator example."""
    return "1.0.0"

@staticmethod
def validate_config(config: dict) -> bool:
    """Static method example."""
    return bool(config)

@classmethod
def from_config(cls, config: dict):
    """Class method example."""
    return cls(**config)
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(python_content)
            temp_path = Path(f.name)
        
        try:
            result = self.parser.parse_python_file(temp_path)
            
            functions = result['functions']
            assert len(functions) == 4
            
            # Find the complex function
            complex_func = next((f for f in functions if f['name'] == 'complex_terraform_function'), None)
            assert complex_func is not None
            
            # Check detailed argument information
            args = complex_func['args']
            assert len(args) >= 2
            
            # Check for region argument
            region_arg = next((arg for arg in args if arg['name'] == 'region'), None)
            assert region_arg is not None
            assert region_arg['annotation'] == 'str'
            
            # Check for instance_type argument with default
            instance_type_arg = next((arg for arg in args if arg['name'] == 'instance_type'), None)
            assert instance_type_arg is not None
            assert instance_type_arg['annotation'] == 'str'
            assert 't2.micro' in instance_type_arg.get('default', '')
            
            # Check vararg and kwarg
            assert complex_func['vararg'] == 'args'
            assert complex_func['kwarg'] == 'kwargs'
            
            # Check return annotation
            assert complex_func['return_annotation'] == 'Dict[str, str]'
            
            # Check complexity analysis
            assert complex_func['complexity'] > 0  # Should detect if/else, for loop, try/except
            
            # Check external calls
            external_calls = complex_func['calls_external']
            assert len(external_calls) > 0
            assert any('boto3' in call or 'ec2' in call for call in external_calls)
            
            # Check Terraform patterns
            assert complex_func['uses_terraform_patterns'] is True
            
            # Check decorators on other functions
            property_func = next((f for f in functions if f['name'] == 'terraform_version'), None)
            assert property_func is not None
            assert len(property_func['decorators']) == 1
            assert property_func['decorators'][0]['name'] == 'property'
            
        finally:
            temp_path.unlink()
    
    def test_analyze_terraform_file(self):
        """Test analyze method with Terraform file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.tf', delete=False) as f:
            f.write("# Test terraform file")
            temp_path = Path(f.name)
        
        try:
            with patch.object(self.parser, 'parse_terraform_file') as mock_parse:
                mock_ast = TerraformAST()
                mock_parse.return_value = mock_ast
                
                result = self.parser.analyze(temp_path)
                
                assert 'ast' in result
                assert 'variables' in result
                assert 'resources' in result
                assert 'outputs' in result
                assert 'modules' in result
                
        finally:
            temp_path.unlink()
    
    def test_analyze_python_file(self):
        """Test analyze method with Python file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("# Test python file")
            temp_path = Path(f.name)
        
        try:
            with patch.object(self.parser, 'parse_python_file') as mock_parse:
                mock_result = {"functions": [], "imports": [], "classes": []}
                mock_parse.return_value = mock_result
                
                result = self.parser.analyze(temp_path)
                
                assert result == mock_result
                
        finally:
            temp_path.unlink()
    
    def test_analyze_unsupported_file(self):
        """Test analyze method with unsupported file type."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Test text file")
            temp_path = Path(f.name)
        
        try:
            result = self.parser.analyze(temp_path)
            assert result == {}
        finally:
            temp_path.unlink()
    
    def test_extract_variables(self):
        """Test variable extraction from AST."""
        variables = [
            Variable(name="var1", type="string", description="Test var 1"),
            Variable(name="var2", type="number", default=42)
        ]
        ast = TerraformAST(variables=variables)
        
        result = self.parser.extract_variables(ast)
        
        assert len(result) == 2
        assert result[0]["name"] == "var1"
        assert result[0]["type"] == "string"
        assert result[1]["name"] == "var2"
        assert result[1]["default"] == 42
    
    def test_extract_resources(self):
        """Test resource extraction from AST."""
        resources = [
            Resource(
                type="aws_instance",
                name="test",
                provider="aws",
                configuration={"ami": "ami-12345"},
                line_number=10
            )
        ]
        ast = TerraformAST(resources=resources)
        
        result = self.parser.extract_resources(ast)
        
        assert len(result) == 1
        assert result[0]["type"] == "aws_instance"
        assert result[0]["name"] == "test"
        assert result[0]["provider"] == "aws"
        assert result[0]["line_number"] == 10
    
    def test_extract_outputs(self):
        """Test output extraction from AST."""
        outputs = [
            Output(name="output1", value="${aws_instance.test.id}", description="Test output")
        ]
        ast = TerraformAST(outputs=outputs)
        
        result = self.parser.extract_outputs(ast)
        
        assert len(result) == 1
        assert result[0]["name"] == "output1"
        assert result[0]["value"] == "${aws_instance.test.id}"
        assert result[0]["description"] == "Test output"
    
    def test_extract_modules(self):
        """Test module extraction from AST."""
        modules = [
            Module(
                name="test_module",
                source="./modules/test",
                version="1.0.0",
                variables={"var1": "value1"}
            )
        ]
        ast = TerraformAST(modules=modules)
        
        result = self.parser.extract_modules(ast)
        
        assert len(result) == 1
        assert result[0]["name"] == "test_module"
        assert result[0]["source"] == "./modules/test"
        assert result[0]["version"] == "1.0.0"
        assert result[0]["variables"] == {"var1": "value1"}
    
    def test_extract_dependencies_from_config(self):
        """Test dependency extraction from configuration."""
        config = {
            "ami": "ami-12345",
            "instance_type": "${var.instance_type}",
            "subnet_id": "${data.aws_subnet.main.id}",
            "security_groups": ["${aws_security_group.web.id}"],
            "tags": {
                "Name": "${module.naming.instance_name}"
            }
        }
        
        dependencies = []
        self.parser._extract_dependencies_from_config(config, dependencies)
        
        assert "${var.instance_type}" in dependencies
        assert "${data.aws_subnet.main.id}" in dependencies
        assert "${aws_security_group.web.id}" in dependencies
        assert "${module.naming.instance_name}" in dependencies
    
    @patch('fortigate_analysis.parser.code_parser.hcl2')
    def test_create_variable_from_config(self, mock_hcl2):
        """Test variable creation from HCL config."""
        context = ParsingContext("/test/file.tf")
        config = {
            "type": "string",
            "description": "Test variable",
            "default": "test_value",
            "sensitive": True
        }
        
        variable = self.parser._create_variable_from_config("test_var", config, context)
        
        assert variable.name == "test_var"
        assert variable.type == "string"
        assert variable.description == "Test variable"
        assert variable.default == "test_value"
        assert variable.sensitive is True
    
    @patch('fortigate_analysis.parser.code_parser.hcl2')
    def test_create_resource_from_config(self, mock_hcl2):
        """Test resource creation from HCL config."""
        context = ParsingContext("/test/file.tf")
        config = {
            "ami": "ami-12345",
            "instance_type": "${var.instance_type}"
        }
        
        resource = self.parser._create_resource_from_config("aws_instance", "test", config, context)
        
        assert resource.type == "aws_instance"
        assert resource.name == "test"
        assert resource.provider == "aws"
        assert resource.configuration == config
        assert "${var.instance_type}" in resource.dependencies


class TestParsingError:
    """Test the ParsingError exception."""
    
    def test_parsing_error_creation(self):
        """Test ParsingError creation with context."""
        error = ParsingError("Test error", "/test/file.tf", 10, "test context")
        
        assert str(error) == "Test error"
        assert error.file_path == "/test/file.tf"
        assert error.line_number == 10
        assert error.context == "test context"
    
    def test_parsing_error_minimal(self):
        """Test ParsingError creation with minimal parameters."""
        error = ParsingError("Test error", "/test/file.tf")
        
        assert str(error) == "Test error"
        assert error.file_path == "/test/file.tf"
        assert error.line_number is None
        assert error.context is None