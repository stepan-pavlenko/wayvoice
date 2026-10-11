"""Apply UI direction before building widgets; GTK mirrors start/end alignment."""
from gi.repository import Gtk
from ..i18n import resolve_language


def set_text_direction(window, language):
    direction = Gtk.TextDirection.RTL if resolve_language(language) == 'ar' else Gtk.TextDirection.LTR
    if Gtk.Widget.get_default_direction() != direction:
        Gtk.Widget.set_default_direction(direction)
    window.set_direction(direction)
