"""Daemon-owned global shortcuts. No GTK dependency or automatic consent dialogs."""
from __future__ import annotations

import re
import os
from pathlib import Path
import threading
import uuid

BUS = 'org.freedesktop.portal.Desktop'
PATH = '/org/freedesktop/portal/desktop'
IFACE = 'org.freedesktop.portal.GlobalShortcuts'
ACTION = 'toggle'
REQUEST_TIMEOUT = 120


def preferred_trigger(binding: str) -> str:
    """Translate our GTK accelerator spelling into the XDG shortcut spelling."""
    modifiers = {'Control': 'CTRL', 'Primary': 'CTRL', 'Shift': 'SHIFT',
                 'Alt': 'ALT', 'Super': 'LOGO', 'Meta': 'LOGO'}
    parts = []
    for match in re.finditer(r'<([^>]+)>', binding):
        modifier = modifiers.get(match.group(1))
        if modifier is None:
            return ''
        if modifier not in parts:
            parts.append(modifier)
    key = re.sub(r'<[^>]+>', '', binding).strip()
    if not key:
        return ''
    return '+'.join(parts + [key.upper() if len(key) == 1 or re.fullmatch(r'F\d+', key, re.I) else key])


def actual_trigger(shortcuts) -> str:
    for action, properties in shortcuts:
        if action == ACTION:
            value = properties.get('trigger_description', '')
            if hasattr(value, 'unpack'):
                value = value.unpack()
            return str(value).strip()
    return ''


