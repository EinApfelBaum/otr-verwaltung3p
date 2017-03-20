OTR-Verwaltung
==============

Copyright (C) 2010 Benjamin Elbers <elbersb@gmail.com>

Die Ursprungsversion von OTRVerwaltung wurden von Benjamin Elbers programmiert.

OTR-Verwaltung++
-----

OTRVerwaltung wurde durch einige Patches erweitert, daraus entstand OTRVerwaltung++
https://github.com/monarc99/otr-verwaltung

OTR-Verwaltung3Plus
-----

Ein Port zu Python 3 und GTK3+.
https://github.com/EinApfelBaum/otr-verwaltung/tree/python3/GTK3

Feedback, Bugreport, Fehler
http://www.otrforum.com/showthread.php?74447-OTRVerwaltung3Plus-eine-Portierung-von-OTRVerwaltung-hinzu-Python3-und-Gtk3

Alpha Version, ich weise hier auch noch mal darauf hin, dass
dies noch keine Release Version ist.


In einer VM Ubuntu 16.04 und Linux Mint 18.1 musste ich folgende Pakete installieren:

sudo apt-get install python3-libtorrent mediainfo-gui mpv

Hint:
Bei mir (Linux Mint 18.1 Cinnamon) wird der CutInterfaceDialog nicht richtig angezeigt.
Das Video ist nicht zu sehen, aber Audio kann ich hören.
In den VMs tritt dieser Fehler nicht auf. Dort ist Bild und Video richtig im CutInterfaceDialog richtig verarbeitet.
Die Ursache habe ich bei mir noch nicht gefunden.

TODO
----

__Oberfläche__
- Windows
- [x] MainWindow
- [x] PreferencesWindow
- Dialoge
- [x] AddDownloadDialog
- [x] ArchiveDialog
- [x] ConclusionDialog
- [x] CutDialog
- [ ] CutinterfaceDialog
- [ ] DownloadPropertiesDialog
- [x] EmailPasswordDialog
- [x] LoadCutDialog
- [x] PlanningDialog
- [x] PluginsDialog
- [x] RenameDialog

__Funktionalität__
- [x] Datei löschen, wiederherstellen
- [x] Datei Abspielen (PlugIn)
- [x] MediaInfo (PlugIn)
- [x] Archivieren
- [x] Convert to MKV
- [x] Datei umbennen
- [x] Ordner erstellen
- [x] Ordner löschen
- [ ] Download
- [ ] geplante Sendungen
- [x] Decode otrkey Datei
- [x] Cut Avi - SmartMKVMerge
- [x] Cut HD - SmartMKVMerge
- [ ] Cut mp4

__Feinheiten__
- [ ] Oberflächengestaltung anpassen ( Abstände , Ränder, etc. ... )
- [ ] Code cleanup
