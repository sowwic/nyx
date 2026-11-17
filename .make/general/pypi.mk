# PyPI publishing: `pypi-publish` builds the package and uploads it with uv.
# `pypi-publish-dev` does the same against TestPyPI.
#
# Tokens: `uv publish` reads the API token from UV_PUBLISH_TOKEN (starts with `pypi-`), so export
# it in the shell for the run, e.g. `UV_PUBLISH_TOKEN=pypi-... make pypi-publish`.
#   pypi-publish       a token made at https://pypi.org/manage/account/token/
#   pypi-publish-dev   a token made at https://test.pypi.org/manage/account/token/
# The two sites have separate accounts, so a token from one is rejected by the other. A token
# scoped to one project can only be made after its first upload, so the first one needs an
# account-wide token. In CI, trusted publishing replaces the token.
#
# A published version can't be replaced. To fix a bad release, bump VERSION and publish again.
# To pull a bad release, yank it on pypi.org (project > release > Options > Yank): PyPI has no
# API for it, so there is no make target.
#
# Set before including (all optional):
#   PYPI_PUBLISH_URL   upload endpoint of `pypi-publish` (default: PyPI)
#   TESTPYPI_PUBLISH_URL   upload endpoint of `pypi-publish-dev` (default: TestPyPI)

PYPI_PUBLISH_URL ?=
TESTPYPI_PUBLISH_URL ?= https://test.pypi.org/legacy/

.PHONY: pypi-publish
pypi-publish: clean build ## Build and publish the package to PyPI
	$(call banner, Publishing $(APP_NAME) $(VERSION) to PyPI...)
	@uv publish $(if $(PYPI_PUBLISH_URL),--publish-url $(PYPI_PUBLISH_URL) )$(DIST_DIR)/*

.PHONY: pypi-publish-dev
pypi-publish-dev: PYPI_PUBLISH_URL = $(TESTPYPI_PUBLISH_URL)
pypi-publish-dev: pypi-publish ## Build and publish the package to TestPyPI
