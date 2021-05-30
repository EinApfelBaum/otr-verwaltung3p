### 1.0.0b8.post5-WIP
* Fixes duplicate Alt-e shortcut in ConclusionDialog
* Decoding should not "hang" anymore if errors occur
* Fixes cutlist rating
* New commandline option reduced debug "--rdebug"

### 1.0.0b8.post4
* Cutinterface: Cursor is hidden in video window
* Preferences->MainWindow: New setting Default sort order of the file list
  (filename or recording date)
* If "Cutlist nach dem Schneiden löschen" is True, cutlists are not deleted but
  moved to the internal AVI trashcan
* ffmsindex files are deleted when toolbar button "move to trash" in section
  AVI_UNCUT is used
* Directory monitors are updated when the path "folder_cut_avis",
  "folder_new_otrkeys" or "folder_uncut_avis" is changed in settings
* decodeorcut: Fixes UnicodeDecodeError when decoder reports errors. Fixes #108
* ConclusionDialog: Snippets can be inserted at cursor position

### 1.0.0b8.post3
* Fixes: ConclusionDialog "Erneut schneiden" -> Cutinterface "Abbrechen"
  instantly reopening the Cutinterface
* Cutinterface
  - New HD format: Showing/coloring of keyframe positions is disabled because
    keyframes are shown with an offset of 2 in the Cutinterface
  - "Schnitt testen" button now only active when a cut is selected

### 1.0.0b8.post2
* Forces correct config value for [programs] vdub
* Adds Button "Erneut schneiden" to ConclusionDialog which cancels the cut
  process and reinvokes the Cutinterface
* ConclusionDialog:
  - Button "Schnitt abbrechen" now closes the dialog if only one file was cut
* PreferenceWindow:
  - Hides entries for vdub and wineprefix in settings
* Other:
  - Fixes deleting ffmsindex files even if cutting was canceled (code was moved
    to conclusions.py)
* Fixes cutsview (Cutinterface) intercepting keystrokes.
* Changes for the AUR git package to show an extended version
* More robust adaption of path.py (Installation)
* Fixes bug in cutvirtualdub.py (wine not found)

### 1.0.0b8.post1
* Fixes error cutting HD2 files
* Fixes f-string usage (cutlists.py)
* Fixes unreadable text in message_error_box (otrverwaltung3p)
* Fixes bug in plugin "Abspielen" (Play.py)
* Fixes only one audio track is copied when remuxing to mp4 (smartmkvmerge)
* Fixes bug in bin/otrverwaltung3p (crashes when pathname in config is empty)

### 1.0.0b8
* Fixes problems with new HD format

##### Cutinterface (CI):
* Adds third stage of cutlist search "by size":
  _**Exact search**_ (1), _**Search for all qualities**_ (2) and _**Search by
  size**_ (3). Search by size will be automatically executed if neither
  (1) nor (2) yield any results but can also be invoked manually (a button
  on the top right).
* New button ">A": Play to next marker A
* New button ">A|B>": Test selected cut
* The settings can now be opened from the CI and changes take effect
  immediately in the CI.
* The length of the video after the cut is now displayed.

##### Hauptfenster:
* New contextmenu item "Manuell schneiden" (Section "Ungeschnitten")
* Readds Plugin "Manuell schneiden"

### 1.0.0b7, 2020-06-08
* Fixes HD videos are cut with wrong encoding parameters
* Cut video will not be moved to archive if cut was cancelled (conclusions.py)
* Fixes bug in fileoperations.py

### 1.0.0b6, 2020-06-01
* Fixes an error in setup.py not copying data/plugins/mediainfo.svg

### 1.0.0b5, 2020-05-29
* Fixes bug with auto-renaming

### 1.0.0b4, 2020-05-23
* Implements cutting of new HD format. Old otr-files are cut without vdub.

### 1.0.0b3, 2020-04-30

##### Hauptfenster:
* New keyboard shortcut Ctrl-f to focus search widget
* New context menu (Schneiden, Abspielen)
* New column in treeview: "Aufnahmedatum"
* Files that are processed are now locked in the file view
* The file treeviews are automatically updated by directory monitors when
  changes occur
* Implemented a wait-cursor where applicable (eg. Indexing)

##### Cutinterface:
* If there is only one cutlist available, it is automatically
  chosen and downloaded, after the dialog was opened
* Two new forward/backward seek buttons, seek distance is now based
  on seconds and can be defined in the settings
* ESCAPE-key disabled
* Mousewheel over slider navigates forward/backward

##### Zusammenfassung:
* Default usercomment is now editable
* Text snippets can be stored (Preferences->Cutlist->Snippets) and appended
  or prepended to the cutlist comment with one click.
