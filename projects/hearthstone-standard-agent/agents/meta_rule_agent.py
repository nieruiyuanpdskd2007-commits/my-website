"""Rule agent that can use aggregate box statistics as a mulligan prior."""

from __future__ import annotations

from agents.rule_agent import RuleAgent
from env.meta_stats import BoxMetaStats


class MetaRuleAgent(RuleAgent):
    def __init__(
        self,
        stats: BoxMetaStats,
        deck_id: str,
        *,
        keep_threshold: float = 0.5,
        seed: int = 0,
        name: str = "MetaRuleAgent",
    ):
        super().__init__(seed=seed, name=name)
        self.stats = stats
        self.deck_id = deck_id
        self.keep_threshold = keep_threshold

    def choose_mulligan(self, observation: dict) -> list[int]:
        replace: list[int] = []
        for card in observation["me"]["hand"]:
            if card["card_id"] == "THE_COIN":
                continue
            keep_rate = self.stats.mulligan_keep_rate(self.deck_id, card["card_id"])
            if keep_rate is not None:
                if keep_rate < self.keep_threshold:
                    replace.append(card["entity_id"])
            elif card["cost"] > 3:
                replace.append(card["entity_id"])
        return replace
