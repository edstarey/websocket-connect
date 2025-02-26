.PHONY: install install-dev uninstall test run lint clean help package-chat-api package-ws-disconnect

# Create virtual environment and install production dependencies
install:
	@echo "Creating venv and installing production dependencies..."
	python3 -m venv venv
	venv/bin/pip install --upgrade pip
	venv/bin/pip install -r requirements/requirements.txt

# Create virtual environment and install development dependencies
install-dev:
	@echo "Creating venv and installing development dependencies..."
	python3 -m venv venv
	venv/bin/pip install --upgrade pip
	venv/bin/pip install -r requirements/requirements-dev.txt

# Remove the virtual environment
uninstall:
	@echo "Removing virtual environment..."
	rm -rf venv

# Run tests using pytest (with PYTHONPATH set so modules are found)
test:
	@echo "Running tests..."
	PYTHONPATH=. venv/bin/python -m pytest tests --maxfail=1 --disable-warnings -q

# Run the application (loads environment variables from .env)
run:
	@echo "Starting application with uvicorn..."
	@export $$(grep -v '^#' .env | xargs) && PYTHONPATH=$(PWD) venv/bin/uvicorn app.main:app --host 0.0.0.0 --reload

# Run code linters/formatters
lint:
	@echo "Running linters and formatters..."
	venv/bin/flake8 .
	venv/bin/black --check .
	venv/bin/isort --check-only .

# Package the chat-api lambda (e.g., for $connect)
package-chat-api:
	@echo "Packaging chat-api lambda..."
	@mkdir -p package
	zip -j package/chat_api.zip src/chat_api.py

# Package the ws-disconnect lambda
package-ws-disconnect:
	@echo "Packaging ws-disconnect lambda..."
	@mkdir -p package
	zip -j package/ws_disconnect.zip src/ws_disconnect.py

# Clean up __pycache__ directories and .pyc files
clean:
	@echo "Cleaning up __pycache__ directories..."
	find . -type d -name "__pycache__" -exec rm -rf {} +
	@echo "Removing .pyc files..."
	find . -name "*.pyc" -delete

# Display help message
help:
	@echo "Makefile commands:"
	@echo "  install              - Create virtual environment and install production dependencies"
	@echo "  install-dev          - Create virtual environment and install development dependencies"
	@echo "  uninstall            - Remove the virtual environment"
	@echo "  test                 - Run tests using pytest"
	@echo "  run                  - Start the application with uvicorn"
	@echo "  lint                 - Run code linters (flake8, black, isort)"
	@echo "  package-chat-api     - Package the chat-api lambda for deployment"
	@echo "  package-ws-disconnect- Package the ws-disconnect lambda for deployment"
	@echo "  clean                - Clean up __pycache__ directories and .pyc files"