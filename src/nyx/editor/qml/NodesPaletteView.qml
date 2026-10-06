import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    id: root
    color: palette.window

    readonly property var activeModel: typeof nodesRegistryModel !== "undefined" ? nodesRegistryModel : null
    // readonly property var activeController: typeof componentsController !== "undefined" ? componentsController : null

    ListView {
        id: nodesPaletteListView
        anchors {
            top: parent.top
            left: parent.left
            right: parent.right
            bottom: parent.bottom
            margins: 6
            rightMargin: 6 + verticalScrollBar.width
        }

        model: root.activeModel
        spacing: 4
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        reuseItems: false   // delegates hold expanded state, so they should not be recycled

        ScrollBar.vertical: ScrollBar {
            id: verticalScrollBar

            parent: nodesPaletteListView.parent
            policy: ScrollBar.AsNeeded
            anchors {
                top: nodesPaletteListView.top
                bottom: nodesPaletteListView.bottom
                left: nodesPaletteListView.right
            }
        }

        delegate: ItemDelegate {
            required property var model

            width: ListView.view.width
            text: model.typeDisplayName

            onClicked: nodeSpawner.spawnNodeAtCenter(model.typeId)
        }
    }

    Label {
        anchors.centerIn: parent
        visible: root.activeModel.count === 0
        text: qsTr("No Nodes Available")
        opacity: 0.5
    }
}
