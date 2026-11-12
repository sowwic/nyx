# Developer Guide

This guide is for people who extend Nyx with plugins or work on Nyx itself.

## Pages

| Page | What you learn |
| --- | --- |
| [The registry](registry.md) | How plugins are discovered and how their content ends up in `NYX_REGISTRY`. |
| [Link pins](link-pins.md) | How pins on links are stored, changed, saved and drawn. |
| [Profiling](profiling.md) | Timing and call profiling with `NYX_PROFILING`. |
| [Writing plugins](plugins/index.md) | The anatomy of a plugin, and pages for each kind of content: [node](plugins/node.md), [function node](plugins/function-node.md), [component](plugins/component.md), [QML for a component](plugins/component-qml.md), [datatype](plugins/datatype.md), [util object](plugins/util-object.md), [graphics object](plugins/graphics-object.md). |
| API reference | Generated from the docstrings of `nyx.core`, `nyx.editor` and the rest of the package (see the navigation). |

## Architecture in one page

```text
nyx
├── core         Qt backend, no widgets
│   ├── Stage                owns the undo stack, the node tree and the crawler
│   ├── Node / NodeComponent QStandardItems; components are connected by Links
│   ├── UtilObject           notes and groups
│   ├── commands/            every change is a QUndoCommand (NyxCommand)
│   ├── StageCrawler         executes a stage; ExecutionChain says which nodes the flow reaches
│   ├── plugin_subsystem/    loader, manager and the registry
│   └── session.py           NyxSession: config, open stages, bridge server
├── api.v1       the public API: plugins import from here
├── stdlib       the core plugin: nodes, components, notes, groups
├── plugins      built-in function node plugins
├── editor       widgets, the graphics scene, views and QML UI
├── cli.py       nyx, nyx stage run, nyx-run-stage
└── static       enums, variables and the paths of user files
```

Points to keep in mind when working on the code:

- **Everything that changes a stage is a command.** Commands derive from `NyxCommand`
  (`core/commands/`), hold the stage weakly, say which nodes they touch (`target_nodes`, so
  nodes of a reference can be protected) and set `MODIFIES_STRUCTURE` when they add, remove
  or redefine nodes or components. Use them from plugins and tools too:
  `stage.push_command(command)`.
- **Stages are held weakly.** Keep a reference to a `Stage` you create, or its nodes and
  commands lose it.
- **`nyx.api.v1` is the contract.** Add to it when a plugin needs something new, don't let
  plugins reach into `nyx.core`.
- **Application startup** is `NyxApplication.__init__`: register built-in content,
  `pre_initialize()`, load plugins, `post_initialize()`. Subclasses override the hooks
  (`NyxEditorApplication` shows the splash screen in `pre_initialize` and builds the QML
  engine and main window in `post_initialize`) rather than reordering around `super().__init__`.
  Prefer adding a no-op `pre_*`/`post_*` hook to a base class over changing its constructor.
- **Paths of user files** are all defined in `nyx/static/paths.py`.

## Working on Nyx

```sh
uv sync --locked --dev       # install
make check                   # ruff + tests
make pytest                  # tests only: uv run pytest tests
make lint-fix                # ruff autofix (line length 89, rules E, F, UP)
make qrc                     # regenerate resources_rc.py after editing .qrc files or icons
make mkdocs                  # this documentation, with live reload
```

Tests use `QT_QPA_PLATFORM=offscreen`. Tests of the editor start the editor application
with pytest-qt, and the `with_plugins(*plugin_ids)` marker initializes plugins for a test.
Coverage is always on; the `output_dir` fixture writes under `test_output/`.

Code conventions: Google-style docstrings (`Args:`, `Returns:`, `Raises:`), new widgets
create their parts in `_create_actions`, `_create_widgets`, `_create_layouts` and
`_create_connections`, all run from `__init__`. `develop` is the default and PR branch.

## Building the documentation

The site is built with MkDocs Material. The API reference is generated from docstrings by
`mkdocs-autoapi` and `mkdocstrings`, excluding `stdlib` and `plugins`, so write docstrings
for everything in `nyx.core`, `nyx.api` and `nyx.editor`.

```sh
make mkdocs                  # serve with live reload
uv run mkdocs build          # build into site/
```