* User is warned when trying to close the ConclusionDialog and not all cut
  files have been inspected.
* ESCAPE-key disabled

##### PreferencesWindow:
* Speicherorte: Paths are manually editable, new FileChooserDialog-Button
* Help texts are tooltips now
* New option to show "Zusammenfassung" after cut without clicking the button
  (Preferences->Schneiden)
* New setup.py using setuptools, using appdirs instead of xdg
* Changed versioning to be compatible with Setuptools
* Dbus disabled

### 1.0.0-beta002, 2020-02-03

* Fix pythonpath for debianoid systems
* Adapted mpv parameters to work with version 0.32.0+
* Dropped mpv option 'geometry' for option 'screen' (works for
  multi-monitor-setups)
* cutlists.py: Fixed error in reading cutlists from xml
* Fix decoding error
* config.py: make backup of conf file before overwriting it if content is
  corrupted
* Simplified keyring detection
* Value for h264_codec now forced to "ffdshow"
* CutinterfaceDialog: Some counter measures against the memory leak occuring by
  opening the CutinterfaceDialog repeatedly (needs more research)
* Plugin Mediainfo now disabled by default

### 1.0.0-beta001, 2020-01-28

* Add option to increase the volume for certain stations in Cutinterface and mpv
* automatically converting (AVI/HQ) cutlists to HD and vice versa (#70)
* New options for password storage
* AES encryption now uses internal lib (pyaes)
* decodeorcut/CutDialog (Choose cutlist): "Search for all qualities" implemented
  (no sorting though)
* Installation scripts updated
* Config file now saved with permissons 600
* Add option for password storage in keyring/wallet (binsky08)
* intern-easydecoder is now the default for decoding
* External programs now default in config (ffmpeg, ffmsindex, mediainfo etc.)
* cutlists.py: Fixed error with umlauts
* intern-virtualdub and intern-eac3to are now in a separate repository
* Installation scripts are now at [github.com/gCurse/support](
  https://github.com/gCurse/support/tree/master/otrv3p_installation_scripts)
* Edited filename is copied to suggested filename only if suggested filename is
  empty. Fixes #85
* Mpv now default for playback
* Bugfix for plugin CutPlay
* Old HQ and HD files are automatically cut with vdub if otr-verwaltung-vdub is
  installed
* Fix to get the configuration path for the config check on application start
  (binsky08)
* Eliminated trailing whitespaces
* Leaving the Cutinterface via "Cancel" or "Escape" will cause the conclusion
  button not be shown (i. e. the errormessage "Keine Schnitte angegeben" is
  suppressed)
* Conclusion button is now colored. YAY :)
* Fix Syntax warnings
* CutinterfaceDialog: Cut marker improved
* Handles if virtualdub (wine stuff) is installed or not

### 3.3.2-A, 2019-03-09

* Fixes AES encryption and dbus.glib deprecation warning
* AddDownloadDialog: libtorrent deactivated. Fixes #80
* Fix remuxing to mp4 for cutsmartmkvmerge

### 3.3.1-A, 2018-08-04

##### PreferencesWindow-Cutlist:
* New option "Vorgeschlagenen Dateinamen der Cutlist ignorieren", including an
  explanation
##### ConclusionDialog:
* File extension now stripped from suggested and other filenames
* Closes #60 File extension should be stripped from suggested_filename
##### +
* Updated encoding parameters for ffmpeg
* New options: Set icon size, use internal icons
* Plugin CutPlay (Geschnittenes Abspielen) now works with mpv

### 3.3.0-A, 2018-07-29

* CutinterfaceDialog now uses gstreamer's gtksink for video output. Fixes
  "CutInterface with black Screen"
* Removed option to set the video-sink of CutinterfaceDialog.player

### 3.2.5-A, 2018-07-23

* Add option to set the video-sink of CutinterfaceDialog.player
* Cutting mp4 with smartMkvMerge should now work reliable. Changed the encoding
  parameters
* CutinterfaceDialog: New context menu for label_filename (copy filename)
* New version


***


#### 3.2.4-A, 2018-07-11

##### Hauptfenster:
  - Die Standard-Aktion für den Button "Schneiden" in der Sektion
    "Ungeschnitten" ist jetzt in Einstellungen:Hauptfenster einstellbar
  - Die Sektion "Ungeschnitten" wird nach dem Programmstart automatisch
    angezeigt und aktiviert, sodass die Auswahl einer Datei mit den Pfeil-Tasten
    möglich ist
  - Neues Plugin "CutManually": Kann verwendet werden un das manuelle Schneiden
    durch Doppelklick auf eine Datei in "Ungeschnitten" zu starten
  - Die Sektionen "Download" und "Geplante Sendungen" sind nicht mehr sichtbar
  - Neue Sektionen: Papierkorb:Avi (zeigt nur avis im Papierkorb) und
    Papierkorb:Otrkey (zeigt nur otrkeys im Papierkorb)
  - Es werden jetzt die Icons aus dem aktiven Icon-Theme verwendet
  - AboutDialog überarbeitet
* Einstellungen:Cutlist: Suche nach Dateiname nun Standard und empfohlen
* Das Schneiden von mp4 mit SmartMKVmerge ist wieder aktiviert (Dies sollte
  genauso (un-)zuverlässig wie in otrv++ sein)
* Easydecoder wurde auf neueste Version 0.4.1133 aktualisiert
* Bugfixes

#### 3.2.3-A, 2018-06-28

* Sollte für HD oder HQ Dateien keine Schnittliste gefunden werden, so wird
  automatisch noch einmal nach Schnittlisten für andere Qualitäten gesucht
* In der Liste der auf cutlist.at verfügbaren Schnittlisten wird nun angezeigt,
  für welche Qualität (MP4, AVI, HQ oder HD) sie gedacht sind
* Neue Buttons im ConclusionDialog (Zusammenfassung) zum Umbenennen (Leerzeichen
  zu Unterstrich, Umlaute inkl. ß zu Ae, ae, ss usw.)
* Upload mehrerer Cutlists funktioniert jetzt

#### 3.2.2-A, 2018-06-20

* Während eine Datei indiziert wird (ffmsindex), wird dies durch einem
  Fortschrittsbalken im Hauptfenster angezeigt
* Neue Zeit -> Frame Konvertierungsmethode (kann in den Einstellungen -
  Cutinterface) aktiviert werden). Hauptsächlich sinnvoll für Aufnahmen von
  NTSC-Sendern (US-Format)
