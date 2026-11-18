import os
import subprocess

import pytest

from nyx.static import shell_env


def test_parse_env_splits_on_nul_and_keeps_equals_in_values():
    output = b"A=1\0B=x=y\0C=\0broken\0=novalue\0"
    assert shell_env.parse_env(output) == {"A": "1", "B": "x=y", "C": ""}


@pytest.fixture
def posix(monkeypatch):
    monkeypatch.setattr(shell_env.sys, "platform", "darwin")
    monkeypatch.delenv(shell_env.LOADED_FLAG, raising=False)


def test_load_adds_missing_variables_and_overrides_only_path(posix, monkeypatch):
    monkeypatch.setenv("PATH", "/minimal")
    monkeypatch.setenv("NYX_TEST_KEPT", "launcher")
    monkeypatch.delenv("NYX_TEST_NEW", raising=False)
    monkeypatch.setattr(
        shell_env,
        "read_shell_env",
        lambda: {"PATH": "/full", "NYX_TEST_KEPT": "shell", "NYX_TEST_NEW": "shell"},
    )
    assert shell_env.load_shell_env()
    assert os.environ["PATH"] == "/full"
    assert os.environ["NYX_TEST_KEPT"] == "launcher"
    assert os.environ["NYX_TEST_NEW"] == "shell"
    assert os.environ[shell_env.LOADED_FLAG] == "1"


def test_load_does_nothing_when_already_loaded(posix, monkeypatch):
    monkeypatch.setenv(shell_env.LOADED_FLAG, "1")
    monkeypatch.setattr(shell_env, "read_shell_env", pytest.fail)
    assert not shell_env.load_shell_env()


def test_load_does_nothing_on_windows(monkeypatch):
    monkeypatch.setattr(shell_env.sys, "platform", "win32")
    monkeypatch.delenv(shell_env.LOADED_FLAG, raising=False)
    monkeypatch.setattr(shell_env, "read_shell_env", pytest.fail)
    assert not shell_env.load_shell_env()


def test_failing_shell_is_swallowed(monkeypatch):
    def fail(*args, **kwargs):
        raise subprocess.TimeoutExpired("sh", 1)

    monkeypatch.setattr(shell_env.subprocess, "run", fail)
    assert shell_env.read_shell_env() == {}
