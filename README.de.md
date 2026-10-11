# Larp Studio · 1.4

Version 1.4 verwendet eine englische Oberfläche und schwebende Glass-Panels
im Schwarz-Weiß-Theme. Die aktuelle englische Kurzanleitung steht in
**START-HERE.txt**. Diese deutsche Anleitung beschreibt die gleichen Funktionen;
einige ältere Schaltflächennamen sind hier noch auf Deutsch angegeben.

Ein persönliches Windows-Studio für Standortsimulation am eigenen iPhone,
gespeicherte Routen und selbst gestaltete Kartenbilder. Reduziertes
Schwarz-Weiß-Design, eigene Programmoberfläche, ohne Benutzerkonto in der App.

Repository: https://github.com/LorenzHPP/LarpStudio

Die öffentliche Version startet an einem öffentlichen Beispielort:
Brandenburger Tor, Berlin. Eigene Orte und WLAN-Gerätedaten bleiben lokal.

Die Oberfläche verwendet leicht transparente Flächen, schlichte Linien-Symbole
und eine schwebende Seitenleiste. Karte oben rechts zwischen Dark und Light wechseln;
beide Ansichten sind monochrom. Die Auswahl wird lokal gespeichert.
Schrift, Symbole und Windows-Icon sind lokal gebündelt. Alle bisherigen
Funktionen einschließlich einzelner Punktlöschung und des experimentellen
WLAN-Modus sind im vollständigen Paket enthalten. Neu: straßenabhängiges
Fahrtempo und eine dazu passende Fahrzeit statt eines konstanten Tempos.

## Starten

ZIP vollständig entpacken, alten Standort-Starter beenden und
**Start-Larp Studio.cmd** doppelklicken. Die erste Einrichtung lädt die Pakete aus
`requirements.txt` in `.venv`. Danach öffnet sich ein eigenes Programmfenster.
Die kurze Anleitung steht in **START-HIER.txt**.
Für die finale Version und das Aktualisieren einer bestehenden Installation:
**FINAL-START.txt**. Optional erstellt **Desktop-Verknuepfung.cmd** einen
Desktop-Link mit dem Larp Studio-Icon; den Programmordner danach nicht verschieben.

Voraussetzungen: Windows 10/11, reguläres Python 3.13 mit tkinter, Microsoft
Edge WebView2 Runtime und funktionierende Apple-USB-Treiber. Das iPhone muss
entsperrt sein, dem PC vertrauen und den Entwicklermodus aktiviert haben.
Die Geräteschnittstelle in dieser App setzt iOS 17.4 oder neuer voraus.
Das ist eine technische Mindestversion, keine Zusage für jede iOS-Version.

## Bedienung

- **Fester Punkt:** Karte anklicken, Pin ziehen, Ort suchen oder Koordinaten
  eingeben. Mit „Standort setzen“ starten.
- **Gehen / Joggen / Fahren:** Start und weitere Punkte auf der Karte setzen,
  „Route entlang Wegen planen“ wählen, Tempo einstellen und starten.
  Gehen und Joggen nutzen Fußwege; Fahren nutzt Straßen. Im Fahrmodus ist
  **Straßentempo** voreingestellt: Route planen und direkt starten.
- **Hin und zurück:** Am Routenende kehrt die Bewegung um. Ohne Wiederholung
  wird der Endpunkt weiter gehalten.
- **Pause:** Bewegung anhalten und den letzten Punkt weiter senden.
- **Beenden:** Bewegung stoppen und die Simulation in derselben Sitzung
  löschen. Bei einem Fehler versucht Larp Studio zusätzlich eine neue Verbindung.
- **Echten Standort wiederherstellen:** Erneuten Löschversuch starten.
- **Gespeicherte Orte:** Lokal in `.atlas-data.json`; keine Anmeldung.
- **Sitzungsprotokoll:** Verbindungsfehler und letzte Befehle nachlesen.

## Neu in Larp Studio

- **Kartenbilder:** Eigener Arbeitsbereich oben im Fenster. Drei Vorlagen,
  Titel, Unterzeile, Farben und eigene PNG/JPEG/WebP-Bilder. Ein Bild lässt
  sich zoomen und mit der Maus im Kartenrahmen verschieben. Export als
  PNG mit **1536 × 969 Pixeln**; der abgerundete Vorschaurahmen ist nicht
  Teil des Exports. Das Bild wird nicht hochgeladen.
- **Routenbibliothek:** Mindestens zwei Punkte wählen, „Route speichern“ und
  einen Namen vergeben. Bis zu 20 Routen laden oder löschen. Beim Laden
  wird die Strecke samt Tempo neu geplant; alte Abschnittsdaten werden
  nicht als aktuell übernommen. In der Desktop-App bleibt die Bibliothek
  in `.larp-routes.json` neben dem Programm, auch nach einem Neustart.
- **GitHub-Workflows:** Offline-Tests auf Windows und Linux bei jedem Push. Ein
  manueller Windows-Build unter **Actions → Windows app → Run workflow**
  erzeugt eine eigenständige EXE mit Dateien und zugehörigem Quellcode.
  Das Artefakt heißt **Larp-Studio-Windows** und bleibt 30 Tage verfügbar.

