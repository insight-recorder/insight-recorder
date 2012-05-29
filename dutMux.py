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

#TODO  work out the co-ords of the bottom right corner of the screencast

#from gi.repository import Gst
import gst
import time
import subprocess

class Muxer:
    def __init__(self, projectDir):

      self.projectDir = projectDir
      self.element = gst.parse_launch ("filesrc location="+projectDir+"/webcam-rmd.ogv ! oggdemux name=demux1 ! queue ! theoradec ! videoscale ! video/x-raw-yuv,width=320,height=240 ! queue ! videomixer name=mix sink_0::xpos=0 sink_0::ypos=0 sink_1::xpos=960 sink_1::ypos=784 ! theoraenc ! oggmux name=outmix ! filesink location="+projectDir+"/user-testing.ogv         filesrc location="+projectDir+"/screencast-rmd.avi ! avidemux name=demux2 ! queue ! ffdec_h264  ! mix. ");

      pipebus = self.element.get_bus ()

      pipebus.add_signal_watch ()
      pipebus.connect ("message", self.pipe1_changed_cb)

      #second pass add audio - we could do this in the above pipeline but due to a bug it doesn't quite work..
      self.element2 = gst.parse_launch ("filesrc location="+projectDir+"/user-testing.ogv ! oggdemux name=demux filesrc location="+projectDir+"/webcam-rmd.ogv ! oggdemux name=audiodemux ! vorbisparse ! audio/x-vorbis ! oggmux name=outmux ! filesink location="+projectDir+"/out2.ogv demux. ! theoraparse ! video/x-theora ! outmux.")
      pipebus2 = self.element2.get_bus ()

      pipebus2.add_signal_watch ()
      pipebus2.connect ("message", self.pipe2_changed_cb)
      self.element2.set_state (gst.STATE_PLAYING)

    def pipe2_changed_cb (self, bus, message):
      if message.type == gst.MESSAGE_ERROR:
        print ("error")
      if message.type == gst.MESSAGE_EOS:
        print ("Second pass done")
      if message.type == gst.MESSAGE_STATE_CHANGED:
         old = None
         new = None
         pending = None
         message.parse_state_changed (old, new, pending)
         if (new == gst.STATE_PLAYING):
           print ("playing pipe")



    def pipe1_changed_cb (self, bus, message):
      if message.type == gst.MESSAGE_EOS:
        print ("Done first pass, starting second pass")

    def record (self, start):
      if start == 1:
        print ("Start mux record")
        self.element.set_state (gst.STATE_PLAYING)

        self.element.get_state (gst.CLOCK_TIME_NONE)
# connect to signal on state change to stopped so that we know it's stopped encoding as it seems to happen async
      else:
        print ("stop mux record")
# Pause
        self.element.set_state (3)
# Null/Stop
        self.element.set_state (1)
