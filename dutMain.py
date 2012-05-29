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


from gi.repository import Gtk
from gi.repository import GLib
#for screen res
from gi.repository import Gdk

from datetime import datetime
#for fun
import time

import subprocess
import rmdWebcamRecord
import rmdMux
import dutNewRecording


class Recordmydesktop3:
    def __init__(self):

        self.webcam = None
        self.mux = None
        self.rmd = None
        self.projectDir = None
        self.projectFile = None
        self.projectLabel = None
        self.listStore = None
        self.spinner = None
        self.buttonBox = None
        self.screen = None
        self.configFile = GLib.KeyFile()
        self.encodeButton = None
        self.recordButton = None
        self.mainWindow = None

        self.icon = Gtk.StatusIcon (visible=False)
        self.icon.set_from_stock (Gtk.STOCK_MEDIA_RECORD)
        self.icon.connect ("activate", self.stop_record)

        self.mainWindow = Gtk.Window(title="Dawati user testing tool",
                                     resizable=False,
                                     icon_name=Gtk.STOCK_MEDIA_RECORD)
        self.mainWindow.connect("destroy", self.on_mainWindow_destroy)

        boxLayout = Gtk.VBox (spacing=5, homogeneous=False)

        menu = Gtk.Toolbar ()
        menu.get_style_context ().add_class (Gtk.STYLE_CLASS_PRIMARY_TOOLBAR)

        fileNew = Gtk.ToolButton.new_from_stock ("gtk-new")
        fileNew.connect ("clicked", self.new_folder_chooser, self.mainWindow)

        fileOpen = Gtk.ToolButton.new_from_stock ("gtk-open")
        fileOpen.connect ("clicked", self.open_file_chooser, self.mainWindow)

        menu.insert (fileNew, 0)
        menu.insert (fileOpen, 1)

        self.listStore = Gtk.ListStore (str, str, int, bool, bool)
#dummy data str, str, str, bool, bool

        self.listStore.append (["Bob and dog", "wefeff3", 5, True, False])
        self.listStore.append (["Bowoifjowejfwoiefjwoefjwoefjoib and dog1", "foiesjwf", 6, False, False])
        self.listStore.append (["Bob and dog2", "wefwef", 7, False, False])


        dateLabel = Gtk.Label ("Date")
        durationLabel = Gtk.Label ("Duration")

        self.projectLabel = Gtk.Label (halign=Gtk.Align.START)
        self.projectLabel.set_markup ("<span style='italic'>No project open</span>")

        self.recordButton = Gtk.Button (label="Create recording")
        self.recordButton.connect("clicked", self.new_record_button_clicked_cb)

        self.encodeButton = Gtk.Button (label="Export", tooltip_text="Encode selected sessions")
        self.encodeButton.connect("clicked", self.encode_button_clicked_cb)

        recordingDeleteButton = Gtk.Button (label="Delete", tooltip_text="Delete selected sessions")

        self.spinner = Gtk.Spinner ()

        recordingsView = Gtk.TreeView (model=self.listStore)
        recordingsView.connect ("row-activated", self.row_activated)

#TODO use some kind of ENUM instead of ints for the index of the cols

        # Column Recording Name
        recordingTitle = Gtk.CellRendererProgress ()
        col1 = Gtk.TreeViewColumn ("Recording name", recordingTitle, text=0)
        recordingsView.append_column (col1)

        # Column Date
        recordingDate = Gtk.CellRendererText ()
        col2 = Gtk.TreeViewColumn ("Date", recordingDate, text=1)
        recordingsView.append_column (col2)

        # Column Duration
        recordingDuration = Gtk.CellRendererText (xalign=0.5)
        col3 = Gtk.TreeViewColumn ("Duration", recordingDuration, text=2)
        recordingsView.append_column (col3)

        # Column for export
        recordingExport = Gtk.CellRendererToggle (xalign=0)
        recordingExport.connect ("toggled", self.export_toggled)
        col4 = Gtk.TreeViewColumn ("Export", recordingExport, active=3)
        recordingsView.append_column (col4)
        col4.connect ("notify::x-offset", self.buttons_x_offset)

        # Column for delete
        recordingDelete = Gtk.CellRendererToggle (xalign=0)
        recordingDelete.connect ("toggled", self.delete_toggled)
        col5 = Gtk.TreeViewColumn ("Delete", recordingDelete, active=4)
        recordingsView.append_column (col5)

        # Box for new recording, export and delete buttons
        self.buttonBox = Gtk.HBox (spacing=5, homogeneous=False)
        self.buttonBox.pack_start (self.recordButton, False, False, 3)
        self.buttonBox.pack_start (self.encodeButton, False, False, 3)
        self.buttonBox.pack_start (recordingDeleteButton, False, False, 3)

        # Box for rest of the UI which doesn't span the whole window
        innerVbox = Gtk.VBox (spacing=5,
                              homogeneous=False,
                              margin_left=5,
                              margin_right=5)

        innerVbox.pack_start (self.projectLabel, False, False, 3)
        innerVbox.pack_start (recordingsView, False, False, 3)
        innerVbox.pack_start (self.buttonBox, False, False, 3)

        # Main container in window
        boxLayout.pack_start (menu, False, False, 3)
        boxLayout.pack_start (innerVbox, False, False, 3)

        self.mainWindow.add(boxLayout)


        self.mainWindow.show_all()
        self.spinner.hide ()

        self.screen = Gdk.get_default_root_window ().get_display ().get_screen (0)
