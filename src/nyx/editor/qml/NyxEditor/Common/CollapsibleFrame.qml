import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    id: collapsibleFrameRoot

    // ---- Public API ----
    property string titleText: ""
    property bool isExpanded: true
    property int framePaddingPixels: 8
    property int contentSpacingPixels: 4
    property int expandCollapseAnimationDurationMilliseconds: 150
    property color backgroundColor: collapsibleFrameRoot.palette.base

    // Emitted only when the user toggles the frame (header click or toggleExpandedState()),
    // never when isExpanded is changed from outside. Use it to write the state back to a model.
    signal expandedStateToggledByUser(bool newExpandedState)

    // Anything declared as a child of CollapsibleFrame ends up in the content area
    default property alias contentItems: collapsibleContentColumnLayout.data

    // ---- Appearance ----
    // color: collapsibleFrameRoot.backgroundColor
    color: "transparent"
    border.color: collapsibleFrameRoot.palette.mid
    border.width: 1
    radius: 4

    // ---- Sizing: derived from content so parent layouts allocate enough room ----
    implicitWidth: frameContentColumnLayout.implicitWidth + 2 * collapsibleFrameRoot.framePaddingPixels
    implicitHeight: frameContentColumnLayout.implicitHeight + 2 * collapsibleFrameRoot.framePaddingPixels

    function toggleExpandedState() {
        collapsibleFrameRoot.isExpanded = !collapsibleFrameRoot.isExpanded;
        collapsibleFrameRoot.expandedStateToggledByUser(collapsibleFrameRoot.isExpanded);
    }

    ColumnLayout {
        id: frameContentColumnLayout

        anchors.fill: parent
        anchors.margins: collapsibleFrameRoot.framePaddingPixels
        spacing: collapsibleFrameRoot.contentSpacingPixels

        // ---- Header (click to toggle) ----
        Item {
            id: headerClickableArea

            Layout.fillWidth: true
            implicitHeight: headerRowLayout.implicitHeight

            RowLayout {
                id: headerRowLayout

                anchors.fill: parent
                spacing: 6

                Label {
                    id: expandCollapseIndicatorLabel

                    text: "\u25B6" // right-pointing triangle
                    font.pixelSize: titleLabel.font.pixelSize * 0.8
                    rotation: collapsibleFrameRoot.isExpanded ? 90 : 0

                    Behavior on rotation {
                        NumberAnimation {
                            duration: collapsibleFrameRoot.expandCollapseAnimationDurationMilliseconds
                            easing.type: Easing.InOutQuad
                        }
                    }
                }

                Label {
                    id: titleLabel

                    Layout.fillWidth: true
                    text: collapsibleFrameRoot.titleText
                    font.bold: true
                    elide: Text.ElideRight
                }
            }

            HoverHandler {
                id: headerHoverHandler
                cursorShape: Qt.PointingHandCursor
            }

            TapHandler {
                id: headerTapHandler
                onTapped: collapsibleFrameRoot.toggleExpandedState()
            }
        }

        // ---- Collapsible content ----
        Item {
            id: collapsibleContentClippingItem

            Layout.fillWidth: true
            clip: true

            implicitWidth: collapsibleContentColumnLayout.implicitWidth
            implicitHeight: collapsibleFrameRoot.isExpanded ? collapsibleContentColumnLayout.implicitHeight : 0

            // Hide completely once collapsed so the parent layout spacing doesn't leave a gap
            visible: collapsibleFrameRoot.isExpanded || implicitHeight > 0

            Behavior on implicitHeight {
                NumberAnimation {
                    duration: collapsibleFrameRoot.expandCollapseAnimationDurationMilliseconds
                    easing.type: Easing.InOutQuad
                }
            }

            ColumnLayout {
                id: collapsibleContentColumnLayout

                anchors.top: parent.top
                anchors.left: parent.left
                anchors.right: parent.right
                spacing: collapsibleFrameRoot.contentSpacingPixels
            }
        }
    }
}
