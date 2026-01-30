"""
Reporting components for the FortiGate Terraform Analysis System.

This module contains components responsible for generating analysis reports,
improvement tasks, and exporting results in various formats.
"""

from .report_generator import ReportGenerator
from .task_generator import TaskGenerator

__all__ = ["ReportGenerator", "TaskGenerator"]