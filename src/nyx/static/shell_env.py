"""Environment of the user's login shell, for when nyx is not started from a shell.

An application launched from the Finder or a desktop entry gets a minimal environment,
without what the shell profile sets (`PATH`, `NYX_PLUGIN_PATH`, ...). This module has
no nyx imports so it can run before the rest of the package is imported.
"""

import logging
import os
import subprocess
import sys

LOGGER = logging.getLogger(__name__)

LOADED_FLAG = "NYX_SHELL_ENV_LOADED"
"""Set once the shell environment is loaded, so child processes don't load it again."""
TIMEOUT = 10.0
"""Seconds to wait for the shell, a profile can be slow."""
_OVERRIDDEN = ("PATH",)
"""Variables the shell value wins for, the launcher one is the minimal default."""


def parse_env(output: bytes) -> dict[str, str]:
    """Parse the NUL separated output of `env -0`.

    Args:
        output (bytes): output of the command.

    Returns:
        dict[str, str]: variables, entries without a name or an `=` are skipped.
    """
    variables = {}
    for entry in output.decode(errors="replace").split("\0"):
        name, separator, value = entry.partition("=")
        if separator and name:
            variables[name] = value
    return variables


def read_shell_env() -> dict[str, str]:
    """Read the environment of the login shell.

    Returns:
        dict[str, str]: variables, empty if the shell failed.
    """
    shell = os.environ.get("SHELL") or "/bin/sh"
    try:
        result = subprocess.run(
            [shell, "-l", "-i", "-c", "env -0"],
            capture_output=True,
            stdin=subprocess.DEVNULL,
            timeout=TIMEOUT,
            check=True,
        )
    except (OSError, subprocess.SubprocessError) as err:
        LOGGER.warning("Could not read the shell environment: %s", err)
        return {}
    return parse_env(result.stdout)


def load_shell_env() -> bool:
    """Add the environment of the login shell to this process.

    Variables that are already set are kept, except `PATH`. Does nothing on Windows or
    when it was done already, by this process or the one that started it.

    Returns:
        bool: the shell environment was loaded.
    """
    if sys.platform == "win32" or os.environ.get(LOADED_FLAG):
        return False
    variables = read_shell_env()
    if not variables:
        return False
    for name, value in variables.items():
        if name in _OVERRIDDEN:
            os.environ[name] = value
        else:
            os.environ.setdefault(name, value)
    os.environ[LOADED_FLAG] = "1"
    return True
