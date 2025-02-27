.PHONY: venv install install-dev test coverage clean help

# Create a fresh virtual environment (removes any existing venv)
venv:
	@echo "Creating virtual environment..."
	@rm -rf venv
	python3 -m venv venv

# Install production dependencies inside the virtual environment
install: venv ## Install production dependencies
	@echo "Upgrading pip and installing production dependencies..."
	venv/bin/pip install --upgrade pip
	venv/bin/pip install -r requirements/requirements.txt

# Install development dependencies (includes production deps)
install-dev: venv ## Install development dependencies
	@echo "Upgrading pip and installing development dependencies..."
	venv/bin/pip install --upgrade pip
	venv/bin/pip install -r requirements/requirements-dev.txt

# Run all unit tests using pytest from the virtual environment
test: ## Run unit tests
	venv/bin/pytest -v

# Run tests with coverage report using pytest-cov
coverage: ## Run tests with coverage report
	venv/bin/pytest -v --cov-report=term-missing --cov .

clean:
	@echo "Cleaning up virtual environment and __pycache__ directories..."
	rm -rf venv
	find . -type d -name "__pycache__" -exec rm -rf {} +

help:
	@echo "Makefile commands:"
	@echo "  venv         - Create a fresh virtual environment"
	@echo "  install      - Install production dependencies"
	@echo "  install-dev  - Install development dependencies"
	@echo "  test         - Run unit tests"
	@echo "  coverage     - Run tests with coverage report"
	@echo "  clean        - Remove the virtual environment and clean caches"