import QtQuick
import QtQuick.Controls

// Picks the datatype hint of a node component from the registered datatypes.
ComboBox {
    id: selectorRoot
    objectName: "datatypeSelector"

    // Row of the component in the components model.
    property var component
    property var controller: root.componentsController

    readonly property var datatypes: controller ? controller.availableDatatypes() : []

    model: datatypes
    textRole: "name"
    valueRole: "id"
    // Locked by the component, e.g. built-ins or a datatype taken from a source.
    enabled: component ? component.isEditable === true && component.isDatatypeLocked !== true : false
    currentIndex: component ? indexOfValue(component.resolvedDatatype) : -1
    // A datatype that can't be picked, like flow, is still shown when it is in effect.
    displayText: currentIndex >= 0 ? currentText : (component ? component.resolvedDatatype : "")

    onActivated: index => {
        if (controller && component)
            controller.setComponentDatatype(component.index, datatypes[index].id);
    }
}
