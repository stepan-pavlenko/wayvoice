"""Portal state behavior without a session bus or any GTK imports."""
import unittest
from unittest.mock import Mock

from wayvoice.shortcut_portal import ShortcutPortal, actual_trigger, preferred_trigger


class PortalTests(unittest.TestCase):
    def test_accelerators_use_xdg_spelling(self):
        self.assertEqual(preferred_trigger('<Control><Shift>F8'), 'CTRL+SHIFT+F8')
        self.assertEqual(preferred_trigger('<Primary><Control>space'), 'CTRL+space')
        self.assertEqual(preferred_trigger('<Hyper>A'), '')
        self.assertEqual(preferred_trigger(''), '')

    def test_only_actual_toggle_trigger_is_reported(self):
        self.assertEqual(actual_trigger([('other', {'trigger_description': 'F9'})]), '')
        self.assertEqual(actual_trigger([('toggle', {'preferred_trigger': 'F8'})]), '')
        self.assertEqual(actual_trigger([('toggle', {'trigger_description': 'Ctrl+F8'})]), 'Ctrl+F8')

    def test_restore_never_binds_or_opens_settings(self):
        portal = ShortcutPortal(Mock())
        portal._request = Mock()
        portal._listed({'shortcuts': [('toggle', {'trigger_description': 'F8'})]})
        self.assertEqual(portal.snapshot()['state'], 'active')
        portal._request.assert_not_called()
        portal._listed({'shortcuts': []})
        self.assertEqual(portal.snapshot()['state'], 'needs_configuration')
        portal._request.assert_not_called()

    def test_activation_filters_session_action_and_actual_assignment(self):
        activate = Mock()
        portal = ShortcutPortal(activate)
        portal._session = '/session/ours'
        def signal(session, action):
            args = Mock()
            args.unpack.return_value = (session, action, 0, {})
            portal._signal(None, None, None, None, 'Activated', args)
        signal('/session/ours', 'toggle')
        signal('/session/foreign', 'toggle')
        portal._update([('toggle', {'trigger_description': 'F8'})])
        signal('/session/ours', 'other')
        activate.assert_not_called()
        signal('/session/ours', 'toggle')
        activate.assert_called_once()

    def test_external_change_and_session_close_remove_active_status(self):
        portal = ShortcutPortal(Mock())
        portal._session = '/ours'
        portal._update([('toggle', {'trigger_description': 'F8'})])
        args = Mock()
        args.unpack.return_value = ('/ours', [('toggle', {'trigger_description': ''})])
        portal._signal(None, None, None, None, 'ShortcutsChanged', args)
        self.assertEqual(portal.snapshot()['state'], 'needs_configuration')
        portal._session_closed()
        self.assertEqual(portal.snapshot()['trigger'], '')
        self.assertEqual(portal.snapshot()['state'], 'unavailable')

    def test_request_finish_unsubscribes_and_destroys_timeout_once(self):
        portal = ShortcutPortal(Mock())
        portal._connection = Mock()
        timer = Mock()
        portal._requests['/request'] = (12, timer)
        portal._finish_request('/request')
        portal._finish_request('/request')
        portal._connection.signal_unsubscribe.assert_called_once_with(12)
        timer.destroy.assert_called_once()

    def test_closed_helper_cannot_restart(self):
        portal = ShortcutPortal(Mock())
        portal.close()
        self.assertFalse(portal.start('F8'))
        self.assertFalse(portal.configure('F9'))

    def test_v1_existing_action_opens_desktop_settings_without_rebinding(self):
        portal = ShortcutPortal(Mock())
        portal._session = '/ours'
        portal._configured = True
        portal._version = 1
        portal.Gio = Mock()
        portal._request = Mock()
        portal._configure()
        portal.Gio.AppInfo.launch_default_for_uri.assert_called_once_with('systemsettings://kcm_keys/', None)
        portal._request.assert_not_called()

    def test_opening_settings_failure_keeps_active_hotkey(self):
        portal = ShortcutPortal(Mock())
        portal._session, portal._configured, portal._version = '/ours', True, 1
        portal._update([('toggle', {'trigger_description': 'F8'})])
        portal.Gio = Mock()
        portal.Gio.AppInfo.launch_default_for_uri.side_effect = RuntimeError('No handler')
        portal._configure()
        self.assertEqual(portal.snapshot(), {'state': 'active', 'trigger': 'F8', 'error': 'No handler'})

    def test_request_accepts_response_before_method_reply_and_cleans_timer(self):
        portal = ShortcutPortal(Mock())
        portal._connection = Mock()
        portal._connection.get_unique_name.return_value = ':1.20'
        portal._context = Mock()
        portal.Gio = Mock()
        portal.GLib = Mock()
        portal.GLib.Variant.side_effect = lambda signature, value: value
        timer = portal.GLib.timeout_source_new_seconds.return_value
        callback = Mock()
        def call(_interface, _method, _parameters, sent, **_kwargs):
            # Portal may emit Response before its method callback is delivered.
            path, = portal._requests
            args = Mock()
            args.unpack.return_value = (0, {'session_handle': '/session'})
            subscribed = portal._connection.signal_subscribe.call_args.args[-1]
            subscribed(None, None, path, None, None, args)
            sent((path,))
        portal._call = call
        portal._request('CreateSession', '(a{sv})', (), {}, callback)
        callback.assert_called_once_with({'session_handle': '/session'})
        self.assertFalse(portal._requests)
        timer.destroy.assert_called_once()

    def test_request_method_failure_drops_response_subscription_immediately(self):
        portal = ShortcutPortal(Mock())
        portal._connection = Mock()
        portal._connection.get_unique_name.return_value = ':1.20'
        portal._context = Mock()
        portal.Gio = Mock()
        portal.GLib = Mock()
        portal.GLib.Variant.side_effect = lambda signature, value: value
        def fail(*_args, on_error, **_kwargs):
            on_error()
        portal._call = fail
        portal._request('CreateSession', '(a{sv})', (), {}, Mock())
        self.assertFalse(portal._requests)
        portal._connection.signal_unsubscribe.assert_called_once()
        portal.GLib.timeout_source_new_seconds.return_value.destroy.assert_called_once()

    def test_native_identity_is_registered_before_portal_use(self):
        from unittest.mock import patch
        portal = ShortcutPortal(Mock())
        portal._connection = Mock()
        portal.Gio = Mock()
        portal.GLib = Mock()
        portal.GLib.Variant.side_effect = lambda signature, value: value
        with patch.dict('os.environ', {'FLATPAK_ID': ''}), patch('wayvoice.shortcut_portal.Path.is_file', return_value=False):
            portal._register_identity()
        args = portal._connection.call_sync.call_args.args
        self.assertEqual(args[2:5], ('org.freedesktop.host.portal.Registry', 'Register', ('io.github.stepan.WayVoice', {})))

    def test_fatal_thread_exit_can_retry_with_fresh_connection(self):
        from unittest.mock import patch
        portal = ShortcutPortal(Mock())
        portal._thread = Mock()
        portal._context = Mock()
        portal._connection = Mock()
        portal._stopped.set()
        with patch('wayvoice.shortcut_portal.threading.Thread') as thread:
            self.assertTrue(portal.configure('F8'))
            thread.return_value.start.assert_called_once()
        self.assertIsNone(portal._connection)
        self.assertIsNone(portal._context)
        self.assertFalse(portal._stopped.is_set())

    def test_v2_configure_failure_preserves_binding_but_never_revives_closed_session(self):
        activate = Mock()
        portal = ShortcutPortal(activate)
        portal._session, portal._configured, portal._version = '/ours', True, 2
        portal.Gio, portal.GLib, portal._connection = Mock(), Mock(), Mock()
        portal.GLib.Variant.side_effect = lambda signature, value: value
        portal._update([('toggle', {'trigger_description': 'F8'})])
        portal._configure()
        done = portal._connection.call.call_args.args[-1]
        portal._connection.call_finish.side_effect = RuntimeError('Cannot open settings')
        done(portal._connection, Mock())
        self.assertEqual(portal.snapshot()['state'], 'active')
        self.assertEqual(portal.snapshot()['trigger'], 'F8')
        args = Mock()
        args.unpack.return_value = ('/ours', 'toggle', 0, {})
        portal._signal(None, None, None, None, 'Activated', args)
        activate.assert_called_once()
        portal._session_closed()
        done(portal._connection, Mock())
        self.assertEqual(portal.snapshot()['trigger'], '')
        portal._signal(None, None, None, None, 'Activated', args)
        activate.assert_called_once()

    def test_failed_bind_retires_session_and_retry_creates_new_session(self):
        for outcome in ('cancel', 'timeout', 'method_error'):
            with self.subTest(outcome=outcome):
                portal = ShortcutPortal(Mock())
                portal._session = '/old'
                portal._session_subscription = 77
                portal._connection, portal.Gio, portal.GLib = Mock(), Mock(), Mock()
                portal._connection.get_unique_name.return_value = ':1.20'
                portal.GLib.Variant.side_effect = lambda signature, value: value
                portal._context = Mock()
                failure = []
                portal._call = lambda *_args, on_error, **_kwargs: failure.append(on_error)
                portal._request('BindShortcuts', '(oa(sa{sv})sa{sv})', ('/old', [], ''), {}, Mock())
                if outcome == 'cancel':
                    args = Mock()
                    args.unpack.return_value = (1, {})
                    response = portal._connection.signal_subscribe.call_args.args[-1]
                    response(None, None, None, None, None, args)
                elif outcome == 'timeout':
                    portal.GLib.timeout_source_new_seconds.return_value.set_callback.call_args.args[0]()
                else:
                    failure[0]()
                self.assertIsNone(portal._session)
                self.assertFalse(portal._requests)
                self.assertIsNone(portal._session_subscription)
                self.assertFalse(portal._pending_configure)
                calls = portal._connection.call.call_args_list
                self.assertTrue(any(call.args[1:4] == ('/old', 'org.freedesktop.portal.Session', 'Close') for call in calls))
                portal._restore = Mock()
                portal._configure()
                portal._restore.assert_called_once()
                self.assertTrue(portal._pending_configure)

    def test_late_closed_from_old_session_does_not_drop_replacement(self):
        portal = ShortcutPortal(Mock())
        portal._session = '/replacement'
        portal._session_subscription = 15
        portal._connection = Mock()
        portal._update([('toggle', {'trigger_description': 'F8'})])
        portal._session_closed(None, None, '/retired')
        self.assertEqual(portal._session, '/replacement')
        self.assertEqual(portal.snapshot()['state'], 'active')
        portal._connection.signal_unsubscribe.assert_not_called()

    def test_late_bind_method_failure_cannot_retire_replacement_session(self):
        portal = ShortcutPortal(Mock())
        portal._session = '/old'
        portal._connection, portal.Gio, portal.GLib = Mock(), Mock(), Mock()
        portal._connection.get_unique_name.return_value = ':1.20'
        portal.GLib.Variant.side_effect = lambda signature, value: value
        portal._context = Mock()
        portal._request('BindShortcuts', '(oa(sa{sv})sa{sv})', ('/old', [], ''), {}, Mock())
        done = portal._connection.call.call_args.args[-1]
        path, = portal._requests
        portal._finish_request(path)
        portal._session = '/replacement'
        portal._update([('toggle', {'trigger_description': 'F8'})])
        portal._connection.call_finish.side_effect = RuntimeError('old connection error')
        done(portal._connection, Mock())
        self.assertEqual(portal._session, '/replacement')
        self.assertEqual(portal.snapshot(), {'state': 'active', 'error': '', 'trigger': 'F8'})
