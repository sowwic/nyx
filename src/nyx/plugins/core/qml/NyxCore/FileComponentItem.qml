pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import NyxEditor.Common

ComponentValue {
    id: fileItemRoot

    label: "File:"
    // The path is used as typed.
    evaluateOnFinish: false

    displayDelegate: TextField {
        readOnly: true
        opacity: fileItemRoot.editable ? 1.0 : 0.6
        text: fileItemRoot.maskedText

        TapHandler {
            onDoubleTapped: fileItemRoot.requestEdit()
        }
    }

    editDelegate: TextField {
        // Set once, see the Value component.
        Component.onCompleted: {
            text = fileItemRoot.textOf(ComponentValue.Raw);
            forceActiveFocus();
            selectAll();
        }
        onAccepted: if (fileItemRoot.editing)
            fileItemRoot.finishEdit(text)
        onActiveFocusChanged: if (!activeFocus && fileItemRoot.editing)
            fileItemRoot.finishEdit(text)
        Keys.onEscapePressed: fileItemRoot.cancelEdit()
    }

    // Ask for a file. Done by the controller: a QML FileDialog would open an extra
    // window when shown from the widget hosting this QML.
    function selectFile() {
        const path = controller.selectFile(qsTr("Select file"), qsTr("All files (*)"), textOf(ComponentValue.Raw));
        if (path.length > 0)
            finishEdit(path);
    }

    EditButton {
        editor: fileItemRoot
    }

    ToolButton {
        icon.source: "qrc:/icons/folder_open"
        enabled: fileItemRoot.editable
        ToolTip.visible: hovered
        ToolTip.text: qsTr("Select file")
        onClicked: fileItemRoot.selectFile()
    }
}
