import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

// Header of a group of palette items, e.g. the items of one plugin.
Item {
    id: headerRoot

    required property string section

    width: ListView.view ? ListView.view.width : implicitWidth
    implicitHeight: headerLabel.implicitHeight + 10

    ColumnLayout {
        anchors.fill: parent
        anchors.topMargin: 6
        spacing: 2

        Label {
            id: headerLabel
            Layout.fillWidth: true
            Layout.leftMargin: 4
            text: headerRoot.section.length > 0 ? headerRoot.section : qsTr("Other")
            font.bold: true
            opacity: 0.7
            elide: Text.ElideRight
        }

        Rectangle {
            Layout.fillWidth: true
            height: 1
            color: headerRoot.palette.mid
        }
    }
}