### Was der Wallet-Bereich kann

Er gestaltet **Bilder**, verändert noch keine vorhandene Apple-Pay-Karte
und erzeugt keine signierten `.pkpass`-Dateien. Das Erscheinungsbild einer
bestehenden Bankkarte lässt sich auf manchen iOS-Versionen mit externen
Werkzeugen wie [AirCard](https://github.com/Mak5er/AirCard) ändern. Laut dessen
README werden iOS 18.0–27.0.1 und **iOS 27.2 Beta 1–2** unterstützt;
**iOS 27.2 Beta 3 und neuer** sind für die verwendete Methode gepatcht.
Die bloße Angabe „27.2“ reicht deshalb nicht zur Kompatibilitätsprüfung.
Larp Studio führt diesen Eingriff nicht automatisch aus und enthält keinen
AirCard-Exploitcode. Bankdaten und Zahlungsfunktionen werden nicht bearbeitet.

Eigene Bonus-/Infokarten in Apple Wallet brauchen einen unterstützten,
signierten Pass vom Aussteller. Eine PNG-Datei allein lässt sich nicht als
Zahlungskarte hinzufügen. Diese App stellt keine Bankkarten aus.

### Von Atlas aktualisieren

Atlas schließen, dieses Paket in den bisherigen Programmordner kopieren
und `.venv`, `.atlas-data.json` sowie gegebenenfalls `.larp-routes.json`
behalten. Danach **Start-Larp Studio.cmd** starten und die Desktop-Verknüpfung
neu erstellen. Der alte Daten-Dateiname bleibt absichtlich erhalten.
Die EXE-Ausgabe ist eine separate Installation; bestehende lokale Daten
bei Bedarf in deren Ordner neben `Larp Studio.exe` kopieren.

## Straßentempo und Fahrzeit

Bei **Fahren → Straßentempo** liefert FOSSGIS/OSRM für jeden Straßenabschnitt
modellierte Geschwindigkeiten aus dem OpenStreetMap-Straßenprofil. Dieses
Modell berücksichtigt Straßenarten und dort vorhandene Tempolimitdaten.
Larp Studio verwendet diese Abschnittswerte, begrenzt sie auf höchstens 130 km/h
und reduziert sie zusätzlich für engere Kurven. Das Profil bremst vor
langsameren Abschnitten, beschleunigt sanft und hält am Start und Ziel an.
Die Fahrzeit ergibt sich aus genau diesem Profil; Vorschau und iPhone-Sitzung
verwenden dasselbe Zeitmodell. Während der Fahrt erscheinen aktuelles
simuliertes Tempo und Restzeit. Vorher zeigt die Seitenleiste den Durchschnitt.
Pause hält Position und Fahrprofil-Uhr an; die Restzeit läuft nicht weiter.

Dies ist eine Schätzung ohne Live-Staus, Ampelphasen oder kurzfristige
Beschilderung und keine verlässliche Auskunft über die aktuell gültigen
Tempolimits. Daten können fehlen oder veraltet sein. Wenn Abschnittsdaten
fehlen oder nicht zur Geometrie passen, ist der Automatikstart gesperrt:
Route neu planen oder ausdrücklich **Festes Tempo** wählen. Festes Tempo
behält die alte Bedienung bei und berücksichtigt keine Straßen oder Kurven.
Nach Punktänderungen die Route einschließlich Fahrprofil neu planen.

„Hin und zurück“ spielt dieselbe Geometrie und dasselbe Profil rückwärts ab.
Es plant keine separate Rückfahrtroute über andere Straßen oder Fahrspuren.

Koordinaten in der Suche: `52.516275, 13.377704` oder mit deutschem
Dezimalkomma `47,6282875; 9,9049859`. Mehrere Routenpunkte können mit der Maus
verschoben werden. Einzelne Punkte mit dem × neben dem Listeneintrag entfernen
oder den nummerierten Kartenpunkt anklicken und „Punkt entfernen“ wählen.
Nach einer Änderung die Route neu planen. Während einer laufenden Sitzung
zuerst „Beenden“ wählen. Maximal zwölf Punkte pro Planung.

Die Sitzung sendet ungefähr einmal pro Sekunde einen Standort und blockiert
dabei nicht die asynchrone USB-Tunnelverbindung durch eine Konsoleneingabe.
Das adressiert eine mögliche Ursache des bisherigen Fünf-Minuten-Abbruchs;
eine Bestätigung an deinem iPhone steht noch aus. „Gesendet“ ist eine
Befehlsbestätigung und keine Messung des tatsächlichen GPS-Orts. Prüfe die
Anzeige zuerst in Apple Karten. Snapchat kann zwischenspeichern oder eine
andere Position anzeigen. Wenn nach dem Zurücksetzen ein falscher Ort bleibt,
Larp Studio beenden und das iPhone neu starten.

## Internet und Kartendaten

Karten: OpenStreetMap; manuelle Suche: Photon/komoot; Routen: FOSSGIS/OSRM.
Der jeweilige Dienst erhält die angefragten Kartenbereiche, Suchbegriffe oder
Routenpunkte und die IP-Adresse des PCs. Eine Adresse kann auch ungenau
gefunden werden; den Zielpunkt auf der Karte kontrollieren.

Kein Vorladen ganzer Regionen, kein Offline-Kartenpaket und keine laufende
Suche beim Tippen. Suche und Routenplanung werden auf höchstens etwa eine
Anfrage pro Sekunde begrenzt und Antworten lokal im Speicher wiederverwendet.
WebView2 verwendet den normalen Browsercache für Kartenkacheln.
Die öffentlichen Kartendienste haben keine Verfügbarkeitsgarantie.

Die Dienstadressen stehen in `services.json` und lassen sich im Quellpaket
anpassen. Bei anderen Anbietern deren Nutzungsbedingungen und Kartenhinweise
berücksichtigen; die angezeigte Attribution muss dann ebenfalls geändert
werden.

## Ohne Kabel über WLAN · experimentell

1. PC und iPhone ins gleiche Heimnetz bringen. Der PC kann auch per LAN
   am selben Router hängen. Ein isoliertes Gastnetz funktioniert nicht.
2. iPhone per USB anschließen, entsperren und in Larp Studio **WLAN vorbereiten**
   öffnen. **Jetzt per USB vorbereiten** wählen und den Abschluss abwarten.
3. Larp Studio schaltet anschließend auf **WLAN**. **Verbinden** klicken und warten,
   bis die WLAN-Prüfung erfolgreich ist. Erst dann das Kabel abziehen.
4. Nun Punkt oder Route starten und in Apple Karten prüfen. Larp Studio verbindet
   sich für die Sitzung ausdrücklich über das Netzwerk, ohne USB-Fallback.

Die Vorbereitung aktiviert WLAN-Verbindungen auf dem bereits vertrauten iPhone,
richtet dessen RemotePairing ein und bereitet die Entwickler-Disk vor.
Die Geräteauswahl bleibt lokal gespeichert; geheime Paarungsdaten liegen im
üblichen lokalen pymobiledevice3-Paarungsspeicher, nicht im Downloadpaket.
Nach einem iPhone-Neustart kann die Vorbereitung erneut nötig sein.

PC und Larp Studio müssen weiterlaufen. Das iPhone muss das Netzwerk erreichen;
eine Route läuft unterwegs ohne PC-Verbindung mit dieser Methode nicht
zuverlässig weiter. Bei einer Windows-Firewall-Abfrage nur das eigene private
Heimnetz verwenden. Es werden keine Ports im Router geöffnet.

Bei Verbindungsabbruch wird ein Löschversuch über WLAN unternommen. Wenn das
iPhone nicht mehr erreichbar ist, kann dieser fehlschlagen. Dann dasselbe
iPhone per USB anschließen, **USB** wählen und den Standort wiederherstellen.
Den echten Ort in Apple Karten prüfen und bei Bedarf das iPhone neu starten.

WLAN-Unterstützung auf deinem iOS 27.2 ist noch nicht an echter Hardware
geprüft. Die App nutzt hierfür einen kleinen Adapter für die genau gepinnte
pymobiledevice3-Version; Bibliotheksupdates benötigen eine erneute Prüfung.

## Optional eine EXE erzeugen

Nach dem ersten erfolgreichen Start kann **EXE-erstellen.cmd** auf deinem
Windows-PC eine EXE mit PyInstaller bauen. Ergebnis:
`dist\Larp Studio\Larp Studio.exe`. Den **gesamten** Ordner `dist\Larp Studio` zusammen behalten.
Python wird anschließend für diesen Ordner nicht mehr benötigt; Apple-Treiber,
WebView2 und die Geräte-Voraussetzungen bleiben nötig.

Die EXE wurde auf GitHubs Windows-Runner gebaut und gestartet. Geräte-CLI,
WebView2-Fenster, Kartenbild-Canvas und Routen-API bestanden den Starttest.
Unter [diesem erfolgreichen Build](https://github.com/LorenzHPP/LarpStudio/actions/runs/38165709646)
das Artefakt **Larp-Studio-Windows** herunterladen (bei GitHub anmelden),
vollständig entpacken und **Larp Studio.exe** öffnen. Kein Python nötig.
Der Betrieb an deinem echten iPhone bleibt separat zu prüfen.

## Entwickeln / Prüfen

`python -m unittest discover -s tests -v` führt Offline-Tests aus und verändert
keinen iPhone-Standort. Prüfumfang und Grenzen stehen in `PRUEFUNG.md`.
`python app.py --preview 8765` bietet eine Browser-Vorschau auf
`http://127.0.0.1:8765`. Diese Vorschau verbindet kein iPhone. Kartenbild-Export und lokale
Routenbibliothek sind nutzbar; in der Vorschau liegen Routen im lokalen
Browser-Speicher. Für Änderungen: `CONTRIBUTING.md`.

Larp Studio-Quellcode: GPL-3.0-or-later. Leaflet und weitere Komponenten haben
eigene Lizenzen; siehe `THIRD-PARTY.md` und `licenses/`.
