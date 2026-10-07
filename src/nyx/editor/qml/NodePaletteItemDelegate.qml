import QtQuick
import QtQuick.Controls

ItemDelegate {
    id: root

    required property var model

    property bool dragEnabled: false
    property string mimeType: ""

    signal spawnRequested(string typeId)

    text: model.typeDisplayName
    onClicked: {
        if (dragEnabled)
            return;
        spawnRequested(String(model.typeId));
    }

    // Snapshot of the row, used as the drag pixmap
    onDownChanged: {
        if (down && dragEnabled)
            grabToImage(function (result) {
                root.Drag.imageSource = result.url;
            });
    }

    Drag.active: dragHandler.active
    Drag.dragType: Drag.Automatic            // starts a native QDrag, so widgets can accept it
    Drag.supportedActions: Qt.CopyAction
    Drag.proposedAction: Qt.CopyAction
    Drag.mimeData: {
        let data = {};
        data[root.mimeType] = String(model.typeId);
        return data;
    }

    DragHandler {
        id: dragHandler
        enabled: root.dragEnabled
        target: null                         // the row stays put; only the drag image moves
        acceptedButtons: Qt.LeftButton
    }
}
