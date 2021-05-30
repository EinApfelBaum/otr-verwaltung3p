# -*- coding: utf-8 -*-
# BEGIN LICENSE
# Copyright (C) 2010 Benjamin Elbers <elbersb@gmail.com>
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3, as published
# by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranties of
# MERCHANTABILITY, SATISFACTORY QUALITY, or FITNESS FOR A PARTICULAR
# PURPOSE.  See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program.  If not, see <http://www.gnu.org/licenses/>.
# END LICENSE

import codecs
import configparser
import logging
import os.path
import sys
import urllib.request

# noinspection PyUnresolvedReferences
import xml.dom.minidom
from pathlib import Path

from otrverwaltung3p import fileoperations

import requests

# UTF-8 Encoding Debugging
# see https://www.i18nqa.com/debug/utf8-debug.html
# wrong_right_chars = {"Ã€" : "À", "Ã"  : "Á", "Ã‚" : "Â", "Ãƒ" : "Ã", "Ã„" : "Ä", "Ã…" : "Å",
# "Ã†" : "Æ", "Ã‡" : "Ç", "Ãˆ" : "È", "Ã‰" : "É", "ÃŠ" : "Ê", "Ã‹" : "Ë",
# "ÃŒ" : "Ì", "Ã"  : "Í", "ÃŽ" : "Î", "Ã"  : "Ï", "Ã"  : "Ð", "Ã‘" : "Ñ",
# "Ã’" : "Ò", "Ã“" : "Ó", "Ã”" : "Ô", "Ã•" : "Õ", "Ã–" : "Ö", "Ã—" : "×",
# "Ã˜" : "Ø", "Ã™" : "Ù", "Ãš" : "Ú", "Ã›" : "Û", "Ãœ" : "Ü", "Ã"  : "Ý",
# "Ãž" : "Þ", "ÃŸ" : "ß", "Ã " : "à", "Ã¡" : "á", "Ã¢" : "â", "Ã£" : "ã",
# "Ã¤" : "ä", "Ã¥" : "å", "Ã¦" : "æ", "Ã§" : "ç", "Ã¨" : "è", "Ã©" : "é",
# "Ãª" : "ê", "Ã«" : "ë", "Ã¬" : "ì", "Ã­"  : "í", "Ã®" : "î", "Ã¯" : "ï",
# "Ã°" : "ð", "Ã±" : "ñ", "Ã²" : "ò", "Ã³" : "ó", "Ã´" : "ô", "Ãµ" : "õ",
# "Ã¶" : "ö", "Ã·" : "÷", "Ã¸" : "ø", "Ã¹" : "ù", "Ãº" : "ú", "Ã»" : "û",
# "Ã¼" : "ü", "Ã½" : "ý", "Ã¾" : "þ", "Ã¿" : "ÿ"}

wrong_right_chars = {
    "Ã„": "Ä",
    "Ã¤": "ä",
    "Ã–": "Ö",
    "Ã¶": "ö",
    "Ãœ": "Ü",
    "Ã¼": "ü",
    "ÃŸ": "ß",
    "Ã ": "à",
    "Ã¡": "á",
    "Ã¢": "â",
    "Ã§": "ç",
    "Ã©": "é",
    "Ã¨": "è",
    "Ãª": "ê",
    "Ã´": "ô",
    "Ã«": "ë",
}

qualities = {".mpg.mp4": "MP4", ".mpg.avi": "AVI", ".HQ.avi": "HQ", ".HD.avi": "HD"}


