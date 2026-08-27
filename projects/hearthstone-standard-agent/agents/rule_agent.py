"""Interpretable V0.1 heuristic agent.

Priority follows the project brief: immediate lethal, favourable trades, efficient
mana use, face damage, then end turn.
"""

from __future__ import annotations

import random

from env.action_space import Action, ActionKind
from env.simulator import GameEngine


class RuleAgent:
    def __init__(self, *, seed: int = 0, name: str = "RuleAgent"):
        self.rng = random.Random(seed)
        self.name = name

    def choose_mulligan(self, observation: dict) -> list[int]:
        return [
            card["entity_id"]
            for card in observation["me"]["hand"]
            if card["card_id"] != "THE_COIN" and card["cost"] > 3
        ]

    def choose_action(
        self, observation: dict, legal_actions: list[Action], engine: GameEngine
    ) -> Action:
        player = observation["player"]
        winning = [action for action in legal_actions if self._wins_now(engine, action, player)]
        if winning:
            return self.rng.choice(winning)

        scored = [(self._score(action, engine, player), action) for action in legal_actions]
        best_score = max(score for score, _ in scored)
        choices = [action for score, action in scored if score == best_score]
        return self.rng.choice(choices)

    @staticmethod
    def _wins_now(engine: GameEngine, action: Action, player: int) -> bool:
        branch = engine.clone()
        branch.apply(action)
        return branch.terminal and branch.winner == player

    @staticmethod
    def _score(action: Action, engine: GameEngine, player: int) -> float:
        me = engine.players[player]
        enemy = engine.players[1 - player]
        enemy_hero = f"hero:{1 - player}"

        if action.kind == ActionKind.ATTACK:
            attacker = engine._find_minion(player, action.source)
            if action.target == enemy_hero:
                return 45.0 + attacker.attack
            defender = engine._minion_from_ref(action.target)
            kills = attacker.attack >= defender.health
            survives = attacker.health > defender.attack
            return 80.0 + defender.attack * 3 + defender.health + (15 if kills else 0) + (8 if survives else 0)

        if action.kind == ActionKind.HERO_ATTACK:
            assert me.weapon is not None
            if action.target == enemy_hero:
                return 43.0 + me.weapon.attack
            defender = engine._minion_from_ref(action.target)
            safe = me.hero.health + me.hero.armor > defender.attack
            return 72.0 + defender.attack * 2 + (8 if safe else -15)

        if action.kind == ActionKind.PLAY_CARD:
            instance = engine._find_hand_card(player, action.source)
            card = engine.card_db[instance.card_id]
            score = 52.0 + card.cost * 2
            if card.type == "MINION":
                score += card.attack + card.health * 0.6
                if "TAUNT" in card.keywords:
                    score += 3
            if action.target == enemy_hero:
                score += card.effects.get("damage", 0) * 2
            elif action.target and action.target.startswith("minion:"):
                target = engine._minion_from_ref(action.target)
                if card.effects.get("damage", 0) >= target.health:
                    score += 25 + target.attack
            score += card.effects.get("draw", 0) * 5
            score += card.effects.get("armor", 0) * (0.8 if me.hero.health < 20 else 0.2)
            return score

        if action.kind == ActionKind.HERO_POWER:
            if me.hero.hero_class == "MAGE" and action.target and action.target.startswith("minion:"):
                target = engine._minion_from_ref(action.target)
                return 68.0 if target.health <= 1 else 36.0
            if me.hero.hero_class == "MAGE" and action.target == enemy_hero:
                return 35.0
            return 33.0 + (4.0 if me.hero.health < 20 else 0.0)

        # Ending is preferred over wasting damage on friendly targets, but comes
        # after every productive play/attack.
        return 10.0 + (2.0 if not me.hand else 0.0) + (1.0 if enemy.hero.health <= 0 else 0.0)
