import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

// Search field with tokens. Text like `tags:logic` is a token: it filters while it is
// typed, Enter turns it into a removable chip in the bar. Backspace in an empty field
// removes the last chip.
Rectangle {
    id: searchRoot

    // Keys that make a token, e.g. ["tags", "section"]. Other `a:b` text stays text.
    property var tokenKeys: []
    property string placeholderText: qsTr("Search...")
    // Chips that were accepted, as strings like "tags:logic"
    property var tokens: []
    // Text in the field, same as typed
    property alias text: field.text

    // What to search for: text without a token being typed, and all the tokens
    readonly property string queryText: pendingToken === "" ? field.text.trim() : ""
    readonly property var queryTokens: pendingToken === "" ? tokens : [...tokens, pendingToken]
    readonly property bool isActive: queryText.length > 0 || queryTokens.length > 0
    // The text in the field if it reads as a token, empty if it doesn't
    readonly property string pendingToken: tokenFromText(field.text)

    signal queryChanged(string text, var tokens)

    implicitHeight: Math.max(field.implicitHeight, 28) + 4
    color: palette.base
    border.color: field.activeFocus ? palette.highlight : palette.mid
    border.width: 1
    radius: 3

    function tokenFromText(value) {
        const match = /^([A-Za-z_]+):(\S.*)$/.exec(value.trim());
        if (match === null || tokenKeys.indexOf(match[1].toLowerCase()) < 0)
            return "";
        return match[1].toLowerCase() + ":" + match[2].trim();
    }

    function commitToken() {
        const token = pendingToken;
        if (token === "")
            return false;
        if (tokens.indexOf(token) < 0)
            tokens = [...tokens, token];
        field.clear();
        return true;
    }

    function removeToken(index) {
        tokens = tokens.filter((_, i) => i !== index);
    }

    function clear() {
        tokens = [];
        field.clear();
    }

    onQueryTextChanged: queryChanged(queryText, queryTokens)
    onQueryTokensChanged: queryChanged(queryText, queryTokens)

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: 4
        anchors.rightMargin: 4
        spacing: 4

        ListView {
            id: chips

            Layout.preferredWidth: Math.min(contentWidth, searchRoot.width * 0.6)
            Layout.fillHeight: true
            Layout.topMargin: 3
            Layout.bottomMargin: 3
            visible: count > 0
            orientation: ListView.Horizontal
            spacing: 4
            clip: true
            interactive: contentWidth > width
            boundsBehavior: Flickable.StopAtBounds
            model: searchRoot.tokens

            delegate: Rectangle {
                id: chip

                required property string modelData
                required property int index

                height: ListView.view.height
                width: chipRow.implicitWidth + 8
                radius: 3
                color: searchRoot.palette.highlight
                opacity: 0.85

                Row {
                    id: chipRow
                    anchors.centerIn: parent
                    spacing: 4

                    Text {
                        anchors.verticalCenter: parent.verticalCenter
                        text: chip.modelData
                        font.pixelSize: 11
                        color: searchRoot.palette.highlightedText
                    }

                    Text {
                        anchors.verticalCenter: parent.verticalCenter
                        text: "×"
                        font.pixelSize: 14
                        font.bold: true
                        color: searchRoot.palette.highlightedText

                        MouseArea {
                            anchors.fill: parent
                            anchors.margins: -3
                            cursorShape: Qt.PointingHandCursor
                            onClicked: searchRoot.removeToken(chip.index)
                        }
                    }
                }
            }
        }

        TextField {
            id: field

            Layout.fillWidth: true
            Layout.fillHeight: true
            placeholderText: searchRoot.tokens.length > 0 ? "" : searchRoot.placeholderText
            selectByMouse: true
            background: null
            // Valid token text is shown in the highlight color, so it is clear Enter keeps it
            color: searchRoot.pendingToken !== "" ? searchRoot.palette.highlight : searchRoot.palette.text

            onAccepted: searchRoot.commitToken()
            Keys.onPressed: event => {
                if (event.key === Qt.Key_Backspace && text.length === 0 && searchRoot.tokens.length > 0) {
                    searchRoot.removeToken(searchRoot.tokens.length - 1);
                    event.accepted = true;
                }
            }
        }
    }
}
