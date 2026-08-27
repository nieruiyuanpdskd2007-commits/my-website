"""Stable vocabulary builder for card-ID embeddings."""

from __future__ import annotations

from env.card_db import CardDatabase


class CardVocabulary:
    PAD = 0
    UNKNOWN = 1

    def __init__(self, card_db: CardDatabase):
        self.card_to_index = {
            card_id: index for index, card_id in enumerate(sorted(card_db.cards), start=2)
        }

    def encode(self, card_id: str) -> int:
        return self.card_to_index.get(card_id, self.UNKNOWN)

    @property
    def size(self) -> int:
        return len(self.card_to_index) + 2
