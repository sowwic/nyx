pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import NyxEditor.Common

ComponentValue {
    id: stageObjectPathRoot

    readonly property bool hasInputConnection: component ? component.inputLinks.length > 0 : false

    // The path of a node (/stage/node) or of a component (/stage/node.component), taken
    // as typed: absolute, or relative to the scope of the node.
    label: "Object:"
    evaluateOnFinish: false
    // A linked path gets its value from its source.
    editable: component ? component.isEditable && !hasInputConnection : false

    displayDelegate: TextField {
        readOnly: true
        opacity: stageObjectPathRoot.editable ? 1.0 : 0.6
        // Red when nothing is found for the path.
        color: stageObjectPathRoot.component && stageObjectPathRoot.component.isValid === false ? "firebrick" : palette.text
        text: stageObjectPathRoot.maskedText

        TapHandler {
            onDoubleTapped: stageObjectPathRoot.requestEdit()
        }
    }

    editDelegate: TextField {
        // Set once, see the Value component.
        Component.onCompleted: {
            text = stageObjectPathRoot.textOf(ComponentValue.Raw);
            forceActiveFocus();
            selectAll();
        }
        onAccepted: if (stageObjectPathRoot.editing)
            stageObjectPathRoot.finishEdit(text)
        onActiveFocusChanged: if (!activeFocus && stageObjectPathRoot.editing)
            stageObjectPathRoot.finishEdit(text)
        Keys.onEscapePressed: stageObjectPathRoot.cancelEdit()
    }

    EditButton {
        editor: stageObjectPathRoot
    }
}
