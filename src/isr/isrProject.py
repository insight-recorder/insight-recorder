#!/usr/bin/env python
#
# Script to record webcam and screencast
#
# Copyright 2012 Intel Corporation.
#
# Author: Michael Wood <michael.g.wood@intel.com>
#
# This program is free software; you can redistribute it and/or modify it
# under the terms and conditions of the GNU Lesser General Public License,
# version 2.1, as published by the Free Software Foundation.
#
# This program is distributed in the hope it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program; if not, see <http://www.gnu.org/licenses>
#


# Util to save and load project config

import ConfigParser

class isrProject:
    def __init__ (self, projectFile, projectName):
        self.projectFile = projectFile
        self.projectName = projectName

    def populate (self, isrMain, cols):

        parser = ConfigParser.RawConfigParser ()
        out = parser.read (self.projectFile)
        isNewFile = len (out)

        listStore = isrMain.listStore
        i = 0

        if isNewFile <= 0:
            print ("Err: empty project!!11")
            return

        self.projectName = parser.get ("project", "name")

        #eeww
        isrMain.projectLabel.set_text ("Project: "+self.projectName)

        try:
            isrMain.projectDir = parser.get ("project", "dir")
        except ConfigParser.NoOptionError:
            print ("Err: project directory key/value not found in config")
            return

        isrMain.enable_buttons (True)

        recording = "recording-"+str(i)

        while (parser.has_section (recording) == True):

            try:
                title = parser.get (recording, "title")
            except ConfigParser.NoOptionError:
                title = "Unknown"

            try:
                date = parser.get (recording, "date")
            except ConfigParser.NoOptionError:
                print ("Err: project config does not contain date field/value")
                return

            try:
                duration = parser.getint (recording, "duration")
            except ConfigParser.NoOptionError:
                duration = 0

            listStore.append ([title,
                               date,
                               duration,
                               False])

            i += 1

            recording = "recording-"+str(i)


    def dump (self, isrMain, cols):

        parser = ConfigParser.RawConfigParser ()

        listStore = isrMain.listStore

        listItr = listStore.get_iter_first ()
        i = 0

        parser.add_section ("project")
        parser.set ("project", "name", self.projectName)
        parser.set ("project", "dir", isrMain.projectDir)

        while (listItr != None):
            recording = "recording-"+str (i)

            #e.g. [recording-0]
            if parser.has_section (recording) == False:
                parser.add_section (recording)

            # e.g. title=bob
            parser.set (recording, "title",
                             listStore.get_value (listItr, cols.TITLE))

            parser.set (recording, "date",
                             listStore.get_value (listItr, cols.DATE))

            parser.set (recording, "duration",
                             listStore.get_value (listItr, cols.DURATION))

            listItr = listStore.iter_next (listItr)
            i += 1


        with open (self.projectFile, "w") as prjob:
            prjob.write ("")
            parser.write (prjob)

        print ("Info: dump done for "+self.projectFile)
