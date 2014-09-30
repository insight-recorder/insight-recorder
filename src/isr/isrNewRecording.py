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
from gi.repository import Gdk
from gi.repository import GdkX11
from gi.repository import GUdev
from gi.repository import GLib
from gi.repository import Gst
from gi.repository import GObject
from gi.repository import GstVideo

import isrVUMeter

Gdk.threads_init ()
GObject.threads_init()
Gst.init(None)

VIDEO_PREVIEW_HEIGHT = 300
VIDEO_PREVIEW_WIDTH = 600

SCALE_CAPS = " capsfilter name=\"previewcaps\" caps=\"video/x-raw,width="+str(VIDEO_PREVIEW_WIDTH)+",height="+str(VIDEO_PREVIEW_HEIGHT) + " \" "

class mode:
    TWOCAM, SCREENCAST_PIP, SCREENCAST, WEBCAM = range (4)

class NewRecording (Gtk.Window):
    def __init__(self, mainWindow):

        Gtk.Window.__init__ (self, Gtk.WindowType.TOPLEVEL)
        self.set_title(_("Create recording"))
        self.set_transient_for (mainWindow)
        self.set_destroy_with_parent (True)
        self.set_modal(True)
        self.set_resizable (False)
        self.set_position (Gtk.WindowPosition.CENTER_ON_PARENT)


        self.player = None
        self.busSig1 = None
        self.busSig2 = None
        self.recordingTitle = None
        self.mode = None
        self.audioLevel = None
        self.opacityScale = None
        self.bus = None


        self.secondarySource = None
        self.primarySource = "Screen"

        self.primarySourceHeight = 0
        self.primarySourceWidth = 0
        self.secondarySourceHeight = 0
        self.secondarySourceWidth = 0

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
        primaryComboLabel = Gtk.Label ()
        primaryComboLabel.set_text (_("Primary capture:"))

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
        secondaryComboLabel = Gtk.Label ()
        secondaryComboLabel.set_text (_("Secondary capture:"))

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
        self.playerWindow.set_size_request (VIDEO_PREVIEW_WIDTH,
                                            VIDEO_PREVIEW_HEIGHT)
        self.playerWindow.connect ("realize",
                                  self.player_window_realized)

        recordingNameBox = Gtk.VBox ()
        recordingNameBox.set_spacing (8)
        recordingNameBox.pack_start (label, False, False, 0)
        recordingNameBox.pack_start (self.entry, False, False, 0)

        opacityScaleLabel = Gtk.Label ()
        opacityScaleLabel.set_text (_("Opacity for secondary capture:"))
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

        audioLabel = Gtk.Label ()
        audioLabel.set_label (_("Audio level:"))
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

        buttonBox = Gtk.ButtonBox ()
        buttonBox.set_layout (Gtk.ButtonBoxStyle.END)
        cancelButton = Gtk.Button.new_from_stock (Gtk.STOCK_CANCEL)
        cancelButton.connect ("clicked",
                              lambda button:
                              self.hide())

        self.startRecordButton = Gtk.Button.new_with_label(_("Start recording"))
        buttonBox.add (cancelButton)
        buttonBox.add (self.startRecordButton)

        contentArea = Gtk.VBox()
        contentArea.set_spacing (4)
        contentArea.set_margin_top (8)
        contentArea.add (recordingNameBox)
        contentArea.add (devicesBox)
        contentArea.add (self.playerWindow)
        contentArea.add (settingsGrid)
        contentArea.add (buttonBox)

        self.add(contentArea)

    def player_window_realized (self, data):
        self.xid = self.playerWindow.get_window ().get_xid()


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


        self.player.set_state (Gst.State.READY)

        # If we were in screencast mode then we need to get out of it
        # as we now have a secondary source to use
        if (self.mode == mode.SCREENCAST):
            self.video_preview_screencast_webcam ()
            return


        if (self.mode == mode.TWOCAM):
            cam1 = self.player.get_by_name ("cam1")
            cam1.set_locked_state (False)
            cam1.set_state (Gst.State.NULL)
            # Avoid both being set by locking the other source in a null state
            if (self.secondarySource == self.primarySource):
                cam1.set_locked_state (True)
                self.primaryCombo.set_active (-1)
                self.samePrimaryAlert.show ()

        cam2 = self.player.get_by_name ("cam2")
        cam2.set_locked_state (False)
        cam2.set_state (Gst.State.NULL)

        cam2.set_property ("device", self.secondarySource)

        self.player.set_state (Gst.State.PLAYING)


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
        self.player.set_state (Gst.State.READY)

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
        cam1.set_state (Gst.State.NULL)

        if (self.mode == mode.TWOCAM):
            cam2 = self.player.get_by_name ("cam2")
            cam2.set_locked_state (False)
            cam2.set_state (Gst.State.NULL)
            # Avoid both being set by locking the other source in a null state
            if (self.secondarySource == self.primarySource):
                cam2.set_locked_state (True)
                self.secondaryCombo.set_active (-1)
                self.sameSecondaryAlert.show ()

        cam1.set_property ("device", self.primarySource)

        self.player.set_state (Gst.State.PLAYING)

    def video_preview_screencast_only (self):

        if (self.mode == mode.SCREENCAST and self.mode is not None
            and self.player is not None):
            return

        if (self.player):
            self.player.set_state(Gst.State.NULL)

        self.mode = mode.SCREENCAST

        self.posY = 0
        self.posX = 0

        screen = Gdk.get_default_root_window ().get_display ().get_screen (0)
        self.primarySourceHeight = screen.get_height ()
        self.primarySourceWidth = screen.get_width ()
        self.primarySource = "Screen"
        self.secondarySource = None

        self.player = Gst.parse_launch (" ximagesrc use-damage=false"
                                        " show-pointer=true ! videoscale !"
                                        + SCALE_CAPS +
                                        " ! ximagesink "
                                        " sync=false name=\"sink\"")


        bus = self.player.get_bus()
        bus.add_signal_watch()
        bus.enable_sync_message_emission()
        self.busSig1 = bus.connect("message", self.on_message)
        # This is apparently no longer needed but will keep it here for
        # compatibility
        self.busSig2 = bus.connect("sync-message::element",
                                   self.on_sync_message)


        self.player.set_state(Gst.State.PLAYING)

    def video_preview_webcam_only (self):

        if (self.mode == mode.WEBCAM and self.mode is not None 
            and self.player is not None):
            return

        if (self.player):
            self.player.set_state(Gst.State.NULL)

        self.mode = mode.WEBCAM

        self.posY = 0
        self.posX = 0


        description = str("v4l2src device="+self.primarySource+""
                      " name=\"cam1\" "
                       # temp caps FIXME these need to be inspected and not
                       # hardcoded
                      " ! video/x-raw,height=480 "
                      " ! videoflip method=horizontal-flip"
                      " ! videoconvert"
                      " ! videoscale ! "
                      + SCALE_CAPS +
                      " ! ximagesink name=\"sink\"")

        print description
        self.player = Gst.parse_launch (description)

        self.bus = self.player.get_bus()
        self.bus.add_signal_watch()
        self.bus.enable_sync_message_emission()
        self.bus.connect("message::error", self.on_error)
        self.busSig1 = self.bus.connect("message", self.on_message)
        self.busSig2 = self.bus.connect("sync-message::element",
                                        self.on_sync_message)


        self.player.set_state(Gst.State.PLAYING)


    def on_error (self, bus, msg):
        print ("on_error:", msg.parse_error())

    def video_preview_screencast_webcam (self):

        if (self.mode == mode.SCREENCAST_PIP and self.mode is not None
            and self.player is not None):
            return

        if (self.player):
            self.player.set_state(Gst.State.NULL)

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

        # Temporary workaround capsfilter issue
        # https://bugzilla.gnome.org/show_bug.cgi?id=727180
        temporaryCaps = " ! video/x-raw,height=" + str(self.primarySourceHeight)  +  ",width=" + str(self.primarySourceWidth) + " "

        description = str ("v4l2src "
                           " device=\""+self.secondarySource+"\""
                           " name=\"cam2\" ! "
                           " videoscale ! queue ! videoflip "
                           " method=horizontal-flip ! "
                           " videoconvert ! "
                           " video/x-raw,height=240"
                           " ! videomixer name=mix sink_0::xpos=0"
                           " sink_0::ypos=0"
                           " sink_1::xpos="+posXStr+""
                           " sink_1::ypos="+posYStr+""
                           + temporaryCaps +
                           " ! videoscale ! "
                           + SCALE_CAPS +
                           " ! ximagesink name=\"sink\" "
                           " sync=false force-aspect-ratio=true"
                           " ximagesrc use-damage=false"
                           " show-pointer=true  !"
                           " videoscale !"
                           " mix.")

        print description
        self.player = Gst.parse_launch (description)

        bus = self.player.get_bus()
        bus.add_signal_watch()
        bus.enable_sync_message_emission()
        self.busSig1 = bus.connect("message", self.on_message)
        self.busSig2 = bus.connect("sync-message::element",
                                   self.on_sync_message)


        self.player.set_state(Gst.State.PLAYING)

    def video_preview_webcam_webcam (self):
        print ("I: Doing webcam_webcam")

        if (self.mode == mode.TWOCAM and self.mode is not None and self.player
            is not None):
            return

        self.mode = mode.TWOCAM

        if (self.player):
            self.player.set_state(Gst.State.NULL)


        self.primarySourceHeight = 768
        self.primarySourceWidth = 1024
        self.secondarySourceHeight = 240
        self.secondarySourceWidth = 320

        self.posY = 528
        self.posX = 704

        # Temporary workaround capsfilter issue
        # https://bugzilla.gnome.org/show_bug.cgi?id=727180
        temporaryCaps = " video/x-raw,height=" + str(self.primarySourceHeight)  +  ",width=" + str(self.primarySourceWidth) + " "


        description = str (" v4l2src"
                           " device="+self.secondarySource+" name=\"cam2\" !"
                           " videoflip method=horizontal-flip ! "
                           " videoconvert !"
                           " video/x-raw,height=240 ! "
                           " videomixer name=mix sink_0::xpos=0 "
                                    "sink_0::ypos=0 sink_1::xpos=704 "
                                    "sink_1::ypos=528  ! "
                           + temporaryCaps +
                           " ! videoscale ! "
                           + SCALE_CAPS +
                           " ! videoconvert ! "
                           " ximagesink name=\"sink\" sync=false "
                           " v4l2src device="+self.primarySource+ ""
                           "                 name=\"cam1\" ! "
                           # temp
                           " video/x-raw,height=480 ! "
                           " videoflip method=horizontal-flip ! "
                           " videoflip  method=vertical-flip ! "
                           " videoscale ! "
                           " video/x-raw,width=1024,height=768 ! "
                           " mix. ")

        print description
        self.player = Gst.parse_launch (description)

        bus = self.player.get_bus()
        bus.add_signal_watch()
        bus.enable_sync_message_emission()
        self.busSig1 = bus.connect("message", self.on_message)
        self.busSig2 = bus.connect("sync-message::element",
                                   self.on_sync_message)


        self.player.set_state(Gst.State.PLAYING)


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
        if t == Gst.MessageType.EOS:
            self.player.set_state(Gst.State.NULL)
        elif t == Gst.MessageType.ERROR:
            self.player.set_state(Gst.State.NULL)
            err, debug = message.parse_error()

            if (debug.find ("No space left on device") > 0):
                msg = "Try using a different usb socket" + "\n" +  err.message + "\n" + debug
                # HACK We can't block here with a dialog so do in idle
                Gdk.threads_add_idle (0, self.open_error_dialog, msg)

            print ("error: "+err.message+ "debug: "+ debug)

    def on_sync_message(self, bus, message):
        message_name = message.get_structure ().get_name()
        if message_name == "prepare-window-handle":
           message.src.set_window_handle (self.xid)

    def redraw (self):
        self.playerWindow.queue_draw()
        print "wefwef"
        return True


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

        self.player.set_state (Gst.State.NULL)
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
