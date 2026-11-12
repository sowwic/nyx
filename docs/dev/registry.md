# The registry

`NYX_REGISTRY` is the single place where Nyx keeps everything plugins provide. When a
stage file says a node has `type_id: "core:branch"`, the registry is what turns that
string into a class. It is a module-level instance of `NyxRegistry`:

```python
from nyx.api.v1 import NYX_REGISTRY
```

## What it holds

| Attribute | Content | Key |
| --- | --- | --- |
| `plugins` | `NyxPluginRegistryEntry` per discovered plugin: the class, whether it is enabled, and the initialized instance | plugin type id |
| `nodes` | node classes | node type id |
| `node_components` | component classes | component type id |
| `datatypes` | `Datatype` instances | datatype type id |
| `util_objects` | util object classes | util object type id |
| `graphics_objects` | graphics item classes, the built-in ones included | graphics object id |
| `qml_import_root_directories` | directories QML modules are imported from | n/a |

All keys are plain strings with a namespace, `"<namespace>:<name>"` (`core:value`,
`function:math.add`), and must be unique inside their category. A duplicate is logged as
an error and skipped: **the first registration wins**.

## Lifecycle

Content gets into the registry in three steps. They run in this order at application
startup (`NyxApplication.__init__`, between `pre_initialize` and `post_initialize`).

### 1. Discovery and registration of plugin classes

`NyxPluginLoader` finds `nyx_plugin.py` files and imports them. Importing is enough to
register the plugin *class*: the `@NyxPluginManager.register_plugin()` decorator
validates it (it must have a `type_id`, and the id must be new) and adds a
`NyxPluginRegistryEntry` to `NYX_REGISTRY.plugins` through `add_plugin`. A plugin that
fails validation is logged and left out; the others continue.

The loader searches, in this order:

1. the directory of `nyx.stdlib`,
2. `nyx/plugins`,
3. the `plugin_paths` config value,
4. the `NYX_PLUGIN_PATH` environment variable.

Plugin files inside the `nyx` package are imported by their real module name (so
`from nyx.stdlib.nodes.value import ...` in another plugin gets the same class the
registry holds). Files outside of it are loaded with their folder registered as a
package, so relative imports (`from . import operations`) work.

### 2. Initialization

`NyxPluginManager.initialize_plugins()` calls `initialize()` on each enabled entry that has
no instance yet. The plugin builds its `contents` (`NyxPluginContents`) and the entry
keeps the instance. Passing `include=[...]` enables exactly the listed plugins (this is
what the `with_plugins` test marker does).

### 3. Registering the contents

`NYX_REGISTRY.register_plugin_content()` rebuilds everything from the initialized,
enabled plugins:

1. clear `nodes`, `node_components`, `datatypes`, `util_objects`, and reset
   `graphics_objects` to the built-in ones,
2. register the core datatypes (`core_types.CORE_DATATYPES`),
3. for each plugin entry, in discovery order: node components, nodes, datatypes, util
   objects, graphics objects and its QML import root.

Registering a node, component or util object class also sets `SOURCE_PLUGIN` on it to the
plugin entry. Serialization writes the plugin id as `source_plugin` into the file, and the
QML resolver uses the plugin's `QML_MODULE_NAME` to find a component's editor. Because
the core plugin is discovered first, **its ids can't be overridden** by another plugin.

!!! note
    Step 3 starts by clearing, so registry content isn't additive across calls: it is
    always the contents of the currently enabled plugins. Don't add classes to the
    registry's dictionaries directly.

## Lookups

| Method | Returns |
| --- | --- |
| `get_node_cls(type_id)` | the node class. Logs an error and returns `None` when unknown. |
| `get_node_component_cls(type_id)` | the component class, or `None`. |
| `get_util_object_cls(type_id)` | the util object class. Logs an error and returns `None` when unknown. |
| `get_graphics_object_cls(type_id)` | the graphics item class, or `None`. |
| `get_datatype(type_id)` | the `Datatype`, or `None`. |
| `resolve_datatype(type_id)` | the `Datatype`, falling back to `OBJECT_DATATYPE` for a missing or unknown id (logged). Use this when reading files. |
| `infer_datatype(value)` | first registered datatype whose Python type is exactly `type(value)`, else `Object`. |
| `find_datatype_for_type(python_type)` | datatype claiming that Python type, or `None`. Used for the type hints of function nodes. |
| `iter_datatypes()`, `iter_node_components()`, `iter_plugins()` | iterate the registered content. |
| `resolve_qml_source(module_uri, type_name)` | path of `<root>/<module/path>/<type_name>.qml` in the first import root that has it, else `FileNotFoundError`. |
| `register_builtin_graphics_object(type_id, cls)` | for the editor: graphics items that exist whatever plugins are enabled (nodes, plugs, links). |

`infer_datatype` and `find_datatype_for_type` return the *first* match in registration
order, so two datatypes with the same Python type resolve to the one registered earlier.

## QML import roots

The registry also keeps the list of QML import roots: the editor's own `qml` folder
first, then the `qml` folder next to each enabled plugin file
(`NyxPlugin.qml_directory()`) as it registers. `NyxEditorApplication` hands the list to
the QML engine (`sync_qml_import_paths`). See
[A QML editor for a component](plugins/component-qml.md).

## Using the registry from your code

```python
from nyx.api.v1 import NYX_REGISTRY

for type_id, node_cls in NYX_REGISTRY.nodes.items():
    print(type_id, node_cls.get_type_display_name(), sorted(node_cls.get_tags()))

NYX_REGISTRY.get_node_cls("core:branch")
NYX_REGISTRY.get_datatype("core:int").accepts(NYX_REGISTRY.get_datatype("core:float"))
```

`NYX_REGISTRY.clear()` empties everything. It exists for tests.
