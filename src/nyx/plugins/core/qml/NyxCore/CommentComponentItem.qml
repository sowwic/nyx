import QtQuick
import QtQuick.Controls
import NyxEditor.Common

ComponentValue {
    id: commentItemRoot

    // Pure text: displayed and edited as typed.
    evaluateOnFinish: false

    displayDelegate: TextArea {
        readOnly: true
        wrapMode: TextEdit.Wrap
        opacity: commentItemRoot.editable ? 1.0 : 0.6
        text: commentItemRoot.maskedText

        TapHandler {
            onDoubleTapped: commentItemRoot.requestEdit()
        }
    }

    editDelegate: TextArea {
        wrapMode: TextEdit.Wrap

        // Set once, see the Value component.
        Component.onCompleted: {
            text = commentItemRoot.textOf(ComponentValue.Raw);
            forceActiveFocus();
            selectAll();
        }
        onActiveFocusChanged: if (!activeFocus && commentItemRoot.editing)
            commentItemRoot.finishEdit(text)
        // Enter inserts a new line, so Ctrl+Enter finishes the edit.
        Keys.onPressed: event => {
            if (commentItemRoot.editing && (event.key === Qt.Key_Return || event.key === Qt.Key_Enter) && (event.modifiers & Qt.ControlModifier)) {
                commentItemRoot.finishEdit(text);
                event.accepted = true;
            }
        }
        Keys.onEscapePressed: commentItemRoot.cancelEdit()
    }
}