class Cutlist:
    def __init__(self):

        self.log = logging.getLogger(self.__class__.__name__)
        # cutlist.at xml-output
        self.id = 0
        self.author = ""
        self.ratingbyauthor = 0
        self.rating = 0
        self.ratingcount = 0
        self.countcuts = 0  # !!!
        self.actualcontent = ""
        self.usercomment = ""
        self.filename = ""
        self.withframes = 0
        self.withtime = 0
        self.duration = ""
        self.errors = ""
        self.othererrordescription = ""
        self.downloadcount = 0
        self.autoname = ""
        self.filename_original = ""

        # additions in cutlist file
        self.wrong_content = 0
        self.missing_beginning = 0
        self.missing_ending = 0
        self.other_error = 0
        self.suggested_filename = ""
        self.intended_app = ""
        self.intended_version = ""
        self.smart = 0
        self.fps = 0

        # own additions
        self.app = "OTR-Verwaltung3p"
        self.errors = False
        self.cuts_seconds = []  # (start, duration) list
        self.cuts_frames = []  # (start, duration) list
        self.local_filename = None
        self.quality = ""

    def upload(self, server, cutlist_hash):
        """ Uploads a cutlist to cutlist.at "
            Upload code from:  http://code.activestate.com/recipes/146306/

            Returns: error message, otherwise None
        """

        clist = open(self.local_filename, "r").read()
        try:
            response = requests.post(
                server,
                {"userid": cutlist_hash, "filename": os.path.basename(self.local_filename)},
                files={"userfile[]": clist},
            )
            self.log.debug(f"response: {response}")
            self.log.debug(f"response.text: {response.text}")

            if "erfolgreich" in response.text:
                return None
            else:
                return response.text
        except TimeoutError:
            return "Connection timed out!"

    def download(self, server, video_filename):
        """ Downloads a cutlist to the folder where video_filename is.
            Checks whether cutlist already exists.

            Returns: error message, otherwise None
        """
        self.local_filename = video_filename
        self.log.debug(f"video_filename: {video_filename}")
        count = 0

        while os.path.exists(self.local_filename + ".cutlist"):
            count += 1
            self.local_filename = f"{video_filename}.{str(count)}"

        self.local_filename += ".cutlist"

        # download cutlist
        url = server + "getfile.php?id=" + str(self.id)

        try:
            self.local_filename, headers = urllib.request.urlretrieve(url, self.local_filename)
        except IOError as error:
            return f"Cutlist konnte nicht heruntergeladen werden ({error})."

    def read_from_file(self):
        config_parser = configparser.ConfigParser()

        try:
            # configparser now reads local cutlist assuming utf-8 encoding
            config_parser.read(self.local_filename, encoding="utf-8")

            self.filename = config_parser.get("Info", "SuggestedMovieName")
            self.author = config_parser.get("Info", "Author")
            self.ratingbyauthor = int(config_parser.get("Info", "RatingByAuthor"))
            self.rating = 0
            self.ratingcount = 0
            self.usercomment = config_parser.get("Info", "UserComment")
            self.countcuts = int(config_parser.get("General", "NoOfCuts"))
            self.actualcontent = config_parser.get("Info", "ActualContent")
            self.filename_original = config_parser.get("General", "ApplyToFile")
            for key, value in qualities.items():
                if key in self.filename_original:
                    self.quality = value

        except Exception as e:
            self.log.error(f"Exception: {e}")
            self.log.error(f"Malformed cutlist: {self.local_filename}")

    def read_cuts(self):
        """ Reads cuts from local_filename.

            Returns: error message, otherwise None
        """

        if self.cuts_seconds or self.cuts_frames:
            return

        config_parser = configparser.ConfigParser()

        try:
            config_parser.read(self.local_filename, encoding="utf-8")
        except configparser.ParsingError as message:
            self.log.info("Malformed cutlist: ", message)

        try:
            noofcuts = int(config_parser.get("General", "NoOfCuts"))

            for count in range(noofcuts):
                cut = "Cut" + str(count)

                if config_parser.has_option(cut, "StartFrame") and config_parser.has_option(cut, "DurationFrames"):
                    start_frame = int(config_parser.get(cut, "StartFrame"))
                    duration_frames = int(config_parser.get(cut, "DurationFrames"))
                    if duration_frames > 0:
                        self.cuts_frames.append((start_frame, duration_frames))
                        self.log.info(f"Append frames: {start_frame}, {duration_frames}")

                start_second = float(config_parser.get(cut, "Start"))
                duration_seconds = float(config_parser.get(cut, "Duration"))
                if duration_seconds > 0:
                    self.cuts_seconds.append((start_second, duration_seconds))
                    self.log.info(f"Append seconds:  {start_second}, {duration_seconds}")

        except configparser.NoSectionError as message:
            return "Fehler in Cutlist: " + str(message)
        except configparser.NoOptionError as message:
            return "Fehler in Cutlist: " + str(message)

    def rate(self, rating, server):
        """ Rates a cutlist.

            Returns: True for success.
        """

        url = f"{server}rate.php?rate={self.id}&rating={rating}"
        self.log.debug(f"Rate URL: {url}".replace(server.split("/")[3], "<FRED>"))

        try:
            httpobj = urllib.request.urlopen(url)

            # message = urllib.request.urlopen(url).read()
            message = httpobj.read()
            self.log.debug(f"Rate message: {message}".replace(server.split("/")[3], "<FRED>"))

            # old response: if "Cutlist wurde bewertet. Vielen Dank!" in message:
            if sys.version_info < (3, 9):
                status_code = httpobj.getcode()
            else:
                status_code = httpobj.status

            if status_code == 200:
                self.log.debug(f"Status code: {httpobj.status}")
                return True, message
            else:
                return False, message
        except (IOError, TypeError) as e:
            self.log.debug(f"Exception: {e}")
            # return False, "Keine Internetverbindung oder sonstiger Fehler"
            return False, f"Exception: {e}"

    def write_local_cutlist(self, uncut_video, intended_app_name, my_rating):
        """ Writes a cutlist file to the instance's local_filename. """
        self.log.debug("Function starts")
        try:
            with codecs.open(self.local_filename, "w", "UTF-8") as cutlist:

                cutlist.writelines(
                    [
                        "[General]\n",
                        f"Application={self.app}\n",
                        f"Version={self.intended_version}\n",
                        f"FramesPerSecond={self.fps:.2f}\n",
                        f"IntendedCutApplicationName={intended_app_name}\n",
                        f"IntendedCutApplication={self.intended_app}\n",
                        f"VDUseSmartRendering={str(int(self.smart))}\n",
                        "VDSmartRenderingCodecFourCC=0x53444646\n",
                        "comment1=The following parts of the movie will be kept, the rest will be cut out.\n",
                        "comment2=All values are given in seconds.\n",
                        f"NoOfCuts={str(len(self.cuts_frames))}\n",
                        f"ApplyToFile={Path(uncut_video).name}\n",
                        f"OriginalFileSizeBytes={str(fileoperations.get_size(uncut_video))}\n",
                        "\n",
                        "[Info]\n",
                        f"Author={self.author}\n",
                        f"RatingByAuthor={str(self.ratingbyauthor)}\n",
                        f"EPGError={str(int(self.wrong_content))}\n",
                        f"ActualContent={str(self.actualcontent)}\n",
                        f"MissingBeginning={str(int(self.missing_beginning))}\n",
                        f"MissingEnding={str(int(self.missing_ending))}\n",
                        "MissingVideo=0\n",
                        "MissingAudio=0\n",
                        f"OtherError={str(int(self.other_error))}\n",
                        f"OtherErrorDescription={str(self.othererrordescription)}\n",
                        f"SuggestedMovieName={str(self.suggested_filename)}\n",
                        f"UserComment={str(self.usercomment)}\n",
                        "\n",
                    ]
                )

                for count, (start_frame, duration_frames) in enumerate(self.cuts_frames):
                    cutlist.writelines(
                        [
                            f"[Cut{count}]\n",
                            f"Start={start_frame / self.fps:.2f}\n",
                            f"StartFrame={start_frame}\n",
                            f"Duration={duration_frames / self.fps:.2f}\n",
                            f"DurationFrames={duration_frames}\n",
                            "\n",
                        ]
                    )
        except IOError:
            self.log.warning(f"Konnte Cutlist-Datei nicht erstellen: {self.local_filename}")


