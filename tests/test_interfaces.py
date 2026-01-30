"""
Unit tests for the core interfaces and protocols.
"""

import pytest
from pathlib import Path
from typing import List, Dict, Any

from fortigate_analysis.interfaces import (
    BaseAnalyzer,
    BaseGenerator,
    RepositoryScannerProtocol,
    CodeParserProtocol,
)
from fortigate_analysis.models import RepositoryInventory, TerraformAST


class TestBaseAnalyzer:
    """Test cases for BaseAnalyzer abstract base class."""
    
    def test_base_analyzer_initialization(self):
        """Test BaseAnalyzer initialization with config."""
        
        class ConcreteAnalyzer(BaseAnalyzer):
            def analyze(self, *args, **kwargs):
                return "analyzed"
        
        analyzer = ConcreteAnalyzer({"setting": "value"})
        assert analyzer.config == {"setting": "value"}
        assert analyzer.validate_input() is True
    
    def test_base_analyzer_error_handling(self):
        """Test BaseAnalyzer error handling."""
        
        class ConcreteAnalyzer(BaseAnalyzer):
            def analyze(self, *args, **kwargs):
                return "analyzed"
        
        analyzer = ConcreteAnalyzer()
        # Should not raise exception
        analyzer.handle_error(ValueError("test error"), "test context")


class TestBaseGenerator:
    """Test cases for BaseGenerator abstract base class."""
    
    def test_base_generator_initialization(self):
        """Test BaseGenerator initialization with config."""
        
        class ConcreteGenerator(BaseGenerator):
            def generate(self, *args, **kwargs):
                return "generated"
        
        generator = ConcreteGenerator({"setting": "value"})
        assert generator.config == {"setting": "value"}
        assert generator.validate_input() is True
    
    def test_base_generator_error_handling(self):
        """Test BaseGenerator error handling."""
        
        class ConcreteGenerator(BaseGenerator):
            def generate(self, *args, **kwargs):
                return "generated"
        
        generator = ConcreteGenerator()
        # Should not raise exception
        generator.handle_error(ValueError("test error"), "test context")


class TestProtocolCompliance:
    """Test cases for protocol compliance."""
    
    def test_repository_scanner_protocol_compliance(self):
        """Test that a class can implement RepositoryScannerProtocol."""
        
        class MockScanner:
            def scan_repository(self, repo_path: Path) -> RepositoryInventory:
                return RepositoryInventory()
            
            def get_terraform_files(self) -> List:
                return []
            
            def get_python_files(self) -> List:
                return []
            
            def get_documentation_files(self) -> List:
                return []
            
            def get_cloud_provider_configs(self) -> Dict[str, List]:
                return {}
        
        scanner = MockScanner()
        
        # Test protocol compliance
        def use_scanner(s: RepositoryScannerProtocol):
            return s.scan_repository(Path("."))
        
        result = use_scanner(scanner)
        assert isinstance(result, RepositoryInventory)
    
    def test_code_parser_protocol_compliance(self):
        """Test that a class can implement CodeParserProtocol."""
        
        class MockParser:
            def parse_terraform_file(self, file_path: Path) -> TerraformAST:
                return TerraformAST()
            
            def parse_python_file(self, file_path: Path) -> Dict[str, Any]:
                return {}
            
            def extract_variables(self, ast: TerraformAST) -> List[Dict[str, Any]]:
                return []
            
            def extract_resources(self, ast: TerraformAST) -> List[Dict[str, Any]]:
                return []
            
            def extract_modules(self, ast: TerraformAST) -> List[Dict[str, Any]]:
                return []
        
        parser = MockParser()
        
        # Test protocol compliance
        def use_parser(p: CodeParserProtocol):
            return p.parse_terraform_file(Path("test.tf"))
        
        result = use_parser(parser)
        assert isinstance(result, TerraformAST)