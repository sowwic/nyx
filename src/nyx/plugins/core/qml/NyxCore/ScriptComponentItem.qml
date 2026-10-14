import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id: scriptItemRoot
    property var component
    spacing: 4

    RowLayout {
        Layout.fillWidth: true

        Label {
            text: "Source:"
        }

        TextField {
            Layout.fillWidth: true
            text: scriptItemRoot.component.displayValue
            enabled: scriptItemRoot.component.isEditable
            onAccepted: {
                if (text === scriptItemRoot.component.displayValue)
                    return;
                root.componentsController.setComponentValue(scriptItemRoot.component.index, text, true);
            }
        }
    }
}
