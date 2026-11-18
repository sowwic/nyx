import QtQuick
import QtQuick.Controls

// Small magnifier for search fields, drawn in the color of placeholder text. It is a
// disabled flat button so the icon follows the palette like the other icons do.
ToolButton {
    icon.source: "qrc:/icons/search"
    icon.width: 16
    icon.height: 16
    icon.color: palette.placeholderText
    enabled: false
    focusPolicy: Qt.NoFocus
    hoverEnabled: false
    padding: 0
    background: null
}
