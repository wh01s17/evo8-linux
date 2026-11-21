import QtQuick
import "."

// Segmented horizontal slider: a row of square cells lit up to the value, with
// a square handle. Turned -90° it is the strips' fader. Drag, click or scroll;
// right click asks for mute (`rightClicked`).
Item {
    id: root
    property real value: 0
    property real minimum: 0
    property real maximum: 1
    property real step: 0.01
    property bool live: true
    signal moved(real value)
    signal rightClicked()

    implicitWidth: 120
    implicitHeight: 18
    opacity: enabled ? 1 : 0.4

    readonly property real cell: 6
    readonly property int cells: Math.max(4, Math.floor((width - cell) / (cell + 2)))
    readonly property real ratio: maximum > minimum
        ? Math.max(0, Math.min(1, (value - minimum) / (maximum - minimum))) : 0

    function valueAt(x) {
        var r = Math.max(0, Math.min(1, (x - cell / 2) / Math.max(1, width - cell)))
        var v = minimum + r * (maximum - minimum)
        if (step > 0) v = Math.round(v / step) * step
        return Math.max(minimum, Math.min(maximum, v))
    }

    Row {
        anchors.verticalCenter: parent.verticalCenter
        x: root.cell / 2
        spacing: 2
        Repeater {
            model: root.cells
            Rectangle {
                required property int index
                width: root.cell
                height: root.cell
                color: (index + 0.5) / root.cells <= root.ratio
                    ? Theme.foreground : Theme.alpha(Theme.accent, 0.22)
            }
        }
    }

    Rectangle {
        width: root.cell + 6
        height: root.cell + 6
        radius: width / 2
        anchors.verticalCenter: parent.verticalCenter
        x: root.ratio * (root.width - width)
        color: Theme.foreground
        border.color: Theme.background
        border.width: 1
    }

    MouseArea {
        anchors.fill: parent
        anchors.margins: -4
        enabled: root.enabled
        acceptedButtons: Qt.LeftButton | Qt.RightButton
        cursorShape: Qt.PointingHandCursor
        preventStealing: true
        onPressed: function(m) {
            if (m.button === Qt.RightButton) { root.rightClicked(); return }
            root.moved(root.valueAt(m.x - 4))
        }
        onPositionChanged: function(m) {
            if (pressed && (m.buttons & Qt.LeftButton)) root.moved(root.valueAt(m.x - 4))
        }
        onWheel: function(w) {
            var s = root.step > 0 ? root.step : (root.maximum - root.minimum) / 100
            var v = root.value + (w.angleDelta.y > 0 ? s : -s)
            root.moved(Math.max(root.minimum, Math.min(root.maximum, v)))
        }
    }
}
