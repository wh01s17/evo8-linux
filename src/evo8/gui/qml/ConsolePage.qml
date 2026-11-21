import QtQuick
import QtQuick.Controls
import "."
import "format.js" as F

// The console: one strip per channel, in signal order -- inputs, Compartido,
// apps, the Mezcla master, the selected output's channels, card profiles.
ScrollView {
    id: page
    clip: true
    ScrollBar.vertical.policy: ScrollBar.AlwaysOff

    readonly property var m: mixer.model
    readonly property var meters: mixer.meters
    readonly property var gains: m.gains
    readonly property var preamp: m.preamp
    readonly property bool monitorOn: m.monitor === "on"

    // Standard positions the reset buttons return to.
    readonly property real standardPreamp: 0
    readonly property real standardInputGain: 1
    readonly property real standardSharedGain: 0.5
    readonly property real standardVolume: 1

    function peak(name, ch) {
        var p = meters ? meters[name] : null
        return p && ch < p.length ? p[ch] : 0
    }

    // Output channels in the stereo pairs they are wired as.
    readonly property var outputGroups: {
        var s = m.sink
        if (!s) return []
        var n = s.volumes.length
        if (!s.isPro || n <= 2) {
            var all = []
            for (var c = 0; c < n; c++) all.push(c)
            return [{ label: "SALIDA", channels: all }]
        }
        var groups = []
        for (var i = 0; i < n; i += 2)
            groups.push({ label: i + 1 < n ? "OUT " + (i + 1) + "-" + (i + 2) : "OUT " + (i + 1),
                          channels: i + 1 < n ? [i, i + 1] : [i] })
        return groups
    }

    function groupVolume(channels) {
        var v = 0
        for (var i = 0; i < channels.length; i++) v = Math.max(v, m.sink.volumes[channels[i]] || 0)
        return v
    }

    Item {
        implicitWidth: Math.max(page.availableWidth, consoleRow.implicitWidth)
        implicitHeight: consoleRow.implicitHeight

        Row {
            id: consoleRow
            anchors.horizontalCenter: parent.horizontalCenter
            spacing: 14

            // ---- inputs ----
            StripGroup {
                title: "ENTRADAS"
                Repeater {
                    model: page.preamp ? page.preamp.gains.length : 2
                    Strip {
                        required property int index
                        readonly property bool inMix: index < 2
                        title: "IN " + (index + 1)
                        subtitle: inMix ? "a la Mezcla" : "solo preamp"
                        topLabel: "PRE"
                        topTip: "Ganancia del preamp de la EVO"
                        topEnabled: !!page.preamp
                        topMinimum: page.preamp ? page.preamp.min : 0
                        topMaximum: page.preamp ? page.preamp.max : 1
                        topStep: page.preamp ? page.preamp.step : 0.5
                        topValue: page.preamp ? page.preamp.gains[index] : 0
                        topText: page.preamp ? F.signedDb(page.preamp.gains[index]) : "—"
                        topStandard: page.standardPreamp
                        faderVisible: inMix
                        faderEnabled: inMix && !!page.gains
                        noFaderText: "No entra a la Mezcla"
                        maximum: 2
                        standard: inMix ? page.standardInputGain : NaN
                        value: inMix && page.gains ? page.gains[index] : 0
                        valueText: inMix && page.gains ? F.gainDb(page.gains[index]) : "—"
                        meterLeft: inMix ? F.meterLevel(page.peak("suma", index)) : -1
                        muted: inMix && !!page.gains && page.gains[index] === 0
                        showMute: inMix
                        monitorVisible: index < page.m.inputMonitors.length
                        monitorChecked: page.monitorOn || !!page.m.inputMonitors[index]
                        monitorEnabled: !page.monitorOn
                        monitorTip: page.monitorOn
                            ? (inMix ? "Ya suena en el Monitor de la Mezcla" : "Apaga el Monitor de la Mezcla para oírla sola")
                            : "Escuchar esta entrada en la salida"
                        onTopMoved: function(v) { mixer.setPreamp(index, v) }
                        onMoved: function(v) { mixer.setGain(index, v) }
                        onMuteToggled: mixer.toggleGainMute(index)
                        onMonitorToggled: mixer.toggleInputMonitor(index)
                    }
                }
            }

            Divider {}

            // ---- Compartido ----
            StripGroup {
                title: "COMPARTIDO"
                Strip {
                    readonly property var esc: page.m.escucha
                    title: "COMP"
                    subtitle: "lo que envías aquí"
                    topLabel: "OÍR"
                    topTip: "Cuánto oyes Compartido (no cambia lo que sale a la llamada)"
                    topEnabled: !page.monitorOn && !!esc
                    topValue: esc ? esc.volume : 0
                    topText: page.monitorOn ? "monitor" : F.percent(topValue)
                    topStandard: page.standardVolume
                    onTopMoved: function(v) { mixer.setListenVolume(v) }
                    faderEnabled: !!page.gains
                    maximum: 2
                    standard: page.standardSharedGain
                    value: page.gains ? page.gains[2] : 0
                    valueText: page.gains ? F.gainDb(page.gains[2]) : "—"
                    meterLeft: F.meterLevel(page.peak("suma", 2))
                    meterRight: F.meterLevel(page.peak("suma", 3))
                    muted: !!page.gains && page.gains[2] === 0
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
                }
            }

            Divider { visible: page.m.streams.length > 0 }

            // ---- apps ----
            StripGroup {
                visible: page.m.streams.length > 0
                title: "APPS"
                Repeater {
                    model: page.m.streams
                    Strip {
                        required property var modelData
                        title: modelData.label
                        subtitle: modelData.shared ? "en Compartido" : "solo salida"
                        shareVisible: true
                        sharedOn: modelData.shared
                        maximum: 1.5
                        standard: page.standardVolume
                        value: modelData.volume
                        valueText: F.percent(modelData.volume)
                        muted: modelData.mute
                        onMoved: function(v) { mixer.setStreamVolume(modelData.index, v) }
                        onMuteToggled: mixer.toggleStreamMute(modelData.index)
                        onShareToggled: mixer.toggleStreamShared(modelData.index)
                    }
                }
            }

            Divider {}

            // ---- Mezcla master ----
            StripGroup {
                title: "SALE A LA LLAMADA"
                Strip {
                    readonly property var mz: page.m.mezcla
                    master: true
                    title: "MEZCLA"
                    subtitle: "micrófono virtual"
                    faderEnabled: !!mz
                    standard: page.standardVolume
                    value: mz ? mz.volume : 0
                    valueText: F.percent(value)
                    meterLeft: F.meterLevel(page.peak("mezcla", 0))
                    muted: !!mz && mz.mute
                    onMoved: function(v) { mixer.setMezclaVolume(v) }
                    onMuteToggled: mixer.toggleMezclaMute()
                    monitorVisible: page.m.monitor === "on" || page.m.monitor === "off"
                    monitorChecked: page.monitorOn
                    monitorTip: "Escuchar la Mezcla completa en la salida"
                    onMonitorToggled: mixer.toggleMonitor()
                }
            }

            Divider {}

            // ---- selected output ----
            StripGroup {
                title: "SALIDA · " + (page.m.sink ? page.m.sink.label.toUpperCase() : "—")
                Repeater {
                    model: page.outputGroups
                    Strip {
                        required property var modelData
                        required property int index
                        title: modelData.label
                        subtitle: page.m.sink && page.m.sink.isPro && modelData.channels[0] === 0 ? "audífonos 1" : ""
                        standard: page.standardVolume
                        value: page.m.sink ? page.groupVolume(modelData.channels) : 0
                        valueText: F.percent(value)
                        muted: !!page.m.sink && page.m.sink.mute
                        showMute: index === 0
                        onMoved: function(v) { mixer.setSinkChannels(modelData.channels, v) }
                        onMuteToggled: mixer.toggleSinkMute()
                    }
                }
            }

            Divider { visible: page.m.cards.length > 0 }

            // ---- card profiles ----
            StripGroup {
                visible: page.m.cards.length > 0
                title: "PERFILES"
                CardProfiles { cards: page.m.cards }
            }
        }
    }
}
