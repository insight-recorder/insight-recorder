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

from gi.repository import Gst
import multiprocessing


class Record:
    def __init__(self,
                 fileOutputLocation,
                 inVideoPipe,
                 recording_finished_func):

      # use all the cpu we can
      cpus = multiprocessing.cpu_count()
      self.duration = 0

      # The Gst.ipeDesciption we get here is straight from the preview so will
      # still contain a ximagesink as the sink - obviously we now want to out
      # put to a file so we remove the ximage sink and replace it with a
      # filesink.
      self.pipe = inVideoPipe

      element = None
      targetBreakElement = None

      # Find the old sink element and note the previous element it was
      # linked to and then remove it from pipe.
      fullItr = self.pipe.iterate_elements ()
      status, element = fullItr.next()

      while status != Gst.IteratorResult.DONE:
          print element
          if (element.get_name () == "previewcaps"):
              status, targetBreakElement = fullItr.next()
              break

          status, element = fullItr.next()

      oldCaps = self.pipe.get_child_by_name ("previewcaps")
      oldSink = self.pipe.get_child_by_name ("sink")

      self.pipe.remove (oldCaps)
      self.pipe.remove (oldSink)

      colorspace = Gst.ElementFactory.make ("videoconvert", "colorspace")

      encoder = Gst.ElementFactory.make ("vp8enc", "encoder")
      encoder.load_preset ("Profile Realtime")
      # These are a copy of the properties set by the realtime profile
      # If the preset is not found these are the essential properties to set
      # Worst case senario we're unioning the presets.
      encoder.set_property ("threads", cpus)
      encoder.set_property ("cpu-used", cpus)
      encoder.set_property ("lag-in-frames", 0)
      encoder.set_property ("deadline", 1)

      muxer = Gst.ElementFactory.make ("webmmux", "muxer")

      filesink = Gst.ElementFactory.make ("filesink", "sink")
      filesink.set_property ("location", fileOutputLocation)

      # Audio pipe
      audiosrc = Gst.ElementFactory.make ("autoaudiosrc", None)
      audioconv = Gst.ElementFactory.make ("audioconvert", None)
      vorbisenc = Gst.ElementFactory.make ("vorbisenc", None)

      # Add all the new elements playbin (where is add_many when you need it!)
      self.pipe.add (colorspace)
      self.pipe.add (encoder)
      self.pipe.add (muxer)
      self.pipe.add (filesink)
      self.pipe.add (audiosrc)
      self.pipe.add (audioconv)
      self.pipe.add (vorbisenc)
      ret = False

      # Link the audio src through to the muxer
      ret = audiosrc.link (audioconv)
      ret = audioconv.link(vorbisenc)
      ret = vorbisenc.link (muxer)

      if (ret == False):
          print ("UNSUCCESSFUL LINK MANY in Audio pipe")

      ret = False
      # Link the new video sink pipe up
      ret = colorspace.link (encoder)
      ret = encoder.link (muxer)
      ret = muxer.link (filesink)

      if (ret == False):
          print ("UNSUCCESSFUL LINK MANY in Video pipe")

      #finally link the last part of the chain to the element that was
      #previously linked to the ximagesink.
      ret = False
      ret = targetBreakElement.link (colorspace)
      if (ret == False):
          print ("UNSUCCESSFUL link of old element to colorspace")

      # useful for debug
      #fullItr = self.pipe.iterate_sorted ()
      #status, element = fullItr.next()
      #while status != Gst.IteratorResult.DONE:
      #    print element
      #    status, element = fullItr.next()

      self.recording_finished_func = recording_finished_func

      pipebus = self.pipe.get_bus ()

      pipebus.add_signal_watch ()
      pipebus.connect ("message", self.pipe_changed_cb)

    def pipe_changed_cb (self, bus, message):
        if message.type == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            print "Error: %s" % err, debug
            self.pipe.set_state (Gst.State.NULL)
        if message.type == Gst.MessageType.EOS:
            # The end position is approx the duration
            # Null/Stop
            self.pipe.set_state (Gst.State.NULL)
            # print ("doing recording finished func")
            self.recording_finished_func ()

    def record (self, start):
      if start == 1:
        print ("Start screencast record")
        self.pipe.set_state (Gst.State.PLAYING)
      else:
        print ("stop screencast record")
        self.pipe.send_event (Gst.Event.new_eos ())
        n, self.duration  = self.pipe.query_position (Gst.Format.TIME)

    def get_duration (self):
        return self.duration

