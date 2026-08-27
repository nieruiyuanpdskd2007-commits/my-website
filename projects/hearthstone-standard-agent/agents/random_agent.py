"""Uniform random baseline."""

from __future__ import annotations

import random

from env.action_space import Action
from env.simulator import GameEngine


class RandomAgent:
    def __init__(self, *, seed: int = 0, name: str = "RandomAgent"):
        self.rng = random.Random(seed)
        self.name = name

    def choose_mulligan(self, observation: dict) -> list[int]:
        return [
            card["entity_id"]
            for card in observation["me"]["hand"]
            if card["card_id"] != "THE_COIN" and self.rng.random() < 0.35
        ]

    def choose_action(
        self, observation: dict, legal_actions: list[Action], engine: GameEngine
    ) -> Action:
        if not legal_actions:
            raise RuntimeError("RandomAgent was asked to act without a legal action")
        return self.rng.choice(legal_actions)
