import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import "../Common"

// Note of a node component: the note rendered in its format, or the editor for it.
//
// The item does not change the component. It reports a finished edit through
// `noteCommitted`, and the owner sets the note.
ColumnLayout {
    id: noteRoot

    // Note and its format, a `NoteFormat` value: plain, markdown or html
    property string note: ""
    property string noteFormat: "plain"
    // Formats to pick from, a list of {id, name}
    property var noteFormats: []

    readonly property bool hasNote: note.length > 0
    property bool editing: false

    signal noteCommitted(string text, string noteFormat)

    spacing: 4

    // Qt can render all of the formats, each one with its own text format
    function textFormatOf(format) {
        switch (format) {
        case "markdown":
            return Text.MarkdownText;
        case "html":
            return Text.RichText;
        default:
            return Text.PlainText;
        }
    }

    // Start editing the note, starting from what it is now
    function beginEdit() {
        editing = true;
    }

    function commitEdit() {
        if (!editing)
            return;
        editing = false;
        noteCommitted(noteEditor.text, formatSelector.currentValue);
    }

    // Empty the editor, keeping the edit going
    function clearEditor() {
        noteEditor.clear();
        noteEditor.forceActiveFocus();
    }

    function cancelEdit() {
        editing = false;
    }

    // ---- Rendered note ----
    Text {
        id: renderedNote

        Layout.fillWidth: true
        visible: !noteRoot.editing
        text: noteRoot.note
        textFormat: noteRoot.textFormatOf(noteRoot.noteFormat)
        wrapMode: Text.Wrap
        color: noteRoot.palette.text
        linkColor: noteRoot.palette.link
        onLinkActivated: link => Qt.openUrlExternally(link)

        HoverHandler {
            cursorShape: parent.hoveredLink ? Qt.PointingHandCursor : Qt.ArrowCursor
        }

        TapHandler {
            onDoubleTapped: noteRoot.beginEdit()
        }
    }

    // ---- Editor ----
    ColumnLayout {
        Layout.fillWidth: true
        visible: noteRoot.editing
        spacing: 4

        TextArea {
            id: noteEditor

            Layout.fillWidth: true
            Layout.preferredHeight: 120
            wrapMode: TextEdit.Wrap
            selectByMouse: true
            placeholderText: qsTr("Write a note...")
            Keys.onEscapePressed: noteRoot.cancelEdit()
            // Enter makes a new line, so Ctrl+Enter finishes the edit
            Keys.onPressed: event => {
                if ((event.key === Qt.Key_Return || event.key === Qt.Key_Enter) && (event.modifiers & Qt.ControlModifier)) {
                    noteRoot.commitEdit();
                    event.accepted = true;
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 2

            ComboBox {
                id: formatSelector

                // As wide as the longest format and no wider
                implicitContentWidthPolicy: ComboBox.WidestText
                ToolTip.visible: hovered
                ToolTip.text: qsTr("Format of the note")
                textRole: "name"
                valueRole: "id"
                model: noteRoot.noteFormats
            }

            Item {
                Layout.fillWidth: true
            }

            EditActionButtons {
                clearEnabled: noteEditor.text.length > 0
                onClearRequested: noteRoot.clearEditor()
                onCancelRequested: noteRoot.cancelEdit()
                onApplyRequested: noteRoot.commitEdit()
            }
        }
    }

    // Fill the editor with the current note each time editing starts
    onEditingChanged: {
        if (!editing)
            return;
        noteEditor.text = note;
        const index = formatSelector.indexOfValue(noteFormat);
        formatSelector.currentIndex = index >= 0 ? index : 0;
        noteEditor.forceActiveFocus();
        noteEditor.selectAll();
    }
}
