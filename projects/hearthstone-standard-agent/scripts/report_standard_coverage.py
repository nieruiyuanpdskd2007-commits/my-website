#!/usr/bin/env python3
"""Measure knowledge and structured-effect coverage for the configured Standard pool."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from live.card_knowledge import StandardCardCatalog, effect_profile  # noqa: E402


def build_report(catalog: StandardCardCatalog) -> dict[str, object]:
    cards = catalog.standard_cards
    profiles = {card.card_id: effect_profile(card) for card in cards}
    recognized = [profile.coverage for profile in profiles.values()]
    low_confidence = sorted(
        card_id for card_id, profile in profiles.items() if profile.coverage < 0.5
    )
    manifest_path = ROOT / "data" / "knowledge" / "manifest.json"
    manifest = (
        json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.is_file() else {}
    )
    return {
        "schema_version": 1,
        "knowledge_snapshot_sha256": manifest.get("cards", {}).get("sha256", ""),
        "configured_standard_sets": sorted(catalog.active_set_ids),
        "standard_card_count": len(cards),
        "cards_with_name": sum(bool(card.name) for card in cards),
        "cards_with_text_or_vanilla_stats": sum(
            bool(card.text) or card.card_type in {"MINION", "WEAPON"} for card in cards
        ),
        "by_set": catalog.standard_set_counts,
        "by_type": dict(sorted(Counter(card.card_type for card in cards).items())),
        "structured_effect_coverage": {
            "average": round(sum(recognized) / len(recognized), 4) if recognized else 0.0,
            "cards_at_least_50_percent": sum(value >= 0.5 for value in recognized),
            "cards_at_least_80_percent": sum(value >= 0.8 for value in recognized),
            "low_confidence_card_count": len(low_confidence),
            "low_confidence_card_ids": low_confidence,
        },
        "legality_source": "Power.log OPTIONS packets",
        "legality_note": (
            "OPTIONS is the live client's authoritative list of available actions and targets; "
            "effect coverage measures ranking knowledge, not whether the client says an action is legal."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    catalog = StandardCardCatalog.load()
    if not catalog.source_available:
        raise SystemExit("validated card snapshot is missing; run scripts/update_data.py first")
    report = build_report(catalog)
    encoded = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        path = args.output if args.output.is_absolute() else ROOT / args.output
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(encoded, encoding="utf-8")
    print(
        f"standard_cards={report['standard_card_count']} "
        f"structured_average={report['structured_effect_coverage']['average']:.1%}"
    )


if __name__ == "__main__":
    main()
