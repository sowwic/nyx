import QtQuick
import QtQuick.Controls

// Button next to the value of a `ComponentValue`: an edit icon to start editing, a check
// icon to confirm while editing. What it shows follows `editor.editing`, so editing
// started by a double click or ended by Enter or Escape is reflected too.
ToolButton {
    id: buttonRoot

    // The ComponentValue this button belongs to
    property var editor
    readonly property bool editing: editor ? editor.editing : false
    readonly property url iconSource: editing ? "qrc:/icons/check.png" : "qrc:/icons/edit.png"

    // Nothing to do for a value that can't be edited
    visible: editor ? editor.editable : false
    // Taking the focus would end the edit before the click is handled, and the click
    // would start it again
    focusPolicy: Qt.NoFocus
    icon.source: iconSource
    ToolTip.visible: hovered
    ToolTip.text: editing ? qsTr("Apply") : qsTr("Edit")

    onClicked: {
        if (!editor)
            return;
        if (editing && editor.field)
            editor.finishEdit(editor.field.text);
        else
            editor.requestEdit();
    }
}
