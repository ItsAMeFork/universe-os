/* Diavoorstelling tijdens het installeren van Universe OS (Calamares slideshow API 2). */
import QtQuick 2.0
import calamares.slideshow 1.0

Presentation {
    id: presentation

    function nextSlide() { presentation.goToNextSlide(); }

    Timer {
        id: advanceTimer
        interval: 8000
        running: presentation.activatedInCalamares
        repeat: true
        onTriggered: nextSlide()
    }

    Rectangle { anchors.fill: parent; color: "#050815"; z: -1 }

    Slide {
        Text {
            anchors.centerIn: parent
            width: parent.width * 0.8
            color: "#e2e6fa"; font.pixelSize: 22; wrapMode: Text.WordWrap; horizontalAlignment: Text.AlignHCenter
            text: "Welkom in Universe OS.\n\nNa het inloggen kom je direct in de ruimtewereld: elke planeet opent een deel van je computer."
        }
    }
    Slide {
        Text {
            anchors.centerIn: parent
            width: parent.width * 0.8
            color: "#e2e6fa"; font.pixelSize: 22; wrapMode: Text.WordWrap; horizontalAlignment: Text.AlignHCenter
            text: "Windows-toets: zoeken en je geopende programma's.\nWindows + D: terug naar de ruimtewereld.\nWindows + A: het bedieningspaneel."
        }
    }
    Slide {
        Text {
            anchors.centerIn: parent
            width: parent.width * 0.8
            color: "#e2e6fa"; font.pixelSize: 22; wrapMode: Text.WordWrap; horizontalAlignment: Text.AlignHCenter
            text: "Programma's installeer je in de Softwarewinkel.\nWindows-programma's (.exe en .msi) kunnen via Wine draaien, maar niet elk programma werkt."
        }
    }

    function onActivate() { presentation.currentSlide = 0; }
    function onLeave() { }
}
