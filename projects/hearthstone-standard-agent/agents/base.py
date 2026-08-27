"""Agent protocol shared by random, rule and future neural agents."""

from __future__ import annotations

from typing import Protocol

from env.action_space import Action
from env.simulator import GameEngine


class Agent(Protocol):
    name: str

    def choose_mulligan(self, observation: dict) -> list[int]: ...

    def choose_action(
        self, observation: dict, legal_actions: list[Action], engine: GameEngine
    ) -> Action: ...
