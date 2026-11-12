# Writing plugins

Everything that a stage can contain comes from a plugin, including the content that ships
with Nyx. This section shows how to add each kind of content:

| I want to add | Page |
| --- | --- |
| A new kind of node | [New node](node.md) |
| A node that calls a Python function | [New function node](function-node.md) |
| A new kind of component (a plug on a node) | [New component](component.md) |
| A custom editor for a component in the UI | [New QML for a component](component-qml.md) |
| A new datatype | [New datatype](datatype.md) |
| A note-like object that doesn't execute | [New util object](util-object.md) |
| A custom drawing for a util object | [New graphics object](graphics-object.md) |

Import from `nyx.api.v1` only. It is the public, versioned API; `nyx.core` and
`nyx.editor` can change without notice. Look at `nyx/stdlib` (the core plugin) and
`nyx/plugins/functions/*` for working examples of everything below.

## Anatomy of a plugin

A plugin is a folder containing a `nyx_plugin.py`. The file defines one subclass of
`NyxPlugin` and registers it with a decorator.

```text
my_plugins/                      <- put this folder in plugin_paths or NYX_PLUGIN_PATH
└── studio_tools/
    ├── nyx_plugin.py            <- found by the loader (any depth below the path)
    ├── nodes/
    │   └── greeter.py
    ├── components/
    │   └── color.py
    ├── qml/                     <- QML import root of the plugin
    │   └── StudioTools/         <- QML module, named by QML_MODULE_NAME
    │       ├── qmldir
    │       └── ColorComponentItem.qml
    └── resources/
        └── icons/
```

```python
# studio_tools/nyx_plugin.py
import typing

from nyx.api.v1 import NyxPlugin, NyxPluginManager

from .nodes.greeter import GreeterNode
from .components.color import ColorComponent


@NyxPluginManager.register_plugin()
class StudioTools(NyxPlugin):
    """Tools of the studio."""

    QML_MODULE_NAME = "StudioTools"

    @classmethod
    def get_type_id(cls) -> str:
        """str: unique plugin id."""
        return "StudioTools"

    @classmethod
    def get_palette_name(cls) -> str:
        """str: name of the section of the palette holding the types of the plugin."""
        return "Studio"

    @classmethod
    def initialize(cls) -> typing.Self:
        """Create the plugin and list its content.

        Returns:
            typing.Self: initialized plugin.
        """
        plugin = cls()
        plugin.contents.node_components = [ColorComponent]
        plugin.contents.nodes = [GreeterNode]
        return plugin
```

The pieces:

- `@NyxPluginManager.register_plugin()` registers the **class** when the file is imported.
  A plugin with no `get_type_id`, or with an id that is already taken, is logged and
  skipped.
- `get_type_id()` is the unique id of the plugin. It is stored in saved stages
  (`source_plugin`), so don't change it once stages exist.
- `get_type_display_name()` (defaults to the id) and `get_palette_name()` (defaults to the
  display name) are used by the UI. `get_tags()` can return a set of tags.
- `initialize()` is called once at startup. Create the plugin and fill `plugin.contents`
  (`NyxPluginContents`):

| Field | Holds |
| --- | --- |
| `nodes` | node classes |
| `node_components` | component classes |
| `datatypes` | `Datatype` instances |
| `util_objects` | util object classes |
| `graphics_objects` | graphics item classes (QGraphicsItem subclasses with a `get_type_id`) |
| `register_function_node(func)` | method that generates a node class from a function and adds it to `nodes` |
| `register_function_module(module, namespace)` | the same for every public function of a module |

- `QML_MODULE_NAME` is the name of the QML module in the plugin's `qml` folder, needed
  only when a component has a custom QML editor.

The plugin class also helps locating files next to it: `root_directory()`,
`qml_directory()`, `resources_directory()`, `icons_directory()` and `get_icon(name)`.

## Where plugins are found

`NyxPluginLoader` searches recursively for `nyx_plugin.py` in `nyx.stdlib`, the built-in
`nyx/plugins`, every directory in the `plugin_paths` config value, and every directory in
the `NYX_PLUGIN_PATH` environment variable. See [The registry](../registry.md) for what
happens next.

```sh
NYX_PLUGIN_PATH=/studio/nyx_plugins nyx
NYX_PLUGIN_PATH=/studio/nyx_plugins nyx stage run nightly.nyx
```

Because the plugin file is loaded as part of a package named after its folder, use
relative imports between your files (`from .nodes.greeter import GreeterNode`), and keep
the folder name unique among your plugins.

## Type ids

Every node, component, datatype, util object and graphics object has a **type id**: a
string stored in saved stages. Rules to follow:

- Use `namespace:name`, with a namespace of your own (`studio:greeter`). `core:` and
  `function:` are taken.
- They have to be unique per category; a duplicate is logged and the first one wins.
- They are part of your file format. Renaming one breaks stages that use it.

## Icons

`get_type_icon()` returns a Qt resource path such as `:/icons/function`. The built-in
icons (`:/icons/...`, `:/core/icons/...`) are available to every plugin. To ship your
own, add a `.qrc` file, compile it with `pyside6-rcc` and import the generated module
from your `nyx_plugin.py` (the stdlib does `from .resources import resources_rc`). Use a
unique prefix in the `.qrc` so paths don't clash.

## Testing a plugin

The repository's test suite shows the pattern. `tests/conftest.py` starts the
application offscreen, and the `with_plugins` marker initializes the plugins named in it:

```python
import pytest

from nyx.api.v1 import Stage, commands

@pytest.mark.with_plugins("NyxStdlib", "StudioTools")
def test_greeter(nyx_app):
    stage = Stage()  # keep the reference: commands hold their stage weakly
    command = commands.CreateNodeCommand(stage=stage, type_id="studio:greeter")
    stage.push_command(command)
    greeter = command.result_node

    stage.crawler.start(greeter)
    assert greeter.greeting_cpnt.pull_value() == "Hello, World."
```

Make sure your plugin folder is on `NYX_PLUGIN_PATH` when the tests run so the loader
finds it. Every change to a stage goes through a command (`push_command`), which is also
what the editor does, so undo works for it. `tests/stage_helpers.py` has small helpers
that wrap this.

## Checklist

- [ ] `nyx_plugin.py` registers exactly one `NyxPlugin` subclass, with a unique id.
- [ ] Type ids have your namespace.
- [ ] Imports come from `nyx.api.v1`.
- [ ] Every class has `get_type_id`, `get_type_display_name` and a `get_description`.
- [ ] Nodes work when their stage is saved and loaded again, see
  [New node](node.md#saving-and-loading).
- [ ] Google-style docstrings (`Args:`, `Returns:`, `Raises:`), they become the
  descriptions in the UI for function nodes.
