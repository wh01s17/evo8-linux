import QtQuick
import "."

// The apps playing now, each with a switch: on sends it to Compartido, so it
// is heard and also goes into the Mezcla. Their volume lives in SONIDO DEL PC.
Item {
    id: root
    property var streams: []
    property real unit: Theme.stripWidth
    width: unit * 1.9

    Rectangle {
        anchors.fill: parent
        radius: Theme.radius
        color: Theme.alpha(Theme.foreground, 0.03)
    }

    Column {
        id: list
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.margins: 8
        spacing: 8

        Text {
            width: parent.width
            wrapMode: Text.WordWrap
            text: root.streams.length > 0
                ? "Encendida, la app suena por Compartido: la oyes y entra a la Mezcla."
                : "Ninguna app está sonando. Las que suenen aparecen aquí."
            color: Theme.dim
            font.family: Theme.font
            font.pixelSize: Theme.caption
        }

        Repeater {
            model: root.streams
            Item {
                required property var modelData
                width: list.width
                height: Math.max(label.implicitHeight, toggle.height)

                Text {
                    id: label
                    anchors.left: parent.left
                    anchors.right: toggle.left
                    anchors.rightMargin: 8
                    anchors.verticalCenter: parent.verticalCenter
                    text: modelData.label
                    color: modelData.shared ? Theme.foreground : Theme.dim
                    font.family: Theme.font
                    font.pixelSize: Theme.caption
                    font.bold: modelData.shared
                    elide: Text.ElideRight
                }
                Toggle {
                    id: toggle
                    anchors.right: parent.right
                    anchors.verticalCenter: parent.verticalCenter
                    checked: modelData.shared
                    tip: modelData.shared ? "Devolver a la salida" : "Enviar a Compartido"
                    onToggled: mixer.toggleStreamShared(modelData.index)
                }
            }
        }
    }
}