# Other methods
def download_cutlists(
    filename,
    server,
    choose_cutlists_by,
    cutlist_mp4_as_hq,
    error_cb=None,
    cutlist_found_cb=None,
    get_all_qualities=None,
):
    """ Downloads all cutlists for the given file.
            filename            - movie filename
            server              - cutlist server
            choose_cutlists_by  - 0 by size, 1 by name
            cutlist_mp4_as_hq   -
            error_cb            - callback: an error occurs (message)
            cutlist_found_cb    - callback: a cutlist is found (Cutlist instance)

        Returns: error, a list of Cutlist instances
    """

    llog = logging.getLogger(__name__)

    baseurl = f"{server}getxml.php"
    if choose_cutlists_by == 0:  # by size
        size1 = fileoperations.get_size(filename)
        # siehe http://www.otrforum.com/showthread.php?t=59666 :
        size2 = (size1 + 2 * 1024 ** 3) % (4 * 1024 ** 3) - 2 * 1024 ** 3
        params = [{"ofsb": str(size1)}, {"ofsb": str(size2)}]
        # urls = [baseurl + f"?ofsb={str(size1)}",
        #         baseurl + f"?ofsb={str(size2)}"]

    else:  # by name
        root = Path(filename).stem
        extension = Path(filename).suffix
        if cutlist_mp4_as_hq and extension == ".mp4":
            root += ".HQ"

        if get_all_qualities:
            for quality in [".HQ", ".HD"]:
                if quality in root:
                    root = root.replace(quality, "")

        params = [{"name": root}]
        # urls = [baseurl + f"?name={root}"]

    cutlists = []

    # for url in urls:
    for param in params:
        try:
            # resp = urllib.request.urlopen(url)
            resp = requests.get(baseurl, params=param)
            llog.debug(f"Download from: {resp.url}".replace(server.split("/")[3], "<FRED>"))
        except TimeoutError:
            if error_cb:
                error_cb("Verbindungsprobleme")
            return "Verbindungsprobleme", None

        try:
            # noinspection PyUnresolvedReferences
            dom_cutlists = xml.dom.minidom.parseString(resp.text)
            dom_cutlists = dom_cutlists.getElementsByTagName("cutlist")

            # import xml.etree.ElementTree as Et
            # tree_cutlists = Et.fromstring(resp.text)
        except Exception as e:
            if error_cb:
                error_cb("Keine Cutlists gefunden")
            return f"Keine Cutlists gefunden ({e})", None

        # Homo ludens
        # for cutlist in range(int(tree_cutlists.attrib["count"])):
        #     c = Cutlist()
        #     for tagg in range(len(tree_cutlists[cutlist])):
        #         exec(f"c.{tree_cutlists[cutlist][tagg].tag} = "
        #              f"'{tree_cutlists[cutlist][tagg].text}'".replace('c.cuts', 'c.countcuts'))
        #     for key, value in qualities.items():
        #         if key in c.filename_original:
        #             c.quality = value
        #         ids = [cutlist.id for cutlist in cutlists]
        #         if c.id not in ids:
        #             if cutlist_found_cb:
        #                 cutlist_found_cb(c)
        #             cutlists.append(c)

        for cutlist in dom_cutlists:

            c = Cutlist()

            c.id = __read_value(cutlist, "id")
            c.rating = __read_value(cutlist, "rating")
            c.ratingcount = __read_value(cutlist, "ratingcount")
            c.author = __read_value(cutlist, "author")
            c.ratingbyauthor = __read_value(cutlist, "ratingbyauthor")
            c.actualcontent = __read_value(cutlist, "actualcontent")
            c.usercomment = __read_value(cutlist, "usercomment")
            c.countcuts = __read_value(cutlist, "cuts")
            c.filename = __read_value(cutlist, "filename")
            c.withframes = __read_value(cutlist, "withframes")
            c.withtime = __read_value(cutlist, "withtime")
            c.duration = __read_value(cutlist, "duration")
            c.errors = __read_value(cutlist, "errors")
            c.othererrordescription = __read_value(cutlist, "othererrordescription")
            c.downloadcount = __read_value(cutlist, "downloadcount")
            c.autoname = __read_value(cutlist, "autoname")
            c.filename_original = os.path.splitext(__read_value(cutlist, "name"))[0]
            for key, value in qualities.items():
                if key in c.filename_original:
                    c.quality = value

            ids = [cutlist.id for cutlist in cutlists]
            if c.id not in ids:
                if cutlist_found_cb:
                    cutlist_found_cb(c)

                cutlists.append(c)

    if len(cutlists) == 0:
        return "Keine Cutlists gefunden", None
    else:
        return None, cutlists


