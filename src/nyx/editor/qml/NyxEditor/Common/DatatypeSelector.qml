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
    enabled: component ? component.isEditable === true : false
    currentIndex: component ? indexOfValue(component.datatype) : -1

    onActivated: index => {
        if (controller && component)
            controller.setComponentDatatype(component.index, datatypes[index].id);
    }
}
