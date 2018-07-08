#!/usr/bin/env bash

# otrv3p-install-opensuse.sh
version="0.0.1"
# 2018-06-19
# https://raw.githubusercontent.com/einapfelbaum/otr-verwaltung3p/master/installscripts/otrv3p-install-arch.sh

# BEGIN LICENSE
# This is free and unencumbered software released into the public domain.
# 
# Anyone is free to copy, modify, publish, use, compile, sell, or
# distribute this software, either in source code form or as a compiled
# binary, for any purpose, commercial or non-commercial, and by any
# means.
# 
# In jurisdictions that recognize copyright laws, the author or authors
# of this software dedicate any and all copyright interest in the
# software to the public domain. We make this dedication for the benefit
# of the public at large and to the detriment of our heirs and
# successors. We intend this dedication to be an overt act of
# relinquishment in perpetuity of all present and future rights to this
# software under copyright law.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS BE LIABLE FOR ANY CLAIM, DAMAGES OR
# OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
# ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.
# 
# For more information, please refer to <http://unlicense.org/>
# END LICENSE

# Made by gcurse.github.io


# colors
RED='\033[1;31m'
BLUE='\033[1;34m'
NOC='\033[0m'  # no color

check_root () {
    ## Check if we are root
    if [ "$(id -u)" != "0" ]; then
        root=0
    else
        root=1
    fi
}

create_desktop_file () {
    echo "otrv3p:create_desktop_file: Erzeuge otrv3p-git.desktop in $HOME/.local/share/applications" | tee -a /tmp/otrv3p-install.log
    echo "[Desktop Entry]
Type=Application
Name=OTR-Verwaltung3p-git
GenericName=Verwaltung von OTR-Dateien
GenericName[en]=Management of OTR-Files
Comment=Dateien von onlinetvrecorder.com verwalten: Schneiden, Schnitte betrachten, Cutlists bewerten...
Comment[en]=Manage files from onlinetvrecorder.com : decode, cut, review cuts, rate cutlists...
Categories=AudioVideo;AudioVideoEditing;
Exec=$HOME/otr-verwaltung3p/bin/otrverwaltung
Terminal=0
Icon=$HOME/otr-verwaltung3p/data/media/icon.png

" > $HOME/.local/share/applications/otrv3p-git.desktop
}

install_deps () {
    check_root
    if [ $root = 1 ]; then
        echo "otrv3p:install_deps: Installiere Abhängigkeiten" | tee -a /tmp/otrv3p-install.log

        for package in  xdg-user-dirs-gtk                    \
                        typelib-1_0-Gtk-3_0                  \
                        typelib-1_0-Gst-1_0                  \
                        typelib-1_0-GstVideo-1_0             \
                        typelib-1_0-GstPlayer-1_0            \
                        typelib-1_0-GstPbutils-1_0           \
                        gstreamer-plugin-python              \
                        python3-gobject                      \
                        python3-gobject-Gdk                  \
                        python3-gobject-cairo                \
                        python3-dbus-python                  \
                        python3-simplejson                   \
                        python3-cairo                        \
                        python3-requests                     \
                        python3-pycrypto                     \
                        python3-pip                          \
                        python3-libtorrent-rasterbar         \
                        gstreamer-plugins-base               \
                        gstreamer-plugins-good               \
                        gstreamer-plugins-bad                \
                        gstreamer-plugins-ugly               \
                        gstreamer-plugins-libav              \
                        gstreamer-utils                      \
                        mediainfo-gui                        \
                        mpv                                  \
                        git-core; do
            ## Only install packages if they are not alredy installed
            rpm -q "$package" > /dev/null 2>&1 || zypper --non-interactive install "$package" | tee -a /tmp/otrv3p-install.log
        done
        if [ $? = 0 ]; then echo -e "Alle Abhängigkeiten sind (jetzt) installiert.\n"; fi
        exit
    else
        echo -e "\n\n${RED}otrv3p:install_deps: Diese Skriptfunktion muss als root ausgeführt werden${NOC}\n\n" | tee -a /tmp/otrv3p-install.log
        exit
    fi
}

