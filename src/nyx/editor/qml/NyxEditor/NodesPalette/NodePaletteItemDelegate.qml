import QtQuick
import QtQuick.Controls

import "../Common"

ItemDelegate {
    id: itemRoot

    required property var model

    property bool dragEnabled: false
    property string mimeType: ""

    signal spawnRequested(string typeId)

    icon.source: "qrc" + model.typeIcon
    text: model.typeDisplayName

    TagsList {
        anchors.right: parent.right
        anchors.rightMargin: 8
        anchors.verticalCenter: parent.verticalCenter
        // Leaves room for the name of the item
        maximumWidth: itemRoot.width * 0.5
        tags: itemRoot.model.typeTags
    }

    DescriptionToolTip {
        visible: itemRoot.hovered && itemRoot.model.description.length > 0
        text: itemRoot.model.description
    }
    onClicked: {
        if (dragEnabled)
            return;
        spawnRequested(String(model.typeId));
    }

    Drag.active: dragHandler.active
    Drag.imageSource: icon.source            // drag pixmap is just the type icon
    Drag.dragType: Drag.Automatic            // starts a native QDrag, so widgets can accept it
    Drag.supportedActions: Qt.CopyAction
    Drag.proposedAction: Qt.CopyAction
    Drag.mimeData: {
        let data = {};
        data[itemRoot.mimeType] = String(model.typeId);
        return data;
    }

    DragHandler {
        id: dragHandler
        enabled: itemRoot.dragEnabled
        target: null                         // the row stays put; only the drag image moves
        acceptedButtons: Qt.LeftButton
    }
}
