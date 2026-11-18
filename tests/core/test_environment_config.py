import logging
import os

import pytest

from nyx.core.config_values import NyxEnvironmentConfigValues
from nyx.core.layered_config import get_app_config


@pytest.fixture
def environment(qapp):
    """The `environment` config values, restored after the test."""
    values = get_app_config().values
    original = values.environment
    values.environment = NyxEnvironmentConfigValues()
    yield values.environment
    values.environment = original


def test_overrides_are_set_in_the_process(qapp, environment, monkeypatch):
    monkeypatch.delenv("NYX_TEST_VAR", raising=False)
    environment.vars_overrides = {"NYX_TEST_VAR": "value"}
    qapp.apply_config_environment()
    assert os.environ["NYX_TEST_VAR"] == "value"


def test_override_values_are_expanded(qapp, environment, monkeypatch):
    monkeypatch.setenv("NYX_TEST_BASE", "base")
    monkeypatch.delenv("NYX_TEST_VAR", raising=False)
    environment.vars_overrides = {"NYX_TEST_VAR": "$NYX_TEST_BASE/bin"}
    qapp.apply_config_environment()
    assert os.environ["NYX_TEST_VAR"] == "base/bin"


def test_invalid_override_names_are_skipped(qapp, environment):
    environment.vars_overrides = {"": "x", "A=B": "y"}
    qapp.apply_config_environment()
    assert "" not in os.environ
    assert "A=B" not in os.environ


def test_source_file_is_empty_by_default_and_loads_nothing(qapp, environment):
    assert environment.source_file == ""
    before = dict(os.environ)
    qapp.apply_config_environment()
    assert dict(os.environ) == before


def test_source_file_variables_are_set(qapp, environment, tmp_path, monkeypatch):
    monkeypatch.delenv("NYX_TEST_FILE_VAR", raising=False)
    path = tmp_path / "studio.env"
    path.write_text("NYX_TEST_FILE_VAR=from file\n")
    environment.source_file = str(path)

    qapp.apply_config_environment()

    assert os.environ["NYX_TEST_FILE_VAR"] == "from file"


def test_overrides_win_over_the_source_file(qapp, environment, tmp_path, monkeypatch):
    monkeypatch.delenv("NYX_TEST_VAR", raising=False)
    path = tmp_path / "studio.env"
    path.write_text("NYX_TEST_VAR=file\nNYX_TEST_ONLY_FILE=file\n")
    monkeypatch.delenv("NYX_TEST_ONLY_FILE", raising=False)
    environment.source_file = str(path)
    environment.vars_overrides = {"NYX_TEST_VAR": "override"}

    qapp.apply_config_environment()

    assert os.environ["NYX_TEST_VAR"] == "override"
    assert os.environ["NYX_TEST_ONLY_FILE"] == "file"


def test_missing_source_file_is_reported_and_overrides_still_apply(
    qapp, environment, tmp_path, monkeypatch, caplog
):
    monkeypatch.delenv("NYX_TEST_VAR", raising=False)
    environment.source_file = str(tmp_path / "missing.env")
    environment.vars_overrides = {"NYX_TEST_VAR": "value"}

    with caplog.at_level(logging.ERROR):
        qapp.apply_config_environment()

    assert "missing.env" in caplog.text
    assert os.environ["NYX_TEST_VAR"] == "value"


def test_applying_again_reads_the_changed_source_file(
    qapp, environment, tmp_path, monkeypatch
):
    monkeypatch.delenv("NYX_TEST_FILE_VAR", raising=False)
    path = tmp_path / "studio.env"
    path.write_text("NYX_TEST_FILE_VAR=1\n")
    environment.source_file = str(path)
    qapp.apply_config_environment()

    path.write_text("NYX_TEST_FILE_VAR=2\n")
    qapp.apply_config_environment()

    assert os.environ["NYX_TEST_FILE_VAR"] == "2"


def test_variables_saved_straight_under_environment_become_overrides():
    values = NyxEnvironmentConfigValues()
    migrated = values.pre_deserialize({"USD_PYTHON": "/usd/python", "A": "1"})

    assert migrated == {"vars_overrides": {"USD_PYTHON": "/usd/python", "A": "1"}}


def test_migration_keeps_options_and_prefers_explicit_overrides():
    values = NyxEnvironmentConfigValues()
    migrated = values.pre_deserialize(
        {"source_file": "a.env", "vars_overrides": {"A": "new"}, "A": "old", "B": "1"}
    )

    assert migrated == {"source_file": "a.env", "vars_overrides": {"A": "new", "B": "1"}}


def test_current_format_is_left_alone():
    values = NyxEnvironmentConfigValues()
    data = {"source_file": "a.env", "vars_overrides": {"A": "1"}}

    assert values.pre_deserialize(data) is data
