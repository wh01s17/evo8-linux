import QtQuick
import "."

// A labelled group of strips side by side.
Column {
    id: group
    property string title: ""
    default property alias strips: row.data
    spacing: 10

    Text {
        text: group.title
        color: Theme.dim
        font.family: Theme.font
        font.pixelSize: Theme.caption
        font.letterSpacing: 1.4
        font.bold: true
    }
    Row {
        id: row
        spacing: 6
    }
}
