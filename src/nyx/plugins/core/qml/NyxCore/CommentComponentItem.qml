import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id: commentItemRoot
    property var component
    spacing: 4

    RowLayout {
        Layout.fillWidth: true

        TextArea {
            Layout.fillWidth: true
            text: commentItemRoot.component.displayValue
            onEditingFinished: {
                if (text === commentItemRoot.component.displayValue)
                    return;
                root.componentsController.setComponentValue(commentItemRoot.component.index, text, true);
            }
        }
    }
}
