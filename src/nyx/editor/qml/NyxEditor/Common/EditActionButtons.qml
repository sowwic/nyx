import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

// Clear, cancel and apply buttons for the editor of a text. They only report the click,
// what to do is up to the editor.
RowLayout {
    id: buttonsRoot

    // The text can be cleared, false while there is none
    property bool clearEnabled: true

    signal clearRequested
    signal cancelRequested
    signal applyRequested

    spacing: 2

    ToolButton {
        icon.source: "qrc:/icons/delete.png"
        enabled: buttonsRoot.clearEnabled
        ToolTip.visible: hovered
        ToolTip.text: qsTr("Clear the text")
        onClicked: buttonsRoot.clearRequested()
    }

    ToolButton {
        icon.source: "qrc:/icons/cross.png"
        ToolTip.visible: hovered
        ToolTip.text: qsTr("Cancel (Esc)")
        onClicked: buttonsRoot.cancelRequested()
    }

    ToolButton {
        icon.source: "qrc:/icons/check.png"
        ToolTip.visible: hovered
        ToolTip.text: qsTr("Apply (Ctrl+Enter)")
        onClicked: buttonsRoot.applyRequested()
    }
}
