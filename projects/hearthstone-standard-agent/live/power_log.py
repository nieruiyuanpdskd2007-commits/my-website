"""Read-only Hearthstone Power.log tailer and conservative public-event parser."""

from __future__ import annotations

import os
import re
import time
from dataclasses import dataclass
from pathlib import Path
from threading import Event
from typing import Callable, Iterator


@dataclass(frozen=True, slots=True)
class PowerEvent:
    kind: str
    entity_id: int | None = None
    card_id: str = ""
    tag: str = ""
    value: str = ""


class PowerLogParser:
    ENTITY_RE = re.compile(r"(?:FULL_ENTITY|SHOW_ENTITY).*?ID=(\d+).*?CardID=([^\s]*)")
    TAG_RE = re.compile(
        r"TAG_CHANGE Entity=(?:\[.*?id=(\d+).*?\]|(\d+)) tag=([A-Z0-9_]+) value=([^\s]+)"
    )
    BLOCK_RE = re.compile(r"BLOCK_START BlockType=([A-Z_]+).*?EffectCardId=([^\s]+)")

    def feed(self, line: str) -> PowerEvent | None:
        if "CREATE_GAME" in line:
            return PowerEvent("game_start")
        if "TAG_CHANGE" in line and "tag=PLAYSTATE" in line:
            return PowerEvent("game_end")
        entity = self.ENTITY_RE.search(line)
        if entity:
            return PowerEvent("entity", int(entity.group(1)), entity.group(2))
        tag = self.TAG_RE.search(line)
        if tag:
            entity_id = int(tag.group(1) or tag.group(2))
            return PowerEvent("tag", entity_id, tag=tag.group(3), value=tag.group(4))
        block = self.BLOCK_RE.search(line)
        if block:
            return PowerEvent("block", card_id=block.group(2), tag="BLOCK_TYPE", value=block.group(1))
        return None


def discover_power_log() -> Path | None:
    """Look only in documented/configured log locations; never scan game memory."""
    candidates: list[Path] = []
    configured = os.environ.get("HEARTHSTONE_POWER_LOG")
    if configured:
        candidates.append(Path(configured))
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        candidates.extend(
            [
                Path(local_app_data) / "Blizzard" / "Hearthstone" / "Logs" / "Power.log",
                Path(local_app_data) / "Hearthstone" / "Logs" / "Power.log",
            ]
        )
    candidates.append(Path.home() / "Library" / "Logs" / "Blizzard" / "Hearthstone" / "Power.log")
    return next((path for path in candidates if path.is_file()), None)


class LogTailer:
    def __init__(self, path: str | Path, *, poll_seconds: float = 0.2, from_start: bool = False):
        self.path = Path(path)
        self.poll_seconds = poll_seconds
        self.from_start = from_start

    def lines(self, stop: Event) -> Iterator[str]:
        with self.path.open(encoding="utf-8", errors="replace") as handle:
            if not self.from_start:
                handle.seek(0, 2)
            while not stop.is_set():
                line = handle.readline()
                if line:
                    yield line.rstrip("\n")
                else:
                    stop.wait(self.poll_seconds)

    def follow(self, stop: Event, callback: Callable[[str], None]) -> None:
        while not stop.is_set():
            if not self.path.exists():
                stop.wait(min(1.0, self.poll_seconds * 5))
                continue
            try:
                for line in self.lines(stop):
                    callback(line)
            except (OSError, UnicodeError):
                time.sleep(self.poll_seconds)
