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


class dutProject:
    def __init__ (self, projectFile, projectName):
        self.projectFile = projectFile
        self.projectName = projectName
        self.parser = ConfigParser.RawConfigParser ()
        out = self.parser.read (projectFile)
        self.isNewFile = len (out)

    def populate (self, dutMain, cols):
        listStore = dutMain.listStore
        i = 0

#       reference  Gtk.ListStore (str, str, float, bool, bool, int)
#                  TITLE, DATE, DURATION, EXPORT, DELETE, PROGRESS

        if self.isNewFile <= 0:
            print ("empty project!!")
            return

        #eeww
        dutMain.projectLabel.set_text ("Project: "+self.parser.get ("project", "name"))

        recording = "recording-"+str(i)

        while (self.parser.has_section (recording) == True):

            listStore.append ([self.parser.get (recording, "title"),
                              self.parser.get (recording, "date"),
                              self.parser.getint (recording, "duration"),
                              False,
                              False,
                              self.parser.getint (recording, "progress")])
            i += 1
            recording = "recording-"+str(i)


    def dump (self, dutMain, cols):
        listStore = dutMain.listStore

        listItr = listStore.get_iter_first ()
        i = 0

        if self.parser.has_section ("project") == False:
            self.parser.add_section ("project")

        self.parser.set ("project", "name", self.projectName)

        while (listItr != None):
            recording = "recording-"+str (i)

            #e.g. [recording-0]
            if self.parser.has_section (recording) == False:
                self.parser.add_section (recording)

            # e.g. title=bob
            self.parser.set (recording, "title",
                             listStore.get_value (listItr, cols.TITLE))

            self.parser.set (recording, "date",
                             listStore.get_value (listItr, cols.DATE))

            self.parser.set (recording, "duration",
                             listStore.get_value (listItr, cols.DURATION))

            self.parser.set (recording, "progress",
                             listStore.get_value (listItr, cols.PROGRESS))

            listItr = listStore.iter_next (listItr)

            i += 1


        with open (self.projectFile, "wb") as prjob:
            self.parser.write (prjob)

        print ("dump done for "+self.projectFile)












