import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id: valueItemRoot
    property var component
    spacing: 4

    readonly property bool hasInputConnection: component.inputLinks.length > 0

    RowLayout {
        Layout.fillWidth: true

        Label {
            text: "Value:"
        }

        TextField {
            Layout.fillWidth: true
            text: valueItemRoot.component.displayValue

            enabled: valueItemRoot.component.isEditable && !valueItemRoot.hasInputConnection
            onAccepted: {
                if (text === valueItemRoot.component.displayValue)
                    return;
                root.componentsController.setComponentValue(valueItemRoot.component.index, text, false);
            }
        }
    }
}
