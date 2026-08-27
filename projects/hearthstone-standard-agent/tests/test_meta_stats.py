from __future__ import annotations

import unittest
from pathlib import Path

from env.meta_stats import BoxMetaStats


ROOT = Path(__file__).resolve().parents[1]


class MetaStatsTests(unittest.TestCase):
    def test_example_box_export(self) -> None:
        stats = BoxMetaStats.load(ROOT / "data" / "meta" / "example.csv")
        self.assertAlmostEqual(stats.matchup_prior("demo_mage", "WARRIOR") or 0, 0.49)
        self.assertAlmostEqual(stats.mulligan_keep_rate("demo_mage", "ARCANE_BOLT") or 0, 0.61)


if __name__ == "__main__":
    unittest.main()
