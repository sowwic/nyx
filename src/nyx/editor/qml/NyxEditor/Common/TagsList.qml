import QtQuick
import QtQuick.Controls

// Row of tags, each one a text in a white frame. Scrolls sideways when the tags don't
// fit in the width it is given.
Flickable {
    id: tagsRoot

    // List of strings
    property var tags: []
    // Most of the width the list takes, it is as wide as its tags up to this
    property real maximumWidth: 200

    readonly property bool hasTags: tags !== null && tags !== undefined && tags.length > 0

    implicitWidth: Math.min(contentWidth, maximumWidth)
    implicitHeight: tagsRow.implicitHeight
    width: implicitWidth
    height: implicitHeight
    visible: hasTags
    contentWidth: tagsRow.implicitWidth
    contentHeight: tagsRow.implicitHeight
    clip: true
    flickableDirection: Flickable.HorizontalFlick
    boundsBehavior: Flickable.StopAtBounds
    // Only takes the mouse when there is something to scroll, so clicks and drags
    // on the tags still reach the item they are in
    interactive: contentWidth > width

    Row {
        id: tagsRow

        spacing: 4

        Repeater {
            model: tagsRoot.hasTags ? tagsRoot.tags : []

            delegate: Rectangle {
                id: tagFrame

                required property string modelData

                implicitWidth: tagText.implicitWidth + 10
                implicitHeight: tagText.implicitHeight + 4
                color: "transparent"
                border.color: "white"
                border.width: 1
                radius: 3

                Text {
                    id: tagText

                    anchors.centerIn: parent
                    text: tagFrame.modelData
                    font.pixelSize: 11
                    color: tagsRoot.palette.text
                }
            }
        }
    }
}
