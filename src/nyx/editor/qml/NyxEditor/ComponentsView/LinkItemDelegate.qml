import QtQuick
import QtQuick.Controls

ItemDelegate {
    id: itemRoot

    // Emitted when the "x" button is clicked, to remove the link.
    signal unlinkRequested

    property string linkDirection
    property string linkPath

    height: 30

    contentItem: Row {
        anchors.verticalCenter: parent.verticalCenter
        spacing: 0

        Rectangle {
            width: 50
            height: parent.height
            color: "#83a5e8"

            Label {
                id: directionLabel
                anchors.centerIn: parent
                text: itemRoot.linkDirection
                color: "#172238"
            }
        }

        Rectangle {
            width: pathLabel.implicitWidth + 16
            height: parent.height
            color: "transparent"

            Label {
                id: pathLabel
                anchors.centerIn: parent
                text: itemRoot.linkPath
            }
        }

        ToolButton {
            id: unlinkButton
            objectName: "unlinkButton"

            width: parent.height
            height: parent.height
            padding: 0
            display: AbstractButton.IconOnly
            icon.source: "qrc:/icons/cross.png"
            icon.width: 12
            icon.height: 12
            ToolTip.visible: hovered
            ToolTip.text: qsTr("Unlink")
            onClicked: itemRoot.unlinkRequested()
        }
    }
}
