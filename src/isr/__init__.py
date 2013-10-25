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
    print (_("Err: Gtk3 introspection not found try installing gir-gtk-3.0 or similar"))
    exit ()

# These are dependencies of Gtk so they should exist if Gtk does
from gi.repository import GLib
from gi.repository import Gio

try:
    import gst
except ImportError:
    print (_("Err: Python gst not found try installing python-gst or similar"))
    exit ()

import time
import shutil
from datetime import timedelta
from datetime import datetime
import sys
import signal
import gettext
import os
import locale
import isrDefs

DOMAIN="insight-recorder"

locale.bind_textdomain_codeset (DOMAIN, "UTF-8")
gettext.install (DOMAIN)
gettext.bindtextdomain (DOMAIN, isrDefs.PREFIX + '/share/locale')
gettext.textdomain (DOMAIN)
from gettext import gettext as _

import isrRecord
import isrMux
import isrNewRecording
import isrProject
import isrIndicator


class m:
    TITLE, DATE, DURATION, DELETE  = range (4)

class isrMain:
    def __init__(self):

        self.primary = None
        self.secondary = None
        self.mux = None

        self.projectDir = None
        self.projectLabel = None
        self.listStore = None
        self.buttonBox = None
        self.screen = None
        self.projectConfig = None
        self.recordButton = None
        self.mainWindow = None
        self.updateTimer = None
        self.listItr = None
        self.currentRecording = None
        self.isRecording = False
        self.stopRecordButton = None
        self.recordingText = _("Recording in progress")

        self.check_gst_elements_available ()

        signal.signal(signal.SIGINT, self.close)

        # UI declaration
        self.icon = Gtk.StatusIcon (visible=False)
        self.icon.set_from_stock (Gtk.STOCK_MEDIA_RECORD)
        self.icon.connect ("activate", self.stop_record)

        self.mainWindow = Gtk.Window(title="Insight recorder",
                                     resizable=False,
                                     icon_name=Gtk.STOCK_MEDIA_RECORD)
        self.mainWindow.connect("destroy", self.on_mainWindow_destroy)

        self.indicator = isrIndicator.Indicator (self)

        outterBoxLayout = Gtk.VBox (homogeneous=False)

        menu = Gtk.Toolbar ()
        menu.get_style_context ().add_class (Gtk.STYLE_CLASS_PRIMARY_TOOLBAR)

        fileNew = Gtk.ToolButton.new_from_stock ("gtk-new")
        fileNew.set_label (_("New project"))
        fileNew.set_tooltip_text (_("Create a new project"))
        fileNew.connect ("clicked", self.new_folder_chooser, self.mainWindow)

        fileOpen = Gtk.ToolButton.new_from_stock ("gtk-open")
        fileOpen.set_label (_("Open project"))
        fileOpen.connect ("clicked", self.open_file_chooser, self.mainWindow)
        fileOpen.set_tooltip_text (_("Open an existing project"))

        menu.insert (fileNew, 0)
        menu.insert (fileOpen, 1)

        #InfoBar
        self.recordingInfoBar = Gtk.InfoBar ()
        self.stopRecordButton = self.recordingInfoBar.add_button (_("Stop recording"), Gtk.ResponseType.OK)
        self.recordingInfoBar.set_message_type (Gtk.MessageType.INFO)
        self.recordingInfoBar.connect ("response", self.stop_record)
        recordingInfoBarArea = self.recordingInfoBar.get_content_area ()
        self.infoBarLabel = Gtk.Label (self.recordingText)
        recordingInfoBarArea.pack_start (self.infoBarLabel,
                                         False, False, 3)
        self.eosSpinner = Gtk.Spinner ()
        self.recordingInfoBar.get_action_area ().pack_start (self.eosSpinner,
                                                             False, False, 3)
        self.eosSpinner.hide ()

        self.projectLabel = Gtk.Label (halign=Gtk.Align.START)
        self.projectLabel.set_markup ("<span style='italic'>"+_("No project open")+"</span>")

        self.recordButton = Gtk.Button (label=_("Create recording"),
                                        tooltip_text=_("Create a new recording"),
                                        sensitive=False)
        self.recordButton.connect("clicked", self.new_record_button_clicked_cb)


        self.recordingDeleteButton = Gtk.Button (label=_("Delete"),
                                            tooltip_text=_("Delete selected sessions"),
                                            sensitive=False)

        self.recordingDeleteButton.connect("clicked", self.delete_button_clicked_cb)

        self.listStore = Gtk.ListStore (str, str, int, bool)


        recordingsView = Gtk.TreeView (model=self.listStore)
        recordingsView.connect ("row-activated", self.row_activated)

        # Column Recording Name
        recordingTitle = Gtk.CellRendererText (xalign=0)
        col1 = Gtk.TreeViewColumn (_("Recording name"),
                                   recordingTitle,
                                   text=m.TITLE)
        recordingsView.append_column (col1)

        # Column Date
        recordingDate = Gtk.CellRendererText ()
        col2 = Gtk.TreeViewColumn (_("Date"), recordingDate, text=m.DATE)
        recordingsView.append_column (col2)

        # Column Duration
        recordingDuration = Gtk.CellRendererText (xalign=0)
        col3 = Gtk.TreeViewColumn (_("Duration"), recordingDuration,
                                   text=m.DURATION)
        recordingsView.append_column (col3)
        col3.set_cell_data_func(recordingDuration,
                                lambda column, cell, model, iter, data:
                                cell.set_property('text',
                                                  str(timedelta (seconds=model.get_value (iter, m.DURATION))))

                               )
        # Column for delete
        recordingDelete = Gtk.CellRendererToggle (xalign=0.5)
        recordingDelete.connect ("toggled", self.delete_toggled)
        col5 = Gtk.TreeViewColumn ("Delete", recordingDelete, active=m.DELETE)
        recordingsView.append_column (col5)
        col5.connect ("notify::x-offset", self.buttons_x_offset)

        # Box for new recording, and delete buttons
        self.buttonBox = Gtk.HBox (spacing=5, homogeneous=False)
        self.buttonBox.pack_start (self.recordButton, False, False, 3)
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
        outterBoxLayout.pack_start (menu, False, False, 0)
        outterBoxLayout.pack_start (self.recordingInfoBar, False, False, 0)
        outterBoxLayout.pack_start (innerVbox, False, False, 0)

        self.mainWindow.add(outterBoxLayout)
        self.mainWindow.show_all()

        self.recordingInfoBar.hide ()

        self.currentRecording = isrNewRecording.NewRecording (self.mainWindow)

        self.currentRecording.connect ("response",
                                       self.new_record_setup_done)


        # New Project dialog
        self.newProjectDialogUI = Gtk.Builder ()
        ui_file = os.path.join(os.path.dirname(__file__),
                               "isrnewprojectdialog.ui");
        self.newProjectDialogUI.add_from_file (ui_file)

        dialog = self.newProjectDialogUI.get_object ("dialog-window")
        dialog.set_transient_for (self.mainWindow)

        fileChooseButton = self.newProjectDialogUI.get_object ("filechooser-button")
        fileChooseButton.set_current_folder (GLib.get_user_special_dir (GLib.UserDirectory.DIRECTORY_VIDEOS))
        chooserEntry = self.newProjectDialogUI.get_object ("project-name")
        chooserEntry.connect ("activate",
                             lambda entry:
                              dialog.response (Gtk.ResponseType.OK))

        #argv always contains at least the execuratable as the first item
        if (len (sys.argv) > 1):
            #Rudimentary check to see if this is a file we want to open
            if (sys.argv[1].find (".isr") > 0 or sys.argv[1].find (".dut") > 0):
                self.projectConfig = isrProject.isrProject (sys.argv[1], None)
                self.projectConfig.populate (self, m)
            else:
                print ("Warning: "+sys.argv[1]+" is not a valid project file (.isr)")

    def check_gst_elements_available (self):
        message = ""

        # gst-plugins-bad
        if (gst.element_factory_find ("vp8enc") == None):
            message += _("Element vp8enc missing: this is normally found in package gstreamer-plugins-bad\n")
        # gst-plugins-good
        if (gst.element_factory_find ("videomixer") == None):
            message += _("Element videomixer missing: this is normally found in package gstreamer-plugins-good\n")

        # gst-plugins-base
        if (gst.element_factory_find ("videoscale") == None):
            message += _("Element videoscale missing: this is normally found in package gstreamer-plugins-base\n")

        # gst-alsa
        if (gst.element_factory_find ("alsasrc") == None):
            message += _("Element alsasrc missing: this is normally found in gstreamer-alsa\n")

        if (message == ""):
            return

        dialog = Gtk.MessageDialog (self.mainWindow, 0, Gtk.MessageType.ERROR,
                                   Gtk.ButtonsType.CANCEL,
                                    _("Required gstreamer element missing"))
        dialog.format_secondary_text (message)

        dialog.run ()

        dialog.destroy ()

    def notification (self, title, message):
        d = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        notify = Gio.DBusProxy.new_sync(d, 0, None,
                                        'org.freedesktop.Notifications',
                                        '/org/freedesktop/Notifications',
                                        'org.freedesktop.Notifications', None)

        notify.Notify('(susssasa{sv}i)', 'insight-recorder', 1, 'gtk-ok',
                      title, message,
                      [], {}, 10000)


    def row_activated (self, tree, path, col):
        uri = GLib.filename_to_uri (self.projectDir+"/"+self.listStore[path][m.TITLE]+self.listStore[path][m.DATE]+".webm", None)

        Gio.AppInfo.launch_default_for_uri (uri, None)


    def buttons_x_offset (self, col, cat):
        (a,b) = self.recordButton.get_preferred_width ()
        #margin from the edge of the record button minus the padding
        self.recordingDeleteButton.set_margin_left (col.get_x_offset ()-a-10)


    def delete_toggled (self, widget, path):
        self.listStore[path][m.DELETE] = not self.listStore[path][m.DELETE]
        print ("delete toggled")

    def enable_buttons (self, enable):
        self.recordButton.set_sensitive (enable)
        self.recordingDeleteButton.set_sensitive (enable)


    def open_file_chooser (self, menuitem, window):
        dialog = Gtk.FileChooserDialog (_("Open Project"),
                                        window,
                                        Gtk.FileChooserAction.OPEN,
                                        (Gtk.STOCK_CANCEL,
                                        Gtk.ResponseType.CANCEL,
                                        Gtk.STOCK_OPEN, Gtk.ResponseType.OK))
        fileFilter = Gtk.FileFilter ()
        fileFilter.set_name (_("Insight recorder projects"))
        #old project file extension
        fileFilter.add_pattern ("*.dut")
        fileFilter.add_pattern ("*.isr")

        response = dialog.run ()

        if (response == Gtk.ResponseType.OK):
            projectFile = dialog.get_filename ()
            self.projectDir = GLib.path_get_dirname (projectFile)
            self.listStore.clear ()
            self.projectConfig = isrProject.isrProject (projectFile, None)
            self.projectConfig.populate (self, m)

        dialog.destroy()


    def new_folder_chooser (self, menuitem, window):
        dialog = self.newProjectDialogUI.get_object ("dialog-window")
        response = dialog.run ()

        if (response == Gtk.ResponseType.OK):
            filechooser = self.newProjectDialogUI.get_object ("filechooser-button")
            projectNameEntry = self.newProjectDialogUI.get_object ("project-name")
            self.listStore.clear ()
            projectName = projectNameEntry.get_text ()
            self.projectDir = filechooser.get_filename ()+"/"+projectName
            GLib.mkdir_with_parents (self.projectDir, 0755)
            self.projectConfig = isrProject.isrProject (self.projectDir+"/"+projectName+".isr", projectName)

            self.projectLabel.set_text (_("Project: ")+projectName)
            self.enable_buttons (True)

        dialog.hide ()


    def on_mainWindow_destroy(self, widget):
        if self.projectConfig != None:
            self.projectConfig.dump (self, m)

        Gtk.main_quit()

    def delete_button_clicked_cb (self, button):

        listItr = self.listStore.get_iter_first ()

        while (listItr != None):

            if (self.listStore.get_value (listItr, m.DELETE) == True):

                recName = self.listStore.get_value (listItr, m.TITLE)
                recDate = self.listStore.get_value (listItr, m.DATE)

                dialog = Gtk.MessageDialog(self.mainWindow,
                                           0, Gtk.MessageType.WARNING,
                                           Gtk.ButtonsType.OK_CANCEL,
                                           _("Move '")+recName+_("' to trash?"))
                dialog.format_secondary_text(
                    _("This operation cannot be undone."))
                response = dialog.run()
                if (response == Gtk.ResponseType.OK):
                    try:
                        shutil.move (self.projectDir+"/"+recName+recDate+".webm",
                                     GLib.get_home_dir ()+"/.local/share/Trash/files/")
                    except:
                        dialog.destroy ()
                        print ("Error deleting")
                        break
                    # Remove moves the current iter and True if it has moved
                    # onto the next item false if not
                    dialog.destroy ()

                    if (self.listStore.remove (listItr) == True):
                        continue
                    else:
                        listItr = None
                        continue

                dialog.destroy ()

            listItr = self.listStore.iter_next (listItr)

    # If filename exists append i number on the end
    def make_unique_file (self, filename):

        stat = None
        i = 0
        append = ""

        # Give up after 99999 tries to find a unique file
        while (i < 99999):
            stat = None
            try:
                stat = os.stat (filename+append)
                i += 1
            except OSError:
                # "file not found"
                break

        if (stat):
            append = str (i)

        filename += append

        return filename

    def new_record_setup_done (self, dialog, response):

        self.currentRecording.close ()

        if (response != Gtk.ResponseType.ACCEPT):
            return

        dateStamp = datetime.today().strftime ("%d-%m-at-%Hh%Mm")
        currentRecording = self.currentRecording

        finalFile = GLib.build_filenamev ([self.projectDir,
                                           currentRecording.recordingTitle+dateStamp+".webm"])

        finalFile = self.make_unique_file (finalFile)

        self.listItr = self.listStore.append ([currentRecording.recordingTitle,
                                               dateStamp,
                                               0, #duration
                                               False])

        self.mainWindow.iconify ()
        self.icon.set_visible (True)

        self.primary = isrRecord.Record (finalFile,
                                         currentRecording.player,
                                         self.record_stopped_cb)

        if (self.primary is not None):
            self.primary.record (1)
            self.isRecording += 1
            self.stopRecordButton.show ()
            self.recordingInfoBar.show ()
            self.eosSpinner.hide ()
            self.enable_buttons (False)

    def new_record_button_clicked_cb (self, button):
         # Open dialog for recording settings
         self.currentRecording.open ()

    def record_stopped_cb (self):
        self.isRecording -= 1

        if (self.isRecording == 0):
            duration = self.primary.get_duration ()
            #duration to seconds
            duration = round ((duration*0.000000001))

            self.listStore.set_value (self.listItr, m.DURATION, int (duration))

            self.primary = None
            self.secondary = None

            self.eosSpinner.hide ()
            self.eosSpinner.stop ();
            self.recordingInfoBar.hide ()
            self.infoBarLabel.set_text (self.recordingText)
            self.enable_buttons (True)


    def stop_record (self, *remains):
        self.stopRecordButton.hide ();
        self.infoBarLabel.set_text (_("Processing ..."))
        self.eosSpinner.show ()
        self.eosSpinner.start ();

        self.primary.record (0)
        if (self.secondary is not None):
            self.secondary.record (0)

        #Show the window again
        self.mainWindow.deiconify ()
        self.mainWindow.present ()
        #BUG in gtk+ 3.8.0
        #https://bugzilla.gnome.org/show_bug.cgi?id=696882
        #self.icon.set_visible (False)

    def close (self, signal, frame):
        sys.exit (0)

def main ():
    print ("Insight Recorder version: " + isrDefs.VERSION)
    isrMain()
    Gtk.main()
