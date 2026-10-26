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

    // Why the component can't be relied on, like when it left the source of a reference.
    readonly property string invalidReason: model.invalidReason || ""
    readonly property bool isInvalid: invalidReason.length > 0

    // False for the components of a reference: they belong to its source file.
    readonly property bool structureEditable: root.componentsController.structureEditable

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
        if (isBuiltIn || !structureEditable)
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

    // Edit the note, showing it first if it is hidden: the component and the note
    // frame are opened, and the frame is shown even though there is no note yet.
    function startNoteEdit() {
        if (!structureEditable)
            return;
        if (!isExpanded)
            toggleExpanded();
        model.noteExpanded = true;
        noteItem.beginEdit();
    }

    onIsDraggingChanged: animateHeight = true
    dragEnabled: !isBuiltIn && structureEditable && !filtersActive
    dropEnabled: !isBuiltIn && structureEditable && !filtersActive

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
                        flat: true
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
                        enabled: itemRoot.structureEditable
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
                        color: itemRoot.isRenaming ? "transparent" : itemRoot.isInvalid ? "firebrick" : palette.windowText

                        HoverHandler {
                            id: componentNameHoverHandler
                        }

                        // The same tooltip as the items of the palettes
                        DescriptionToolTip {
                            visible: componentNameHoverHandler.hovered && !itemRoot.isRenaming && text.length > 0
                            text: itemRoot.isInvalid ? itemRoot.invalidReason : (itemRoot.model.description || itemRoot.typeDisplayName)
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

                            // The neighbours change as components move, so ask when the menu opens.
                            property bool canMoveUp: false
                            property bool canMoveDown: false
                            onAboutToShow: {
                                canMoveUp = root.componentsController.canMoveComponent(itemRoot.index, -1);
                                canMoveDown = root.componentsController.canMoveComponent(itemRoot.index, 1);
                            }

                            MenuItem {
                                text: "Rename"
                                visible: !itemRoot.isBuiltIn && itemRoot.structureEditable
                                // A hidden MenuItem keeps its slot in the menu; collapse it explicitly.
                                height: visible ? implicitHeight : 0
                                onClicked: itemRoot.startRename()
                            }

                            MenuItem {
                                text: "Remove"
                                visible: itemRoot.isInvalid
                                height: visible ? implicitHeight : 0
                                onClicked: root.componentsController.removeComponent(itemRoot.index)
                            }

                            MenuItem {
                                text: "Move Up"
                                visible: itemRoot.dragEnabled
                                height: visible ? implicitHeight : 0
                                enabled: componentOptionsMenu.canMoveUp
                                onClicked: root.componentsController.moveComponent(itemRoot.index, -1)
                            }

                            MenuItem {
                                text: "Move Down"
                                visible: itemRoot.dragEnabled
                                height: visible ? implicitHeight : 0
                                enabled: componentOptionsMenu.canMoveDown
                                onClicked: root.componentsController.moveComponent(itemRoot.index, 1)
                            }

                            MenuSeparator {}

                            MenuItem {
                                id: writableMenuItem
                                text: "Writable"
                                visible: !itemRoot.isBuiltIn && itemRoot.structureEditable
                                height: visible ? implicitHeight : 0
                                checked: itemRoot.model.writable
                                checkable: true

                                onClicked: {
                                    root.componentsController.setComponentWritable(itemRoot.model.index, checked);
                                }
                            }
                            MenuItem {
                                id: readableMenuItem
                                text: "Readable"
                                visible: !itemRoot.isBuiltIn && itemRoot.structureEditable
                                height: visible ? implicitHeight : 0
                                checked: itemRoot.model.readable
                                checkable: true

                                onClicked: {
                                    root.componentsController.setComponentReadable(itemRoot.model.index, checked);
                                }
                            }

                            MenuSeparator {}

                            MenuItem {
                                text: "Edit Note"
                                visible: itemRoot.structureEditable
                                height: visible ? implicitHeight : 0
                                onClicked: itemRoot.startNoteEdit()
                            }

                            MenuItem {
                                text: "Help"
                                onClicked: itemRoot.helpRequested()
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

            CollapsibleFrame {
                id: linksFrame

                Layout.fillWidth: true

                visible: !!(itemRoot.model.readable || itemRoot.model.writable) && itemRoot.showExpanded
                titleText: qsTr("Links (in: %1 | out: %2)").arg(itemRoot.model.inputLinks?.length ?? 0).arg(itemRoot.model.outputLinks?.length ?? 0)
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

            // Hidden while there is no note, unless it is being written. Like the links,
            // it is also hidden while the component is dragged.
            CollapsibleFrame {
                id: noteFrame
                objectName: "noteFrame"

                Layout.fillWidth: true

                visible: (noteItem.hasNote || noteItem.editing) && itemRoot.showExpanded
                titleText: qsTr("Note")
                isExpanded: itemRoot.model.noteExpanded

                // Same as the links frame: the state is kept in the model so it survives
                // the delegate being recreated, and the binding is restored after a toggle.
                onExpandedStateToggledByUser: newExpandedState => {
                    itemRoot.model.noteExpanded = newExpandedState;
                }

                Binding {
                    target: noteFrame
                    property: "isExpanded"
                    value: itemRoot.model.noteExpanded
                }

                NodeComponentNoteItem {
                    id: noteItem
                    objectName: "noteItem"

                    Layout.fillWidth: true
                    enabled: itemRoot.structureEditable

                    note: itemRoot.model.note
                    noteFormat: itemRoot.model.noteFormat
                    noteFormats: root.componentsController.noteFormats()
                    onNoteCommitted: (text, format) => root.componentsController.setComponentNote(itemRoot.model.index, text, format)
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
