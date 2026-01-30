"""
Code parsing components for the FortiGate Terraform Analysis System.

This module contains components responsible for parsing Terraform configurations
and Python scripts, extracting AST representations and metadata.
"""

from .code_parser import CodeParser

__all__ = ["CodeParser"]