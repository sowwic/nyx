"""Entry point of the `nyx-run-stage` executable of the packaged application."""

import sys

from nyx.cli import run_stage_main

if __name__ == "__main__":
    sys.exit(run_stage_main())
