import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import "../Common"

DraggableDelegate {
    id: itemRoot

    // Emitted when the "?" button in the header is clicked.
    signal helpRequested

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

    // True while the inline rename editor is shown over the title.
    property bool isRenaming: false

    function toggleExpanded() {
        animateHeight = true;
        model.isExpanded = !isExpanded;
    }

    function startRename() {
        if (isBuiltIn)
            return;
        isRenaming = true;
        renameField.text = name;
        // Deferred so a closing context menu doesn't take focus back right after we set it.
        Qt.callLater(function () {
            renameField.forceActiveFocus();
            renameField.selectAll();
        });
    }

    function commitRename() {
        if (!isRenaming)
            return;
        isRenaming = false;
        const newName = renameField.text.trim();
        if (newName.length > 0 && newName !== name)
            root.componentsController.renameComponent(model.index, newName);
    }

    function cancelRename() {
        isRenaming = false;
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
            onDoubleTapped: eventPoint => {
                const tapPosition = componentNameLabel.mapFromItem(card, eventPoint.position);
                const onTitle = componentNameLabel.contains(tapPosition);
                if (onTitle && !itemRoot.isBuiltIn)
                    itemRoot.startRename();
            }
        }

        TapHandler {
            acceptedModifiers: Qt.ControlModifier
            onTapped: root.componentsController.selectRow(itemRoot.index, 1)
        }

        TapHandler {
            acceptedModifiers: Qt.ShiftModifier
            onTapped: root.componentsController.selectRow(itemRoot.index, 2)
        }

        TapHandler {
            onTapped: itemRoot.ListView.view.forceActiveFocus()
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
                        // Hide only the label's own text while renaming. (Hiding the label itself
                        // or lowering its opacity would also affect the TextField child.)
                        color: itemRoot.isRenaming ? "transparent" : palette.windowText

                        ToolTip.visible: componentNameHoverHandler.hovered && !itemRoot.isRenaming
                        ToolTip.delay: 600
                        ToolTip.text: itemRoot.typeDisplayName

                        HoverHandler {
                            id: componentNameHoverHandler
                        }

                        // Inline rename editor, drawn over the title.
                        TextField {
                            id: renameField
                            visible: itemRoot.isRenaming
                            anchors {
                                left: parent.left
                                right: parent.right
                                verticalCenter: parent.verticalCenter
                            }
                            font.bold: true
                            selectByMouse: true

                            // Commit only on Enter/Return.
                            onAccepted: itemRoot.commitRename()
                            Keys.onEscapePressed: itemRoot.cancelRename()
                            // Clicking elsewhere discards the edit instead of committing it.
                            onActiveFocusChanged: {
                                if (!activeFocus)
                                    itemRoot.cancelRename();
                            }
                        }
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
                                // A hidden MenuItem keeps its slot in the menu; collapse it explicitly.
                                height: visible ? implicitHeight : 0
                                onClicked: itemRoot.startRename()
                            }

                            MenuItem {
                                text: "Help"
                                onClicked: itemRoot.helpRequested()
                            }
                        }
                    }
                }
            }
            CollapsibleFrame {
                id: linksFrame

                Layout.fillWidth: true

                visible: itemRoot.isExpanded
                titleText: "Links"
                isExpanded: itemRoot.model.linksExpanded

                // A user toggle assigns isExpanded imperatively, which breaks the binding above.
                // Write the new state back to the model so it survives delegate recreation...
                onExpandedStateToggledByUser: newExpandedState => {
                    itemRoot.model.linksExpanded = newExpandedState;
                }

                // ...and re-establish the model -> frame direction after the binding is broken,
                // so external changes to the model (undo, load, etc.) still update the frame.
                Binding {
                    target: linksFrame
                    property: "isExpanded"
                    value: itemRoot.model.linksExpanded
                }

                LinksView {
                    id: linksView

                    Layout.fillWidth: true

                    inputLinks: itemRoot.model.inputLinks
                    outputLinks: itemRoot.model.outputLinks
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
