"""Framework-neutral Policy + Value interfaces.

PyTorch is intentionally optional in V0.1.  Implement this protocol after the
simulator/replay loop is stable, then use the entity tokens from state_encoder.py.
"""

from __future__ import annotations

from typing import Protocol

from env.action_space import Action


class PolicyValueModel(Protocol):
    def predict(self, observation: dict, legal_actions: list[Action]) -> tuple[list[float], float]:
        """Return normalized legal-action probabilities and value in [-1, 1]."""
        ...
