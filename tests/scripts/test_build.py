import importlib.util
import pathlib

import pytest

SCRIPT = pathlib.Path(__file__).resolve().parents[2] / "scripts" / "build.py"


@pytest.fixture(scope="module")
def build():
    # Loaded by path: a plain `import build` can hit the PyPA `build` package.
    spec = importlib.util.spec_from_file_location("nyx_build_script", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_archive_name_has_version_platform_and_architecture(build):
    name = build.archive_base_name()

    assert (
        name
        == f"nyx-{build.read_version()}-{build.platform_name()}-{build.architecture()}"
    )


def test_bundle_path_is_an_app_only_on_macos(build, monkeypatch):
    monkeypatch.setattr(build, "IS_MACOS", True)
    assert build.bundle_path().name == "nyx.app"
    assert build.executables_dir().parts[-2:] == ("Contents", "MacOS")

    monkeypatch.setattr(build, "IS_MACOS", False)
    assert build.bundle_path().name == "nyx"
    assert build.executables_dir() == build.bundle_path()


@pytest.mark.parametrize(
    "machine, expected",
    [("arm64", "arm64"), ("aarch64", "arm64"), ("x86_64", "x64"), ("AMD64", "x64")],
)
def test_architecture_names(build, monkeypatch, machine, expected):
    monkeypatch.setattr(build.platform, "machine", lambda: machine)

    assert build.architecture() == expected


def test_parser_requires_a_command(build):
    with pytest.raises(SystemExit):
        build.build_parser().parse_args([])


def test_parser_reads_install_directories(build):
    args = build.build_parser().parse_args(["install-cli", "--bin-dir", "/tmp/bin"])

    assert (args.command, str(args.bin_dir)) == ("install-cli", "/tmp/bin")
