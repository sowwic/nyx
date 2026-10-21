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

    // The popup palette is driven by the keyboard. The docked one, where nodes are
    // dragged out, has no selection.
    readonly property bool keyboardNavigation: !dragEnabled
    onKeyboardNavigationChanged: nodesPaletteListView.currentIndex = keyboardNavigation ? 0 : -1

    // Gives the search bar the keyboard focus
    function focusSearch() {
        searchBar.focusField();
    }

    // Moves the selection of the list, stays on the first or last item at the ends
    function moveSelection(delta) {
        if (!keyboardNavigation || nodesPaletteListView.count === 0)
            return;
        const index = Math.max(0, Math.min(nodesPaletteListView.count - 1, nodesPaletteListView.currentIndex + delta));
        nodesPaletteListView.currentIndex = index;
        nodesPaletteListView.positionViewAtIndex(index, ListView.Contain);
    }

    // Creates a node of the selected type
    function activateSelection() {
        if (!keyboardNavigation)
            return;
        const item = nodesPaletteListView.currentItem;
        if (item !== null)
            root.nodeSpawner.spawnNode(String(item.model.typeId));
    }

    ColumnLayout {
        id: mainLayout
        anchors.fill: parent
        spacing: 0

        SearchBar {
            id: searchBar
            objectName: "searchBar"
            Layout.fillWidth: true
            Layout.topMargin: 6
            Layout.leftMargin: 6
            Layout.rightMargin: 6
            tokenKeys: root.nodesRegistryFilterModel.tokenKeys
            onQueryChanged: (text, tokens) => {
                root.nodesRegistryFilterModel.setQuery(text, tokens);
                nodesPaletteListView.currentIndex = root.keyboardNavigation ? 0 : -1;
            }
            onNavigateUp: root.moveSelection(-1)
            onNavigateDown: root.moveSelection(1)
            onSubmitted: root.activateSelection()
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
                objectName: "nodesPaletteListView"
                anchors {
                    fill: parent
                    rightMargin: verticalScrollBar.width
                }

                model: root.nodesRegistryFilterModel
                currentIndex: root.keyboardNavigation ? 0 : -1
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
                    highlighted: root.keyboardNavigation && ListView.isCurrentItem
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
