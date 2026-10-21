import QtQuick
import QtQuick.Controls

import "../Common"

ItemDelegate {
    id: itemRoot

    required property var model

    signal spawnRequested(string typeId, var targetNode)
    icon.source: "qrc" + model.typeIcon

    text: model.typeDisplayName

    DescriptionToolTip {
        visible: itemRoot.hovered && itemRoot.model.description.length > 0
        text: itemRoot.model.description
    }
    onClicked: {
        spawnRequested(String(model.typeId), model.node);
    }
}
