"""
Command-line interface for the FortiGate Terraform Analysis System.
"""

import click
from pathlib import Path
from typing import Optional

from .analyzer.analysis_engine import AnalysisEngine
from .scanner.repository_scanner import RepositoryScanner
from .parser.code_parser import CodeParser
from .analyzer.security_analyzer import SecurityAnalyzer
from .analyzer.best_practices_validator import BestPracticesValidator
from .analyzer.architecture_mapper import ArchitectureMapper
from .analyzer.gap_detector import GapDetector
from .reporter.report_generator import ReportGenerator
from .reporter.task_generator import TaskGenerator


@click.group()
@click.version_option(version="0.1.0")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
@click.pass_context
def cli(ctx, verbose):
    """FortiGate Terraform Analysis System - Comprehensive codebase analysis tool."""
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose


@cli.command()
@click.argument("repository_path", type=click.Path(exists=True, path_type=Path))
@click.option("--output", "-o", type=click.Path(path_type=Path), help="Output directory for reports")
@click.option("--format", "-f", multiple=True, default=["json"], 
              type=click.Choice(["json", "html", "markdown", "csv"]),
              help="Output format(s)")
@click.option("--config", "-c", type=click.Path(exists=True, path_type=Path), 
              help="Configuration file path")
@click.pass_context
def analyze(ctx, repository_path: Path, output: Optional[Path], format: tuple, config: Optional[Path]):
    """Analyze a FortiGate Terraform repository."""
    verbose = ctx.obj.get("verbose", False)
    
    if verbose:
        click.echo(f"Analyzing repository: {repository_path}")
        click.echo(f"Output formats: {', '.join(format)}")
    
    # Create analysis engine and components
    engine = AnalysisEngine()
    
    # Set up components (dependency injection)
    engine.set_scanner(RepositoryScanner())
    engine.set_parser(CodeParser())
    engine.set_security_analyzer(SecurityAnalyzer())
    engine.set_best_practices_validator(BestPracticesValidator())
    engine.set_architecture_mapper(ArchitectureMapper())
    engine.set_gap_detector(GapDetector())
    engine.set_task_generator(TaskGenerator())
    engine.set_report_generator(ReportGenerator())
    
    try:
        # Perform analysis
        if verbose:
            click.echo("Starting repository analysis...")
        
        report = engine.analyze_repository(repository_path)
        
        if verbose:
            click.echo("Analysis completed successfully!")
            click.echo(f"Analysis timestamp: {report.analysis_timestamp}")
            click.echo(f"Total files analyzed: {report.repository_inventory.total_files}")
        
        # TODO: Export reports in requested formats
        click.echo("Analysis completed. Report generation will be implemented in future tasks.")
        
    except Exception as e:
        click.echo(f"Error during analysis: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.argument("report_path", type=click.Path(exists=True, path_type=Path))
@click.option("--format", "-f", default="json", 
              type=click.Choice(["json", "html", "markdown", "csv"]),
              help="Report format")
@click.pass_context
def report(ctx, report_path: Path, format: str):
    """Generate reports from analysis results."""
    verbose = ctx.obj.get("verbose", False)
    
    if verbose:
        click.echo(f"Generating {format} report from: {report_path}")
    
    # TODO: Implement report generation from saved analysis results
    click.echo("Report generation will be implemented in future tasks.")


@cli.command()
@click.argument("report_path", type=click.Path(exists=True, path_type=Path))
@click.option("--priority", "-p", type=click.Choice(["HIGH", "MEDIUM", "LOW"]),
              help="Filter tasks by priority")
@click.option("--category", "-c", type=click.Choice(["SECURITY", "BEST_PRACTICES", "ARCHITECTURE", "DOCUMENTATION"]),
              help="Filter tasks by category")
@click.pass_context
def tasks(ctx, report_path: Path, priority: Optional[str], category: Optional[str]):
    """List and manage improvement tasks."""
    verbose = ctx.obj.get("verbose", False)
    
    if verbose:
        click.echo(f"Loading tasks from: {report_path}")
        if priority:
            click.echo(f"Filtering by priority: {priority}")
        if category:
            click.echo(f"Filtering by category: {category}")
    
    # TODO: Implement task listing and management
    click.echo("Task management will be implemented in future tasks.")


def main():
    """Main entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main()