# Common targets of a Python project: lint, test, docs, build, version, release.
#
# Set before including (all optional unless said):
#   APP_NAME, PACKAGE_NAME   required, project and import names
#   RELEASE_BRANCH, DEVELOP_BRANCH, GH_WORKFLOWS_REF
#   LINT_PATHS               paths of ruff (default: src tests)
#   PYTEST_CMD, PYTEST_PDB_CMD   commands of `pytest` and `pytest-pdb`
#   BUILD_PREREQS            targets `build` needs first, e.g. qrc
# Add steps to `check` or `clean` in the project Makefile with a double-colon rule, e.g.
# `clean:: ; rm -rf node_modules`.

SHELL := /bin/bash

VERSION := $(shell tr -d '\r\n' < VERSION)
DIST_DIR ?= dist
BUILD_DIR ?= build
MKDOCS_SITE_DIR ?= site
TEST_OUTPUT_DIR ?= .test_output
RELEASE_BRANCH ?= main
DEVELOP_BRANCH ?= develop
GH_WORKFLOWS_REF ?= v1
LINT_PATHS ?= src tests
PYTEST_CMD ?= uv run pytest tests
PYTEST_PDB_CMD ?= uv run pytest -vvv --pdb --log-cli-level=DEBUG tests
BUILD_PREREQS ?=

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
	@grep -hE '^[a-zA-Z0-9_-]+:.*?##' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS=":.*?##"}; {printf "  %-15s %s\n", $$1, $$2}'
	@echo ""

.PHONY: clean
clean:: ## Remove build artifacts, cache, and temporary files
	$(call banner, Cleaning project...)
	@rm -rf .pytest_cache
	@rm -rf .ruff_cache
	@rm -rf __pycache__
	@rm -rf .coverage
	@rm -rf src/**/__pycache__
	@rm -rf tests/**/__pycache__
	@rm -rf $(BUILD_DIR)
	@rm -rf $(DIST_DIR)
	@rm -rf $(TEST_OUTPUT_DIR)
	@rm -rf $(MKDOCS_SITE_DIR)
	@printf "$(GREEN)Clean up complete.$(RESET)\n"

.PHONY: lint
lint: ## Run the Ruff linter on source and test files
	$(call banner, Running Ruff linter...)
	@uv run ruff check $(LINT_PATHS)

.PHONY: lint-fix
lint-fix: ## Run the Ruff linter on source and test files and apply fixes
	$(call banner, Running Ruff linter with fixes...)
	@uv run ruff check --fix $(LINT_PATHS)

.PHONY: format
format: ## Run the Ruff formatter on source and test files
	$(call banner, Running Ruff formatter...)
	@uv run ruff format $(LINT_PATHS)

.PHONY: pytest
pytest: ## Run pytest on tests directory
	$(call banner, Running pytest...)
	@$(PYTEST_CMD)

.PHONY: pytest-pdb
pytest-pdb: ## Run pytest with pdb on failure
	$(call banner, Cleaning pytest output dir...)
	@rm -rf $(TEST_OUTPUT_DIR)
	$(call banner, Running pytest with pdb...)
	@$(PYTEST_PDB_CMD)

.PHONY: mkdocs
mkdocs: ## Run MkDocs development server
	$(call banner, Starting MkDocs development server...)
	@uv run mkdocs serve

.PHONY: check
check:: lint pytest ## Run all checks (linting and testing)

.PHONY: build
build: $(BUILD_PREREQS) ## Build the package using uv
	$(call banner, Building $(APP_NAME)...)
	@uv build

.PHONY: update-version
update-version: ## Update the version in pyproject.toml to match the VERSION file
	$(call banner, Updating version in pyproject.toml...)
	@printf "$(CYAN)==>$(RESET) Updating pyproject.toml version to %s\n" "$(VERSION)"
	@uv version $(VERSION)

.PHONY: release
release: ## Tag, push and back-merge a release: make release VERSION=x.y.z [RELEASE_TITLE=...]
	$(if $(VERSION),,$(error VERSION is required, e.g. make release VERSION=1.2.3))
	$(call banner, Releasing $(APP_NAME) v$(VERSION)...)
	@curl -fsSL https://raw.githubusercontent.com/sowwic/gh-workflows/$(GH_WORKFLOWS_REF)/scripts/release.py | \
		python3 - $(VERSION) --release-branch $(RELEASE_BRANCH) --develop-branch $(DEVELOP_BRANCH) $(if $(RELEASE_TITLE),--title "$(RELEASE_TITLE)")

.PHONY: update-make
update-make: ## Fetch the shared makefile modules again (at MAKEFILES_REF)
	$(call banner, Fetching makefile modules $(MAKEFILES_REF)...)
	@rm -rf .make
	@$(MAKE) --no-print-directory $(MAKEFILES_MODULES:%=.make/%.mk)
