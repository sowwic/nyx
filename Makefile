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

clean:
	$(call banner, Cleaning project...)
	@rm -rf .pytest_cache
	@rm -rf __pycache__
	@rm -rf src/**/__pycache__
	@rm -rf tests/**/__pycache__
	@rm -rf $(BUILD_DIR)
	@rm -rf $(DIST_DIR)
	@rm -rf $(TEST_OUTPUT_DIR)
	@printf "$(GREEN)Clean up complete.$(RESET)\n"

lint:
	$(call banner, Running flake8 linting...)
	@poetry run flake8 src tests || true

pytest:
	$(call banner, Running pytest...)
	@poetry run pytest tests

check: lint pytest

qrc:
	$(call banner, Generating QRC resources...)
	@pyside6-rcc resources/resources.qrc -o resources/resources_rc.py
	@printf "$(GREEN)QRC generation complete.$(RESET)\n"

build: qrc update-version
	$(call banner, Building $(APP_NAME)...)
	@poetry build

update-version:
	@VERSION=$$(cat VERSION); \
	printf "$(CYAN)==>$(RESET) Updating pyproject.toml version to %s\n" "$$VERSION"; \
	poetry version $$VERSION
