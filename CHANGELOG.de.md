### 1.0.0b8.post5
* Neue Option Einstellungen -> Cutinterface -> "Cutlistsuche automatisch öffnen"
  sucht automatisch nach einer Cutlist, wenn keine lokal vorhanden ist
* Der doppelt vergebene Shortcut "Alt-e" in der Zusammenfassung wurde korrigiert
* Das Dekodieren sollte nun nicht mehr "hängen" wenn ein Dekoderfehler auftritt
* Das Bewerten der Cutlists sollte nun wieder funktionieren
* Neuer Parameter für reduzierte Debug-Ausgabe "--rdebug"
* Bugfix in CutAction.LOCAL_CUTLIST
* LoadCutDialog: Fehlerspalten werden nur erweitert, wenn ein Fehler vorliegt
* Das neue HD-Format der xPlus-Sender wird jetzt erkannt (kann nur mit wine und virtualdub geschnitten werden)

### 1.0.0b8.post4
* Cutinterface: Mauszeiger wird im Videofenster ausgeblendet
* Einstellungen->Hauptfenster: Neue Einstellung Standardsortierung der Dateiliste
  entweder nach Name oder Aufzeichnungsdatum.
* Wenn "Cutlist nach dem Schneiden löschen" aktiv ist werden Cutlists nicht gelöscht,
  sondern in den internen AVI-Papierkorb verschoben.
* Zusammenfassung: Snippets können an der Cursor-Position eingefügt werden.

### 1.0.0b8.post3
* Zusammenfassung "Erneut schneiden" -> Cutinterface "Abbrechen" öffnete sofort
  wieder das Cutinterface. Dies ist behoben.
* Cutinterface
  - Die Anzeige/farbliche Markierung der Keyframe-Positionen wurde für das neue
    HD-Format deaktiviert, weil Keyframes mit einem Offset von 2 angezeigt werden.
  - "Schnitt testen" ist jetzt nur aktiv, wenn ein Schnitt ausgewählt ist.

### 1.0.0b8.post2
* Fügt den Button "Erneut schneiden" zur Zusammenfassung hinzu, der den Schnitt
  abbricht und die Datei erneut im Cutinterface öffnet.
* Zusammenfassung:
  - "Schnitt abbrechen" schliesst den Dialog, falls nur eine Datei geschnitten
    wurde.
* Einstellungen:
  - Blendet Einträge für vdub und wineprefix in Einstellungen aus
* Sonstiges:
  - Behebt Fehler in cutvirtualdub.py (wine nicht gefunden).

### 1.0.0b8.post1
* Korrigiert Fehler beim Schneiden von HD2-Dateien.
* f-strings mit zu neuer Syntax wurden wurden geändert (cutlists.py).
* Behebt Fehler im Plugin "Abspielen" (Play.py).
* "Am Ende automatisch MP4 erzeugen" kopiert jetzt alle Audiotracks (smartmkvmerge).
* Fehler in bin/otrverwaltung3p behoben (stürzt ab, wenn Pfadname in der Konfiguration leer ist).

### 1.0.0b8

* Behebt Probleme beim Schneiden des neuen HD-Formates.

##### Cutinterface (CI):
* Fügt eine dritte Stufe der Cutlist-Suche "nach Größe" hinzu:
  _**Exakte Suche**_ (1), _**Suche nach allen Qualitäten**_ (2) und _**Suche
  nach Größe**_ (3). Die Suche nach Größe wird automatisch ausgeführt, wenn weder
  (1) noch (2) zu einem Ergebnis führt, sie kann aber auch manuell ausgeführt
  werden (Button oben rechts im "Cutlist wählen" Dialog).

* Neuer Button ">A": Abspielen bis zum nächsten Marker-A
* Neuer Button ">A|B>": Markierten Schnitt testen
* Die Einstellungen können nun aus dem CI heraus geöffnet werden und
  Änderungen werden sofort wirksam, soweit sie das CI betreffen.
* Die Länge des Videos nach dem Schnitt wird nun angezeigt.

##### Hauptfenster:
* Kontextmenü (Sektion "Ungeschnitten") erweitert um "Manuell schneiden"
* Das Plugin "Manuell schneiden" ist wieder da.

### 1.0.0b4, 2020-05-23
* Das neue HD-Format kann geschnitten werden. Alte otr-Dateien können ohne
  vdub geschnitten werden.

### 1.0.0b3, 2020-03-18

##### Hauptfenster:
* Neue Spalte "Aufnahmedatum" in der Dateiansicht
* Neue Tastenkombination Strg-f zum Fokussieren des Suchfeldes
* Neues Kontextmenü (Schneiden, Abspielen)
* Verarbeitete Dateien sind jetzt in der Dateibaumansicht gesperrt.
* Die Dateiansichten werden automatisch von Verzeichnismonitoren aktualisiert,
  wenn Änderungen auftreten

##### Cutinterface:
* Wenn nur eine Cutlist vorhanden ist, wird diese automatisch
  ausgewählt und heruntergeladen, nachdem der Dialog geöffnet worden ist
* Der Cutlist-Dialog kann nun mit der Tastatur bedient werden (Auf/Ab
  um die Cutlist zu wählen und ENTER um sie zu übernehmen und den
  Dialog zu schließen)
* Zwei neue Buttons für Vorwärts-/Rückwärtssuche, Suchabstand basiert
  jetzt auf Sekunden und kann in den Einstellungen festgelegt werden
* Es kann nun mit dem Mausrad auf dem Slider navigiert werden
* ESCAPE-Taste deaktiviert

