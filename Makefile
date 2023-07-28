SHELL := /bin/bash
MAIN_FILE_PATH := ./src/nyx/main.py


clean:
	rm -rf .venv
	rm -rf .tox
	rm -rf .test_output
	rm -rf .pytest_cache
	rm -rf .coverage

lint:
	flake8 src tests

venv:
	@echo "Creating virtual env..."
	py -3.10 -m venv .venv
	. .venv/scripts/activate

install-dep:
	@echo "Installing packages..."
	python -m pip install -r dev_requirements.txt

install-nyx:
	python -m pip install -e .

dev: venv install-dep install-nyx

documentation:
	sphinx-apidoc -o docs .

test:
	python -m pytest

launch:
	python $(MAIN_FILE_PATH)

launch-dev: dev launch