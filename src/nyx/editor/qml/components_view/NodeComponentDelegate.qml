import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import "../common"

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

    // Emitted when the "?" button in the header is clicked.
    signal helpRequested

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
            // Grabbing anywhere on the header (except its buttons and switch) drags the whole row.
            // Left to right: expand/collapse toggle, active switch, icon, spacer,
            // name, then right-aligned help and options buttons.
            Item {
                id: headerDragSurface
                Layout.fillWidth: true
                implicitHeight: headerLayout.implicitHeight

                // Declared first so it sits underneath the controls and never steals their clicks.
                RowDragHandler {
                    id: headerRowDragHandler
                    row: itemRoot
                }

                RowLayout {
                    id: headerLayout
                    anchors.fill: parent
                    spacing: 6

                    ToolButton {
                        id: expandCollapseToggleButton
                        Layout.alignment: Qt.AlignVCenter
                        text: itemRoot.showExpanded ? "\u25BE" : "\u25B8"
                        onClicked: itemRoot.toggleExpanded()
                    }

                    Image {
                        id: componentTypeIconImage
                        Layout.alignment: Qt.AlignVCenter
                        Layout.preferredWidth: 16
                        Layout.preferredHeight: 16
                        source: "qrc" + itemRoot.model.typeIcon
                        sourceSize: Qt.size(16, 16)
                        fillMode: Image.PreserveAspectFit
                        opacity: itemRoot.isActive ? 1.0 : 0.5
                    }

                    CheckBox {
                        id: componentActiveStateSwitch
                        Layout.alignment: Qt.AlignVCenter
                        checked: itemRoot.isActive
                        visible: !itemRoot.model.isStatic
                        onToggled: root.componentsController.setSetComponentActiveState(itemRoot.model.index, checked)
                    }

                    Label {
                        id: componentNameLabel
                        Layout.fillWidth: true
                        Layout.alignment: Qt.AlignVCenter
                        text: itemRoot.name
                        font.bold: true
                        elide: Text.ElideRight
                        opacity: itemRoot.isActive ? 1.0 : 0.5

                        ToolTip.visible: componentNameHoverHandler.hovered
                        ToolTip.delay: 600
                        ToolTip.text: itemRoot.typeDisplayName

                        HoverHandler {
                            id: componentNameHoverHandler
                        }
                    }

                    ToolButton {
                        id: helpButton
                        Layout.alignment: Qt.AlignVCenter
                        text: "?"
                        font.bold: true
                        onClicked: itemRoot.helpRequested()

                        ToolTip.visible: hovered
                        ToolTip.delay: 600
                        ToolTip.text: qsTr("Help")
                    }

                    ToolButton {
                        id: optionsMenuButton
                        Layout.alignment: Qt.AlignVCenter
                        text: "\u22EE"   // vertical three dots
                        onClicked: componentOptionsMenu.popup(optionsMenuButton, 0, optionsMenuButton.height)

                        Menu {
                            id: componentOptionsMenu

                            MenuItem {
                                text: "Rename"
                                visible: !itemRoot.isBuiltIn
                            }
                        }
                    }
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
