"""Importer for user-exported 炉石盒子/meta statistics.

No scraping or private endpoint is used.  Export data you are allowed to use as
CSV/JSON, then point this loader at that file.
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class MetaRow:
    snapshot_date: str
    mode: str
    rank_band: str
    deck_id: str
    deck_name: str
    hero_class: str
    games: int
    win_rate: float
    opponent_class: str = ""
    matchup_win_rate: float | None = None
    card_id: str = ""
    mulligan_keep_rate: float | None = None
    drawn_win_rate: float | None = None


class BoxMetaStats:
    def __init__(self, rows: list[MetaRow]):
        self.rows = rows

    @classmethod
    def load(cls, path: str | Path) -> "BoxMetaStats":
        path = Path(path)
        if path.suffix.lower() == ".csv":
            with path.open(encoding="utf-8-sig", newline="") as handle:
                payload = list(csv.DictReader(handle))
        elif path.suffix.lower() == ".json":
            raw = json.loads(path.read_text(encoding="utf-8"))
            payload = raw.get("rows", raw) if isinstance(raw, dict) else raw
        else:
            raise ValueError("Box export must be .csv or .json")
        return cls([cls._parse_row(row) for row in payload])

    def matchup_prior(self, deck_id: str, opponent_class: str) -> float | None:
        rows = [
            row
            for row in self.rows
            if row.deck_id == deck_id
            and row.opponent_class.upper() == opponent_class.upper()
            and row.matchup_win_rate is not None
        ]
        if not rows:
            return None
        games = sum(max(row.games, 1) for row in rows)
        return sum(row.matchup_win_rate * max(row.games, 1) for row in rows) / games  # type: ignore[operator]

    def mulligan_keep_rate(self, deck_id: str, card_id: str) -> float | None:
        rows = [
            row.mulligan_keep_rate
            for row in self.rows
            if row.deck_id == deck_id and row.card_id == card_id and row.mulligan_keep_rate is not None
        ]
        return None if not rows else sum(rows) / len(rows)

    def top_decks(self, *, min_games: int = 200, limit: int = 10) -> list[MetaRow]:
        candidates = [row for row in self.rows if row.games >= min_games and not row.card_id]
        return sorted(candidates, key=lambda row: (row.win_rate, row.games), reverse=True)[:limit]

    @staticmethod
    def _parse_row(row: dict[str, Any]) -> MetaRow:
        required = {"snapshot_date", "mode", "rank_band", "deck_id", "deck_name", "hero_class"}
        missing = sorted(required - row.keys())
        if missing:
            raise ValueError(f"Meta row is missing columns: {', '.join(missing)}")
        return MetaRow(
            snapshot_date=str(row["snapshot_date"]),
            mode=str(row["mode"]),
            rank_band=str(row["rank_band"]),
            deck_id=str(row["deck_id"]),
            deck_name=str(row["deck_name"]),
            hero_class=str(row["hero_class"]),
            games=int(row.get("games") or 0),
            win_rate=BoxMetaStats._rate(row.get("win_rate")) or 0.0,
            opponent_class=str(row.get("opponent_class") or ""),
            matchup_win_rate=BoxMetaStats._rate(row.get("matchup_win_rate")),
            card_id=str(row.get("card_id") or ""),
            mulligan_keep_rate=BoxMetaStats._rate(row.get("mulligan_keep_rate")),
            drawn_win_rate=BoxMetaStats._rate(row.get("drawn_win_rate")),
        )

    @staticmethod
    def _rate(value: Any) -> float | None:
        if value is None or value == "":
            return None
        text = str(value).strip()
        result = float(text[:-1]) / 100.0 if text.endswith("%") else float(text)
        if result > 1.0:
            result /= 100.0
        if not 0.0 <= result <= 1.0:
            raise ValueError(f"Win/keep rate must be in [0, 1], got {value}")
        return result
