import QtQuick
import QtQuick.Controls

ItemDelegate {
    id: itemRoot

    required property var model

    signal spawnRequested(string typeId, var targetNode)
    icon.source: "qrc" + model.typeIcon

    text: model.typeDisplayName
    onClicked: {
        spawnRequested(String(model.typeId), model.node);
    }
}
