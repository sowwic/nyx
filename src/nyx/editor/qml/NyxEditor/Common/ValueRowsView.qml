import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

// Read-only list of the entries of a dictionary, list, tuple or set value.
//
// `rows` is a list of `{key, value, more}`, both as text, see the `valueRows` role of a
// component. A row with `more` is the note of a cut off collection and isn't counted.
// The key column fits the longest key, see `minKeyWidth` and `maxKeyWidth`.
// The list scrolls once it is taller than `maxVisibleRows` rows.
Rectangle {
    id: viewRoot

    property var rows: []
    property int maxVisibleRows: 8
    // The key column is as wide as the longest key, between these widths.
    property int minKeyWidth: 100
    property int maxKeyWidth: 200
    readonly property int keyWidth: {
        let widest = 0;
        for (const row of rows)
            widest = Math.max(widest, keyMetrics.advanceWidth(row.key));
        return Math.max(minKeyWidth, Math.min(maxKeyWidth, Math.ceil(widest) + 1));
    }

    readonly property int itemCount: {
        const hasNote = rows.length > 0 && rows[rows.length - 1].more === true;
        return hasNote ? rows.length - 1 : rows.length;
    }

    implicitHeight: header.implicitHeight + Math.min(list.contentHeight, list.rowHeight * maxVisibleRows) + 2 * border.width + 4
    radius: 4
    color: palette.base
    border.color: palette.mid

    FontMetrics {
        id: keyMetrics

        font.bold: true
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 2
        spacing: 0

        Label {
            id: header

            Layout.fillWidth: true
            Layout.leftMargin: 4
            text: viewRoot.itemCount === 1 ? qsTr("1 item") : qsTr("%1 items").arg(viewRoot.itemCount)
            color: palette.placeholderText
            font.pixelSize: 11
        }

        ListView {
            id: list

            readonly property int rowHeight: 22

            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            model: viewRoot.rows
            boundsBehavior: Flickable.StopAtBounds

            ScrollBar.vertical: ScrollBar {}

            delegate: Rectangle {
                id: rowItem

                required property int index
                required property var modelData

                width: ListView.view.width
                height: Math.max(list.rowHeight, valueText.implicitHeight + 4)
                color: index % 2 ? palette.alternateBase : "transparent"

                Label {
                    id: keyText

                    anchors.left: parent.left
                    anchors.leftMargin: 4
                    anchors.verticalCenter: parent.verticalCenter
                    width: viewRoot.keyWidth
                    text: rowItem.modelData.key
                    elide: Text.ElideRight
                    font.bold: true
                    color: rowItem.modelData.more ? palette.placeholderText : palette.text
                }

                // Selectable, so a value can be copied.
                TextEdit {
                    id: valueText

                    anchors.left: keyText.right
                    anchors.leftMargin: 6
                    anchors.right: parent.right
                    anchors.rightMargin: 14
                    anchors.verticalCenter: parent.verticalCenter
                    text: rowItem.modelData.value
                    readOnly: true
                    selectByMouse: true
                    wrapMode: TextEdit.WrapAnywhere
                    color: palette.text
                    selectionColor: palette.highlight
                    selectedTextColor: palette.highlightedText
                }
            }
        }
    }
}
