import pathlib
import sys

SCRIPTS_DIR = pathlib.Path(__file__).resolve().parents[2] / "scripts"

# The build scripts are not part of the package, they import each other by name.
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))
