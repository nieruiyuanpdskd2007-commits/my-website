from __future__ import annotations

import unittest

from live.advisor import LiveAdvisor
from live.main import demo_snapshot
from live.power_log import PowerLogParser
from live.tracker import PublicStateTracker
from live.types import GameMode, LiveSnapshot, ModePolicy


class LiveAdvisorTests(unittest.TestCase):
    def test_ladder_hard_gate_never_returns_move_advice(self) -> None:
        snapshot = demo_snapshot(GameMode.LADDER)
        recommendation = LiveAdvisor().recommend(snapshot)
        self.assertFalse(recommendation.enabled)
        self.assertIn("天梯保护模式", recommendation.primary)
        self.assertFalse(ModePolicy.for_mode(GameMode.LADDER).input_automation)

    def test_practice_mode_finds_visible_lethal(self) -> None:
        recommendation = LiveAdvisor().recommend(demo_snapshot(GameMode.PRACTICE))
        self.assertTrue(recommendation.enabled)
        self.assertIn("Fireball", recommendation.primary)
        self.assertGreaterEqual(recommendation.confidence, 0.9)

    def test_unknown_mode_is_safe_by_default(self) -> None:
        snapshot = LiveSnapshot(mode=GameMode.UNKNOWN, local_player_id=1, current_player_id=1)
        self.assertFalse(LiveAdvisor().recommend(snapshot).enabled)

    def test_power_log_parser_and_tracker_hide_opponent_hand_identity(self) -> None:
        parser = PowerLogParser()
        tracker = PublicStateTracker(GameMode.PRACTICE, local_player_id=1)
        entity = parser.feed(
            "D 12:00 FULL_ENTITY - Creating ID=42 CardID=SECRET_OPPONENT_CARD"
        )
        controller = parser.feed("D 12:00 TAG_CHANGE Entity=42 tag=CONTROLLER value=2")
        zone = parser.feed("D 12:00 TAG_CHANGE Entity=42 tag=ZONE value=HAND")
        self.assertIsNotNone(entity)
        self.assertIsNotNone(controller)
        self.assertIsNotNone(zone)
        tracker.apply(entity)  # type: ignore[arg-type]
        tracker.apply(controller)  # type: ignore[arg-type]
        snapshot = tracker.apply(zone)  # type: ignore[arg-type]
        public = snapshot.public_dict()
        self.assertEqual(public["enemy_hand_size"], 1)
        self.assertNotIn("SECRET_OPPONENT_CARD", str(public))


if __name__ == "__main__":
    unittest.main()
