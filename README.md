
# Insight Recorder

This is a prototype application for recording screencasts and webcams simultaneously for running user testing sessions. Use at your own risk.

![Screenshot](http://insight-recorder.github.io/isr3.png)
![Screenshot](http://insight-recorder.github.io/isr2.png)
![Screenshot](http://insight-recorder.github.io/isr.png)

### system install

$ ./autogen.sh --prefix=/usr
$ sudo make install

### single user install

Either just run from current directory or use your own prefix.

$ ./autogen.sh --prefix=$HOME/install


### Run

insight-recorder

### Required dependencies

Debain/Ubuntu package names:

- python-gst0.10
- python-gi
- gir1.2-gtk-3.0
- gir1.2-gudev-1.0
- gstreamer0.10-plugins-bad (vp8enc)
- gstreamer0.10-plugins-good
- gstreamer0.10-alsa

special (optional) for ubuntu gir1.2-appindicator3-0.1
