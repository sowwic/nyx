import QtQuick
import QtQuick.Controls

Rectangle {
    id: root
    color: palette.window

    ListView {
        id: list
        anchors.fill: parent
        anchors.margins: 6
        model: componentsModel
        spacing: 4
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        reuseItems: false   // delegates hold expanded state, so don't recycle them

        delegate: NodeComponentDelegate {}

        ScrollBar.vertical: ScrollBar {}

        add: Transition {
            NumberAnimation {
                property: "opacity"
                from: 0
                to: 1
                duration: 120
            }
        }
        remove: Transition {
            NumberAnimation {
                property: "opacity"
                to: 0
                duration: 120
            }
        }
        displaced: Transition {
            NumberAnimation {
                properties: "y"
                duration: 120
            }
        }
    }

    Label {
        anchors.centerIn: parent
        visible: list.count === 0
        text: qsTr("No components")
        opacity: 0.5
    }
}
