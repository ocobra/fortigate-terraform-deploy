"""
Repository scanner implementation for discovering and cataloging repository contents.
"""

import os
import chardet
from pathlib import Path
from typing import List, Dict, Optional, Set
from datetime import datetime
import logging

from ..models import (
    RepositoryInventory,
    TerraformFile,
    PythonFile,
    DocumentationFile,
    CloudProviderConfig,
)
from ..interfaces import RepositoryScannerProtocol, BaseAnalyzer
from ..parser.code_parser import CodeParser

logger = logging.getLogger(__name__)


class RepositoryScanner(BaseAnalyzer):
    """
    Scans repository directory structure to discover and catalog all files.
    
    Identifies Terraform configurations, Python scripts, and documentation files,
    categorizing them by cloud provider and deployment scenario.
    """
    
    # File extensions to scan for
    TERRAFORM_EXTENSIONS = {'.tf', '.tfvars', '.hcl'}
    PYTHON_EXTENSIONS = {'.py'}
    DOCUMENTATION_EXTENSIONS = {'.md', '.txt', '.rst', '.adoc'}
    
    # Special files without extensions that should be treated as documentation
    SPECIAL_DOC_FILES = {'README', 'LICENSE', 'CHANGELOG', 'CONTRIBUTING', 'AUTHORS', 'NOTICE'}
    
    # Enhanced cloud provider patterns for detection
    CLOUD_PROVIDER_PATTERNS = {
        'aws': [
            # Resource prefixes
            'aws_', 'amazon',
            # Service names
            'ec2', 'vpc', 's3', 'iam', 'route53', 'elb', 'alb', 'nlb', 'gwlb',
            'cloudformation', 'lambda', 'rds', 'dynamodb', 'sns', 'sqs',
            'cloudwatch', 'cloudtrail', 'kms', 'secretsmanager',
            # AWS-specific terms
            'availability_zone', 'subnet', 'security_group', 'internet_gateway',
            'nat_gateway', 'route_table', 'network_acl', 'transit_gateway',
            # AMI and instance types
            'ami-', 't2.', 't3.', 'm5.', 'c5.', 'r5.',
            # AWS regions
            'us-east-1', 'us-west-2', 'eu-west-1', 'ap-southeast-1'
        ],
        'azure': [
            # Resource prefixes
            'azurerm_', 'azure', 'microsoft',
            # Service names
            'virtual_machine', 'virtual_network', 'network_security_group',
            'public_ip', 'load_balancer', 'application_gateway',
            'storage_account', 'key_vault', 'resource_group',
            # Azure-specific terms
            'subscription_id', 'tenant_id', 'client_id', 'client_secret',
            'location', 'sku', 'managed_disk',
            # Azure regions
            'eastus', 'westus2', 'westeurope', 'southeastasia'
        ],
        'gcp': [
            # Resource prefixes (more specific)
            'google_', 'gcp_',
            # Service names (more specific)
            'google_compute_', 'google_project_', 'google_storage_', 'google_container_',
            'google_compute_instance', 'google_compute_network', 'google_compute_firewall',
            'google_compute_address', 'google_compute_disk', 'google_compute_image',
            'google_compute_instance_group', 'google_compute_target_pool',
            'google_compute_forwarding_rule', 'google_compute_health_check',
            # GCP-specific terms (more specific)
            'project_id', 'machine_type', 'boot_disk', 'network_tier', 'service_account',
            # GCP regions/zones (more specific)
            'us-central1', 'us-west1', 'europe-west1', 'asia-southeast1'
        ],
        'ibm': [
            # Resource prefixes
            'ibm_', 'ibmcloud',
            # Service names
            'is_instance', 'is_vpc', 'is_subnet', 'is_security_group',
            'is_floating_ip', 'is_volume', 'is_image',
            'resource_group', 'iam_', 'kms_',
            # IBM-specific terms
            'vpc_gen2', 'classic', 'power_systems',
            'softlayer', 'bluemix'
        ],
        'oci': [
            # Resource prefixes
            'oci_', 'oracle',
            # Service names
            'core_instance', 'core_vcn', 'core_subnet', 'core_security_list',
            'core_internet_gateway', 'core_nat_gateway', 'core_route_table',
            'core_volume', 'core_image', 'load_balancer',
            'identity_', 'kms_', 'vault_',
            # OCI-specific terms
            'compartment_id', 'availability_domain', 'fault_domain',
            'shape', 'boot_volume', 'block_volume'
        ],
        'alicloud': [
            # Resource prefixes (more specific)
            'alicloud_', 'alibaba_',
            # Service names (more specific)
            'alicloud_instance', 'alicloud_vpc', 'alicloud_vswitch', 'alicloud_security_group',
            'alicloud_eip', 'alicloud_slb', 'alicloud_disk', 'alicloud_image', 'alicloud_snapshot',
            'alicloud_oss_bucket', 'alicloud_rds_instance', 'alicloud_kvstore_instance',
            # AliCloud-specific terms (more specific)
            'region_id', 'zone_id', 'internet_charge_type'
        ],
        'openstack': [
            # Resource prefixes
            'openstack_', 'neutron_', 'nova_', 'cinder_', 'glance_',
            # Service names
            'compute_instance_v2', 'networking_network_v2', 'networking_subnet_v2',
            'networking_router_v2', 'networking_floatingip_v2',
            'networking_secgroup_v2', 'blockstorage_volume_v2',
            'images_image_v2', 'identity_',
            # OpenStack-specific terms
            'tenant_name', 'tenant_id', 'auth_url', 'endpoint_type',
            'flavor', 'key_pair', 'availability_zone'
        ]
    }
    
    # Enhanced deployment type patterns
    DEPLOYMENT_PATTERNS = {
        'single': [
            'single', 'standalone', 'single-instance', 'single_instance',
            'solo', 'individual', 'basic', 'simple'
        ],
        'ha': [
            'ha', 'high-availability', 'high_availability', 'cluster',
            'active-passive', 'active_passive', 'active-active', 'active_active',
            'failover', 'redundant', 'clustered', 'dual', 'primary-secondary',
            'master-slave', 'leader-follower'
        ],
        'load_balancer': [
            'lb', 'load-balancer', 'load_balancer', 'elb', 'alb', 'nlb',
            'application-gateway', 'application_gateway', 'load-balancing',
            'load_balancing', 'balancer', 'distribute', 'frontend'
        ],
        'gwlb': [
            'gwlb', 'gateway-load-balancer', 'gateway_load_balancer',
            'gateway-lb', 'gateway_lb', 'transparent-proxy', 'transparent_proxy',
            'inline', 'bump-in-the-wire', 'security-gateway'
        ],
        'transit_gateway': [
            'tgw', 'transit-gateway', 'transit_gateway', 'transit-gw',
            'hub-and-spoke', 'hub_and_spoke', 'central-hub', 'central_hub',
            'network-hub', 'network_hub', 'routing-hub', 'routing_hub',
            'interconnect', 'peering-hub'
        ]
    }
    
    # Enhanced FortiGate version patterns
    FORTIGATE_VERSION_PATTERNS = [
        # Version patterns with dots
        r'6\.2(?:\.\d+)?', r'6\.4(?:\.\d+)?', r'7\.0(?:\.\d+)?', 
        r'7\.2(?:\.\d+)?', r'7\.4(?:\.\d+)?', r'7\.6(?:\.\d+)?',
        # Version patterns with 'v' prefix
        r'v6\.2(?:\.\d+)?', r'v6\.4(?:\.\d+)?', r'v7\.0(?:\.\d+)?',
        r'v7\.2(?:\.\d+)?', r'v7\.4(?:\.\d+)?', r'v7\.6(?:\.\d+)?',
        # Version patterns in quotes
        r'"6\.2(?:\.\d+)?"', r'"6\.4(?:\.\d+)?"', r'"7\.0(?:\.\d+)?"',
        r'"7\.2(?:\.\d+)?"', r'"7\.4(?:\.\d+)?"', r'"7\.6(?:\.\d+)?"',
        # Version patterns with FortiOS prefix
        r'fortios[_-]?6\.2(?:\.\d+)?', r'fortios[_-]?6\.4(?:\.\d+)?',
        r'fortios[_-]?7\.0(?:\.\d+)?', r'fortios[_-]?7\.2(?:\.\d+)?',
        r'fortios[_-]?7\.4(?:\.\d+)?', r'fortios[_-]?7\.6(?:\.\d+)?',
        # Version patterns in AMI names or image names
        r'fortigate[_-]?6\.2(?:\.\d+)?', r'fortigate[_-]?6\.4(?:\.\d+)?',
        r'fortigate[_-]?7\.0(?:\.\d+)?', r'fortigate[_-]?7\.2(?:\.\d+)?',
        r'fortigate[_-]?7\.4(?:\.\d+)?', r'fortigate[_-]?7\.6(?:\.\d+)?'
    ]
    
    def __init__(self, config: Dict = None):
        super().__init__(config)
        self._terraform_files: List[TerraformFile] = []
        self._python_files: List[PythonFile] = []
        self._documentation_files: List[DocumentationFile] = []
        
        # Initialize code parser for detailed file analysis
        self._code_parser = CodeParser(config)
        
        # Configuration options
        self.max_file_size = self.config.get('max_file_size', 10 * 1024 * 1024)  # 10MB
        self.exclude_dirs = set(self.config.get('exclude_dirs', [
            '.git', '.terraform', '__pycache__', 'node_modules', '.vscode', '.idea'
        ]))
        self.follow_symlinks = self.config.get('follow_symlinks', False)
    
    def analyze(self, repo_path: Path) -> RepositoryInventory:
        """Alias for scan_repository to match BaseAnalyzer interface."""
        return self.scan_repository(repo_path)
    
    def scan_repository(self, repo_path: Path) -> RepositoryInventory:
        """
        Scan repository and return complete inventory.
        
        Args:
            repo_path: Path to the repository root
            
        Returns:
            RepositoryInventory with all discovered files and metadata
            
        Raises:
            FileNotFoundError: If repository path doesn't exist
            PermissionError: If repository is not accessible
        """
        if not repo_path.exists():
            raise FileNotFoundError(f"Repository path does not exist: {repo_path}")
        
        if not repo_path.is_dir():
            raise ValueError(f"Repository path is not a directory: {repo_path}")
        
        logger.info(f"Starting repository scan: {repo_path}")
        
        # Clear previous results
        self._terraform_files.clear()
        self._python_files.clear()
        self._documentation_files.clear()
        
        try:
            # Recursively scan directory
            self._scan_directory(repo_path, repo_path)
            
            # Calculate repository size
            total_size = sum(
                f.file_size for f in self._terraform_files + self._python_files + self._documentation_files
            )
            
            # Create inventory
            inventory = RepositoryInventory(
                terraform_files=self._terraform_files.copy(),
                python_files=self._python_files.copy(),
                documentation_files=self._documentation_files.copy(),
                cloud_provider_configs=self._build_cloud_provider_configs(),
                total_files=len(self._terraform_files) + len(self._python_files) + len(self._documentation_files),
                repository_size=total_size,
                scan_timestamp=datetime.now()
            )
            
            logger.info(f"Repository scan completed. Found {inventory.total_files} files "
                       f"({len(self._terraform_files)} Terraform, {len(self._python_files)} Python, "
                       f"{len(self._documentation_files)} documentation)")
            
            return inventory
            
        except Exception as e:
            self.handle_error(e, "repository scanning")
            raise
    
    def _scan_directory(self, directory: Path, repo_root: Path) -> None:
        """
        Recursively scan a directory for files.
        
        Args:
            directory: Directory to scan
            repo_root: Root of the repository for relative path calculation
        """
        try:
            for item in directory.iterdir():
                # Skip excluded directories
                if item.is_dir() and item.name in self.exclude_dirs:
                    continue
                
                # Handle symbolic links
                if item.is_symlink() and not self.follow_symlinks:
                    continue
                
                if item.is_file():
                    self._process_file(item, repo_root)
                elif item.is_dir():
                    self._scan_directory(item, repo_root)
                    
        except PermissionError as e:
            logger.warning(f"Permission denied accessing directory: {directory}")
            self.handle_error(e, f"scanning directory {directory}")
        except Exception as e:
            logger.error(f"Error scanning directory {directory}: {e}")
            self.handle_error(e, f"scanning directory {directory}")
    
    def _process_file(self, file_path: Path, repo_root: Path) -> None:
        """
        Process a single file and categorize it.
        
        Args:
            file_path: Path to the file
            repo_root: Root of the repository for relative path calculation
        """
        try:
            # Get file metadata
            stat = file_path.stat()
            file_size = stat.st_size
            last_modified = datetime.fromtimestamp(stat.st_mtime)
            relative_path = str(file_path.relative_to(repo_root))
            
            # Skip files that are too large
            if file_size > self.max_file_size:
                logger.warning(f"Skipping large file: {relative_path} ({file_size} bytes)")
                return
            
            # Detect encoding
            encoding = self._detect_encoding(file_path)
            
            # Categorize by file extension
            suffix = file_path.suffix.lower()
            name = file_path.name.upper()
            
            if suffix in self.TERRAFORM_EXTENSIONS:
                terraform_file = self._create_terraform_file(
                    file_path, relative_path, file_size, last_modified, encoding
                )
                self._terraform_files.append(terraform_file)
                
            elif suffix in self.PYTHON_EXTENSIONS:
                python_file = self._create_python_file(
                    file_path, relative_path, file_size, last_modified, encoding
                )
                self._python_files.append(python_file)
                
            elif suffix in self.DOCUMENTATION_EXTENSIONS or name in self.SPECIAL_DOC_FILES:
                doc_file = self._create_documentation_file(
                    file_path, relative_path, file_size, last_modified, encoding
                )
                self._documentation_files.append(doc_file)
                
        except PermissionError as e:
            logger.warning(f"Permission denied accessing file: {file_path}")
            self.handle_error(e, f"processing file {file_path}")
        except Exception as e:
            logger.error(f"Error processing file {file_path}: {e}")
            self.handle_error(e, f"processing file {file_path}")
    
    def _detect_encoding(self, file_path: Path) -> str:
        """
        Detect file encoding using chardet.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Detected encoding or 'utf-8' as fallback
        """
        try:
            with open(file_path, 'rb') as f:
                raw_data = f.read(min(8192, os.path.getsize(file_path)))  # Read first 8KB
                result = chardet.detect(raw_data)
                return result.get('encoding', 'utf-8') or 'utf-8'
        except Exception as e:
            logger.debug(f"Could not detect encoding for {file_path}: {e}")
            return 'utf-8'
    
    def _create_terraform_file(self, file_path: Path, relative_path: str, 
                              file_size: int, last_modified: datetime, encoding: str) -> TerraformFile:
        """Create a TerraformFile object with enhanced metadata and analysis."""
        try:
            # Read file content for analysis
            content = self._read_file_content(file_path, encoding)
            
            # Detect primary cloud provider (most likely)
            cloud_provider = self._detect_cloud_provider(content, relative_path)
            
            # Detect all cloud providers (for multi-cloud configurations)
            all_cloud_providers = self._detect_all_cloud_providers(content, relative_path)
            
            # Detect primary deployment type (most likely)
            deployment_type = self._detect_deployment_type(content, relative_path)
            
            # Detect all deployment types (for complex configurations)
            all_deployment_types = self._detect_all_deployment_types(content, relative_path)
            
            # Detect FortiGate versions
            fortigate_versions = self._detect_fortigate_versions(content)
            
            # Parse the file to extract AST, modules, resources, etc.
            try:
                ast = self._code_parser.parse_terraform_file(file_path)
                variables = ast.variables if ast else []
                resources = ast.resources if ast else []
                outputs = ast.outputs if ast else []
                modules = ast.modules if ast else []
            except Exception as parse_error:
                logger.warning(f"Failed to parse {relative_path}: {parse_error}")
                ast = None
                variables = []
                resources = []
                outputs = []
                modules = []
            
            # Create enhanced TerraformFile with additional metadata
            terraform_file = TerraformFile(
                path=relative_path,
                cloud_provider=cloud_provider,
                deployment_type=deployment_type,
                fortigate_versions=fortigate_versions,
                ast=ast,
                variables=variables,
                resources=resources,
                outputs=outputs,
                modules=modules,
                file_size=file_size,
                last_modified=last_modified,
                encoding=encoding
            )
            
            # Add additional metadata as custom attributes
            terraform_file.all_cloud_providers = all_cloud_providers
            terraform_file.all_deployment_types = all_deployment_types
            terraform_file.content_summary = self._create_terraform_summary(content)
            terraform_file._content = content  # Store content for feature detection
            
            return terraform_file
            
        except Exception as e:
            logger.error(f"Error creating TerraformFile for {relative_path}: {e}")
            # Return minimal file info on error
            return TerraformFile(
                path=relative_path,
                cloud_provider='unknown',
                deployment_type='unknown',
                fortigate_versions=[],
                file_size=file_size,
                last_modified=last_modified,
                encoding=encoding,
                syntax_errors=[str(e)]
            )
    
    def _create_terraform_summary(self, content: str, max_lines: int = 10) -> str:
        """
        Create a summary of Terraform configuration content.
        
        Extracts key information like resources, providers, and variables.
        """
        lines = content.split('\n')
        summary_parts = []
        
        # Look for key Terraform blocks
        resource_count = content.lower().count('resource ')
        provider_count = content.lower().count('provider ')
        variable_count = content.lower().count('variable ')
        output_count = content.lower().count('output ')
        module_count = content.lower().count('module ')
        
        if resource_count > 0:
            summary_parts.append(f"{resource_count} resources")
        if provider_count > 0:
            summary_parts.append(f"{provider_count} providers")
        if variable_count > 0:
            summary_parts.append(f"{variable_count} variables")
        if output_count > 0:
            summary_parts.append(f"{output_count} outputs")
        if module_count > 0:
            summary_parts.append(f"{module_count} modules")
        
        # Add first few meaningful lines
        meaningful_lines = []
        for line in lines[:max_lines]:
            line = line.strip()
            if line and not line.startswith('#') and not line.startswith('//'):
                meaningful_lines.append(line)
                if len(meaningful_lines) >= 3:
                    break
        
        summary = "; ".join(summary_parts)
        if meaningful_lines:
            if summary:
                summary += " | "
            summary += " ".join(meaningful_lines)[:200]
        
        return summary[:300]  # Limit to 300 characters
    
    def _create_python_file(self, file_path: Path, relative_path: str,
                           file_size: int, last_modified: datetime, encoding: str) -> PythonFile:
        """Create a PythonFile object with metadata."""
        try:
            # Read file content for analysis
            content = self._read_file_content(file_path, encoding)
            
            # Determine purpose based on path and content
            purpose = self._determine_python_purpose(content, relative_path)
            
            # Extract basic information (functions and imports will be done by parser)
            functions = self._extract_python_functions(content)
            imports = self._extract_python_imports(content)
            
            return PythonFile(
                path=relative_path,
                purpose=purpose,
                functions=functions,
                imports=imports,
                file_size=file_size,
                last_modified=last_modified,
                encoding=encoding
            )
            
        except Exception as e:
            logger.error(f"Error creating PythonFile for {relative_path}: {e}")
            return PythonFile(
                path=relative_path,
                purpose='unknown',
                file_size=file_size,
                last_modified=last_modified,
                encoding=encoding,
                syntax_errors=[str(e)]
            )
    
    def _create_documentation_file(self, file_path: Path, relative_path: str,
                                  file_size: int, last_modified: datetime, encoding: str) -> DocumentationFile:
        """Create a DocumentationFile object with metadata."""
        try:
            # Read file content for summary
            content = self._read_file_content(file_path, encoding)
            
            # Determine document type
            doc_type = self._determine_doc_type(relative_path)
            
            # Create content summary (first few lines)
            content_summary = self._create_content_summary(content)
            
            return DocumentationFile(
                path=relative_path,
                type=doc_type,
                content_summary=content_summary,
                file_size=file_size,
                last_modified=last_modified,
                encoding=encoding
            )
            
        except Exception as e:
            logger.error(f"Error creating DocumentationFile for {relative_path}: {e}")
            return DocumentationFile(
                path=relative_path,
                type='unknown',
                file_size=file_size,
                last_modified=last_modified,
                encoding=encoding
            )
    
    def _read_file_content(self, file_path: Path, encoding: str) -> str:
        """
        Safely read file content with encoding handling.
        
        Args:
            file_path: Path to the file
            encoding: Detected encoding
            
        Returns:
            File content as string
        """
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                return f.read()
        except UnicodeDecodeError:
            # Fallback to utf-8 with error handling
            try:
                with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                    return f.read()
            except Exception:
                # Last resort: read as binary and decode with errors
                with open(file_path, 'rb') as f:
                    return f.read().decode('utf-8', errors='replace')
    
    def _detect_cloud_provider(self, content: str, file_path: str) -> str:
        """
        Detect cloud provider from file content and path with enhanced pattern matching.
        
        Returns the most likely cloud provider based on weighted scoring.
        """
        content_lower = content.lower()
        path_lower = file_path.lower()
        
        # Score each provider based on pattern matches
        provider_scores = {}
        
        for provider, patterns in self.CLOUD_PROVIDER_PATTERNS.items():
            score = 0
            matches = 0
            
            for pattern in patterns:
                # Content matches (higher weight)
                content_matches = content_lower.count(pattern)
                score += content_matches * 2
                matches += content_matches
                
                # Path matches (lower weight but still significant)
                if pattern in path_lower:
                    score += 1
                    matches += 1
            
            if matches > 0:
                provider_scores[provider] = score
        
        # Return the provider with the highest score
        if provider_scores:
            return max(provider_scores.items(), key=lambda x: x[1])[0]
        
        return 'unknown'
    
    def _detect_deployment_type(self, content: str, file_path: str) -> str:
        """
        Detect deployment type from file content and path with enhanced pattern matching.
        
        Returns the most likely deployment type based on weighted scoring.
        """
        content_lower = content.lower()
        path_lower = file_path.lower()
        
        # Score each deployment type based on pattern matches
        deployment_scores = {}
        
        for deployment_type, patterns in self.DEPLOYMENT_PATTERNS.items():
            score = 0
            matches = 0
            
            for pattern in patterns:
                # Content matches (higher weight)
                content_matches = content_lower.count(pattern)
                score += content_matches * 2
                matches += content_matches
                
                # Path matches (lower weight but still significant)
                if pattern in path_lower:
                    score += 1
                    matches += 1
            
            if matches > 0:
                deployment_scores[deployment_type] = score
        
        # Return the deployment type with the highest score
        if deployment_scores:
            return max(deployment_scores.items(), key=lambda x: x[1])[0]
        
        return 'unknown'
    
    def _detect_fortigate_versions(self, content: str) -> List[str]:
        """
        Detect FortiGate versions mentioned in content with enhanced pattern matching.
        
        Returns a list of unique versions found, normalized to standard format.
        """
        import re
        versions = []
        
        for pattern in self.FORTIGATE_VERSION_PATTERNS:
            matches = re.findall(pattern, content, re.IGNORECASE)
            versions.extend(matches)
        
        # Normalize versions and remove duplicates
        normalized_versions = []
        for version in versions:
            # Remove quotes, 'v' prefix, and 'fortios'/'fortigate' prefixes
            clean_version = re.sub(r'^["\']?(?:v|fortios[_-]?|fortigate[_-]?)?([0-9.]+)["\']?$', r'\1', version, flags=re.IGNORECASE)
            if clean_version and clean_version not in normalized_versions:
                normalized_versions.append(clean_version)
        
        return normalized_versions
    
    def _detect_all_cloud_providers(self, content: str, file_path: str) -> List[str]:
        """
        Detect all cloud providers mentioned in content and path.
        
        Returns a list of all cloud providers found, useful for multi-cloud configurations.
        """
        content_lower = content.lower()
        path_lower = file_path.lower()
        
        found_providers = []
        
        for provider, patterns in self.CLOUD_PROVIDER_PATTERNS.items():
            for pattern in patterns:
                if pattern in content_lower or pattern in path_lower:
                    if provider not in found_providers:
                        found_providers.append(provider)
                    break  # Found this provider, move to next
        
        return found_providers
    
    def _detect_all_deployment_types(self, content: str, file_path: str) -> List[str]:
        """
        Detect all deployment types mentioned in content and path.
        
        Returns a list of all deployment types found, useful for complex configurations.
        """
        content_lower = content.lower()
        path_lower = file_path.lower()
        
        found_types = []
        
        for deployment_type, patterns in self.DEPLOYMENT_PATTERNS.items():
            for pattern in patterns:
                if pattern in content_lower or pattern in path_lower:
                    if deployment_type not in found_types:
                        found_types.append(deployment_type)
                    break  # Found this type, move to next
        
        return found_types
        """Determine the purpose of a Python file."""
        content_lower = content.lower()
        path_lower = file_path.lower()
        
        # Prioritize path-based detection first
        if 'test' in path_lower or 'test_' in path_lower:
            return 'test'
        elif 'deploy' in path_lower:
            return 'deployment'
        elif 'util' in path_lower or 'helper' in path_lower:
            return 'utility'
        elif 'config' in path_lower:
            return 'configuration'
        elif 'script' in path_lower:
            return 'script'
        # Then check content-based detection
        elif 'deploy' in content_lower:
            return 'deployment'
        elif 'config' in content_lower:
            return 'configuration'
        elif '__main__' in content:
            return 'script'
        else:
            return 'unknown'
    
    def _extract_python_functions(self, content: str) -> List[str]:
        """Extract function names from Python content."""
        import re
        functions = []
        
        # Simple regex to find function definitions
        pattern = r'def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\('
        matches = re.findall(pattern, content)
        functions.extend(matches)
        
        return functions
    
    def _extract_python_imports(self, content: str) -> List[str]:
        """Extract import statements from Python content."""
        import re
        imports = []
        
        # Find import statements
        import_patterns = [
            r'import\s+([a-zA-Z_][a-zA-Z0-9_.]*)',
            r'from\s+([a-zA-Z_][a-zA-Z0-9_.]*)\s+import'
        ]
        
        for pattern in import_patterns:
            matches = re.findall(pattern, content)
            imports.extend(matches)
        
        return list(set(imports))  # Remove duplicates
    
    def _determine_python_purpose(self, content: str, file_path: str) -> str:
        """Determine the purpose of a Python file based on content and path."""
        path_lower = file_path.lower()
        content_lower = content.lower()
        
        # Check path patterns first
        if 'test' in path_lower:
            return 'test'
        elif 'deploy' in path_lower or 'deployment' in path_lower:
            return 'deployment'
        elif 'util' in path_lower or 'helper' in path_lower:
            return 'utility'
        elif 'config' in path_lower or 'setting' in path_lower:
            return 'configuration'
        elif 'script' in path_lower:
            return 'script'
        
        # Check content patterns
        if any(keyword in content_lower for keyword in ['terraform', 'boto3', 'azure', 'gcp']):
            if 'def deploy' in content_lower or 'def main' in content_lower:
                return 'deployment'
            elif 'class' in content_lower and 'config' in content_lower:
                return 'configuration'
            else:
                return 'automation'
        elif 'def test_' in content_lower or 'import pytest' in content_lower:
            return 'test'
        elif 'if __name__ == "__main__"' in content_lower:
            return 'script'
        else:
            return 'utility'
    
    def _determine_doc_type(self, file_path: str) -> str:
        """Determine documentation type from file path."""
        path_lower = file_path.lower()
        
        if 'readme' in path_lower:
            return 'README'
        elif 'guide' in path_lower or 'tutorial' in path_lower:
            return 'guide'
        elif 'api' in path_lower:
            return 'api'
        elif 'changelog' in path_lower or 'history' in path_lower:
            return 'changelog'
        elif 'license' in path_lower:
            return 'license'
        else:
            return 'documentation'
    
    def _create_content_summary(self, content: str, max_lines: int = 5) -> str:
        """Create a summary of document content."""
        lines = content.split('\n')
        summary_lines = []
        
        for line in lines[:max_lines]:
            line = line.strip()
            if line and not line.startswith('#'):  # Skip empty lines and markdown headers
                summary_lines.append(line)
                if len(summary_lines) >= 3:  # Limit to 3 meaningful lines
                    break
        
        return ' '.join(summary_lines)[:200]  # Limit to 200 characters
    
    def _build_cloud_provider_configs(self) -> Dict[str, CloudProviderConfig]:
        """Build enhanced cloud provider configuration mapping with detailed analysis."""
        configs = {}
        
        # Group Terraform files by cloud provider
        provider_files = {}
        for tf_file in self._terraform_files:
            provider = tf_file.cloud_provider
            if provider not in provider_files:
                provider_files[provider] = []
            provider_files[provider].append(tf_file)
            
            # Also include files that mention this provider in all_cloud_providers
            if hasattr(tf_file, 'all_cloud_providers'):
                for additional_provider in tf_file.all_cloud_providers:
                    if additional_provider != provider:  # Don't duplicate primary provider
                        if additional_provider not in provider_files:
                            provider_files[additional_provider] = []
                        if tf_file not in provider_files[additional_provider]:
                            provider_files[additional_provider].append(tf_file)
        
        # Create CloudProviderConfig for each provider
        for provider, files in provider_files.items():
            if provider == 'unknown':
                continue
                
            # Collect deployment scenarios
            deployment_scenarios = set()
            for f in files:
                if f.deployment_type != 'unknown':
                    deployment_scenarios.add(f.deployment_type)
                # Also add from all_deployment_types if available
                if hasattr(f, 'all_deployment_types'):
                    deployment_scenarios.update(f.all_deployment_types)
            
            # Collect supported versions
            supported_versions = set()
            for f in files:
                supported_versions.update(f.fortigate_versions)
            
            # Collect configuration files
            configuration_files = [f.path for f in files]
            
            # Identify specific features based on content analysis
            specific_features = self._identify_provider_features(provider, files)
            
            configs[provider] = CloudProviderConfig(
                provider=provider,
                deployment_scenarios=list(deployment_scenarios),
                supported_versions=sorted(list(supported_versions)),
                specific_features=specific_features,
                configuration_files=configuration_files
            )
        
        return configs
    
    def _identify_provider_features(self, provider: str, files: List[TerraformFile]) -> List[str]:
        """
        Identify specific features used for a cloud provider based on file analysis.
        
        Args:
            provider: Cloud provider name
            files: List of Terraform files for this provider
            
        Returns:
            List of specific features identified
        """
        features = set()
        
        # Provider-specific feature patterns
        feature_patterns = {
            'aws': {
                'vpc': ['aws_vpc', 'vpc_id'],
                'ec2': ['aws_instance', 'instance_type'],
                'elb': ['aws_elb', 'aws_lb', 'load_balancer'],
                'security_groups': ['aws_security_group', 'security_group_ids'],
                'iam': ['aws_iam_', 'iam_instance_profile'],
                'route53': ['aws_route53_', 'hosted_zone'],
                'cloudformation': ['aws_cloudformation_'],
                'lambda': ['aws_lambda_'],
                'rds': ['aws_db_', 'aws_rds_'],
                'transit_gateway': ['aws_ec2_transit_gateway'],
                'gwlb': ['aws_lb_target_group', 'gateway']
            },
            'azure': {
                'virtual_network': ['azurerm_virtual_network', 'virtual_network'],
                'virtual_machine': ['azurerm_virtual_machine', 'azurerm_linux_virtual_machine'],
                'load_balancer': ['azurerm_lb', 'load_balancer'],
                'application_gateway': ['azurerm_application_gateway'],
                'network_security_group': ['azurerm_network_security_group'],
                'storage': ['azurerm_storage_account'],
                'key_vault': ['azurerm_key_vault'],
                'resource_group': ['azurerm_resource_group']
            },
            'gcp': {
                'compute': ['google_compute_instance', 'google_compute_'],
                'network': ['google_compute_network', 'google_compute_subnetwork'],
                'firewall': ['google_compute_firewall'],
                'load_balancer': ['google_compute_forwarding_rule', 'google_compute_target_pool'],
                'storage': ['google_storage_bucket'],
                'iam': ['google_project_iam_', 'google_service_account']
            }
        }
        
        if provider in feature_patterns:
            for tf_file in files:
                try:
                    # Use stored content if available, otherwise try to read the file
                    if hasattr(tf_file, '_content') and tf_file._content:
                        content = tf_file._content
                    else:
                        # Try to read the file if path exists
                        file_path = Path(tf_file.path)
                        if not file_path.is_absolute():
                            # Skip relative paths for now
                            continue
                        content = self._read_file_content(file_path, tf_file.encoding)
                    
                    content_lower = content.lower()
                    
                    for feature_name, patterns in feature_patterns[provider].items():
                        for pattern in patterns:
                            if pattern in content_lower:
                                features.add(feature_name)
                                break
                except Exception as e:
                    logger.debug(f"Error processing file {tf_file.path} for feature detection: {e}")
                    continue
        
        return sorted(list(features))
    
    def get_terraform_files(self) -> List[TerraformFile]:
        """Get all discovered Terraform files."""
        return self._terraform_files
    
    def get_python_files(self) -> List[PythonFile]:
        """Get all discovered Python files."""
        return self._python_files
    
    def get_documentation_files(self) -> List[DocumentationFile]:
        """Get all discovered documentation files."""
        return self._documentation_files
    
    def get_cloud_provider_configs(self) -> Dict[str, List[TerraformFile]]:
        """Get configurations grouped by cloud provider."""
        result = {}
        for tf_file in self._terraform_files:
            provider = tf_file.cloud_provider
            if provider not in result:
                result[provider] = []
            result[provider].append(tf_file)
        return result