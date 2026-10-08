import QtQuick

QtObject {
    id: state

    property int sourceRow: -1          // row being dragged, -1 when idle
    property int targetRow: -1          // slot currently under the dragged card
    property real shift: 0              // how far in-between rows move aside
    property bool committing: false     // true briefly after release, to suppress animations
    readonly property bool active: sourceRow >= 0

    // Clears itself shortly after a commit, so undo/redo still animate normally
    property Timer settleTimer: Timer {
        interval: 50
        onTriggered: state.committing = false
    }

    function begin(row) {
        sourceRow = row;
        targetRow = row;
    }

    function setTarget(row) {
        if (active && row !== targetRow)
            targetRow = row;
    }

    // Ends the drag and returns what to commit
    function finish() {
        const result = {
            from: sourceRow,
            to: targetRow
        };
        committing = true;
        settleTimer.restart();
        sourceRow = -1;
        targetRow = -1;
        return result;
    }

    // Preview offset for a row while another row is being dragged
    function offsetFor(row) {
        if (!active || row === sourceRow)
            return 0;
        if (sourceRow < targetRow && row > sourceRow && row <= targetRow)
            return -shift;
        if (sourceRow > targetRow && row >= targetRow && row < sourceRow)
            return shift;
        return 0;
    }
}
