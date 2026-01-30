"""
Architecture mapper implementation for mapping system architecture and relationships.

This module provides comprehensive architecture mapping capabilities for Terraform
configurations, including entry point identification, dependency graph construction,
deployment scenario categorization, and data flow analysis.
"""

import logging
import re
from pathlib import Path
from typing import List, Dict, Any, Set, Tuple, Optional
from collections import defaultdict, deque

from ..models import (
    TerraformFile, 
    ArchitectureMap, 
    ArchitectureComponent,
    Module,
    Resource,
    DeploymentScenario
)
from ..interfaces import ArchitectureMapperProtocol, BaseAnalyzer

logger = logging.getLogger(__name__)


class ArchitectureMapper(BaseAnalyzer):
    """
    Maps system architecture and component relationships.
    
    Identifies entry points, maps dependencies, categorizes deployments,
    and documents common patterns across the codebase. Provides comprehensive
    analysis of Terraform module structure and data flow.
    """
    
    # Patterns for identifying entry points
    ENTRY_POINT_PATTERNS = {
        'main_files': ['main.tf', 'root.tf', 'terraform.tf'],
        'root_indicators': ['terraform', 'provider', 'backend'],
        'directory_patterns': ['root', 'main', 'deploy', 'infrastructure'],
        'exclude_patterns': ['modules/', 'examples/', 'test/', 'tests/']
    }
    
    # Patterns for deployment scenario categorization
    DEPLOYMENT_SCENARIO_PATTERNS = {
        'single_instance': {
            'patterns': ['single', 'standalone', 'basic', 'simple'],
            'resource_indicators': ['count = 1', 'single_instance'],
            'architecture_type': 'single'
        },
        'high_availability': {
            'patterns': ['ha', 'high-availability', 'cluster', 'active-passive', 'active-active'],
            'resource_indicators': ['count = 2', 'availability_zone', 'multi_az'],
            'architecture_type': 'ha'
        },
        'load_balancer': {
            'patterns': ['lb', 'load-balancer', 'elb', 'alb', 'nlb'],
            'resource_indicators': ['load_balancer', 'target_group', 'listener'],
            'architecture_type': 'load_balancer'
        },
        'gateway_load_balancer': {
            'patterns': ['gwlb', 'gateway-load-balancer', 'transparent-proxy'],
            'resource_indicators': ['gateway_load_balancer', 'gwlb'],
            'architecture_type': 'gwlb'
        },
        'transit_gateway': {
            'patterns': ['tgw', 'transit-gateway', 'hub-and-spoke'],
            'resource_indicators': ['transit_gateway', 'tgw', 'route_table'],
            'architecture_type': 'transit_gateway'
        }
    }
    
    # Common patterns for reusable components
    COMMON_PATTERNS = {
        'networking': ['vpc', 'subnet', 'route_table', 'internet_gateway', 'nat_gateway'],
        'security': ['security_group', 'network_acl', 'firewall', 'policy'],
        'compute': ['instance', 'virtual_machine', 'compute_instance'],
        'storage': ['volume', 'disk', 'storage_account', 'bucket'],
        'load_balancing': ['load_balancer', 'target_group', 'backend_pool'],
        'monitoring': ['cloudwatch', 'log_analytics', 'monitoring'],
        'identity': ['iam', 'identity', 'service_account', 'role']
    }
    
    # Terraform best practice patterns
    BEST_PRACTICE_PATTERNS = {
        'variable_usage': {
            'patterns': ['var.', 'variable'],
            'description': 'Proper use of variables for parameterization'
        },
        'output_usage': {
            'patterns': ['output', 'value ='],
            'description': 'Proper output definitions for module interfaces'
        },
        'data_sources': {
            'patterns': ['data "', 'data.'],
            'description': 'Use of data sources for external resource references'
        },
        'locals': {
            'patterns': ['locals {', 'local.'],
            'description': 'Use of local values for computed expressions'
        },
        'module_composition': {
            'patterns': ['module "', 'source ='],
            'description': 'Modular architecture with reusable components'
        }
    }
    
    # Anti-patterns to detect
    ANTI_PATTERNS = {
        'hardcoded_values': {
            'patterns': [r'\d+\.\d+\.\d+\.\d+', r'us-[a-z]+-\d+[a-z]?', r'ami-[a-f0-9]+', r'subnet-[a-f0-9]+'],
            'description': 'Hardcoded IP addresses, regions, or resource IDs',
            'severity': 'MEDIUM'
        },
        'missing_tags': {
            'patterns': ['resource "', 'tags = {}'],
            'description': 'Resources without proper tagging',
            'severity': 'LOW'
        },
        'overly_permissive_security': {
            'patterns': ['0.0.0.0/0', 'cidr_blocks = ["0.0.0.0/0"]', 'from_port = 0', 'to_port = 65535'],
            'description': 'Overly permissive security group rules',
            'severity': 'HIGH'
        },
        'single_az_deployment': {
            'patterns': ['availability_zone =', 'count = 1'],
            'description': 'Single availability zone deployment (potential SPOF)',
            'severity': 'MEDIUM'
        },
        'missing_versioning': {
            'patterns': ['source = "terraform-', 'source = "git::', '# Missing version constraint'],
            'description': 'Module sources without version pinning',
            'severity': 'LOW'
        }
    }
    
    # FortiGate-specific patterns
    FORTIGATE_PATTERNS = {
        'ha_configuration': {
            'patterns': ['fgcp', 'ha-mode', 'priority', 'unicast-peer'],
            'description': 'FortiGate High Availability configuration'
        },
        'security_policies': {
            'patterns': ['firewall policy', 'srcintf', 'dstintf', 'action accept'],
            'description': 'FortiGate security policy configuration'
        },
        'network_interfaces': {
            'patterns': ['config system interface', 'set ip', 'set allowaccess'],
            'description': 'FortiGate network interface configuration'
        },
        'routing_configuration': {
            'patterns': ['config router static', 'set gateway', 'set device'],
            'description': 'FortiGate routing configuration'
        },
        'vpn_configuration': {
            'patterns': ['config vpn ipsec', 'config vpn ssl', 'set peertype'],
            'description': 'FortiGate VPN configuration'
        }
    }
    
    def __init__(self, config: Dict = None):
        super().__init__(config)
        self.cycle_detection_enabled = config.get('cycle_detection', True) if config else True
        self.max_dependency_depth = config.get('max_dependency_depth', 10) if config else 10
        
    def analyze(self, terraform_files: List[TerraformFile]) -> ArchitectureMap:
        """Alias for map_architecture to match BaseAnalyzer interface."""
        return self.map_architecture(terraform_files)
    
    def map_architecture(self, terraform_files: List[TerraformFile]) -> ArchitectureMap:
        """
        Map system architecture and relationships.
        
        Performs comprehensive analysis including:
        - Entry point identification
        - Component extraction and classification
        - Dependency graph construction with cycle detection
        - Deployment scenario categorization
        - Common pattern identification
        - Data flow analysis
        
        Args:
            terraform_files: List of Terraform files to analyze
            
        Returns:
            ArchitectureMap with complete system structure and relationships
        """
        logger.info(f"Starting architecture mapping for {len(terraform_files)} Terraform files")
        
        try:
            # Extract all modules and resources from files
            all_modules = []
            all_resources = []
            
            for tf_file in terraform_files:
                if tf_file.modules:
                    all_modules.extend(tf_file.modules)
                if tf_file.resources:
                    all_resources.extend(tf_file.resources)
            
            # Identify entry points
            entry_points = self.identify_entry_points_from_files(terraform_files)
            
            # Create architecture components
            components = self._create_architecture_components(terraform_files, all_modules, all_resources)
            
            # Build dependency graph
            dependency_graph = self._build_dependency_graph(components, all_modules, all_resources)
            
            # Detect cycles in dependency graph
            if self.cycle_detection_enabled:
                cycles = self._detect_dependency_cycles(dependency_graph)
                if cycles:
                    logger.warning(f"Detected {len(cycles)} dependency cycles in architecture")
            
            # Categorize deployment scenarios
            deployment_scenarios = self._categorize_deployment_scenarios(terraform_files)
            
            # Extract cloud providers
            cloud_providers = list(set(tf_file.cloud_provider for tf_file in terraform_files if tf_file.cloud_provider != 'unknown'))
            
            # Identify common patterns
            common_patterns = self._identify_common_patterns(all_resources, terraform_files)
            
            # Create architecture map
            architecture_map = ArchitectureMap(
                components=components,
                entry_points=entry_points,
                dependency_graph=dependency_graph,
                deployment_scenarios=deployment_scenarios,
                cloud_providers=cloud_providers,
                common_patterns=common_patterns
            )
            
            # Generate pattern documentation
            architecture_map.pattern_documentation = self.generate_pattern_documentation(architecture_map)
            
            logger.info(f"Architecture mapping completed: {len(components)} components, "
                       f"{len(entry_points)} entry points, {len(deployment_scenarios)} scenarios, "
                       f"{len(common_patterns)} patterns identified")
            
            return architecture_map
            
        except Exception as e:
            logger.error(f"Error during architecture mapping: {e}")
            self.handle_error(e, "architecture mapping")
            # Return minimal architecture map on error
            return ArchitectureMap(
                components=[],
                entry_points=[],
                dependency_graph={},
                deployment_scenarios=[],
                cloud_providers=[],
                common_patterns=[]
            )
    
    def identify_entry_points_from_files(self, terraform_files: List[TerraformFile]) -> List[str]:
        """
        Identify main entry points and root modules from Terraform files.
        
        Entry points are identified based on:
        - File names (main.tf, root.tf, etc.)
        - Directory structure (root directories)
        - Content analysis (terraform blocks, providers)
        - Module references (files not referenced as modules)
        
        Args:
            terraform_files: List of Terraform files to analyze
            
        Returns:
            List of entry point file paths
        """
        entry_points = []
        
        try:
            # Track all module sources to identify non-referenced files
            referenced_modules = set()
            
            # First pass: collect all module references
            for tf_file in terraform_files:
                for module in tf_file.modules:
                    if module.source and not module.source.startswith(('http', 'git', 'registry')):
                        # Local module reference
                        referenced_modules.add(self._normalize_module_path(module.source))
            
            # Second pass: identify entry points
            for tf_file in terraform_files:
                file_path = tf_file.path
                is_entry_point = False
                
                # Check file name patterns
                file_name = Path(file_path).name.lower()
                if file_name in self.ENTRY_POINT_PATTERNS['main_files']:
                    is_entry_point = True
                    logger.debug(f"Entry point identified by filename: {file_path}")
                
                # Check directory patterns
                path_parts = Path(file_path).parts
                for part in path_parts:
                    if part.lower() in self.ENTRY_POINT_PATTERNS['directory_patterns']:
                        is_entry_point = True
                        logger.debug(f"Entry point identified by directory: {file_path}")
                        break
                
                # Exclude certain patterns
                for exclude_pattern in self.ENTRY_POINT_PATTERNS['exclude_patterns']:
                    if exclude_pattern in file_path:
                        is_entry_point = False
                        break
                
                # Check if file is not referenced as a module
                normalized_path = self._normalize_file_path(file_path)
                if normalized_path not in referenced_modules:
                    # Check if file has root-level indicators
                    if self._has_root_indicators(tf_file):
                        is_entry_point = True
                        logger.debug(f"Entry point identified by root indicators: {file_path}")
                
                if is_entry_point:
                    entry_points.append(file_path)
            
            # If no entry points found, use heuristics
            if not entry_points:
                entry_points = self._fallback_entry_point_detection(terraform_files)
            
            logger.info(f"Identified {len(entry_points)} entry points")
            return entry_points
            
        except Exception as e:
            logger.error(f"Error identifying entry points: {e}")
            self.handle_error(e, "entry point identification")
            return []
    
    def identify_entry_points(self, modules: List[Dict[str, Any]]) -> List[str]:
        """
        Legacy method for compatibility with interface.
        
        Args:
            modules: List of module dictionaries
            
        Returns:
            List of entry point names
        """
        # Convert modules to simplified format and identify entry points
        entry_points = []
        
        try:
            # Look for modules that are not referenced by others
            all_sources = set()
            for module in modules:
                if module.get('source'):
                    all_sources.add(module['source'])
            
            for module in modules:
                module_name = module.get('name', '')
                if module_name and module_name not in all_sources:
                    entry_points.append(module_name)
            
            return entry_points
            
        except Exception as e:
            logger.error(f"Error in legacy entry point identification: {e}")
            return []
    
    def map_dependencies(self, modules: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """
        Map module dependencies and data flow.
        
        Creates a dependency graph showing relationships between modules
        and performs cycle detection.
        
        Args:
            modules: List of module dictionaries
            
        Returns:
            Dictionary mapping module names to their dependencies
        """
        dependency_graph = {}
        
        try:
            for module in modules:
                module_name = module.get('name', '')
                if not module_name:
                    continue
                
                dependencies = []
                
                # Extract dependencies from module variables
                variables = module.get('variables', {})
                for var_name, var_value in variables.items():
                    if isinstance(var_value, str):
                        # Look for references to other modules
                        deps = self._extract_dependencies_from_value(var_value)
                        dependencies.extend(deps)
                
                # Add explicit dependencies
                explicit_deps = module.get('dependencies', [])
                dependencies.extend(explicit_deps)
                
                # Remove duplicates and self-references
                dependencies = list(set(dep for dep in dependencies if dep != module_name))
                
                dependency_graph[module_name] = dependencies
            
            # Detect cycles
            if self.cycle_detection_enabled:
                cycles = self._detect_dependency_cycles(dependency_graph)
                if cycles:
                    logger.warning(f"Detected dependency cycles: {cycles}")
            
            return dependency_graph
            
        except Exception as e:
            logger.error(f"Error mapping dependencies: {e}")
            self.handle_error(e, "dependency mapping")
            return {}
    
    def categorize_deployments(self, files: List[TerraformFile]) -> List[str]:
        """
        Categorize deployment scenarios based on file analysis.
        
        Args:
            files: List of Terraform files to analyze
            
        Returns:
            List of deployment scenario names
        """
        return self._categorize_deployment_scenarios(files)
    
    def _create_architecture_components(self, terraform_files: List[TerraformFile], 
                                      modules: List[Module], resources: List[Resource]) -> List[ArchitectureComponent]:
        """Create architecture components from Terraform files, modules, and resources."""
        components = []
        
        try:
            # Create components from modules
            for module in modules:
                component = ArchitectureComponent(
                    name=module.name,
                    type='module',
                    cloud_provider=self._infer_cloud_provider_from_module(module),
                    dependencies=module.dependencies.copy(),
                    dependents=[],  # Will be populated later
                    entry_point=False  # Will be determined later
                )
                components.append(component)
            
            # Create components from resources
            for resource in resources:
                component = ArchitectureComponent(
                    name=f"{resource.type}.{resource.name}",
                    type='resource',
                    cloud_provider=resource.provider,
                    dependencies=resource.dependencies.copy(),
                    dependents=[],  # Will be populated later
                    entry_point=False
                )
                components.append(component)
            
            # Create components from data sources (if any)
            for tf_file in terraform_files:
                if hasattr(tf_file, 'data_sources'):
                    for data_source in tf_file.data_sources:
                        component = ArchitectureComponent(
                            name=f"data.{data_source.get('type', 'unknown')}.{data_source.get('name', 'unknown')}",
                            type='data_source',
                            cloud_provider=self._infer_cloud_provider_from_name(data_source.get('type', '')),
                            dependencies=[],
                            dependents=[],
                            entry_point=False
                        )
                        components.append(component)
            
            # Populate dependents (reverse dependencies)
            self._populate_dependents(components)
            
            return components
            
        except Exception as e:
            logger.error(f"Error creating architecture components: {e}")
            return []
    
    def _build_dependency_graph(self, components: List[ArchitectureComponent], 
                               modules: List[Module], resources: List[Resource]) -> Dict[str, List[str]]:
        """Build comprehensive dependency graph from components."""
        dependency_graph = {}
        
        try:
            # Initialize graph with all components
            for component in components:
                dependency_graph[component.name] = component.dependencies.copy()
            
            # Add cross-references between modules and resources
            for module in modules:
                module_name = module.name
                if module_name in dependency_graph:
                    # Add dependencies based on module variables that reference resources
                    for var_name, var_value in module.variables.items():
                        if isinstance(var_value, str):
                            resource_refs = self._extract_resource_references(var_value)
                            dependency_graph[module_name].extend(resource_refs)
            
            # Clean up dependencies (remove duplicates, invalid references)
            for component_name in dependency_graph:
                deps = dependency_graph[component_name]
                # Remove duplicates and self-references
                clean_deps = list(set(dep for dep in deps if dep != component_name and dep))
                dependency_graph[component_name] = clean_deps
            
            return dependency_graph
            
        except Exception as e:
            logger.error(f"Error building dependency graph: {e}")
            return {}
    
    def _detect_dependency_cycles(self, dependency_graph: Dict[str, List[str]]) -> List[List[str]]:
        """
        Detect cycles in the dependency graph using DFS.
        
        Args:
            dependency_graph: Dictionary mapping components to their dependencies
            
        Returns:
            List of cycles, where each cycle is a list of component names
        """
        cycles = []
        visited = set()
        rec_stack = set()
        
        def dfs(node: str, path: List[str]) -> None:
            if node in rec_stack:
                # Found a cycle
                cycle_start = path.index(node)
                cycle = path[cycle_start:] + [node]
                cycles.append(cycle)
                return
            
            if node in visited:
                return
            
            visited.add(node)
            rec_stack.add(node)
            path.append(node)
            
            for neighbor in dependency_graph.get(node, []):
                if neighbor in dependency_graph:  # Only follow valid nodes
                    dfs(neighbor, path.copy())
            
            rec_stack.remove(node)
        
        try:
            for node in dependency_graph:
                if node not in visited:
                    dfs(node, [])
            
            return cycles
            
        except Exception as e:
            logger.error(f"Error detecting dependency cycles: {e}")
            return []
    
    def _categorize_deployment_scenarios(self, terraform_files: List[TerraformFile]) -> List[str]:
        """
        Categorize deployment scenarios based on comprehensive file analysis.
        
        Args:
            terraform_files: List of Terraform files to analyze
            
        Returns:
            List of deployment scenario names
        """
        scenarios = []
        
        try:
            for tf_file in terraform_files:
                file_scenarios = []
                
                # Check primary deployment type from file metadata
                if tf_file.deployment_type != 'unknown':
                    file_scenarios.append(tf_file.deployment_type)
                
                # Check additional deployment types if available
                if hasattr(tf_file, 'all_deployment_types'):
                    file_scenarios.extend(tf_file.all_deployment_types)
                
                # Analyze file content for deployment patterns
                content_scenarios = self._analyze_deployment_patterns_in_file(tf_file)
                file_scenarios.extend(content_scenarios)
                
                # Add unique scenarios
                for scenario in file_scenarios:
                    if scenario not in scenarios and scenario != 'unknown':
                        scenarios.append(scenario)
            
            # If no scenarios found, try to infer from resources
            if not scenarios:
                scenarios = self._infer_scenarios_from_resources(terraform_files)
            
            return scenarios
            
        except Exception as e:
            logger.error(f"Error categorizing deployment scenarios: {e}")
            return []
    
    def _identify_common_patterns(self, resources: List[Resource], terraform_files: List[TerraformFile]) -> List[str]:
        """
        Identify common patterns and reusable components.
        
        Args:
            resources: List of all resources
            terraform_files: List of Terraform files
            
        Returns:
            List of identified common patterns
        """
        patterns = []
        
        try:
            # Identify basic resource patterns
            basic_patterns = self._identify_basic_resource_patterns(resources)
            patterns.extend(basic_patterns)
            
            # Identify best practice patterns
            best_practice_patterns = self._identify_best_practice_patterns(terraform_files)
            patterns.extend(best_practice_patterns)
            
            # Identify anti-patterns
            anti_patterns = self._identify_anti_patterns(terraform_files)
            patterns.extend(anti_patterns)
            
            # Identify FortiGate-specific patterns
            fortigate_patterns = self._identify_fortigate_patterns(terraform_files)
            patterns.extend(fortigate_patterns)
            
            # Identify reusable components across cloud providers
            reusable_components = self._identify_reusable_components(terraform_files)
            patterns.extend(reusable_components)
            
            # Perform configuration similarity analysis
            similarity_clusters = self._analyze_configuration_similarity(terraform_files)
            patterns.extend(similarity_clusters)
            
            # Identify multi-cloud patterns
            multi_cloud_patterns = self._identify_multi_cloud_patterns(terraform_files)
            patterns.extend(multi_cloud_patterns)
            
            return patterns
            
        except Exception as e:
            logger.error(f"Error identifying common patterns: {e}")
            return []
    
    def _identify_basic_resource_patterns(self, resources: List[Resource]) -> List[str]:
        """Identify basic resource patterns from resource analysis."""
        patterns = []
        
        try:
            # Count resource types to identify common patterns
            resource_type_counts = defaultdict(int)
            for resource in resources:
                resource_type_counts[resource.type] += 1
            
            # Identify patterns based on resource frequency and combinations
            for pattern_name, pattern_resources in self.COMMON_PATTERNS.items():
                pattern_score = 0
                found_resources = []
                
                for pattern_resource in pattern_resources:
                    for resource_type, count in resource_type_counts.items():
                        if pattern_resource in resource_type.lower():
                            pattern_score += count
                            found_resources.append(resource_type)
                
                # If pattern has significant presence, add it
                if pattern_score >= 2:  # Threshold for pattern significance
                    pattern_description = f"{pattern_name} (found: {', '.join(set(found_resources))})"
                    patterns.append(pattern_description)
            
            return patterns
            
        except Exception as e:
            logger.error(f"Error identifying basic resource patterns: {e}")
            return []
    
    def _identify_best_practice_patterns(self, terraform_files: List[TerraformFile]) -> List[str]:
        """Identify Terraform best practice patterns."""
        patterns = []
        
        try:
            for pattern_name, pattern_config in self.BEST_PRACTICE_PATTERNS.items():
                pattern_found = False
                file_count = 0
                
                for tf_file in terraform_files:
                    if hasattr(tf_file, '_content') and tf_file._content:
                        content_lower = tf_file._content.lower()
                        
                        for pattern in pattern_config['patterns']:
                            if pattern.lower() in content_lower:
                                pattern_found = True
                                file_count += 1
                                break
                
                if pattern_found:
                    description = pattern_config['description']
                    patterns.append(f"best_practice_{pattern_name} ({description}, found in {file_count} files)")
            
            return patterns
            
        except Exception as e:
            logger.error(f"Error identifying best practice patterns: {e}")
            return []
    
    def _identify_anti_patterns(self, terraform_files: List[TerraformFile]) -> List[str]:
        """Identify Terraform anti-patterns that should be avoided."""
        patterns = []
        
        try:
            for pattern_name, pattern_config in self.ANTI_PATTERNS.items():
                issues_found = []
                
                for tf_file in terraform_files:
                    if hasattr(tf_file, '_content') and tf_file._content:
                        content = tf_file._content
                        
                        for pattern in pattern_config['patterns']:
                            # Check if pattern looks like a regex (contains regex metacharacters)
                            if any(char in pattern for char in [r'\d', r'\w', r'\s', '[', ']', '+', '*', '?', '^', '$']):
                                # Treat as regex pattern
                                try:
                                    if re.search(pattern, content):
                                        issues_found.append(tf_file.path)
                                        break  # Found one match, no need to check other patterns for this file
                                except re.error as e:
                                    logger.warning(f"Invalid regex pattern {pattern}: {e}")
                            else:
                                # Simple string pattern
                                if pattern.lower() in content.lower():
                                    issues_found.append(tf_file.path)
                                    break  # Found one match, no need to check other patterns for this file
                
                if issues_found:
                    description = pattern_config['description']
                    severity = pattern_config['severity']
                    patterns.append(f"anti_pattern_{pattern_name} ({description}, severity: {severity}, found in {len(set(issues_found))} files)")
            
            return patterns
            
        except Exception as e:
            logger.error(f"Error identifying anti-patterns: {e}")
            return []
    
    def _identify_fortigate_patterns(self, terraform_files: List[TerraformFile]) -> List[str]:
        """Identify FortiGate-specific configuration patterns."""
        patterns = []
        
        try:
            for pattern_name, pattern_config in self.FORTIGATE_PATTERNS.items():
                pattern_found = False
                file_count = 0
                
                for tf_file in terraform_files:
                    if hasattr(tf_file, '_content') and tf_file._content:
                        content_lower = tf_file._content.lower()
                        
                        for pattern in pattern_config['patterns']:
                            if pattern.lower() in content_lower:
                                pattern_found = True
                                file_count += 1
                                break
                
                if pattern_found:
                    description = pattern_config['description']
                    patterns.append(f"fortigate_{pattern_name} ({description}, found in {file_count} files)")
            
            return patterns
            
        except Exception as e:
            logger.error(f"Error identifying FortiGate patterns: {e}")
            return []
    
    def _identify_reusable_components(self, terraform_files: List[TerraformFile]) -> List[str]:
        """Identify reusable components across cloud providers."""
        patterns = []
        
        try:
            # Track module usage across different cloud providers
            module_usage = defaultdict(lambda: {'count': 0, 'providers': set(), 'files': []})
            
            for tf_file in terraform_files:
                for module in tf_file.modules:
                    if module.source and not module.source.startswith(('http', 'git', 'registry')):
                        # Local module
                        module_key = self._normalize_module_path(module.source)
                        module_usage[module_key]['count'] += 1
                        module_usage[module_key]['providers'].add(tf_file.cloud_provider)
                        module_usage[module_key]['files'].append(tf_file.path)
            
            # Identify highly reused modules
            for module_path, usage_info in module_usage.items():
                if usage_info['count'] >= 2:  # Used in multiple places
                    providers = list(usage_info['providers'])
                    if len(providers) > 1:
                        patterns.append(f"multi_cloud_reusable_module ({module_path}, used across {', '.join(providers)})")
                    else:
                        patterns.append(f"reusable_module ({module_path}, used {usage_info['count']} times)")
            
            # Identify common resource patterns across providers
            resource_patterns = self._identify_cross_provider_resource_patterns(terraform_files)
            patterns.extend(resource_patterns)
            
            return patterns
            
        except Exception as e:
            logger.error(f"Error identifying reusable components: {e}")
            return []
    
    def _identify_cross_provider_resource_patterns(self, terraform_files: List[TerraformFile]) -> List[str]:
        """Identify common resource patterns across different cloud providers."""
        patterns = []
        
        try:
            # Group resources by cloud provider
            provider_resources = defaultdict(lambda: defaultdict(int))
            
            for tf_file in terraform_files:
                provider = tf_file.cloud_provider
                if provider != 'unknown':
                    for resource in tf_file.resources:
                        # Normalize resource type to generic pattern
                        generic_type = self._normalize_resource_type(resource.type)
                        provider_resources[provider][generic_type] += 1
            
            # Find patterns that exist across multiple providers
            all_patterns = set()
            for provider_patterns in provider_resources.values():
                all_patterns.update(provider_patterns.keys())
            
            for pattern in all_patterns:
                providers_with_pattern = []
                total_count = 0
                
                for provider, patterns_dict in provider_resources.items():
                    if pattern in patterns_dict:
                        providers_with_pattern.append(provider)
                        total_count += patterns_dict[pattern]
                
                if len(providers_with_pattern) >= 2:  # Pattern exists in multiple providers
                    patterns.append(f"cross_provider_{pattern} (found in {', '.join(providers_with_pattern)}, total: {total_count})")
            
            return patterns
            
        except Exception as e:
            logger.error(f"Error identifying cross-provider resource patterns: {e}")
            return []
    
    def _normalize_resource_type(self, resource_type: str) -> str:
        """Normalize resource type to generic pattern."""
        # Remove provider prefix and normalize to generic type
        if '_' in resource_type:
            parts = resource_type.split('_', 1)
            if len(parts) > 1:
                generic_type = parts[1]
                
                # Map to common patterns - order matters for specificity
                if any(keyword in generic_type for keyword in ['vpc', 'virtual_network', 'vnet']) or generic_type == 'compute_network':
                    return 'virtual_network'
                elif 'subnet' in generic_type or generic_type == 'compute_subnetwork':
                    return 'subnet'
                elif any(keyword in generic_type for keyword in ['security_group', 'nsg', 'network_security_group']):
                    return 'security_group'
                elif any(keyword in generic_type for keyword in ['load_balancer', 'lb']):
                    return 'load_balancer'
                elif any(keyword in generic_type for keyword in ['storage', 'disk', 'volume']):
                    return 'storage'
                elif any(keyword in generic_type for keyword in ['instance', 'virtual_machine', 'compute_instance']) or (generic_type.startswith('compute_') and 'instance' in generic_type):
                    return 'compute_instance'
                else:
                    # Return the original resource type if no pattern matches
                    return resource_type
        
        return resource_type
    
    def _analyze_configuration_similarity(self, terraform_files: List[TerraformFile]) -> List[str]:
        """Analyze configuration similarity and create clusters of similar configurations."""
        patterns = []
        
        try:
            # Group files by deployment type and cloud provider
            deployment_groups = defaultdict(list)
            
            for tf_file in terraform_files:
                key = f"{tf_file.deployment_type}_{tf_file.cloud_provider}"
                deployment_groups[key].append(tf_file)
            
            # Analyze similarity within each group
            for group_key, files in deployment_groups.items():
                if len(files) >= 2:  # Need at least 2 files to compare
                    similarity_score = self._calculate_configuration_similarity(files)
                    
                    if similarity_score >= 0.7:  # High similarity threshold
                        patterns.append(f"high_similarity_cluster ({group_key}, {len(files)} files, similarity: {similarity_score:.2f})")
                    elif similarity_score >= 0.4:  # Medium similarity
                        patterns.append(f"medium_similarity_cluster ({group_key}, {len(files)} files, similarity: {similarity_score:.2f})")
            
            # Identify template patterns
            template_patterns = self._identify_template_patterns(terraform_files)
            patterns.extend(template_patterns)
            
            return patterns
            
        except Exception as e:
            logger.error(f"Error analyzing configuration similarity: {e}")
            return []
    
    def _calculate_configuration_similarity(self, files: List[TerraformFile]) -> float:
        """Calculate similarity score between configuration files."""
        try:
            if len(files) < 2:
                return 0.0
            
            # Compare resource types and counts
            resource_signatures = []
            
            for tf_file in files:
                signature = defaultdict(int)
                for resource in tf_file.resources:
                    signature[resource.type] += 1
                resource_signatures.append(signature)
            
            # Calculate Jaccard similarity between resource signatures
            total_similarity = 0.0
            comparisons = 0
            
            for i in range(len(resource_signatures)):
                for j in range(i + 1, len(resource_signatures)):
                    sig1, sig2 = resource_signatures[i], resource_signatures[j]
                    
                    # Calculate Jaccard similarity
                    all_types = set(sig1.keys()) | set(sig2.keys())
                    intersection = sum(min(sig1.get(t, 0), sig2.get(t, 0)) for t in all_types)
                    union = sum(max(sig1.get(t, 0), sig2.get(t, 0)) for t in all_types)
                    
                    if union > 0:
                        similarity = intersection / union
                        total_similarity += similarity
                        comparisons += 1
            
            return total_similarity / comparisons if comparisons > 0 else 0.0
            
        except Exception as e:
            logger.error(f"Error calculating configuration similarity: {e}")
            return 0.0
    
    def _identify_template_patterns(self, terraform_files: List[TerraformFile]) -> List[str]:
        """Identify template patterns that could be abstracted into reusable modules."""
        patterns = []
        
        try:
            # Look for repeated resource combinations
            resource_combinations = defaultdict(list)
            
            for tf_file in terraform_files:
                if len(tf_file.resources) >= 2:  # Need multiple resources to form a pattern
                    # Create a signature of resource types in this file
                    resource_types = sorted([r.type for r in tf_file.resources])
                    combination_key = tuple(resource_types)
                    resource_combinations[combination_key].append(tf_file.path)
            
            # Identify frequently occurring combinations
            for combination, files in resource_combinations.items():
                if len(files) >= 2:  # Pattern appears in multiple files
                    resource_list = ', '.join(combination[:3])  # Show first 3 resource types
                    if len(combination) > 3:
                        resource_list += f" (and {len(combination) - 3} more)"
                    
                    patterns.append(f"template_pattern ({resource_list}, found in {len(files)} files)")
            
            return patterns
            
        except Exception as e:
            logger.error(f"Error identifying template patterns: {e}")
            return []
    
    def _identify_multi_cloud_patterns(self, terraform_files: List[TerraformFile]) -> List[str]:
        """Identify multi-cloud deployment patterns."""
        patterns = []
        
        try:
            # Collect cloud providers
            cloud_providers = set()
            for tf_file in terraform_files:
                if tf_file.cloud_provider != 'unknown':
                    cloud_providers.add(tf_file.cloud_provider)
            
            if len(cloud_providers) > 1:
                patterns.append(f"multi_cloud (providers: {', '.join(sorted(cloud_providers))})")
                
                # Analyze deployment consistency across providers
                deployment_consistency = self._analyze_multi_cloud_consistency(terraform_files)
                patterns.extend(deployment_consistency)
            
            # Identify module reuse patterns
            module_sources = defaultdict(int)
            for tf_file in terraform_files:
                for module in tf_file.modules:
                    if module.source:
                        module_sources[module.source] += 1
            
            reused_modules = [source for source, count in module_sources.items() if count > 1]
            if reused_modules:
                patterns.append(f"module_reuse ({len(reused_modules)} reused modules)")
            
            return patterns
            
        except Exception as e:
            logger.error(f"Error identifying multi-cloud patterns: {e}")
            return []
    
    def _analyze_multi_cloud_consistency(self, terraform_files: List[TerraformFile]) -> List[str]:
        """Analyze consistency of deployments across cloud providers."""
        patterns = []
        
        try:
            # Group by deployment type
            deployment_by_type = defaultdict(lambda: defaultdict(list))
            
            for tf_file in terraform_files:
                if tf_file.deployment_type != 'unknown' and tf_file.cloud_provider != 'unknown':
                    deployment_by_type[tf_file.deployment_type][tf_file.cloud_provider].append(tf_file)
            
            # Check consistency within each deployment type
            for deployment_type, provider_files in deployment_by_type.items():
                if len(provider_files) > 1:  # Multiple providers for same deployment type
                    providers = list(provider_files.keys())
                    
                    # Calculate consistency score
                    consistency_score = self._calculate_multi_cloud_consistency_score(provider_files)
                    
                    if consistency_score >= 0.8:
                        patterns.append(f"consistent_multi_cloud_{deployment_type} (providers: {', '.join(providers)}, consistency: {consistency_score:.2f})")
                    elif consistency_score < 0.5:
                        patterns.append(f"inconsistent_multi_cloud_{deployment_type} (providers: {', '.join(providers)}, consistency: {consistency_score:.2f})")
            
            return patterns
            
        except Exception as e:
            logger.error(f"Error analyzing multi-cloud consistency: {e}")
            return []
    
    def _calculate_multi_cloud_consistency_score(self, provider_files: Dict[str, List[TerraformFile]]) -> float:
        """Calculate consistency score across cloud providers for the same deployment type."""
        try:
            # Compare resource patterns across providers
            provider_patterns = {}
            
            for provider, files in provider_files.items():
                pattern = defaultdict(int)
                for tf_file in files:
                    for resource in tf_file.resources:
                        generic_type = self._normalize_resource_type(resource.type)
                        pattern[generic_type] += 1
                provider_patterns[provider] = pattern
            
            # Calculate similarity between provider patterns
            providers = list(provider_patterns.keys())
            if len(providers) < 2:
                return 1.0
            
            total_similarity = 0.0
            comparisons = 0
            
            for i in range(len(providers)):
                for j in range(i + 1, len(providers)):
                    pattern1 = provider_patterns[providers[i]]
                    pattern2 = provider_patterns[providers[j]]
                    
                    # Calculate Jaccard similarity
                    all_types = set(pattern1.keys()) | set(pattern2.keys())
                    intersection = sum(min(pattern1.get(t, 0), pattern2.get(t, 0)) for t in all_types)
                    union = sum(max(pattern1.get(t, 0), pattern2.get(t, 0)) for t in all_types)
                    
                    if union > 0:
                        similarity = intersection / union
                        total_similarity += similarity
                        comparisons += 1
            
            return total_similarity / comparisons if comparisons > 0 else 0.0
            
        except Exception as e:
            logger.error(f"Error calculating multi-cloud consistency score: {e}")
            return 0.0
    
    def _normalize_module_path(self, module_source: str) -> str:
        """Normalize module source path for comparison."""
        # Remove leading ./ and trailing /
        normalized = module_source.strip('./').rstrip('/')
        return normalized
    
    def _normalize_file_path(self, file_path: str) -> str:
        """Normalize file path for comparison."""
        # Convert to Path and get parent directory
        path = Path(file_path)
        return str(path.parent) if path.parent != Path('.') else ''
    
    def _has_root_indicators(self, tf_file: TerraformFile) -> bool:
        """Check if file has indicators of being a root module."""
        # Check for terraform block
        if tf_file.ast and tf_file.ast.terraform_block:
            return True
        
        # Check for provider configurations
        if tf_file.ast and tf_file.ast.providers:
            return True
        
        # Check for backend configuration
        if hasattr(tf_file, '_content') and tf_file._content:
            content_lower = tf_file._content.lower()
            if 'backend' in content_lower or 'terraform {' in content_lower:
                return True
        
        return False
    
    def _fallback_entry_point_detection(self, terraform_files: List[TerraformFile]) -> List[str]:
        """Fallback method for entry point detection when primary methods fail."""
        entry_points = []
        
        # Use files in root directories
        root_files = [tf_file.path for tf_file in terraform_files 
                     if '/' not in tf_file.path or tf_file.path.count('/') <= 1]
        
        if root_files:
            entry_points.extend(root_files[:3])  # Limit to first 3 files
        else:
            # Use first few files as fallback
            entry_points.extend([tf_file.path for tf_file in terraform_files[:2]])
        
        logger.info(f"Using fallback entry point detection: {entry_points}")
        return entry_points
    
    def _extract_dependencies_from_value(self, value: str) -> List[str]:
        """Extract dependency references from a string value."""
        dependencies = []
        
        # Look for various reference patterns
        patterns = [
            r'module\.([a-zA-Z_][a-zA-Z0-9_]*)',  # module.name
            r'data\.([a-zA-Z_][a-zA-Z0-9_]*\.[a-zA-Z_][a-zA-Z0-9_]*)',  # data.type.name
            r'([a-zA-Z_][a-zA-Z0-9_]*\.[a-zA-Z_][a-zA-Z0-9_]*)',  # resource.name
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, value)
            dependencies.extend(matches)
        
        return dependencies
    
    def _extract_resource_references(self, value: str) -> List[str]:
        """Extract resource references from a string value."""
        references = []
        
        # Look for resource references
        resource_pattern = r'([a-zA-Z_][a-zA-Z0-9_]*_[a-zA-Z_][a-zA-Z0-9_]*)\.[a-zA-Z_][a-zA-Z0-9_]*'
        matches = re.findall(resource_pattern, value)
        
        for match in matches:
            # Convert to resource.name format
            parts = match.split('_', 1)
            if len(parts) == 2:
                references.append(f"{match}.{parts[1]}")
        
        return references
    
    def _populate_dependents(self, components: List[ArchitectureComponent]) -> None:
        """Populate the dependents field for each component."""
        # Create a mapping of component names to components
        component_map = {comp.name: comp for comp in components}
        
        # For each component, add it as a dependent to its dependencies
        for component in components:
            for dependency in component.dependencies:
                if dependency in component_map:
                    component_map[dependency].dependents.append(component.name)
    
    def _infer_cloud_provider_from_module(self, module: Module) -> str:
        """Infer cloud provider from module source or name."""
        source_lower = module.source.lower() if module.source else ''
        name_lower = module.name.lower()
        
        cloud_indicators = {
            'aws': ['aws', 'amazon'],
            'azure': ['azure', 'azurerm'],
            'gcp': ['google', 'gcp'],
            'ibm': ['ibm'],
            'oci': ['oci', 'oracle'],
            'alicloud': ['alicloud', 'alibaba'],
            'openstack': ['openstack']
        }
        
        for provider, indicators in cloud_indicators.items():
            for indicator in indicators:
                if indicator in source_lower or indicator in name_lower:
                    return provider
        
        return 'unknown'
    
    def _infer_cloud_provider_from_name(self, name: str) -> str:
        """Infer cloud provider from resource or data source name."""
        name_lower = name.lower()
        
        if name_lower.startswith('aws_'):
            return 'aws'
        elif name_lower.startswith('azurerm_'):
            return 'azure'
        elif name_lower.startswith('google_'):
            return 'gcp'
        elif name_lower.startswith('ibm_'):
            return 'ibm'
        elif name_lower.startswith('oci_'):
            return 'oci'
        elif name_lower.startswith('alicloud_'):
            return 'alicloud'
        elif name_lower.startswith('openstack_'):
            return 'openstack'
        
        return 'unknown'
    
    def _analyze_deployment_patterns_in_file(self, tf_file: TerraformFile) -> List[str]:
        """Analyze deployment patterns within a single file."""
        patterns = []
        
        try:
            # Check file path for patterns
            file_path_lower = tf_file.path.lower()
            
            for scenario_name, scenario_config in self.DEPLOYMENT_SCENARIO_PATTERNS.items():
                # Check path patterns
                for pattern in scenario_config['patterns']:
                    if pattern in file_path_lower:
                        patterns.append(scenario_name)
                        break
                
                # Check resource indicators if we have content
                if hasattr(tf_file, '_content') and tf_file._content:
                    content_lower = tf_file._content.lower()
                    for indicator in scenario_config['resource_indicators']:
                        if indicator in content_lower:
                            patterns.append(scenario_name)
                            break
            
            return list(set(patterns))  # Remove duplicates
            
        except Exception as e:
            logger.error(f"Error analyzing deployment patterns in file {tf_file.path}: {e}")
            return []
    
    def _infer_scenarios_from_resources(self, terraform_files: List[TerraformFile]) -> List[str]:
        """Infer deployment scenarios from resource analysis."""
        scenarios = []
        
        try:
            all_resources = []
            for tf_file in terraform_files:
                all_resources.extend(tf_file.resources)
            
            # Count resource types
            resource_counts = defaultdict(int)
            for resource in all_resources:
                resource_counts[resource.type] += 1
            
            # Infer scenarios based on resource patterns
            for scenario_name, scenario_config in self.DEPLOYMENT_SCENARIO_PATTERNS.items():
                scenario_score = 0
                
                for indicator in scenario_config['resource_indicators']:
                    for resource_type in resource_counts:
                        if indicator in resource_type.lower():
                            scenario_score += resource_counts[resource_type]
                
                if scenario_score > 0:
                    scenarios.append(scenario_name)
            
            return scenarios
            
        except Exception as e:
            logger.error(f"Error inferring scenarios from resources: {e}")
            return []
    
    def generate_pattern_documentation(self, architecture_map: ArchitectureMap) -> Dict[str, Any]:
        """
        Generate comprehensive documentation of identified patterns and their usage.
        
        Args:
            architecture_map: The architecture map containing identified patterns
            
        Returns:
            Dictionary containing pattern documentation with usage examples and recommendations
        """
        documentation = {
            'pattern_summary': {
                'total_patterns': len(architecture_map.common_patterns),
                'pattern_categories': {},
                'recommendations': []
            },
            'pattern_details': {},
            'usage_examples': {},
            'improvement_suggestions': []
        }
        
        try:
            # Categorize patterns
            pattern_categories = {
                'best_practices': [],
                'anti_patterns': [],
                'fortigate_specific': [],
                'reusable_components': [],
                'multi_cloud': [],
                'similarity_clusters': [],
                'template_patterns': []
            }
            
            for pattern in architecture_map.common_patterns:
                if pattern.startswith('best_practice_'):
                    pattern_categories['best_practices'].append(pattern)
                elif pattern.startswith('anti_pattern_'):
                    pattern_categories['anti_patterns'].append(pattern)
                elif pattern.startswith('fortigate_'):
                    pattern_categories['fortigate_specific'].append(pattern)
                elif 'reusable' in pattern or 'multi_cloud_reusable' in pattern:
                    pattern_categories['reusable_components'].append(pattern)
                elif pattern.startswith('multi_cloud') or 'cross_provider' in pattern:
                    pattern_categories['multi_cloud'].append(pattern)
                elif 'similarity_cluster' in pattern:
                    pattern_categories['similarity_clusters'].append(pattern)
                elif 'template_pattern' in pattern:
                    pattern_categories['template_patterns'].append(pattern)
            
            documentation['pattern_summary']['pattern_categories'] = {
                k: len(v) for k, v in pattern_categories.items() if v
            }
            
            # Generate detailed documentation for each pattern category
            for category, patterns in pattern_categories.items():
                if patterns:
                    documentation['pattern_details'][category] = self._generate_category_documentation(category, patterns)
            
            # Generate usage examples
            documentation['usage_examples'] = self._generate_usage_examples(pattern_categories)
            
            # Generate improvement suggestions
            documentation['improvement_suggestions'] = self._generate_improvement_suggestions(pattern_categories)
            
            # Add general recommendations
            documentation['pattern_summary']['recommendations'] = self._generate_general_recommendations(pattern_categories)
            
            return documentation
            
        except Exception as e:
            logger.error(f"Error generating pattern documentation: {e}")
            return documentation
    
    def _generate_category_documentation(self, category: str, patterns: List[str]) -> Dict[str, Any]:
        """Generate detailed documentation for a pattern category."""
        category_docs = {
            'description': '',
            'patterns': [],
            'impact': '',
            'recommendations': []
        }
        
        try:
            # Category descriptions
            descriptions = {
                'best_practices': 'Terraform best practices found in the codebase that promote maintainability and reliability.',
                'anti_patterns': 'Anti-patterns that should be addressed to improve code quality and security.',
                'fortigate_specific': 'FortiGate-specific configuration patterns and practices.',
                'reusable_components': 'Components that are reused across different deployments or cloud providers.',
                'multi_cloud': 'Patterns related to multi-cloud deployments and cross-provider consistency.',
                'similarity_clusters': 'Groups of similar configurations that could benefit from standardization.',
                'template_patterns': 'Repeated resource combinations that could be abstracted into reusable templates.'
            }
            
            category_docs['description'] = descriptions.get(category, 'Identified patterns in this category.')
            
            # Process each pattern
            for pattern in patterns:
                pattern_info = self._parse_pattern_info(pattern)
                category_docs['patterns'].append(pattern_info)
            
            # Generate category-specific recommendations
            category_docs['recommendations'] = self._generate_category_recommendations(category, patterns)
            
            # Assess impact
            category_docs['impact'] = self._assess_category_impact(category, len(patterns))
            
            return category_docs
            
        except Exception as e:
            logger.error(f"Error generating category documentation for {category}: {e}")
            return category_docs
    
    def _parse_pattern_info(self, pattern: str) -> Dict[str, Any]:
        """Parse pattern string to extract structured information."""
        pattern_info = {
            'name': '',
            'description': '',
            'details': '',
            'severity': 'INFO',
            'count': 0
        }
        
        try:
            # Extract pattern name (before first parenthesis)
            if '(' in pattern:
                pattern_info['name'] = pattern.split('(')[0].strip()
                details_part = pattern.split('(', 1)[1].rstrip(')')
                pattern_info['details'] = details_part
            else:
                pattern_info['name'] = pattern
            
            # Extract severity for anti-patterns
            if 'severity:' in pattern:
                severity_match = re.search(r'severity:\s*(\w+)', pattern)
                if severity_match:
                    pattern_info['severity'] = severity_match.group(1)
            
            # Extract count information
            count_patterns = [
                r'found in (\d+) files',
                r'used (\d+) times',
                r'total: (\d+)',
                r'(\d+) files'
            ]
            
            for count_pattern in count_patterns:
                match = re.search(count_pattern, pattern)
                if match:
                    pattern_info['count'] = int(match.group(1))
                    break
            
            # Generate description based on pattern type
            pattern_info['description'] = self._generate_pattern_description(pattern_info['name'])
            
            return pattern_info
            
        except Exception as e:
            logger.error(f"Error parsing pattern info for {pattern}: {e}")
            return pattern_info
    
    def _generate_pattern_description(self, pattern_name: str) -> str:
        """Generate a description for a pattern based on its name."""
        descriptions = {
            'best_practice_variable_usage': 'Proper use of variables for parameterization improves flexibility and reusability.',
            'best_practice_output_usage': 'Well-defined outputs enable proper module composition and data flow.',
            'best_practice_data_sources': 'Data sources provide clean integration with existing infrastructure.',
            'best_practice_locals': 'Local values help organize complex expressions and reduce duplication.',
            'best_practice_module_composition': 'Modular architecture promotes reusability and maintainability.',
            'anti_pattern_hardcoded_values': 'Hardcoded values reduce flexibility and make configurations environment-specific.',
            'anti_pattern_missing_tags': 'Missing tags make resource management and cost tracking difficult.',
            'anti_pattern_overly_permissive_security': 'Overly permissive security rules create potential security vulnerabilities.',
            'anti_pattern_single_az_deployment': 'Single AZ deployments create single points of failure.',
            'anti_pattern_missing_versioning': 'Missing version constraints can lead to unexpected changes.',
            'fortigate_ha_configuration': 'High availability configuration ensures business continuity.',
            'fortigate_security_policies': 'Security policies define traffic flow and access control.',
            'fortigate_network_interfaces': 'Network interface configuration enables proper connectivity.',
            'fortigate_routing_configuration': 'Routing configuration ensures proper traffic flow.',
            'fortigate_vpn_configuration': 'VPN configuration enables secure remote connectivity.'
        }
        
        return descriptions.get(pattern_name, f'Pattern identified: {pattern_name}')
    
    def _generate_category_recommendations(self, category: str, patterns: List[str]) -> List[str]:
        """Generate recommendations for a pattern category."""
        recommendations = []
        
        try:
            if category == 'best_practices':
                recommendations.extend([
                    'Continue following these best practices across all configurations',
                    'Document these patterns as organizational standards',
                    'Use these patterns as templates for new deployments'
                ])
            
            elif category == 'anti_patterns':
                recommendations.extend([
                    'Prioritize fixing high-severity anti-patterns first',
                    'Create linting rules to prevent these patterns in the future',
                    'Refactor configurations to eliminate these issues'
                ])
            
            elif category == 'fortigate_specific':
                recommendations.extend([
                    'Ensure FortiGate configurations follow vendor best practices',
                    'Validate configurations against FortiGate documentation',
                    'Consider creating reusable FortiGate modules'
                ])
            
            elif category == 'reusable_components':
                recommendations.extend([
                    'Extract common patterns into shared modules',
                    'Create a module registry for organization-wide reuse',
                    'Document module interfaces and usage examples'
                ])
            
            elif category == 'multi_cloud':
                recommendations.extend([
                    'Standardize deployment patterns across cloud providers',
                    'Create provider-agnostic abstractions where possible',
                    'Maintain consistency in naming and tagging conventions'
                ])
            
            elif category == 'similarity_clusters':
                recommendations.extend([
                    'Consider consolidating similar configurations',
                    'Create templates for common deployment patterns',
                    'Standardize configurations within each cluster'
                ])
            
            elif category == 'template_patterns':
                recommendations.extend([
                    'Abstract repeated patterns into reusable modules',
                    'Create configuration templates for common scenarios',
                    'Reduce duplication through better module design'
                ])
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error generating category recommendations for {category}: {e}")
            return recommendations
    
    def _assess_category_impact(self, category: str, pattern_count: int) -> str:
        """Assess the impact level of a pattern category."""
        impact_levels = {
            'anti_patterns': 'HIGH' if pattern_count > 5 else 'MEDIUM' if pattern_count > 2 else 'LOW',
            'best_practices': 'POSITIVE',
            'fortigate_specific': 'MEDIUM',
            'reusable_components': 'POSITIVE',
            'multi_cloud': 'HIGH' if pattern_count > 3 else 'MEDIUM',
            'similarity_clusters': 'MEDIUM',
            'template_patterns': 'MEDIUM'
        }
        
        return impact_levels.get(category, 'LOW')
    
    def _generate_usage_examples(self, pattern_categories: Dict[str, List[str]]) -> Dict[str, List[str]]:
        """Generate usage examples for different pattern categories."""
        examples = {}
        
        try:
            if pattern_categories.get('best_practices'):
                examples['best_practices'] = [
                    'Use variables for all configurable values: var.instance_type',
                    'Define clear outputs: output "vpc_id" { value = aws_vpc.main.id }',
                    'Use data sources: data "aws_ami" "ubuntu" { ... }'
                ]
            
            if pattern_categories.get('reusable_components'):
                examples['reusable_components'] = [
                    'Create shared VPC module: module "vpc" { source = "./modules/vpc" }',
                    'Reuse FortiGate module across environments',
                    'Use consistent naming conventions across modules'
                ]
            
            if pattern_categories.get('multi_cloud'):
                examples['multi_cloud'] = [
                    'Standardize resource naming: ${var.environment}-${var.application}-vpc',
                    'Use consistent tagging: tags = merge(var.common_tags, { Name = "..." })',
                    'Abstract provider differences in modules'
                ]
            
            return examples
            
        except Exception as e:
            logger.error(f"Error generating usage examples: {e}")
            return examples
    
    def _generate_improvement_suggestions(self, pattern_categories: Dict[str, List[str]]) -> List[Dict[str, Any]]:
        """Generate specific improvement suggestions based on identified patterns."""
        suggestions = []
        
        try:
            # Anti-pattern improvements
            if pattern_categories.get('anti_patterns'):
                suggestions.append({
                    'category': 'Security',
                    'priority': 'HIGH',
                    'suggestion': 'Address overly permissive security group rules',
                    'impact': 'Reduces security vulnerabilities',
                    'effort': 'MEDIUM'
                })
                
                suggestions.append({
                    'category': 'Maintainability',
                    'priority': 'MEDIUM',
                    'suggestion': 'Replace hardcoded values with variables',
                    'impact': 'Improves configuration flexibility',
                    'effort': 'SMALL'
                })
            
            # Reusability improvements
            if pattern_categories.get('template_patterns'):
                suggestions.append({
                    'category': 'Architecture',
                    'priority': 'MEDIUM',
                    'suggestion': 'Extract repeated patterns into reusable modules',
                    'impact': 'Reduces code duplication and improves maintainability',
                    'effort': 'LARGE'
                })
            
            # Multi-cloud improvements
            if pattern_categories.get('multi_cloud'):
                suggestions.append({
                    'category': 'Standardization',
                    'priority': 'MEDIUM',
                    'suggestion': 'Standardize deployment patterns across cloud providers',
                    'impact': 'Improves consistency and reduces operational complexity',
                    'effort': 'LARGE'
                })
            
            return suggestions
            
        except Exception as e:
            logger.error(f"Error generating improvement suggestions: {e}")
            return suggestions
    
    def _generate_general_recommendations(self, pattern_categories: Dict[str, List[str]]) -> List[str]:
        """Generate general recommendations based on all identified patterns."""
        recommendations = []
        
        try:
            total_patterns = sum(len(patterns) for patterns in pattern_categories.values())
            
            if total_patterns > 20:
                recommendations.append('Consider implementing automated pattern detection in CI/CD pipeline')
            
            if pattern_categories.get('anti_patterns'):
                recommendations.append('Prioritize addressing anti-patterns to improve code quality')
            
            if pattern_categories.get('reusable_components'):
                recommendations.append('Leverage identified reusable components to reduce duplication')
            
            if pattern_categories.get('multi_cloud'):
                recommendations.append('Develop multi-cloud governance standards')
            
            if len(pattern_categories.get('best_practices', [])) > 5:
                recommendations.append('Document and share best practices across the organization')
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error generating general recommendations: {e}")
            return recommendations