import QtQuick
import "."

// A Nerd Font glyph that acts as a button, with a tooltip.
Text {
    id: glyph
    property bool active: true
    property string tip: ""
    signal clicked()
    font.family: Theme.font
    font.pixelSize: Theme.body
    color: Theme.foreground
    horizontalAlignment: Text.AlignHCenter
    verticalAlignment: Text.AlignVCenter
    opacity: active ? (mouse.containsMouse ? 1 : 0.85) : 0.18

    MouseArea {
        id: mouse
        anchors.fill: parent
        anchors.margins: -4
        enabled: glyph.active
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: glyph.clicked()
    }
    Tip {
        visible: mouse.containsMouse && glyph.tip !== ""
        text: glyph.tip
    }
}
