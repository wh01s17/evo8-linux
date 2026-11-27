import QtQuick
import QtQuick.Controls
import "."
import "format.js" as F

// Sound on the PC, without the virtual microphone: the interface's inputs as
// the system sees them, the apps playing, the selected output and the card
// profiles. Nothing here depends on the Mezcla being on.
ScrollView {
    id: page
    clip: true
    ScrollBar.vertical.policy: ScrollBar.AlwaysOff

    readonly property var m: mixer.model
    readonly property var meters: mixer.meters
    readonly property var preamp: m.preamp
    readonly property var source: m.source
    readonly property bool monitorOn: m.monitor === "on"

    // Standard positions the reset buttons return to.
    readonly property real standardPreamp: 0
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

    // Strip width that fills the window: the room left after gaps and
    // dividers, shared by every strip (profiles count 1.9).
    readonly property int nInputs: preamp ? preamp.gains.length : 4
    readonly property int nApps: m.streams.length
    readonly property bool showProfiles: m.cards.length > 0
    readonly property int nGroups: 2 + (nApps > 0 ? 1 : 0) + (showProfiles ? 1 : 0)
    readonly property real units: nInputs + nApps + outputGroups.length + (showProfiles ? 1.9 : 0)
    readonly property int innerGaps: (nInputs - 1) + Math.max(0, nApps - 1) + Math.max(0, outputGroups.length - 1)
    readonly property real unit: Math.max(Theme.stripWidth,
        (availableWidth - (2 * nGroups - 2) * 14 - (nGroups - 1) - innerGaps * 6 - 4) / units)
    // Fader height that fills the window below the group titles; the input
    // strips (PRE on top, MONITOR below) are the tallest.
    readonly property real faderHeight: Math.max(140, availableHeight - 30
        - (inputs.count > 0 && inputs.itemAt(0) ? inputs.itemAt(0).chromeHeight : 330))

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
            x: 2
            spacing: 14

            // ---- inputs ----
            StripGroup {
                title: "ENTRADAS"
                Repeater {
                    id: inputs
                    model: page.nInputs
                    Strip {
                        unit: page.unit
                        faderHeight: page.faderHeight
                        required property int index
                        readonly property bool hasChannel: !!page.source && index < page.source.volumes.length
                        title: "IN " + (index + 1)
                        subtitle: "EVO 8"
                        topLabel: "PRE"
                        topTip: "Ganancia del preamp de la EVO"
                        topEnabled: !!page.preamp
                        topMinimum: page.preamp ? page.preamp.min : 0
                        topMaximum: page.preamp ? page.preamp.max : 1
                        topStep: page.preamp ? page.preamp.step : 0.5
                        topValue: page.preamp ? page.preamp.gains[index] : 0
                        topText: page.preamp ? F.signedDb(page.preamp.gains[index]) : "—"
                        topStandard: page.standardPreamp
                        topEditable: true
                        faderTip: "Volumen de la entrada " + (index + 1) + " para todo el sistema: la Mezcla, el monitor y cualquier app que grabe de la EVO"
                        faderEnabled: hasChannel
                        maximum: 1.5
                        standard: page.standardVolume
                        value: hasChannel ? page.source.volumes[index] : 0
                        valueText: hasChannel ? F.percent(value) : "—"
                        meterLeft: hasChannel ? F.meterLevel(page.peak("entradas", index)) : -1
                        muted: !!page.source && page.source.mute
                        // The system mutes the whole source, like the output: one button.
                        showMute: index === 0 && !!page.source
                        onMuteToggled: mixer.toggleSourceMute()
                        monitorVisible: index < page.m.inputMonitors.length
                        monitorChecked: page.monitorOn || !!page.m.inputMonitors[index]
                        monitorEnabled: !page.monitorOn
                        monitorTip: page.monitorOn
                            ? "Suena el Monitor del micrófono virtual: apágalo para oír la entrada sola"
                            : "Escuchar esta entrada en la salida"
                        onTopMoved: function(v) { mixer.setPreamp(index, v) }
                        onMoved: function(v) { mixer.setSourceChannel(index, v) }
                        onMonitorToggled: mixer.toggleInputMonitor(index)
                    }
                }
            }

            Divider { height: page.availableHeight - 8; visible: page.nApps > 0 }

            // ---- apps ----
            StripGroup {
                visible: page.nApps > 0
                title: "APPS"
                Repeater {
                    model: page.m.streams
                    Strip {
                        unit: page.unit
                        faderHeight: page.faderHeight
                        required property var modelData
                        title: modelData.label
                        subtitle: modelData.shared ? "por Compartido" : "a la salida"
                        faderTip: "Volumen de esta app"
                        maximum: 1.5
                        standard: page.standardVolume
                        value: modelData.volume
                        valueText: F.percent(modelData.volume)
                        muted: modelData.mute
                        onMoved: function(v) { mixer.setStreamVolume(modelData.index, v) }
                        onMuteToggled: mixer.toggleStreamMute(modelData.index)
                    }
                }
            }

            Divider { height: page.availableHeight - 8 }

            // ---- selected output ----
            StripGroup {
                title: "SALIDA · " + (page.m.sink ? page.m.sink.label.toUpperCase() : "—")
                Repeater {
                    model: page.outputGroups
                    Strip {
                        unit: page.unit
                        faderHeight: page.faderHeight
                        required property var modelData
                        required property int index
                        title: modelData.label
                        subtitle: page.m.sink && page.m.sink.isPro && modelData.channels[0] === 0 ? "audífonos 1" : ""
                        faderTip: "Volumen de la salida"
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

            Divider { height: page.availableHeight - 8; visible: page.showProfiles }

            // ---- card profiles ----
            StripGroup {
                visible: page.showProfiles
                title: "PERFILES"
                tip: "Cómo usa el sistema cada tarjeta de sonido: elige una opción"
                CardProfiles { cards: page.m.cards; unit: page.unit }
            }
        }
    }
}
