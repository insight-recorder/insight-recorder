AC_INIT(insight-recorder, 0.9)
AM_INIT_AUTOMAKE([1.11 no-dist-gzip dist-xz foreign])
AM_SILENT_RULES([yes])
AM_MAINTAINER_MODE([enable])
GNOME_MAINTAINER_MODE_DEFINES

GLIB_GSETTINGS

AM_PATH_PYTHON([2.4],,AC_MSG_ERROR([Python not found]))


IT_PROG_INTLTOOL([0.35.0])
GETTEXT_PACKAGE=insight-recorder
AC_SUBST(GETTEXT_PACKAGE)
AC_DEFINE_UNQUOTED([GETTEXT_PACKAGE], ["$GETTEXT_PACKAGE"],
                                      [The domain to use with gettext])
AM_GLIB_GNU_GETTEXT

AC_OUTPUT([
Makefile
po/Makefile.in
data/Makefile
data/insight-recorder.desktop.in
src/isr/isrDefs.py
src/Makefile
src/isr/Makefile
])
