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

import gst

from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GdkX11
from gi.repository import GUdev
from gi.repository import GLib

import isrVUMeter

Gdk.threads_init ()

class mode:
    TWOCAM, SCREENCAST_PIP, SCREENCAST, WEBCAM = range (4)

class NewRecording (Gtk.Dialog):
    def __init__(self, mainWindow):

        Gtk.Dialog.__init__ (self, _("Create recording"),
                             mainWindow,
                             Gtk.DialogFlags.MODAL)

        self.player = None
        self.busSig1 = None
        self.busSig2 = None
        self.recordingTitle = None
        self.mode = None
        self.audioLevel = None
        self.opacityScale = None

        self.secondarySource = None
        self.primarySource = "Screen"

        self.primarySourceHeight = 0
        self.primarySourceWidth = 0
        self.secondarySourceHeight = 0
        self.secondarySourceWidth = 0


        self.add_button (_("Cancel"), Gtk.ResponseType.CANCEL)
        self.add_button (_("Start recording"), Gtk.ResponseType.ACCEPT)

        # UI Elements for create recording dialog
        label = Gtk.Label (label=_("Recording name:"), halign=Gtk.Align.START)
        self.entry = Gtk.Entry ()
        self.entry.connect ("activate",
                            lambda entry:
                                self.response (Gtk.ResponseType.ACCEPT))
        self.primaryCombo = Gtk.ComboBoxText ()
        self.primaryCombo.connect ("changed", self.primary_capture_changed)
        self.primaryCombo.set_title ("Primary Combo")
        self.primaryCombo.append_text ("Screen")
        primaryComboLabel = Gtk.Label (_("Primary capture:"))

        self.secondaryCombo = Gtk.ComboBoxText ()
        self.secondaryCombo.connect ("changed", self.secondary_capture_changed)
        self.secondaryCombo.set_title ("Secondary Combo")

        #Add available video4linux devices
        self.uDevClient = GUdev.Client (subsystems=["video4linux"])
        self.uDevClient.connect ("uevent", self.devices_changed)

        devices = self.uDevClient.query_by_subsystem ("video4linux")

        self.defaultSecondarySource = None

        for device in devices:
            deviceName = device.get_name ()

            if self.defaultSecondarySource == None:
                self.defaultSecondarySource = "/dev/"+deviceName

            self.secondaryCombo.append_text (deviceName)
            self.primaryCombo.append_text (deviceName)

        self.secondaryCombo.append_text ("None");
        secondaryComboLabel = Gtk.Label (_("Secondary capture:"))

        devicesBox = Gtk.HBox ()
        devicesBox.pack_start (primaryComboLabel, False, False, 3)
        devicesBox.pack_start (self.primaryCombo, False, False, 3)
        self.samePrimaryAlert = Gtk.Image.new_from_icon_name ("dialog-warning",
                                                Gtk.IconSize.SMALL_TOOLBAR)
        devicesBox.pack_start (self.samePrimaryAlert, False, False, 3)

        devicesBox.pack_start (secondaryComboLabel, False, False, 3)
        devicesBox.pack_start (self.secondaryCombo, False, False, 3)

        self.sameSecondaryAlert = Gtk.Image.new_from_icon_name ("dialog-warning",
                                                Gtk.IconSize.SMALL_TOOLBAR)
        devicesBox.pack_start (self.sameSecondaryAlert, False, False, 3)

        self.playerWindow = Gtk.DrawingArea ()
        self.playerWindow.set_double_buffered (False)
        self.playerWindow.set_size_request (600, 300)

        recordingNameBox = Gtk.VBox ()
        recordingNameBox.set_spacing (8)
        recordingNameBox.pack_start (label, False, False, 0)
        recordingNameBox.pack_start (self.entry, False, False, 0)

        opacityScaleLabel = Gtk.Label (_("Opacity for secondary capture:"))
        opacityScaleLabel.set_halign (Gtk.Align.START)
        self.opacityScale = Gtk.HScale ()
        self.opacityScale.set_range (0.2, 1.0)
        self.opacityScale.set_value (1.0)
        self.opacityScale.set_inverted (True)
        self.opacityScale.set_size_request (270, -1)
        self.opacityScale.set_draw_value (False)
        self.opacityScale.set_halign (Gtk.Align.START)
        self.opacityScale.set_valign (Gtk.Align.CENTER)
        self.opacityScale.connect ("value-changed",
                                   self.alpha_adjust_changed)

        audioLabel = Gtk.Label (_("Audio level:"))
        audioLabel.set_halign (Gtk.Align.START)
        audioButton = Gtk.ToolButton ()
        audioButton.set_tooltip_text ( _("Audio settings"))
        audioButton.set_icon_name ("audio-input-microphone")
        audioButton.connect ("clicked", self.launch_audio_settings)
        audioButton.set_halign (Gtk.Align.END)
        audioButton.set_valign (Gtk.Align.CENTER)

        self.audioLevel = isrVUMeter.VUMeter ()
        self.audioLevel.set_valign (Gtk.Align.CENTER)
        self.audioLevel.set_halign (Gtk.Align.START)

        # This is so readable!
        # attach (widget, left, top, width span, height span)
        settingsGrid = Gtk.Grid ()
        settingsGrid.set_column_spacing (3)
        settingsGrid.attach (opacityScaleLabel, 0, 0, 1, 1)
        settingsGrid.attach (self.opacityScale, 0 , 1, 1 ,1)
        settingsGrid.attach (audioLabel, 1, 0 , 1, 1)
        settingsGrid.attach (self.audioLevel, 1, 1 , 1, 1)
        settingsGrid.attach (audioButton, 2, 1 , 1, 1)

        contentArea = self.get_content_area ()
        contentArea.set_spacing (4)
        contentArea.set_margin_top (8)
        contentArea.add (recordingNameBox)
        contentArea.add (devicesBox)
        contentArea.add (self.playerWindow)
        contentArea.add (settingsGrid)

    def alpha_adjust_changed (self, adjustment):
        if (self.player):
            videoMixer = self.player.get_by_name ("mix")
            if (videoMixer):
                pad = videoMixer.get_static_pad ("sink_1")
                pad.set_property ("alpha", adjustment.get_value ())

    def launch_audio_settings (self, data):
        GLib.spawn_command_line_async ("gnome-control-center sound")


    def devices_changed (self, client, action, device):
        deviceName = device.get_name ()

        if (action == "add"):
            self.primaryCombo.append_text (deviceName)
            self.secondaryCombo.append_text (deviceName)
        elif (action == "remove"):
            devPath = "/dev/"+deviceName
            if (self.secondarySource == devPath or
                self.primarySource == devPath):
                print ("warning: OUCH! You removed a video device I was using!")
                self.player = None

            primaryModel = self.primaryCombo.get_model ()
            secondaryModel = self.secondaryCombo.get_model ()

            listItr = primaryModel.get_iter_first ()

            while (listItr != None):
                if (primaryModel.get_value (listItr, 0) == deviceName):
                    primaryModel.remove (listItr)
                    break
                listItr = primaryModel.iter_next (listItr)

            listItr = secondaryModel.get_iter_first ()

            while (listItr != None):
                if (secondaryModel.get_value (listItr, 0) == deviceName):
                    secondaryModel.remove (listItr)
                    break
                listItr = secondaryModel.iter_next (listItr)



    def secondary_capture_changed (self, combo):
        deviceName = combo.get_active_text ()
        # reset opacity setting for new pipe
        self.opacityScale.set_value (1.0)

        if (deviceName == None or self.player == None):
            return

        self.sameSecondaryAlert.hide ()

        if (deviceName == "None"):
            self.secondarySource = None
            if (self.primarySource == "Screen"):
                self.video_preview_screencast_only ()
            else:
                self.video_preview_webcam_only ()
            return


        print ("set secondary source")
        self.secondarySource = "/dev/"+deviceName

        #There are no modes which have a secondary capture and no primary
        if (self.mode == mode.WEBCAM or self.mode == mode.SCREENCAST):
            #determine which mode we should switch to based on current primary
            if (self.primarySource == "Screen"):
                self.video_preview_screencast_webcam ()
                return
            else:
                self.video_preview_webcam_webcam ()
                return


        self.player.set_state (gst.STATE_READY)

        # If we were in screencast mode then we need to get out of it
        # as we now have a secondary source to use
        if (self.mode == mode.SCREENCAST):
            self.video_preview_screencast_webcam ()
            return


        if (self.mode == mode.TWOCAM):
            cam1 = self.player.get_by_name ("cam1")
            cam1.set_locked_state (False)
            cam1.set_state (gst.STATE_NULL)
            # Avoid both being set by locking the other source in a null state
            if (self.secondarySource == self.primarySource):
                cam1.set_locked_state (True)
                self.primaryCombo.set_active (-1)
                self.samePrimaryAlert.show ()

        cam2 = self.player.get_by_name ("cam2")
        cam2.set_locked_state (False)
        cam2.set_state (gst.STATE_NULL)

        cam2.set_property ("device", self.secondarySource)

        self.player.set_state (gst.STATE_PLAYING)


    def primary_capture_changed (self, combo):
        deviceName = combo.get_active_text ()
        # reset opacity setting for new pipe
        self.opacityScale.set_value (1.0)
        self.samePrimaryAlert.hide ()


        if (deviceName == "Screen"):
            self.primarySource = deviceName
            if (self.secondarySource == None):
                self.video_preview_screencast_only ()
            else:
                self.video_preview_screencast_webcam ()
            return

        self.primarySource = "/dev/"+deviceName
        self.player.set_state (gst.STATE_READY)

        #our secondary source is none and we're not recording a screencast
        if (self.secondarySource == None and self.mode is not mode.WEBCAM):
            self.video_preview_webcam_only ()
            return
        #we have a primary source which is not the screen and a secondary source
        #that is not none.
        if (self.secondarySource is not None and self.mode is not mode.TWOCAM):
            self.video_preview_webcam_webcam ()
            return

        cam1 = self.player.get_by_name ("cam1")
        cam1.set_locked_state (False)
        cam1.set_state (gst.STATE_NULL)

        if (self.mode == mode.TWOCAM):
            cam2 = self.player.get_by_name ("cam2")
            cam2.set_locked_state (False)
            cam2.set_state (gst.STATE_NULL)
            # Avoid both being set by locking the other source in a null state
            if (self.secondarySource == self.primarySource):
                cam2.set_locked_state (True)
                self.secondaryCombo.set_active (-1)
                self.sameSecondaryAlert.show ()

        cam1.set_property ("device", self.primarySource)

        self.player.set_state (gst.STATE_PLAYING)

    def video_preview_screencast_only (self):

        if (self.mode == mode.SCREENCAST and self.mode is not None
            and self.player is not None):
            return

        if (self.player):
            self.player.set_state(gst.STATE_NULL)

        self.mode = mode.SCREENCAST

        self.posY = 0
        self.posX = 0

        screen = Gdk.get_default_root_window ().get_display ().get_screen (0)
        self.primarySourceHeight = screen.get_height ()
        self.primarySourceWidth = screen.get_width ()
        self.primarySource = "Screen"
        self.secondarySource = None

        self.player = gst.parse_launch (" ximagesrc use-damage=false"
                                        " show-pointer=true ! videoscale"
                                        " ! ximagesink "
                                        " sync=false name=\"sink\"")


        bus = self.player.get_bus()
        bus.add_signal_watch()
        bus.enable_sync_message_emission()
        self.busSig1 = bus.connect("message", self.on_message)
        self.busSig2 = bus.connect("sync-message::element",
                                   self.on_sync_message)

        self.xid = self.playerWindow.get_window ().get_xid()

        self.player.set_state(gst.STATE_PLAYING)

    def video_preview_webcam_only (self):

        if (self.mode == mode.WEBCAM and self.mode is not None 
            and self.player is not None):
            return

        if (self.player):
            self.player.set_state(gst.STATE_NULL)

        self.mode = mode.WEBCAM

        self.posY = 0
        self.posX = 0

        self.player = gst.parse_launch ("v4l2src device="+self.primarySource+""
                                        " name=\"cam1\""
                                        " ! videoflip method=horizontal-flip"
                                        " ! ffmpegcolorspace"
                                        " ! videoscale !"
                                        " ximagesink name=\"sink\"")

        bus = self.player.get_bus()
        bus.add_signal_watch()
        bus.enable_sync_message_emission()
        self.busSig1 = bus.connect("message", self.on_message)
        self.busSig2 = bus.connect("sync-message::element",
                                   self.on_sync_message)

        self.xid = self.playerWindow.get_window ().get_xid()

        self.player.set_state(gst.STATE_PLAYING)



    def video_preview_screencast_webcam (self):

        if (self.mode == mode.SCREENCAST_PIP and self.mode is not None
            and self.player is not None):
            return

        if (self.player):
            self.player.set_state(gst.STATE_NULL)

        self.mode = mode.SCREENCAST_PIP

        screen = Gdk.get_default_root_window ().get_display ().get_screen (0)

        self.primarySourceHeight = screen.get_height ()
        self.primarySourceWidth = screen.get_width ()
        self.secondarySourceHeight = 240
        self.secondarySourceWidth = 320


        self.posY = self.primarySourceHeight - self.secondarySourceHeight
        self.posX = self.primarySourceWidth - self.secondarySourceWidth

        posYStr = str (self.posY)
        posXStr = str (self.posX)


        self.player = gst.parse_launch ("v4l2src "
                                        " device=\""+self.secondarySource+"\""
                                        " name=\"cam2\" ! "
                                        " videoscale ! queue ! videoflip "
                                        " method=horizontal-flip ! "
                                        " ffmpegcolorspace ! "
                                        " video/x-raw-rgb,height=240,framerate=15/1"
                                        " ! videomixer name=mix sink_0::xpos=0"
                                        " sink_0::ypos=0"
                                        " sink_1::xpos="+posXStr+""
                                        " sink_1::ypos="+posYStr+""
                                        " ! videoscale !"
                                        " ximagesink name=\"sink\" "
                                        " sync=false"
                                        " ximagesrc use-damage=false"
                                        " show-pointer=true  !"
                                        " videoscale !"
                                        " video/x-raw-rgb,framerate=15/1 ! "
                                        " mix.")

        bus = self.player.get_bus()
        bus.add_signal_watch()
        bus.enable_sync_message_emission()
        self.busSig1 = bus.connect("message", self.on_message)
        self.busSig2 = bus.connect("sync-message::element",
                                   self.on_sync_message)

        self.xid = self.playerWindow.get_window ().get_xid()

        self.player.set_state(gst.STATE_PLAYING)

    def video_preview_webcam_webcam (self):

        if (self.mode == mode.TWOCAM and self.mode is not None and self.player
            is not None):
            return

        self.mode = mode.TWOCAM

        if (self.player):
            self.player.set_state(gst.STATE_NULL)


        self.primarySourceHeight = 768
        self.primarySourceWidth = 1024
        self.secondarySourceHeight = 240
        self.secondarySourceWidth = 320

        self.posY = 528
        self.posX = 704

        self.player = gst.parse_launch ("v4l2src"
                                        " device="+self.secondarySource+" "
                                        " name=\"cam2\" ! queue !"
                        "videoflip method=horizontal-flip ! ffmpegcolorspace !"
                        "videoscale  add-borders=1 ! "
                        "video/x-raw-rgb,width=320,height=240,framerate=15/1,pixel-aspect-ratio=1/1  ! "
                        "videomixer name=mix sink_0::xpos=0 "
                                   "sink_0::ypos=0 sink_1::xpos=704 "
                                   "sink_1::ypos=528 ! "
                        "videoscale ! ximagesink name=\"sink\" sync=false "
                        "v4l2src device="+self.primarySource+" name=\"cam1\" ! "
                        "queue ! videoflip method=horizontal-flip ! videoflip "
                        " method=vertical-flip ! ffmpegcolorspace ! "
                        " videoscale add-borders=1 ! "
                        " video/x-raw-rgb,width=1024,height=768,pixel-aspect-ratio=1/1 ! "
                        "mix. ")

        bus = self.player.get_bus()
        bus.add_signal_watch()
        bus.enable_sync_message_emission()
        self.busSig1 = bus.connect("message", self.on_message)
        self.busSig2 = bus.connect("sync-message::element",
                                   self.on_sync_message)

        self.xid = self.playerWindow.get_window ().get_xid()

        self.player.set_state(gst.STATE_PLAYING)


    def open_error_dialog (self, msg):
        dialog = Gtk.MessageDialog (self,
                                    Gtk.DialogFlags.MODAL,
                                    Gtk.MessageType.ERROR,
                                    Gtk.ButtonsType.CLOSE,
                                    msg)
        dialog.run ()
        dialog.destroy ()
        return False


    def on_message(self, bus, message):
        t = message.type
        if t == gst.MESSAGE_EOS:
            self.player.set_state(gst.STATE_NULL)
        elif t == gst.MESSAGE_ERROR:
            self.player.set_state(gst.STATE_NULL)
            err, debug = message.parse_error()

            if (debug.find ("No space left on device") > 0):
                msg = "Try using a different usb socket" + "\n" +  err.message + "\n" + debug
                # HACK We can't block here with a dialog so do in idle
                Gdk.threads_add_idle (0, self.open_error_dialog, msg)

            print ("error: "+err.message+ "debug: "+ debug)

    def on_sync_message(self, bus, message):
        message_name = message.structure.get_name()
        if message_name == "prepare-xwindow-id":
            message.src.set_property("force-aspect-ratio", True)
            message.src.set_xwindow_id (self.xid)

    def close (self):
        self.recordingTitle = self.entry.get_text ()

        self.hide ()

        #Make sure that the cameras aren't in a locked state state
        cam2 = self.player.get_by_name ("cam2")
        cam1 = self.player.get_by_name ("cam1")

        if (cam2 != None):
            cam2.set_locked_state (False)

        if (cam1 != None):
            cam1.set_locked_state (False)

        self.player.set_state (gst.STATE_NULL)
        self.audioLevel.set_active (False)

    def open (self):
        self.player = None
        self.show_all ()
        self.samePrimaryAlert.hide ()
        self.sameSecondaryAlert.hide ()
        self.secondaryCombo.set_active (0)
        self.primaryCombo.set_active (0)
        self.audioLevel.set_active (True)
        self.entry.set_text ("")
        self.entry.grab_focus ()

        self.opacityScale.set_value (1.0)
        self.secondarySource = self.defaultSecondarySource

        if (self.defaultSecondarySource == None):
            self.video_preview_screencast_only ()
        else:
            self.video_preview_screencast_webcam ()
