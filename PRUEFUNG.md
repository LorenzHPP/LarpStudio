# Prüfumfang · 11.10.2026 · Larp Studio 1.4

Version 1.4 zusätzlich geprüft:

- Oberfläche, Dialoge, Status-/Fehlermeldungen und Einrichtungsfenster auf
  Englisch umgestellt. Suchanfragen verwenden Englisch als bevorzugte Sprache.
- Glass-Panels schweben über der gesamten Karte; Punkte und Routen werden
  neben der Seitenleiste eingerahmt. Sichtbarkeit geladener Routenpunkte geprüft.
- Echte OSM-Kartenansicht in Dark und Light visuell geprüft; Screenshots
  mit öffentlichen Beispielorten in docs/location-glass.png und docs/artwork-studio.png.
- 38 Backend-Tests sowie Bedienprüfungen für Pin, Suche, Favoriten, Punktlöschung,
  Routenplanung, Fahrprofil, Pause/Beenden, Bibliothek und PNG-Export bestanden.
- Fenstergrößen 1024 × 700, 1366 × 768 und 1920 × 1080 geprüft.
- Windows-EXE mit englischer Oberfläche gebaut; verpackte Geräte-CLI und
  natives WebView2-Fenster bestanden ihre Starttests auf GitHubs Windows-Runner.
- Kein neues Hardware-Ergebnis: iOS 27.2 und Snapchat bleiben ungetestet.

Ausgeführt in einer Linux-Umgebung ohne angeschlossenes iPhone:

- Larp Studio 1.3: Kartenbild-Vorlagen, Texte, Farben, Bildimport, Zoom und
  Ausschnittverschiebung im Browser geprüft. Exportierte PNG-Datei exakt
  1536 × 969 Pixel; Vorschau-Rahmen nicht enthalten. Nativer Export über
  Speicher-Dialog mit Testdaten sowie Abbruch ohne Schreibzugriff geprüft.
- Routen speichern, nach Neuladen laden, löschen und neu planen geprüft.
  Namen werden als Text dargestellt. Native Bibliothek bleibt in separater
  Datei nach Programmneustart erhalten; ungültige Koordinaten überschreiben
  keine gespeicherten Daten. Keine Gerätesitzung durch Enter im Designstudio.
- Neues Studio bei 1024 × 700 und 1366 × 768 ohne horizontales Überlaufen.
  Reproduzierbarer UI-Test: tools/check_studio.py; benötigt Playwright.

- Fahrprofil im Browser geprüft: Python/JavaScript liefern dieselben
  Positionen, Geschwindigkeiten und Zeiten. Automatik ist voreingestellt,
  ein altes manuelles Tempo von 160 km/h beeinflusst sie nicht. Pause,
  Fortsetzen, Endpunkt, Restzeit, Datenverlust, explizites festes Tempo und
  Übergabe des Profils über die native Bridge mit Testdaten geprüft.
- Kartenrenderer korrigiert: Symbolgrößen gelten nicht mehr für das
  Leaflet-Routen-SVG. Dadurch wird die Route in voller Kartengröße gezeichnet.
  Größe und sichtbare Linie im Browser geprüft.
- Monochrome-Oberfläche: Bestehende Browser-Bedienprüfungen und gezielte
  Punktlöschungsprüfung erneut erfolgreich. Browser-Tests verwenden lokale
  Testdaten für Kartenkacheln, Suche, Routen und die Geräte-Bridge.
- Neue lokale SVG-Symbole und Inter-Schrift laden korrekt. Dunkel/Hell
  wechselt die Darstellung ohne neue Kartenkacheln anzufragen. Beide
  Ansichten sind monochrom; die Routenlinie wechselt zwischen Weiß und
  Schwarz, passend zum Kartenhintergrund. Alle vier Modi verwenden das
  passende Symbol in der laufenden Kartenansicht.
- Bedienelemente bei 1024 × 700, 1366 × 768 und 1920 × 1080 geprüft.
  Eine echte OSM-Kartenansicht wurde visuell geprüft; keine JavaScript-Fehler.
- 38 Python-Tests erfolgreich, einschließlich elf neuer Fahrprofil-Prüfungen:
  Stadt/Autobahn/Stadt, Begrenzung pro Abschnitt, Bremsen vor langsamen
  Straßen, Beschleunigung, Kurven, passende Fahrzeit, Endpunkt halten,
  Wiederholung ohne Teleport, doppelte Punkte, kurze Routen, fehlende Daten,
  Profilvalidierung, Maps-Anbindung und automatische Sitzung mit Pause.
- Ein echtes FOSSGIS-Straßenprofil um Heimenkirch für eine Route mit mehreren
  Zwischenpunkten wurde verarbeitet: 565 Geometriepunkte, 2135 Fahrprofil-
  Stützpunkte, geschätzte Dauer rund 26 Minuten. Keine zusätzlichen Dienste.
