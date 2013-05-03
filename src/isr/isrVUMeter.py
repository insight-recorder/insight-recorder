import gst

from gi.repository import Gtk


def clamp(x, min, max):
        if x < min:
            return min
        elif x > max:
            return max
        return x

class VUMeter (Gtk.DrawingArea):

    def __init__ (self):
        Gtk.DrawingArea.__init__ (self)

        self.connect ("draw", self.draw);
        self.set_size_request (270, 14)

        pipeline = "autoaudiosrc ! level message=true ! fakesink sync=true"

        self.element = gst.parse_launch (pipeline)

        pipebus = self.element.get_bus ()
        pipebus.add_signal_watch ()
        pipebus.connect ("message", self.pipe_message)

        self.clear = False

        self.rms, self.maxPeak, self.peaks = (0, 0, 0)

    def reset_peak_value (self, unused):
        self.maxPeak = 0

    def pipe_message (self, bus, message):

        level = message.get_structure ()
        if level and level.get_name () == 'level':
            totalRMS, biggestPeak, i = (0, 0, 0)

            peakVals = level.get_value ('peak')
            rmsVals = level.get_value ('rms')

            channels = len (rmsVals)
            biggestPeak = peakVals[0];

            for i in range (0, channels):
                totalRMS = totalRMS + rmsVals[i]

                # find the biggest peak per channel
                if peakVals[i] > biggestPeak:
                    biggestPeak = peakVals[i]

            # This esentially averages out left and right channels in most
            # setups
            meanRMS = totalRMS/channels

            # normalise  0.0 1.0
            self.rms = clamp (pow (10, (meanRMS / 20)), 0, 1)

            peak = clamp (pow (10, (biggestPeak / 20)), 0, 1)

            self.peaks = peak

            if (peak > self.maxPeak):
                self.maxPeak = peak

            GLib.timeout_add_seconds (2, self.reset_peak_value, None)

            self.queue_draw ()

    def draw (self, widget, cr):
             height = 14
             width = 270

             #running peaks
             #green
             cr.set_source_rgb (0.214, 0.8878, 0.39)
             cr.rectangle (0, 0, (self.peaks * width), height)

             #yellow and red
             if (self.peaks > 0.7 and self.peaks < 1.0):
                 cr.set_source_rgb (0.925, 0.882, 0.183)
             elif (self.peaks > 0.9):
                 cr.set_source_rgb (1, 0, 0)

             cr.fill ()

             #rms
             #dark green
             cr.set_source_rgb (0.078, 0.611, 0)
             cr.rectangle (0, 0, (self.rms * width), height)

             #dark yellow and red
             if (self.rms > 0.7 and self.peaks < 1.0):
                 cr.set_source_rgb (0.694, 0.654, 0)
             elif (self.rms > 0.9):
                 cr.set_source_rgb (0.580, 0, 0)

             cr.fill ()

             # max peak indicator
             cr.set_source_rgb (0.6, 0.6, 0.6)
             cr.rectangle ((self.maxPeak * width), 0, 2, height)
             cr.fill ()


             # rectangle border
             cr.set_source_rgb (0, 0, 0)
             cr.set_line_width (1)
             cr.rectangle (0, 0, width, height)
             cr.stroke ()

             self.clear = False

             return True

    def set_active (self, state):

        if (state):
            self.element.set_state (gst.STATE_PLAYING)
        else:
            self.element.set_state (gst.STATE_NULL)

