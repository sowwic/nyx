import QtQuick
import QtQuick.Controls

Label {
    id: handle

    required property DraggableDelegate row     // the row this handle drags

    text: "\u2630"
    padding: 4
    opacity: !row.dragEnabled ? 0.15 : area.containsMouse ? 1 : 0.5

    MouseArea {
        id: area
        anchors.fill: parent
        enabled: handle.row.dragEnabled
        hoverEnabled: true
        cursorShape: drag.active ? Qt.ClosedHandCursor : Qt.OpenHandCursor

        drag.target: handle.row.dragItem
        drag.axis: Drag.YAxis
        drag.minimumY: -handle.row.y
        drag.maximumY: handle.row.view.contentHeight - handle.row.y - handle.row.dragItem.height
        drag.threshold: 0                       // start moving immediately

        onPressed: handle.row.view.interactive = false    // belt and braces
        onReleased: handle.row.view.interactive = true
        onCanceled: handle.row.view.interactive = true

        drag.onActiveChanged: handle.row.isDragging = drag.active
    }
}
