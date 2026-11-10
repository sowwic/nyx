"""Command line interface: open the editor, or run stages without it.

Qt is imported when a command needs it, so reading `--help` or reporting a wrong
argument is quick and works without a display.
"""

from __future__ import annotations

import argparse
import logging
import os
import pathlib
import typing

if typing.TYPE_CHECKING:
    from nyx.core.node import Node

EXIT_OK = 0
EXIT_STAGE_FAILED = 1
EXIT_USAGE = 2
EXIT_INTERRUPTED = 130


def add_run_arguments(parser: argparse.ArgumentParser) -> None:
    """Add the arguments of running a stage.

    Args:
        parser (argparse.ArgumentParser): parser to add them to.
    """
    parser.add_argument("path", type=pathlib.Path, help="stage file to run")
    parser.add_argument(
        "--no-bridge",
        dest="bridge",
        action="store_false",
        help="do not start the bridge server, so remote nodes have no client to use",
    )
    parser.add_argument(
        "--port",
        type=int,
        help="port of the bridge server for this run, instead of the configured one",
    )


def build_parser() -> argparse.ArgumentParser:
    """Create the parser of the `nyx` command.

    Returns:
        argparse.ArgumentParser: parser. Without a command the editor is opened.
    """
    parser = argparse.ArgumentParser(
        prog="nyx", description="Nyx, a Python nodal execution graph."
    )
    commands = parser.add_subparsers(dest="command", metavar="command")
    stage = commands.add_parser("stage", help="work with stage files")
    stage_commands = stage.add_subparsers(
        dest="stage_command", metavar="command", required=True
    )
    run = stage_commands.add_parser("run", help="run a stage without the editor")
    add_run_arguments(run)
    return parser


def build_run_stage_parser() -> argparse.ArgumentParser:
    """Create the parser of the `nyx-run-stage` command.

    Returns:
        argparse.ArgumentParser: parser, same arguments as `nyx stage run`.
    """
    parser = argparse.ArgumentParser(
        prog="nyx-run-stage", description="Run a Nyx stage without the editor."
    )
    add_run_arguments(parser)
    return parser


def main(argv: typing.Sequence[str] | None = None) -> int:
    """Entry point of the `nyx` command.

    Args:
        argv (Sequence[str] | None): arguments, `sys.argv` if omitted.

    Returns:
        int: exit code.
    """
    args = build_parser().parse_args(argv)
    if args.command is None:
        return _open_editor()
    return run_stage(args.path, args.bridge, args.port)


def run_stage_main(argv: typing.Sequence[str] | None = None) -> int:
    """Entry point of the `nyx-run-stage` command.

    Args:
        argv (Sequence[str] | None): arguments, `sys.argv` if omitted.

    Returns:
        int: exit code.
    """
    args = build_run_stage_parser().parse_args(argv)
    return run_stage(args.path, args.bridge, args.port)


def _open_editor() -> int:
    """Run the editor, see `nyx.main.main`.

    Returns:
        int: exit code.
    """
    from nyx import main as editor

    editor.main()
    return EXIT_OK


def run_stage(
    path: pathlib.Path | str,
    bridge: bool = True,
    port: int | None = None,
) -> int:
    """Run a stage file without the editor.

    The application config is used but never saved.

    Args:
        path (pathlib.Path | str): stage file.
        bridge (bool): start the bridge server, if the config enables it.
        port (int | None): port of the bridge server, the configured one if omitted.

    Returns:
        int: exit code, 0 when the stage ran, 1 when it failed, 2 when it could not
            be loaded.
    """
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from nyx.core.logger import NyxLogger

    # Before the other modules make their loggers, like the editor does: the nyx loggers
    # write to the console and the log file.
    logging.setLoggerClass(NyxLogger)
    from PySide6 import QtWidgets

    from nyx.api.v1 import Stage
    from nyx.application import NyxApplication

    app = QtWidgets.QApplication.instance() or NyxApplication()
    session = app.session
    try:
        path = pathlib.Path(path)
        if not path.is_file():
            logging.getLogger(__name__).error("Stage file not found: %s", path)
            return EXIT_USAGE

        stage = Stage()  # nodes do not keep their stage alive
        if stage.import_json(path) is None:
            logging.getLogger(__name__).error("Could not load the stage from %s", path)
            return EXIT_USAGE

        if bridge:
            if port is not None:
                session.config.values.bridge.port = port
            session.autostart_bridge_server()

        return _crawl(stage)
    finally:
        session.shutdown()


def _crawl(stage) -> int:
    """Run a stage and report how it went.

    Args:
        stage (Stage): stage to run.

    Returns:
        int: exit code.
    """
    failed: list[Node] = []
    stage.execution_failed.connect(failed.append)
    try:
        stage.crawler.start()
    except KeyboardInterrupt:
        logging.getLogger(__name__).error("Interrupted")
        return EXIT_INTERRUPTED
    except Exception as err:
        where = failed[0].path.as_posix() if failed else "the stage"
        logging.getLogger(__name__).error("Stage failed at %s: %s", where, err)
        return EXIT_STAGE_FAILED
    finally:
        stage.execution_failed.disconnect(failed.append)
    return EXIT_OK
