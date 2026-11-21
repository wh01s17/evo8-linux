pragma Singleton
import QtQuick

// Colours and sizes for the whole window. Dark console look, pixel accents.
QtObject {
    readonly property color background: "#12171a"
    readonly property color surface: "#182024"
    readonly property color foreground: "#d6dfd2"
    readonly property color dim: "#7f8c82"
    readonly property color accent: "#84c959"
    readonly property color warn: "#e8b53f"
    readonly property color urgent: "#ff6b66"
    readonly property string font: "JetBrainsMono Nerd Font"
    readonly property int caption: 11
    readonly property int body: 13
    readonly property int title: 16
    readonly property int radius: 3
    readonly property real stripWidth: 96
    readonly property real faderHeight: 220

    function alpha(c, a) { return Qt.rgba(c.r, c.g, c.b, a) }
}
