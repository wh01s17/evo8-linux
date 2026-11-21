import QtQuick
import "."
import "format.js" as F

// One channel strip, top to bottom:
//   title / subtitle
//   optional top control (PRE gain, Compartido listening level) + its reset
//   share + mute buttons
//   meter(s) beside an upright fader with its standard position marked
//   value + reset
//   optional bottom control (Compartido's sync delay) + reset
//   optional MONITOR switch
Item {
    id: strip
    property string title: ""
    property string subtitle: ""
    property bool master: false

    property string topLabel: ""
    property bool topEnabled: true
    property real topValue: 0
    property real topMinimum: 0
    property real topMaximum: 1
    property real topStep: 0.01
    property string topText: ""
    property real topStandard: NaN
    property string topTip: ""

    property bool faderEnabled: true
    property bool faderVisible: true
    property string noFaderText: ""
    property real value: 0
    property real minimum: 0
    property real maximum: 1
    property real step: 0.01
    property real standard: NaN
    property string valueText: ""
    property real meterLeft: -1
    property real meterRight: -1
    property bool muted: false
    property bool showMute: true
    property bool shareVisible: false
    property bool sharedOn: false

    property string bottomLabel: ""
    property bool bottomEnabled: true
    property real bottomValue: 0
    property real bottomMaximum: 1
    property real bottomStep: 1
    property string bottomText: ""
    property real bottomStandard: NaN
    property string bottomTip: ""

    property bool monitorVisible: false
    property bool monitorChecked: false
    property bool monitorEnabled: true
    property string monitorTip: ""

    signal moved(real value)
    signal topMoved(real value)
    signal bottomMoved(real value)
    signal muteToggled()
    signal shareToggled()
    signal monitorToggled()

    readonly property bool hasStandard: !isNaN(standard)

    width: master ? Theme.stripWidth * 1.3 : Theme.stripWidth
    height: column.implicitHeight + 16

    Rectangle {
        anchors.fill: parent
        radius: Theme.radius
        color: Theme.alpha(Theme.foreground, strip.master ? 0.07 : 0.03)
        border.width: strip.master ? 1 : 0
        border.color: Theme.alpha(Theme.foreground, 0.28)
    }

    // Label + reset on one line, the slider, the value underneath.
    component SmallControl: Column {
        id: sc
        property string label: ""
        property bool controlEnabled: true
        property real val: 0
        property real minimum: 0
        property real maximum: 1
        property real step: 0.01
        property string text: ""
        property real standard: NaN
        property string tip: ""
        signal changed(real v)
        width: parent.width
        spacing: 3

        Item {
            width: parent.width
            height: labelText.implicitHeight
            opacity: sc.controlEnabled ? 1 : 0.45
            Text {
                id: labelText
                text: sc.label
                color: Theme.dim
                font.family: Theme.font
                font.pixelSize: Theme.caption
                font.letterSpacing: 1.2
                font.bold: true
                MouseArea { id: labelMouse; anchors.fill: parent; hoverEnabled: true }
                Tip { visible: labelMouse.containsMouse && sc.tip !== ""; text: sc.tip }
            }
            GlyphButton {
                anchors.right: parent.right
                anchors.verticalCenter: labelText.verticalCenter
                visible: !isNaN(sc.standard)
                text: "󰑐"
                font.pixelSize: Theme.caption
                active: sc.controlEnabled && !F.atDefault(sc.val, sc.standard, sc.step)
                tip: "Volver al estándar"
                onClicked: sc.changed(sc.standard)
            }
        }
        PixelSlider {
            width: parent.width
            minimum: sc.minimum
            maximum: sc.maximum
            step: sc.step
            value: sc.val
            enabled: sc.controlEnabled
            onMoved: function(v) { sc.changed(v) }
        }
        Text {
            width: parent.width
            horizontalAlignment: Text.AlignHCenter
            text: sc.text
            color: sc.controlEnabled ? Theme.foreground : Theme.dim
            font.family: Theme.font
            font.pixelSize: Theme.caption
            font.bold: true
        }
    }

    Column {
        id: column
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
                elide: Text.ElideRight
            }
            Text {
                width: parent.width
                horizontalAlignment: Text.AlignHCenter
                text: strip.subtitle === "" ? " " : strip.subtitle
                color: Theme.dim
                font.family: Theme.font
                font.pixelSize: Theme.caption
                elide: Text.ElideRight
            }
        }

        // Top control; an empty slot keeps every strip's fader aligned.
        Item {
            width: parent.width
            height: 62
            SmallControl {
                visible: strip.topLabel !== ""
                label: strip.topLabel
                controlEnabled: strip.topEnabled
                val: strip.topValue
                minimum: strip.topMinimum
                maximum: strip.topMaximum
                step: strip.topStep
                text: strip.topText
                standard: strip.topStandard
                tip: strip.topTip
                onChanged: function(v) { strip.topMoved(v) }
            }
        }

        // Share + mute.
        Item {
            width: parent.width
            height: 26
            Row {
                anchors.centerIn: parent
                spacing: 14
                GlyphButton {
                    visible: strip.shareVisible
                    text: "󰒗"
                    font.pixelSize: Theme.title
                    color: strip.sharedOn ? Theme.foreground : Theme.dim
                    opacity: strip.sharedOn ? 1 : 0.55
                    active: strip.faderEnabled
                    tip: strip.sharedOn ? "En Compartido (entra a la Mezcla)" : "Enviar a Compartido"
                    onClicked: strip.shareToggled()
                }
                GlyphButton {
                    visible: strip.showMute
                    text: strip.muted ? "󰝟" : "󰕾"
                    font.pixelSize: Theme.title
                    color: strip.muted ? Theme.urgent : Theme.foreground
                    active: strip.faderEnabled
                    tip: strip.muted ? "Activar" : "Silenciar"
                    onClicked: strip.muteToggled()
                }
            }
        }

        // Meters beside the fader.
        Item {
            width: parent.width
            height: Theme.faderHeight

            Text {
                visible: !strip.faderVisible
                anchors.centerIn: parent
                width: parent.width
                horizontalAlignment: Text.AlignHCenter
                wrapMode: Text.WordWrap
                text: strip.noFaderText
                color: Theme.dim
                font.family: Theme.font
                font.pixelSize: Theme.caption
            }

            Row {
                visible: strip.faderVisible
                anchors.centerIn: parent
                height: parent.height
                spacing: 4

                VMeter { visible: strip.meterLeft >= 0; height: parent.height; level: strip.meterLeft }
                VMeter { visible: strip.meterRight >= 0; height: parent.height; level: strip.meterRight }
                Item { visible: strip.meterLeft >= 0; width: 8; height: 1 }

                Item {
                    width: 30
                    height: parent.height
                    opacity: strip.faderEnabled ? (strip.muted ? 0.5 : 1) : 0.25

                    // Standard position mark.
                    Rectangle {
                        visible: strip.hasStandard
                        width: parent.width
                        height: 1
                        color: Theme.alpha(Theme.foreground, 0.35)
                        y: parent.height * (1 - (strip.standard - strip.minimum)
                                            / Math.max(0.0001, strip.maximum - strip.minimum))
                    }
                    PixelSlider {
                        anchors.centerIn: parent
                        width: parent.height
                        rotation: -90
                        minimum: strip.minimum
                        maximum: strip.maximum
                        step: strip.step
                        value: strip.value
                        enabled: strip.faderEnabled
                        onMoved: function(v) { strip.moved(v) }
                        onRightClicked: strip.muteToggled()
                    }
                }
            }
        }

        // Value and reset.
        Item {
            width: parent.width
            height: valueText.implicitHeight
            Text {
                id: valueText
                anchors.horizontalCenter: parent.horizontalCenter
                anchors.horizontalCenterOffset: strip.hasStandard ? -8 : 0
                text: strip.muted ? "silencio" : strip.valueText
                color: strip.muted ? Theme.urgent : Theme.foreground
                font.family: Theme.font
                font.pixelSize: Theme.caption
                font.bold: true
            }
            GlyphButton {
                anchors.left: valueText.right
                anchors.leftMargin: 6
                anchors.verticalCenter: valueText.verticalCenter
                visible: strip.hasStandard
                text: "󰑐"
                font.pixelSize: Theme.caption
                active: strip.faderEnabled && !F.atDefault(strip.value, strip.standard, strip.step)
                tip: "Volver al estándar"
                onClicked: strip.moved(strip.standard)
            }
        }

        SmallControl {
            visible: strip.bottomLabel !== ""
            label: strip.bottomLabel
            controlEnabled: strip.bottomEnabled
            val: strip.bottomValue
            minimum: 0
            maximum: strip.bottomMaximum
            step: strip.bottomStep
            text: strip.bottomText
            standard: strip.bottomStandard
            tip: strip.bottomTip
            onChanged: function(v) { strip.bottomMoved(v) }
        }

        Column {
            visible: strip.monitorVisible
            width: parent.width
            spacing: 4
            topPadding: 4
            Text {
                width: parent.width
                horizontalAlignment: Text.AlignHCenter
                text: "MONITOR"
                color: Theme.dim
                font.family: Theme.font
                font.pixelSize: Theme.caption
                font.letterSpacing: 1.2
            }
            Toggle {
                anchors.horizontalCenter: parent.horizontalCenter
                checked: strip.monitorChecked
                enabled: strip.monitorEnabled
                tip: strip.monitorTip
                onToggled: strip.monitorToggled()
            }
        }
    }
}
