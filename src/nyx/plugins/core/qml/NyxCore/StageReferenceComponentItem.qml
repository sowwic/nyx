import QtQuick
import QtQuick.Controls
import NyxEditor.Common

ComponentValue {
    id: stageReferenceRoot

    // The path of a node (/stage/node) or of a component (/stage/node.component), taken
    // as typed: absolute, or relative to the scope of the node.
    label: "Path:"
    evaluateOnFinish: false

    displayDelegate: TextField {
        readOnly: true
        opacity: stageReferenceRoot.editable ? 1.0 : 0.6
        // Red when nothing is found for the reference.
        color: stageReferenceRoot.component && stageReferenceRoot.component.isValid === false ? "firebrick" : palette.text
        text: stageReferenceRoot.maskedText

        TapHandler {
            onDoubleTapped: stageReferenceRoot.requestEdit()
        }
    }

    editDelegate: TextField {
        // Set once, see the Value component.
        Component.onCompleted: {
            text = stageReferenceRoot.textOf(ComponentValue.Raw);
            forceActiveFocus();
            selectAll();
        }
        onAccepted: if (stageReferenceRoot.editing)
            stageReferenceRoot.finishEdit(text)
        onActiveFocusChanged: if (!activeFocus && stageReferenceRoot.editing)
            stageReferenceRoot.finishEdit(text)
        Keys.onEscapePressed: stageReferenceRoot.cancelEdit()
    }
}
