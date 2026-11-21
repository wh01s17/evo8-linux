import QtQuick
import QtQuick.Controls
import "."

// Tooltip in the window's style.
ToolTip {
    id: tip
    delay: 400
    contentItem: Text {
        text: tip.text
        color: Theme.foreground
        font.family: Theme.font
        font.pixelSize: Theme.caption
    }
    background: Rectangle {
        color: Theme.surface
        border.color: Theme.alpha(Theme.foreground, 0.3)
        radius: Theme.radius
    }
}
