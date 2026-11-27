import QtQuick
import "."

// A labelled group of strips side by side.
Column {
    id: group
    property string title: ""
    property string tip: ""
    default property alias strips: row.data
    spacing: 10

    Text {
        text: group.title
        color: Theme.dim
        font.family: Theme.font
        font.pixelSize: Theme.caption
        font.letterSpacing: 1.4
        font.bold: true
        HoverHandler { id: titleHover }
        Tip { visible: titleHover.hovered && group.tip !== ""; text: group.tip }
    }
    Row {
        id: row
        spacing: 6
    }
}
