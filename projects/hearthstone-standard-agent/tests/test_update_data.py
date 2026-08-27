from __future__ import annotations

import gzip
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("update_data", ROOT / "scripts" / "update_data.py")
assert SPEC and SPEC.loader
update_data = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(update_data)


class UpdateDataTests(unittest.TestCase):
    def test_normalize_rejects_duplicate_ids(self) -> None:
        cards = [
            {"id": "A", "name": "A", "type": "MINION", "set": "CORE"},
            {"id": "A", "name": "B", "type": "SPELL", "set": "CORE"},
        ]
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            update_data.normalize_cards(json.dumps(cards).encode(), minimum_card_count=1)

    def test_card_snapshot_is_deterministic_and_validated_before_write(self) -> None:
        cards = [
            {
                "id": f"CARD_{index:03d}",
                "dbfId": index,
                "name": f"Card {index}",
                "type": "MINION",
                "set": "CORE" if index % 2 else "DEMO_SET",
                "cost": index % 10,
                "attack": 1,
                "health": 1,
            }
            for index in range(100)
        ]
        normalized, discovered = update_data.normalize_cards(
            json.dumps(cards).encode(), minimum_card_count=100
        )
        first = update_data.deterministic_gzip_json(normalized)
        second = update_data.deterministic_gzip_json(list(reversed(normalized)))
        self.assertNotEqual(first, second)
        self.assertEqual(discovered, {"CORE", "DEMO_SET"})
        self.assertEqual(len(json.loads(gzip.decompress(first))), 100)

        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "cards.json.gz"
            target.write_bytes(b"previous-good-data")
            bad = json.dumps(cards[:2]).encode()
            with self.assertRaisesRegex(ValueError, "suspiciously small"):
                update_data.normalize_cards(bad, minimum_card_count=100)
            self.assertEqual(target.read_bytes(), b"previous-good-data")

    def test_meta_validator_requires_standard_mode(self) -> None:
        header = (
            "snapshot_date,mode,rank_band,deck_id,deck_name,hero_class,games,win_rate\n"
        )
        good = header + "2026-08-27,STANDARD,ALL,d1,Deck,MAGE,300,52.1%\n"
        self.assertEqual(update_data.validate_meta_csv(good.encode()), 1)
        bad = header + "2026-08-27,WILD,ALL,d1,Deck,MAGE,300,52.1%\n"
        with self.assertRaisesRegex(ValueError, "not STANDARD"):
            update_data.validate_meta_csv(bad.encode())


if __name__ == "__main__":
    unittest.main()
