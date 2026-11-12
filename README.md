# nyx

![Tests](https://github.com/sowwic/nyx/actions/workflows/unit_tests.yml/badge.svg)
![Code](https://github.com/sowwic/nyx/actions/workflows/code_quality.yml/badge.svg)

Nyx is a nodal execution graph written in Python. You build a *stage*: a tree of nodes
whose components are connected by links. Data links move values between components,
flow links decide which node runs next. Running the stage executes the nodes in order.

- **Editor.** A PySide6 application to build, inspect and run stages.
- **Headless runner.** The same stages run from the command line, for batch jobs and CI.
- **Plugins.** New nodes, components, datatypes and notes are plain Python classes
  registered by a plugin. Any Python function can become a node.
- **Bridge.** Stages can send code to other applications (Maya, Blender, anything that
  runs Python) over a small TCP protocol, and use the results in the graph.

Documentation lives in [`docs/`](docs/) (`make mkdocs` serves it locally): a user guide
(config, how a graph executes, datatypes, references, remote nodes, batch mode) and a
developer guide (registry, profiling, writing plugins).

## Installation

Nyx requires Python `3.14.3` (pinned in `pyproject.toml`).

### From source

The project uses [uv](https://docs.astral.sh/uv/).

```sh
git clone https://github.com/sowwic/nyx.git
cd nyx
uv sync --locked --dev
uv run nyx                  # open the editor
```

### As a package in your project

Nyx is not published on PyPI yet, install it from git. `json-config`, `json-config-qt`
and `nyx-bridge` are git dependencies as well, and uv resolves them from the sources
declared in Nyx's `pyproject.toml` only when Nyx is the root project. In your own
project declare them again:

```toml
# pyproject.toml of your project
[project]
requires-python = "==3.14.3"
dependencies = ["nyx"]

[tool.uv.sources]
nyx = { git = "https://github.com/sowwic/nyx", tag = "<release tag>" }
json-config = { git = "https://github.com/sowwic/json-config", tag = "v1.0.5" }
json-config-qt = { git = "https://github.com/sowwic/json-config-qt", tag = "v1.0.0" }
nyx-bridge = { git = "https://github.com/sowwic/nyx-bridge", tag = "v1.0.0" }
```

Copy the tags from the `[tool.uv.sources]` table of the Nyx release you install. pip
ignores `[tool.uv.sources]`, so with plain pip install the git dependencies first:

```sh
pip install "json-config @ git+https://github.com/sowwic/json-config@v1.0.5" \
            "json-config-qt @ git+https://github.com/sowwic/json-config-qt@v1.0.0" \
            "nyx-bridge @ git+https://github.com/sowwic/nyx-bridge@v1.0.0"
pip install "nyx @ git+https://github.com/sowwic/nyx@<release tag>"
```

Then import from the public API, which is what plugins use too. Nothing outside
`nyx.api.v1` is a stable interface.

```python
from nyx.api.v1 import Stage, NYX_REGISTRY, NyxPlugin, NyxPluginManager
```

Running a stage from your own code needs the plugins loaded, which `NyxApplication`
does at startup:

```python
from PySide6 import QtWidgets
from nyx.api.v1 import Stage
from nyx.application import NyxApplication

app = NyxApplication()                 # loads the config and the plugins
stage = Stage()                        # keep the reference, nodes don't hold the stage
stage.import_json("path/to/stage.nyx")
stage.crawler.start()
app.session.shutdown()
```

`NyxApplication` is a `QApplication` without any window. Use `NyxEditorApplication`
(`nyx.application`) when you want the editor.

## Command line

```sh
nyx                               # open the editor
nyx stage run path/to/stage.nyx   # run a stage without the editor
nyx-run-stage path/to/stage.nyx   # the same, as one command
```

`stage run` loads the plugins, starts the bridge server (so stages with Remote Client
nodes can reach Maya, Blender, ...) unless `--no-bridge` is given, and runs the stage
once. `--port N` replaces the configured bridge port for the run. The config is read
but never saved.

Exit codes: `0` the stage ran, `1` it failed (the log names the node), `2` the file was
not found or could not be loaded.

## Standalone build

Nyx can be packaged as an application with PyInstaller. PyInstaller does not
cross-compile, so build on the platform you ship for. The build is driven by
`scripts/build.py`, which works without `make` (use it on Windows):

```sh
uv run python scripts/build.py build-app      # or: make build-app
```

| Command | Result |
| --- | --- |
| `build-app` | Compiles the Qt resources, generates the icons and runs PyInstaller. Output: `dist/nyx.app` (macOS) or `dist/nyx/` (Linux, Windows). |
| `archive-app` | `build-app`, then a zip (macOS, Windows) or tar.gz (Linux): `dist/nyx-<version>-<os>-<arch>`. |
| `test-app` | Runs the built executables: `--help`, a missing file (exit code 2) and a real stage. |
| `install-app` | Copies `dist/nyx.app` to `/Applications` (macOS). |
| `install-cli` | Links the `nyx` and `nyx-run-stage` commands of the app into a bin directory such as `/usr/local/bin`. |
| `qrc`, `icons` | Only compile the Qt resources, or generate the icon file of this platform. |

Each `make` target of the same name calls the script. The version comes from the
`VERSION` file. The built app contains `nyx` (the editor, also `nyx stage run`) and
`nyx-run-stage`. On Linux the folder also gets a `.desktop` entry and an icon.

Plugins outside the application are still found by the built app: set the
`plugin_paths` config value or `NYX_PLUGIN_PATH`, see below.

## Plugins

Everything a stage can contain comes from a plugin: nodes, node components, datatypes,
notes and groups ("util objects") and the graphics items that draw them. The built-in
ones are plugins too:

| Plugin | Provides |
| --- | --- |
| `nyx.stdlib` | The core: flow, value, script, file components and the core nodes (branch, loops, getter/setter, reference, remote nodes, ...), notes and groups. |
| `nyx/plugins/functions/*` | Function nodes for math, strings, lists, dictionaries, paths, files, JSON, regex, dates, random, encoding, logic and system operations. |

A plugin is a folder with a `nyx_plugin.py` file defining a `NyxPlugin` subclass. Nyx
searches for `nyx_plugin.py` files recursively in:

1. the standard library plugin (`nyx.stdlib`),
2. the built-in plugins (`nyx/plugins`),
3. every directory in the `plugin_paths` config value,
4. every directory in the `NYX_PLUGIN_PATH` environment variable (separated by `:` on
   Linux and macOS, `;` on Windows).

Minimal plugin that turns two functions into nodes:

```python
# my_plugins/greetings/nyx_plugin.py
import typing

from nyx.api.v1 import NyxPlugin, NyxPluginManager


def greet(name: str, excited: bool = False) -> str:
    """Build a greeting.

    Args:
        name: Who to greet.
        excited: Add an exclamation mark.
    """
    return f"Hello, {name}{'!' if excited else '.'}"


@NyxPluginManager.register_plugin()
class GreetingsPlugin(NyxPlugin):
    @classmethod
    def get_type_id(cls) -> str:
        return "GreetingsPlugin"

    @classmethod
    def initialize(cls) -> typing.Self:
        plugin = cls()
        plugin.contents.register_function_node(greet, type_id="function:greetings.greet")
        return plugin
```

```sh
NYX_PLUGIN_PATH=/path/to/my_plugins nyx
```

The developer guide shows how to add every kind of plugin content: nodes, function
nodes, components, QML editors for components, datatypes, util objects and graphics
objects.

## Bridge

Many pipelines need a graph to drive other applications: open a scene in Maya, export
from Blender, call a tool that only exists inside a DCC. Nyx does this through the
**bridge**:

- Nyx is the TCP **server**. The external process is the **client** and connects out to
  it, so the application that executes code never listens on a port.
- The server starts with the application (config section `bridge`), generates a token and
  writes its address and token to `bridge.json` in the Nyx data directory. Clients read
  that file to find the server, so no setup is needed on the same machine.
- A **Remote Client** node waits for a matching client to connect. The **Remote Action**
  nodes inside it send a Python script or a `module:function` entry point to that client,
  and the value the code assigns to `result` comes back as the node output.
- The optional **Launch Process** node starts the client itself (for example a headless
  Blender), waits for it to connect and stops it when its nodes are done.

Protocol, client and server classes live in a separate, dependency-free package so they
can be imported inside the Python of a DCC (which cannot install Nyx itself):

| Repository | Purpose |
| --- | --- |
| [sowwic/nyx-bridge](https://github.com/sowwic/nyx-bridge) | Protocol, `BridgeServer` and the base `NyxClient`. Python 3.11+, no dependencies. Never imports Nyx or Qt. |
| [sowwic/nyx-bridge-maya](https://github.com/sowwic/nyx-bridge-maya) | Maya client and a Nyx plugin with Maya-flavoured nodes. |
| [sowwic/nyx-bridge-blender](https://github.com/sowwic/nyx-bridge-blender) | Blender add-on client and a Nyx plugin with Blender-flavoured nodes. |

The DCC plugins are ordinary Nyx plugins: add their folder to `plugin_paths` or
`NYX_PLUGIN_PATH`. See the user guide ("Remote nodes") for how a stage uses the bridge.

## Development

```sh
make check          # ruff + tests
make pytest         # tests only
make lint-fix       # ruff autofix
make format         # ruff format
make qrc            # regenerate resources_rc.py after editing .qrc files or icons
make mkdocs         # documentation server
```

`develop` is the default and PR branch, `main` is the release branch.

## License

MIT, see [LICENSE](LICENSE).
