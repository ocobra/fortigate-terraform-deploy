"""
Analysis components for the FortiGate Terraform Analysis System.

This module contains various analyzer components including security analysis,
best practices validation, architecture mapping, gap detection, and version analysis.
"""

from .security_analyzer import SecurityAnalyzer
from .best_practices_validator import BestPracticesValidator
from .architecture_mapper import ArchitectureMapper
from .gap_detector import GapDetector
from .version_analyzer import VersionAnalyzer
from .analysis_engine import AnalysisEngine

__all__ = [
    "SecurityAnalyzer",
    "BestPracticesValidator", 
    "ArchitectureMapper",
    "GapDetector",
    "VersionAnalyzer",
    "AnalysisEngine",
]