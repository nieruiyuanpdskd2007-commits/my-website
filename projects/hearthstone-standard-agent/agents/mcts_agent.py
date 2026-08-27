"""Agent wrapper for the rollout search baseline."""

from __future__ import annotations

from agents.rule_agent import RuleAgent
from env.action_space import Action
from env.simulator import GameEngine
from search.mcts import MCTS


class MCTSAgent:
    def __init__(self, *, simulations: int = 48, seed: int = 0, name: str = "MCTSAgent"):
        self.name = name
        self.searcher = MCTS(simulations=simulations, seed=seed)
        self.mulligan_agent = RuleAgent(seed=seed)

    def choose_mulligan(self, observation: dict) -> list[int]:
        return self.mulligan_agent.choose_mulligan(observation)

    def choose_action(
        self, observation: dict, legal_actions: list[Action], engine: GameEngine
    ) -> Action:
        action, _ = self.searcher.search(engine, observation["player"])
        return action
