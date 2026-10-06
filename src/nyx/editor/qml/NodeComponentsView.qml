import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    id: root
    color: palette.window

    readonly property var activeModel: typeof componentsModel !== "undefined" ? componentsModel : null
    readonly property var activeController: typeof componentsController !== "undefined" ? componentsController : null

    // Current text in the search field (hook this up to your filtering, see TODO below)
    property alias searchText: searchField.text

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

            // TODO: apply the filter, e.g. via a proxy model or controller call
            // onTextChanged: root.activeController.setFilterText(text)
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
                anchors {
                    fill: parent
                    rightMargin: verticalScrollBar.width
                }

                property var reorderState: ReorderState {}

                model: root.activeModel
                spacing: 4
                clip: true
                boundsBehavior: Flickable.StopAtBounds
                reuseItems: false   // delegates hold expanded state, so they should not be recycled

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

                delegate: NodeComponentDelegate {
                    reorderState: componentsListView.reorderState
                    onMoveRequested: (from, to) => componentsController.reorderComponent(from, to)
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
                    onClicked: console.log("TODO: add component")

                    background: Rectangle {
                        radius: 4
                        color: !addButton.enabled ? Qt.alpha("#2e7d32", 0.35) : addButton.down ? Qt.darker("#2e7d32", 1.3) : addButton.hovered ? Qt.lighter("#2e7d32", 1.15) : "#2e7d32"
                    }
                }

                Button {
                    id: removeButton
                    enabled: root.activeController !== null && root.activeController.selectionModel.hasSelection
                    Layout.fillWidth: true
                    icon.source: "qrc:/icons/delete.png"
                    icon.width: 16
                    icon.height: 16
                    text: "Remove"
                    font.bold: true
                    ToolTip.visible: hovered
                    ToolTip.text: qsTr("Remove component")
                    onClicked: root.activeController.deleteSelectedNodeComponents()

                    background: Rectangle {
                        radius: 4
                        color: !removeButton.enabled ? Qt.alpha("#c62828", 0.35) : removeButton.down ? Qt.darker("#c62828", 1.3) : removeButton.hovered ? Qt.lighter("#c62828", 1.15) : "#c62828"
                    }
                }
            }
        }
    }
}
