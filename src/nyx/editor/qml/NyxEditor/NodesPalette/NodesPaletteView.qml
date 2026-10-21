pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import "../Common"

Rectangle {
    id: root
    color: palette.window

    required property var nodesRegistryFilterModel
    required property var nodeSpawner
    property bool dragEnabled: false
    property string nodeMimeType: ""

    property alias searchText: searchBar.queryText

    ColumnLayout {
        id: mainLayout
        anchors.fill: parent
        spacing: 0

        SearchBar {
            id: searchBar
            Layout.fillWidth: true
            Layout.topMargin: 6
            Layout.leftMargin: 6
            Layout.rightMargin: 6
            tokenKeys: root.nodesRegistryFilterModel.tokenKeys
            onQueryChanged: (text, tokens) => root.nodesRegistryFilterModel.setQuery(text, tokens)
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

                section.property: "paletteSection"
                section.criteria: ViewSection.FullString
                section.delegate: PaletteSectionHeader {}

                delegate: NodePaletteItemDelegate {
                    dragEnabled: root.dragEnabled
                    mimeType: root.nodeMimeType
                    onSpawnRequested: typeId => root.nodeSpawner.spawnNode(typeId)
                    width: ListView.view.width
                }
            }

            Label {
                anchors.centerIn: parent
                visible: nodesPaletteListView.count === 0
                text: searchBar.isActive ? qsTr("No Matching Nodes") : qsTr("No Nodes Available")
                opacity: 0.5
            }
        }
    }
}
