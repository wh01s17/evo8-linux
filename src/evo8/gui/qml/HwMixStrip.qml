import QtQuick
import "."
import "format.js" as F

// One source in the EVO's internal mix, like a channel of EVO Control's mixer:
// pan (balance for a stereo pair), mute, and an upright fader in dB whose
// bottom cell is "off".
Item {
    id: strip
    property string title: ""
    property string subtitle: ""
    property var state: null          // {level, pan, muted} or null when unknown
    property bool pending: false
    property real floor: -61
    property real faderHeight: Theme.faderHeight * 0.8
    // Everything but the fader, so a parent can size the fader to fill a
    // height. Summed from the other children (never from the column's own
    // height, which includes the fader and would make a binding loop).
    readonly property real chromeHeight: {
        var h = 16, n = 0
        for (var i = 0; i < col.children.length; i++) {
            var c = col.children[i]
            if (c === faderBox || !c.visible) continue
            h += c.height
            n++
        }
        return h + col.spacing * n
    }
    signal levelMoved(real level)
    signal panMoved(real pan)
    signal muteToggled()

    readonly property bool known: state !== null
    readonly property real level: known ? Math.max(floor, state.level) : floor
    readonly property real pan: known ? state.pan : 0
    readonly property bool muted: known && state.muted

    width: Theme.stripWidth
    height: col.implicitHeight + 16
    opacity: known ? 1 : 0.5

    Rectangle {
        anchors.fill: parent
        radius: Theme.radius
        color: Theme.alpha(Theme.foreground, 0.03)
        border.width: strip.pending ? 1 : 0
        border.color: Theme.accent
    }

    Column {
        id: col
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.margins: 8
        spacing: 8

        Column {
            width: parent.width
            spacing: 1
            Text {
                width: parent.width
                horizontalAlignment: Text.AlignHCenter
                text: strip.title
                color: Theme.foreground
                font.family: Theme.font
                font.pixelSize: Theme.body
                font.bold: true
            }
            Text {
                width: parent.width
                horizontalAlignment: Text.AlignHCenter
                elide: Text.ElideRight
                text: strip.subtitle === "" ? " " : strip.subtitle
                color: Theme.dim
                font.family: Theme.font
                font.pixelSize: Theme.caption
            }
        }

        // Pan / balance with its reset to centre.
        Column {
            width: parent.width
            spacing: 3
            Item {
                width: parent.width
                height: panLabel.implicitHeight
                Text {
                    id: panLabel
                    text: "PAN"
                    color: Theme.dim
                    font.family: Theme.font
                    font.pixelSize: Theme.caption
                    font.letterSpacing: 1.2
                    font.bold: true
                }
                GlyphButton {
                    anchors.right: parent.right
                    anchors.verticalCenter: panLabel.verticalCenter
                    text: "󰑐"
                    font.pixelSize: Theme.caption
                    active: strip.known && !strip.muted && Math.abs(strip.pan) > 0.005
                    tip: "Al centro"
                    onClicked: strip.panMoved(0)
                }
            }
            PixelSlider {
                width: parent.width
                minimum: -1
                maximum: 1
                step: 0.05
                value: strip.pan
                enabled: strip.known && !strip.muted
                onMoved: function(v) { strip.panMoved(v) }
            }
            Text {
                width: parent.width
                horizontalAlignment: Text.AlignHCenter
                text: F.panText(strip.pan)
                color: Theme.foreground
                font.family: Theme.font
                font.pixelSize: Theme.caption
                font.bold: true
            }
        }

        GlyphButton {
            anchors.horizontalCenter: parent.horizontalCenter
            text: strip.muted ? "󰝟" : "󰕾"
            font.pixelSize: Theme.title
            color: strip.muted ? Theme.urgent : Theme.foreground
            active: strip.known
            tip: strip.muted ? "Volver a oír" : "Dejar de oír"
            onClicked: strip.muteToggled()
        }

        Item {
            id: faderBox
            width: parent.width
            height: strip.faderHeight
            Item {
                anchors.centerIn: parent
                width: 30
                height: parent.height
                opacity: strip.muted ? 0.5 : 1
                // 0 dB mark (the factory level).
                Rectangle {
                    width: parent.width
                    height: 1
                    color: Theme.alpha(Theme.foreground, 0.35)
                    y: 0
                }
                PixelSlider {
                    anchors.centerIn: parent
                    width: parent.height
                    rotation: -90
                    minimum: strip.floor
                    maximum: 0
                    step: 1
                    value: strip.muted ? strip.floor : strip.level
                    enabled: strip.known
                    onMoved: function(v) { strip.levelMoved(v) }
                    onRightClicked: strip.muteToggled()
                }
            }
        }

        Text {
            width: parent.width
            horizontalAlignment: Text.AlignHCenter
            text: !strip.known ? "?" : strip.muted ? "apagado" : Math.round(strip.level) + " dB"
            color: strip.muted ? Theme.urgent : (strip.pending ? Theme.accent : Theme.foreground)
            font.family: Theme.font
            font.pixelSize: Theme.caption
            font.bold: true
        }
    }
}
