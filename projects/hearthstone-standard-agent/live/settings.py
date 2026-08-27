"""Small, non-secret desktop settings store."""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path

from live.types import GameMode


def default_settings_path() -> Path:
    if os.name == "nt":
        root = Path(os.environ.get("APPDATA", Path.home()))
    else:
        root = Path.home() / ".config"
    return root / "HearthstoneStandardAgent" / "settings.json"


@dataclass(slots=True)
class AppSettings:
    mode: str = GameMode.PRACTICE.value
    log_path: str = ""
    local_player_id: int | None = None
    overlay_x: int = 40
    overlay_y: int = 90

    @classmethod
    def load(cls, path: Path | None = None) -> "AppSettings":
        path = path or default_settings_path()
        if not path.exists():
            return cls()
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            allowed = {field for field in cls.__dataclass_fields__}
            settings = cls(**{key: value for key, value in payload.items() if key in allowed})
            GameMode(settings.mode)
            return settings
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            return cls()

    def save(self, path: Path | None = None) -> Path:
        path = path or default_settings_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = (json.dumps(asdict(self), ensure_ascii=False, indent=2) + "\n").encode()
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as handle:
            handle.write(payload)
            temporary = Path(handle.name)
        temporary.replace(path)
        return path