##### Zusammenfassung (ConclusionDialog):
* Es können kurze Texte (snippets) gespeichert werden (Einstellungen->Cutlist
  Snippets), die mit einem Klick an den Cutlist-Kommentar angehängt oder
  vorangestellt werden können
* Benutzer wird beim Versuch den Zusammenfassung-Dialog zu schließen gewarnt,
  wenn nicht alle Dateien geprüft wurden.
* ESCAPE-Taste deaktiviert
* Neue Option um die Zusammenfassung automatisch nach dem Schneiden anzuzeigen
  (ohne Klick auf den Button "... Datei ist fertig")
* Neue setup.py mit Setuptools
* Geänderte Versionierung, um mit Setuptools kompatibel zu sein
* Dbus entfernt
* ESCAPE-Taste in CutinterfacDialog und ConclusionDialog deaktiviert
* Warte-Cursor implementiert wo sinnvoll (z.B. Indexierung)
* Standard-Benutzerkommentar ist jetzt editierbar

##### Einstellungen:
* Speicherorte: Pfade sind manuell editierbar
* Die meisten Hilfetexte sind jetzt Tooltips

### 1.0.0-beta002, 2020-02-03

* Pythonpfad für debianoide Systeme korrigiert
* mpv-Parameter für die Version 0.32.0+ angepasst
* Platzierung des Hauptfensters beim Start funktioniert jetzt auch für
  Multi-Monitor-Setups
* cutlists.py: Fehler beim Lesen von Cutlists aus xml behoben
* Decodierungsfehler behoben
* config.py: Es wird ein Backup der conf-Dateierstellt, bevor sie überschrieben
  wird, wenn der Inhalt nicht gelesen werden kann
* Wert für h264_codec ist nun immer "ffdshow"
* CutinterfaceDialog: Einige Gegenmaßnahmen gegen das Speicherleck, das durch
  wiederholtes Öffnen des CutinterfaceDialogs ensteht
* Das Plugin Mediainfo ist jetzt standardmäßig deaktiviert

### 1.0.0-beta001, 2020-01-28

* Option zur Erhöhung der Lautstärke für bestimmte Sender im Cutinterface
  und mpv hinzugefügt
* Automatische Konvertierung von (AVI/HQ-)Schnittlisten nach HD und umgekehrt
* Neue Optionen für die Speicherung von Passwörtern
* AES-Verschlüsselung verwendet jetzt intern "pyaes"
* Decodierung/CutDialog (Auswahl der Schnittliste): "Suche nach allen
  Qualitäten" implementiert (allerdings keine Sortierung)
* Installationsskripte aktualisiert
* Konfigurationsdatei jetzt mit Berechtigungen 600 gespeichert
* Option für die Speicherung des Passworts im Keyring / Wallet hinzugefügt
  (binsky08)
* Intern-easydecoder ist jetzt der Standard für die Decodierung
* Externe Programme sind jetzt in der Konfiguration voreingestellt (ffmpeg,
  ffmsindex, mediainfo usw.).
* intern-virtualdub und intern-eac3to sind jetzt in einem separaten Repository
* Der bearbeitete Dateiname wird nur dann in den vorgeschlagenen Dateinamen
  kopiert, wenn der vorgeschlagene Dateiname leer ist.
* Mpv jetzt Standard für die Wiedergabe
* Fehlerbehebung für das Plugin CutPlay
* Alte HQ- und HD-Dateien werden automatisch mit vdub geschnitten, wenn
  otr-verwaltung-vdub installiert ist
* Fix, um die conf Datei beim Start der Anwendung zu finden (binsky08)
* Nach dem Verlassen des Cutinterface über "Abbrechen" oder "Escape" wird der
  Button "Eine Datei ist fertig" nicht mehr angezeigt. (d. h. die Fehlermeldung
  "Keine Schnitte angegeben" wird unterdrückt)
* Der Button "Eine Datei ist fertig" ist jetzt farbig. YAY :)
* CutinterfaceDialog: Schnittmarkierung verbessert

### 3.3.2-A, 2019-03-09

* Behebt die AES-Verschlüsselung und die `dbus.glib` deprecated Meldungen.
* AddDownloadDialog: libtorrent deaktiviert. Fixes #80
* "Am Ende automatisch mp4 erzeugen" funktioniert wieder.

### 3.3.1-A, 2018-08-04

##### Einstellungen-Cutlist:
* Neue Option "Vorgeschlagene Dateinamen der Cutlist ignorieren", einschließlich
  Erklärung.

##### Zusammenfassung:
* Dateierweiterung jetzt von vorgeschlagenen und anderen Dateinamen entfernt.
* Schließt #60 "File extension should be stripped from suggested_filename".

* Aktualisierte Kodierungsparameter für ffmpeg.
* Neue Optionen: Icon-Größe einstellen, interne Icons verwenden.
* Plugin Geschnittenes Abspielen funktioniert jetzt mit mpv

### 3.3.0-A, 2018-07-29

* CutinterfaceDialog verwendet jetzt den gtksink von gstreamer für die
  Videoausgabe. Behebt "CutInterface with black screen"
* Option zum Einstellen des Video-Sinks von `CutinterfaceDialog.player` entfernt

### 3.2.5-A, 2018-07-23

* Option zum Festlegen des Video-Sinks von `CutinterfaceDialog.player` hinzufügen
* Das Schneiden von mp4 mit smartMkvMerge sollte nun zuverlässig funktionieren.
  Die Kodierung wurde geändert.
* CutinterfaceDialog: Neues Kontextmenü für label_filename (Kopiere Dateinamen)
