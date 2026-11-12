import QtQuick

Item {
    id: root

    required property int index                      // injected by the ListView
    readonly property ListView view: ListView.view

    default property alias content: dragContent.data
    readonly property Item dragItem: dragContent

    property ReorderState reorderState: null
    property bool dragEnabled: true   // can this row be picked up?
    property bool dropEnabled: true   // can other rows be dragged over it?
    property bool isDragging: false   // set by the DragHandle

    signal moveRequested(int from, int to)

    width: view.width
    height: dragContent.height
    z: isDragging ? 2 : 1             // dragged row paints above neighbours

    function updateTarget() {
        if (!reorderState)
            return;
        const centerY = root.y + dragContent.y + dragContent.height / 2;
        const hit = view.indexAt(view.width / 2, centerY);
        if (hit < 0)
            return;
        const hitItem = view.itemAtIndex(hit);
        if (hitItem && !hitItem.dropEnabled)          // pinned rows are not valid targets
            return;
        reorderState.setTarget(hit);
    }

    onIsDraggingChanged: {
        if (!reorderState)
            return;
        if (isDragging) {
            reorderState.begin(index);
        } else {
            const result = reorderState.finish();
            dragContent.y = 0;                        // snap into its slot
            if (result.from >= 0 && result.from !== result.to)
                moveRequested(result.from, result.to);
        }
    }

    // Track the dragged card while it moves
    Connections {
        target: dragContent
        function onYChanged() {
            if (root.isDragging)
                root.updateTarget();
        }
    }

    // How far the dragged row's neighbours shift aside
    Binding {
        target: root.reorderState
        property: "shift"
        value: dragContent.height + root.view.spacing
        when: root.isDragging && root.reorderState !== null
    }

    // Applies the preview offset while another row is being dragged
    Item {
        id: previewShift
        width: root.width
        height: dragContent.height
        y: root.reorderState ? root.reorderState.offsetFor(root.index) : 0

        Behavior on y {
            enabled: !root.reorderState || !root.reorderState.committing
            NumberAnimation {
                duration: 120
                easing.type: Easing.OutCubic
            }
        }

        Item {
            id: dragContent
            width: previewShift.width
            height: childrenRect.height
        }
    }
}
