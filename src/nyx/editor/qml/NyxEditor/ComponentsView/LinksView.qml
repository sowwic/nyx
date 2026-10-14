import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: linksViewRoot

    required property var inputLinks
    required property var outputLinks

    readonly property bool hasLinks: (inputLinks?.length ?? 0) > 0 || (outputLinks?.length ?? 0) > 0

    // Size the root from its content so parent layouts allocate enough room
    implicitWidth: linksContentColumnLayout.implicitWidth
    implicitHeight: linksContentColumnLayout.implicitHeight

    ColumnLayout {
        id: linksContentColumnLayout

        anchors.fill: parent
        spacing: 2

        Label {
            visible: !linksViewRoot.hasLinks
            Layout.fillWidth: true
            text: "No links"
        }

        Repeater {
            id: inputLinksRepeater

            model: linksViewRoot.inputLinks
            delegate: Label {
                required property string modelData

                Layout.fillWidth: true
                text: modelData
                elide: Text.ElideRight
            }
        }

        Repeater {
            id: outputLinksRepeater

            model: linksViewRoot.outputLinks
            delegate: Label {
                required property string modelData

                Layout.fillWidth: true
                text: modelData
                elide: Text.ElideRight
            }
        }
    }
}
