import importlib.util
import pathlib
import sys

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

    assert (args.command, args.bin_dir) == ("install-cli", pathlib.Path("/tmp/bin"))


@pytest.mark.skipif(sys.platform == "win32", reason="Linux only, needs symlinks")
def test_clear_executable_stacks_only_patches_elf_libraries(
    build, monkeypatch, tmp_path
):
    elf = tmp_path / "lib" / "libpython3.14.so.1.0"
    elf.parent.mkdir()
    elf.write_bytes(b"\x7fELF" + bytes(16))
    (tmp_path / "lib" / "libqt.so.6").symlink_to(elf)
    (tmp_path / "lib" / "notes.so.txt").write_text("not a library")
    (tmp_path / "lib" / "nyx").write_bytes(b"\x7fELF" + bytes(16))
    monkeypatch.setattr(build, "find_tool", lambda name: f"/usr/bin/{name}")
    calls = []
    monkeypatch.setattr(build, "run", calls.append)

    build.clear_executable_stacks(tmp_path)

    assert calls == [["/usr/bin/patchelf", "--clear-execstack", elf]]
