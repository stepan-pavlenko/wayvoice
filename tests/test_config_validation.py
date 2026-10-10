"""Malformed hand-edited settings remain recoverable without rewriting the file."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from wayvoice import config, languages, i18n
from wayvoice.daemon import _recording_limit


class ConfigValidationTests(unittest.TestCase):
    def test_invalid_known_values_are_reported_without_losing_unknown_settings(self):
        bad_values = {"language": 42, "ui_language": [], "notify": "false",
                      "model": {}, "max_recording_sec": float("inf"),
                      "transcription_timeout_sec": float("nan")}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            raw = json.dumps(dict(bad_values, extra={"keep": True}, device="cpu"))
            path.write_text(raw)
            with mock.patch.object(config, "config_path", return_value=path):
                loaded = config.load_config()
                for key in bad_values:
                    self.assertEqual(loaded[key], config.DEFAULTS[key])
                    self.assertIn(key, config.config_error())
                self.assertEqual(loaded["extra"], {"keep": True})
                self.assertEqual(loaded["device"], "cpu")
                self.assertEqual(path.read_text(), raw)
                path.write_text('{"beam_size": "3", "language": "en"}')
                self.assertEqual(config.load_config()["beam_size"], "3")
                self.assertEqual(config.config_error(), "")

    def test_nonfinite_numbers_fall_back_and_recording_refuses_them(self):
        for value in (float("inf"), float("-inf"), float("nan"), "Infinity", "NaN"):
            with self.subTest(value=value):
                self.assertEqual(config.number({"limit": value}, "limit", 120), 120)
                self.assertEqual(config.number({"limit": value}, "limit", 120.0), 120.0)
                with self.assertRaisesRegex(ValueError, "max_recording_sec"):
                    _recording_limit({"max_recording_sec": value})

    def test_language_normalizers_defend_direct_callers_too(self):
        for value in (42, [], {}, True):
            with self.subTest(value=value), mock.patch.object(i18n.locale, "getlocale", return_value=("en_US", "UTF-8")):
                self.assertEqual(languages.normalize(value), "auto")
                self.assertFalse(languages.is_valid(value))
                self.assertEqual(i18n.resolve_language(value), "en")
