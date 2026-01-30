"""
FortiGate Terraform Analysis System

A comprehensive codebase analysis tool for FortiGate Terraform deployments.
Analyzes configurations across multiple cloud providers, identifies security
vulnerabilities, validates best practices, and generates actionable improvement tasks.
"""

__version__ = "0.1.0"
__author__ = "FortiGate Analysis Team"

from .models import (
    TerraformFile,
    SecurityIssue,
    AnalysisReport,
    ImprovementTask,
    RepositoryInventory,
    ArchitectureMap,
)

__all__ = [
    "TerraformFile",
    "SecurityIssue", 
    "AnalysisReport",
    "ImprovementTask",
    "RepositoryInventory",
    "ArchitectureMap",
]