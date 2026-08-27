"""Privacy-minimized public-event recorder for post-game review."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from live.power_log import PowerEvent


class PublicReplayRecorder:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, event: PowerEvent) -> None:
        # Parsed fields exclude account IDs and raw log text by construction.
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(event), ensure_ascii=False) + "\n")
