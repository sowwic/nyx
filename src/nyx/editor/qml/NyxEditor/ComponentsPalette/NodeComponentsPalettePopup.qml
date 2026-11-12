import QtQuick
import QtQuick.Controls

// Popup wrapping NodeComponentsPaletteView. Set `parent` to the item it should
// span, and `bottomReserved` to the space at the parent's bottom it must stay above.
Popup {
    id: root

    signal spawnRequested(string typeId)

    required property var componentsRegistryFilterModel

    // Space (px) at the bottom of the parent that the popup should not cover
    property real bottomReserved: 0
    property real maxHeight: 420
    property real margin: 6

    x: margin
    y: parent.height - bottomReserved - height - 4
    width: parent.width - 2 * margin
    height: Math.min(maxHeight, parent.height - bottomReserved - 2 * margin)

    padding: 0
    modal: false
    focus: true
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutsideParent

    background: Rectangle {
        color: palette.window
        border.color: palette.mid
        radius: 4
    }

    contentItem: NodeComponentsPaletteView {
        componentsRegistryFilterModel: root.componentsRegistryFilterModel
        onSpawnRequested: typeId => root.spawnRequested(typeId)
        color: "transparent"
        clip: true
    }
}
