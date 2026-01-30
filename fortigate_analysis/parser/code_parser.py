"""
Code parser implementation for parsing Terraform and Python files.

This module provides comprehensive parsing capabilities for Terraform configurations
using python-hcl2 and Python scripts using the built-in AST module. It includes
robust error handling, parsing context tracking, and detailed extraction of
variables, resources, outputs, and modules.
"""

import ast
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
import chardet

try:
    import hcl2
except ImportError:
    hcl2 = None

from ..models import TerraformAST, Variable, Resource, Output, Module
from ..interfaces import CodeParserProtocol, BaseAnalyzer


logger = logging.getLogger(__name__)


class ParsingError(Exception):
    """Custom exception for parsing errors with context."""
    
    def __init__(self, message: str, file_path: str, line_number: Optional[int] = None, context: Optional[str] = None):
        self.file_path = file_path
        self.line_number = line_number
        self.context = context
        super().__init__(message)


class ParsingContext:
    """Tracks parsing context for better error reporting."""
    
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.current_block = None
        self.current_line = None
        self.errors = []
        self.warnings = []
    
    def add_error(self, message: str, line_number: Optional[int] = None):
        """Add an error to the parsing context."""
        error = {
            "message": message,
            "line_number": line_number or self.current_line,
            "block": self.current_block,
            "file_path": self.file_path
        }
        self.errors.append(error)
        logger.error(f"Parsing error in {self.file_path}: {message}")
    
    def add_warning(self, message: str, line_number: Optional[int] = None):
        """Add a warning to the parsing context."""
        warning = {
            "message": message,
            "line_number": line_number or self.current_line,
            "block": self.current_block,
            "file_path": self.file_path
        }
        self.warnings.append(warning)
        logger.warning(f"Parsing warning in {self.file_path}: {message}")


