import QtQuick
import QtQuick.Controls
import NyxEditor.Common

ComponentValue {
    id: scriptItemRoot

    label: "Source:"
    // Entry point or script path, used as typed.
    evaluateOnFinish: false

    displayDelegate: TextField {
        readOnly: true
        opacity: scriptItemRoot.editable ? 1.0 : 0.6
        text: scriptItemRoot.maskedText

        TapHandler {
            onDoubleTapped: scriptItemRoot.requestEdit()
        }
    }

    editDelegate: TextField {
        // Set once, see the Value component.
        Component.onCompleted: {
            text = scriptItemRoot.textOf(ComponentValue.Raw);
            forceActiveFocus();
            selectAll();
        }
        onAccepted: if (scriptItemRoot.editing)
            scriptItemRoot.finishEdit(text)
        onActiveFocusChanged: if (!activeFocus && scriptItemRoot.editing)
            scriptItemRoot.finishEdit(text)
        Keys.onEscapePressed: scriptItemRoot.cancelEdit()
    }

    // Ask for a script file. Done by the controller: a QML FileDialog would open
    // an extra window when shown from the widget hosting this QML.
    function selectScriptFile() {
        const path = controller.selectFile(qsTr("Select script"), qsTr("Python scripts (*.py);;All files (*)"), textOf(ComponentValue.Raw));
        if (path.length > 0)
            finishEdit(path);
    }

    ToolButton {
        text: "…"
        enabled: scriptItemRoot.editable
        ToolTip.visible: hovered
        ToolTip.text: qsTr("Select script file")
        onClicked: scriptItemRoot.selectScriptFile()
    }
}
