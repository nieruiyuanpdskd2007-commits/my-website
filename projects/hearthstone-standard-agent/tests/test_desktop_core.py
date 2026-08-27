from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from live.auth import LocalGuestAuth
from live.settings import AppSettings


class DesktopCoreTests(unittest.TestCase):
    def test_settings_round_trip_contains_no_credentials(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            settings = AppSettings(mode="friendly", log_path="C:/Logs/Power.log", local_player_id=1)
            settings.save(path)
            loaded = AppSettings.load(path)
            self.assertEqual(loaded.mode, "friendly")
            self.assertEqual(loaded.local_player_id, 1)
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertNotIn("password", payload)
            self.assertNotIn("access_token", payload)

    def test_unknown_settings_fields_are_ignored(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            path.write_text(
                json.dumps({"mode": "practice", "password": "must-not-load"}),
                encoding="utf-8",
            )
            loaded = AppSettings.load(path)
            self.assertEqual(loaded.mode, "practice")
            self.assertFalse(hasattr(loaded, "password"))

    def test_v02_auth_is_local_guest_only(self) -> None:
        provider = LocalGuestAuth()
        session = provider.current_session()
        self.assertFalse(session.authenticated)
        self.assertIsNone(session.access_token)
        with self.assertRaises(NotImplementedError):
            provider.sign_in("person@example.com", "not-stored")
        with self.assertRaises(NotImplementedError):
            provider.register("person@example.com", "not-stored")


if __name__ == "__main__":
    unittest.main()
