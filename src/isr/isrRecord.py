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
import multiprocessing


class Record:
    def __init__(self,
                 fileOutputLocation,
                 inVideoPipe,
                 recording_finished_func):

      cpus = 1
      if (multiprocessing.cpu_count () > 1):
          cpus = multiprocessing.cpu_count ()/2

      self.duration = 0

      # The gstPipeDesciption we get here is straight from the preview so will
      # still contain a ximagesink as the sink - obviously we now want to out
      # put to a file so we remove the ximage sink and replace it with a
      # filesink.
      self.pipe = inVideoPipe


      fullItr = self.pipe.elements ()

      element = None
      oldSink = None
      oldElementLinkedTo = None

      # Find the old sink element and note the previous element it was
      # linked to and then remove it from pipe.
      for element in fullItr:
          #print (element.get_name ())
          if (element.get_name () == "sink"):
           #   print ("\n\n FOUND ELEMENT \n\n")
              oldSink = element
              oldElementLinkedTo = fullItr.next ()
              break

      self.pipe.remove (oldSink)

      colorspace = gst.element_factory_make ("ffmpegcolorspace", "colorspace")

      encoder = gst.element_factory_make ("vp8enc", "encoder")
      encoder.set_property ("threads", cpus)
      encoder.set_property ("speed", 7)

      #print ("threads: "+str(cpus))

      muxer = gst.element_factory_make ("webmmux", "muxer")

      filesink = gst.element_factory_make ("filesink", "sink")
      filesink.set_property ("location", fileOutputLocation)

      # Audio pipe
      audiosrc = gst.element_factory_make ("alsasrc")
      audiocaps = gst.element_factory_make ("capsfilter")
      audiocaps.set_property ("caps", gst.caps_from_string ("audio/x-raw-int,depth=16,channels=1,rate=44100"))
      audioconv = gst.element_factory_make ("audioconvert")
      queue = gst.element_factory_make ("queue")
      vorbisenc = gst.element_factory_make ("vorbisenc")

      # Add all the new elements to the bin
      self.pipe.add_many (colorspace,
                          encoder,
                          muxer,
                          filesink,
                          audiosrc,
                          audiocaps,
                          audioconv,
                          queue,
                          vorbisenc)
      ret = False

      # Link the audio src through to the muxer
      ret = gst.element_link_many (audiosrc,
                                   audiocaps,
                                   audioconv,
                                   queue,
                                   vorbisenc,
                                   muxer)

      if (ret == False):
          print ("UNSUCCESSFUL LINK MANY in Audio pipe")

      ret = False
      # Link the new video sink pipe up
      ret = gst.element_link_many (colorspace,
                                   encoder,
                                   muxer,
                                   filesink)
      if (ret == False):
          print ("UNSUCCESSFUL LINK MANY in Video pipe")

      #finally link the last part of the chain to the element that was
      #previously linked to the ximagesink.
      ret = False
      ret = oldElementLinkedTo.link (colorspace)
      if (ret == False):
          print ("UNSUCCESSFUL link of old element to colorspace")
# debug
#     fullItr = self.pipe.elements ()
#     for elemet in fullItr:
#         print ("--->")
#         print (elemet.get_name ())

      self.recording_finished_func = recording_finished_func

      pipebus = self.pipe.get_bus ()

      pipebus.add_signal_watch ()
      pipebus.connect ("message", self.pipe_changed_cb)

    def pipe_changed_cb (self, bus, message):
        if message.type == gst.MESSAGE_ERROR:
            err, debug = message.parse_error()
            print "Error: %s" % err, debug
            self.pipe.set_state (gst.STATE_NULL)
        if message.type == gst.MESSAGE_EOS:
            # The end position is approx the duration
            # Null/Stop
            self.pipe.set_state (gst.STATE_NULL)
            # print ("doing recording finished func")
            self.recording_finished_func ()

    def record (self, start):
      if start == 1:
        print ("Start screencast record")
        self.pipe.set_state (gst.STATE_PLAYING)
      else:
        print ("stop screencast record")
        self.pipe.send_event (gst.event_new_eos ())
        self.duration, format = self.pipe.query_position (gst.FORMAT_TIME, None)
     #   self.pipe.set_state (gst.STATE_NULL)

    def get_duration (self):
        return self.duration

