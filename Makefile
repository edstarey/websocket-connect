.PHONY: install install-dev test clean uninstall

install:
	python3 -m pip install --break-system-packages -r requirements/requirements.txt

install-dev:
	python3 -m pip install --break-system-packages -r requirements/requirements-dev.txt

test:
	pytest tests/

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf build/ dist/ *.egg-info/

uninstall:
	python3 -m pip uninstall --break-system-packages -y -r requirements/requirements.txt
	python3 -m pip uninstall --break-system-packages -y -r requirements/requirements-dev.txt