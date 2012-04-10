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

##  devices = g_udev_client_query_by_subsystem (monitor->priv->client, "video4linux");


class Webcam:
    def __init__(self, projectDir):
      self.element = gst.parse_launch ("""v4l2src device=/dev/video1 ! queue !
                                       videoflip method=horizontal-flip !
                                       video/x-raw-yuv,width=1024,height=768,framerate=30/1 ! theoraenc ! queue ! mux. alsasrc ! audio/x-raw-int,rate=48000,channels=1,depth=16 ! queue ! audioconvert ! queue ! vorbisenc ! queue ! mux. oggmux name=mux ! filesink location="""+projectDir+"""/webcam-rmd.ogv""")

      pipebus = self.element.get_bus ()

      pipebus.add_signal_watch ()
      pipebus.connect ("message", self.pipe1_changed_cb)

    def pipe1_changed_cb (self, bus, message):
      print ("lalal")

    def record (self, start):
      if start == 1:
        print ("Start record")
        self.element.set_state (4)
      else:
        print ("stop record")
# Pause
        self.element.set_state (3)
# Null/Stop
        self.element.set_state (1)
