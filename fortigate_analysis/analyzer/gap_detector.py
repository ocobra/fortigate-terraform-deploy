"""
Gap detection and analysis for FortiGate Terraform configurations.

This module implements comprehensive gap analysis to identify missing functionality,
configuration inconsistencies, and incomplete deployment scenarios across the
FortiGate Terraform repository.
"""

from typing import List, Dict, Set, Any, Optional
from collections import defaultdict, Counter
from pathlib import Path

from ..models import (
    RepositoryInventory,
    GapAnalysis,
    TerraformFile,
    CloudProviderConfig,
    DeploymentScenario,
    Severity,
    Category,
    BestPracticeIssue,
)
from ..interfaces import GapDetectorProtocol, BaseAnalyzer


class GapDetector(BaseAnalyzer, GapDetectorProtocol):
    """
    Detects gaps and missing functionality in FortiGate Terraform configurations.
    
    This class performs comprehensive gap analysis by comparing deployment scenarios
    across cloud providers, identifying missing functionality, detecting configuration
    inconsistencies, and analyzing completeness of deployment scenarios.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the GapDetector.
        
        Args:
            config: Optional configuration dictionary for customizing gap detection
        """
        super().__init__(config)
        
        # Expected deployment scenarios for comprehensive coverage
        self.expected_scenarios = {
            'single', 'ha', 'ha-single-az', 'ha-3ports', 'ha-cross-zone',
            'ha-cross-zone-3ports', 'loadbalancer', 'gwlb', 'gwlb-crossaz',
            'gwlb-transit', 'gwlb-multitenant', 'transitgwy', 'transitgwyconnect',
            'ha-endpoint', 'ha-existing-vpc', 'ha-single-az-existing',
            'ha-port1-mgmt', 'ha-port1-mgmt-3ports', 'ha-port1-mgmt-crosszone',
            'ha-port1-mgmt-crosszone-3ports', 'ha-port1-mgmt-float',
            'azurevwan', 'ha-dualloadbalancer', 'ha-loadbalancer',
            'ha-cross', 'ha-par'
        }
        
        # Expected cloud providers
        self.expected_providers = {
            'aws', 'azure', 'gcp', 'ibm', 'oci', 'alicloud', 'openstack'
        }
        
        # Expected FortiGate versions
        self.expected_versions = {'6.2', '6.4', '7.0', '7.2', '7.4', '7.6'}
        
        # Common configuration patterns that should be consistent
        self.common_patterns = {
            'security_groups', 'firewall_rules', 'network_interfaces',
            'load_balancers', 'auto_scaling', 'monitoring', 'logging',
            'backup_configuration', 'high_availability', 'encryption'
        }
    
    def analyze(self, inventory: RepositoryInventory) -> GapAnalysis:
        """
        Perform analysis operation (required by BaseAnalyzer).
        
        Args:
            inventory: Repository inventory to analyze
            
        Returns:
            GapAnalysis containing all identified gaps and inconsistencies
        """
        return self.detect_gaps(inventory)
    
    def detect_gaps(self, inventory: RepositoryInventory) -> GapAnalysis:
        """
        Perform comprehensive gap analysis on the repository inventory.
        
        Args:
            inventory: Complete repository inventory from scanning
            
        Returns:
            GapAnalysis containing all identified gaps and inconsistencies
        """
        if not self.validate_input(inventory):
            raise ValueError("Invalid repository inventory provided")
        
        try:
            # Analyze different types of gaps
            missing_functionality = self._find_missing_functionality(inventory)
            inconsistencies = self._detect_configuration_inconsistencies(inventory)
            incomplete_scenarios = self._analyze_scenario_completeness(inventory)
            cross_provider_gaps = self._identify_cross_provider_gaps(inventory)
            
            return GapAnalysis(
                missing_functionality=missing_functionality,
                inconsistencies=inconsistencies,
                incomplete_scenarios=incomplete_scenarios,
                cross_provider_gaps=cross_provider_gaps
            )
            
        except Exception as e:
            self.handle_error(e, "gap detection")
            # Return empty analysis on error
            return GapAnalysis()
    
    def find_missing_functionality(self, scenarios: List[str]) -> List[str]:
        """
        Find missing functionality across deployment scenarios.
        
        Args:
            scenarios: List of available deployment scenarios
            
        Returns:
            List of missing functionality descriptions
        """
        available_scenarios = set(scenarios)
        missing_scenarios = self.expected_scenarios - available_scenarios
        
        missing_functionality = []
        
        # Check for missing core scenarios
        if 'single' not in available_scenarios:
            missing_functionality.append("Single instance deployment scenario missing")
        
        if 'ha' not in available_scenarios:
            missing_functionality.append("High availability deployment scenario missing")
        
        # Check for missing advanced scenarios
        if not any('gwlb' in scenario for scenario in available_scenarios):
            missing_functionality.append("Gateway Load Balancer scenarios missing")
        
        if not any('transit' in scenario for scenario in available_scenarios):
            missing_functionality.append("Transit Gateway scenarios missing")
        
        # Add specific missing scenarios
        for scenario in missing_scenarios:
            missing_functionality.append(f"Missing deployment scenario: {scenario}")
        
        return missing_functionality
    
    def detect_inconsistencies(self, configs: Dict[str, List[TerraformFile]]) -> List[str]:
        """
        Detect configuration inconsistencies across cloud providers.
        
        Args:
            configs: Dictionary mapping cloud providers to their configuration files
            
        Returns:
            List of inconsistency descriptions
        """
        inconsistencies = []
        
        # Analyze variable naming consistency
        variable_patterns = self._analyze_variable_patterns(configs)
        inconsistencies.extend(variable_patterns)
        
        # Analyze resource naming consistency
        resource_patterns = self._analyze_resource_patterns(configs)
        inconsistencies.extend(resource_patterns)
        
        # Analyze security configuration consistency
        security_patterns = self._analyze_security_patterns(configs)
        inconsistencies.extend(security_patterns)
        
        # Analyze network configuration consistency
        network_patterns = self._analyze_network_patterns(configs)
        inconsistencies.extend(network_patterns)
        
        return inconsistencies
    
    def _find_missing_functionality(self, inventory: RepositoryInventory) -> List[str]:
        """Find missing functionality across the entire repository."""
        missing = []
        
        # Check cloud provider coverage
        available_providers = set(inventory.cloud_provider_configs.keys())
        missing_providers = self.expected_providers - available_providers
        
        for provider in missing_providers:
            missing.append(f"Missing cloud provider support: {provider}")
        
        # Check deployment scenario coverage per provider
        for provider, config in inventory.cloud_provider_configs.items():
            available_scenarios = set(config.deployment_scenarios)
            missing_scenarios = self.expected_scenarios - available_scenarios
            
            # Only report missing scenarios that are relevant for the provider
            relevant_missing = self._filter_relevant_scenarios(provider, missing_scenarios)
            for scenario in relevant_missing:
                missing.append(f"Missing {scenario} scenario for {provider}")
        
        # Check version coverage
        all_versions = set()
        for scenario in inventory.deployment_scenarios:
            all_versions.update(scenario.fortigate_versions)
        
        missing_versions = self.expected_versions - all_versions
        for version in missing_versions:
            missing.append(f"Missing FortiGate version support: {version}")
        
        # Check for missing documentation
        doc_files = [f.path for f in inventory.documentation_files]
        if not any('README' in f for f in doc_files):
            missing.append("Missing main README documentation")
        
        # Check for missing examples or demos
        if not any('example' in f.lower() or 'demo' in f.lower() for f in doc_files):
            missing.append("Missing example configurations or demos")
        
        return missing
    
    def _detect_configuration_inconsistencies(self, inventory: RepositoryInventory) -> List[str]:
        """Detect inconsistencies in configuration patterns."""
        inconsistencies = []
        
        # Group files by cloud provider
        provider_files = defaultdict(list)
        for tf_file in inventory.terraform_files:
            provider_files[tf_file.cloud_provider].append(tf_file)
        
        # Analyze variable naming patterns
        variable_patterns = self._analyze_variable_consistency(provider_files)
        inconsistencies.extend(variable_patterns)
        
        # Analyze resource configuration patterns
        resource_patterns = self._analyze_resource_consistency(provider_files)
        inconsistencies.extend(resource_patterns)
        
        # Analyze output patterns
        output_patterns = self._analyze_output_consistency(provider_files)
        inconsistencies.extend(output_patterns)
        
        return inconsistencies
    
    def _analyze_scenario_completeness(self, inventory: RepositoryInventory) -> List[str]:
        """Analyze completeness of deployment scenarios."""
        incomplete = []
        
        # Check each deployment scenario for completeness
        for scenario in inventory.deployment_scenarios:
            completeness_issues = self._check_scenario_completeness(scenario, inventory)
            incomplete.extend(completeness_issues)
        
        # Check for scenarios with insufficient cloud provider support
        scenario_providers = defaultdict(set)
        for scenario in inventory.deployment_scenarios:
            for provider in scenario.cloud_providers:
                scenario_providers[scenario.name].add(provider)
        
        for scenario_name, providers in scenario_providers.items():
            if len(providers) < 3:  # Expect at least 3 major cloud providers
                incomplete.append(
                    f"Scenario '{scenario_name}' has limited cloud provider support: {', '.join(providers)}"
                )
        
        return incomplete
    
    def _group_similar_variables(self, variables: set) -> List[List[str]]:
        """Group variables with similar names that might indicate inconsistencies."""
        groups = []
        processed = set()
        
        for var in variables:
            if var in processed:
                continue
                
            # Find similar variables
            similar = [var]
            for other_var in variables:
                if other_var != var and other_var not in processed:
                    # Check for similar patterns (e.g., instance_type vs vm_size vs machine_type)
                    if self._are_variables_similar(var, other_var):
                        similar.append(other_var)
            
            if len(similar) > 1:
                groups.append(similar)
                processed.update(similar)
            else:
                processed.add(var)
        
        return groups
    
    def _are_variables_similar(self, var1: str, var2: str) -> bool:
        """Check if two variable names are similar and might represent the same concept."""
        # Common patterns for similar variables
        instance_patterns = {'instance_type', 'vm_size', 'machine_type', 'instance_size'}
        key_patterns = {'key_name', 'ssh_key', 'key_pair', 'public_key'}
        region_patterns = {'region', 'location', 'zone', 'availability_zone'}
        
        pattern_groups = [instance_patterns, key_patterns, region_patterns]
        
        for pattern_group in pattern_groups:
            if var1 in pattern_group and var2 in pattern_group:
                return True
        
        return False
    
    def _identify_cross_provider_gaps(self, inventory: RepositoryInventory) -> List[str]:
        """Identify gaps when comparing across cloud providers."""
        gaps = []
        
        # Analyze feature parity across providers
        provider_features = self._extract_provider_features(inventory)
        gaps.extend(self._find_feature_gaps(provider_features))
        
        # Analyze configuration complexity differences
        complexity_gaps = self._analyze_complexity_gaps(inventory)
        gaps.extend(complexity_gaps)
        
        # Analyze version support differences
        version_gaps = self._analyze_version_support_gaps(inventory)
        gaps.extend(version_gaps)
        
        return gaps
    
    def _filter_relevant_scenarios(self, provider: str, scenarios: Set[str]) -> Set[str]:
        """Filter scenarios to only those relevant for the given provider."""
        # Provider-specific scenario filtering
        provider_specific = {
            'aws': {'gwlb', 'gwlb-crossaz', 'gwlb-transit', 'gwlb-multitenant', 'transitgwy', 'transitgwyconnect'},
            'azure': {'azurevwan', 'ha-port1-mgmt', 'ha-port1-mgmt-3ports', 'ha-port1-mgmt-crosszone'},
            'gcp': {'ha-dualloadbalancer', 'ha-loadbalancer'},
            'ibm': {'ha-cross', 'ha-par'},
        }
        
        # Return intersection of missing scenarios and provider-specific scenarios
        if provider in provider_specific:
            return scenarios & provider_specific[provider]
        
        # For providers without specific scenarios, return common scenarios
        common_scenarios = {'single', 'ha', 'ha-single-az', 'loadbalancer'}
        return scenarios & common_scenarios
    
    def _analyze_variable_consistency(self, provider_files: Dict[str, List[TerraformFile]]) -> List[str]:
        """Analyze consistency of variable naming and usage across providers."""
        inconsistencies = []
        
        # Collect variable names by provider
        provider_variables = {}
        for provider, files in provider_files.items():
            variables = set()
            for tf_file in files:
                for var in tf_file.variables:
                    variables.add(var.name)
            provider_variables[provider] = variables
        
        # Find common variable patterns that should exist across providers
        # Look for variables that exist in multiple providers but not all
        all_variables = set()
        for variables in provider_variables.values():
            all_variables.update(variables)
        
        # Check for inconsistent naming patterns
        for var_name in all_variables:
            providers_with_var = [p for p, vars in provider_variables.items() if var_name in vars]
            # If a variable exists in some but not all providers, it might indicate inconsistency
            if 1 < len(providers_with_var) < len(provider_variables):
                missing_providers = set(provider_variables.keys()) - set(providers_with_var)
                inconsistencies.append(
                    f"Variable '{var_name}' missing in providers: {', '.join(missing_providers)}"
                )
        
        # Check for similar variable names that might indicate naming inconsistencies
        variable_groups = self._group_similar_variables(all_variables)
        for group in variable_groups:
            if len(group) > 1:
                # Multiple similar variable names might indicate inconsistency
                providers_per_var = {}
                for var in group:
                    providers_per_var[var] = [p for p, vars in provider_variables.items() if var in vars]
                
                # If similar variables are used by different providers, it's an inconsistency
                if len(set().union(*providers_per_var.values())) > 1:
                    inconsistencies.append(
                        f"Similar variable names used inconsistently: {', '.join(group)}"
                    )
        
        return inconsistencies
    
    def _analyze_resource_consistency(self, provider_files: Dict[str, List[TerraformFile]]) -> List[str]:
        """Analyze consistency of resource configurations across providers."""
        inconsistencies = []
        
        # Collect resource types by provider
        provider_resources = {}
        for provider, files in provider_files.items():
            resource_types = Counter()
            for tf_file in files:
                for resource in tf_file.resources:
                    resource_types[resource.type] += 1
            provider_resources[provider] = resource_types
        
        # Find resources that should be common but are missing
        common_resource_patterns = {
            'network', 'security', 'compute', 'storage', 'monitoring'
        }
        
        for provider, resources in provider_resources.items():
            resource_names = ' '.join(resources.keys()).lower()
            for pattern in common_resource_patterns:
                if pattern not in resource_names:
                    inconsistencies.append(
                        f"Provider '{provider}' may be missing {pattern} resources"
                    )
        
        return inconsistencies
    
    def _analyze_output_consistency(self, provider_files: Dict[str, List[TerraformFile]]) -> List[str]:
        """Analyze consistency of outputs across providers."""
        inconsistencies = []
        
        # Collect output names by provider
        provider_outputs = {}
        for provider, files in provider_files.items():
            outputs = set()
            for tf_file in files:
                for output in tf_file.outputs:
                    outputs.add(output.name)
            provider_outputs[provider] = outputs
        
        # Find outputs that should be common
        common_outputs = {'instance_id', 'public_ip', 'private_ip', 'security_group_id'}
        
        for provider, outputs in provider_outputs.items():
            missing_outputs = common_outputs - outputs
            if missing_outputs:
                inconsistencies.append(
                    f"Provider '{provider}' missing common outputs: {', '.join(missing_outputs)}"
                )
        
        return inconsistencies
    
    def _check_scenario_completeness(self, scenario: DeploymentScenario, inventory: RepositoryInventory) -> List[str]:
        """Check if a deployment scenario is complete."""
        issues = []
        
        # Check if scenario has sufficient documentation
        scenario_docs = [
            f for f in inventory.documentation_files
            if scenario.name.lower() in f.path.lower()
        ]
        if not scenario_docs:
            issues.append(f"Scenario '{scenario.name}' lacks documentation")
        
        # Check if scenario supports multiple FortiGate versions
        if len(scenario.fortigate_versions) < 2:
            issues.append(f"Scenario '{scenario.name}' supports limited FortiGate versions")
        
        # Check if scenario has examples or test configurations
        scenario_files = [
            f for f in inventory.terraform_files
            if scenario.name.lower() in f.path.lower()
        ]
        
        has_examples = any('example' in f.path.lower() for f in scenario_files)
        has_tests = any('test' in f.path.lower() for f in scenario_files)
        
        if not has_examples:
            issues.append(f"Scenario '{scenario.name}' lacks example configurations")
        
        if not has_tests:
            issues.append(f"Scenario '{scenario.name}' lacks test configurations")
        
        return issues
    
    def _extract_provider_features(self, inventory: RepositoryInventory) -> Dict[str, Set[str]]:
        """Extract features supported by each cloud provider."""
        provider_features = defaultdict(set)
        
        for tf_file in inventory.terraform_files:
            provider = tf_file.cloud_provider
            
            # Extract features from resource types
            for resource in tf_file.resources:
                resource_type_lower = resource.type.lower()
                
                if 'load_balancer' in resource_type_lower or 'lb' in resource_type_lower:
                    provider_features[provider].add('load_balancing')
                if 'security' in resource_type_lower or 'firewall' in resource_type_lower:
                    provider_features[provider].add('security_groups')
                if 'network' in resource_type_lower or 'vpc' in resource_type_lower or 'subnet' in resource_type_lower:
                    provider_features[provider].add('networking')
                if 'auto' in resource_type_lower and 'scal' in resource_type_lower:
                    provider_features[provider].add('auto_scaling')
                if 'monitor' in resource_type_lower or 'log' in resource_type_lower:
                    provider_features[provider].add('monitoring')
                if 'instance' in resource_type_lower or 'virtual_machine' in resource_type_lower or 'compute' in resource_type_lower:
                    provider_features[provider].add('compute')
                if 'storage' in resource_type_lower or 'disk' in resource_type_lower or 'volume' in resource_type_lower:
                    provider_features[provider].add('storage')
            
            # Extract features from deployment types
            deployment_type = tf_file.deployment_type.lower()
            if 'ha' in deployment_type:
                provider_features[provider].add('high_availability')
            if 'gwlb' in deployment_type:
                provider_features[provider].add('gateway_load_balancer')
            if 'transit' in deployment_type:
                provider_features[provider].add('transit_gateway')
            if 'loadbalancer' in deployment_type or 'lb' in deployment_type:
                provider_features[provider].add('load_balancing')
        
        return provider_features
    
    def _find_feature_gaps(self, provider_features: Dict[str, Set[str]]) -> List[str]:
        """Find feature gaps across providers."""
        gaps = []
        
        # Find all available features
        all_features = set()
        for features in provider_features.values():
            all_features.update(features)
        
        # Check which providers are missing which features
        for feature in all_features:
            providers_with_feature = [p for p, features in provider_features.items() if feature in features]
            providers_without_feature = set(provider_features.keys()) - set(providers_with_feature)
            
            if providers_without_feature:
                gaps.append(
                    f"Feature '{feature}' missing in providers: {', '.join(providers_without_feature)}"
                )
        
        return gaps
    
    def _analyze_complexity_gaps(self, inventory: RepositoryInventory) -> List[str]:
        """Analyze differences in configuration complexity across providers."""
        gaps = []
        
        # Calculate complexity metrics per provider
        provider_complexity = {}
        for provider, config in inventory.cloud_provider_configs.items():
            complexity = len(config.deployment_scenarios) * len(config.supported_versions)
            provider_complexity[provider] = complexity
        
        # Find providers with significantly lower complexity
        if provider_complexity:
            avg_complexity = sum(provider_complexity.values()) / len(provider_complexity)
            
            for provider, complexity in provider_complexity.items():
                if complexity < avg_complexity * 0.5:  # Less than half average
                    gaps.append(
                        f"Provider '{provider}' has significantly lower configuration complexity"
                    )
        
        return gaps
    
    def _analyze_version_support_gaps(self, inventory: RepositoryInventory) -> List[str]:
        """Analyze differences in FortiGate version support across providers."""
        gaps = []
        
        # Collect version support by provider
        provider_versions = defaultdict(set)
        for scenario in inventory.deployment_scenarios:
            for provider in scenario.cloud_providers:
                provider_versions[provider].update(scenario.fortigate_versions)
        
        # Find version support gaps
        all_versions = set()
        for versions in provider_versions.values():
            all_versions.update(versions)
        
        for provider, versions in provider_versions.items():
            missing_versions = all_versions - versions
            if missing_versions:
                gaps.append(
                    f"Provider '{provider}' missing FortiGate version support: {', '.join(missing_versions)}"
                )
        
        return gaps
    
    def _analyze_variable_patterns(self, configs: Dict[str, List[TerraformFile]]) -> List[str]:
        """Analyze variable naming patterns for consistency."""
        return self._analyze_variable_consistency(configs)
    
    def _analyze_resource_patterns(self, configs: Dict[str, List[TerraformFile]]) -> List[str]:
        """Analyze resource naming patterns for consistency."""
        return self._analyze_resource_consistency(configs)
    
    def _analyze_security_patterns(self, configs: Dict[str, List[TerraformFile]]) -> List[str]:
        """Analyze security configuration patterns for consistency."""
        inconsistencies = []
        
        # Check for consistent security group configurations
        for provider, files in configs.items():
            has_security_groups = False
            for tf_file in files:
                for resource in tf_file.resources:
                    if 'security' in resource.type.lower():
                        has_security_groups = True
                        break
                if has_security_groups:
                    break
            
            if not has_security_groups:
                inconsistencies.append(f"Provider '{provider}' may lack security group configurations")
        
        return inconsistencies
    
    def _analyze_network_patterns(self, configs: Dict[str, List[TerraformFile]]) -> List[str]:
        """Analyze network configuration patterns for consistency."""
        inconsistencies = []
        
        # Check for consistent network configurations
        for provider, files in configs.items():
            has_network_config = False
            for tf_file in files:
                for resource in tf_file.resources:
                    if any(net_term in resource.type.lower() for net_term in ['network', 'vpc', 'subnet']):
                        has_network_config = True
                        break
                if has_network_config:
                    break
            
            if not has_network_config:
                inconsistencies.append(f"Provider '{provider}' may lack network configurations")
        
        return inconsistencies
    
    def validate_input(self, inventory: RepositoryInventory) -> bool:
        """Validate that the repository inventory is valid for gap analysis."""
        if not inventory:
            return False
        
        if not inventory.terraform_files and not inventory.cloud_provider_configs:
            return False
        
        return True
    
    def handle_error(self, error: Exception, context: str) -> None:
        """Handle errors during gap detection."""
        print(f"Error during {context}: {error}")
        # In a production system, this would use proper logging