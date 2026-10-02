import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: root

    required property int index                      // injected by the ListView
    readonly property ListView view: ListView.view   // attached property, no wiring needed
    readonly property bool isDragging: handleArea.drag.active

    // Whatever is declared inside a DraggableDelegate { ... } lands in contentSlot
    default property alias content: contentSlot.data

    property bool dragEnabled: true   // can this row be picked up?
    property bool dropEnabled: true   // can other rows be dragged over it?

    signal moveRequested(int from, int to)

    width: view.width
    height: dragContent.height
    z: handleArea.drag.active ? 2 : 1     // dragged row paints above neighbours

    // Each row is a drop target
    DropArea {
        enabled: root.dropEnabled
        anchors.fill: parent
        onEntered: drag => {
            const from = drag.source.visualIndex;
            if (from !== root.index)
                root.moveRequested(from, root.index);
        }
    }

    Item {
        id: dragContent
        property int visualIndex: root.index
        width: root.width
        height: row.implicitHeight

        Drag.active: handleArea.drag.active
        Drag.source: dragContent
        Drag.hotSpot.x: width / 2
        Drag.hotSpot.y: height / 2

        RowLayout {
            id: row
            width: parent.width
            spacing: 4

            Label {                       // drag handle
                text: "\u2630"
                opacity: !root.dragEnabled ? 0.15 : handleArea.containsMouse ? 1 : 0.5
                Layout.alignment: Qt.AlignTop
                Layout.topMargin: 6

                MouseArea {
                    id: handleArea
                    enabled: root.dragEnabled
                    anchors.fill: parent
                    anchors.margins: -4
                    hoverEnabled: true
                    cursorShape: drag.active ? Qt.ClosedHandCursor : Qt.OpenHandCursor
                    drag.target: dragContent
                    drag.axis: Drag.YAxis
                    drag.minimumY: -root.y                                          // clamp to list bounds
                    drag.maximumY: root.view.contentHeight - root.y - dragContent.height
                    onReleased: {
                        dragContent.Drag.drop();
                        dragContent.y = 0;     // snap back into its slot
                    }
                }
            }

            Item {
                id: contentSlot
                Layout.fillWidth: true
                implicitHeight: childrenRect.height
            }
        }
    }
}
