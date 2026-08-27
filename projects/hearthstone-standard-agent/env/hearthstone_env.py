"""Small environment wrapper used by game loops and future RL integrations."""

from __future__ import annotations

from env.action_space import Action
from env.card_db import CardDatabase, Deck
from env.simulator import GameEngine


class HearthstoneEnv:
    def __init__(self, card_db: CardDatabase, deck_a: Deck, deck_b: Deck, *, max_turns: int = 80):
        self.card_db = card_db
        self.deck_a = deck_a
        self.deck_b = deck_b
        self.max_turns = max_turns
        self.engine: GameEngine | None = None

    def reset(self, *, seed: int = 0) -> tuple[dict, dict]:
        self.engine = GameEngine(
            self.card_db, self.deck_a, self.deck_b, seed=seed, max_turns=self.max_turns
        )
        self.engine.initialize()
        return self.engine.observation(0), self.engine.observation(1)

    def mulligan(self, player: int, entity_ids: list[int]) -> None:
        self._engine().mulligan(player, entity_ids)

    def start(self) -> dict:
        engine = self._engine()
        engine.start()
        return engine.observation(engine.current_player)

    def step(self, action: Action) -> tuple[dict, float, bool, dict]:
        engine = self._engine()
        actor = engine.current_player
        engine.apply(action)
        reward = 0.0
        if engine.terminal:
            reward = 0.0 if engine.winner is None else (1.0 if engine.winner == actor else -1.0)
        next_player = engine.current_player
        return (
            engine.observation(next_player),
            reward,
            engine.terminal,
            {"winner": engine.winner},
        )

    def legal_actions(self) -> list[Action]:
        return self._engine().legal_actions()

    def _engine(self) -> GameEngine:
        if self.engine is None:
            raise RuntimeError("Call reset() before using the environment")
        return self.engine