class ShortcutPortal:
    def __init__(self, on_activate):
        self._activate = on_activate
        self._lock = threading.Lock()
        self._state = {'state': 'idle', 'error': '', 'trigger': ''}
        self._thread = None
        self._stopped = threading.Event()
        self._context = self._loop = self._connection = None
        self._session = None
        self._session_subscription = None
        self._requests = {}
        self._subscriptions = []
        self._binding = ''
        self._configured = False
        self._version = 0
        self._connecting = False
        self._pending_configure = False
        self._closed = False

    def snapshot(self):
        with self._lock:
            return dict(self._state)

    def _status(self, state, error='', trigger=''):
        with self._lock:
            self._state = dict(state=state, error=error, trigger=trigger)

    def start(self, binding, configure=False):
        with self._lock:
            if self._closed:
                return False
            if self._stopped.is_set():
                self._thread = None
                self._context = self._loop = self._connection = None
                self._session = self._session_subscription = None
                self._requests = {}
                self._subscriptions = []
                self._configured = self._connecting = False
                self._stopped.clear()
            self._binding = binding
            self._pending_configure |= configure
            if self._thread is None:
                self._thread = threading.Thread(target=self._run, name='wayvoice-shortcut-portal', daemon=True)
                try:
                    self._thread.start()
                except RuntimeError as exc:
                    self._thread = None
                    self._state = dict(state="error", error=str(exc), trigger="")
                    return False
                return True
        self._schedule(self._configure if configure else self._restore)
        return True

    def configure(self, binding):
        return self.start(binding, configure=True)

    def _schedule(self, callback):
        if self._context is None or self._closed:
            return
        source = self.GLib.idle_source_new()
        source.set_callback(lambda *_: (callback(), False)[1])
        source.attach(self._context)

    def _run(self):
        try:
            from gi.repository import Gio, GLib
            self.Gio, self.GLib = Gio, GLib
            self._context = GLib.MainContext.new()
            self._context.push_thread_default()
            self._loop = GLib.MainLoop.new(self._context, False)
            address = Gio.dbus_address_get_for_bus_sync(Gio.BusType.SESSION, None)
            self._connection = Gio.DBusConnection.new_for_address_sync(
                address, Gio.DBusConnectionFlags.AUTHENTICATION_CLIENT | Gio.DBusConnectionFlags.MESSAGE_BUS_CONNECTION,
                None, None)
            self._connection.set_exit_on_close(False)
            self._subscriptions.append(self._connection.signal_subscribe(
                BUS, IFACE, None, PATH, None, Gio.DBusSignalFlags.NONE, self._signal))
            self._subscriptions.append(self._connection.signal_subscribe(
                'org.freedesktop.DBus', 'org.freedesktop.DBus', 'NameOwnerChanged',
                '/org/freedesktop/DBus', BUS, Gio.DBusSignalFlags.NONE, self._owner_changed))
            self._register_identity()
            self._restore()
            if not self._closed:
                self._loop.run()
        except Exception as exc:
            self._status('unavailable', str(exc))
        finally:
            try:
                self._cleanup()
            finally:
                if self._context is not None:
                    self._context.pop_thread_default()
                self._stopped.set()

    def _register_identity(self):
        # Native systemd services have no app-* scope identity. Register before
        # any authenticated portal call caches an empty host application ID.
        if os.environ.get('FLATPAK_ID') or Path('/.flatpak-info').is_file():
            return
        self._connection.call_sync(
            BUS, PATH, 'org.freedesktop.host.portal.Registry', 'Register',
            self.GLib.Variant('(sa{sv})', ('io.github.stepan.WayVoice', {})), None,
            self.Gio.DBusCallFlags.NONE, 5000, None)

    def _call(self, interface, method, parameters, callback, path=PATH, on_error=None, preserve_active=False):
        def done(connection, result, *_):
            try:
                value = connection.call_finish(result).unpack()
                callback(value)
            except Exception as exc:
                if on_error is not None and on_error() is False:
                    return
                previous = self.snapshot()
                if preserve_active and previous['state'] == 'active':
                    self._status('active', str(exc), previous['trigger'])
                else:
                    self._status('error', str(exc))
        self._connection.call(BUS, path, interface, method, parameters, None,
                              self.Gio.DBusCallFlags.NONE, 5000, None, done)

    def _request(self, method, signature, arguments, options, callback):
        token = 'wayvoice_' + uuid.uuid4().hex
        sender = self._connection.get_unique_name()[1:].replace('.', '_')
        path = f'/org/freedesktop/portal/desktop/request/{sender}/{token}'
        options['handle_token'] = self.GLib.Variant('s', token)
        def failed():
            if path not in self._requests:
                return False
            self._finish_request(path)
            if method == 'BindShortcuts':
                self._retire_session()
            return True
        def response(_connection, _sender, _path, _iface, _signal, parameters, *_):
            if path not in self._requests:
                return
            code, results = parameters.unpack()
            if code == 0:
                self._finish_request(path)
                callback(results)
            else:
                failed()
                self._status('cancelled' if code == 1 else 'error', '' if code == 1 else 'Shortcut request failed')
        subscription = self._connection.signal_subscribe(
            BUS, 'org.freedesktop.portal.Request', 'Response', path, None,
            self.Gio.DBusSignalFlags.NONE, response)
        timer = self.GLib.timeout_source_new_seconds(REQUEST_TIMEOUT)
        timer.set_callback(lambda *_: self._request_timeout(path, failed))
        timer.attach(self._context)
        self._requests[path] = (subscription, timer)
        def sent(value):
            if value[0] != path:
                if failed():
                    self._status('error', 'Portal returned an unexpected request path')
        self._call(IFACE, method, self.GLib.Variant(signature, (*arguments, options)), sent,
                   on_error=failed)

    def _finish_request(self, path):
        pending = self._requests.pop(path, None)
        if pending:
            self._connection.signal_unsubscribe(pending[0])
            pending[1].destroy()

    def _request_timeout(self, path, on_failure=None):
        if path not in self._requests:
            return False
        if on_failure is not None:
            on_failure()
        else:
            self._finish_request(path)
        self._connection.call(BUS, path, 'org.freedesktop.portal.Request', 'Close', None, None,
                              self.Gio.DBusCallFlags.NONE, 1000, None, None)
        self._status('error', 'Shortcut request timed out')
        return False

    def _retire_session(self):
        # BindShortcuts is single-use even if its consent was cancelled or timed
        # out. Retry must create a new session and inspect its restored actions.
        session = self._session
        self._drop_session_subscription()
        self._session = None
        self._configured = False
        self._pending_configure = False
        if session:
            self._connection.call(BUS, session, 'org.freedesktop.portal.Session', 'Close', None, None,
                                  self.Gio.DBusCallFlags.NONE, 1000, None, None)

    def _restore(self):
        if self._session or self._requests or self._closed or self._connecting:
            return
        self._connecting = True
        self._status('connecting')
        def properties(value):
            self._connecting = False
            self._version = int(value[0])
            self._request('CreateSession', '(a{sv})', (), {
                'session_handle_token': self.GLib.Variant('s', 'wayvoice_' + uuid.uuid4().hex)}, self._created)
        self._call('org.freedesktop.DBus.Properties', 'Get',
                   self.GLib.Variant('(ss)', (IFACE, 'version')), properties,
                   on_error=lambda: setattr(self, '_connecting', False))

    def _created(self, results):
        self._session = results['session_handle']
        self._drop_session_subscription()
        self._session_subscription = self._connection.signal_subscribe(
            BUS, 'org.freedesktop.portal.Session', 'Closed', self._session, None,
            self.Gio.DBusSignalFlags.NONE, self._session_closed)
        self._request('ListShortcuts', '(oa{sv})', (self._session,), {}, self._listed)

    def _listed(self, results):
        shortcuts = results.get('shortcuts', [])
        self._configured = any(action == ACTION for action, _ in shortcuts)
        self._update(shortcuts)
        if self._pending_configure:
            self._pending_configure = False
            self._configure()

    def _update(self, shortcuts):
        trigger = actual_trigger(shortcuts)
        self._status('active' if trigger else 'needs_configuration', trigger=trigger)

    def _configure(self):
        if not self._session:
            self._pending_configure = True
            self._restore()
            return
        if self._requests:
            self._pending_configure = True
            return
        self._pending_configure = False
        if not self._configured:
            self._status('configuring')
            shortcut = {'description': self.GLib.Variant('s', 'Start or stop dictation')}
            trigger = preferred_trigger(self._binding)
            if trigger:
                shortcut['preferred_trigger'] = self.GLib.Variant('s', trigger)
            self._request('BindShortcuts', '(oa(sa{sv})sa{sv})',
                          (self._session, [(ACTION, shortcut)], ''), {}, self._bound)
        elif self._version >= 2:
            self._call(IFACE, 'ConfigureShortcuts', self.GLib.Variant('(osa{sv})',
                       (self._session, '', {})), lambda _: None, preserve_active=True)
        else:
            try:
                self.Gio.AppInfo.launch_default_for_uri('systemsettings://kcm_keys/', None)
            except Exception as exc:
                previous = self.snapshot()
                self._status(previous['state'], str(exc), previous['trigger'])

    def _bound(self, results):
        self._pending_configure = False
        self._configured = True
        self._update(results.get('shortcuts', []))

    def _signal(self, _connection, _sender, _path, _interface, signal, parameters, *_):
        values = parameters.unpack()
        if values[0] != self._session:
            return
        if signal == 'ShortcutsChanged':
            self._update(values[1])
        elif signal == 'Activated' and values[1] == ACTION and self.snapshot()['state'] == 'active':
            try:
                self._activate()
            except Exception as exc:
                self._status('error', str(exc))

    def _drop_session_subscription(self):
        if self._session_subscription is not None:
            self._connection.signal_unsubscribe(self._session_subscription)
            self._session_subscription = None

    def _session_closed(self, _connection=None, _sender=None, path=None, *_):
        if path is not None and path != self._session:
            return
        self._drop_session_subscription()
        self._session = None
        self._configured = False
        self._status('unavailable', 'Shortcut session closed; reconnect from settings')

    def _owner_changed(self, _connection, _sender, _path, _interface, _signal, parameters, *_):
        _, old, new = parameters.unpack()
        if old:
            self._drop_session_subscription()
            for path in list(self._requests):
                self._finish_request(path)
            self._connecting = False
            self._configured = False
            self._pending_configure = False
            self._session = None
            self._status('unavailable', 'Shortcut portal restarted')
        if new:
            try:
                self._register_identity()
                self._restore()
            except Exception as exc:
                self._status('unavailable', str(exc))

    def close(self):
        self._closed = True
        if self._context is not None and self._loop is not None:
            source = self.GLib.idle_source_new()
            source.set_callback(lambda *_: (self._loop.quit(), False)[1])
            source.attach(self._context)
        if self._thread is not None and self._thread is not threading.current_thread():
            self._thread.join(timeout=2)

    def _cleanup(self):
        if self._connection is None:
            return
        for path in list(self._requests):
            self._finish_request(path)
            self._connection.call(BUS, path, 'org.freedesktop.portal.Request', 'Close', None, None,
                                  self.Gio.DBusCallFlags.NONE, 1000, None, None)
        # Closing the private connection also closes every portal session it owns.
        self._drop_session_subscription()
        for subscription in self._subscriptions:
            self._connection.signal_unsubscribe(subscription)
        self._connection.close_sync(None)
