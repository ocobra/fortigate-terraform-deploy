# Makefile for FortiGate Terraform Analysis System

.PHONY: help install install-dev test test-unit test-property test-integration lint format type-check clean docs build

# Default target
help:
	@echo "Available targets:"
	@echo "  install       - Install package and dependencies"
	@echo "  install-dev   - Install package with development dependencies"
	@echo "  test          - Run all tests"
	@echo "  test-unit     - Run unit tests only"
	@echo "  test-property - Run property-based tests only"
	@echo "  test-integration - Run integration tests only"
	@echo "  lint          - Run linting checks"
	@echo "  format        - Format code with black and isort"
	@echo "  type-check    - Run type checking with mypy"
	@echo "  clean         - Clean build artifacts"
	@echo "  docs          - Build documentation"
	@echo "  build         - Build package"
	@echo "  pre-commit    - Install pre-commit hooks"

# Installation targets
install:
	pip install -e .

install-dev:
	pip install -e ".[dev]"
	pre-commit install

# Testing targets
test:
	pytest

test-unit:
	pytest -m "unit or not (property or integration)"

test-property:
	pytest -m "property" --hypothesis-show-statistics

test-integration:
	pytest -m "integration"

# Code quality targets
lint:
	flake8 fortigate_analysis tests
	black --check fortigate_analysis tests
	isort --check-only fortigate_analysis tests

format:
	black fortigate_analysis tests
	isort fortigate_analysis tests

type-check:
	mypy fortigate_analysis

# Utility targets
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

docs:
	cd docs && make html

build:
	python -m build

pre-commit:
	pre-commit install
	pre-commit run --all-files

# Development workflow
dev-setup: install-dev pre-commit
	@echo "Development environment setup complete!"

check: lint type-check test
	@echo "All checks passed!"