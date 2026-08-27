"""Small rollout search baseline.

This is a root Monte-Carlo search, deliberately simpler than the eventual
information-set MCTS needed for hidden opponent hands.  It is useful for validating
clone/apply/terminal correctness before coupling a learned Policy + Value model.
"""

from __future__ import annotations

import random

from env.action_space import Action
from env.simulator import GameEngine


class MCTS:
    def __init__(self, *, simulations: int = 48, rollout_actions: int = 500, seed: int = 0):
        self.simulations = simulations
        self.rollout_actions = rollout_actions
        self.rng = random.Random(seed)

    def search(self, engine: GameEngine, root_player: int) -> tuple[Action, dict[Action, float]]:
        actions = engine.legal_actions(root_player)
        if not actions:
            raise RuntimeError("MCTS root has no legal actions")
        totals = {action: 0.0 for action in actions}
        visits = {action: 0 for action in actions}
        for index in range(self.simulations):
            action = actions[index % len(actions)] if index < len(actions) else self._ucb_action(totals, visits)
            branch = engine.clone()
            branch.apply(action)
            value = self._rollout(branch, root_player)
            totals[action] += value
            visits[action] += 1
        means = {
            action: totals[action] / visits[action] if visits[action] else -2.0 for action in actions
        }
        best = max(actions, key=lambda action: (means[action], visits[action]))
        return best, means

    def _rollout(self, engine: GameEngine, root_player: int) -> float:
        steps = 0
        while not engine.terminal and steps < self.rollout_actions:
            engine.apply(self.rng.choice(engine.legal_actions()))
            steps += 1
        if not engine.terminal or engine.winner is None:
            if not engine.terminal:
                scores = [p.hero.health + p.hero.armor for p in engine.players]
                return 0.25 if scores[root_player] > scores[1 - root_player] else -0.25
            return 0.0
        return 1.0 if engine.winner == root_player else -1.0

    def _ucb_action(self, totals: dict[Action, float], visits: dict[Action, int]) -> Action:
        unvisited = [action for action, count in visits.items() if count == 0]
        if unvisited:
            return self.rng.choice(unvisited)
        total_visits = sum(visits.values())
        return max(
            totals,
            key=lambda action: totals[action] / visits[action]
            + 1.4 * (total_visits**0.5) / (1 + visits[action]),
        )
