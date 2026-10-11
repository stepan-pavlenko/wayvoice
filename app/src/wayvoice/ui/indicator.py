"""Opt-in status window: read-only, no transcript and no activation on updates."""
from gi.repository import Adw, Gtk, GLib, Gdk, Pango
from .. import deps
from ..cli import request
from ..config import load_config
from ..i18n import tr
from .async_tasks import TaskRunner
from .localization import set_text_direction
from .health_presentation import recovery_text
from .setup_presentation import model_missing
from .widgets.labels import make_label


class IndicatorWindow(Adw.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app)
        self.tasks = TaskRunner()
        self._poll_running = False
        self._menu_unavailable = False
        self.language = load_config().get('ui_language', 'auto')
        set_text_direction(self, self.language)
        self.set_title(self.t('indicator.title'))
        self.set_size_request(280, 64)
        self.set_default_size(340, 84)
        self.set_resizable(False)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        for side in ('top', 'bottom', 'start', 'end'):
            getattr(box, f'set_margin_{side}')(8)
        row = Gtk.Box(spacing=6)
        self.handle = Gtk.WindowHandle()
        self.handle.set_child(row)
        box.append(self.handle)
        self.state_icon = Gtk.Image.new_from_icon_name('audio-input-microphone-symbolic')
        row.append(self.state_icon)
        self.spinner = Gtk.Spinner()
        self.spinner.set_visible(False)
        row.append(self.spinner)
        self.state_label = make_label(self.t('status.waiting'), 'heading')
        self.state_label.set_ellipsize(Pango.EllipsizeMode.END)
        self.state_label.set_hexpand(True)
        row.append(self.state_label)
        self.settings_button = self._icon_button('preferences-system-symbolic',
                                                 self.t('indicator.open_app'))
        self.settings_button.connect('clicked', lambda *_: app.activate())
        row.append(self.settings_button)
        self.window_actions_button = self._icon_button('view-more-symbolic',
                                                      self.t('indicator.window_actions'))
        menu_click = Gtk.GestureClick()
        menu_click.set_button(Gdk.BUTTON_PRIMARY)
        menu_click.connect('pressed', self._menu_pressed)
        self.window_actions_button.connect('clicked', self._menu_clicked, menu_click)
        self.window_actions_button.add_controller(menu_click)
        menu_keys = Gtk.EventControllerKey()
        menu_keys.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        menu_keys.connect('key-pressed', self._menu_key_pressed)
        self.window_actions_button.add_controller(menu_keys)
        row.append(self.window_actions_button)
        self.close_button = self._icon_button('window-close-symbolic', self.t('common.close'))
        self.close_button.connect('clicked', lambda *_: self.close())
        row.append(self.close_button)
        self.details = Gtk.Expander(label=self.t('indicator.details'))
        detail_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.detail_label = make_label('', wrap=True)
        self.detail_label.set_max_width_chars(38)
        detail_box.append(self.detail_label)
        self.limit_label = make_label(self.t('indicator.limit'), 'dim-label', wrap=True)
        self.limit_label.set_max_width_chars(38)
        detail_box.append(self.limit_label)
        self.window_actions_hint = make_label(self.t('indicator.window_actions_hint'),
                                             'dim-label', wrap=True)
        self.window_actions_hint.set_max_width_chars(38)
        detail_box.append(self.window_actions_hint)
        self.details.set_child(detail_box)
        box.append(self.details)
        keys = Gtk.EventControllerKey()
        keys.connect('key-pressed', self._window_key_pressed)
        self.add_controller(keys)
        self.set_content(box)
        self.connect('unrealize', self._dispose_ui)
        self.connect('close-request', self._dispose_ui)
        self.tasks.idle(self._poll)
        self.tasks.every(650, self._poll)

    @staticmethod
    def _icon_button(icon, label):
        button = Gtk.Button.new_from_icon_name(icon)
        button.add_css_class('flat')
        button.set_tooltip_text(label)
        button.update_property([Gtk.AccessibleProperty.LABEL], [label])
        return button

    def _show_window_menu(self, event):
        surface = self.get_surface()
        if event is not None and surface is not None and surface.show_window_menu(event):
            self._menu_unavailable = False
            self.window_actions_hint.set_text(self.t('indicator.window_actions_hint'))
            return True
        self._menu_unavailable = True
        self.window_actions_hint.set_text(self.t('indicator.window_actions_unavailable'))
        self.details.set_expanded(True)
        return False

    def _menu_pressed(self, gesture, _count, _x, _y):
        self._show_window_menu(gesture.get_last_event(None))

    def _menu_clicked(self, _button, gesture):
        # Assistive activation has no input serial for the compositor menu.
        if gesture.get_current_event() is None:
            self._show_window_menu(None)

    def _menu_key_pressed(self, controller, keyval, _keycode, _modifiers):
        if keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter, Gdk.KEY_space):
            self._show_window_menu(controller.get_current_event())
            return True
        return False

    def _window_key_pressed(self, controller, keyval, _keycode, modifiers):
        if keyval == Gdk.KEY_Menu or (keyval == Gdk.KEY_F10 and modifiers & Gdk.ModifierType.SHIFT_MASK):
            self._show_window_menu(controller.get_current_event())
            return True
        return False

    def t(self, key, **kwargs):
        return tr(key, self.language, **kwargs)

    def _dispose_ui(self, *_args):
        self.tasks.close()
        return False

    @staticmethod
    def _snapshot():
        reply = request('status', timeout=0.3)
        reply['_missing_deps'] = [d.label for d in deps.dependencies()
                                  if d.required and not deps.status_of(d)['ok']]
        return reply, load_config()

    def _poll(self):
        if not self._poll_running:
            self._poll_running = True
            self.tasks.run(self._snapshot, self._paint,
                           lambda exc: self._paint(({'ok': False, 'error': str(exc)}, {})))
        return GLib.SOURCE_CONTINUE

    def _paint(self, snapshot):
        self._poll_running = False
        reply, cfg = snapshot
        self.language = cfg.get('ui_language', self.language or 'auto')
        set_text_direction(self, self.language)
        self.set_title(self.t('indicator.title'))
        for button, key in ((self.settings_button, 'indicator.open_app'),
                            (self.window_actions_button, 'indicator.window_actions'),
                            (self.close_button, 'common.close')):
            label = self.t(key)
            button.set_tooltip_text(label)
            button.update_property([Gtk.AccessibleProperty.LABEL], [label])
        self.details.set_label(self.t('indicator.details'))
        self.limit_label.set_text(self.t('indicator.limit'))
        self.window_actions_hint.set_text(self.t(
            'indicator.window_actions_unavailable' if self._menu_unavailable else
            'indicator.window_actions_hint'))
        if not reply.get('ok'):
            state = self.t('health.attention')
            detail = self.t('health.daemon_unavailable')
        elif reply.get('recording'):
            state = self.t('status.recording')
            detail = self.t('hero.recording_hint')
        elif reply.get('busy'):
            state = self.t('status.transcribing')
            detail = self.t('indicator.processing')
        elif reply.get('config_error') or reply.get('last_error'):
            state = self.t('health.attention')
            reason = reply.get('config_error') or reply['last_error']
            detail = '\n'.join(recovery_text(self.t, reason,
                                            'config' if reply.get('config_error') else None))
        elif ((reply.get('model') or {}).get('download') or {}).get('state') in {'downloading', 'warming'}:
            state = self.t('settings.preparing')
            detail = self.t('indicator.preparing')
        elif reply.get('_missing_deps'):
            state = self.t('health.attention')
            detail = self.t('health.deps_missing', names=', '.join(reply['_missing_deps']))
        elif reply.get('last_warning'):
            state = self.t('health.attention')
            detail = '\n'.join(recovery_text(self.t, reply['last_warning']))
        elif (reply.get('engine') or {}).get('state') != 'ready' or model_missing(reply):
            state = self.t('health.attention')
            detail = self.t('setup.model_next' if model_missing(reply) else 'hero.open_settings')
        else:
            state = self.t('status.ready')
            portal = reply.get('shortcut_portal')
            has_shortcut = bool(portal.get('trigger')) if portal is not None else bool(cfg.get('shortcut'))
            detail = self.t('indicator.ready' if has_shortcut else 'setup.shortcut_disabled')
        self.state_label.set_text(state)
        self.detail_label.set_text(detail)
        self.state_label.set_tooltip_text(detail)
        processing = bool(reply.get('ok') and reply.get('busy') and not reply.get('recording'))
        self.spinner.set_spinning(processing)
        self.spinner.set_visible(processing)
        self.state_icon.set_visible(not processing)
        icon = ('media-record-symbolic' if reply.get('recording') else
                'dialog-warning-symbolic' if state == self.t('health.attention') else
                'audio-input-microphone-symbolic')
        self.state_icon.set_from_icon_name(icon)
