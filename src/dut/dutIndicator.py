
from gi.repository import Gdk
from gi.repository import Gtk

try:
    from gi.repository import AppIndicator3
    hasIndicator = True
except ImportError:
    hasIndicator = False

class dutIndicator:
    def __init__ (self, dutMain):

      self.hasIndicator = hasIndicator
      self.dutMain = dutMain

      if (hasIndicator == False):
        return

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