def __read_value(cutlist_element, node_name):
    llog = logging.getLogger(__name__)
    try:
        elements = cutlist_element.getElementsByTagName(node_name)
        for node in elements[0].childNodes:
            bad_string = node.nodeValue
            for key, value in wrong_right_chars.items():
                if key in bad_string:
                    bad_string = bad_string.replace(key, value)
            return bad_string  # hopefully not bad anymore
    except Exception as e:
        llog.debug(f"Exception: {e}")
        return ""

    llog.debug(f"Reading node {node_name} failed. Returning empty string.")
    return ""


def get_best_cutlist(cutlists):
    """ Der Algorithmus berücksichtigt die Anzahl der Wertungen.
     Hat eine Cutlist nur wenige Wertungen erhalten, wird
     ihre Bewertung etwas heruntergestuft. Existiert auch eine
     andere Cutlist, die sehr viel mehr Wertungen erhalten hat,
     wird auf diese Weise auch diese Cutlist als beste genommen.

     Beispiel: Cutlist A:
                   Wertung: 5.00,  Anzahl der Bewerter: 2
               Cutlist B:
                   Wertung: 4.88   Anzahl der Bewerter: 24

     Der Algorithmus sucht (im Gegensatz zu cutlist.at) Cutlist B
     als beste heraus.
     Sind keine Benutzerwertungen vorhanden, wird nach der Autoren-
     bewertung sortiert.

    """

    best_cutlists = {}

    for cutlist in cutlists:
        if cutlist.rating:
            if int(cutlist.ratingcount) > 6:
                rating = float(cutlist.rating)
            else:
                rating = float(cutlist.rating) - (6 - int(cutlist.ratingcount)) * 0.05

            best_cutlists[cutlist] = rating

    if best_cutlists:
        items = best_cutlists.items()
    else:
        items = [(cutlist, cutlist.ratingbyauthor) for cutlist in cutlists]

    sorted(items, key=lambda x: x[1])

    return next(iter(items))[0]
