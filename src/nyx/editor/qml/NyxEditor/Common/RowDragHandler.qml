import QtQuick

// Turns the area it fills into a drag surface for a DraggableDelegate row.
// Declare it as the first child of the item that should act as the grab area,
// so that buttons and switches stacked above it still receive their own clicks.
Item {
    id: rowDragHandlerRoot

    required property DraggableDelegate row     // the row this surface drags

    readonly property bool isHovered: hoverHandler.hovered

    anchors.fill: parent

    HoverHandler {
        id: hoverHandler
        enabled: rowDragHandlerRoot.row.dragEnabled
        cursorShape: rowDragHandlerRoot.row.isDragging ? Qt.ClosedHandCursor : Qt.OpenHandCursor
    }

    DragHandler {
        id: dragHandler
        enabled: rowDragHandlerRoot.row.dragEnabled
        target: null                               // we position the item ourselves
        acceptedDevices: PointerDevice.Mouse | PointerDevice.Stylus  // ignore raw trackpad touches
        grabPermissions: PointerHandler.CanTakeOverFromAnything
        xAxis.enabled: false

        property real grabOffsetY: 0               // pointer offset inside the dragged item

        function updatePosition() {
            if (!active)
                return;
            const row = rowDragHandlerRoot.row;
            const item = row.dragItem;
            const pointerY = row.mapFromItem(null, centroid.scenePosition).y;
            const minY = -row.y;
            const maxY = row.view.contentHeight - row.y - item.height;
            item.y = Math.max(minY, Math.min(maxY, pointerY - grabOffsetY));
        }

        onActiveChanged: {
            rowDragHandlerRoot.row.isDragging = active;
            if (active)
                grabOffsetY = rowDragHandlerRoot.row.dragItem.mapFromItem(null, centroid.scenePressPosition).y;
        }
        onCentroidChanged: updatePosition()
    }

    // The slot moves when the live reorder happens. Re-run the mapping so the
    // dragged item stays under the pointer instead of jumping with its slot.
    Connections {
        target: rowDragHandlerRoot.row
        function onYChanged() {
            dragHandler.updatePosition();
        }
    }
}
