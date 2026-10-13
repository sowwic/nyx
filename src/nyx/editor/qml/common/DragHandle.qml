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
        opacity: !handle.row.dragEnabled ? 0.6 : rowDragHandler.isHovered ? 1 : 0.5
    }

    RowDragHandler {
        id: rowDragHandler
        row: handle.row
    }
}
