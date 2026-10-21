"""Functions reading the system and the environment of the running program."""

import os
import platform
import shutil
import subprocess
import sys
import time


def get_env(name: str, default: str = "") -> str:
    """Get an environment variable, the default if it isn't set.

    Args:
        name: Name of the variable or program.
        default: Value to get if the variable isn't set.
    """
    return os.environ.get(name, default)


def set_env(name: str, value: str) -> str:
    """Set an environment variable for this program. Get the value.

    Args:
        name: Name of the variable.
        value: Value to set.
    """
    os.environ[name] = value
    return value


def has_env(name: str) -> bool:
    """Check if an environment variable is set.

    Args:
        name: Name of the variable or program.
    """
    return name in os.environ


def platform_name() -> str:
    """Get the name of the operating system, like "Darwin", "Linux" or "Windows"."""
    return platform.system()


def python_version() -> str:
    """Get the version of the python running the program."""
    return platform.python_version()


def current_folder() -> str:
    """Get the working folder of the program."""
    return os.getcwd()


def home_folder() -> str:
    """Get the home folder of the user."""
    return os.path.expanduser("~")


def user_name() -> str:
    """Get the name of the user running the program."""
    return os.environ.get("USER") or os.environ.get("USERNAME") or ""


def cpu_count() -> int:
    """Get the number of CPUs."""
    return os.cpu_count() or 1


def timestamp() -> float:
    """Get the seconds since 1970-01-01."""
    return time.time()


def sleep(seconds: float) -> float:
    """Wait for a number of seconds. Get how long it was.

    Args:
        seconds: How long to wait, in seconds.
    """
    time.sleep(seconds)
    return seconds


def run_command(command: list, timeout: float = 60.0) -> str:
    """Run a program with its arguments, no shell. Get what it printed.

    Raises when the program fails or takes longer than the timeout.

    Args:
        command: Program followed by its arguments.
        timeout: Seconds to wait before giving up.
    """
    result = subprocess.run(
        [str(part) for part in command],
        capture_output=True,
        text=True,
        timeout=timeout,
        check=True,
    )
    return result.stdout


def executable_path(name: str) -> str:
    """Get the path of a program found in PATH, empty if there is none.

    Args:
        name: Name of the program.
    """
    return shutil.which(name) or ""


def python_executable() -> str:
    """Get the path of the python running the program."""
    return sys.executable
