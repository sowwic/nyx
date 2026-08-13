SHELL := /bin/bash

APP_NAME = nyx
DIST_DIR = dist
BUILD_DIR = build
TEST_OUTPUT_DIR = .test_output
APP_PATH = $(DIST_DIR)/$(APP_NAME).app
APPLICATIONS_DIR = /Applications

# Colors
BLUE := \033[34m
GREEN := \033[32m
YELLOW := \033[33m
RED := \033[31m
MAGENTA := \033[35m
CYAN := \033[36m
RESET := \033[0m

# Banner helper
define banner
	@printf "$(CYAN)==>$(RESET) $(1)\n"
endef

.PHONY: help
help: ## Show this help message
	@echo "Available make targets:"
	@echo ""
	@grep -E '^[a-zA-Z0-9_-]+:.*?##' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS=":.*?##"}; {printf "  %-15s %s\n", $$1, $$2}'
	@echo ""

.PHONY: clean
clean: ## Cleans up build artifacts, test outputs, and caches
	$(call banner, Cleaning project...)
	@rm -rf build
	@rm -rf dist
	@rm -rf site
	@rm -rf .pytest_cache
	@rm -rf .ruff_cache
	@rm -rf .coverage
	@rm -rf __pycache__
	@rm -rf src/**/__pycache__
	@rm -rf tests/**/__pycache__
	@rm -rf $(BUILD_DIR)
	@rm -rf $(DIST_DIR)
	@rm -rf $(TEST_OUTPUT_DIR)
	@printf "$(GREEN)Clean up complete.$(RESET)\n"

.PHONY: lint
lint: ## Runs the Ruff linter on source and test files
	$(call banner, Running Ruff linter...)
	@uv run ruff check src tests || true

.PHONY: lint
lint-fix: ## Runs the Ruff linter on source and test files
	$(call banner, Running Ruff linter...)
	@uv run ruff check --fix src tests || true

.PHONY: format
format: ## Runs the Ruff formatter on source and test files
	$(call banner, Running Ruff formatter...)
	@uv run ruff format src tests

.PHONY: pytest
pytest: ## Runs pytest on the tests directory
	$(call banner, Running pytest...)
	@uv run pytest tests

.PHONY: pytest-pdb
pytest-pdb: ## Runs pytest with pdb enabled for debugging
	$(call banner, Cleaning pytest output dir...)
	@rm -rf $(TEST_OUTPUT_DIR)
	$(call banner, Running pytest with pdb...)
	@uv run pytest -vvv --pdb --log-cli-level=DEBUG tests

.PHONY: mkdocs
mkdocs: ## Serves the MkDocs documentation locally
	$(call banner, Building MkDocs documentation...)
	@uv run mkdocs serve

.PHONY: check
check: lint pytest ## Runs linting and tests

.PHONY: qrc
qrc: ## Generates Python resources from the Qt resource file
	$(call banner, Generating QRC resources...)
	@pyside6-rcc src/nyx/resources/resources.qrc -o src/nyx/resources/resources_rc.py
	@printf "$(GREEN)QRC generation complete.$(RESET)\n"

.PHONY: build
build: qrc update-version ## Builds the application using uv
	$(call banner, Building $(APP_NAME)...)
	@uv build

.PHONY: update-version
update-version: ## Updates the version in pyproject.toml based on the VERSION file
	@VERSION=$$(cat VERSION); \
	printf "$(CYAN)==>$(RESET) Updating pyproject.toml version to %s\n" "$$VERSION"; \
	uv version $$VERSION

.PHONY: launch
launch-editor:  ## Launch the editor
	python ./src/nyx/main.py