class CodeParser(BaseAnalyzer):
    """
    Parses Terraform configurations and Python scripts into analyzable structures.
    
    Uses HCL parser for Terraform files and Python AST for Python scripts,
    extracting variables, resources, outputs, and module references with
    comprehensive error handling and context tracking.
    """
    
    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        self.encoding_detection = config.get('encoding_detection', True) if config else True
        self.max_file_size = config.get('max_file_size', 10 * 1024 * 1024) if config else 10 * 1024 * 1024  # 10MB
        
        if hcl2 is None:
            logger.warning("python-hcl2 not available. Terraform parsing will be limited.")
    
    def analyze(self, file_path: Path) -> Dict[str, Any]:
        """Analyze a file and return parsed content."""
        try:
            if file_path.suffix == '.tf':
                ast_result = self.parse_terraform_file(file_path)
                return {
                    "ast": ast_result,
                    "variables": self.extract_variables(ast_result),
                    "resources": self.extract_resources(ast_result),
                    "outputs": self.extract_outputs(ast_result),
                    "modules": self.extract_modules(ast_result)
                }
            elif file_path.suffix == '.py':
                return self.parse_python_file(file_path)
            else:
                return {}
        except Exception as e:
            logger.error(f"Failed to analyze file {file_path}: {e}")
            return {"error": str(e)}
    
    def _detect_encoding(self, file_path: Path) -> str:
        """Detect file encoding using chardet."""
        if not self.encoding_detection:
            return 'utf-8'
        
        try:
            with open(file_path, 'rb') as f:
                raw_data = f.read(min(10000, self.max_file_size))  # Read first 10KB for detection
                result = chardet.detect(raw_data)
                encoding = result.get('encoding', 'utf-8')
                confidence = result.get('confidence', 0)
                
                if confidence < 0.7:
                    logger.warning(f"Low confidence ({confidence:.2f}) in encoding detection for {file_path}, using utf-8")
                    return 'utf-8'
                
                return encoding
        except Exception as e:
            logger.warning(f"Failed to detect encoding for {file_path}: {e}, using utf-8")
            return 'utf-8'
    
    def _read_file_safely(self, file_path: Path) -> str:
        """Safely read file with encoding detection and size limits."""
        # Check file size
        file_size = file_path.stat().st_size
        if file_size > self.max_file_size:
            raise ParsingError(
                f"File too large ({file_size} bytes, max {self.max_file_size})",
                str(file_path)
            )
        
        # Detect encoding
        encoding = self._detect_encoding(file_path)
        
        # Read file
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                return f.read()
        except UnicodeDecodeError as e:
            # Fallback to utf-8 with error handling
            logger.warning(f"Failed to read {file_path} with {encoding}, trying utf-8 with error handling")
            try:
                with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                    return f.read()
            except Exception as fallback_error:
                raise ParsingError(
                    f"Failed to read file with encoding {encoding} and utf-8 fallback: {fallback_error}",
                    str(file_path)
                ) from e
    
    def parse_terraform_file(self, file_path: Path) -> TerraformAST:
        """
        Parse a Terraform file and return AST.
        
        Args:
            file_path: Path to the Terraform file
            
        Returns:
            TerraformAST with parsed content
            
        Raises:
            ParsingError: If parsing fails with context information
        """
        if hcl2 is None:
            raise ParsingError(
                "python-hcl2 library not available. Install with: pip install python-hcl2",
                str(file_path)
            )
        
        context = ParsingContext(str(file_path))
        
        try:
            # Read file content
            content = self._read_file_safely(file_path)
            
            # Parse HCL content
            try:
                parsed_hcl = hcl2.loads(content)
            except Exception as e:
                context.add_error(f"HCL parsing failed: {e}")
                # Return empty AST with error information
                ast_result = TerraformAST()
                return ast_result
            
            # Extract components from parsed HCL
            variables = self._extract_variables_from_hcl(parsed_hcl, context)
            resources = self._extract_resources_from_hcl(parsed_hcl, context)
            outputs = self._extract_outputs_from_hcl(parsed_hcl, context)
            modules = self._extract_modules_from_hcl(parsed_hcl, context)
            providers = self._extract_providers_from_hcl(parsed_hcl, context)
            terraform_block = self._extract_terraform_block_from_hcl(parsed_hcl, context)
            
            # Create AST
            ast_result = TerraformAST(
                variables=variables,
                resources=resources,
                outputs=outputs,
                modules=modules,
                providers=providers,
                terraform_block=terraform_block
            )
            
            return ast_result
            
        except ParsingError:
            raise
        except Exception as e:
            raise ParsingError(
                f"Unexpected error parsing Terraform file: {e}",
                str(file_path)
            ) from e
    
    def _extract_variables_from_hcl(self, parsed_hcl: Dict, context: ParsingContext) -> List[Variable]:
        """Extract variable definitions from parsed HCL."""
        variables = []
        
        if 'variable' not in parsed_hcl:
            return variables
        
        context.current_block = "variable"
        
        variable_block = parsed_hcl['variable']
        
        # Handle case where variable block is a list (multiple variable blocks)
        if isinstance(variable_block, list):
            for var_block in variable_block:
                if isinstance(var_block, dict):
                    for var_name, var_configs in var_block.items():
                        try:
                            if isinstance(var_configs, list):
                                for var_config in var_configs:
                                    variables.append(self._create_variable_from_config(var_name, var_config, context))
                            else:
                                variables.append(self._create_variable_from_config(var_name, var_configs, context))
                        except Exception as e:
                            context.add_error(f"Failed to parse variable '{var_name}': {e}")
        else:
            # Handle case where variable block is a dict
            for var_name, var_configs in variable_block.items():
                try:
                    if isinstance(var_configs, list):
                        for var_config in var_configs:
                            variables.append(self._create_variable_from_config(var_name, var_config, context))
                    else:
                        variables.append(self._create_variable_from_config(var_name, var_configs, context))
                except Exception as e:
                    context.add_error(f"Failed to parse variable '{var_name}': {e}")
        
        return variables
    
    def _create_variable_from_config(self, name: str, config: Dict, context: ParsingContext) -> Variable:
        """Create Variable object from HCL configuration."""
        return Variable(
            name=name,
            type=config.get('type', 'any'),
            description=config.get('description'),
            default=config.get('default'),
            sensitive=config.get('sensitive', False),
            validation=config.get('validation')
        )
    
    def _extract_resources_from_hcl(self, parsed_hcl: Dict, context: ParsingContext) -> List[Resource]:
        """Extract resource definitions from parsed HCL."""
        resources = []
        
        if 'resource' not in parsed_hcl:
            return resources
        
        context.current_block = "resource"
        
        resource_block = parsed_hcl['resource']
        
        # Handle case where resource block is a list
        if isinstance(resource_block, list):
            for res_block in resource_block:
                if isinstance(res_block, dict):
                    for resource_type, resource_names in res_block.items():
                        self._process_resource_type(resource_type, resource_names, resources, context)
        else:
            # Handle case where resource block is a dict
            for resource_type, resource_names in resource_block.items():
                self._process_resource_type(resource_type, resource_names, resources, context)
        
        return resources
    
    def _process_resource_type(self, resource_type: str, resource_names: Any, resources: List[Resource], context: ParsingContext):
        """Process a specific resource type and its instances."""
        if isinstance(resource_names, dict):
            for resource_name, resource_configs in resource_names.items():
                try:
                    # Handle multiple resource definitions with same type/name
                    if isinstance(resource_configs, list):
                        for resource_config in resource_configs:
                            resources.append(self._create_resource_from_config(
                                resource_type, resource_name, resource_config, context
                            ))
                    else:
                        resources.append(self._create_resource_from_config(
                            resource_type, resource_name, resource_configs, context
                        ))
                except Exception as e:
                    context.add_error(f"Failed to parse resource '{resource_type}.{resource_name}': {e}")
        elif isinstance(resource_names, list):
            # Handle case where resource_names is a list
            for resource_name_block in resource_names:
                if isinstance(resource_name_block, dict):
                    for resource_name, resource_configs in resource_name_block.items():
                        try:
                            if isinstance(resource_configs, list):
                                for resource_config in resource_configs:
                                    resources.append(self._create_resource_from_config(
                                        resource_type, resource_name, resource_config, context
                                    ))
                            else:
                                resources.append(self._create_resource_from_config(
                                    resource_type, resource_name, resource_configs, context
                                ))
                        except Exception as e:
                            context.add_error(f"Failed to parse resource '{resource_type}.{resource_name}': {e}")
    
    def _create_resource_from_config(self, resource_type: str, name: str, config: Dict, context: ParsingContext) -> Resource:
        """Create Resource object from HCL configuration."""
        # Extract provider from resource type (e.g., "aws_instance" -> "aws")
        provider = resource_type.split('_')[0] if '_' in resource_type else 'unknown'
        
        # Extract dependencies from configuration
        dependencies = []
        self._extract_dependencies_from_config(config, dependencies)
        
        return Resource(
            type=resource_type,
            name=name,
            provider=provider,
            configuration=config,
            line_number=0,  # HCL2 doesn't provide line numbers easily
            dependencies=dependencies
        )
    
    def _extract_dependencies_from_config(self, config: Any, dependencies: List[str]) -> None:
        """Recursively extract dependencies from resource configuration."""
        if isinstance(config, dict):
            for key, value in config.items():
                self._extract_dependencies_from_value(value, dependencies)
        elif isinstance(config, list):
            for item in config:
                self._extract_dependencies_from_value(item, dependencies)
        else:
            self._extract_dependencies_from_value(config, dependencies)
    
    def _extract_dependencies_from_value(self, value: Any, dependencies: List[str]) -> None:
        """Extract dependencies from a configuration value."""
        if isinstance(value, str):
            # Look for various reference patterns
            if ('${' in value or 
                value.startswith('var.') or 
                value.startswith('data.') or 
                value.startswith('module.') or
                value.startswith('aws_') or
                value.startswith('azurerm_') or
                value.startswith('google_')):
                dependencies.append(value)
        elif isinstance(value, (dict, list)):
            self._extract_dependencies_from_config(value, dependencies)
    
    def _extract_outputs_from_hcl(self, parsed_hcl: Dict, context: ParsingContext) -> List[Output]:
        """Extract output definitions from parsed HCL."""
        outputs = []
        
        if 'output' not in parsed_hcl:
            return outputs
        
        context.current_block = "output"
        
        output_block = parsed_hcl['output']
        
        # Handle case where output block is a list
        if isinstance(output_block, list):
            for out_block in output_block:
                if isinstance(out_block, dict):
                    for output_name, output_configs in out_block.items():
                        try:
                            if isinstance(output_configs, list):
                                for output_config in output_configs:
                                    outputs.append(self._create_output_from_config(output_name, output_config, context))
                            else:
                                outputs.append(self._create_output_from_config(output_name, output_configs, context))
                        except Exception as e:
                            context.add_error(f"Failed to parse output '{output_name}': {e}")
        else:
            # Handle case where output block is a dict
            for output_name, output_configs in output_block.items():
                try:
                    if isinstance(output_configs, list):
                        for output_config in output_configs:
                            outputs.append(self._create_output_from_config(output_name, output_config, context))
                    else:
                        outputs.append(self._create_output_from_config(output_name, output_configs, context))
                except Exception as e:
                    context.add_error(f"Failed to parse output '{output_name}': {e}")
        
        return outputs
    
    def _create_output_from_config(self, name: str, config: Dict, context: ParsingContext) -> Output:
        """Create Output object from HCL configuration."""
        return Output(
            name=name,
            value=config.get('value'),
            description=config.get('description'),
            sensitive=config.get('sensitive', False)
        )
    
    def _extract_modules_from_hcl(self, parsed_hcl: Dict, context: ParsingContext) -> List[Module]:
        """Extract module definitions from parsed HCL."""
        modules = []
        
        if 'module' not in parsed_hcl:
            return modules
        
        context.current_block = "module"
        
        module_block = parsed_hcl['module']
        
        # Handle case where module block is a list
        if isinstance(module_block, list):
            for mod_block in module_block:
                if isinstance(mod_block, dict):
                    for module_name, module_configs in mod_block.items():
                        try:
                            if isinstance(module_configs, list):
                                for module_config in module_configs:
                                    modules.append(self._create_module_from_config(module_name, module_config, context))
                            else:
                                modules.append(self._create_module_from_config(module_name, module_configs, context))
                        except Exception as e:
                            context.add_error(f"Failed to parse module '{module_name}': {e}")
        else:
            # Handle case where module block is a dict
            for module_name, module_configs in module_block.items():
                try:
                    if isinstance(module_configs, list):
                        for module_config in module_configs:
                            modules.append(self._create_module_from_config(module_name, module_config, context))
                    else:
                        modules.append(self._create_module_from_config(module_name, module_configs, context))
                except Exception as e:
                    context.add_error(f"Failed to parse module '{module_name}': {e}")
        
        return modules
    
    def _create_module_from_config(self, name: str, config: Dict, context: ParsingContext) -> Module:
        """Create Module object from HCL configuration."""
        # Extract variables (all keys except source and version are variables)
        variables = {}
        dependencies = []
        
        for key, value in config.items():
            if key not in ['source', 'version']:
                variables[key] = value
                # Check if this variable references other resources
                if isinstance(value, str) and ('${' in value or value.startswith('var.') or value.startswith('data.') or value.startswith('module.')):
                    dependencies.append(value)
        
        return Module(
            name=name,
            source=config.get('source', ''),
            version=config.get('version'),
            variables=variables,
            dependencies=dependencies
        )
    
    def _extract_providers_from_hcl(self, parsed_hcl: Dict, context: ParsingContext) -> List[Dict[str, Any]]:
        """Extract provider configurations from parsed HCL."""
        providers = []
        
        if 'provider' not in parsed_hcl:
            return providers
        
        context.current_block = "provider"
        
        provider_block = parsed_hcl['provider']
        
        # Handle case where provider block is a list
        if isinstance(provider_block, list):
            for prov_block in provider_block:
                if isinstance(prov_block, dict):
                    for provider_name, provider_configs in prov_block.items():
                        try:
                            if isinstance(provider_configs, list):
                                for provider_config in provider_configs:
                                    providers.append({
                                        'name': provider_name,
                                        'config': provider_config
                                    })
                            else:
                                providers.append({
                                    'name': provider_name,
                                    'config': provider_configs
                                })
                        except Exception as e:
                            context.add_error(f"Failed to parse provider '{provider_name}': {e}")
        else:
            # Handle case where provider block is a dict
            for provider_name, provider_configs in provider_block.items():
                try:
                    if isinstance(provider_configs, list):
                        for provider_config in provider_configs:
                            providers.append({
                                'name': provider_name,
                                'config': provider_config
                            })
                    else:
                        providers.append({
                            'name': provider_name,
                            'config': provider_configs
                        })
                except Exception as e:
                    context.add_error(f"Failed to parse provider '{provider_name}': {e}")
        
        return providers
    
    def _extract_terraform_block_from_hcl(self, parsed_hcl: Dict, context: ParsingContext) -> Optional[Dict[str, Any]]:
        """Extract terraform block configuration from parsed HCL."""
        if 'terraform' not in parsed_hcl:
            return None
        
        context.current_block = "terraform"
        
        terraform_configs = parsed_hcl['terraform']
        if isinstance(terraform_configs, list):
            # Return the first terraform block if multiple exist
            return terraform_configs[0] if terraform_configs else None
        else:
            return terraform_configs
    
    def parse_python_file(self, file_path: Path) -> Dict[str, Any]:
        """
        Parse a Python file and extract comprehensive metadata.
        
        Enhanced to extract function definitions, imports, configuration patterns,
        and handle various Python script patterns commonly found in Terraform deployments.
        
        Args:
            file_path: Path to the Python file
            
        Returns:
            Dictionary with extracted metadata including functions, imports, classes,
            configuration patterns, constants, and error information
        """
        context = ParsingContext(str(file_path))
        
        try:
            # Read file content
            content = self._read_file_safely(file_path)
            
            # Parse Python AST
            try:
                tree = ast.parse(content, filename=str(file_path))
            except SyntaxError as e:
                context.add_error(f"Python syntax error: {e.msg} at line {e.lineno}, column {e.offset}", e.lineno)
                return {
                    "functions": [],
                    "imports": [],
                    "classes": [],
                    "constants": [],
                    "configuration_patterns": [],
                    "terraform_patterns": [],
                    "errors": context.errors,
                    "warnings": context.warnings
                }
            except Exception as e:
                context.add_error(f"Failed to parse Python AST: {e}")
                return {
                    "functions": [],
                    "imports": [],
                    "classes": [],
                    "constants": [],
                    "configuration_patterns": [],
                    "terraform_patterns": [],
                    "errors": context.errors,
                    "warnings": context.warnings
                }
            
            # Extract components with enhanced analysis
            functions = []
            imports = []
            classes = []
            constants = []
            configuration_patterns = []
            terraform_patterns = []
            
            # Walk through AST nodes for comprehensive extraction
            for node in ast.walk(tree):
                try:
                    if isinstance(node, ast.FunctionDef):
                        func_info = self._extract_function_info(node, context)
                        functions.append(func_info)
                        
                        # Check for Terraform-specific patterns in functions
                        terraform_func_patterns = self._detect_terraform_function_patterns(node, context)
                        terraform_patterns.extend(terraform_func_patterns)
                    
                    elif isinstance(node, ast.AsyncFunctionDef):
                        func_info = self._extract_async_function_info(node, context)
                        functions.append(func_info)
                    
                    elif isinstance(node, ast.ClassDef):
                        class_info = self._extract_class_info(node, context)
                        classes.append(class_info)
                        
                        # Check for configuration patterns in classes
                        config_patterns = self._detect_class_configuration_patterns(node, context)
                        configuration_patterns.extend(config_patterns)
                    
                    elif isinstance(node, (ast.Import, ast.ImportFrom)):
                        import_info = self._extract_import_info(node, context)
                        imports.extend(import_info)
                    
                    elif isinstance(node, ast.Assign):
                        # Extract constants and configuration assignments
                        constant_info = self._extract_constant_assignments(node, context)
                        if constant_info:
                            constants.extend(constant_info)
                        
                        # Check for configuration patterns in assignments
                        config_patterns = self._detect_assignment_configuration_patterns(node, context)
                        configuration_patterns.extend(config_patterns)
                
                except Exception as e:
                    context.add_warning(f"Failed to extract info from AST node {type(node).__name__}: {e}")
            
            # Detect additional patterns by analyzing the entire content
            additional_patterns = self._detect_content_patterns(content, context)
            terraform_patterns.extend(additional_patterns.get('terraform_patterns', []))
            configuration_patterns.extend(additional_patterns.get('configuration_patterns', []))
            
            return {
                "functions": functions,
                "imports": imports,
                "classes": classes,
                "constants": constants,
                "configuration_patterns": configuration_patterns,
                "terraform_patterns": terraform_patterns,
                "errors": context.errors,
                "warnings": context.warnings,
                "file_info": {
                    "total_lines": len(content.splitlines()),
                    "has_main_block": self._has_main_block(tree),
                    "has_terraform_imports": self._has_terraform_imports(imports),
                    "script_type": self._determine_script_type(content, imports, functions)
                }
            }
            
        except ParsingError:
            raise
        except Exception as e:
            raise ParsingError(
                f"Unexpected error parsing Python file: {e}",
                str(file_path)
            ) from e
    
    def extract_variables(self, ast: TerraformAST) -> List[Dict[str, Any]]:
        """Extract variables from Terraform AST."""
        return [
            {
                "name": var.name,
                "type": var.type,
                "description": var.description,
                "default": var.default,
                "sensitive": var.sensitive,
                "validation": var.validation
            }
            for var in ast.variables
        ]
    
    def extract_resources(self, ast: TerraformAST) -> List[Dict[str, Any]]:
        """Extract resources from Terraform AST."""
        return [
            {
                "type": resource.type,
                "name": resource.name,
                "provider": resource.provider,
                "configuration": resource.configuration,
                "line_number": resource.line_number,
                "dependencies": resource.dependencies
            }
            for resource in ast.resources
        ]
    
    def extract_outputs(self, ast: TerraformAST) -> List[Dict[str, Any]]:
        """Extract outputs from Terraform AST."""
        return [
            {
                "name": output.name,
                "value": output.value,
                "description": output.description,
                "sensitive": output.sensitive
            }
            for output in ast.outputs
        ]
    
    def extract_modules(self, ast: TerraformAST) -> List[Dict[str, Any]]:
        """Extract modules from Terraform AST."""
        return [
            {
                "name": module.name,
                "source": module.source,
                "version": module.version,
                "variables": module.variables,
                "dependencies": module.dependencies
            }
            for module in ast.modules
        ]
    
    def _extract_function_info(self, node: ast.FunctionDef, context: ParsingContext) -> Dict[str, Any]:
        """Extract comprehensive information from a function definition."""
        try:
            # Extract arguments with types and defaults
            args_info = []
            for i, arg in enumerate(node.args.args):
                arg_info = {
                    "name": arg.arg,
                    "annotation": ast.unparse(arg.annotation) if arg.annotation else None
                }
                # Add default value if available
                defaults_offset = len(node.args.args) - len(node.args.defaults)
                if i >= defaults_offset:
                    default_index = i - defaults_offset
                    arg_info["default"] = ast.unparse(node.args.defaults[default_index])
                args_info.append(arg_info)
            
            # Extract keyword-only arguments
            kwonly_args = []
            for i, arg in enumerate(node.args.kwonlyargs):
                kwarg_info = {
                    "name": arg.arg,
                    "annotation": ast.unparse(arg.annotation) if arg.annotation else None
                }
                if i < len(node.args.kw_defaults) and node.args.kw_defaults[i]:
                    kwarg_info["default"] = ast.unparse(node.args.kw_defaults[i])
                kwonly_args.append(kwarg_info)
            
            # Extract decorators with more detail
            decorators = []
            for decorator in node.decorator_list:
                try:
                    decorators.append({
                        "name": ast.unparse(decorator),
                        "type": self._classify_decorator(decorator)
                    })
                except Exception as e:
                    context.add_warning(f"Failed to parse decorator in function {node.name}: {e}")
                    decorators.append({"name": "unknown", "type": "unknown"})
            
            # Analyze function body for patterns
            body_analysis = self._analyze_function_body(node, context)
            
            return {
                "name": node.name,
                "line_number": node.lineno,
                "end_line_number": getattr(node, 'end_lineno', None),
                "args": args_info,
                "kwonly_args": kwonly_args,
                "vararg": node.args.vararg.arg if node.args.vararg else None,
                "kwarg": node.args.kwarg.arg if node.args.kwarg else None,
                "return_annotation": ast.unparse(node.returns) if node.returns else None,
                "decorators": decorators,
                "docstring": ast.get_docstring(node),
                "is_async": False,
                "complexity": body_analysis.get("complexity", 0),
                "calls_external": body_analysis.get("calls_external", []),
                "uses_terraform_patterns": body_analysis.get("uses_terraform_patterns", False),
                "configuration_operations": body_analysis.get("configuration_operations", [])
            }
        except Exception as e:
            context.add_error(f"Failed to extract function info for {node.name}: {e}", node.lineno)
            return {
                "name": node.name,
                "line_number": node.lineno,
                "args": [],
                "decorators": [],
                "docstring": None,
                "is_async": False,
                "error": str(e)
            }
    
    def _extract_async_function_info(self, node: ast.AsyncFunctionDef, context: ParsingContext) -> Dict[str, Any]:
        """Extract information from an async function definition."""
        # Reuse the regular function extraction but mark as async
        func_info = self._extract_function_info(node, context)
        func_info["is_async"] = True
        return func_info
    
    def _extract_class_info(self, node: ast.ClassDef, context: ParsingContext) -> Dict[str, Any]:
        """Extract comprehensive information from a class definition."""
        try:
            # Extract base classes
            bases = []
            for base in node.bases:
                try:
                    bases.append(ast.unparse(base))
                except Exception as e:
                    context.add_warning(f"Failed to parse base class in {node.name}: {e}")
                    bases.append("unknown")
            
            # Extract decorators
            decorators = []
            for decorator in node.decorator_list:
                try:
                    decorators.append({
                        "name": ast.unparse(decorator),
                        "type": self._classify_decorator(decorator)
                    })
                except Exception as e:
                    context.add_warning(f"Failed to parse decorator in class {node.name}: {e}")
                    decorators.append({"name": "unknown", "type": "unknown"})
            
            # Extract methods and attributes
            methods = []
            attributes = []
            
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    method_info = self._extract_function_info(item, context) if isinstance(item, ast.FunctionDef) else self._extract_async_function_info(item, context)
                    method_info["is_method"] = True
                    method_info["is_property"] = any(d["name"] == "property" for d in method_info.get("decorators", []))
                    method_info["is_classmethod"] = any(d["name"] == "classmethod" for d in method_info.get("decorators", []))
                    method_info["is_staticmethod"] = any(d["name"] == "staticmethod" for d in method_info.get("decorators", []))
                    methods.append(method_info)
                elif isinstance(item, ast.Assign):
                    # Extract class attributes
                    for target in item.targets:
                        if isinstance(target, ast.Name):
                            attributes.append({
                                "name": target.id,
                                "line_number": item.lineno,
                                "value": ast.unparse(item.value) if hasattr(ast, 'unparse') else "unknown",
                                "annotation": None
                            })
                elif isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                    # Extract annotated class attributes
                    attributes.append({
                        "name": item.target.id,
                        "line_number": item.lineno,
                        "value": ast.unparse(item.value) if item.value and hasattr(ast, 'unparse') else None,
                        "annotation": ast.unparse(item.annotation) if item.annotation else None
                    })
            
            return {
                "name": node.name,
                "line_number": node.lineno,
                "end_line_number": getattr(node, 'end_lineno', None),
                "bases": bases,
                "decorators": decorators,
                "docstring": ast.get_docstring(node),
                "methods": methods,
                "attributes": attributes,
                "is_configuration_class": self._is_configuration_class(node, methods, attributes),
                "is_terraform_related": self._is_terraform_related_class(node, methods, attributes)
            }
        except Exception as e:
            context.add_error(f"Failed to extract class info for {node.name}: {e}", node.lineno)
            return {
                "name": node.name,
                "line_number": node.lineno,
                "bases": [],
                "decorators": [],
                "docstring": None,
                "methods": [],
                "attributes": [],
                "error": str(e)
            }
    
    def _extract_import_info(self, node: Union[ast.Import, ast.ImportFrom], context: ParsingContext) -> List[Dict[str, Any]]:
        """Extract detailed import information."""
        imports = []
        
        try:
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append({
                        "module": alias.name,
                        "alias": alias.asname,
                        "line_number": node.lineno,
                        "type": "import",
                        "is_terraform_related": self._is_terraform_related_import(alias.name),
                        "is_cloud_provider": self._is_cloud_provider_import(alias.name),
                        "is_configuration": self._is_configuration_import(alias.name)
                    })
            else:  # ImportFrom
                module_name = node.module or ""
                for alias in node.names:
                    imports.append({
                        "module": module_name,
                        "name": alias.name,
                        "alias": alias.asname,
                        "line_number": node.lineno,
                        "type": "from_import",
                        "level": node.level,  # Relative import level
                        "is_terraform_related": self._is_terraform_related_import(module_name) or self._is_terraform_related_import(alias.name),
                        "is_cloud_provider": self._is_cloud_provider_import(module_name) or self._is_cloud_provider_import(alias.name),
                        "is_configuration": self._is_configuration_import(module_name) or self._is_configuration_import(alias.name)
                    })
        except Exception as e:
            context.add_warning(f"Failed to extract import info: {e}")
        
        return imports
    
    def _extract_constant_assignments(self, node: ast.Assign, context: ParsingContext) -> List[Dict[str, Any]]:
        """Extract constant assignments and configuration variables."""
        constants = []
        
        try:
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id.isupper():
                    # Likely a constant (all uppercase)
                    constants.append({
                        "name": target.id,
                        "line_number": node.lineno,
                        "value": ast.unparse(node.value) if hasattr(ast, 'unparse') else "unknown",
                        "type": self._infer_value_type(node.value),
                        "is_configuration": self._is_configuration_constant(target.id, node.value),
                        "is_terraform_related": self._is_terraform_related_constant(target.id, node.value)
                    })
        except Exception as e:
            context.add_warning(f"Failed to extract constant assignment: {e}")
        
        return constants
    
    def _classify_decorator(self, decorator: ast.expr) -> str:
        """Classify the type of decorator."""
        try:
            decorator_str = ast.unparse(decorator)
            
            if decorator_str in ["property", "staticmethod", "classmethod"]:
                return "builtin"
            elif decorator_str.startswith("@"):
                return "custom"
            elif "." in decorator_str:
                return "method_call"
            else:
                return "function"
        except:
            return "unknown"
    
    def _analyze_function_body(self, node: ast.FunctionDef, context: ParsingContext) -> Dict[str, Any]:
        """Analyze function body for complexity and patterns."""
        analysis = {
            "complexity": 0,
            "calls_external": [],
            "uses_terraform_patterns": False,
            "configuration_operations": []
        }
        
        try:
            for child in ast.walk(node):
                # Count complexity indicators
                if isinstance(child, (ast.If, ast.For, ast.While, ast.With, ast.Try)):
                    analysis["complexity"] += 1
                
                # Track external calls
                elif isinstance(child, ast.Call):
                    if isinstance(child.func, ast.Name):
                        analysis["calls_external"].append(child.func.id)
                    elif isinstance(child.func, ast.Attribute):
                        try:
                            call_str = ast.unparse(child.func) if hasattr(ast, 'unparse') else "unknown"
                            analysis["calls_external"].append(call_str)
                            
                            # Check for Terraform patterns
                            if any(pattern in call_str.lower() for pattern in ["terraform", "hcl", "tf_", "aws_", "azure_", "gcp_"]):
                                analysis["uses_terraform_patterns"] = True
                        except:
                            analysis["calls_external"].append("unknown")
                
                # Track configuration operations
                elif isinstance(child, ast.Assign):
                    for target in child.targets:
                        if isinstance(target, ast.Name) and any(keyword in target.id.lower() for keyword in ["config", "setting", "param", "option"]):
                            analysis["configuration_operations"].append({
                                "variable": target.id,
                                "line": child.lineno,
                                "operation": "assignment"
                            })
                        # Check for terraform-related assignments
                        elif isinstance(target, ast.Subscript):
                            try:
                                target_str = ast.unparse(target) if hasattr(ast, 'unparse') else str(target)
                                if any(pattern in target_str.lower() for pattern in ["terraform", "config", "provider", "aws", "azure", "gcp"]):
                                    analysis["uses_terraform_patterns"] = True
                                    analysis["configuration_operations"].append({
                                        "variable": target_str,
                                        "line": child.lineno,
                                        "operation": "subscript_assignment"
                                    })
                            except:
                                pass
                
                # Check string literals for terraform patterns
                elif isinstance(child, ast.Constant) and isinstance(child.value, str):
                    if any(pattern in child.value.lower() for pattern in ["terraform", "provider", "aws", "azure", "gcp", "region", "instance"]):
                        analysis["uses_terraform_patterns"] = True
            
            # Also check the function name and docstring for terraform patterns
            func_name_lower = node.name.lower()
            if any(pattern in func_name_lower for pattern in ["terraform", "aws", "azure", "gcp", "deploy", "provision", "configure"]):
                analysis["uses_terraform_patterns"] = True
            
            docstring = ast.get_docstring(node)
            if docstring and any(pattern in docstring.lower() for pattern in ["terraform", "aws", "azure", "gcp", "provider", "infrastructure", "deploy"]):
                analysis["uses_terraform_patterns"] = True
                
        except Exception as e:
            context.add_warning(f"Failed to analyze function body: {e}")
        
        return analysis
    
    def _is_configuration_class(self, node: ast.ClassDef, methods: List[Dict], attributes: List[Dict]) -> bool:
        """Determine if a class is likely a configuration class."""
        class_name_lower = node.name.lower()
        
        # Check class name patterns
        if any(pattern in class_name_lower for pattern in ["config", "setting", "param", "option", "terraform", "deployment"]):
            return True
        
        # Check for configuration-like attributes
        config_attributes = sum(1 for attr in attributes if any(pattern in attr["name"].lower() for pattern in ["config", "setting", "param", "option"]))
        if config_attributes > 2:
            return True
        
        # Check for configuration-like methods
        config_methods = sum(1 for method in methods if any(pattern in method["name"].lower() for pattern in ["configure", "setup", "init", "load", "save"]))
        if config_methods > 1:
            return True
        
        return False
    
    def _is_terraform_related_class(self, node: ast.ClassDef, methods: List[Dict], attributes: List[Dict]) -> bool:
        """Determine if a class is related to Terraform operations."""
        class_name_lower = node.name.lower()
        
        # Check class name patterns
        if any(pattern in class_name_lower for pattern in ["terraform", "tf_", "hcl", "aws", "azure", "gcp", "cloud", "provider"]):
            return True
        
        # Check docstring for Terraform references
        docstring = ast.get_docstring(node)
        if docstring and any(pattern in docstring.lower() for pattern in ["terraform", "hcl", "infrastructure", "cloud", "deployment"]):
            return True
        
        return False
    
    def _is_terraform_related_import(self, module_name: str) -> bool:
        """Check if an import is related to Terraform."""
        if not module_name:
            return False
        
        terraform_patterns = [
            "terraform", "hcl", "tf_", "boto3", "azure", "google.cloud", 
            "oci", "alibabacloud", "openstack", "pulumi", "cdktf"
        ]
        
        return any(pattern in module_name.lower() for pattern in terraform_patterns)
    
    def _is_cloud_provider_import(self, module_name: str) -> bool:
        """Check if an import is related to cloud providers."""
        if not module_name:
            return False
        
        cloud_patterns = [
            "boto3", "botocore", "aws", "azure", "google.cloud", "gcp", 
            "oci", "alibabacloud", "openstack", "ibm_cloud", "digitalocean"
        ]
        
        return any(pattern in module_name.lower() for pattern in cloud_patterns)
    
    def _is_configuration_import(self, module_name: str) -> bool:
        """Check if an import is related to configuration management."""
        if not module_name:
            return False
        
        config_patterns = [
            "configparser", "yaml", "json", "toml", "ini", "config", 
            "settings", "environ", "dotenv", "pydantic"
        ]
        
        return any(pattern in module_name.lower() for pattern in config_patterns)
    
    def _infer_value_type(self, node: ast.expr) -> str:
        """Infer the type of a value from AST node."""
        if isinstance(node, ast.Constant):
            return type(node.value).__name__
        elif isinstance(node, ast.List):
            return "list"
        elif isinstance(node, ast.Dict):
            return "dict"
        elif isinstance(node, ast.Tuple):
            return "tuple"
        elif isinstance(node, ast.Set):
            return "set"
        elif isinstance(node, ast.Name):
            return "variable"
        elif isinstance(node, ast.Call):
            return "function_call"
        else:
            return "unknown"
    
    def _is_configuration_constant(self, name: str, value_node: ast.expr) -> bool:
        """Check if a constant is likely a configuration value."""
        config_patterns = ["CONFIG", "SETTING", "PARAM", "OPTION", "DEFAULT", "TERRAFORM", "AWS", "AZURE", "GCP"]
        return any(pattern in name for pattern in config_patterns)
    
    def _is_terraform_related_constant(self, name: str, value_node: ast.expr) -> bool:
        """Check if a constant is related to Terraform."""
        terraform_patterns = ["TERRAFORM", "TF_", "HCL", "AWS", "AZURE", "GCP", "CLOUD", "PROVIDER", "REGION", "ZONE"]
        return any(pattern in name for pattern in terraform_patterns)
    
    def _detect_terraform_function_patterns(self, node: ast.FunctionDef, context: ParsingContext) -> List[Dict[str, Any]]:
        """Detect Terraform-specific patterns in function definitions."""
        patterns = []
        
        try:
            # Check function name patterns
            func_name_lower = node.name.lower()
            if any(pattern in func_name_lower for pattern in ["terraform", "tf_", "deploy", "provision", "configure", "setup_aws", "setup_azure", "setup_gcp"]):
                patterns.append({
                    "type": "terraform_function",
                    "pattern": "function_name",
                    "description": f"Function name '{node.name}' suggests Terraform operations",
                    "line_number": node.lineno,
                    "confidence": "high"
                })
            
            # Check function parameters for cloud/terraform patterns
            for arg in node.args.args:
                if any(pattern in arg.arg.lower() for pattern in ["region", "zone", "provider", "terraform", "aws", "azure", "gcp", "config"]):
                    patterns.append({
                        "type": "terraform_parameter",
                        "pattern": "parameter_name",
                        "description": f"Parameter '{arg.arg}' suggests cloud/terraform configuration",
                        "line_number": node.lineno,
                        "confidence": "medium"
                    })
            
            # Check docstring for Terraform references
            docstring = ast.get_docstring(node)
            if docstring:
                terraform_keywords = ["terraform", "hcl", "infrastructure", "cloud", "aws", "azure", "gcp", "deployment", "provision"]
                found_keywords = [kw for kw in terraform_keywords if kw in docstring.lower()]
                if found_keywords:
                    patterns.append({
                        "type": "terraform_docstring",
                        "pattern": "docstring_keywords",
                        "description": f"Docstring contains Terraform-related keywords: {', '.join(found_keywords)}",
                        "line_number": node.lineno,
                        "confidence": "medium"
                    })
        
        except Exception as e:
            context.add_warning(f"Failed to detect Terraform patterns in function {node.name}: {e}")
        
        return patterns
    
    def _detect_class_configuration_patterns(self, node: ast.ClassDef, context: ParsingContext) -> List[Dict[str, Any]]:
        """Detect configuration patterns in class definitions."""
        patterns = []
        
        try:
            # Check if class follows configuration patterns
            if self._is_configuration_class(node, [], []):
                patterns.append({
                    "type": "configuration_class",
                    "pattern": "class_structure",
                    "description": f"Class '{node.name}' appears to be a configuration class",
                    "line_number": node.lineno,
                    "confidence": "high"
                })
            
            # Check for dataclass or pydantic patterns in decorators
            for decorator in node.decorator_list:
                try:
                    decorator_str = ast.unparse(decorator) if hasattr(ast, 'unparse') else str(decorator)
                    if any(pattern in decorator_str.lower() for pattern in ["dataclass", "pydantic", "basemodel", "config"]):
                        patterns.append({
                            "type": "structured_configuration",
                            "pattern": "decorator",
                            "description": f"Class uses configuration decorator: {decorator_str}",
                            "line_number": node.lineno,
                            "confidence": "high"
                        })
                except Exception as e:
                    context.add_warning(f"Failed to parse decorator in class {node.name}: {e}")
            
            # Check for configuration patterns in base classes
            for base in node.bases:
                try:
                    base_str = ast.unparse(base) if hasattr(ast, 'unparse') else str(base)
                    if any(pattern in base_str.lower() for pattern in ["basemodel", "config", "settings", "pydantic"]):
                        patterns.append({
                            "type": "structured_configuration",
                            "pattern": "base_class",
                            "description": f"Class inherits from configuration base class: {base_str}",
                            "line_number": node.lineno,
                            "confidence": "high"
                        })
                except Exception as e:
                    context.add_warning(f"Failed to parse base class in class {node.name}: {e}")
        
        except Exception as e:
            context.add_warning(f"Failed to detect configuration patterns in class {node.name}: {e}")
        
        return patterns
    
    def _detect_assignment_configuration_patterns(self, node: ast.Assign, context: ParsingContext) -> List[Dict[str, Any]]:
        """Detect configuration patterns in assignments."""
        patterns = []
        
        try:
            for target in node.targets:
                if isinstance(target, ast.Name):
                    var_name = target.id
                    
                    # First check for dictionary configurations (higher priority)
                    if isinstance(node.value, ast.Dict) and len(node.value.keys) >= 2:
                        # Check if dictionary keys suggest configuration
                        dict_keys = []
                        for key in node.value.keys:
                            if isinstance(key, ast.Constant) and isinstance(key.value, str):
                                dict_keys.append(key.value.lower())
                        
                        config_key_patterns = ["terraform", "aws", "azure", "gcp", "config", "setting", "provider", "region", "version"]
                        if any(pattern in ' '.join(dict_keys) for pattern in config_key_patterns):
                            patterns.append({
                                "type": "configuration_dict",
                                "pattern": "dictionary_config",
                                "description": f"Variable '{var_name}' is assigned a configuration dictionary with {len(node.value.keys)} keys",
                                "line_number": node.lineno,
                                "confidence": "high"
                            })
                        else:
                            # Large dictionary but no obvious config keys - still might be config
                            patterns.append({
                                "type": "configuration_dict",
                                "pattern": "dictionary_config",
                                "description": f"Variable '{var_name}' is assigned a large dictionary with {len(node.value.keys)} keys",
                                "line_number": node.lineno,
                                "confidence": "medium"
                            })
                    
                    # Then check for configuration variable patterns
                    elif any(pattern in var_name.lower() for pattern in ["config", "setting", "param", "terraform", "aws", "azure", "gcp"]):
                        value_type = self._infer_value_type(node.value)
                        patterns.append({
                            "type": "configuration_variable",
                            "pattern": "variable_assignment",
                            "description": f"Variable '{var_name}' appears to be a configuration variable ({value_type})",
                            "line_number": node.lineno,
                            "confidence": "medium"
                        })
        
        except Exception as e:
            context.add_warning(f"Failed to detect assignment configuration patterns: {e}")
        
        return patterns
    
    def _detect_content_patterns(self, content: str, context: ParsingContext) -> Dict[str, List[Dict[str, Any]]]:
        """Detect patterns by analyzing the entire file content."""
        patterns = {
            "terraform_patterns": [],
            "configuration_patterns": []
        }
        
        try:
            lines = content.splitlines()
            
            for i, line in enumerate(lines, 1):
                line_lower = line.lower().strip()
                
                # Skip empty lines but process comments for terraform commands
                if not line_lower:
                    continue
                
                # Check for Terraform CLI commands in comments or strings
                if any(pattern in line_lower for pattern in ["terraform init", "terraform plan", "terraform apply", "terraform destroy"]):
                    patterns["terraform_patterns"].append({
                        "type": "terraform_command",
                        "pattern": "cli_command",
                        "description": f"Line contains Terraform CLI command reference",
                        "line_number": i,
                        "confidence": "high"
                    })
                
                # Check for HCL/Terraform syntax patterns (skip comments for this check)
                if not line_lower.startswith('#') and any(pattern in line_lower for pattern in ["resource \"", "variable \"", "output \"", "module \"", "provider \""]):
                    patterns["terraform_patterns"].append({
                        "type": "hcl_syntax",
                        "pattern": "hcl_block",
                        "description": f"Line contains HCL block syntax",
                        "line_number": i,
                        "confidence": "high"
                    })
                
                # Check for cloud provider resource patterns (skip comments for this check)
                if not line_lower.startswith('#'):
                    cloud_resources = ["aws_", "azurerm_", "google_", "oci_", "alicloud_", "openstack_"]
                    for resource_prefix in cloud_resources:
                        if resource_prefix in line_lower:
                            patterns["terraform_patterns"].append({
                                "type": "cloud_resource",
                                "pattern": "resource_reference",
                                "description": f"Line references cloud provider resource: {resource_prefix}",
                                "line_number": i,
                                "confidence": "medium"
                            })
                            break
                
                # Check for configuration file patterns
                if any(pattern in line_lower for pattern in [".tfvars", ".tf", "terraform.rc", ".terraformrc"]):
                    patterns["configuration_patterns"].append({
                        "type": "terraform_file_reference",
                        "pattern": "file_reference",
                        "description": f"Line references Terraform configuration file",
                        "line_number": i,
                        "confidence": "high"
                    })
        
        except Exception as e:
            context.add_warning(f"Failed to detect content patterns: {e}")
        
        return patterns
    
    def _has_main_block(self, tree: ast.AST) -> bool:
        """Check if the script has a main block."""
        for node in ast.walk(tree):
            if (isinstance(node, ast.If) and 
                isinstance(node.test, ast.Compare) and
                isinstance(node.test.left, ast.Name) and
                node.test.left.id == "__name__" and
                any(isinstance(comp, ast.Eq) for comp in node.test.ops) and
                any(isinstance(comp, ast.Constant) and comp.value == "__main__" for comp in node.test.comparators)):
                return True
        return False
    
    def _has_terraform_imports(self, imports: List[Dict[str, Any]]) -> bool:
        """Check if the script has Terraform-related imports."""
        return any(imp.get("is_terraform_related", False) for imp in imports)
    
    def _determine_script_type(self, content: str, imports: List[Dict[str, Any]], functions: List[Dict[str, Any]]) -> str:
        """Determine the type/purpose of the Python script."""
        content_lower = content.lower()
        
        # Check for specific script types
        if any(pattern in content_lower for pattern in ["#!/usr/bin/env python", "if __name__ == \"__main__\""]):
            if self._has_terraform_imports(imports):
                return "terraform_automation_script"
            elif any(pattern in content_lower for pattern in ["deploy", "provision", "configure"]):
                return "deployment_script"
            else:
                return "executable_script"
        
        # Check for module types
        elif any(imp.get("is_terraform_related", False) for imp in imports):
            return "terraform_module"
        elif any(imp.get("is_cloud_provider", False) for imp in imports):
            return "cloud_provider_module"
        elif any(imp.get("is_configuration", False) for imp in imports):
            return "configuration_module"
        elif len(functions) > 3:
            return "utility_module"
        else:
            return "general_module"