import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

DraggableDelegate {
    id: itemRoot

    // Injected by the ListView into this root object.
    // `index` is NOT redeclared here: DraggableDelegate already requires it.
    required property var model
    required property string name
    required property string typeDisplayName
    required property bool isActive
    required property bool isExpanded
    required property url editorQmlFile
    required property bool isBuiltIn

    required property bool filtersActive

    readonly property bool isSelected: {
        if (!root.componentsController.selectionModel.model)
            return false;

        root.componentsController.selectionModel.selection;
        return root.componentsController.selectionModel.isSelected(root.componentsController.selectionModel.model.index(index, 0));
    }
    readonly property bool showExpanded: isExpanded && !isDragging

    // Becomes true on the first user toggle, so creation doesn't animate.
    property bool animateHeight: false

    function toggleExpanded() {
        animateHeight = true;
        model.isExpanded = !isExpanded;
    }

    onIsDraggingChanged: animateHeight = true

    dragEnabled: !isBuiltIn && !filtersActive
    dropEnabled: !isBuiltIn && !filtersActive

    Rectangle {
        id: card
        width: parent.width        // parent is DraggableDelegate's content slot
        height: mainLayout.implicitHeight + 2 * mainLayout.anchors.margins
        clip: true
        radius: 4
        color: itemRoot.isSelected ? Qt.alpha(palette.highlight, 0.15) : palette.base
        border.width: itemRoot.isSelected ? 2 : 1
        border.color: itemRoot.isSelected ? palette.highlight : palette.mid

        Behavior on height {
            enabled: itemRoot.animateHeight
            NumberAnimation {
                duration: 120
                easing.type: Easing.OutCubic
            }
        }

        TapHandler {
            acceptedModifiers: Qt.NoModifier
            onTapped: root.componentsController.selectRow(itemRoot.index, 0)
            onDoubleTapped: itemRoot.toggleExpanded()
        }

        TapHandler {
            acceptedModifiers: Qt.ControlModifier
            onTapped: root.componentsController.selectRow(itemRoot.index, 1)
        }

        TapHandler {
            acceptedModifiers: Qt.ShiftModifier
            onTapped: root.componentsController.selectRow(itemRoot.index, 2)
        }

        ColumnLayout {
            id: mainLayout
            anchors {
                left: parent.left
                right: parent.right
                top: parent.top
                margins: 4
            }
            spacing: 4

            // ---- Header (always visible) ----
            RowLayout {
                Layout.fillWidth: true
                spacing: 6

                DragHandle {
                    row: itemRoot
                    Layout.alignment: Qt.AlignVCenter
                }

                Switch {
                    checked: itemRoot.isActive
                    onToggled: itemRoot.model.isActive = checked
                    visible: !itemRoot.model.isStatic
                }

                Item {
                    Layout.fillWidth: true
                    implicitHeight: headerRow.implicitHeight

                    RowLayout {
                        id: headerRow
                        anchors.fill: parent
                        spacing: 8
                        opacity: itemRoot.isActive ? 1.0 : 0.5

                        Label {
                            Layout.fillWidth: true
                            text: itemRoot.name
                            font.bold: true
                            elide: Text.ElideRight
                        }
                        Label {
                            text: itemRoot.typeDisplayName
                            opacity: 0.6
                        }
                    }
                }

                ToolButton {
                    text: itemRoot.showExpanded ? "\u25BE" : "\u25B8"
                    onClicked: itemRoot.toggleExpanded()
                }
            }

            // ---- Per-type editor (created only while expanded) ----
            Loader {
                id: editorLoader

                Layout.fillWidth: true
                Layout.leftMargin: 8
                Layout.rightMargin: 8
                Layout.bottomMargin: 4

                active: itemRoot.isExpanded
                visible: active && itemRoot.showExpanded
                source: itemRoot.editorQmlFile

                Binding {
                    target: editorLoader.item
                    property: "component"
                    value: itemRoot.model
                    when: editorLoader.item !== null && itemRoot.model !== null
                    restoreMode: Binding.RestoreNone
                }

                onStatusChanged: {
                    if (status === Loader.Error)
                        console.warn("Editor failed to load:", itemRoot.editorQmlFile);
                }
            }

            Label {
                visible: editorLoader.status === Loader.Error && itemRoot.showExpanded
                text: qsTr("Editor could not be loaded")
                color: "firebrick"
                Layout.leftMargin: 8
            }
        }
    }
}
