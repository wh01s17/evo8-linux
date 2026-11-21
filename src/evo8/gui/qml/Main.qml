import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "."

ApplicationWindow {
    id: window
    title: "Mezclador"
    width: 1640
    height: 640
    minimumWidth: 720
    minimumHeight: 520
    visible: true
    color: Theme.background

    readonly property var m: mixer.model
    property int page: 0

    Shortcut { sequence: "Escape"; onActivated: window.close() }

    component Tab: Text {
        id: tab
        property int index: 0
        text: ""
        color: window.page === index ? Theme.foreground : Theme.dim
        font.family: Theme.font
        font.pixelSize: Theme.body
        font.bold: window.page === index
        font.letterSpacing: 1.2
        Rectangle {
            anchors.top: parent.bottom
            anchors.topMargin: 4
            width: parent.width
            height: 2
            color: Theme.accent
            visible: window.page === tab.index
        }
        MouseArea {
            anchors.fill: parent
            anchors.margins: -6
            cursorShape: Qt.PointingHandCursor
            onClicked: window.page = tab.index
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 18
        spacing: 14

        RowLayout {
            Layout.fillWidth: true
            spacing: 28
            Text {
                text: "Mezclador"
                color: Theme.foreground
                font.family: Theme.font
                font.pixelSize: Theme.title
                font.bold: true
            }
            Tab { index: 0; text: "CONSOLA" }
            Tab { index: 1; text: "EVO 8" }
            Item { Layout.fillWidth: true }
            Text {
                text: window.m.message || ""
                color: Theme.urgent
                font.family: Theme.font
                font.pixelSize: Theme.caption
                elide: Text.ElideLeft
                Layout.maximumWidth: 600
            }
        }

        Text {
            Layout.fillWidth: true
            visible: window.page === 0
            text: window.m.gains !== null
                ? "PRE  preamp de la EVO   ·   FADER  cuánto entra a la Mezcla   ·   SINC  alinea lo que tocas sobre Compartido   ·   󰑐  volver al estándar"
                : "No se encontró la Mezcla (config/pipewire/pipewire.conf.d/20-mezcla.conf)"
            color: window.m.gains !== null ? Theme.dim : Theme.urgent
            font.family: Theme.font
            font.pixelSize: Theme.caption
            elide: Text.ElideRight
        }

        StackLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: window.page
            ConsolePage {}
            HardwarePage {}
        }
    }
}