- Bestehende 21 Python-Tests erneut erfolgreich: Koordinatenprüfung, Entfernungen,
  Routeninterpolation mit doppelten Punkten und über die Datumsgrenze,
  Verhinderung falscher Gerätezuordnung, fehlgeschlagener Löschversuch und
  erneutes Zurücksetzen, Löschen über eine neue Verbindung bei Sitzungsfehler,
  gespeicherte Orte, Bridge-Fehler und passende Fußweg-/Straßenprofile.
- WLAN ergänzt: lokale USB-Vorbereitung, Wiederverbinden nach App-Neustart,
  USB-unabhängige Sitzung und Löschversuch, USB-Wiederherstellung nach
  WLAN-Verlust. Adaptertests prüfen die genaue Geräteauswahl, Schließen
  unbenutzter Verbindungen, Ablehnung einer falschen Gerätekennung und
  fehlender WLAN-Geräte ohne einen verdeckten USB-Fallback.
- Asynchrone Sitzung mit simuliertem Transport: Während pausierter Bewegung
  laufen Hintergrundaufgaben weiter, derselbe Punkt wird wiederholt gesendet
  und am Ende wird gelöscht. Kein Test an echter Apple-Hardware.
- Browser-Bedienung mit Chromium: Pin/Koordinaten, Ortsuche, lokale Favoriten,
  sicher angezeigte Suchtexte, Routenpunkte, Routenplanung, Modi, Tempo,
  Wiederholung, Start/Pause/Fortsetzen/Beenden, Weltansicht, Hilfe und Protokoll.
  Prüfung des kleinsten Fensterformats 1024 × 700 ohne horizontales Überlaufen
  und mit erreichbaren Start-/Zurücksetzen-Schaltflächen.
- WLAN-Schaltflächen, Einrichtungsdialog, Start erst nach erfolgreicher
  Verbindungsprüfung und gesperrter Transportwechsel während einer Sitzung
  mit Testdaten geprüft.
- Einzelne Routenpunkte entfernen: erster, mittlerer und letzter Punkt
  über Listenknopf oder Kartenpopup; anschließende Nummerierung und neue
  Planung geprüft. Ein veraltetes Planungsergebnis wird auch verworfen,
  wenn während der Anfrage ein Punkt entfernt wird. Entfernen ist während
  Bewegung und Pause gesperrt und nach Beenden wieder möglich.
- Native-JavaScript-Bridge und Fehlermeldungen mit Testdaten geprüft.
  Browser-Bedientests verwendeten lokale Kachel-/Such-/Routen-Testdaten.
- Echte öffentliche Photon- und FOSSGIS-Dienste separat geprüft: Fußweg- und
  Straßenroute um Heimenkirch erfolgreich berechnet (etwa 805 m bzw. 538 m).
  Eine tatsächliche OSM-Kartenansicht wurde visuell geprüft.
- JavaScript-Syntax und Python-Importe geprüft. Geräte-CLI über die gepinnte
  pymobiledevice3-Version ausgeführt: Hilfe erfolgreich über Datei-IPC empfangen.

Zusätzlich auf GitHubs Windows-Runner geprüft:

- Eigenständige EXE mit Python 3.13 und PyInstaller 6.22.3 gebaut.
- Gebündelte Geräte-CLI mit ihren DLLs und Paketinformationen erfolgreich
  gestartet; Hilfe per Datei-IPC empfangen.
- Native WebView2-Oberfläche geöffnet: Dokumenttitel, Kartenbild-Canvas
  (1536 × 969) und Geräte-/Routen-/Export-API erfolgreich geladen.
  Das interne Fensterobjekt wird nicht als JavaScript-API veröffentlicht.
- Offline-Tests und JavaScript-Syntax auf Windows und Linux erfolgreich.
- [Windows-Build mit Starttests](https://github.com/LorenzHPP/LarpStudio/actions/runs/38165709646).

Noch nicht geprüft:

- Visuelle Darstellung und echter Speicherdialog auf deinem Windows-PC.
- USB-Tunnel, Developer Disk Image und Standortbefehle an einem echten iPhone.
- WLAN-Paarung, Gerätediscovery und Kabel-unabhängiger Betrieb auf Windows
  mit iOS 27.2; Router, Firewall und Sperrzustand können das Verhalten ändern.
- Dauerbetrieb über zehn Minuten und das reale Zurücksetzen auf iOS 27.2.
- Anzeige und Aktualisierungsverhalten in Snapchat.

Diese Punkte lassen sich hier ohne deinen Windows-PC und dein iPhone nicht
abschließend prüfen. Der erste praktische Test sollte in Apple Karten erfolgen.
