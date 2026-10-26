import QtQuick
import QtQuick.Controls

ItemDelegate {
    id: itemRoot

    // Emitted when the "x" button is clicked, to remove the link.
    signal unlinkRequested

    property string linkDirection
    property string linkPath

    // The implicit height, so the layout showing the item is free to size it.
    implicitHeight: 30

    contentItem: Item {
        implicitWidth: labelsRow.implicitWidth + unlinkButton.width

        Row {
            id: labelsRow

            anchors.verticalCenter: parent.verticalCenter
            height: parent.height
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
        }

        // At the right end of the item, whatever its width.
        ToolButton {
            id: unlinkButton
            objectName: "unlinkButton"

            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
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
