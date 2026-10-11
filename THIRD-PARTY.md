# Quellen und Lizenzen

Larp Studio-Quellcode: GPL-3.0-or-later; vollständiger Text in `LICENSE`.

| Komponente | Version | Lizenz / Quelle |
| --- | --- | --- |
| Leaflet | 1.9.4 | BSD-2-Clause, `ui/vendor/LEAFLET-LICENSE.txt`, https://leafletjs.com/ |
| Inter Variable | lokal gebündelt | SIL Open Font License 1.1, `ui/assets/INTER-LICENSE.txt`, https://github.com/rsms/inter |
| pywebview | 6.2.1 | BSD-3-Clause, `licenses/PYWEBVIEW.txt`, https://github.com/r0x0r/pywebview |
| pymobiledevice3 | 11.26.0 | GPL-3.0-or-later, `licenses/PYMOBILEDEVICE3.txt`, https://github.com/doronz88/pymobiledevice3 |
| pytun-pmd3 / Wintun | über pymobiledevice3 | Hinweise und Wintun-Lizenz im gebündelten Paket, https://github.com/doronz88/pytun-pmd3 |
| Python | vom PC | PSF-Lizenz, https://www.python.org/psf/license/ |
| PyInstaller (optional) | 6.22.3 | GPL mit Bootloader-Ausnahme, https://pyinstaller.org/en/stable/license.html |

Python-Pakete und ihre weiteren Abhängigkeiten werden beim ersten Start aus
PyPI geladen; sie werden im Quell-Download nicht vorinstalliert mitgeliefert.
Ihre Lizenzdateien bleiben in der installierten Umgebung erhalten. Beim
Weitergeben eines gebauten Programms müssen auch die Lizenz- und
Quellcodepflichten der enthaltenen Abhängigkeiten berücksichtigt werden.
Die GitHub-EXE-Ausgabe enthält unter `Third-party/` ein Paketverzeichnis,
Lizenzdateien und die passenden, per SHA-256 geprüften Quellarchive der
GPL-/LGPL-Abhängigkeiten. `Quellcode.zip` enthält den zugehörigen App-Code
und die Build-Anweisungen.

Kartendaten © OpenStreetMap contributors, ODbL:
https://www.openstreetmap.org/copyright

- OSM-Kachelrichtlinie: https://operations.osmfoundation.org/policies/tiles/
- Photon-Suche: https://github.com/komoot/photon
- FOSSGIS-Routen: https://routing.openstreetmap.de/about.html
- OSRM API: https://project-osrm.org/docs/v5.24.0/api/
- pywebview-Windows-Installation: https://pywebview.flowrl.com/guide/installation.html
- Apple-Entwicklermodus: https://developer.apple.com/documentation/xcode/enabling-developer-mode-on-a-device

Larp Studio ist eine eigenständige Oberfläche für pymobiledevice3. Es verwendet
keinen Quellcode des anfangs verlinkten Repositorys ios-location-spoofer.

Das monochrome App-Logo und die Linien-Symbole wurden für Larp Studio als lokale
SVG-Dateien erstellt. Sie werden mit dem Larp Studio-Quellcode unter
GPL-3.0-or-later bereitgestellt. Die Figma-Illustrationen der bisherigen
Orbit Edition werden in dieser Oberfläche nicht mehr verwendet.

Der ursprüngliche Repository-Starttext stand unter MIT; dessen Hinweis bleibt
in `licenses/ORIGINAL-REPOSITORY-MIT.txt` erhalten. Der hinzugefügte App-Code
wird unter GPL-3.0-or-later bereitgestellt, wie das bisherige Quellpaket.
