# An Larp Studio arbeiten

Python 3.13 und Node.js 22 verwenden. Offline-Prüfungen:

```sh
python -m unittest discover -s tests -v
node --check ui/app.js
node --check ui/studio.js
node --check ui/library.js
```

Mit `python app.py --preview 8765` lässt sich die Oberfläche im Browser prüfen.
Die Vorschau verbindet kein iPhone. PNG-Export und Routenbibliothek sind dort
nutzbar; Gerätesteuerung benötigt die Windows-App.

Eine Änderung an USB/WLAN braucht zusätzlich einen Test am eigenen iPhone.
Im Pull Request angeben, ob Hardware geprüft wurde, welches iOS verwendet
wurde und ob Start, Pause, Beenden und Zurücksetzen funktionierten.
Geräte-Seriennummern, Paarungsdateien und private Ortsdaten nicht hochladen.

Abhängigkeiten bleiben gepinnt. Bibliotheksänderungen erfordern eine Prüfung
der transport.py-Schnittstellen und des eingefrorenen Windows-Programms.

Der Windows-Build unter **Actions → Windows app → Run workflow** erzeugt ein
ZIP-Artefakt mit EXE, Dateien und dem dazugehörigen GPL-Quellcode.

Für den Browser-Test `python -m pip install playwright` und
`python -m playwright install chromium` ausführen. Vorschau starten, dann
`python tools/check_studio.py`. Der Test verwendet lokale Karten-Testdaten
und verändert kein iPhone.
