pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import "../common"
import "../components_palette"

Rectangle {
    id: root
    color: palette.window

    required property var componentsFilterModel
    required property var componentsRegistryFilterModel
    required property var componentsController
    required property var componentsSpawner

    property alias searchText: searchField.text
    property bool hasActiveFilters: searchText.length > 0

    ColumnLayout {
        id: mainLayout
        anchors.fill: parent
        anchors.bottomMargin: 5
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
            onTextChanged: root.componentsFilterModel.setFilterFixedString(text)
        }

        // ---- List area ----
        // Wrapper item keeps the scrollbar beside the list (not overlapping delegates)
        Item {
            id: listContainer
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.margins: 6

            ListView {
                id: componentsListView

                property var reorderState: ReorderState {}

                anchors {
                    fill: parent
                    rightMargin: verticalScrollBar.width
                }

                model: root.componentsFilterModel
                spacing: 4
                clip: true
                boundsBehavior: Flickable.StopAtBounds
                reuseItems: false   // delegates hold expanded state, so they should not be recycled
                activeFocusOnTab: true

                ScrollBar.vertical: ScrollBar {
                    id: verticalScrollBar

                    parent: listContainer
                    policy: ScrollBar.AsNeeded
                    anchors {
                        top: componentsListView.top
                        bottom: componentsListView.bottom
                        left: componentsListView.right
                    }
                }

                section {
                    property: "isBuiltIn"
                    criteria: ViewSection.FullString
                    labelPositioning: ViewSection.InlineLabels | ViewSection.CurrentLabelAtStart
                    delegate: NodeComponentsSectionHeader {
                        width: componentsListView.width
                    }
                }

                delegate: NodeComponentDelegate {
                    reorderState: componentsListView.reorderState
                    filtersActive: root.hasActiveFilters
                    onMoveRequested: (from, to) => root.componentsController.reorderComponent(from, to)
                }

                add: Transition {
                    enabled: !componentsListView.reorderState.committing
                    NumberAnimation {
                        property: "opacity"
                        from: 0
                        to: 1
                        duration: 120
                    }
                }
                remove: Transition {
                    enabled: !componentsListView.reorderState.committing
                    NumberAnimation {
                        property: "opacity"
                        to: 0
                        duration: 120
                    }
                }
                displaced: Transition {
                    enabled: !componentsListView.reorderState.committing
                    NumberAnimation {
                        properties: "y"
                        duration: 120
                    }
                }
            }

            Label {
                anchors.centerIn: parent
                visible: componentsListView.count === 0
                text: root.searchText.length > 0 ? qsTr("No matching components") : qsTr("No components")
                opacity: 0.5
            }
        }

        // ---- Bottom button bar ----
        Rectangle {
            id: buttonBar
            Layout.fillWidth: true
            Layout.preferredHeight: barLayout.implicitHeight + 8
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
                    icon.source: "qrc:/icons/plus.png"
                    icon.width: 16
                    icon.height: 16
                    text: "Add"
                    font.bold: true
                    ToolTip.visible: hovered
                    ToolTip.text: qsTr("Add component")
                    onClicked: palettePopup.opened ? palettePopup.close() : palettePopup.open()

                    background: Rectangle {
                        radius: 4
                        color: !addButton.enabled ? Qt.alpha("#2e7d32", 0.35) : addButton.down ? Qt.darker("#2e7d32", 1.3) : addButton.hovered ? Qt.lighter("#2e7d32", 1.15) : "#2e7d32"
                    }
                }

                Button {
                    id: removeButton
                    enabled: root.componentsController.selectionModel.hasSelection
                    Layout.fillWidth: true
                    icon.source: "qrc:/icons/delete.png"
                    icon.width: 16
                    icon.height: 16
                    text: "Remove"
                    font.bold: true
                    ToolTip.visible: hovered
                    ToolTip.text: qsTr("Remove component")
                    onClicked: root.componentsController.deleteSelectedNodeComponents()

                    background: Rectangle {
                        radius: 4
                        color: !removeButton.enabled ? Qt.alpha("#c62828", 0.35) : removeButton.down ? Qt.darker("#c62828", 1.3) : removeButton.hovered ? Qt.lighter("#c62828", 1.15) : "#c62828"
                    }
                }
            }
        }
    }

    NodeComponentsPalettePopup {
        id: palettePopup
        parent: root
        bottomReserved: root.height - buttonBar.y

        componentsRegistryFilterModel: root.componentsRegistryFilterModel
        onSpawnRequested: typeId => {
            root.componentsSpawner.spawnComponent(typeId, root.componentsFilterModel.node);
            palettePopup.close();
        }
    }
}
