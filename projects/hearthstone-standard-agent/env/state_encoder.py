"""Observation encoders for baselines and future Transformer models."""

from __future__ import annotations

from dataclasses import dataclass


HERO_CLASS_IDS = {"MAGE": 1.0, "WARRIOR": 2.0}
CARD_TYPE_IDS = {"MINION": 1.0, "SPELL": 2.0, "WEAPON": 3.0}


@dataclass(slots=True)
class FlatStateEncoder:
    """Compact public-information vector, useful for simple value baselines."""

    def encode(self, observation: dict) -> list[float]:
        me = observation["me"]
        enemy = observation["opponent"]
        my_board_attack = sum(item["current_attack"] for item in me["board"])
        enemy_board_attack = sum(item["current_attack"] for item in enemy["board"])
        return [
            min(observation["turn"], 80) / 80.0,
            me["hero_hp"] / 30.0,
            min(me["armor"], 30) / 30.0,
            me["mana"] / 10.0,
            me["max_mana"] / 10.0,
            me["hand_size"] / 10.0,
            me["deck_size"] / 30.0,
            len(me["board"]) / 7.0,
            min(my_board_attack, 30) / 30.0,
            sum(item["current_health"] for item in me["board"]) / 50.0,
            enemy["hero_hp"] / 30.0,
            min(enemy["armor"], 30) / 30.0,
            enemy["hand_size"] / 10.0,
            enemy["deck_size"] / 30.0,
            len(enemy["board"]) / 7.0,
            min(enemy_board_attack, 30) / 30.0,
            sum(item["current_health"] for item in enemy["board"]) / 50.0,
            0.0 if me["weapon"] is None else me["weapon"]["attack"] / 10.0,
            0.0 if me["weapon"] is None else me["weapon"]["durability"] / 5.0,
            HERO_CLASS_IDS.get(me["hero_class"], 0.0) / 12.0,
            HERO_CLASS_IDS.get(enemy["hero_class"], 0.0) / 12.0,
            float(observation["current_player"] == observation["player"]),
        ]


@dataclass(slots=True)
class EntityTokenEncoder:
    """Creates variable-length entity tokens suitable for a Transformer.

    No opponent hand identities are emitted; only an aggregate hidden-hand token is
    present.  A neural model can add learned embeddings for card IDs later.
    """

    max_history: int = 12

    def encode(self, observation: dict) -> list[dict]:
        me = observation["me"]
        enemy = observation["opponent"]
        tokens: list[dict] = [
            {"zone": "TURN", "turn": observation["turn"]},
            self._hero_token("MY_HERO", me),
            self._hero_token("ENEMY_HERO", enemy),
            {"zone": "ENEMY_HAND", "count": enemy["hand_size"]},
        ]
        tokens.extend(self._card_token("MY_HAND", card) for card in me["hand"])
        tokens.extend(self._card_token("MY_BOARD", card) for card in me["board"])
        tokens.extend(self._card_token("ENEMY_BOARD", card) for card in enemy["board"])
        for event in observation["history"][-self.max_history :]:
            tokens.append(
                {
                    "zone": "HISTORY",
                    "turn": event.get("turn", 0),
                    "actor_is_me": event.get("player") == observation["player"],
                    "event": event.get("event", ""),
                }
            )
        return tokens

    @staticmethod
    def _hero_token(zone: str, player: dict) -> dict:
        return {
            "zone": zone,
            "hero_class": player["hero_class"],
            "health": player["hero_hp"],
            "armor": player["armor"],
            "mana": player["mana"],
            "max_mana": player["max_mana"],
        }

    @staticmethod
    def _card_token(zone: str, card: dict) -> dict:
        return {
            "zone": zone,
            "card_id": card["card_id"],
            "type_id": CARD_TYPE_IDS.get(card["type"], 0.0),
            "cost": card["cost"],
            "attack": card.get("current_attack", card.get("attack", 0)),
            "health": card.get("current_health", card.get("health", 0)),
            "keywords": card.get("keywords", []),
        }
