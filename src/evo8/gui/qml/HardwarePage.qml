import QtQuick
import QtQuick.Controls
import "."
import "format.js" as F

// Settings stored in the EVO 8 itself, sent over USB. Sending them drops the
// audio for a moment, so changes wait here until "Aplicar".
ScrollView {
    id: page
    clip: true

    readonly property var hw: mixer.hardware
    readonly property var pending: hw.pending || ({})
    readonly property string pendingLoopback: hw.pendingLoopback || ""
    readonly property var pendingPhantom: hw.pendingPhantom || ({})
    readonly property var pendingMute: hw.pendingMute || ({})
    readonly property bool hasPending: Object.keys(pending).length > 0 || pendingLoopback !== ""
        || Object.keys(pendingPhantom).length > 0 || Object.keys(pendingMute).length > 0

    // Flag as it will be after "Aplicar": pending value, else last read.
    function flag(kind, i) {
        var p = kind === "phantom" ? pendingPhantom : pendingMute
        if (p[String(i)] !== undefined) return p[String(i)]
        var cur = hw[kind]
        return cur ? !!cur[i] : false
    }
    function flagPending(kind, i) {
        return (kind === "phantom" ? pendingPhantom : pendingMute)[String(i)] !== undefined
    }
    readonly property var rows: ["IN 1", "IN 2", "IN 3", "IN 4", "PC 1", "PC 2", "PC 3", "PC 4", "PC 5", "PC 6"]
    readonly property var outputs: ["OUT 1", "OUT 2", "OUT 3", "OUT 4"]
    readonly property var loopbackOptions: [
        { name: "loopback", label: "PC 5-6", detail: "par loop-back (fábrica)" },
        { name: "pc12", label: "Salidas 1-2", detail: "todo lo que suena en el PC" },
        { name: "pc34", label: "Salidas 3-4", detail: "" },
        { name: "in12", label: "Entradas 1-2", detail: "" },
        { name: "in34", label: "Entradas 3-4", detail: "" }
    ]
    readonly property real offPosition: -61    // slider's leftmost cell = off

    function cellValue(i, o) {
        var key = i + "," + o
        if (pending[key] !== undefined) return pending[key]
        return hw.mix ? hw.mix[i][o] : null
    }

    component Button: Rectangle {
        id: btn
        property string text: ""
        property bool primary: false
        property bool fill: false
        signal clicked()
        width: fill ? parent.width : label.implicitWidth + 24
        height: label.implicitHeight + 12
        radius: Theme.radius
        opacity: enabled ? 1 : 0.4
        color: primary && enabled ? Theme.alpha(Theme.accent, mouse.containsMouse ? 0.35 : 0.22)
             : mouse.containsMouse ? Theme.alpha(Theme.foreground, 0.1) : "transparent"
        border.width: 1
        border.color: primary ? Theme.accent : Theme.alpha(Theme.foreground, 0.4)
        Text {
            id: label
            anchors.centerIn: parent
            text: btn.text
            color: Theme.foreground
            font.family: Theme.font
            font.pixelSize: Theme.caption
            font.bold: btn.primary
        }
        MouseArea {
            id: mouse
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: btn.clicked()
        }
    }

    component SectionTitle: Text {
        color: Theme.dim
        font.family: Theme.font
        font.pixelSize: Theme.caption
        font.letterSpacing: 1.4
        font.bold: true
    }

    // Main area fills the visible window; "Avanzado" opens below it.
    readonly property real mainHeight: Math.max(460, page.availableHeight - 40)

    Column {
        width: page.availableWidth
        spacing: 18

        Item {
            width: parent.width
            height: page.mainHeight

            // ---- left: actions and inputs ----
            Column {
                id: side
                width: 340
                height: parent.height
                spacing: 14

                Text {
                    width: parent.width
                    wrapMode: Text.WordWrap
                    text: "Estos ajustes se guardan en la EVO. Leerlos o aplicarlos corta el audio un instante."
                    color: Theme.dim
                    font.family: Theme.font
                    font.pixelSize: Theme.caption
                }
                Column {
                    width: parent.width
                    spacing: 8
                    Button {
                        fill: true
                        text: "Leer de la EVO"
                        enabled: !page.hw.busy
                        onClicked: mixer.hwRead()
                    }
                    Button {
                        fill: true
                        text: page.hasPending ? "Aplicar a la EVO (cambios pendientes)" : "Aplicar a la EVO"
                        primary: true
                        enabled: !page.hw.busy && page.hasPending
                        onClicked: mixer.hwApply()
                    }
                    Button {
                        fill: true
                        text: "Descartar cambios"
                        enabled: !page.hw.busy && page.hasPending
                        onClicked: mixer.hwDiscard()
                    }
                }
                Text {
                    width: parent.width
                    wrapMode: Text.WordWrap
                    text: page.hw.message
                        ? page.hw.message
                        : (page.hw.readAt ? "Último estado conocido: " + page.hw.readAt
                                          : "Aún no se ha leído la EVO.")
                    color: String(page.hw.message).indexOf("Error") === 0 ? Theme.urgent : Theme.foreground
                    font.family: Theme.font
                    font.pixelSize: Theme.caption
                }

                Item { width: 1; height: 6 }
                SectionTitle { text: "ENTRADAS · 48 V Y SILENCIO" }
                Grid {
                    columns: 2
                    spacing: 10
                    Repeater {
                        model: 4
                        Rectangle {
                            required property int index
                            width: (side.width - 10) / 2
                            height: inCol.implicitHeight + 16
                            radius: Theme.radius
                            color: Theme.alpha(Theme.foreground, 0.03)
                            Column {
                                id: inCol
                                anchors.centerIn: parent
                                spacing: 8
                                Text {
                                    anchors.horizontalCenter: parent.horizontalCenter
                                    text: "IN " + (index + 1)
                                    color: Theme.foreground
                                    font.family: Theme.font
                                    font.pixelSize: Theme.body
                                    font.bold: true
                                }
                                Repeater {
                                    model: [{ kind: "phantom", label: "48 V" }, { kind: "mute", label: "SILENCIO" }]
                                    Row {
                                        required property var modelData
                                        spacing: 10
                                        Text {
                                            width: 72
                                            anchors.verticalCenter: parent.verticalCenter
                                            text: modelData.label
                                            color: page.flagPending(modelData.kind, index) ? Theme.accent : Theme.dim
                                            font.family: Theme.font
                                            font.pixelSize: Theme.caption
                                            font.bold: true
                                        }
                                        Toggle {
                                            checked: page.flag(modelData.kind, index)
                                            enabled: !page.hw.busy && !!page.hw[modelData.kind]
                                            tip: modelData.kind === "phantom"
                                                ? "Alimentación para micrófonos de condensador"
                                                : "Silenciar la entrada en la EVO"
                                            onToggled: modelData.kind === "phantom"
                                                ? mixer.hwSetPhantom(index, !checked)
                                                : mixer.hwSetMute(index, !checked)
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }

            Rectangle {
                id: split
                x: side.width + 20
                width: 1
                height: parent.height
                color: Theme.alpha(Theme.foreground, 0.12)
            }

            // ---- right: what the headphones hear directly (EVO Control's mixer) ----
            Column {
                id: hpMix
                anchors.left: split.right
                anchors.leftMargin: 20
                anchors.right: parent.right
                height: parent.height
                spacing: 10
            // 0 = audífonos 1 (outputs 1-2), 1 = audífonos 2 (outputs 3-4).
            property int pair: 0
            // Level and pan each strip had before muting, to bring them back.
            property var beforeMute: ({})
            readonly property var sources: [
                { title: "IN 1", subtitle: "entrada 1", rows: [0] },
                { title: "IN 2", subtitle: "entrada 2", rows: [1] },
                { title: "IN 3", subtitle: "entrada 3", rows: [2] },
                { title: "IN 4", subtitle: "entrada 4", rows: [3] },
                { title: "PC 1-2", subtitle: "audio del PC", rows: [4, 5] },
                { title: "PC 3-4", subtitle: "salidas 3-4", rows: [6, 7] },
                { title: "PC 5-6", subtitle: "loop-back", rows: [8, 9] }
            ]

            // Cells a source touches in the selected pair: [row, out] for left
            // and right; a stereo pair also owns its cross-feed cells.
            function cells(src) {
                var l = pair * 2, r = pair * 2 + 1
                if (src.rows.length === 1) return { left: [src.rows[0], l], right: [src.rows[0], r], cross: [] }
                return { left: [src.rows[0], l], right: [src.rows[1], r],
                         cross: [[src.rows[0], r], [src.rows[1], l]] }
            }
            function stateOf(src) {
                var c = cells(src)
                return F.hwLevelPan(page.cellValue(c.left[0], c.left[1]), page.cellValue(c.right[0], c.right[1]))
            }
            function isPending(src) {
                var c = cells(src), all = [c.left, c.right].concat(c.cross)
                for (var i = 0; i < all.length; i++)
                    if (page.pending[all[i][0] + "," + all[i][1]] !== undefined) return true
                return false
            }
            function write(src, level, pan) {
                var c = cells(src), v = F.hwCells(level, pan, page.offPosition)
                mixer.hwSetCell(c.left[0], c.left[1], v[0])
                mixer.hwSetCell(c.right[0], c.right[1], v[1])
                // A stereo source plays left on left and right on right.
                for (var i = 0; i < c.cross.length; i++) mixer.hwSetCell(c.cross[i][0], c.cross[i][1], F.HW_OFF)
            }
            function toggleMute(src) {
                var st = stateOf(src), key = src.title + "/" + pair
                if (!st) return
                if (st.muted) {
                    var back = beforeMute[key] || { level: 0, pan: 0 }
                    write(src, back.level, back.pan)
                } else {
                    var m = Object.assign({}, beforeMute)
                    m[key] = { level: st.level, pan: st.pan }
                    beforeMute = m
                    write(src, page.offPosition, 0)
                }
            }


                SectionTitle { text: "LO QUE OYES DIRECTO EN LOS AUDÍFONOS · SIN PASAR POR EL PC, SIN LATENCIA" }

                // Which headphone mix the strips below edit: one joined control.
                Row {
                    spacing: 14
                    Text {
                        width: 70
                        anchors.verticalCenter: parent.verticalCenter
                        text: "EDITAR"
                        color: Theme.dim
                        font.family: Theme.font
                        font.pixelSize: Theme.caption
                        font.letterSpacing: 1.2
                        font.bold: true
                    }
                    Rectangle {
                        width: seg.implicitWidth + 2
                        height: seg.implicitHeight + 2
                        radius: Theme.radius
                        color: "transparent"
                        border.width: 1
                        border.color: Theme.alpha(Theme.foreground, 0.35)
                        Row {
                            id: seg
                            x: 1
                            y: 1
                            Repeater {
                                model: ["Audífonos 1 · salidas 1-2", "Audífonos 2 · salidas 3-4"]
                                Rectangle {
                                    required property var modelData
                                    required property int index
                                    readonly property bool current: hpMix.pair === index
                                    width: segText.implicitWidth + 32
                                    height: segText.implicitHeight + 14
                                    radius: Theme.radius
                                    color: current ? Theme.alpha(Theme.accent, 0.3)
                                         : segMouse.containsMouse ? Theme.alpha(Theme.foreground, 0.08) : "transparent"
                                    Text {
                                        id: segText
                                        anchors.centerIn: parent
                                        text: (parent.current ? "● " : "○ ") + modelData
                                        color: parent.current ? Theme.foreground : Theme.dim
                                        font.family: Theme.font
                                        font.pixelSize: Theme.body
                                        font.bold: parent.current
                                    }
                                    MouseArea {
                                        id: segMouse
                                        anchors.fill: parent
                                        hoverEnabled: true
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked: hpMix.pair = index
                                    }
                                }
                            }
                        }
                    }
                }

                // Shortcuts: they only stage changes for the headphones being
                // edited; nothing reaches the EVO until "Aplicar".
                Row {
                    spacing: 14
                    function preset(level) {
                        for (var i = 0; i < page.rows.length; i++)
                            for (var o = hpMix.pair * 2; o <= hpMix.pair * 2 + 1; o++) {
                                var db = level(i)
                                if (db !== null) mixer.hwSetCell(i, o, db)
                            }
                    }
                    Text {
                        width: 70
                        anchors.verticalCenter: parent.verticalCenter
                        text: "ATAJOS"
                        color: Theme.dim
                        font.family: Theme.font
                        font.pixelSize: Theme.caption
                        font.letterSpacing: 1.2
                        font.bold: true
                    }
                    Repeater {
                        model: [
                            { label: "Como de fábrica", fn: function(i) { return 0 } },
                            { label: "No oír ninguna entrada", fn: function(i) { return i < 4 ? -128 : null } },
                            { label: "Oír solo la entrada 1", fn: function(i) { return i === 0 ? 0 : (i < 4 ? -128 : null) } },
                            { label: "Oír entradas 1 y 2", fn: function(i) { return i < 2 ? 0 : (i < 4 ? -128 : null) } }
                        ]
                        Text {
                            required property var modelData
                            anchors.verticalCenter: parent.verticalCenter
                            text: "› " + modelData.label
                            color: shortcutMouse.containsMouse && enabled ? Theme.foreground : Theme.dim
                            font.family: Theme.font
                            font.pixelSize: Theme.caption
                            font.underline: shortcutMouse.containsMouse && enabled
                            enabled: !page.hw.busy && !!page.hw.mix
                            opacity: enabled ? 1 : 0.4
                            MouseArea {
                                id: shortcutMouse
                                anchors.fill: parent
                                anchors.margins: -4
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: parent.parent.preset(modelData.fn)
                            }
                        }
                    }
                }

                Row {
                    id: strips
                    spacing: 6
                    readonly property real stripWidth: (hpMix.width - spacing * (hpMix.sources.length - 1)) / hpMix.sources.length
                    readonly property real available: hpMix.height - y - hint.height - hpMix.spacing
                    Repeater {
                        model: hpMix.sources
                        HwMixStrip {
                            required property var modelData
                            width: strips.stripWidth
                            faderHeight: Math.max(120, strips.available - chromeHeight)
                            title: modelData.title
                            subtitle: modelData.subtitle
                            floor: page.offPosition
                            state: page.hw.mix ? hpMix.stateOf(modelData) : null
                            pending: hpMix.isPending(modelData)
                            enabled: !page.hw.busy
                            onLevelMoved: function(v) {
                                var st = hpMix.stateOf(modelData)
                                hpMix.write(modelData, v, st && !st.muted ? st.pan : 0)
                            }
                            onPanMoved: function(p) {
                                var st = hpMix.stateOf(modelData)
                                if (st && !st.muted) hpMix.write(modelData, st.level, p)
                            }
                            onMuteToggled: hpMix.toggleMute(modelData)
                        }
                    }
                }
                Text {
                    id: hint
                    width: parent.width
                    elide: Text.ElideRight
                    text: page.hw.mix
                        ? "Fader abajo del todo o 󰝟 = no oír esa fuente. Los cambios llegan a la EVO al pulsar «Aplicar a la EVO»."
                        : "Pulsa «Leer de la EVO» para ver y cambiar estos valores."
                    color: Theme.dim
                    font.family: Theme.font
                    font.pixelSize: Theme.caption
                }
            }
        }

        // ---- advanced: loop-back and the full matrix ----
        Column {
            id: advanced
            property bool open: false
            spacing: 18

            // Opening scrolls the page down to the options, closing back up,
            // so the change is never off-screen.
            function toggle() {
                open = !open
                Qt.callLater(function() {
                    var f = page.contentItem
                    f.contentY = open ? Math.max(0, Math.min(advanced.y, f.contentHeight - f.height)) : 0
                })
            }

            Rectangle {
                width: advLabel.implicitWidth + 28
                height: advLabel.implicitHeight + 14
                radius: Theme.radius
                color: advanced.open ? Theme.alpha(Theme.foreground, 0.1)
                     : advMouse.containsMouse ? Theme.alpha(Theme.foreground, 0.07) : "transparent"
                border.width: 1
                border.color: Theme.alpha(Theme.foreground, advanced.open ? 0.5 : 0.3)
                Text {
                    id: advLabel
                    anchors.centerIn: parent
                    text: (advanced.open ? "▾  Ocultar avanzado" : "▸  Avanzado")
                          + " · loop-back y matriz completa (incluye el audio del PC)"
                    color: Theme.foreground
                    font.family: Theme.font
                    font.pixelSize: Theme.caption
                    font.bold: true
                }
                MouseArea {
                    id: advMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: advanced.toggle()
                }
            }

            Column {
                visible: advanced.open
                spacing: 22
            // ---- loop-back ----
            Column {
                spacing: 8
                SectionTitle { text: "LOOP-BACK · LO QUE LLEGA A LA CAPTURA 5-6" }
                Text {
                    text: "Solo para programas que graban desde una entrada de la EVO (OBS, etc.). Si usas la Mezcla como micrófono, déjalo en PC 5-6."
                    color: Theme.dim
                    font.family: Theme.font
                    font.pixelSize: Theme.caption
                }
                Row {
                    spacing: 8
                    Repeater {
                        model: page.loopbackOptions
                        Rectangle {
                            required property var modelData
                            readonly property bool current: page.hw.loopback === modelData.name
                            readonly property bool chosen: page.pendingLoopback === modelData.name
                            width: 200
                            height: 52
                            radius: Theme.radius
                            color: chosen ? Theme.alpha(Theme.accent, 0.22)
                                 : current && page.pendingLoopback === "" ? Theme.alpha(Theme.foreground, 0.12)
                                 : optMouse.containsMouse ? Theme.alpha(Theme.foreground, 0.07) : "transparent"
                            border.width: 1
                            border.color: chosen ? Theme.accent : Theme.alpha(Theme.foreground, current ? 0.5 : 0.2)
                            Column {
                                anchors.centerIn: parent
                                spacing: 2
                                Text {
                                    anchors.horizontalCenter: parent.horizontalCenter
                                    text: (parent.parent.current ? "󰄬 " : "") + modelData.label
                                    color: Theme.foreground
                                    font.family: Theme.font
                                    font.pixelSize: Theme.body
                                    font.bold: parent.parent.current || parent.parent.chosen
                                }
                                Text {
                                    anchors.horizontalCenter: parent.horizontalCenter
                                    width: 188
                                    horizontalAlignment: Text.AlignHCenter
                                    elide: Text.ElideRight
                                    text: modelData.detail
                                    color: Theme.dim
                                    font.family: Theme.font
                                    font.pixelSize: Theme.caption
                                }
                            }
                            MouseArea {
                                id: optMouse
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                enabled: !page.hw.busy
                                onClicked: mixer.hwSetLoopback(modelData.name)
                            }
                        }
                    }
                }
            }

            // ---- internal monitor mix ----
            Column {
                spacing: 8
                SectionTitle { text: "MATRIZ COMPLETA · dB por entrada y salida (izquierda del todo = apagado)" }
                Grid {
                    columns: page.outputs.length + 1
                    columnSpacing: 14
                    rowSpacing: 6
                    verticalItemAlignment: Grid.AlignVCenter

                    Item { width: 60; height: 1 }
                    Repeater {
                        model: page.outputs
                        SectionTitle { required property var modelData; text: modelData; width: 170 }
                    }

                    Repeater {
                        model: page.rows.length * (page.outputs.length + 1)
                        Item {
                            id: cell
                            required property int index
                            readonly property int row: Math.floor(index / (page.outputs.length + 1))
                            readonly property int col: index % (page.outputs.length + 1) - 1
                            readonly property var db: col >= 0 ? page.cellValue(row, col) : null
                            readonly property bool isPending: col >= 0 && page.pending[row + "," + col] !== undefined
                            width: col < 0 ? 60 : 170
                            height: 24

                            Text {
                                visible: cell.col < 0
                                anchors.verticalCenter: parent.verticalCenter
                                text: page.rows[cell.row]
                                color: Theme.foreground
                                font.family: Theme.font
                                font.pixelSize: Theme.body
                                font.bold: true
                            }
                            Row {
                                visible: cell.col >= 0
                                anchors.verticalCenter: parent.verticalCenter
                                spacing: 8
                                PixelSlider {
                                    width: 120
                                    enabled: !page.hw.busy && cell.db !== null
                                    minimum: page.offPosition
                                    maximum: 0
                                    step: 1
                                    value: cell.db === null ? page.offPosition : Math.max(page.offPosition, cell.db)
                                    onMoved: function(v) {
                                        mixer.hwSetCell(cell.row, cell.col, v <= page.offPosition ? -128 : v)
                                    }
                                }
                                Text {
                                    width: 40
                                    anchors.verticalCenter: parent.verticalCenter
                                    text: F.hwDb(cell.db)
                                    color: cell.isPending ? Theme.accent : Theme.foreground
                                    font.family: Theme.font
                                    font.pixelSize: Theme.caption
                                    font.bold: cell.isPending
                                }
                            }
                        }
                    }
                }
            }
            }
        }
    }
}
