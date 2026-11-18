pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import NyxEditor.Common

ComponentValue {
    id: valueItemRoot

    readonly property bool hasInputConnection: component ? component.inputLinks.length > 0 : false

    label: "Value:"
    // The raw text is evaluated when set.
    evaluateOnFinish: true
    // A linked value comes from its source.
    editable: component ? component.isEditable && !hasInputConnection : false

    EditButton {
        editor: valueItemRoot
    }

    DatatypeSelector {
        component: valueItemRoot.component
        controller: valueItemRoot.controller
    }

    // Entries of a dictionary or list, empty for any other value.
    readonly property var valueRows: component && component.valueRows ? component.valueRows : []

    // A collection is listed, anything else is one line of text.
    displayDelegate: valueRows.length > 0 ? rowsDelegate : textDelegate

    Component {
        id: textDelegate

        TextField {
            readOnly: true
            opacity: valueItemRoot.editable ? 1.0 : 0.6
            text: valueItemRoot.maskedText

            TapHandler {
                onDoubleTapped: valueItemRoot.requestEdit()
            }
        }
    }

    Component {
        id: rowsDelegate

        ValueRowsView {
            rows: valueItemRoot.valueRows

            TapHandler {
                onDoubleTapped: valueItemRoot.requestEdit()
            }
        }
    }

    editDelegate: TextField {
        // Set once: what is typed must not be replaced by a binding. The raw value is
        // read directly, `maskedText` has not followed `editing` yet.
        Component.onCompleted: {
            text = valueItemRoot.textOf(ComponentValue.Raw);
            forceActiveFocus();
            selectAll();
        }
        onAccepted: if (valueItemRoot.editing)
            valueItemRoot.finishEdit(text)
        onActiveFocusChanged: if (!activeFocus && valueItemRoot.editing)
            valueItemRoot.finishEdit(text)
        Keys.onEscapePressed: valueItemRoot.cancelEdit()
    }
}
