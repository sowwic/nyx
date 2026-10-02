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

    readonly property bool showExpanded: isExpanded && !isDragging

    // Becomes true on the first user toggle, so creation doesn't animate.
    property bool animateHeight: false

    function toggleExpanded() {
        animateHeight = true;
        model.isExpanded = !isExpanded;
    }

    onIsDraggingChanged: animateHeight = true

    dragEnabled: !isBuiltIn
    dropEnabled: !isBuiltIn

    Rectangle {
        id: card
        width: parent.width        // parent is DraggableDelegate's content slot
        height: mainLayout.implicitHeight + 2 * mainLayout.anchors.margins
        clip: true
        radius: 4
        color: palette.base
        border.color: itemRoot.showExpanded ? palette.highlight : palette.mid

        Behavior on height {
            enabled: itemRoot.animateHeight
            NumberAnimation {
                duration: 120
                easing.type: Easing.OutCubic
            }
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

                    TapHandler {
                        onTapped: itemRoot.toggleExpanded()
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

                Component.onCompleted: setSource(itemRoot.editorQmlFile, {
                    "component": itemRoot.model
                })

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
