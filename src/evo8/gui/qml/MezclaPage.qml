import QtQuick
import QtQuick.Controls
import "."
import "format.js" as F

// The virtual microphone, and only it: the switch that turns it on or off,
// then (while on) what goes into it -- the interface inputs chosen with + / ✕,
// Compartido, which apps play through Compartido -- and the Mezcla master with
// its monitor.
ScrollView {
    id: page
    clip: true
    ScrollBar.vertical.policy: ScrollBar.AlwaysOff

    readonly property var m: mixer.model
    readonly property var meters: mixer.meters
    readonly property var gains: m.gains
    readonly property string service: m.mezclaService || ""
    readonly property bool on: service === "on" || service === "legacy"
    readonly property bool ready: on && gains !== null && gains !== undefined
    readonly property bool canSwitch: !m.mezclaBusy && (service === "on" || service === "off" || service === "failed")
    readonly property bool monitorOn: m.monitor === "on"

    // Interface inputs in the Mezcla (1-4), and the ones that could be added.
    readonly property int inputCount: 4
    readonly property var members: m.mezclaInputs || []
    readonly property var missing: {
        var out = []
        for (var i = 1; i <= inputCount; i++) if (members.indexOf(i) < 0) out.push(i)
        return out
    }
    // Index in the gains list and the "suma" meter: inputs 1-2, Compartido
    // L/R, inputs 3-4 (mix:Gain 1-6).
    function gainIndex(inp) { return inp <= 2 ? inp - 1 : inp + 1 }

    // Standard positions the reset buttons return to.
    readonly property real standardInputGain: 1
    readonly property real standardSharedGain: 0.5
    readonly property real standardVolume: 1

    function peak(name, ch) {
        var p = meters ? meters[name] : null
        return p && ch < p.length ? p[ch] : 0
    }

    readonly property string stateText: {
        if (m.mezclaBusy) return on ? "ENCENDIENDO…" : "APAGANDO…"
        switch (service) {
        case "on": return "ENCENDIDO"
        case "off": return "APAGADO"
        case "failed": return "NO ARRANCÓ"
        case "legacy": return "SIEMPRE ENCENDIDO (INSTALACIÓN ANTERIOR)"
        case "missing": return "SIN INSTALAR"
        default: return ""
        }
    }
    readonly property string helpText: {
        switch (service) {
        case "legacy": return "La Mezcla de una versión anterior está cargada dentro de PipeWire y no se puede apagar. "
                            + "Si instalaste con pipx, corre «evoctl setup»; después reinicia PipeWire "
                            + "(systemctl --user restart pipewire pipewire-pulse wireplumber)."
        case "missing": return "Falta el servicio evo8-mezcla.service: corre «evoctl setup»."
        case "failed": return "El servicio no arrancó: journalctl --user -u evo8-mezcla.service dice por qué."
        // What to do now that it is on; what you get by turning it on.
        default: return page.on
            ? "Elige <b>Mezcla</b> como micrófono en cualquier app (OBS, un DAW, Discord, el navegador). "
              + "Suma las entradas de la EVO que agregues abajo y lo que mandes a Compartido."
            : "Enciéndelo para tener un micrófono más, <b>Mezcla</b>, que junta tus entradas de la EVO con "
              + "música o apps. Apagado no existe y no cambia nada del resto del sonido."
        }
    }

    // Strip width: fills the window, but these few strips never grow huge.
    readonly property int nGroups: 4
    readonly property real units: members.length + (missing.length > 0 ? 0.6 : 0) + 1 + 1.9 + 1.3
    readonly property real unit: Math.min(Theme.stripWidth * 1.7, Math.max(Theme.stripWidth,
        (availableWidth - (2 * nGroups - 2) * 14 - (nGroups - 1) - 6 - 4) / units))
    readonly property real faderHeight: Math.max(140, availableHeight - 30 - header.height - 14
                                                 - Math.max(compStrip.chromeHeight, masterStrip.chromeHeight))

    Column {
        width: Math.max(page.availableWidth, consoleRow.implicitWidth + 4)
        spacing: 14

        // ---- the switch ----
        Rectangle {
            id: header
            width: page.availableWidth - 4
            x: 2
            height: headerRow.implicitHeight + 20
            radius: Theme.radius
            color: Theme.alpha(page.on ? Theme.accent : Theme.foreground, page.on ? 0.08 : 0.04)
            border.width: 1
            border.color: Theme.alpha(page.on ? Theme.accent : Theme.foreground, page.on ? 0.45 : 0.2)

            Row {
                id: headerRow
                x: 14
                anchors.verticalCenter: parent.verticalCenter
                spacing: 16
                Toggle {
                    anchors.verticalCenter: parent.verticalCenter
                    checked: page.on
                    busy: !!page.m.mezclaBusy
                    enabled: page.canSwitch
                    tip: page.on ? "Apagar el micrófono virtual" : "Encender el micrófono virtual (queda encendido al reiniciar)"
                    onToggled: mixer.setMezclaEnabled(!page.on)
                }
                Column {
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 3
                    Text {
                        text: "MICRÓFONO VIRTUAL · " + page.stateText
                        color: page.service === "failed" || page.service === "missing" ? Theme.urgent
                             : page.on ? Theme.accent : Theme.foreground
                        font.family: Theme.font
                        font.pixelSize: Theme.body
                        font.bold: true
                        font.letterSpacing: 1.2
                    }
                    Text {
                        width: header.width - 120
                        wrapMode: Text.WordWrap
                        text: page.helpText
                        textFormat: Text.StyledText
                        color: page.service === "legacy" ? Theme.warn : Theme.dim
                        font.family: Theme.font
                        font.pixelSize: Theme.caption
                    }
                }
            }
        }

        Item {
            width: 1
            height: consoleRow.implicitHeight
            // Off: the strips stay laid out (no relayout on every switch),
            // just hidden and inert.
            opacity: page.ready ? 1 : 0
            enabled: page.ready

            Row {
                id: consoleRow
                x: 2
                spacing: 14

                // ---- inputs into the Mezcla ----
                StripGroup {
                    title: "ENTRADAS A LA MEZCLA"
                    Repeater {
                        id: inputStrips
                        model: page.members
                        Strip {
                            unit: page.unit
                            faderHeight: page.faderHeight
                            required property int modelData
                            readonly property int g: page.gainIndex(modelData)
                            title: "IN " + modelData
                            subtitle: "a la Mezcla"
                            removeVisible: true
                            removeTip: "Quitar de la Mezcla"
                            onRemoveClicked: mixer.setMezclaInput(modelData, false)
                            faderTip: "Cuánto entra esta entrada a la Mezcla"
                            faderEnabled: page.ready
                            maximum: 2
                            standard: page.standardInputGain
                            value: page.ready ? page.gains[g] : 0
                            valueText: page.ready ? F.gainDb(page.gains[g]) : "—"
                            meterLeft: F.meterLevel(page.peak("suma", g))
                            muted: page.ready && page.gains[g] === 0
                            onMoved: function(v) { mixer.setGain(g, v) }
                            onMuteToggled: mixer.toggleGainMute(g)
                        }
                    }

                    // + : add one of the interface inputs not in the Mezcla.
                    Rectangle {
                        visible: page.missing.length > 0
                        width: page.unit * 0.6
                        // As tall as an input strip (or Compartido's, with none left).
                        height: inputStrips.count > 0 && inputStrips.itemAt(0)
                            ? inputStrips.itemAt(0).height : compStrip.height
                        radius: Theme.radius
                        color: addMouse.containsMouse || addMenu.opened
                            ? Theme.alpha(Theme.foreground, 0.07) : "transparent"
                        border.width: 1
                        border.color: Theme.alpha(Theme.foreground, 0.18)

                        Column {
                            anchors.centerIn: parent
                            spacing: 6
                            Text {
                                anchors.horizontalCenter: parent.horizontalCenter
                                text: "󰐕"
                                color: Theme.foreground
                                font.family: Theme.font
                                font.pixelSize: 28
                            }
                            Text {
                                anchors.horizontalCenter: parent.horizontalCenter
                                text: "ENTRADA"
                                color: Theme.dim
                                font.family: Theme.font
                                font.pixelSize: Theme.caption
                                font.letterSpacing: 1.2
                            }
                        }
                        MouseArea {
                            id: addMouse
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: page.missing.length === 1
                                ? mixer.setMezclaInput(page.missing[0], true) : addMenu.open()
                        }
                        Tip {
                            visible: addMouse.containsMouse && !addMenu.opened
                            text: page.missing.length === 1
                                ? "Agregar la entrada " + page.missing[0] + " a la Mezcla"
                                : "Agregar una entrada de la EVO a la Mezcla"
                        }

                        Popup {
                            id: addMenu
                            x: parent.width + 6
                            y: (parent.height - height) / 2
                            padding: 6
                            background: Rectangle {
                                color: Theme.surface
                                radius: Theme.radius
                                border.color: Theme.alpha(Theme.foreground, 0.3)
                            }
                            contentItem: Column {
                                spacing: 2
                                Repeater {
                                    model: page.missing
                                    Rectangle {
                                        required property int modelData
                                        width: 120
                                        height: itemLabel.implicitHeight + 10
                                        radius: Theme.radius
                                        color: itemMouse.containsMouse ? Theme.alpha(Theme.foreground, 0.1) : "transparent"
                                        Text {
                                            id: itemLabel
                                            x: 8
                                            anchors.verticalCenter: parent.verticalCenter
                                            text: "󰐕  IN " + modelData
                                            color: Theme.foreground
                                            font.family: Theme.font
                                            font.pixelSize: Theme.caption
                                            font.bold: true
                                        }
                                        MouseArea {
                                            id: itemMouse
                                            anchors.fill: parent
                                            hoverEnabled: true
                                            cursorShape: Qt.PointingHandCursor
                                            onClicked: {
                                                mixer.setMezclaInput(modelData, true)
                                                addMenu.close()
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }

                Divider { height: page.faderHeight + 220 }

                // ---- Compartido ----
                StripGroup {
                    title: "COMPARTIDO"
                    Strip {
                        id: compStrip
                        unit: page.unit
                        faderHeight: page.faderHeight
                        readonly property var esc: page.m.escucha
                        title: "COMP"
                        subtitle: "música y apps"
                        topLabel: "OÍR"
                        topTip: "Cuánto oyes Compartido (no cambia lo que entra a la Mezcla)"
                        topEnabled: !page.monitorOn && !!esc
                        topValue: esc ? esc.volume : 0
                        topText: page.monitorOn ? "monitor" : F.percent(topValue)
                        topStandard: page.standardVolume
                        onTopMoved: function(v) { mixer.setListenVolume(v) }
                        faderTip: "Cuánto entra Compartido a la Mezcla"
                        faderEnabled: page.ready
                        maximum: 2
                        standard: page.standardSharedGain
                        value: page.ready ? page.gains[2] : 0
                        valueText: page.ready ? F.gainDb(page.gains[2]) : "—"
                        meterLeft: F.meterLevel(page.peak("suma", 2))
                        meterRight: F.meterLevel(page.peak("suma", 3))
                        muted: page.ready && page.gains[2] === 0
                        onMoved: function(v) { mixer.setSharedGain(v) }
                        onMuteToggled: mixer.toggleGainMute(2)
                        bottomLabel: "SINC"
                        bottomTip: "Retrasa Compartido hacia la Mezcla para alinearlo con lo que tocas"
                        bottomEnabled: page.m.delayMs !== null && page.m.delayMs !== undefined
                        bottomValue: bottomEnabled ? page.m.delayMs : 0
                        bottomMaximum: 500
                        bottomStep: 1
                        bottomText: F.delayText(bottomValue)
                        bottomStandard: 0
                        onBottomMoved: function(v) { mixer.setDelay(v) }
                        actionText: page.m.calibrating ? "Escuchando…" : "Calibrar"
                        actionEnabled: !page.m.calibrating && bottomEnabled
                        actionTip: "Suena un click por Compartido: toca un golpe corto en cada uno y se mide el desfase"
                        onActionClicked: mixer.calibrate()
                    }
                }

                // ---- which apps play through Compartido ----
                StripGroup {
                    title: "APPS A COMPARTIDO"
                    AppShare { streams: page.m.streams; unit: page.unit; height: compStrip.height }
                }

                Divider { height: page.faderHeight + 220 }

                // ---- Mezcla master ----
                StripGroup {
                    title: "MEZCLA"
                    Strip {
                        id: masterStrip
                        unit: page.unit
                        faderHeight: page.faderHeight
                        readonly property var mz: page.m.mezcla
                        master: true
                        title: "MEZCLA"
                        subtitle: "lo que reciben las apps"
                        faderTip: "Volumen del micrófono virtual: lo que reciben las apps"
                        faderEnabled: !!mz
                        standard: page.standardVolume
                        value: mz ? mz.volume : 0
                        valueText: F.percent(value)
                        meterLeft: F.meterLevel(page.peak("mezcla", 0))
                        muted: !!mz && mz.mute
                        onMoved: function(v) { mixer.setMezclaVolume(v) }
                        onMuteToggled: mixer.toggleMezclaMute()
                        monitorVisible: true
                        monitorEnabled: page.m.monitor === "on" || page.m.monitor === "off"
                        monitorChecked: page.monitorOn
                        monitorTip: "Escuchar la Mezcla completa en la salida"
                        onMonitorToggled: mixer.toggleMonitor()
                    }
                }
            }
        }
    }
}