#svcreen=self.mainWindow.get_screen ()

    def row_activated (col, tree, path, self):
        print ("row activated: "+col.listStore[path][0])

    def buttons_x_offset (self, col, cat):
        (a,b) = self.recordButton.get_preferred_width ()
        #margin from the edge of the record button minus the padding
        self.encodeButton.set_margin_left (col.get_x_offset ()-a-10)

    def export_toggled (self, widget, path):
        self.listStore[path][3] = not self.listStore[path][3]
        self.listStore[path][4] = False
        print ("export doggled")

    def delete_toggled (self, widget, path):
        self.listStore[path][4] = not self.listStore[path][4]
        self.listStore[path][3] = False
        print ("delete toggled")

    def open_file_chooser (self, menuitem, window):
        dialog = Gtk.FileChooserDialog ("Open File",
                                        window,
                                        Gtk.FileChooserAction.OPEN,
                                        (Gtk.STOCK_CANCEL,
                                        Gtk.ResponseType.CANCEL,
                                        Gtk.STOCK_OPEN, Gtk.ResponseType.OK))
        response = dialog.run ()

        if response == Gtk.ResponseType.OK:
            self.projectFile = dialog.get_filename ()
            error = None
            GLib.KeyFile.load_from_file (self.configFile, self.projectFile, 0,
                                         error)
            if (error):
                print ("Error loading config file")


        dialog.destroy()


    def new_folder_chooser (self, menuitem, window):
        dialog = Gtk.FileChooserDialog ("New project",
                                        window,
                                        Gtk.FileChooserAction.CREATE_FOLDER,
                                        (Gtk.STOCK_CANCEL,
                                        Gtk.ResponseType.CANCEL,
                                        Gtk.STOCK_SAVE, Gtk.ResponseType.OK))

        response = dialog.run ()

        if response == Gtk.ResponseType.OK:
            self.projectDir = dialog.get_filename ()
            projectName = GLib.filename_display_basename (self.projectDir)
            self.projectFile = "/"+projectName+".ini"

            self.projectLabel.set_text (projectName)

        dialog.destroy()

    def create_new_dir (self):
        self.projectDir = GLib.get_user_special_dir (GLib.USER_DIRECTORY_VIDEOS)
        self.projectDir += "/User-testing/"
        self.projectDir += self.projectLabel.get_text ()
        self.projectDir += datetime.today().strftime("-%d%m%y-at-%H%M")
        GLib.mkdir_with_parents (self.projectDir, 0755)
        print ("Saving to" + self.projectDir)

    def on_mainWindow_destroy(self, widget):
        Gtk.main_quit()


    def encode_button_clicked_cb (self, button):
          self.mux = rmdMux.Muxer(self.projectDir)
          self.mux.record (1)
          button.set_label ("Encoding")

    def new_record_button_clicked_cb (self, button):
         newRecording = dutNewRecording.NewRecording (self.configFile, self.mainWindow)
         recordingInfo = newRecording.get_new_recording ()
         if recordingInfo:
             self.listStore.append ([recordingInfo[0],
                                     datetime.today().strftime ("%d/%m/%y %H:%M"),
                                     0, False, False])
             self.mainWindow.iconify ()
             self.icon.set_visible (True)


             self.create_new_dir ()
             self.webcam = rmdWebcamRecord.Webcam(self.projectDir)

             self.webcam.record (1)
          #Wait for the camera to initilise
          #this should run when the webcam gst pipline is running as there is a delay where the webcam is starting
             self.rmd = subprocess.Popen (["ffmpeg",
                                           "-r", "30",
                                           "-s", "1280x1024",
                                           "-f", "x11grab",
                                           "-i", ":0.0",
                                           "-vcodec", "libx264",
                                           self.projectDir+"/screencast-rmd.avi"])

    def stop_record (self, button):
        self.webcam.record (0)
        self.rmd.terminate ()
        self.spinner.stop ()
        self.spinner.hide ()
        self.webcam = None

        #Show the window again
        self.mainWindow.deiconify ()
        self.mainWindow.present ()
        self.icon.set_visible (False)


if __name__ == "__main__":
    Recordmydesktop3()
    Gtk.main()
