import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "."

ApplicationWindow {
    id: window
    title: "Mezclador EVO 8"
    width: 1640
    height: 640
    minimumWidth: 720
    minimumHeight: 520
    visible: true
    color: Theme.background

    readonly property var m: mixer.model
    property int page: 0

    Shortcut { sequence: "Escape"; onActivated: window.close() }

    // The tabs, one per part of the project: the PC's sound, the optional
    // virtual microphone, the interface's own hardware, and about.
    readonly property bool mezclaOn: m.mezclaService === "on" || m.mezclaService === "legacy"

    component Tab: Text {
        id: tab
        property int index: 0
        property bool lit: false    // a small square: this part is on
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
        Rectangle {
            visible: tab.lit
            anchors.left: parent.right
            anchors.leftMargin: 6
            anchors.verticalCenter: parent.verticalCenter
            width: 6
            height: 6
            color: Theme.accent
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

        // First line: the app's name and version, plus notices.
        RowLayout {
            Layout.fillWidth: true
            spacing: 10
            Image {
                source: "../../data/evo8-mixer.svg"
                Layout.preferredWidth: 22
                Layout.preferredHeight: 22
                sourceSize: Qt.size(44, 44)
                smooth: true
            }
            Text {
                text: "Mezclador EVO 8"
                color: Theme.foreground
                font.family: Theme.font
                font.pixelSize: Theme.title
                font.bold: true
            }
            Text {
                Layout.alignment: Qt.AlignBaseline
                text: mixer.about.version ? "v" + mixer.about.version : ""
                color: Theme.accent
                font.family: Theme.font
                font.pixelSize: Theme.caption
                font.bold: true
            }
            Item { Layout.fillWidth: true }
            Text {
                text: window.m.notice || ""
                visible: text !== "" && !(window.m.message)
                color: Theme.accent
                font.family: Theme.font
                font.pixelSize: Theme.caption
                font.bold: true
                elide: Text.ElideLeft
                Layout.maximumWidth: 900
            }
            Text {
                text: window.m.message || ""
                color: Theme.urgent
                font.family: Theme.font
                font.pixelSize: Theme.caption
                elide: Text.ElideLeft
                Layout.maximumWidth: 600
            }
        }

        // Second line: the tabs.
        Row {
            Layout.fillWidth: true
            Layout.bottomMargin: 4
            spacing: 28
            Tab { index: 0; text: "SONIDO DEL PC" }
            Tab { index: 1; text: "MICRÓFONO VIRTUAL"; lit: window.mezclaOn }
            Tab { index: 2; text: "EVO 8" }
            Tab { index: 3; text: "ACERCA DE" }
        }

        // Give the scroll views the available space directly. Their content
        // sizes depend on that space and must stay out of layout negotiation.
        //
        // Pages are switched with opacity + enabled, not visible: toggling
        // visible tells every one of a page's ~2000 items, and each Row or
        // Column of fader/meter cells lays itself out again per child
        // (~0.4 s on the console). A page at opacity 0 is skipped by the
        // renderer, and a disabled one gets no input.
        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true

            SystemPage {
                anchors.fill: parent
                opacity: window.page === 0 ? 1 : 0
                enabled: window.page === 0
            }

            MezclaPage {
                anchors.fill: parent
                opacity: window.page === 1 ? 1 : 0
                enabled: window.page === 1
            }

            HardwarePage {
                anchors.fill: parent
                opacity: window.page === 2 ? 1 : 0
                enabled: window.page === 2
            }

            AboutPage {
                anchors.fill: parent
                opacity: window.page === 3 ? 1 : 0
                enabled: window.page === 3
            }
        }
    }
}
