import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    id: itemRoot

    required property var model
    required property int index
    required property string name
    required property string typeDisplayName
    required property bool isActive
    required property url editorQmlFile

    width: ListView.view ? ListView.view.width : 0
    height: mainLayout.implicitHeight + 2 * mainLayout.anchors.margins
    clip: true
    radius: 4
    color: palette.base

    Behavior on height {
        NumberAnimation {
            duration: 120
            easing.type: Easing.OutCubic
        }
    }

    ColumnLayout {
        id: mainLayout
        anchors {
            left: parent.left
            right: parent.right
            top: parent.top
            margins: 4
        }
        spacing: 4

        Label {
            Layout.fillWidth: true
            text: "UUID: " + itemRoot.model.uuid
        }

        Label {
            Layout.fillWidth: true
            text: "Type ID: " + itemRoot.model.typeId
        }

        Label {
            Layout.fillWidth: true
            text: "Type: " + itemRoot.model.typeDisplayName
        }

        Label {
            Layout.fillWidth: true
            text: "Active: " + itemRoot.model.isActive
        }

        Label {
            Layout.fillWidth: true
            text: "Name: " + itemRoot.model.name
        }

        Label {
            Layout.fillHeight: true
            text: "Value: " + itemRoot.model.value
        }

        Label {
            Layout.fillHeight: true
            text: "Default Value: " + itemRoot.model.defaultValue
        }

        Label {
            Layout.fillHeight: true
            text: "Tags: " + itemRoot.model.tags
        }

        Label {
            Layout.fillHeight: true
            text: "Links: " + itemRoot.model.links
        }

        Label {
            Layout.fillHeight: true
            text: "Path: " + itemRoot.model.path
        }

        Label {
            Layout.fillHeight: true
            text: "Editable: " + itemRoot.model.isEditable
        }
        Label {
            Layout.fillHeight: true
            text: "Built-in: " + itemRoot.model.isBuiltIn
        }

        Label {
            Layout.fillHeight: true
            text: "QML Source: " + itemRoot.model.editorQmlFile
        }
    }
}
