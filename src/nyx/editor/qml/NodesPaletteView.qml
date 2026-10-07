import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    id: root
    color: palette.window

    required property var nodesRegistryFilterModel
    required property var nodeSpawner

    // Current text in the search field (hook this up to your filtering, see TODO below)
    property alias searchText: searchField.text

    ColumnLayout {
        id: mainLayout
        anchors.fill: parent
        spacing: 0

        // ---- Search field ----
        // TODO: Replace with common search bar component
        TextField {
            id: searchField
            Layout.fillWidth: true
            Layout.topMargin: 6
            Layout.leftMargin: 6
            Layout.rightMargin: 6
            placeholderText: qsTr("Search...")
            selectByMouse: true
            onTextChanged: root.nodesRegistryFilterModel.setFilterFixedString(text)
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

                model: root.nodesRegistryFilterModel
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

                delegate: ItemDelegate {
                    required property var model

                    width: ListView.view.width
                    text: model.typeDisplayName

                    onClicked: root.nodeSpawner.spawnNode(model.typeId)
                }
            }

            Label {
                anchors.centerIn: parent
                visible: nodesPaletteListView.count === 0
                text: root.searchText.length > 0 ? qsTr("No Matching Nodes") : qsTr("No Nodes Available")
                opacity: 0.5
            }
        }
    }
}
