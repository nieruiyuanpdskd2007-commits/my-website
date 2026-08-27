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
    packet_id: int | None = None
    index: int | None = None
    option_type: str = ""
    source_entity_id: int | None = None
    target_entity_id: int | None = None
    suboption_index: int | None = None
    error: str = "NONE"


class PowerLogParser:
    ENTITY_RE = re.compile(
        r"(?:FULL_ENTITY|SHOW_ENTITY|CHANGE_ENTITY).*?(?:ID|id)=(\d+).*?"
        r"(?:CardID|cardId)=([^\s\]]*)",
        re.IGNORECASE,
    )
    TAG_RE = re.compile(
        r"TAG_CHANGE Entity=(?:\[.*?id=(\d+).*?\]|(\d+)) tag=([A-Z0-9_]+) value=([^\s]+)"
    )
    BLOCK_RE = re.compile(r"BLOCK_START BlockType=([A-Z_]+).*?EffectCardId=([^\s]+)")
    OPTIONS_START_RE = re.compile(r"OPTIONS_START.*?id=(\d+)", re.IGNORECASE)
    OPTION_RE = re.compile(r"\boption\s+(\d+)\s+type=([A-Z_]+)\s+mainEntity=(.*)", re.IGNORECASE)
    SUBOPTION_RE = re.compile(r"\bsubOption\s+(\d+)\s+entity=(.*)", re.IGNORECASE)
    TARGET_RE = re.compile(r"\btarget\s+(\d+)\s+entity=(.*)", re.IGNORECASE)

    def __init__(self) -> None:
        self._packet_id: int | None = None
        self._option_index: int | None = None
        self._suboption_index: int | None = None

    def feed(self, line: str) -> PowerEvent | None:
        options_start = self.OPTIONS_START_RE.search(line)
        if options_start:
            self._packet_id = int(options_start.group(1))
            self._option_index = None
            self._suboption_index = None
            return PowerEvent("options_start", packet_id=self._packet_id)
        if "OPTIONS_END" in line:
            event = PowerEvent("options_end", packet_id=self._packet_id)
            self._option_index = None
            self._suboption_index = None
            return event
        option = self.OPTION_RE.search(line)
        if option:
            self._option_index = int(option.group(1))
            self._suboption_index = None
            tail = option.group(3)
            return PowerEvent(
                "option",
                card_id=_card_id(tail),
                packet_id=self._packet_id,
                index=self._option_index,
                option_type=option.group(2).upper(),
                source_entity_id=_entity_id(tail),
                error=_error(tail),
                value=_entity_name(tail),
            )
        suboption = self.SUBOPTION_RE.search(line)
        if suboption and self._option_index is not None:
            self._suboption_index = int(suboption.group(1))
            tail = suboption.group(2)
            return PowerEvent(
                "suboption",
                card_id=_card_id(tail),
                packet_id=self._packet_id,
                index=self._option_index,
                source_entity_id=_entity_id(tail),
                suboption_index=self._suboption_index,
                error=_error(tail),
                value=_entity_name(tail),
            )
        target = self.TARGET_RE.search(line)
        if target and self._option_index is not None:
            tail = target.group(2)
            return PowerEvent(
                "option_target",
                packet_id=self._packet_id,
                index=self._option_index,
                target_entity_id=_entity_id(tail),
                suboption_index=self._suboption_index,
                value=target.group(1),
                error=_error(tail),
            )
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


def _entity_id(value: str) -> int | None:
    bracketed = re.search(r"\bid=(\d+)\b", value, re.IGNORECASE)
    if bracketed:
        return int(bracketed.group(1))
    plain = re.match(r"\s*(\d+)\b", value)
    return int(plain.group(1)) if plain else None


def _card_id(value: str) -> str:
    match = re.search(r"\bcard(?:Id|ID)=([^\s\]]*)", value, re.IGNORECASE)
    return match.group(1) if match else ""


def _error(value: str) -> str:
    match = re.search(r"\berror=([A-Z0-9_]+)", value, re.IGNORECASE)
    return match.group(1).upper() if match else "NONE"


def _entity_name(value: str) -> str:
    match = re.search(r"\bentityName=(.*?)\s+id=\d+", value, re.IGNORECASE)
    return match.group(1).strip() if match else ""


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
