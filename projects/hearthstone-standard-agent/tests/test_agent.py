from __future__ import annotations

import unittest

from agents.random_agent import RandomAgent
from agents.rule_agent import RuleAgent
from env.action_space import Action, ActionKind
from env.card_db import CardDatabase
from env.hearthstone_env import HearthstoneEnv
from env.simulator import GameEngine, IllegalAction, MinionState
from env.state_encoder import EntityTokenEncoder, FlatStateEncoder
from training.self_play import play_game


def fixtures() -> tuple[CardDatabase, object, object]:
    db = CardDatabase.load()
    return db, db.load_deck("data/decks/mage.json"), db.load_deck("data/decks/warrior.json")


class AgentPipelineTests(unittest.TestCase):
    def test_complete_games_terminate_and_emit_training_samples(self) -> None:
        db, mage, warrior = fixtures()
        env = HearthstoneEnv(db, mage, warrior, max_turns=80)
        for seed in range(8):
            result = play_game(
                env,
                (RuleAgent(seed=seed), RandomAgent(seed=seed + 100)),
                seed=seed,
            )
            self.assertIn(result.winner, (0, 1, None))
            self.assertLessEqual(result.turns, 81)
            self.assertGreater(result.actions, 0)
            self.assertEqual(result.actions, len(result.samples))
            self.assertTrue(all(sample.outcome in (-1.0, 0.0, 1.0) for sample in result.samples))

    def test_opponent_hand_is_hidden(self) -> None:
        db, mage, warrior = fixtures()
        engine = GameEngine(db, mage, warrior, seed=1)
        engine.initialize()
        observation = engine.observation(0)
        self.assertEqual(observation["opponent"]["hand"], [])
        self.assertEqual(observation["opponent"]["hand_size"], 5)  # four cards + coin
        tokens = EntityTokenEncoder().encode(observation)
        self.assertEqual(sum(token["zone"] == "ENEMY_HAND" for token in tokens), 1)
        self.assertFalse(any(token["zone"] == "OPPONENT_HAND_CARD" for token in tokens))

    def test_taunt_restricts_attack_targets(self) -> None:
        db, mage, warrior = fixtures()
        engine = GameEngine(db, mage, warrior, seed=2)
        engine.initialize()
        engine.mulligan(0, [])
        engine.mulligan(1, [])
        engine.start()
        engine.players[0].board.append(MinionState(1001, "BOULDER_COLOSSUS", 6, 7, 7, 1))
        engine.players[1].board.append(MinionState(1002, "STONE_GUARD", 2, 4, 4, 0))
        attacks = [action for action in engine.legal_actions() if action.kind == ActionKind.ATTACK]
        self.assertTrue(attacks)
        self.assertEqual({action.target for action in attacks}, {"minion:1002"})

    def test_illegal_action_is_rejected(self) -> None:
        db, mage, warrior = fixtures()
        engine = GameEngine(db, mage, warrior, seed=3)
        engine.initialize()
        engine.mulligan(0, [])
        engine.mulligan(1, [])
        engine.start()
        with self.assertRaises(IllegalAction):
            engine.apply(Action(ActionKind.PLAY_CARD, source=999999))

    def test_flat_encoder_has_stable_dimension(self) -> None:
        db, mage, warrior = fixtures()
        engine = GameEngine(db, mage, warrior, seed=4)
        engine.initialize()
        lengths = {len(FlatStateEncoder().encode(engine.observation(player))) for player in (0, 1)}
        self.assertEqual(lengths, {22})


if __name__ == "__main__":
    unittest.main()
