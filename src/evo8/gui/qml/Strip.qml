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
    property bool topEditable: false     // click its value to type it (in the control's units)

    property string faderTip: ""    // shown while hovering the fader
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
    property bool removeVisible: false     // a ✕ in the top-right corner (take the channel out)
    property string removeTip: ""
    signal removeClicked()

    property string bottomLabel: ""
    property bool bottomEnabled: true
    property real bottomValue: 0
    property real bottomMaximum: 1
    property real bottomStep: 1
    property string bottomText: ""
    property real bottomStandard: NaN
    property string bottomTip: ""

    // Optional button under the bottom control (Compartido: calibrate).
    property string actionText: ""
    property bool actionEnabled: true
    property string actionTip: ""
    signal actionClicked()

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
    // Width of a regular strip (the master is 1.3×) and fader height; the
    // console sets both so the strips fill the window.
    property real unit: Theme.stripWidth
    property real faderHeight: Theme.faderHeight
    // Everything but the fader, summed from the other children (the
    // column's own height includes the fader: that would be a binding loop).
    readonly property real chromeHeight: {
        var h = 16, n = 0
        for (var i = 0; i < column.children.length; i++) {
            var c = column.children[i]
            if (c === faderArea || !c.visible) continue
            h += c.height
            n++
        }
        return h + column.spacing * n
    }

    width: master ? unit * 1.3 : unit
    height: column.implicitHeight + 16

    // Above the column, so the title keeps its centre.
    GlyphButton {
        z: 1
        visible: strip.removeVisible
        anchors.top: parent.top
        anchors.right: parent.right
        anchors.topMargin: 6
        anchors.rightMargin: 8
        text: "󰅖"
        font.pixelSize: Theme.body
        color: Theme.dim
        tip: strip.removeTip
        onClicked: strip.removeClicked()
    }

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
        property bool editable: false
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
            standard: sc.standard
            minimum: sc.minimum
            maximum: sc.maximum
            step: sc.step
            value: sc.val
            enabled: sc.controlEnabled
            onMoved: function(v) { sc.changed(v) }
        }
        // The value; when editable, a click turns it into a field:
        // Enter applies (clamped to the range, on the step grid), Esc cancels.
        Item {
            width: parent.width
            height: valueLabel.implicitHeight
            Text {
                id: valueLabel
                anchors.fill: parent
                visible: !field.visible
                horizontalAlignment: Text.AlignHCenter
                text: sc.text
                color: sc.controlEnabled ? Theme.foreground : Theme.dim
                font.family: Theme.font
                font.pixelSize: Theme.caption
                font.bold: true
                font.underline: sc.editable && sc.controlEnabled && valueMouse.containsMouse
            }
            MouseArea {
                id: valueMouse
                anchors.fill: parent
                enabled: sc.editable && sc.controlEnabled
                hoverEnabled: true
                cursorShape: Qt.IBeamCursor
                onClicked: {
                    field.text = String(Math.round(sc.val * 100) / 100)
                    field.visible = true
                    field.forceActiveFocus()
                    field.selectAll()
                }
            }
            Tip {
                visible: valueMouse.containsMouse && !field.visible
                text: "Clic para escribir el valor (" + sc.minimum + " a " + sc.maximum + ")"
            }
            Rectangle {
                anchors.fill: field
                anchors.margins: -2
                visible: field.visible
                color: Theme.surface
                radius: Theme.radius
                border.color: field.invalid ? Theme.urgent : Theme.accent
            }
            TextInput {
                id: field
                objectName: sc.editable ? "typedValue" : ""
                property bool invalid: text !== "" && F.parseTyped(text, sc.minimum, sc.maximum, sc.step) === null
                anchors.fill: parent
                visible: false
                horizontalAlignment: TextInput.AlignHCenter
                color: Theme.foreground
                selectionColor: Theme.alpha(Theme.accent, 0.5)
                font.family: Theme.font
                font.pixelSize: Theme.caption
                font.bold: true
                selectByMouse: true
                function commit() {
                    var v = F.parseTyped(text, sc.minimum, sc.maximum, sc.step)
                    visible = false
                    if (v !== null) sc.changed(v)
                }
                onAccepted: commit()
                onActiveFocusChanged: if (!activeFocus && visible) commit()
                // Esc here cancels the edit instead of closing the window.
                Keys.onShortcutOverride: function(e) { e.accepted = (e.key === Qt.Key_Escape) }
                Keys.onEscapePressed: visible = false
            }
            // While editing, a click anywhere else in the window applies, like
            // Enter (clicking empty space takes no focus, so focus loss is not
            // enough). The click still reaches whatever is under it.
            MouseArea {
                parent: field.visible && field.Window.window ? field.Window.window.contentItem : field
                anchors.fill: parent
                z: 10000
                enabled: field.visible
                visible: field.visible
                onPressed: function(mouse) {
                    var p = mapToItem(field, mouse.x, mouse.y)
                    if (p.x < 0 || p.y < 0 || p.x > field.width || p.y > field.height)
                        field.commit()
                    mouse.accepted = false
                }
            }
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
                editable: strip.topEditable
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
            id: faderArea
            width: parent.width
            height: strip.faderHeight

            // HoverHandler, not a MouseArea: it never takes the slider's input.
            HoverHandler { id: faderHover }
            Tip { visible: faderHover.hovered && strip.faderTip !== "" && strip.faderVisible; text: strip.faderTip }

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
                        standard: strip.standard
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

        Rectangle {
            visible: strip.actionText !== ""
            width: parent.width
            height: actionLabel.implicitHeight + 10
            radius: Theme.radius
            opacity: strip.actionEnabled ? 1 : 0.5
            color: actionMouse.containsMouse && strip.actionEnabled ? Theme.alpha(Theme.foreground, 0.12) : "transparent"
            border.width: 1
            border.color: Theme.alpha(Theme.foreground, strip.actionEnabled ? 0.45 : 0.2)
            Text {
                id: actionLabel
                anchors.centerIn: parent
                text: strip.actionText
                color: Theme.foreground
                font.family: Theme.font
                font.pixelSize: Theme.caption
            }
            MouseArea {
                id: actionMouse
                anchors.fill: parent
                enabled: strip.actionEnabled
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: strip.actionClicked()
            }
            Tip {
                visible: actionMouse.containsMouse && strip.actionTip !== ""
                text: strip.actionTip
            }
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
