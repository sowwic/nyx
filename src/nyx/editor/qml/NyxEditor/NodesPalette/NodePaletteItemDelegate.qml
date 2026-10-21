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

    Drag.imageSource: icon.source            // drag pixmap is just the type icon
    Drag.dragType: Drag.Automatic            // activating starts a native QDrag, so widgets can accept it
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

        // Activate the drag once pointer delivery has unwound, rather than from
        // inside this handler's activation. On macOS the QDrag blocks until the
        // drop, after which the attached Drag is reset for the next one.
        onActiveChanged: {
            if (active)
                Qt.callLater(() => {
                    if (!dragHandler.active)
                        return;
                    // QQuickWidget accepts touch events, so a macOS trackpad feeds raw
                    // touch points into the scene, and starting a QDrag from one of
                    // those crashes Qt. Those have no button down. Filtering by device
                    // type would not do: after a scroll, Qt reports the clicks of a
                    // mouse as coming from the trackpad device.
                    if (!(dragHandler.centroid.pressedButtons & Qt.LeftButton))
                        return;
                    itemRoot.Drag.active = true;
                    itemRoot.Drag.active = false;
                });
        }
    }
}
