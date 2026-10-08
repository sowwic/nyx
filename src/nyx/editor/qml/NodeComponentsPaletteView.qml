pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    id: root
    signal spawnRequested(string typeId)

    required property var componentsRegistryFilterModel

    property alias searchText: searchField.text

    color: palette.window

    ColumnLayout {
        id: mainLayout
        anchors.fill: parent
        spacing: 0

        // TODO: Replace with common search bar component
        TextField {
            id: searchField
            Layout.fillWidth: true
            Layout.topMargin: 6
            Layout.leftMargin: 6
            Layout.rightMargin: 6
            placeholderText: qsTr("Search...")
            selectByMouse: true
            onTextChanged: root.componentsRegistryFilterModel.setFilterFixedString(text)
        }

        // ---- List area ----
        // Wrapper item keeps the scrollbar beside the list (not overlapping delegates)
        Item {
            id: listContainer
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.margins: 6

            ListView {
                id: nodesPaletteListView
                anchors {
                    fill: parent
                    rightMargin: verticalScrollBar.width
                }

                model: root.componentsRegistryFilterModel
                spacing: 4
                clip: true
                boundsBehavior: Flickable.StopAtBounds
                reuseItems: false   // delegates hold expanded state, so they should not be recycled

                ScrollBar.vertical: ScrollBar {
                    id: verticalScrollBar

                    parent: listContainer
                    policy: ScrollBar.AsNeeded
                    anchors {
                        top: nodesPaletteListView.top
                        bottom: nodesPaletteListView.bottom
                        left: nodesPaletteListView.right
                    }
                }

                delegate: ComponentPaletteItemDelegate {
                    onSpawnRequested: typeId => root.spawnRequested(typeId)
                    width: ListView.view.width
                }
            }

            Label {
                anchors.centerIn: parent
                visible: nodesPaletteListView.count === 0
                text: root.searchText.length > 0 ? qsTr("No Matching Components") : qsTr("No Components Available")
                opacity: 0.5
            }
        }
    }
}
