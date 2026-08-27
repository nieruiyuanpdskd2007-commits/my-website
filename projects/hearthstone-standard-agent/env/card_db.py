"""Card/deck loading and validation.

The bundled catalogue is deliberately small.  The simulator implements mechanics,
not a claim that these demo decks are legal in the live Standard rotation.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True, slots=True)
class CardDef:
    id: str
    name: str
    card_class: str
    type: str
    cost: int
    attack: int = 0
    health: int = 0
    durability: int = 0
    target: str = "none"
    effects: dict[str, int] = field(default_factory=dict)
    keywords: tuple[str, ...] = ()

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "CardDef":
        return cls(
            id=value["id"],
            name=value["name"],
            card_class=value["card_class"],
            type=value["type"],
            cost=int(value["cost"]),
            attack=int(value.get("attack", 0)),
            health=int(value.get("health", 0)),
            durability=int(value.get("durability", 0)),
            target=value.get("target", "none"),
            effects={k: int(v) for k, v in value.get("effects", {}).items()},
            keywords=tuple(value.get("keywords", [])),
        )

    def public_dict(self, entity_id: int | None = None) -> dict[str, Any]:
        result: dict[str, Any] = {
            "card_id": self.id,
            "name": self.name,
            "class": self.card_class,
            "type": self.type,
            "cost": self.cost,
            "attack": self.attack,
            "health": self.health,
            "durability": self.durability,
            "target": self.target,
            "effects": dict(self.effects),
            "keywords": list(self.keywords),
        }
        if entity_id is not None:
            result["entity_id"] = entity_id
        return result


@dataclass(frozen=True, slots=True)
class Deck:
    name: str
    hero_class: str
    cards: tuple[str, ...]


class CardDatabase:
    def __init__(self, cards: dict[str, CardDef]):
        self.cards = cards

    @classmethod
    def load(cls, path: Path | None = None) -> "CardDatabase":
        path = path or PROJECT_ROOT / "data" / "cards.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        cards = {item["id"]: CardDef.from_dict(item) for item in payload["cards"]}
        return cls(cards)

    def __getitem__(self, card_id: str) -> CardDef:
        try:
            return self.cards[card_id]
        except KeyError as exc:
            raise KeyError(f"Unknown card id: {card_id}") from exc

    def load_deck(self, path: str | Path) -> Deck:
        resolved = Path(path)
        if not resolved.is_absolute():
            resolved = PROJECT_ROOT / resolved
        payload = json.loads(resolved.read_text(encoding="utf-8"))
        expanded: list[str] = []
        for entry in payload["cards"]:
            if entry["id"] not in self.cards:
                raise ValueError(f"Deck {payload['name']} uses unknown card {entry['id']}")
            expanded.extend([entry["id"]] * int(entry.get("count", 1)))
        if len(expanded) != 30:
            raise ValueError(f"Deck {payload['name']} must contain 30 cards, got {len(expanded)}")
        return Deck(payload["name"], payload["hero_class"], tuple(expanded))
