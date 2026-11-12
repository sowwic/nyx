# New QML for a component

The inspector and the nodes of the editor show components with small QML items. A
component type without its own item uses a generic one (`NodeComponentItem.qml`). To give a
type a custom editor, put a QML file in your plugin and name it in `EDITOR_QML`.

## Files

```text
studio_tools/
├── nyx_plugin.py                  QML_MODULE_NAME = "StudioTools"
└── qml/                           <- NyxPlugin.qml_directory(), an import root
    └── StudioTools/               <- the module, same name as QML_MODULE_NAME
        ├── qmldir
        └── ColorComponentItem.qml
```

```qml
// qml/StudioTools/qmldir
module StudioTools

ColorComponentItem 1.0 ColorComponentItem.qml
```

```python
class ColorComponent(NodeComponent):
    EDITOR_QML = "ColorComponentItem"     # file name without .qml
```

```python
class StudioTools(NyxPlugin):
    QML_MODULE_NAME = "StudioTools"       # folder inside qml/
```

How it is found: when a component needs its editor, Nyx asks the registry for
`<import root>/StudioTools/ColorComponentItem.qml` (`NYX_REGISTRY.resolve_qml_source`),
searching the registered import roots. The `qml` folder of every enabled plugin is an
import root, the editor's own `qml` folder is one too. A missing file raises
`FileNotFoundError` with the roots it tried.

The file is loaded by its path, as an item inside the component's row in the inspector and
on the node, and only while the component is expanded. The `qmldir` makes the type
importable by name (`import StudioTools`) for other QML files and for the QML language
server; keep it up to date like the stdlib does. If loading fails, the log shows
`Editor failed to load: <file>`.

The QML engine of the editor knows the import roots, so your files can
`import NyxEditor.Common` for the shared building blocks.

## The easy way: derive from `ComponentValue`

`ComponentValue` (from `NyxEditor.Common`) holds the editing logic of a value: the
component, the editing state, the masks of the value, and what happens when the user
finishes typing. You only provide *what is shown* with delegates.

```qml
// qml/StudioTools/ColorComponentItem.qml
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import NyxEditor.Common

ComponentValue {
    id: colorItemRoot

    label: "Color:"
    // The text is a color, keep it as typed instead of evaluating it as an expression.
    evaluateOnFinish: false

    // Shown when not editing
    displayDelegate: Row {
        spacing: 6

        Rectangle {
            width: 18
            height: 18
            radius: 3
            border.color: palette.mid
            color: colorItemRoot.maskedText
        }

        Label {
            text: colorItemRoot.maskedText
            opacity: colorItemRoot.editable ? 1.0 : 0.6

            TapHandler {
                onDoubleTapped: colorItemRoot.requestEdit()
            }
        }
    }

    // Shown while editing the raw value
    editDelegate: TextField {
        // Set once: what is typed must not be replaced by a binding.
        Component.onCompleted: {
            text = colorItemRoot.textOf(ComponentValue.Raw);
            forceActiveFocus();
            selectAll();
        }
        onAccepted: if (colorItemRoot.editing)
            colorItemRoot.finishEdit(text)
        onActiveFocusChanged: if (!activeFocus && colorItemRoot.editing)
            colorItemRoot.finishEdit(text)
        Keys.onEscapePressed: colorItemRoot.cancelEdit()
    }

    // Children are placed after the delegate
    EditButton {
        editor: colorItemRoot
    }
}
```

### What `ComponentValue` gives you

| Member | Meaning |
| --- | --- |
| `component` | The component being edited (model row): `component.rawValue`, `.cachedValue`, `.displayValue`, `.isEditable`, `.inputLinks`, `.datatypeId`, ... |
| `controller` | The components controller; `controller.setComponentValue(...)` is what `finishEdit` ends up calling. Controllers can offer more, for instance `selectFile` that the File item uses. |
| `label` | Text before the value. |
| `editable` | Whether editing is allowed. Defaults to `component.isEditable`; bind it to `&& !hasInputConnection` to forbid editing a linked value (the Value item does). |
| `editing` | In edit mode. |
| `evaluateOnFinish` | `true`: the typed text is evaluated as a Python expression when set. `false`: it is stored as typed. |
| `displayDelegate`, `editDelegate`, `cachedDelegate` | The `Component`s shown for each state, see the rules below. |
| `restingMask` | Value shown when not editing: `ComponentValue.Display` (default), `Raw` or `Cached`. |
| `maskedText` | The text of the current mask. `textOf(mask)` reads any of them. |
| `requestEdit()`, `beginEdit()`, `finishEdit(text)`, `cancelEdit()` | Drive the edit state. `finishEdit` sends the new text to the component unless it didn't change. |
| `field` | The item the current delegate created. |
| `default property alias content` | Items declared inside `ComponentValue` are placed after the delegate. |

Which delegate shows: editing selects `editDelegate`; otherwise a `Cached` mask uses
`cachedDelegate` (falling back to `displayDelegate`) and any other mask uses
`displayDelegate`.

Ready-made building blocks in `NyxEditor.Common`: `EditButton` (edit/confirm button
following `editor.editing`), `DatatypeSelector` (pick the datatype of a component), and
`CollapsibleFrame`, `DescriptionToolTip`, `TagsList` and others used by the palettes. Read
`editor/qml/NyxEditor/Common` and the items in `stdlib/qml/NyxStdlib` (`ValueComponentItem`,
`FileComponentItem`, `CommentComponentItem`, `FlowComponentItem`) as examples. The Comment
item renders Markdown, the File item adds a file dialog button.

## A freer editor

If `ComponentValue` doesn't fit, your root item can be any `Item`. It must declare
`property var component`, which the editor binds to the model row of the component, and can
reach the components controller like `ComponentValue` does (`root.componentsController`).
Keep the item small: one is created for every expanded component on screen.

## Checking it

1. `make qrc` is **not** needed for QML files in a plugin folder; they are read from disk.
   It is needed if your QML refers to icons from a `.qrc` you changed.
2. Start the editor with your plugin on `NYX_PLUGIN_PATH`, add the component to a node, expand
   it and look at the log. A QML error is printed there with the file and line.
3. In the repository, `generate_qmlls_config.py` writes the config the QML language server
   needs to resolve the `NyxEditor.*` imports while you edit.
