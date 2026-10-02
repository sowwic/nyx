import QtQuick
import QtQuick.Controls

Item {
    id: handle

    required property DraggableDelegate row     // the row this handle drags

    implicitWidth: 24
    implicitHeight: 24

    Image {
        anchors.centerIn: parent
        width: 16
        height: 16
        sourceSize: Qt.size(width * Screen.devicePixelRatio, height * Screen.devicePixelRatio)   // stay crisp on HiDPI
        fillMode: Image.PreserveAspectFit
        source: handle.row.dragEnabled ? "qrc:/icons/drag_indicator.png" : "qrc:/icons/lock.png"
        opacity: !handle.row.dragEnabled ? 0.6 : hover.hovered ? 1 : 0.5
    }

    HoverHandler {
        id: hover
        enabled: handle.row.dragEnabled
        cursorShape: handle.row.isDragging ? Qt.ClosedHandCursor : Qt.OpenHandCursor
    }

    DragHandler {
        id: dragHandler
        enabled: handle.row.dragEnabled
        target: null                               // we position the item ourselves
        grabPermissions: PointerHandler.CanTakeOverFromAnything
        xAxis.enabled: false

        property real grabOffsetY: 0               // pointer offset inside the dragged item

        function updatePosition() {
            if (!active)
                return;
            const row = handle.row;
            const item = row.dragItem;
            const pointerY = row.mapFromItem(null, centroid.scenePosition).y;
            const minY = -row.y;
            const maxY = row.view.contentHeight - row.y - item.height;
            item.y = Math.max(minY, Math.min(maxY, pointerY - grabOffsetY));
        }

        onActiveChanged: {
            handle.row.isDragging = active;
            if (active)
                grabOffsetY = handle.row.dragItem.mapFromItem(null, centroid.scenePressPosition).y;
        }
        onCentroidChanged: updatePosition()
    }

    // The slot moves when the live reorder happens. Re-run the mapping so the
    // dragged item stays under the pointer instead of jumping with its slot.
    Connections {
        target: handle.row
        function onYChanged() {
            dragHandler.updatePosition();
        }
    }
}
