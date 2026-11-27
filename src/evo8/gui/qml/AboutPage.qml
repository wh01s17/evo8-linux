import QtQuick
import QtQuick.Controls
import "."

// "Acerca de": what this is, where it comes from, and the facts a bug report
// needs (version, EVO firmware, how it is installed). Read from files only.
ScrollView {
    id: page
    clip: true
    contentWidth: availableWidth
    ScrollBar.vertical.policy: ScrollBar.AsNeeded

    readonly property var a: mixer.about
    readonly property var dev: a.device || ({})

    onEnabledChanged: if (enabled) mixer.refreshAbout()

    component SectionTitle: Text {
        color: Theme.dim
        font.family: Theme.font
        font.pixelSize: Theme.caption
        font.letterSpacing: 1.4
        font.bold: true
    }

    // One "key  value" line.
    component Field: Row {
        id: field
        property string k: ""
        property string v: ""
        property color tone: Theme.foreground
        width: parent ? parent.width : 0
        spacing: 12
        Text {
            width: 150
            text: field.k
            color: Theme.dim
            font.family: Theme.font
            font.pixelSize: Theme.caption
        }
        Text {
            width: field.width - 162
            text: field.v || "—"
            color: field.tone
            font.family: Theme.font
            font.pixelSize: Theme.caption
            wrapMode: Text.WrapAnywhere
        }
    }

    component Link: Text {
        id: link
        property string url: ""
        color: Theme.accent
        font.family: Theme.font
        font.pixelSize: Theme.body
        font.underline: linkMouse.containsMouse
        MouseArea {
            id: linkMouse
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: Qt.openUrlExternally(link.url)
        }
    }

    component Card: Rectangle {
        default property alias content: inner.data
        width: parent ? parent.width : 0
        height: inner.implicitHeight + 28
        radius: Theme.radius
        color: Theme.alpha(Theme.foreground, 0.03)
        Column {
            id: inner
            x: 14
            y: 14
            width: parent.width - 28
            spacing: 8
        }
    }

    Row {
        id: columns
        width: page.availableWidth
        spacing: 28
        readonly property real colWidth: Math.min(640, (width - spacing) / 2)

        // ---- what it is ----
        Column {
            width: columns.colWidth
            spacing: 18

            Row {
                width: parent.width
                spacing: 18
                Image {
                    source: "../../data/evo8-mixer.svg"
                    width: 72
                    height: 72
                    sourceSize: Qt.size(144, 144)
                    smooth: true
                }
            Column {
                width: parent.width - 90
                spacing: 6
                Row {
                    spacing: 12
                    Text {
                        text: page.a.app || ""
                        color: Theme.foreground
                        font.family: Theme.font
                        font.pixelSize: 22
                        font.bold: true
                    }
                    Text {
                        anchors.baseline: parent.children[0].baseline
                        text: "v" + (page.a.version || "")
                        color: Theme.accent
                        font.family: Theme.font
                        font.pixelSize: Theme.body
                        font.bold: true
                    }
                }
                Text {
                    width: parent.width
                    text: page.a.description || ""
                    color: Theme.foreground
                    font.family: Theme.font
                    font.pixelSize: Theme.body
                    wrapMode: Text.WordWrap
                    lineHeight: 1.2
                }
            }
            }

            Column {
                width: parent.width
                spacing: 8
                SectionTitle { text: "ENLACES" }
                Link { text: "󰊤  Código y documentación"; url: page.a.repo || "" }
                Link { text: "󰃤  Reportar un problema"; url: page.a.issues || "" }
            }

            Column {
                width: parent.width
                spacing: 6
                SectionTitle { text: "LICENCIA" }
                Text {
                    width: parent.width
                    text: "Licencia " + (page.a.license || "") + " · hecho por " + (page.a.author || "")
                    color: Theme.foreground
                    font.family: Theme.font
                    font.pixelSize: Theme.caption
                }
                Text {
                    width: parent.width
                    text: (page.a.disclaimer || "") + " EVO es una marca de Audient."
                    color: Theme.dim
                    font.family: Theme.font
                    font.pixelSize: Theme.caption
                    wrapMode: Text.WordWrap
                }
            }
        }

        // ---- this machine ----
        Column {
            width: columns.colWidth
            spacing: 18

            Column {
                width: parent.width
                spacing: 8
                SectionTitle { text: "EVO 8" }
                Card {
                    Field {
                        k: "Estado"
                        v: page.dev.connected ? "conectada" : "no conectada"
                        tone: page.dev.connected ? Theme.accent : Theme.warn
                    }
                    Field {
                        visible: !!page.dev.connected
                        k: "Firmware"
                        v: (page.dev.firmware || "") + (page.dev.tested ? " (probado)"
                           : " · se probó con " + (page.a.testedFirmware || "") + ", el control por USB podría fallar")
                        tone: page.dev.tested ? Theme.foreground : Theme.warn
                    }
                    Field { visible: !!page.dev.connected; k: "USB"; v: page.dev.speed || "" }
                }
            }

            Column {
                width: parent.width
                spacing: 8
                SectionTitle { text: "INSTALACIÓN" }
                Card {
                    Field { k: "Tipo"; v: page.a.install || "" }
                    Field {
                        k: "Config Mezcla"
                        v: page.a.pipewireConfig || "no encontrada: el micrófono virtual no se puede encender"
                        tone: page.a.pipewireConfig ? Theme.foreground : Theme.urgent
                    }
                    Field {
                        k: "Regla udev"
                        v: page.a.udevRule || "no instalada: sin control por USB"
                        tone: page.a.udevRule ? Theme.foreground : Theme.warn
                    }
                    Field { k: "Ajustes guardados"; v: page.a.stateFile || "" }
                }
            }

            Column {
                width: parent.width
                spacing: 8
                SectionTitle { text: "VERSIONES" }
                Card {
                    Repeater {
                        model: Object.keys(page.a.versions || {})
                        Field {
                            required property string modelData
                            k: modelData
                            v: page.a.versions[modelData]
                        }
                    }
                    Field { k: "Sistema"; v: page.a.platform || "" }
                }
            }

            Rectangle {
                id: copy
                property bool done: false
                width: copyLabel.implicitWidth + 24
                height: copyLabel.implicitHeight + 12
                radius: Theme.radius
                color: copyMouse.containsMouse ? Theme.alpha(Theme.foreground, 0.1) : "transparent"
                border.width: 1
                border.color: copy.done ? Theme.accent : Theme.alpha(Theme.foreground, 0.4)
                Text {
                    id: copyLabel
                    anchors.centerIn: parent
                    text: copy.done ? "󰄬  Copiado" : "󰆏  Copiar para reportar un problema"
                    color: copy.done ? Theme.accent : Theme.foreground
                    font.family: Theme.font
                    font.pixelSize: Theme.caption
                }
                MouseArea {
                    id: copyMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: { mixer.copyAbout(); copy.done = true; copyReset.restart() }
                }
                Timer { id: copyReset; interval: 2000; onTriggered: copy.done = false }
            }
        }
    }
}