install_otrv3p_git () {
    check_root
    if [ $root = 0 ]; then
        cd $HOME
        if [[ -d "otr-verwaltung3p" ]]; then
            echo -e "otrv3p:install_otrv3p_git: Das Verzeichnis $HOME/otr-verwaltung3p existiert. Das Repo wird nicht geklont." | tee -a /tmp/otrv3p-install.log
            echo "no" > /tmp/otrv3pCloneYesNo
        else
            git clone https://github.com/EinApfelBaum/otr-verwaltung3p.git 2>&1 | tee -a /tmp/otrv3p-install.log
            echo "yes" > /tmp/otrv3pCloneYesNo
        fi
        mkdir -p $HOME/.local/share/applications 2>&1 | tee -a /tmp/otrv3p-install.log
        mkdir -p $HOME/.local/share/otrverwaltung 2>&1 | tee -a /tmp/otrv3p-install.log
        create_desktop_file
        echo "otrv3p:install_otrv3p_git: Updating desktop database" | tee -a /tmp/otrv3p-install.log
        update-desktop-database $HOME/.local/share/applications 2>&1 | tee -a /tmp/otrv3p-install.log
        ## pip3 install stuff
        if $(python3 -c "import git" > /dev/null 2>&1); then
            echo "otrv3p:install_otrv3p_git: gitpython ist bereits installiert."
        else
            echo "otrv3p:install_otrv3p_git: Installiere gitpython." | tee -a /tmp/otrv3p-install.log
            pip3 install gitpython --user 2>&1 | tee -a /tmp/otrv3p-install.log
        fi
        if $(python3 -c "import xdg" > /dev/null 2>&1); then
            echo "otrv3p:install_otrv3p_git: python3-xdg ist bereits installiert."
        else
            echo "otrv3p:install_otrv3p_git: Installiere xdg." | tee -a /tmp/otrv3p-install.log
            pip3 install pyxdg --user 2>&1 | tee -a /tmp/otrv3p-install.log
        fi
        exit
    else
        echo -e "\n\n${RED}otrv3p:install_otrv3p_git: Diese Skriptfunktion darf nicht als root ausgeführt werden${NOC}\n\n" | tee -a /tmp/otrv3p-install.log
        exit
    fi
}

usage () {
    echo -e "\n${RED}"
    echo -e "ACHTUNG: Es wird vorausgesezt, dass das 'Packman' Repository aktiviert ist!!\n${BLUE}"
    echo -e "Die Installation wird in zwei Schritten durchgeführt werden:\n"
    echo -e "    1. Installation der Abhängigkeiten (Root-Rechte benötigt)."
    echo -e "    2. Installation der otr-verwaltung3p (ohne Root-Rechte).\n\n"
    echo -e "Das läuft automatisch ab. Bereit? Dann weiter mit der Eingabetaste, abbrechen mit Strg-C${NOC}"
    read dummy
}

if [ -z "$1" ]; then
    check_root
    if [ $root = 1 ]; then
        echo -e "\n\n${RED}Dieses Skript darf nicht als root ausgeführt werden${NOC}\n\n" | tee -a /tmp/otrv3p-install.log
        exit 1
    fi

    #export myhome=$HOME
    echo -e "\n"$(date +"%Y-%m-%d_%H:%M:%S")" LOG BEGINS\n" >> /tmp/otrv3p-install.log
    usage
elif [ "$1" = "deps" ]; then
    #myhome="$2"
    install_deps
elif [ "$1" = "prog" ]; then
    #myhome="$2"
    install_otrv3p_git
else
    echo -e "\n\n${RED}otrv3p: Das hätte niemals passieren dürfen! THE END${NOC}\n\n" 2>&1 | tee -a /tmp/otrv3p-install.log
    exit 1
fi

# Recursive call
echo "otrv3p: Start sudo $0 deps" | tee -a /tmp/otrv3p-install.log
sudo "$0" deps #$HOME
# Recursive call
echo "otrv3p: Start $0 prog" | tee -a /tmp/otrv3p-install.log
"$0" prog #$HOME
clone=$(cat /tmp/otrv3pCloneYesNo)
rm /tmp/otrv3pCloneYesNo
# check for wine and hint
echo "otrv3p: checking for wine" | tee -a /tmp/otrv3p-install.log
which wine > /dev/null 2>&1
if [ "$?" = 0 ]; then
    echo -e "otrv3p: wine ist installiert." | tee -a /tmp/otrv3p-install.log
else
    echo -e "otrv3p: wine ist nicht installiert.\nFalls mp4 geschnitten werden sollen, muss wine installiert werden.\n" | tee -a /tmp/otrv3p-install.log
    echo -n "Soll wine installiert werden? (j/N)? "
    read answer
    if [ "$answer" != "${answer#[Jj]}" ]; then
        echo "Installiere wine"; sudo apt-get install wine
    else
        echo "wine wird nicht installiert."
    fi
fi
 
