# Common targets come from sowwic/makefiles, fetched into .make/ (commit it). `make update-make` fetches them again.
APP_NAME = nyx
PACKAGE_NAME = nyx
TEST_OUTPUT_DIR = test_output
BUILD_PREREQS = qrc update-version

MAKEFILES_REF ?= v1
MAKEFILES_URL ?= https://raw.githubusercontent.com/sowwic/makefiles/$(MAKEFILES_REF)
MAKEFILES_MODULES = general/python

.make/%.mk:
	@mkdir -p $(dir $@)
	@curl -fsSL $(MAKEFILES_URL)/$*.mk -o $@
include $(MAKEFILES_MODULES:%=.make/%.mk)

# Building the application lives in scripts/build.py so it works without make (Windows).
BUILD_SCRIPT = uv run python scripts/build.py

.PHONY: pstats
pstats: ## Open profiler stats dir using snakeviz
	snakeviz "$$(python -c 'from nyx.static.paths import PROFILING_DIR; print(PROFILING_DIR)')"

.PHONY: qrc
qrc: ## Generates Python resources from the Qt resource files
	@$(BUILD_SCRIPT) qrc

.PHONY: icons
icons: ## Generate the app icon file of this platform into build/icons
	@$(BUILD_SCRIPT) icons

.PHONY: build-app
build-app: ## Build the standalone app with PyInstaller: dist/nyx.app (macOS) or dist/nyx
	@$(BUILD_SCRIPT) build-app

.PHONY: archive-app
archive-app: ## Build the app and zip it (tar.gz on Linux): dist/nyx-<version>-<os>-<arch>
	@$(BUILD_SCRIPT) archive-app

.PHONY: test-app
test-app: ## Run the built app's executables: help, missing file, a real stage
	@$(BUILD_SCRIPT) test-app

.PHONY: install-app
install-app: ## Copy dist/nyx.app into /Applications (macOS)
	@$(BUILD_SCRIPT) install-app

.PHONY: install-cli
install-cli: ## Link the nyx and nyx-run-stage commands of the app into /usr/local/bin
	@$(BUILD_SCRIPT) install-cli

.PHONY: config-file-path
config-file: ## Print out config file path
	@(python -c 'from nyx.static.paths import USER_CONFIG_FILE_PATH; print(USER_CONFIG_FILE_PATH)')

.PHONY: launch
launch-editor:  ## Launch the editor
	python ./src/nyx/main.py
