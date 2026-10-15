"""Generate .qmlls.ini by deriving QML import roots from qmldir files."""

import argparse
import configparser
import os
import pathlib
import subprocess
import sys


def find_project_root_directory(start_directory: pathlib.Path) -> pathlib.Path:
    for candidate_directory in [start_directory, *start_directory.parents]:
        if (candidate_directory / ".git").exists():
            return candidate_directory
    return start_directory


def find_qmldir_files_in_project(
    project_root_directory: pathlib.Path,
) -> list[pathlib.Path]:
    """Respect .gitignore when possible, so .venv, build dirs etc. are skipped."""
    try:
        git_listing = subprocess.run(
            [
                "git",
                "ls-files",
                "--cached",
                "--others",
                "--exclude-standard",
                "--",
                "*qmldir",
            ],
            cwd=project_root_directory,
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        return [
            project_root_directory / each_line
            for each_line in git_listing.splitlines()
            if pathlib.PurePath(each_line).name == "qmldir"
        ]
    except subprocess.CalledProcessError, FileNotFoundError:
        return list(project_root_directory.rglob("qmldir"))


def read_module_uri_from_qmldir(qmldir_file_path: pathlib.Path) -> str | None:
    for each_line in qmldir_file_path.read_text(encoding="utf-8").splitlines():
        stripped_line = each_line.strip()
        if stripped_line.startswith("module "):
            return stripped_line.split(maxsplit=1)[1].strip()
    return None


def derive_import_root_directory(qmldir_file_path: pathlib.Path) -> pathlib.Path | None:
    module_uri = read_module_uri_from_qmldir(qmldir_file_path)
    if not module_uri:
        return None

    module_uri_parts = module_uri.split(".")
    module_directory = qmldir_file_path.parent
    actual_trailing_directory_names = list(
        module_directory.parts[-len(module_uri_parts) :]
    )
    if actual_trailing_directory_names != module_uri_parts:
        print(
            f"warning: {qmldir_file_path} declares 'module {module_uri}' but its folder "
            f"does not end in {'/'.join(module_uri_parts)}; skipping",
            file=sys.stderr,
        )
        return None

    import_root_directory = module_directory
    for _ in module_uri_parts:
        import_root_directory = import_root_directory.parent
    return import_root_directory


def collect_import_root_directories(
    project_root_directory: pathlib.Path,
    additional_search_directories: list[pathlib.Path],
) -> list[pathlib.Path]:
    qmldir_file_paths = find_qmldir_files_in_project(project_root_directory)
    for each_search_directory in additional_search_directories:
        qmldir_file_paths.extend(each_search_directory.rglob("qmldir"))

    unique_import_root_directories: dict[pathlib.Path, None] = {}
    for each_qmldir_file_path in sorted(qmldir_file_paths):
        import_root_directory = derive_import_root_directory(
            each_qmldir_file_path.resolve()
        )
        if import_root_directory is not None:
            unique_import_root_directories[import_root_directory] = None
    return list(unique_import_root_directories)


def main() -> None:
    argument_parser = argparse.ArgumentParser(description=__doc__)
    argument_parser.add_argument(
        "--also-scan",
        nargs="*",
        default=[],
        type=pathlib.Path,
        help="extra directories outside the repo (e.g. external plugin folders)",
    )
    argument_parser.add_argument(
        "--print-env",
        action="store_true",
        help="print a QML_IMPORT_PATH export line instead of writing .qmlls.ini",
    )
    parsed_arguments = argument_parser.parse_args()

    project_root_directory = find_project_root_directory(pathlib.Path.cwd()).resolve()
    import_root_directories = collect_import_root_directories(
        project_root_directory, [path.resolve() for path in parsed_arguments.also_scan]
    )
    joined_import_roots = os.pathsep.join(str(path) for path in import_root_directories)

    if parsed_arguments.print_env:
        print(f'export QML_IMPORT_PATH="{joined_import_roots}"')
        return

    qmlls_config = configparser.ConfigParser()
    qmlls_config.optionxform = str  # keep key case, qmlls is case sensitive
    qmlls_config["General"] = {
        "no-cmake-calls": "true",
        "importPaths": joined_import_roots,
    }
    qmlls_config_file_path = project_root_directory / ".qmlls.ini"
    with qmlls_config_file_path.open("w", encoding="utf-8") as qmlls_config_file:
        qmlls_config.write(qmlls_config_file)

    print(
        f"Wrote {qmlls_config_file_path} with {len(import_root_directories)} import roots:"
    )
    for each_import_root_directory in import_root_directories:
        print(f"  {each_import_root_directory}")


if __name__ == "__main__":
    main()
