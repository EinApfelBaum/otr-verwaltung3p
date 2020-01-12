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

import base64


def get_comp_data_dx50():
    """ Encoder: MPEG4, FourCC: DX50 """

    return '2935,"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"'


def get_comp_data_h264_43():
    """ Encoder: H.264; FourCC: H.264, CQ 22, Darstellungsverhältnis 4:3
        von monarc99 """

    return '2992,"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"'


def get_comp_data_h264_169():
    """ Encoder: H.264; FourCC: H.264, CQ22, Darstellungsverhältnis 16:9
        von monarc99 """

    return '2994,"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"'


def get_comp_data_hd_43():
    """ """

    return '2992,"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"'


def get_comp_data_hd_169():
    """ """

    return '2994,"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"'


def get_comp_data_x264vfw_dynamic(sar, x264vfw_config_string):
    """ """

    x264vfw_config_string = '--sar ' + sar + " " + x264vfw_config_string
    fillchars = len(x264vfw_config_string) % 3
    if fillchars != 0:
        x264vfw_config_string = x264vfw_config_string.ljust(len(x264vfw_config_string) + (3 - fillchars), ' ')

    part1 = '4720,"AgAAAAUAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACAAAAFwAAAOYAAAAgAwAAAQAAAAAAAAAAAAAAAQAAAC5ceDI2NC5zdGF0cwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABAAAAAQAAAAIAAAABAAAAAQAAAAAAAAAAAAAA'
    part2 = x264vfw_config_string
    encoded_string = part1 + part2
    return encoded_string.ljust(6300, 'A') + '=="'


def get_comp_data_komisar_dynamic(sar, komisar_config_string):
    """ """

    komisar_config_string = '--sar ' + sar + " " + komisar_config_string
    fillchars = len(komisar_config_string) % 3
    if fillchars != 0:
        komisar_config_string = komisar_config_string.ljust(len(komisar_config_string) + (3 - fillchars), ' ')

    part1 = '9052,"AQQAAAIAAAAXAAAA5gAAACADAAABAAAAAAAAAAAAAAABAAAALlx4MjY0LnN0YXRzAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAg'
    part2 = base64.b64encode(komisar_config_string)
    part3 = 'EAAAABAAAAAgAAAAEAAAABAAAAAAAAAAAAAABIMjY0AAAAAAEAAAAAAAAAAQAAAAEAAAABAAAAAQAAAAEAAAABAAAAAAAAAAEAAAABAAAAAwAAAAEAAAACAAAAEAAAAAcAAAABAAAAAACAPwAAAAD6AAAAKAAAAAIAAAAAAAAAAQAAAAAAAAABAAAAAgAAAAEAAAABAAAAAAAAAAAAAAAAAAAAAQAAAAEAAAAAAAAAAQAAAAsAAAAVAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAWgAAAAoAAAAzAAAABAAAADMzsz9mZqY/AAAAAJqZGT8AAKBBAAAAPwAAgD8BAAAAAACAPwAAAAABAAAAAAAAAAAAAAAFAAAAAAAAAAIAAAACAAAAAgAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=="'
    encoded_string = part1 + part2
    return encoded_string.ljust(5868, 'A') + part3