* Fehler beim Anzeigen der Schnitte in grün behoben: Der erste markierte Frame
  muss ein Keyframe sein, der letzte ein (Keyframe - 1)
* Neues Shellskript data/tools/otr-avi2hq.sh um otr-avi zu otr-avi.HQ zu
  konvertieren (falls Anfang oder Ende einer Sendung fehlt und nicht als HQ zu
  haben ist)
* Installationsskript für OpenSuse Leap 15 hinzugefügt. Dies erfordert die
  Aktivierung des "packman" repository. Anleitungen findet man im Netz
* Bei mehr sehr vielen Schnitten kam das Programm bisher beim Schneiden
  durcheinander. Jetzt sind beliebig viele Schnitte möglich (thx Mainboand)
* Neue Keyboard shortcuts (s. Wiki)
* Cutinterface: Widgets skalieren mit Fenstergröße
* Cutinterface: Neues Feature "Sucher (seeker)"
* Down-/Upload von Schnittlisten funktioniert mit der neuen cutlist.at
  (sniplist)
* Neue Option: 'mpv bevorzugen' für 'Schnitte anspielen'
* Die Funktion Zugangsdaten prüfen zeigt das Ergbnis jetzt deutlich an
* Keyframe jump funktioniert jetzt auch für Ubuntu etc
* Neues Icon
* setup.py funktioniert nun
* Der opensource Dekoder otrtool kann verwendet werden
* Bugfixes

#### 3.2.1-A, 2018-04-27

* Cutinterface stabilisert (OpenGL Fenster Ausbruch (no xvideo) und leeres
  Videofenster gefixt)
* Auto-update Funktion hinzugefügt

#### 3.2.0-A, 2018-04-21

* Programmversion und aktuelle Version auf github werden in der Fensterleiste
  angezeigt
* OTR Email und Passwort im Optionendialog können auf Korrektheit gepüft werden
* Überprüfung auf vorhandenes Passwort kann im Optionendialog abgeschaltet
  werden
* Verbesserter Startup-Dialog, wenn keine conf-Datei vorhanden oder Daten fehlen
* OTR-Passwort wird jetzt AES-verschlüsselt gespeichert
* CutInterface: Anzeige der Schnitte mit farbigen Balken, Balken grün wenn
  Schnitt an Keyframe
* CutInterface: Keyframe vor/zurück jetzt implementiert
* Cutlist upload funktioniert
* Das Umbenennenfeld ist jetzt leserlich und (immer noch) editierbar
* Einstellungendialog: Die persönliche cutlist.at URL ist editierbar
* (Fast?) Alle print Anweisungen durch logging ersetzt

#### 3.1-A, 2017-10-01

* OTR-Verwaltung++ umgestellt auf Python3, GTK3, GStreamer1.0
