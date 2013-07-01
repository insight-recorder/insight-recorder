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
import os

if os.environ.get('DESKTOP_SESSION') not in ('ubuntu', 'ubuntu-2d'):
   isUnity = False
else:
    try:
        from gi.repository import AppIndicator3
        isUnity = True
    except ImportError:
        print ("Error: we detected ubuntu as the desktop but found no appindicator library")
        isUnity = False

from gi.repository import Gtk
from gi.repository import Gdk

class Indicator:
    def __init__ (self, isrMain):
      if (isUnity is not True):
          return;

      self.isrMain = isrMain

      self.indicator = AppIndicator3.Indicator.new ("insight-recorder",
                                                    Gtk.STOCK_MEDIA_RECORD,
                                                    AppIndicator3.IndicatorCategory.APPLICATION_STATUS)

      menu = Gtk.Menu ()
      self.stopRecord = Gtk.MenuItem (_("Stop recording"))
      self.stopRecord.connect ("activate", isrMain.stop_record)

      menu.append (self.stopRecord)
      self.stopRecord.show ()
      self.indicator.set_menu (menu)

      isrMain.mainWindow.connect ("window-state-event", self.on_window_event)

    def on_window_event (self, widget, event):
      if (event.new_window_state == Gdk.WindowState.ICONIFIED and
          self.isrMain.isRecording == True):
        self.indicator.set_status (AppIndicator3.IndicatorStatus.ACTIVE)
      else:
        if (event.new_window_state == Gdk.WindowState.FOCUSED and
            self.isrMain.isRecording == False):
            self.indicator.set_status (AppIndicator3.IndicatorStatus.PASSIVE)
