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


try:
    from gi.repository import Gtk
except ImportError:
    print ("Gtk3 introspection not found")
    exit ()

# These are dependencies of Gtk so they should exist if Gtk does
from gi.repository import GLib
from gi.repository import Gdk

try:
    import gst
except ImportError:
    print ("Python gst not found try installing python-gst0.10 or similar")
    exit ()

from datetime import datetime
import time

import subprocess
import dutWebcamRecord
import dutMux
import dutNewRecording

class m:
    TITLE, DATE, DURATION, EXPORT, DELETE, PROGRESS = range (6)

class dutMain:
    def __init__(self):

        self.webcam = None
        self.mux = None
        self.dut = None
        self.projectDir = None
        self.projectFile = None
        self.projectLabel = None
        self.listStore = None
        self.buttonBox = None
        self.screen = None
        self.configFile = GLib.KeyFile()
        self.encodeButton = None
        self.recordButton = None
        self.mainWindow = None
        self.updateTimer = None
        self.encodeQueue = []
        self.listItr = None

        self.icon = Gtk.StatusIcon (visible=False)
        self.icon.set_from_stock (Gtk.STOCK_MEDIA_RECORD)
        self.icon.connect ("activate", self.stop_record)

        self.mainWindow = Gtk.Window(title="Dawati user testing tool",
                                     resizable=False,
                                     icon_name=Gtk.STOCK_MEDIA_RECORD)
        self.mainWindow.connect("destroy", self.on_mainWindow_destroy)

        outterBoxLayout = Gtk.VBox (spacing=5, homogeneous=False)

        menu = Gtk.Toolbar ()
        menu.get_style_context ().add_class (Gtk.STYLE_CLASS_PRIMARY_TOOLBAR)

        fileNew = Gtk.ToolButton.new_from_stock ("gtk-new")
        fileNew.connect ("clicked", self.new_folder_chooser, self.mainWindow)

        fileOpen = Gtk.ToolButton.new_from_stock ("gtk-open")
        fileOpen.connect ("clicked", self.open_file_chooser, self.mainWindow)

        menu.insert (fileNew, 0)
        menu.insert (fileOpen, 1)

        dateLabel = Gtk.Label ("Date")
        durationLabel = Gtk.Label ("Duration")

        self.projectLabel = Gtk.Label (halign=Gtk.Align.START)
        self.projectLabel.set_markup ("<span style='italic'>No project open</span>")

        self.recordButton = Gtk.Button (label="Create recording",
                                        sensitive=False)
        self.recordButton.connect("clicked", self.new_record_button_clicked_cb)

        self.encodeButton = Gtk.Button (label="Export",
                                        tooltip_text="Encode selected sessions",
                                        sensitive=False)
        self.encodeButton.connect("clicked", self.encode_button_clicked_cb)

        self.recordingDeleteButton = Gtk.Button (label="Delete",
                                            tooltip_text="Delete selected sessions",
                                            sensitive=False)


        self.listStore = Gtk.ListStore (str, str, int, bool, bool, int)


        recordingsView = Gtk.TreeView (model=self.listStore)
        recordingsView.connect ("row-activated", self.row_activated)

        # Column Recording Name
        recordingTitle = Gtk.CellRendererProgress ()
        col1 = Gtk.TreeViewColumn ("Recording name",
                                   recordingTitle,
                                   text=m.TITLE,
                                   value=m.PROGRESS)
        recordingsView.append_column (col1)

        # Column Date
        recordingDate = Gtk.CellRendererText ()
        col2 = Gtk.TreeViewColumn ("Date", recordingDate, text=m.DATE)
        recordingsView.append_column (col2)

        # Column Duration
        recordingDuration = Gtk.CellRendererText (xalign=0.5)
        col3 = Gtk.TreeViewColumn ("Duration", recordingDuration,
                                   text=m.DURATION)
        recordingsView.append_column (col3)

        # Column for export
        recordingExport = Gtk.CellRendererToggle (xalign=0)
        recordingExport.connect ("toggled", self.export_toggled)
        col4 = Gtk.TreeViewColumn ("Export", recordingExport, active=m.EXPORT)
        recordingsView.append_column (col4)
        col4.connect ("notify::x-offset", self.buttons_x_offset)

        # Column for delete
        recordingDelete = Gtk.CellRendererToggle (xalign=0)
        recordingDelete.connect ("toggled", self.delete_toggled)
        col5 = Gtk.TreeViewColumn ("Delete", recordingDelete, active=m.DELETE)
        recordingsView.append_column (col5)

        # Box for new recording, export and delete buttons
        self.buttonBox = Gtk.HBox (spacing=5, homogeneous=False)
        self.buttonBox.pack_start (self.recordButton, False, False, 3)
        self.buttonBox.pack_start (self.encodeButton, False, False, 3)
        self.buttonBox.pack_start (self.recordingDeleteButton, False, False, 3)

        # Box for rest of the UI which doesn't span the whole window
        innerVbox = Gtk.VBox (spacing=5,
                              homogeneous=False,
                              margin_left=5,
                              margin_right=5)

        innerVbox.pack_start (self.projectLabel, False, False, 3)
        innerVbox.pack_start (recordingsView, False, False, 3)
        innerVbox.pack_start (self.buttonBox, False, False, 3)


        # Main container in window
        outterBoxLayout.pack_start (menu, False, False, 3)
        outterBoxLayout.pack_start (innerVbox, False, False, 3)

        self.mainWindow.add(outterBoxLayout)
        self.mainWindow.show_all()

        self.screen = Gdk.get_default_root_window ().get_display ().get_screen (0)

    def row_activated (self, tree, path, col):
        print ("row activated: "+self.listStore[path][m.TITLE])
        self.listStore[path][m.PROGRESS] +=10


    def buttons_x_offset (self, col, cat):
        (a,b) = self.recordButton.get_preferred_width ()
        #margin from the edge of the record button minus the padding
        self.encodeButton.set_margin_left (col.get_x_offset ()-a-10)

    def export_toggled (self, widget, path):
        self.listStore[path][m.EXPORT] = not self.listStore[path][m.EXPORT]
        #Don't allow export and delete to both be toggled
        self.listStore[path][m.DELETE] = False
        print ("export doggled")

    def delete_toggled (self, widget, path):
        self.listStore[path][m.DELETE] = not self.listStore[path][m.DELETE]
        #Don't allow export and delete to both be toggled
        self.listStore[path][m.EXPORT] = False
        print ("delete toggled")

    def enable_buttons (self):
        self.recordButton.set_sensitive (True)
        self.encodeButton.set_sensitive (True)
        self.recordingDeleteButton.set_sensitive (True)


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
            else:
                self.enable_buttons ()


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
            self.enable_buttons ()

        dialog.destroy()

    def on_mainWindow_destroy(self, widget):
        Gtk.main_quit()

    def update_progress_bar (self, encodeItem):
        percentDone = self.mux.pipe_report ()

        self.listStore.set_value (encodeItem, m.PROGRESS, percentDone)

        if percentDone == 100:
            if (self.encodeQueue != None):
                #Allow the system to settle down before starting next
                time.sleep (3)
                self.run_encode_queue ()
            return False

        return True

    def create_new_dir (self, timeStamp):
        recordingDir = self.projectDir
        recordingDir += "/"+timeStamp+"/"
        GLib.mkdir_with_parents (recordingDir, 0755)
        return recordingDir

    def run_encode_queue (self):
        encodeItem = self.encodeQueue.pop ()
        print ("run encode queue")
        #If we've already encoded this item skip it
        if (self.listStore.get_value (encodeItem, m.PROGRESS) == 100):
            return

        recordingDir = self.projectDir+"/"+self.listStore.get_value (encodeItem, m.DATE)
        self.mux = dutMux.Muxer (recordingDir)
        GLib.timeout_add (500, self.update_progress_bar, encodeItem)
        print ("run muxer")
        self.mux.record (1)


    def encode_button_clicked_cb (self, button):

        listItr = self.listStore.get_iter_first ()

        while (listItr != None):
            print (self.listStore.get_value (listItr, m.EXPORT))
            print (self.listStore.get_value (listItr, m.TITLE))

            if (self.listStore.get_value (listItr, m.EXPORT) == True):
                #Add item to queue
                print ("Add " + self.listStore.get_value (listItr,
                                                          m.TITLE) + " to enqueue")
                self.encodeQueue.append (listItr)

            listItr = self.listStore.iter_next (listItr)

        if (self.encodeQueue != None):
            self.run_encode_queue ()

    def new_record_button_clicked_cb (self, button):
         # Open dialog for recording settings
         timeStamp = datetime.today().strftime("%d-%m-%y-at-%H%M%S")

         newRecording = dutNewRecording.NewRecording (self.configFile,
                                                      self.mainWindow)

         recordingInfo = newRecording.get_new_recording_info ()

         if recordingInfo:
             self.listStore.append ([recordingInfo[0],
                                     timeStamp,
                                     0,
                                     False, False, 0])

             self.mainWindow.iconify ()
             self.icon.set_visible (True)

             # Create a dir for this recording
             recordingDir = self.create_new_dir (timeStamp)
             self.webcam = dutWebcamRecord.Webcam(recordingDir)

             self.webcam.record (1)
             #Wait for the camera to initilise
             #this should run when the webcam gst pipline is running as there is a delay where the webcam is starting
             time.sleep (1)
             self.dut = subprocess.Popen (["ffmpeg",
                                           "-r", "15",
                                           "-s", "1280x1024",
                                           "-f", "x11grab",
                                           "-i", ":0.0",
                                           "-vcodec", "libx264",
                                           recordingDir+"/screencast-dut.avi"])

    def stop_record (self, button):
        self.webcam.record (0)
        self.dut.terminate ()
        self.webcam = None

        #Show the window again
        self.mainWindow.deiconify ()
        self.mainWindow.present ()
        self.icon.set_visible (False)


if __name__ == "__main__":
    dutMain()
    Gtk.main()
