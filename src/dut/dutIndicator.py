import os

class dutIndicator:
    def __init__ (self, dutMain):
      if os.environ.get('DESKTOP_SESSION') not in ('ubuntu', 'ubuntu-2d'):
        self.hasIndicator = False
      else:
          try:
              from gi.repository import AppIndicator3 as AppIndicator
          except ImportError:
              self.hasIndicator = False
          else:
              self.hasIndicator = True

      self.dutMain = dutMain

      self.indicator = AppIndicator3.Indicator.new ("dawati-user-testing",
                                                    Gtk.STOCK_MEDIA_RECORD,
                                                    AppIndicator3.IndicatorCategory.APPLICATION_STATUS)

      menu = Gtk.Menu ()
      self.stopRecord = Gtk.MenuItem ("Stop recording")

      menu.append (self.stopRecord)
      self.stopRecord.show ()
      self.indicator.set_menu (menu)

      dutMain.mainWindow.connect ("window-state-event", self.on_window_event)

    def on_window_event (self, widget, event):
      if (event.new_window_state == Gdk.WindowState.ICONIFIED and
          self.dutMain.isRecording == True):
        self.indicator.set_status (AppIndicator3.IndicatorStatus.ACTIVE)
      else:
        if (event.new_window_state == Gdk.WindowState.FOCUSED and
            self.dutMain.isRecording == False):
            self.indicator.set_status (AppIndicator3.IndicatorStatus.PASSIVE)
