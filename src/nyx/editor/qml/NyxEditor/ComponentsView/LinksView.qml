import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: linksViewRoot

    // Emitted with the direction ("Input" or "Output") and the path of the component
    // at the other end of the link whose "x" button was clicked.
    signal unlinkRequested(string direction, string linkPath)

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
            delegate: LinkItemDelegate {
                required property string modelData

                Layout.fillWidth: true
                linkDirection: "Input"
                linkPath: modelData
                onUnlinkRequested: linksViewRoot.unlinkRequested(linkDirection, linkPath)
            }
        }

        Repeater {
            id: outputLinksRepeater

            model: linksViewRoot.outputLinks
            delegate: LinkItemDelegate {
                required property string modelData

                Layout.fillWidth: true
                linkDirection: "Output"
                linkPath: modelData
                onUnlinkRequested: linksViewRoot.unlinkRequested(linkDirection, linkPath)
            }
        }
    }
}
