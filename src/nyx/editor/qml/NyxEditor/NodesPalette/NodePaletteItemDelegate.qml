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
        // Leaves room for the icon and name of the item, the tags scroll if they don't fit
        maximumWidth: Math.max(0, itemRoot.width - itemRoot.leftPadding - itemRoot.contentItem.implicitWidth - 2 * anchors.rightMargin)
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

    // Resets the drag for the next one, whichever Qt version ran it.
    Drag.onDragFinished: itemRoot.Drag.active = false

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
                    // Qt 6.10 runs the QDrag right here and returns when it ended. Qt 6.12
                    // starts it after this returns, so deactivating now would cancel it.
                    // The drag is deactivated when it finished, see onDragFinished.
                    // Setting a property to the value it has does nothing, so should a
                    // drag be left active (one that never finished) the next one would
                    // not start. Deactivating first makes every press start clean. This
                    // is a guard, no such drag was seen on 6.10 or 6.12.
                    itemRoot.Drag.active = false;
                    itemRoot.Drag.active = true;
                });
        }
    }
}
