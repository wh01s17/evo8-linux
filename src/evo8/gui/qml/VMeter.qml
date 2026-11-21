import QtQuick
import "."
import "format.js" as F

// Segmented vertical peak meter on a dB scale, lit from the bottom; the top
// segments turn amber then red near clipping.
Item {
    id: meter
    property real level: 0     // 0..1 from F.meterLevel
    width: 5
    readonly property real cell: 5
    readonly property int segments: Math.max(8, Math.floor(height / cell))

    Repeater {
        model: meter.segments
        Rectangle {
            required property int index
            readonly property real position: (index + 0.5) / meter.segments
            readonly property string zone: F.meterZone(position)
            readonly property bool lit: position <= meter.level
            width: meter.width
            height: meter.height / meter.segments - 1
            y: meter.height - (index + 1) * (meter.height / meter.segments)
            color: zone === "hot" ? Theme.urgent : zone === "loud" ? Theme.warn : Theme.foreground
            opacity: lit ? 0.95 : 0.12
        }
    }
}
