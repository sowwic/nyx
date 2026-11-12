import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import NyxEditor.Common

ComponentValue {
    id: commentItemRoot

    // Pure text: edited as typed. It is shown as Markdown.
    evaluateOnFinish: false

    displayDelegate: Text {
        readonly property bool isEmpty: commentItemRoot.maskedText.length === 0

        text: isEmpty ? qsTr("Empty comment") : commentItemRoot.maskedText
        textFormat: isEmpty ? Text.PlainText : Text.MarkdownText
        wrapMode: Text.Wrap
        font.italic: isEmpty
        color: palette.text
        linkColor: palette.link
        opacity: isEmpty || !commentItemRoot.editable ? 0.6 : 1.0
        onLinkActivated: link => Qt.openUrlExternally(link)

        TapHandler {
            onDoubleTapped: commentItemRoot.requestEdit()
        }
    }

    editDelegate: ColumnLayout {
        id: editRoot

        // What is typed, for the owner to read
        property alias text: commentEditor.text

        spacing: 4

        TextArea {
            id: commentEditor

            Layout.fillWidth: true
            Layout.preferredHeight: 120
            wrapMode: TextEdit.Wrap
            selectByMouse: true
            placeholderText: qsTr("Write a comment...")

            // Set once, see the Value component.
            Component.onCompleted: {
                text = commentItemRoot.textOf(ComponentValue.Raw);
                forceActiveFocus();
                selectAll();
            }
            // Enter inserts a new line, so Ctrl+Enter finishes the edit.
            Keys.onPressed: event => {
                if (commentItemRoot.editing && (event.key === Qt.Key_Return || event.key === Qt.Key_Enter) && (event.modifiers & Qt.ControlModifier)) {
                    commentItemRoot.finishEdit(text);
                    event.accepted = true;
                }
            }
            Keys.onEscapePressed: commentItemRoot.cancelEdit()
        }

        EditActionButtons {
            Layout.alignment: Qt.AlignRight
            clearEnabled: commentEditor.text.length > 0
            onClearRequested: {
                commentEditor.clear();
                commentEditor.forceActiveFocus();
            }
            onCancelRequested: commentItemRoot.cancelEdit()
            onApplyRequested: commentItemRoot.finishEdit(commentEditor.text)
        }
    }

    // The edit buttons of the editor take over while editing
    EditButton {
        editor: commentItemRoot
        visible: commentItemRoot.editable && !commentItemRoot.editing
    }
}
