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

class Webcam:
    def __init__(self, fileOutputLocation, device, width, height, Vflip):
      self.duration = 0
      widthStr = str (width)
      heightStr = str (height)
      flip = ""

      if Vflip == True:
          flip = " videoflip method=vertical-flip !"

      self.element = gst.parse_launch ("""v4l2src device="""+device+""" ! videorate
                                       force-fps=15/1 ! queue !
                                       videoflip method=horizontal-flip !
                                       videoscale add-borders=1 ! """+flip+"""
                                       video/x-raw-yuv,width="""+widthStr+""",
                                       height="""+heightStr+""",pixel-aspect-ratio=1/1 !
                                       vp8enc speed=7 !
                                       queue ! mux. alsasrc !
                                       audio/x-raw-int,rate=48000,channels=1,depth=16 !
                                       queue ! audioconvert ! queue !
                                       vorbisenc ! queue ! mux.
                                       webmmux name=mux ! filesink
                                       location="""+fileOutputLocation+"""""")

      pipebus = self.element.get_bus ()

      pipebus.add_signal_watch ()
      pipebus.connect ("message", self.pipe1_changed_cb)

    def pipe1_changed_cb (self, bus, message):
        if message.type == gst.MESSAGE_ERROR:
            err, debug = message.parse_error()
            print "Err: %s" % err, debug
            self.player.set_state(gst.STATE_NULL)
        if message.type == gst.MESSAGE_EOS:
            # The end position is approx the duration
            self.duration, format = self.element.query_position (gst.FORMAT_TIME,
                                                                 None)
            # Null/Stop
            self.element.set_state (gst.STATE_NULL)

    def record (self, start):
      if start == 1:
        print ("Start record")
        self.element.set_state (gst.STATE_PLAYING)
      else:
        print ("stop record")
        self.element.send_event (gst.event_new_eos ())

    def get_duration (self):
        self.duration, format = self.element.query_position (gst.FORMAT_TIME,
                                                                 None)
        return self.duration
