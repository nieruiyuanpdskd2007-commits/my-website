from __future__ import annotations

import unittest

from live.advisor import LiveAdvisor
from live.card_knowledge import StandardCardCatalog, effect_profile
from live.power_log import PowerLogParser
from live.tracker import PublicStateTracker
from live.types import GameMode


class StandardLivePipelineTests(unittest.TestCase):
    def test_current_standard_catalog_is_loaded_from_validated_snapshot(self) -> None:
        catalog = StandardCardCatalog.load()
        self.assertTrue(catalog.source_available)
        self.assertGreaterEqual(catalog.standard_card_count, 1100)
        self.assertEqual(
            catalog.active_set_ids,
            {
                "CORE",
                "EMERALD_DREAM",
                "THE_LOST_CITY",
                "TIME_TRAVEL",
                "CATACLYSM",
                "ESCAPEFROM_VIOLET_HOLD",
                "EVENT",
            },
        )
        frostbolt = catalog.get("CORE_CS2_024")
        self.assertIsNotNone(frostbolt)
        self.assertTrue(frostbolt.standard)  # type: ignore[union-attr]
        self.assertEqual(effect_profile(frostbolt).damage, 3)

    def test_options_packets_create_authoritative_targeted_lethal(self) -> None:
        parser = PowerLogParser()
        tracker = PublicStateTracker(GameMode.PRACTICE, local_player_id=1)
        lines = [
            "D CREATE_GAME",
            "D FULL_ENTITY - Creating ID=10 CardID=CORE_CS2_024",
            "D TAG_CHANGE Entity=10 tag=CONTROLLER value=1",
            "D TAG_CHANGE Entity=10 tag=ZONE value=HAND",
            "D TAG_CHANGE Entity=10 tag=ZONE_POSITION value=1",
            "D TAG_CHANGE Entity=1 tag=PLAYER_ID value=1",
            "D TAG_CHANGE Entity=1 tag=CURRENT_PLAYER value=1",
            "D TAG_CHANGE Entity=1 tag=RESOURCES value=2",
            "D TAG_CHANGE Entity=1 tag=RESOURCES_USED value=0",
            "D FULL_ENTITY - Creating ID=30 CardID=HERO_08",
            "D TAG_CHANGE Entity=30 tag=CONTROLLER value=2",
            "D TAG_CHANGE Entity=30 tag=ZONE value=PLAY",
            "D TAG_CHANGE Entity=30 tag=CARDTYPE value=3",
            "D TAG_CHANGE Entity=30 tag=HEALTH value=3",
            "D OPTIONS_START id=44",
            "D option 0 type=END_TURN mainEntity=0 error=NONE",
            "D option 1 type=POWER mainEntity=[entityName=寒冰箭 id=10 zone=HAND zonePos=1 cardId=CORE_CS2_024 player=1] error=NONE",
            "D target 0 entity=[entityName=法师 id=30 zone=PLAY zonePos=0 cardId=HERO_08 player=2] error=NONE",
            "D OPTIONS_END",
        ]
        for line in lines:
            event = parser.feed(line)
            if event is not None:
                tracker.apply(event)

        snapshot = tracker.snapshot
        self.assertTrue(snapshot.legal_actions_authoritative)
        self.assertEqual(snapshot.mana, 2)
        self.assertEqual(snapshot.enemy_hero_hp, 3)
        frostbolt = next(action for action in snapshot.legal_actions if action.card_id == "CORE_CS2_024")
        self.assertEqual(frostbolt.kind, "play_card")
        self.assertEqual(frostbolt.target, "enemy_hero")
        self.assertEqual(frostbolt.damage, 3)
        self.assertTrue(frostbolt.authoritative)
        recommendation = LiveAdvisor().recommend(snapshot)
        self.assertTrue(recommendation.enabled)
        self.assertIn("寒冰箭", recommendation.primary)
        self.assertGreaterEqual(recommendation.confidence, 0.8)

    def test_options_error_is_filtered_out(self) -> None:
        parser = PowerLogParser()
        tracker = PublicStateTracker(GameMode.FRIENDLY, local_player_id=1)
        for line in (
            "D OPTIONS_START id=9",
            "D option 0 type=END_TURN mainEntity=0 error=NONE",
            "D option 1 type=POWER mainEntity=77 error=NOT_ENOUGH_MANA",
            "D OPTIONS_END",
        ):
            event = parser.feed(line)
            if event is not None:
                tracker.apply(event)
        self.assertEqual([action.kind for action in tracker.snapshot.legal_actions], ["end_turn"])

    def test_power_option_on_board_minion_is_not_mislabeled_as_attack(self) -> None:
        parser = PowerLogParser()
        tracker = PublicStateTracker(GameMode.PRACTICE, local_player_id=1)
        for line in (
            "D FULL_ENTITY - Creating ID=40 CardID=",
            "D TAG_CHANGE Entity=40 tag=CONTROLLER value=1",
            "D TAG_CHANGE Entity=40 tag=ZONE value=PLAY",
            "D TAG_CHANGE Entity=40 tag=CARDTYPE value=MINION",
            "D FULL_ENTITY - Creating ID=50 CardID=",
            "D TAG_CHANGE Entity=50 tag=CONTROLLER value=2",
            "D TAG_CHANGE Entity=50 tag=ZONE value=PLAY",
            "D TAG_CHANGE Entity=50 tag=CARDTYPE value=MINION",
            "D OPTIONS_START id=12",
            "D option 1 type=POWER mainEntity=[entityName=泰坦 id=40 zone=PLAY zonePos=1 cardId= player=1] error=NONE",
            "D target 0 entity=[entityName=目标 id=50 zone=PLAY zonePos=1 cardId= player=2] error=NONE",
            "D OPTIONS_END",
        ):
            event = parser.feed(line)
            if event is not None:
                tracker.apply(event)
        self.assertEqual(len(tracker.snapshot.legal_actions), 1)
        self.assertEqual(tracker.snapshot.legal_actions[0].kind, "minion_power")


if __name__ == "__main__":
    unittest.main()
