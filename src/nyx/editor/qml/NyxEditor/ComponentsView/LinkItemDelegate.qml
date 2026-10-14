import QtQuick
import QtQuick.Controls

ItemDelegate {
    id: itemRoot

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
    }
}
