#!/usr/bin/env python3
"""Safely refresh external card knowledge and optional box/meta statistics.

The updater validates everything in memory, writes atomically, and preserves the
previous snapshot when a source is unavailable or malformed.  It updates knowledge
data only; executable card mechanics and model code never self-modify.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import io
import json
import os
import tempfile
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "data" / "update_sources.json"
MANIFEST_PATH = ROOT / "data" / "knowledge" / "manifest.json"
USER_AGENT = "HearthstoneStandardAgent/0.1 (+https://nieruiyuan.com)"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def download(url: str, timeout: float) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
        if getattr(response, "status", 200) != 200:
            raise RuntimeError(f"Source returned HTTP {response.status}: {url}")
        return response.read()


def normalize_cards(payload: bytes, *, minimum_card_count: int) -> tuple[list[dict[str, Any]], set[str]]:
    raw = json.loads(payload.decode("utf-8-sig"))
    if not isinstance(raw, list):
        raise ValueError("HearthstoneJSON payload must be a list")
    cards: list[dict[str, Any]] = []
    seen: set[str] = set()
    sets: set[str] = set()
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            raise ValueError(f"Card at index {index} is not an object")
        missing = [field for field in ("id", "name", "type", "set") if not item.get(field)]
        if missing:
            raise ValueError(f"Card at index {index} is missing: {', '.join(missing)}")
        card_id = str(item["id"])
        if card_id in seen:
            raise ValueError(f"Duplicate card id: {card_id}")
        seen.add(card_id)
        set_id = str(item["set"])
        sets.add(set_id)
        cards.append(
            {
                key: item[key]
                for key in (
                    "id",
                    "dbfId",
                    "name",
                    "text",
                    "flavor",
                    "cardClass",
                    "classes",
                    "type",
                    "set",
                    "rarity",
                    "cost",
                    "attack",
                    "health",
                    "durability",
                    "mechanics",
                    "races",
                    "spellSchool",
                    "collectible",
                )
                if key in item
            }
        )
    if len(cards) < minimum_card_count:
        raise ValueError(
            f"Card payload is suspiciously small: {len(cards)} < {minimum_card_count}"
        )
    cards.sort(key=lambda card: card["id"])
    return cards, sets


def deterministic_gzip_json(value: Any) -> bytes:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    buffer = io.BytesIO()
    with gzip.GzipFile(fileobj=buffer, mode="wb", mtime=0) as archive:
        archive.write(raw)
    return buffer.getvalue()


def atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as handle:
        handle.write(payload)
        temporary = Path(handle.name)
    temporary.replace(path)


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def validate_meta_csv(payload: bytes) -> int:
    text = payload.decode("utf-8-sig")
    rows = list(csv.DictReader(io.StringIO(text)))
    required = {
        "snapshot_date",
        "mode",
        "rank_band",
        "deck_id",
        "deck_name",
        "hero_class",
        "games",
        "win_rate",
    }
    if not rows:
        raise ValueError("Meta export contains no data rows")
    missing = required - set(rows[0])
    if missing:
        raise ValueError(f"Meta export is missing columns: {', '.join(sorted(missing))}")
    for index, row in enumerate(rows, start=2):
        if row.get("mode", "").upper() != "STANDARD":
            raise ValueError(f"Meta row {index} is not STANDARD mode")
        games = int(row.get("games") or 0)
        if games < 0:
            raise ValueError(f"Meta row {index} has negative games")
        _parse_rate(row.get("win_rate"), index)
    return len(rows)


def _parse_rate(value: str | None, row_number: int) -> float:
    if value is None or not value.strip():
        raise ValueError(f"Meta row {row_number} has no win_rate")
    text = value.strip()
    result = float(text[:-1]) / 100 if text.endswith("%") else float(text)
    if result > 1:
        result /= 100
    if not 0 <= result <= 1:
        raise ValueError(f"Meta row {row_number} has invalid win_rate: {value}")
    return result


def update_cards(
    payload: bytes,
    *,
    output_path: Path,
    source_url: str,
    minimum_card_count: int,
    now: str,
) -> tuple[dict[str, Any], bool]:
    cards, discovered_sets = normalize_cards(payload, minimum_card_count=minimum_card_count)
    standard_config = load_json(ROOT / "data" / "standard_sets.json")
    active_sets = set(standard_config["active_set_ids"])
    for card in cards:
        card["standard_config_match"] = card["set"] in active_sets
    encoded = deterministic_gzip_json(cards)
    previous = load_json(MANIFEST_PATH) if MANIFEST_PATH.exists() else {}
    previous_cards_manifest = previous.get("cards", {})
    previous_discovered_sets = set(previous_cards_manifest.get("discovered_sets", []))
    previous_pending_sets = set(previous_cards_manifest.get("pending_set_review", []))
    newly_discovered_sets = discovered_sets - previous_discovered_sets
    pending_set_review = (previous_pending_sets | newly_discovered_sets) - active_sets
    content_hash = sha256(encoded)
    content_changed = previous.get("cards", {}).get("sha256") != content_hash
    if content_changed:
        atomic_write(output_path, encoded)
    cards_manifest = {
        "source": source_url,
        "sha256": content_hash,
        "card_count": len(cards),
        "discovered_sets": sorted(discovered_sets),
        "configured_standard_sets": sorted(active_sets),
        "configured_standard_card_count": sum(
            card["standard_config_match"] for card in cards
        ),
        "pending_set_review": sorted(pending_set_review),
        "rotation_review_required": bool(pending_set_review),
    }
    previous_cards = dict(previous.get("cards", {}))
    previous_cards.pop("snapshot_updated_at", None)
    changed = previous_cards != cards_manifest
    if changed:
        cards_manifest["snapshot_updated_at"] = now
        manifest = dict(previous)
        manifest.update({"schema_version": 1, "updated_at": now, "cards": cards_manifest})
        atomic_write(
            MANIFEST_PATH,
            (json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode(),
        )
    else:
        manifest = previous
    return manifest, changed


def update_meta(
    payload: bytes, *, output_path: Path, source: str, now: str
) -> tuple[dict[str, Any], bool]:
    row_count = validate_meta_csv(payload)
    manifest = load_json(MANIFEST_PATH) if MANIFEST_PATH.exists() else {"schema_version": 1}
    meta_manifest = {
        "source": source,
        "sha256": sha256(payload),
        "row_count": row_count,
    }
    previous_meta = dict(manifest.get("meta", {}))
    previous_meta.pop("snapshot_updated_at", None)
    changed = previous_meta != meta_manifest
    if changed:
        atomic_write(output_path, payload)
        meta_manifest["snapshot_updated_at"] = now
        manifest["updated_at"] = now
        manifest["meta"] = meta_manifest
        atomic_write(
            MANIFEST_PATH,
            (json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode(),
        )
    return manifest, changed


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cards-file", type=Path, help="offline/test source instead of network")
    parser.add_argument("--cards-url", help="override configured HearthstoneJSON URL")
    parser.add_argument("--box-file", type=Path, help="authorized local box/meta CSV")
    parser.add_argument("--box-url", help="authorized meta URL; defaults to BOX_META_URL")
    parser.add_argument("--timeout", type=float, default=30.0)
    args = parser.parse_args()

    config = load_json(CONFIG_PATH)
    cards_url = args.cards_url or config["cards"]["url"]
    cards_payload = (
        args.cards_file.read_bytes() if args.cards_file else download(cards_url, args.timeout)
    )
    now = datetime.now(UTC).replace(microsecond=0).isoformat()
    manifest, cards_changed = update_cards(
        cards_payload,
        output_path=ROOT / config["cards"]["output"],
        source_url=cards_url,
        minimum_card_count=int(config["cards"]["minimum_card_count"]),
        now=now,
    )
    print(
        f"cards={manifest['cards']['card_count']} changed={cards_changed} "
        f"rotation_review_required={manifest['cards']['rotation_review_required']}"
    )

    box_url = args.box_url or os.environ.get(config["meta"]["url_environment_variable"], "")
    if args.box_file or box_url:
        meta_payload = args.box_file.read_bytes() if args.box_file else download(box_url, args.timeout)
        manifest, meta_changed = update_meta(
            meta_payload,
            output_path=ROOT / config["meta"]["output"],
            source="user-authorized box/meta export",
            now=now,
        )
        print(f"meta_rows={manifest['meta']['row_count']} changed={meta_changed}")


if __name__ == "__main__":
    main()
