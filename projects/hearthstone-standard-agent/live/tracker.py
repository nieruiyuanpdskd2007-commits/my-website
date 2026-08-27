"""Conservative public-state reconstruction from parsed log events."""

from __future__ import annotations

from dataclasses import replace

from live.types import GameMode, LiveSnapshot, PublicEntity
from live.power_log import PowerEvent


class PublicStateTracker:
    def __init__(self, mode: GameMode, *, local_player_id: int | None = None):
        self.snapshot = LiveSnapshot(mode=mode, local_player_id=local_player_id)
        self.entities: dict[int, PublicEntity] = {}
        self.tags: dict[int, dict[str, str]] = {}

    def apply(self, event: PowerEvent) -> LiveSnapshot:
        if event.kind == "game_start":
            self.snapshot.turn = 0
            self.snapshot.history.append("Game started")
        elif event.kind == "game_end":
            self.snapshot.game_over = True
            self.snapshot.history.append("Game ended")
        elif event.kind == "entity" and event.entity_id is not None:
            current = self.entities.get(event.entity_id, PublicEntity(event.entity_id))
            self.entities[event.entity_id] = replace(current, card_id=event.card_id or current.card_id)
        elif event.kind == "tag" and event.entity_id is not None:
            self._tag(event.entity_id, event.tag, event.value)
        elif event.kind == "block":
            label = f"{event.value}: {event.card_id or 'public action'}"
            self.snapshot.history.append(label)
        self.snapshot.history[:] = self.snapshot.history[-30:]
        self._rebuild_zones()
        return self.snapshot

    def _tag(self, entity_id: int, tag: str, value: str) -> None:
        self.tags.setdefault(entity_id, {})[tag] = value
        current = self.entities.get(entity_id, PublicEntity(entity_id))
        if tag == "TURN":
            try:
                self.snapshot.turn = int(value)
            except ValueError:
                pass
        elif tag == "CURRENT_PLAYER" and value == "1":
            self.snapshot.current_player_id = entity_id
        elif tag == "CONTROLLER":
            current = replace(current, controller=self._integer(value))
        elif tag == "ZONE":
            current = replace(current, zone=value)
        elif tag == "ATK":
            current = replace(current, attack=self._integer(value) or 0)
        elif tag in {"HEALTH", "DAMAGE"}:
            health = current.health
            if tag == "HEALTH":
                health = self._integer(value) or health
            else:
                health = max(0, health - (self._integer(value) or 0))
            current = replace(current, health=health)
        elif tag == "COST":
            current = replace(current, cost=self._integer(value) or 0)
        elif tag == "TAUNT":
            current = replace(current, taunt=value == "1")
        elif tag == "EXHAUSTED":
            current = replace(current, can_attack=value == "0")
        self.entities[entity_id] = current

    def _rebuild_zones(self) -> None:
        local = self.snapshot.local_player_id
        my_hand: list[PublicEntity] = []
        my_board: list[PublicEntity] = []
        enemy_board: list[PublicEntity] = []
        enemy_hand_size = 0
        for entity in self.entities.values():
            mine = local is not None and entity.controller == local
            if entity.zone == "HAND":
                if mine:
                    my_hand.append(entity)
                else:
                    enemy_hand_size += 1
            elif entity.zone == "PLAY":
                (my_board if mine else enemy_board).append(entity)
        self.snapshot.my_hand = sorted(my_hand, key=lambda item: item.entity_id)
        self.snapshot.my_board = sorted(my_board, key=lambda item: item.entity_id)
        self.snapshot.enemy_board = sorted(enemy_board, key=lambda item: item.entity_id)
        self.snapshot.enemy_hand_size = enemy_hand_size

    @staticmethod
    def _integer(value: str) -> int | None:
        try:
            return int(value)
        except ValueError:
            return None
