"""Build, archive, test and install the Nyx application on macOS, Windows and Linux.

Usage:
    uv run python scripts/build.py <command>

Commands:
    qrc          compile the Qt resource files
    icons        generate the icon file of the current platform into build/icons
    build-app    qrc + icons + PyInstaller, gives dist/nyx.app (macOS) or dist/nyx
    archive-app  build-app + zip/tar.gz into dist/nyx-<version>-<os>-<arch>
    test-app     run the built executables to check that they start and run a stage
    install-app  copy dist/nyx.app into /Applications (macOS)
    install-cli  link the `nyx` and `nyx-run-stage` commands of the app into a bin dir

PyInstaller cannot cross-compile, run this on the platform you build for.
"""

import argparse
import os
import pathlib
import platform
import shutil
import subprocess
import sys

import icons

APP_NAME = "nyx"
CLI_NAME = "nyx-run-stage"

ROOT = pathlib.Path(__file__).resolve().parents[1]
DIST_DIR = ROOT / "dist"
BUILD_DIR = ROOT / "build"
ICON_BUILD_DIR = BUILD_DIR / "icons"
ICON_SOURCE_DIR = ROOT / "src" / "nyx" / "resources" / "icons" / "nyx"
SPEC_FILE = ROOT / f"{APP_NAME}.spec"
SMOKE_STAGE = ROOT / "scripts" / "smoke_stage.nyx"
QRC_FILES = (
    ROOT / "src" / "nyx" / "resources" / "resources.qrc",
    ROOT / "src" / "nyx" / "stdlib" / "resources" / "resources.qrc",
)

IS_MACOS = sys.platform == "darwin"
IS_WINDOWS = sys.platform == "win32"
EXE_SUFFIX = ".exe" if IS_WINDOWS else ""

DESKTOP_ENTRY = """[Desktop Entry]
Type=Application
Name=Nyx
Comment=Python nodal execution graph
Exec=nyx
Icon=nyx
Categories=Development;
Terminal=false
"""


def platform_name() -> str:
    """Get the short name of the current platform.

    Returns:
        str: `macos`, `windows` or `linux`.
    """
    if IS_MACOS:
        return "macos"
    if IS_WINDOWS:
        return "windows"
    return "linux"


def architecture() -> str:
    """Get the short name of the CPU architecture.

    Returns:
        str: `arm64` or `x64`, the machine name in lower case for others.
    """
    machine = platform.machine().lower()
    if machine in ("arm64", "aarch64"):
        return "arm64"
    if machine in ("x86_64", "amd64"):
        return "x64"
    return machine


def read_version() -> str:
    """Read the application version.

    Returns:
        str: content of the VERSION file.
    """
    return (ROOT / "VERSION").read_text().strip()


def bundle_path() -> pathlib.Path:
    """Get the path of the PyInstaller output.

    Returns:
        pathlib.Path: `dist/nyx.app` on macOS, the `dist/nyx` folder elsewhere.
    """
    return DIST_DIR / (f"{APP_NAME}.app" if IS_MACOS else APP_NAME)


def executables_dir() -> pathlib.Path:
    """Get the folder with the executables of the app.

    Returns:
        pathlib.Path: directory.
    """
    return bundle_path() / "Contents" / "MacOS" if IS_MACOS else bundle_path()


def archive_base_name() -> str:
    """Get the name of the archive, without the extension.

    Returns:
        str: name with the version, platform and architecture.
    """
    return f"{APP_NAME}-{read_version()}-{platform_name()}-{architecture()}"


def run(command: list[str | pathlib.Path], **kwargs) -> None:
    """Run a command in the project root and stop the build if it fails.

    Args:
        command (list[str | pathlib.Path]): program and arguments.
        **kwargs: passed to `subprocess.run`.
    """
    print(f"==> {' '.join(str(part) for part in command)}", flush=True)
    subprocess.run(command, cwd=ROOT, check=True, **kwargs)


def build_qrc() -> None:
    """Compile the Qt resource files into `resources_rc.py` modules."""
    rcc = pathlib.Path(sys.executable).parent / f"pyside6-rcc{EXE_SUFFIX}"
    program = str(rcc) if rcc.is_file() else shutil.which("pyside6-rcc")
    if program is None:
        raise SystemExit("pyside6-rcc not found, run with `uv run`")
    for qrc_file in QRC_FILES:
        run([program, qrc_file, "-o", qrc_file.with_name("resources_rc.py")])


def build_icons() -> None:
    """Generate the icon file the platform needs into `build/icons`."""
    if IS_MACOS:
        icons.write_icns(ICON_SOURCE_DIR, ICON_BUILD_DIR / f"{APP_NAME}.icns")
    elif IS_WINDOWS:
        icons.write_ico(ICON_SOURCE_DIR, ICON_BUILD_DIR / f"{APP_NAME}.ico")
    else:
        print("==> No icon file to generate on Linux")


