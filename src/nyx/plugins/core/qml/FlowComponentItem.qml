import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id: flowItemRoot
    property var component
    spacing: 4

    Label {
        Layout.fillWidth: true
        text: "Inputs:"
    }

    Repeater {
        id: inputLinksRepeater

        Layout.fillWidth: true

        model: flowItemRoot.component.inputLinks
        delegate: Label {
            required property string modelData
            text: modelData
        }
    }

    Item {
        implicitHeight: 10
    }

    Label {
        Layout.fillWidth: true
        text: "Outputs:"
    }

    Repeater {
        id: outputLinksRepeater

        Layout.fillWidth: true

        model: flowItemRoot.component.outputLinks
        delegate: Label {
            required property string modelData

            text: modelData
        }
    }
}
