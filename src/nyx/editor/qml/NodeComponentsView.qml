import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    id: root
    color: palette.window

    ListView {
        id: componentsListView
        anchors {
            top: parent.top
            left: parent.left
            right: parent.right
            bottom: buttonBar.top
            margins: 6
            rightMargin: 6 + verticalScrollBar.width
        }
        model: componentsModel
        spacing: 4
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        reuseItems: false   // delegates hold expanded state, so they should not be recycled

        ScrollBar.vertical: ScrollBar {
            id: verticalScrollBar

            parent: componentsListView.parent
            policy: ScrollBar.AsNeeded
            anchors {
                top: componentsListView.top
                bottom: componentsListView.bottom
                left: componentsListView.right
            }
        }

        delegate: NodeComponentDelegate {}

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
        visible: componentsListView.count === 0
        text: qsTr("No components")
        opacity: 0.5
    }
    // ---- Bottom button bar ----
    Rectangle {
        id: buttonBar
        anchors {
            left: parent.left
            right: parent.right
            bottom: parent.bottom
        }
        height: barLayout.implicitHeight + 8
        color: palette.window

        // thin separator line on top
        Rectangle {
            anchors {
                left: parent.left
                right: parent.right
                top: parent.top
            }
            height: 1
            color: palette.mid
        }

        RowLayout {
            id: barLayout
            anchors {
                fill: parent
                margins: 4
            }
            spacing: 4
            uniformCellSizes: true

            Button {
                id: addButton
                Layout.fillWidth: true
                text: "+ Add"
                font.bold: true
                ToolTip.visible: hovered
                ToolTip.text: qsTr("Add component")
                onClicked: console.log("TODO: add component")

                background: Rectangle {
                    radius: 4
                    color: !addButton.enabled ? Qt.alpha("#2e7d32", 0.35) : addButton.down ? Qt.darker("#2e7d32", 1.3) : addButton.hovered ? Qt.lighter("#2e7d32", 1.15) : "#2e7d32"
                }
                contentItem: Label {
                    text: addButton.text
                    font: addButton.font
                    color: "white"
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
            }

            Button {
                id: removeButton
                Layout.fillWidth: true
                text: "\u2212 Remove"
                font.bold: true
                ToolTip.visible: hovered
                ToolTip.text: qsTr("Remove component")
                onClicked: console.log("TODO: remove component")

                background: Rectangle {
                    radius: 4
                    color: !removeButton.enabled ? Qt.alpha("#c62828", 0.35) : removeButton.down ? Qt.darker("#c62828", 1.3) : removeButton.hovered ? Qt.lighter("#c62828", 1.15) : "#c62828"
                }
                contentItem: Label {
                    text: removeButton.text
                    font: removeButton.font
                    color: "white"
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
            }
        }
    }
}