def build_app() -> None:
    """Build the application with PyInstaller."""
    build_qrc()
    build_icons()
    run(
        [
            sys.executable,
            "-m",
            "PyInstaller",
            "--noconfirm",
            "--distpath",
            DIST_DIR,
            "--workpath",
            BUILD_DIR / "pyinstaller",
            SPEC_FILE,
        ]
    )
    if platform_name() == "linux":
        # No launcher can be made from a folder, ship the pieces to make one.
        shutil.copy(ICON_SOURCE_DIR / "512.png", bundle_path() / f"{APP_NAME}.png")
        (bundle_path() / f"{APP_NAME}.desktop").write_text(DESKTOP_ENTRY)


def archive_app() -> pathlib.Path:
    """Build the application and archive it.

    Returns:
        pathlib.Path: archive path, a zip (macOS, Windows) or tar.gz (Linux).
    """
    build_app()
    base_name = DIST_DIR / archive_base_name()
    if IS_MACOS:
        # ditto keeps the symlinks and permissions of the app, zipfile does not.
        archive = pathlib.Path(f"{base_name}.zip")
        archive.unlink(missing_ok=True)
        run(["ditto", "-c", "-k", "--keepParent", bundle_path(), archive])
    else:
        archive_format = "zip" if IS_WINDOWS else "gztar"
        archive = pathlib.Path(
            shutil.make_archive(
                str(base_name), archive_format, root_dir=DIST_DIR, base_dir=APP_NAME
            )
        )
    print(f"==> Created {archive}")
    return archive


def check_app() -> None:
    """Run the built executables: help, a missing file and a real stage."""
    env = {**os.environ}
    env.setdefault("QT_QPA_PLATFORM", "offscreen")
    cli = executables_dir() / f"{CLI_NAME}{EXE_SUFFIX}"
    editor = executables_dir() / f"{APP_NAME}{EXE_SUFFIX}"
    checks = (
        ([cli, "--help"], 0),
        ([cli, ROOT / "does_not_exist.nyx"], 2),
        ([cli, "--no-bridge", SMOKE_STAGE], 0),
        ([editor, "stage", "run", "--no-bridge", SMOKE_STAGE], 0),
    )
    for command, expected in checks:
        print(f"==> {' '.join(str(part) for part in command)}", flush=True)
        result = subprocess.run(command, cwd=ROOT, env=env, timeout=180)
        if result.returncode != expected:
            raise SystemExit(f"Expected exit code {expected}, got {result.returncode}")
    print("==> Smoke test passed")


def install_app(destination: pathlib.Path) -> None:
    """Copy the macOS application into a directory.

    Args:
        destination (pathlib.Path): directory such as /Applications.
    """
    if not IS_MACOS:
        raise SystemExit("install is only for the macOS app")
    target = destination / bundle_path().name
    print(f"==> Installing {APP_NAME} v{read_version()} into {destination}")
    shutil.rmtree(target, ignore_errors=True)
    shutil.copytree(bundle_path(), target, symlinks=True)


def install_cli(bin_dir: pathlib.Path) -> None:
    """Link the commands of the app into a directory on the PATH.

    Args:
        bin_dir (pathlib.Path): directory such as /usr/local/bin.
    """
    if IS_WINDOWS:
        raise SystemExit(
            "install-cli is not supported on Windows, add the folder to PATH"
        )
    print(f"==> Linking nyx commands into {bin_dir}")
    for name in (APP_NAME, CLI_NAME):
        link = bin_dir / name
        link.unlink(missing_ok=True)
        link.symlink_to((executables_dir() / name).resolve())


def build_parser() -> argparse.ArgumentParser:
    """Create the command line parser.

    Returns:
        argparse.ArgumentParser: parser of the commands.
    """
    parser = argparse.ArgumentParser(
        description="Build, archive, test and install the Nyx application."
    )
    commands = parser.add_subparsers(dest="command", metavar="command", required=True)
    commands.add_parser("qrc", help="compile the Qt resource files")
    commands.add_parser("icons", help="generate the icon file of this platform")
    commands.add_parser("build-app", help="build dist/nyx.app (macOS) or dist/nyx")
    commands.add_parser("archive-app", help="build the app and zip or tar.gz it")
    commands.add_parser("test-app", help="run the built executables")
    install = commands.add_parser(
        "install-app", help="copy dist/nyx.app into /Applications (macOS)"
    )
    install.add_argument("--dest", type=pathlib.Path, default="/Applications")
    link = commands.add_parser(
        "install-cli", help="link the nyx and nyx-run-stage commands into /usr/local/bin"
    )
    link.add_argument("--bin-dir", type=pathlib.Path, default="/usr/local/bin")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run a build command.

    Args:
        argv (list[str] | None): arguments, `sys.argv` if omitted.

    Returns:
        int: exit code.
    """
    args = build_parser().parse_args(argv)
    match args.command:
        case "qrc":
            build_qrc()
        case "icons":
            build_icons()
        case "build-app":
            build_app()
        case "archive-app":
            archive_app()
        case "test-app":
            check_app()
        case "install-app":
            install_app(pathlib.Path(args.dest))
        case "install-cli":
            install_cli(pathlib.Path(args.bin_dir))
    return 0


if __name__ == "__main__":
    sys.exit(main())
