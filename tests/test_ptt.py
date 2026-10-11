"""Hold gestures own only the take they successfully started."""
import queue
import unittest
from unittest.mock import Mock, patch

from wayvoice.daemon import WayVoiceDaemon
from wayvoice.shortcut_portal import ShortcutPortal


class HoldTests(unittest.TestCase):
    def setUp(self):
        self.daemon = WayVoiceDaemon()
        self.daemon.recorder = Mock(recording=False)
        self.daemon._record_started = 0
        def start():
            self.daemon.recorder.recording = True
            self.daemon._record_started += 1
            return {'ok': True}
        def stop():
            self.daemon.recorder.recording = False
            return {'ok': True}
        self.daemon.start_recording = Mock(side_effect=start)
        self.daemon.stop_recording = Mock(side_effect=stop)
        self.daemon.cancel = Mock(side_effect=stop)

    def test_press_repeat_release_are_idempotent(self):
        for _ in range(3):
            self.daemon._ptt_press()
            self.daemon._drain_ptt()
        self.daemon.start_recording.assert_called_once()
        for _ in range(3):
            self.daemon._ptt_release()
            self.daemon._drain_ptt()
        self.daemon.stop_recording.assert_called_once()

    def test_short_gesture_before_worker_runs_does_not_open_microphone(self):
        self.daemon._ptt_press()
        self.daemon._ptt_release()
        self.daemon._drain_ptt()
        self.daemon.start_recording.assert_not_called()

    def test_release_does_not_touch_another_recording(self):
        self.daemon._ptt_press()
        self.daemon._drain_ptt()
        self.daemon._record_started += 1  # Old take ended; UI opened another.
        self.daemon._ptt_release()
        self.daemon._drain_ptt()
        self.daemon.stop_recording.assert_not_called()

    def test_busy_press_and_failed_start_never_claim_existing_take(self):
        self.daemon.busy = True
        self.daemon._ptt_press()
        self.daemon._drain_ptt()
        self.daemon.busy = False
        self.daemon.recorder.recording = True
        self.daemon._ptt_release()
        self.daemon._drain_ptt()
        self.daemon.stop_recording.assert_not_called()
        self.daemon.recorder.recording = False
        self.daemon.start_recording.side_effect = lambda: {'ok': False}
        self.daemon._ptt_press()
        self.daemon._drain_ptt()
        self.assertIsNone(self.daemon._ptt_take)

    def test_disconnect_cancels_instead_of_transcribing(self):
        self.daemon._ptt_press()
        self.daemon._drain_ptt()
        self.daemon._ptt_disconnect()
        self.daemon._drain_ptt()
        self.daemon.cancel.assert_called_once()
        self.daemon.stop_recording.assert_not_called()

    def test_saturated_command_queue_cannot_drop_release(self):
        self.daemon._commands = queue.Queue(maxsize=1)
        self.daemon._commands.put((None, 'status'))
        with patch('wayvoice.daemon.load_config', return_value={'shortcut_mode': 'hold'}):
            self.daemon._portal_activation()
        self.daemon._drain_ptt()
        self.daemon._ptt_release()
        self.daemon._drain_ptt()
        self.daemon.stop_recording.assert_called_once()

    def test_portal_routes_release_and_cancels_on_binding_loss(self):
        release, disconnect = Mock(), Mock()
        portal = ShortcutPortal(Mock(), release, disconnect)
        portal._session = '/ours'
        portal._update([('toggle', {'trigger_description': 'F8'})])
        parameters = Mock()
        parameters.unpack.return_value = ('/ours', 'toggle', 0, {})
        portal._signal(None, None, None, None, 'Deactivated', parameters)
        release.assert_called_once()
        portal._update([])
        disconnect.assert_called_once()

    def test_shutdown_does_not_start_pending_press(self):
        self.daemon._ptt_press()
        self.daemon._shutdown.set()
        self.daemon._drain_ptt()
        self.daemon.start_recording.assert_not_called()

    def test_failed_stop_keeps_ownership_for_retry(self):
        self.daemon._ptt_press()
        self.daemon._drain_ptt()
        self.daemon.stop_recording.side_effect = lambda: {'ok': False, 'error': 'temporary'}
        self.daemon._ptt_release()
        self.assertFalse(self.daemon._drain_ptt()['ok'])
        self.assertIsNotNone(self.daemon._ptt_take)
        self.daemon.stop_recording.side_effect = lambda: {'ok': True}
        self.daemon._drain_ptt()
        self.assertIsNone(self.daemon._ptt_take)

    def test_busy_and_failed_start_report_failure_to_manual_binding(self):
        self.daemon.busy = True
        self.daemon._ptt_press()
        self.assertFalse(self.daemon._drain_ptt()['ok'])
        self.daemon._ptt_release()
        self.daemon._drain_ptt()
        self.daemon.busy = False
        self.daemon.start_recording.side_effect = lambda: {'ok': False, 'error': 'Missing model'}
        self.daemon._ptt_press()
        self.assertEqual(self.daemon._drain_ptt()['error'], 'Missing model')

    def test_unexpected_hold_exception_does_not_kill_command_worker(self):
        self.daemon.start_recording.side_effect = RuntimeError('recorder failed')
        self.daemon._ptt_press()
        commands = queue.Queue()
        commands.put((None, 'status'))
        commands.put(None)
        self.daemon.dispatch = Mock(return_value={'ok': True})
        self.daemon._command_loop(commands)
        self.daemon.dispatch.assert_called_once_with('status')
        self.assertIn('recorder failed', self.daemon.last_error)
