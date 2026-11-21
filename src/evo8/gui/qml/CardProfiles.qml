import QtQuick
import "."

// Every sound card with its profiles as a pick list, the active one ticked,
// and a warning when the Mezcla needs another profile (EVO 8 → Pro Audio).
Item {
    id: root
    property var cards: []
    property real unit: Theme.stripWidth
    width: unit * 1.9
    height: list.implicitHeight + 16

    Rectangle {
        anchors.fill: parent
        radius: Theme.radius
        color: Theme.alpha(Theme.foreground, 0.03)
    }

    Column {
        id: list
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.margins: 8
        spacing: 12

        Repeater {
            model: root.cards
            Column {
                id: card
                required property var modelData
                width: list.width
                spacing: 2

                Row {
                    spacing: 6
                    Text {
                        visible: card.modelData.warning !== ""
                        text: "󰀦"
                        color: Theme.urgent
                        font.family: Theme.font
                        font.pixelSize: Theme.body
                    }
                    Text {
                        text: card.modelData.label
                        color: Theme.foreground
                        font.family: Theme.font
                        font.pixelSize: Theme.body
                        font.bold: true
                    }
                }
                Text {
                    visible: card.modelData.warning !== ""
                    text: card.modelData.warning
                    color: Theme.urgent
                    font.family: Theme.font
                    font.pixelSize: Theme.caption
                }
                Repeater {
                    model: card.modelData.profiles
                    Rectangle {
                        required property var modelData
                        readonly property bool active: modelData.name === card.modelData.active
                        width: card.width
                        height: label.implicitHeight + 8
                        radius: Theme.radius
                        color: active ? Theme.alpha(Theme.foreground, 0.12)
                             : mouse.containsMouse ? Theme.alpha(Theme.foreground, 0.07) : "transparent"
                        Text {
                            id: tick
                            x: 4
                            anchors.verticalCenter: parent.verticalCenter
                            width: 16
                            text: parent.active ? "󰄬" : ""
                            color: Theme.foreground
                            font.family: Theme.font
                            font.pixelSize: Theme.caption
                        }
                        Text {
                            id: label
                            anchors.left: tick.right
                            anchors.right: parent.right
                            anchors.verticalCenter: parent.verticalCenter
                            text: modelData.label
                            color: parent.active ? Theme.foreground : Theme.dim
                            font.family: Theme.font
                            font.pixelSize: Theme.caption
                            font.bold: parent.active
                            elide: Text.ElideRight
                        }
                        MouseArea {
                            id: mouse
                            anchors.fill: parent
                            hoverEnabled: true
                            enabled: !parent.active
                            cursorShape: Qt.PointingHandCursor
                            onClicked: mixer.setCardProfile(card.modelData.name, modelData.name)
                        }
                    }
                }
            }
        }
    }
}
