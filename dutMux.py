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

from gi.repository import GLib
from gi.repository import Gdk
import gst
import time
import subprocess

class Muxer:
    def __init__(self, projectDir):

      self.projectDir = projectDir

      screen = Gdk.get_default_root_window ().get_display ().get_screen (0)
      posY = str (screen.get_height () - 240)
      posX = str (screen.get_width () - 320)

      self.element = gst.parse_launch ("""filesrc
                                       location="""+projectDir+"""/webcam-dut.webm !
                                       matroskademux name=demux1 ! queue !
                                       vp8dec ! videorate force-fps=15/1 !
                                       video/x-raw-yuv,width=320,height=240,framerate=15/1 !
                                       queue ! videomixer name=mix
                                       sink_0::xpos=0 sink_0::ypos=0
                                       sink_1::xpos="""+posX+"""
                                       sink_1::ypos="""+posY+""" ! vp8enc
                                       quality=10 speed=2 threads=4 ! webmmux
                                       name=outmux !
                                       filesink
                                       location="""+projectDir+"""/user-testing.webm
                                       filesrc location="""+projectDir+"""/screencast-dut.webm
                                       ! matroskademux name=demux2 ! queue !
                                       vp8dec ! videorate force-fps=15/1 !
                                       video/x-raw-yuv,framerate=15/1 ! mix.""")

      pipebus = self.element.get_bus ()

      pipebus.add_signal_watch ()
      pipebus.connect ("message", self.pipe1_changed_cb)

      #second pass add audio - we could do this in the above pipeline but due to a bug it doesn't quite work..
      self.element2 = gst.parse_launch ("""filesrc
                                        location="""+projectDir+"""/webcam-dut.webm ! queue !
                                        matroskademux ! vorbisparse !
                                        audio/x-vorbis !  queue ! outmux.audio_0
                                        filesrc location="""+projectDir+"""/user-testing.webm !
                                        queue ! matroskademux ! video/x-vp8 !
                                        queue ! outmux.video_0 webmmux
                                        name=outmux ! filesink name=sinker
                                        location="""+projectDir+"""/final.webm""")

      pipebus2 = self.element2.get_bus ()

      pipebus2.add_signal_watch ()
      pipebus2.connect ("message", self.pipe2_changed_cb)



    def pipe2_changed_cb (self, bus, message):
      if message.type == gst.MESSAGE_ERROR:
        err, debug = message.parse_error()
        print ("Error dutMux pipe2: %s" % err, debug)

      if message.type == gst.MESSAGE_EOS:
        print ("Second pass done")
      if message.type == gst.MESSAGE_STATE_CHANGED:
         old = None
         new = None
         pending = None
#         message.parse_state_changed (old, new, pending)
         if (new == gst.STATE_PLAYING):
           print ("playing pipe")


    def pipe1_changed_cb (self, bus, message):
      if message.type == gst.MESSAGE_EOS:
        print ("Done first pass, starting second pass")
        self.element2.set_state (gst.STATE_PLAYING)
      if message.type == gst.MESSAGE_ERROR:
        err, debug = message.parse_error()
        print ("Error dutMux pipe1: %s" % err, debug)

    def pipe_report (self):
        positionMs, format = self.element.query_position (gst.FORMAT_TIME, None)
        durationMs, format = self.element.query_duration (gst.FORMAT_TIME, None)

        duration = durationMs*0.000000001
        position = positionMs*0.000000001

        print ("position %f" % position)
        print ("duration %f" % duration)

        percentDone = int ((position/duration)*100)

        # HACK because sometimes gstreamer gets the duration wrong :(
        if percentDone > 100:
            percentDone = 100

        print ("Percent done %d" % percentDone)

        return percentDone

    def record (self, start):
      if start == 1:
        print ("Start mux record")
        #GLib.timeout_add_seconds (1, self.pipe_report, self.element)
        self.element.set_state (gst.STATE_PLAYING)

        self.element.get_state (gst.CLOCK_TIME_NONE)
# connect to signal on state change to stopped so that we know it's stopped encoding as it seems to happen async
      else:
        print ("stop mux record")
# Pause
        self.element.set_state (3)
# Null/Stop
        self.element.set_state (1)

