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
        enabled: handle.row.dragEnabled
        target: handle.row.dragItem
        grabPermissions: PointerHandler.CanTakeOverFromAnything
        xAxis.enabled: false                     // vertical only
        yAxis.minimum: -handle.row.y             // clamp to list bounds
        yAxis.maximum: handle.row.view.contentHeight - handle.row.y - handle.row.dragItem.height
        onActiveChanged: handle.row.isDragging = active
    }
}
