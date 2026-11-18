"""Functions reading the system and the environment of the running program."""

import os
import platform
import shutil
import subprocess
import sys
import time

from nyx.api.v1 import static_env_file


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


def _split_env(name: str, separator: str) -> list[str]:
    """Get the entries of an environment variable, without the empty ones."""
    return [entry for entry in os.environ.get(name, "").split(separator) if entry]


def _store_env(name: str, entries: list[str], separator: str) -> str:
    """Set an environment variable from its entries, unset it if there are none."""
    value = separator.join(entries)
    if value:
        os.environ[name] = value
    else:
        os.environ.pop(name, None)
    return value


def append_env(name: str, value: str, separator: str = os.pathsep) -> str:
    """Add an entry to the end of an environment variable, like a path to PATH.

    Entries are separated, so PATH with a/b becomes PATH:a/b. An entry that is already
    there moves to the end instead of being added twice. Get the new value.

    Args:
        name: Name of the variable.
        value: Entry to add.
        separator: Text between entries, the one of paths on this system by default.
    """
    entries = [entry for entry in _split_env(name, separator) if entry != value]
    entries.append(value)
    return _store_env(name, entries, separator)


def prepend_env(name: str, value: str, separator: str = os.pathsep) -> str:
    """Add an entry to the start of an environment variable, like a path to PATH.

    Entries are separated, so PATH with a/b becomes a/b:PATH. An entry that is already
    there moves to the start instead of being added twice. Get the new value.

    Args:
        name: Name of the variable.
        value: Entry to add.
        separator: Text between entries, the one of paths on this system by default.
    """
    entries = [entry for entry in _split_env(name, separator) if entry != value]
    entries.insert(0, value)
    return _store_env(name, entries, separator)


def pop_env(name: str, value: str, separator: str = os.pathsep) -> str:
    """Remove an entry from an environment variable, like a path from PATH.

    Does nothing if the entry is not there. The variable is unset when its last entry
    goes. Get the new value, empty if it is unset.

    Args:
        name: Name of the variable.
        value: Entry to remove.
        separator: Text between entries, the one of paths on this system by default.
    """
    entries = [entry for entry in _split_env(name, separator) if entry != value]
    return _store_env(name, entries, separator)


def unset_env(name: str) -> bool:
    """Remove an environment variable. Get whether it was set.

    Args:
        name: Name of the variable.
    """
    return os.environ.pop(name, None) is not None


def update_env(values: dict) -> dict:
    """Set many environment variables from a dictionary. Get what was set.

    Names and values are made text. Nothing is set if a name is empty or has an equals
    sign in it.

    Args:
        values: Value of each variable by name.
    """
    variables = {str(name): str(value) for name, value in values.items()}
    for name in variables:
        if not name or "=" in name:
            raise ValueError(f"Not a name of an environment variable: {name!r}")
    os.environ.update(variables)
    return variables


def split_env(name: str, separator: str = os.pathsep) -> list:
    """Get the entries of an environment variable, like the paths in PATH.

    Empty entries are left out, so is everything for a variable that isn't set.

    Args:
        name: Name of the variable.
        separator: Text between entries, the one of paths on this system by default.
    """
    return _split_env(name, separator)


def has_env_entry(name: str, value: str, separator: str = os.pathsep) -> bool:
    """Check if an entry is in an environment variable, like a path in PATH.

    Args:
        name: Name of the variable.
        value: Entry to look for.
        separator: Text between entries, the one of paths on this system by default.
    """
    return value in _split_env(name, separator)


def expand_env(text: str) -> str:
    """Replace $NAME and ${NAME} in a text with environment variables.

    Variables that aren't set are left as they are.

    Args:
        text: Text to expand.
    """
    return os.path.expandvars(text)


def load_env_file(path: str) -> dict:
    """Set the variables of an environment file. Get what was set.

    Lines are NAME=value, with an optional export in front. Empty lines and lines
    starting with # are skipped. A value in single quotes is taken as it is, any other
    one has $NAME expanded. Raises when the file can't be read.

    Args:
        path: Environment file.
    """
    return static_env_file.load_env_file(path)


def filter_env(prefix: str, strip_prefix: bool = False) -> dict:
    """Get the environment variables whose names start with a prefix.

    Args:
        prefix: Start of the names, case matters.
        strip_prefix: Leave the prefix out of the names of the result.
    """
    start = len(prefix) if strip_prefix else 0
    return {
        name[start:]: value
        for name, value in os.environ.items()
        if name.startswith(prefix)
    }


def get_env_bool(name: str, default: bool = False) -> bool:
    """Get an environment variable as true or false.

    1, true, yes, on, y and t are true, 0, false, no, off, n, f and empty are false,
    in any case. The default is used if the variable isn't set or is anything else.

    Args:
        name: Name of the variable.
        default: Value to get if the variable isn't set or can't be read.
    """
    value = os.environ.get(name)
    if value is None:
        return default
    value = value.strip().lower()
    if value in ("1", "true", "yes", "on", "y", "t"):
        return True
    if value in ("0", "false", "no", "off", "n", "f", ""):
        return False
    return default


def get_env_int(name: str, default: int = 0) -> int:
    """Get an environment variable as a whole number.

    Args:
        name: Name of the variable.
        default: Value to get if the variable isn't set or isn't a whole number.
    """
    try:
        return int(os.environ[name].strip())
    except KeyError, ValueError:
        return default


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
