import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id: root
    required property var component

    spacing: 4

    Label {
        Layout.fillWidth: true
        text: "UUID: " + root.component.uuid
    }
    Label {
        Layout.fillWidth: true
        text: "Type ID: " + root.component.typeId
    }
    Label {
        Layout.fillWidth: true
        text: "Value: " + root.component.value
    }
    Label {
        Layout.fillWidth: true
        text: "Default Value: " + root.component.defaultValue
    }
    Label {
        Layout.fillWidth: true
        text: "Tags: " + root.component.tags
    }
    Label {
        Layout.fillWidth: true
        text: "Links: " + root.component.links
    }
    Label {
        Layout.fillWidth: true
        text: "Path: " + root.component.path
    }
    Label {
        Layout.fillWidth: true
        text: "Editable: " + root.component.isEditable
    }
    Label {
        Layout.fillWidth: true
        text: "Built-in: " + root.component.isBuiltIn
    }
}
