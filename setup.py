#!/usr/bin/env python
# -*- coding: utf-8 -*-
### BEGIN LICENSE
# Copyright (C) 2010 Benjamin Elbers <elbersb@gmail.com>
#This program is free software: you can redistribute it and/or modify it 
#under the terms of the GNU General Public License version 3, as published 
#by the Free Software Foundation.
#
#This program is distributed in the hope that it will be useful, but 
#WITHOUT ANY WARRANTY; without even the implied warranties of 
#MERCHANTABILITY, SATISFACTORY QUALITY, or FITNESS FOR A PARTICULAR 
#PURPOSE.  See the GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License along 
#with this program.  If not, see <http://www.gnu.org/licenses/>.
### END LICENSE

###################### DO NOT TOUCH THIS (HEAD TO THE SECOND PART) ######################
import sys

try:
    import DistUtilsExtra.auto
except ImportError:
    print('To build otrverwaltung3p you need https://launchpad.net/python-distutils-extra', file=sys.stderr)
    sys.exit(1)

assert DistUtilsExtra.auto.__version__ >= '2.10', 'needs DistUtilsExtra.auto >= 2.10'
import os
import tarfile


def update_data_path(prefix, oldvalue=None):

    try:
        fin = open('otrverwaltung3p/path.py', 'r')
        fout = open(fin.name + '.new', 'w')

        for line in fin:            
            fields = line.split(' = ') # Separate variable from value
            if fields[0] == 'data_dir':
                # update to prefix, store oldvalue
                if not oldvalue:
                    oldvalue = fields[1]
                    line = "%s = '%s'\n" % (fields[0], prefix)
                else: # restore oldvalue
                    line = "%s = %s" % (fields[0], oldvalue)
            fout.write(line)

        fout.flush()
        fout.close()
        fin.close()
        os.rename(fout.name, fin.name)
    except (OSError, IOError) as e:
        print ("ERROR: Can't find otrverwaltung3p/path.py")
        sys.exit(1)
    return oldvalue


def update_desktop_file(datadir):

    try:
        fin = open('otrverwaltung.desktop.in', 'r')
        fout = open(fin.name + '.new', 'w')

        for line in fin:            
            if 'Icon=' in line:
                line = "Icon=%s\n" % (datadir + 'media/icon.png')
            fout.write(line)
        fout.flush()
        fout.close()
        fin.close()
        os.rename(fout.name, fin.name)
    except (OSError, IOError) as e:
        print ("ERROR: Can't find otrverwaltung.desktop.in")
        sys.exit(1)

def pack_tools_dir():

    if os.path.isfile('data/tools.tar.bz2'):
        os.remove('data/tools.tar.bz2')
        
    def reset(tarinfo):
        tarinfo.uid = tarinfo.gid = 0
        tarinfo.uname = tarinfo.gname = "root"
        return tarinfo
        
        tar = tarfile.open("data/tools.tar.bz2", "w:bz2")
        tar.add("data/tools", filter=reset)
        tar.close()
    
class InstallAndUpdateDataDirectory(DistUtilsExtra.auto.install_auto):
    def run(self):
        if self.root or self.home:
            print("WARNING: You don't use a standard --prefix installation. You can " \
            "ignore this warning if you are packaging and use --prefix.")
        if self.prefix:
            pre = self.prefix
        else:
            pre = site.USER_BASE
        previous_value = update_data_path(self.prefix + '/share/otrverwaltung3p/')
        update_desktop_file(self.prefix + '/share/otrverwaltung3p/')
        pack_tools_dir()
        DistUtilsExtra.auto.install_auto.run(self)
        update_data_path(self.prefix, previous_value)


        
##################################################################################
###################### YOU SHOULD MODIFY ONLY WHAT IS BELOW ######################
##################################################################################

DistUtilsExtra.auto.setup(
    name='otrverwaltung3p',
    version=open('data/VERSION', 'r').read().strip(),
    license='GPL-3',
    author='Benjamin Elbers',
    author_email='noone@nowhere.org',
    description='Dateien von onlinetvrecorder.com verwalten',
    long_description='Dateien von onlinetvrecorder.com verwalten: Schneiden, Schnitte betrachten, Cutlists bewerten...',
    url='https://github.com/EinApfelBaum/otr-verwaltung3p',
    cmdclass={'install': InstallAndUpdateDataDirectory}  
    )
