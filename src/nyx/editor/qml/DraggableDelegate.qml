import QtQuick

Item {
    id: root

    required property int index                      // injected by the ListView
    readonly property ListView view: ListView.view

    default property alias content: dragContent.data
    readonly property Item dragItem: dragContent

    property bool dragEnabled: true   // can this row be picked up?
    property bool dropEnabled: true   // can other rows be dragged over it?
    property bool isDragging: false     // set by the DragHandle

    signal moveRequested(int from, int to)

    width: view.width
    height: dragContent.height
    z: isDragging ? 2 : 1               // dragged row paints above neighbours

    onIsDraggingChanged: if (!isDragging) {
        dragContent.y = 0;   // snap back into its slot
    }
    DropArea {
        anchors.fill: parent
        enabled: root.dropEnabled
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
        height: childrenRect.height

        Drag.active: root.isDragging
        Drag.source: dragContent
        Drag.hotSpot.x: width / 2
        Drag.hotSpot.y: height / 2
    }
}
