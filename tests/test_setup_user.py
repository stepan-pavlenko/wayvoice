"""Expected manual desktop setup must not fail dependency integration."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


class SetupUserTests(unittest.TestCase):
    def test_manual_desktops_succeed_but_gnome_registration_failure_is_reported(self):
        script = Path(__file__).resolve().parents[1] / "scripts/setup-user"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name, body in (("wayvoice", "echo manual-command; exit 1"),
                               ("systemctl", "exit 0")):
                target = root / name
                target.write_text("#!/bin/sh\n" + body + "\n")
                target.chmod(0o700)
            for desktop, expected in (("KDE", 0), ("sway", 0), ("GNOME", 1)):
                with self.subTest(desktop=desktop):
                    env = dict(os.environ, XDG_CURRENT_DESKTOP=desktop,
                               WAYVOICE_BINDIR=str(root), PATH=str(root) + ":/usr/bin:/bin")
                    # Copy so sibling helper resolution uses the controlled executable.
                    copied = root / "setup-user"
                    copied.write_text(script.read_text())
                    result = subprocess.run(["/bin/sh", str(copied)], env=env,
                                            capture_output=True, text=True, timeout=5)
                    self.assertEqual(result.returncode, expected, result.stderr)
                    self.assertIn("manual-command", result.stdout + result.stderr)
