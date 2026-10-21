import QtQuick
import QtQuick.Controls

// Tooltip with black text on a white background, for longer descriptions.
//
// It is a popup inside of the QML view, so it can't extend past the view. The margins
// keep it within the view and the text wraps to the width that is left.
ToolTip {
    id: toolTipRoot

    readonly property real viewWidth: Overlay.overlay ? Overlay.overlay.width : 320

    delay: 500
    timeout: -1
    padding: 8
    margins: 6
    y: parent ? parent.height + 4 : 0
    // Wide enough for a sentence, the text wraps beyond that
    contentWidth: Math.max(
        40, Math.min(textItem.implicitWidth, 320, viewWidth - 2 * margins - leftPadding - rightPadding))

    contentItem: Text {
        id: textItem
        text: toolTipRoot.text
        font: toolTipRoot.font
        color: "black"
        wrapMode: Text.WordWrap
    }

    background: Rectangle {
        color: "white"
        border.color: "#B0B0B0"
        border.width: 1
        radius: 4
    }
}
