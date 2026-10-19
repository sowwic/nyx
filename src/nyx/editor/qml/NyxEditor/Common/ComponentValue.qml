import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

// Editor for the value of a node component, with masks of the value.
//
// The editor holds the state and the logic; what is shown comes from delegates, one
// per state, supplied by the component type:
//   - editing                          -> `editDelegate`    (raw value)
//   - not editing, mask is Cached      -> `cachedDelegate`  (falls back to display)
//   - not editing, any other mask      -> `displayDelegate` (display value by default)
//
// A delegate is a Component. Declared in the file of the editor's user, it reaches the
// editor by its id. The root item may also declare `property var editor`, which is set
// right after the item is created (not yet in Component.onCompleted). It reads
// `editor.maskedText` (or `editor.textOf(mask)`) and talks back through:
//   - editor.requestEdit()    emits `editRequested`, which starts editing by default
//   - editor.finishEdit(text) emits `editFinished(text)` and leaves editing
//   - editor.cancelEdit()     leaves editing without a value
//
// `editFinished` sets the value of the component through the components controller.
// Children declared inside the editor are placed after the delegate (buttons, ...).
ColumnLayout {
    id: editorRoot

    enum ValueMask {
        Display,
        Raw,
        Cached
    }

    // Row of the component in the components model.
    property var component
    property var controller: root.componentsController

    property string label: ""
    // Value is evaluated when set, otherwise it is pushed as it was typed.
    property bool evaluateOnFinish: false
    property bool editable: component ? component.isEditable === true : false
    // Switch to editing on `editRequested`. Disable to handle the request instead.
    property bool autoBeginEdit: true

    // Delegates, see above.
    property Component displayDelegate
    property Component editDelegate
    property Component cachedDelegate

    // Mask shown while not editing. Editing always shows the raw value.
    property int restingMask: ComponentValue.Display
    property bool editing: false
    readonly property int mask: editing ? ComponentValue.Raw : restingMask

    readonly property string maskedText: textOf(mask)
    readonly property Component currentDelegate: {
        if (editing)
            return editDelegate;
        if (mask === ComponentValue.Cached && cachedDelegate)
            return cachedDelegate;
        return displayDelegate;
    }
    // Item currently shown by the delegate loader.
    readonly property Item field: delegateLoader.item

    default property alias content: contentRow.data

    signal editRequested
    signal editFinished(string value)

    spacing: 4

    function textOf(valueMask) {
        if (!component)
            return "";
        let value;
        switch (valueMask) {
        case ComponentValue.Raw:
            value = component.rawValue;
            break;
        case ComponentValue.Cached:
            value = component.cachedValue;
            break;
        default:
            value = component.displayValue;
        }
        return (value === null || value === undefined) ? "" : String(value);
    }

    // Ask to edit. Ignored when the component can't be edited.
    function requestEdit() {
        if (!editable || editing)
            return;
        editRequested();
    }

    // Start editing the raw value.
    function beginEdit() {
        if (!editable)
            return;
        editing = true;
    }

    // Leave editing and report the new value.
    function finishEdit(value) {
        if (!editable)
            return;
        editing = false;
        editFinished(value);
    }

    // Leave editing and drop what was typed.
    function cancelEdit() {
        editing = false;
    }

    onEditRequested: {
        if (autoBeginEdit)
            beginEdit();
    }
    onEditFinished: value => {
        if (!controller || !component)
            return;
        if (value === textOf(ComponentValue.Raw))
            return;
        controller.setComponentValue(component.index, value, !evaluateOnFinish);
    }

    RowLayout {
        Layout.fillWidth: true

        Label {
            visible: editorRoot.label.length > 0
            text: editorRoot.label
        }

        Loader {
            id: delegateLoader

            Layout.fillWidth: true
            sourceComponent: editorRoot.currentDelegate
            onLoaded: {
                if (item && "editor" in item)
                    item.editor = editorRoot;
            }
        }

        RowLayout {
            id: contentRow
        }
    }
}
