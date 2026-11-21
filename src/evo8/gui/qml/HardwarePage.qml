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
        signal clicked()
        width: label.implicitWidth + 24
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

    Column {
        width: page.availableWidth
        spacing: 22
        padding: 4

        // ---- actions ----
        Column {
            spacing: 8
            Text {
                text: "Estos ajustes se guardan en la EVO. Leerlos o aplicarlos corta el audio un instante."
                color: Theme.dim
                font.family: Theme.font
                font.pixelSize: Theme.caption
            }
            Row {
                spacing: 10
                Button {
                    text: "Leer de la EVO"
                    enabled: !page.hw.busy
                    onClicked: mixer.hwRead()
                }
                Button {
                    text: "Aplicar a la EVO"
                    primary: true
                    enabled: !page.hw.busy && page.hasPending
                    onClicked: mixer.hwApply()
                }
                Button {
                    text: "Descartar cambios"
                    enabled: !page.hw.busy && page.hasPending
                    onClicked: mixer.hwDiscard()
                }
                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    text: page.hw.message
                        ? page.hw.message
                        : (page.hw.readAt ? "Último estado conocido: " + page.hw.readAt
                                          : "Aún no se ha leído la EVO.")
                    color: String(page.hw.message).indexOf("Error") === 0 ? Theme.urgent : Theme.foreground
                    font.family: Theme.font
                    font.pixelSize: Theme.caption
                }
            }
        }

        // ---- inputs: phantom and mute ----
        Column {
            spacing: 8
            SectionTitle { text: "ENTRADAS · 48 V Y SILENCIO EN LA EVO" }
            Row {
                spacing: 14
                Repeater {
                    model: 4
                    Rectangle {
                        required property int index
                        width: 150
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
                                        width: 64
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

        // ---- what the headphones hear directly ----
        // One level per input and headphone pair: it sets both sides (L and R)
        // of that pair in the internal mix, so a mono input sits centred.
        Column {
            spacing: 8
            SectionTitle { text: "LO QUE OYES DIRECTO EN LOS AUDÍFONOS · SIN PASAR POR EL PC, SIN LATENCIA" }
            Row {
                spacing: 10
                // Presets only stage changes; nothing reaches the EVO until "Aplicar".
                function preset(level) {
                    for (var i = 0; i < page.rows.length; i++)
                        for (var o = 0; o < page.outputs.length; o++) {
                            var db = level(i, o)
                            if (db !== null) mixer.hwSetCell(i, o, db)
                        }
                }
                Button {
                    text: "Como de fábrica"
                    enabled: !page.hw.busy && !!page.hw.mix
                    onClicked: parent.preset(function(i, o) { return 0 })
                }
                Button {
                    text: "No oír ninguna entrada"
                    enabled: !page.hw.busy && !!page.hw.mix
                    onClicked: parent.preset(function(i, o) { return i < 4 ? -128 : null })
                }
                Button {
                    text: "Oír solo la entrada 1"
                    enabled: !page.hw.busy && !!page.hw.mix
                    onClicked: parent.preset(function(i, o) { return i === 0 ? 0 : (i < 4 ? -128 : null) })
                }
                Button {
                    text: "Oír entradas 1 y 2"
                    enabled: !page.hw.busy && !!page.hw.mix
                    onClicked: parent.preset(function(i, o) { return i < 2 ? 0 : (i < 4 ? -128 : null) })
                }
            }

            Grid {
                columns: 3
                columnSpacing: 24
                rowSpacing: 8
                verticalItemAlignment: Grid.AlignVCenter

                Item { width: 60; height: 1 }
                SectionTitle { text: "AUDÍFONOS 1 (salidas 1-2)"; width: 230 }
                SectionTitle { text: "AUDÍFONOS 2 (salidas 3-4)"; width: 230 }

                Repeater {
                    model: 4 * 3
                    Item {
                        id: pairCell
                        required property int index
                        readonly property int row: Math.floor(index / 3)
                        readonly property int pair: index % 3 - 1          // -1 = row label
                        // The louder side of the pair, so an uneven pair never reads quieter.
                        readonly property var db: {
                            if (pair < 0) return null
                            var l = page.cellValue(row, pair * 2), r = page.cellValue(row, pair * 2 + 1)
                            if (l === null || r === null) return null
                            return Math.max(l, r)
                        }
                        readonly property bool isPending: pair >= 0
                            && (page.pending[row + "," + (pair * 2)] !== undefined
                                || page.pending[row + "," + (pair * 2 + 1)] !== undefined)
                        width: pair < 0 ? 60 : 230
                        height: 26

                        Text {
                            visible: pairCell.pair < 0
                            anchors.verticalCenter: parent.verticalCenter
                            text: "IN " + (pairCell.row + 1)
                            color: Theme.foreground
                            font.family: Theme.font
                            font.pixelSize: Theme.body
                            font.bold: true
                        }
                        Row {
                            visible: pairCell.pair >= 0
                            anchors.verticalCenter: parent.verticalCenter
                            spacing: 10
                            PixelSlider {
                                width: 160
                                enabled: !page.hw.busy && pairCell.db !== null
                                minimum: page.offPosition
                                maximum: 0
                                step: 1
                                value: pairCell.db === null ? page.offPosition : Math.max(page.offPosition, pairCell.db)
                                onMoved: function(v) {
                                    var db = v <= page.offPosition ? -128 : v
                                    mixer.hwSetCell(pairCell.row, pairCell.pair * 2, db)
                                    mixer.hwSetCell(pairCell.row, pairCell.pair * 2 + 1, db)
                                }
                            }
                            Text {
                                width: 60
                                anchors.verticalCenter: parent.verticalCenter
                                text: pairCell.db === null ? "?" : (pairCell.db <= -127.5 ? "apagado" : Math.round(pairCell.db) + " dB")
                                color: pairCell.isPending ? Theme.accent : Theme.foreground
                                font.family: Theme.font
                                font.pixelSize: Theme.caption
                                font.bold: pairCell.isPending
                            }
                        }
                    }
                }
            }
            Text {
                text: page.hw.mix ? "Mueve la barra a la izquierda del todo para dejar de oír esa entrada. Los cambios llegan a la EVO al pulsar «Aplicar a la EVO»."
                                  : "Pulsa «Leer de la EVO» para ver y cambiar estos valores."
                color: Theme.dim
                font.family: Theme.font
                font.pixelSize: Theme.caption
            }
        }

        // ---- advanced: loop-back and the full matrix ----
        Column {
            id: advanced
            property bool open: false
            spacing: 18

            Text {
                text: (advanced.open ? "▾ " : "▸ ") + "AVANZADO · loop-back y matriz completa (incluye el audio del PC)"
                color: Theme.dim
                font.family: Theme.font
                font.pixelSize: Theme.caption
                font.letterSpacing: 1.2
                font.bold: true
                MouseArea {
                    anchors.fill: parent
                    anchors.margins: -4
                    cursorShape: Qt.PointingHandCursor
                    onClicked: advanced.open = !advanced.open
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
                    text: "Solo para programas que graban desde una entrada de la EVO (OBS, etc.). Si usas la Mezcla en la llamada, déjalo en PC 5-6."
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
