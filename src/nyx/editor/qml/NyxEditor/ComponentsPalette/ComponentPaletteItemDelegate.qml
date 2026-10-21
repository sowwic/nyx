import QtQuick
import QtQuick.Controls

import "../Common"

ItemDelegate {
    id: itemRoot

    required property var model

    signal spawnRequested(string typeId, var targetNode)
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
        spawnRequested(String(model.typeId), model.node);
    }
}
