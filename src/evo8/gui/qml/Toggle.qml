import QtQuick
import "."

// On/off switch: a track with a square knob.
Item {
    id: root
    property bool checked: false
    property bool busy: false
    property string tip: ""
    signal toggled()
    implicitWidth: 44
    implicitHeight: 22
    opacity: enabled ? 1 : 0.45

    Rectangle {
        anchors.fill: parent
        radius: Theme.radius
        color: root.checked ? Theme.alpha(Theme.accent, 0.25) : "transparent"
        border.width: 1
        border.color: root.checked ? Theme.accent : Theme.alpha(Theme.foreground, mouse.containsMouse ? 0.6 : 0.3)
    }
    Rectangle {
        width: parent.height - 8
        height: width
        y: 4
        x: root.checked ? parent.width - width - 4 : 4
        color: root.checked ? Theme.accent : Theme.alpha(Theme.foreground, 0.65)
        Behavior on x { NumberAnimation { duration: 90 } }
    }
    MouseArea {
        id: mouse
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: if (!root.busy && root.enabled) root.toggled()
    }
    Tip {
        visible: mouse.containsMouse && root.tip !== ""
        text: root.tip
    }
}
