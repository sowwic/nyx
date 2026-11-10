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

.PHONY: pstats
pstats: ## Open profiler stats dir using snakeviz
	snakeviz "$$(python -c 'from nyx.static.paths import PROFILING_DIR; print(PROFILING_DIR)')"

.PHONY: qrc
qrc: ## Generates Python resources from the Qt resource file
	$(call banner, Generating QRC resources...)
	@pyside6-rcc src/nyx/resources/resources.qrc -o src/nyx/resources/resources_rc.py
	$(call banner, Generating NyxStdlib QRC resources...)
	@pyside6-rcc src/nyx/stdlib/resources/resources.qrc -o src/nyx/stdlib/resources/resources_rc.py 
	@printf "$(GREEN)QRC generation complete.$(RESET)\n"

.PHONY: config-file-path
config-file: ## Print out config file path
	@(python -c 'from nyx.static.paths import USER_CONFIG_FILE_PATH; print(USER_CONFIG_FILE_PATH)')

.PHONY: launch
launch-editor:  ## Launch the editor
	python ./src/nyx/main.py
