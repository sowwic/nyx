import QtQuick
import QtQuick.Controls

Item {
    id: sectionHeaderRoot

    // Injected by ListView: the stringified value of the section property,
    // so a bool arrives as "true" or "false".
    required property string section

    readonly property bool isBuiltInSection: section === "true"
    readonly property string sectionDisplayTitle: isBuiltInSection ? qsTr("Built-in") : qsTr("Custom")

    // Based on the application's default font, NOT on the label's own font,
    // otherwise the binding refers to the property it is assigning and loops.
    readonly property real sectionTitlePointSize: Math.max(Qt.application.font.pointSize - 1, 1)

    implicitHeight: sectionTitleLabel.implicitHeight + 8

    Label {
        id: sectionTitleLabel
        anchors {
            left: parent.left
            right: parent.right
            verticalCenter: parent.verticalCenter
            leftMargin: 4
        }
        text: sectionHeaderRoot.sectionDisplayTitle
        font.bold: true
        font.capitalization: Font.AllUppercase
        font.pointSize: sectionHeaderRoot.sectionTitlePointSize
        opacity: 0.6
    }

    // Thin rule under the title
    Rectangle {
        anchors {
            left: parent.left
            right: parent.right
            bottom: parent.bottom
        }
        height: 1
        color: palette.mid
    }
}
