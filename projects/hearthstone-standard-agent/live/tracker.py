"""Public-state reconstruction and authoritative legal-action extraction."""

from __future__ import annotations

from collections import Counter
from dataclasses import replace

from live.action_engine import LiveActionEngine
from live.card_knowledge import StandardCardCatalog
from live.power_log import PowerEvent
from live.types import ClientOption, GameMode, LiveSnapshot, OptionTarget, PublicEntity


class PublicStateTracker:
    def __init__(
        self,
        mode: GameMode,
        *,
        local_player_id: int | None = None,
        catalog: StandardCardCatalog | None = None,
    ):
        self.catalog = catalog or StandardCardCatalog.load()
        self.action_engine = LiveActionEngine(self.catalog)
        self.snapshot = LiveSnapshot(
            mode=mode,
            local_player_id=local_player_id,
            standard_card_count=self.catalog.standard_card_count,
            knowledge_status=self.catalog.coverage_summary(),
        )
        self.entities: dict[int, PublicEntity] = {}
        self.tags: dict[int, dict[str, str]] = {}
        self._pending_options: list[ClientOption] = []
        self._option_lookup: dict[tuple[int, int | None], ClientOption] = {}

    def apply(self, event: PowerEvent) -> LiveSnapshot:
        if event.kind == "game_start":
            self._reset_game()
        elif event.kind == "game_end":
            self.snapshot.game_over = True
            self.snapshot.history.append("Game ended")
        elif event.kind == "entity" and event.entity_id is not None:
            self._entity(event.entity_id, event.card_id)
        elif event.kind == "tag" and event.entity_id is not None:
            self._tag(event.entity_id, event.tag, event.value)
        elif event.kind == "block":
            label = f"{event.value}: {self._card_name(event.card_id)}"
            self.snapshot.history.append(label)
        elif event.kind == "options_start":
            self._pending_options.clear()
            self._option_lookup.clear()
            self.snapshot.legal_actions.clear()
            self.snapshot.legal_actions_authoritative = False
        elif event.kind == "option" and event.index is not None:
            option = ClientOption(
                index=event.index,
                option_type=event.option_type,
                source_entity_id=event.source_entity_id,
                card_id=event.card_id,
                error=event.error,
            )
            self._pending_options.append(option)
            self._option_lookup[(event.index, None)] = option
            if event.source_entity_id is not None and (event.card_id or event.value):
                self._entity(event.source_entity_id, event.card_id, event.value)
        elif event.kind == "suboption" and event.index is not None:
            parent = self._option_lookup.get((event.index, None))
            if parent in self._pending_options:
                self._pending_options.remove(parent)
            option = ClientOption(
                index=event.index,
                option_type=parent.option_type if parent else "POWER",
                source_entity_id=event.source_entity_id or (parent.source_entity_id if parent else None),
                card_id=event.card_id or (parent.card_id if parent else ""),
                error=event.error,
                suboption_index=event.suboption_index,
            )
            self._pending_options.append(option)
            self._option_lookup[(event.index, event.suboption_index)] = option
            if event.source_entity_id is not None and (event.card_id or event.value):
                self._entity(event.source_entity_id, event.card_id, event.value)
        elif event.kind == "option_target" and event.index is not None:
            option = self._option_lookup.get((event.index, event.suboption_index))
            option = option or self._option_lookup.get((event.index, None))
            if option is not None and event.target_entity_id is not None:
                option.targets.append(
                    OptionTarget(
                        index=self._integer(event.value) or 0,
                        entity_id=event.target_entity_id,
                        error=event.error,
                    )
                )
        elif event.kind == "options_end":
            self._rebuild_zones()
            self.snapshot.legal_actions = self.action_engine.generate(
                self._pending_options, self.entities, self.snapshot
            )
            self.snapshot.legal_actions_authoritative = True
            self._update_completeness()

        self.snapshot.history[:] = self.snapshot.history[-30:]
        if event.kind != "options_end":
            self._rebuild_zones()
            self._update_completeness()
        return self.snapshot

    def _reset_game(self) -> None:
        mode = self.snapshot.mode
        local = self.snapshot.local_player_id
        self.snapshot = LiveSnapshot(
            mode=mode,
            local_player_id=local,
            standard_card_count=self.catalog.standard_card_count,
            knowledge_status=self.catalog.coverage_summary(),
        )
        self.entities.clear()
        self.tags.clear()
        self._pending_options.clear()
        self._option_lookup.clear()
        self.snapshot.history.append("Game started")

    def _entity(self, entity_id: int, card_id: str, name: str = "") -> None:
        current = self.entities.get(entity_id, PublicEntity(entity_id))
        if card_id or name:
            resolved_card_id = card_id or current.card_id
            card = self.catalog.get(resolved_card_id)
            current = replace(
                current,
                card_id=resolved_card_id,
                name=card.name if card else (name or resolved_card_id or current.name),
                card_type=card.card_type if card else current.card_type,
                card_text=card.text if card else current.card_text,
                mechanics=card.mechanics if card else current.mechanics,
                attack=current.attack or (card.attack if card else 0),
                health=current.health or (card.health if card else 0),
                max_health=current.max_health or (card.health if card else 0),
                cost=current.cost or (card.cost if card else 0),
                durability=current.durability or (card.durability if card else 0),
                taunt=current.taunt or bool(card and "TAUNT" in card.mechanics),
                divine_shield=current.divine_shield
                or bool(card and "DIVINE_SHIELD" in card.mechanics),
                poisonous=current.poisonous or bool(card and "POISONOUS" in card.mechanics),
                lifesteal=current.lifesteal or bool(card and "LIFESTEAL" in card.mechanics),
                stealth=current.stealth or bool(card and "STEALTH" in card.mechanics),
            )
        self.entities[entity_id] = current

    def _tag(self, entity_id: int, tag: str, value: str) -> None:
        tag = tag.upper()
        self.tags.setdefault(entity_id, {})[tag] = value
        current = self.entities.get(entity_id, PublicEntity(entity_id))
        if tag == "TURN":
            self.snapshot.turn = self._integer(value) or self.snapshot.turn
        elif tag == "CURRENT_PLAYER" and value == "1":
            self.snapshot.current_player_id = self._player_id(entity_id)
        elif tag == "CONTROLLER":
            current = replace(current, controller=self._integer(value))
        elif tag == "ZONE":
            current = replace(current, zone=self._zone_name(value))
        elif tag == "ZONE_POSITION":
            current = replace(current, zone_position=self._integer(value) or 0)
        elif tag == "CARDTYPE":
            current = replace(current, card_type=self._card_type_name(value))
        elif tag == "ATK":
            current = replace(current, attack=self._integer(value) or 0)
        elif tag in {"HEALTH", "DAMAGE"}:
            base_health = self._integer(self.tags[entity_id].get("HEALTH")) or current.max_health
            damage = self._integer(self.tags[entity_id].get("DAMAGE")) or 0
            current = replace(
                current,
                max_health=max(current.max_health, base_health),
                health=max(0, base_health - damage),
            )
        elif tag == "ARMOR":
            current = replace(current, armor=self._integer(value) or 0)
        elif tag == "DURABILITY":
            current = replace(current, durability=self._integer(value) or 0)
        elif tag == "COST":
            current = replace(current, cost=self._integer(value) or 0)
        elif tag == "TAUNT":
            current = replace(current, taunt=value == "1")
        elif tag == "DIVINE_SHIELD":
            current = replace(current, divine_shield=value == "1")
        elif tag in {"POISONOUS", "VENOMOUS"}:
            current = replace(current, poisonous=value == "1")
        elif tag == "LIFESTEAL":
            current = replace(current, lifesteal=value == "1")
        elif tag == "STEALTH":
            current = replace(current, stealth=value == "1")
        elif tag == "FROZEN":
            current = replace(current, frozen=value == "1")
        elif tag in {"EXHAUSTED", "CANT_ATTACK"}:
            current = replace(current, can_attack=value == "0")
        self.entities[entity_id] = current
        self._update_resources(entity_id)

    def _update_resources(self, entity_id: int) -> None:
        player_id = self._player_id(entity_id)
        if self.snapshot.local_player_id is None or player_id != self.snapshot.local_player_id:
            return
        tags = self.tags.get(entity_id, {})
        resources = self._integer(tags.get("RESOURCES")) or 0
        used = self._integer(tags.get("RESOURCES_USED")) or 0
        temporary = self._integer(tags.get("TEMP_RESOURCES")) or 0
        if resources or used or temporary:
            self.snapshot.max_mana = resources
            self.snapshot.mana = max(0, resources + temporary - used)

    def _rebuild_zones(self) -> None:
        if self.snapshot.local_player_id is None:
            revealed_hand_controllers = [
                entity.controller
                for entity in self.entities.values()
                if entity.zone == "HAND" and entity.card_id and entity.controller is not None
            ]
            if revealed_hand_controllers:
                self.snapshot.local_player_id = Counter(revealed_hand_controllers).most_common(1)[0][0]

        local = self.snapshot.local_player_id
        my_hand: list[PublicEntity] = []
        my_board: list[PublicEntity] = []
        enemy_board: list[PublicEntity] = []
        enemy_hand_size = 0
        known_cards = 0
        visible_cards = 0
        for entity in self.entities.values():
            mine = local is not None and entity.controller == local
            if entity.zone == "HAND":
                if mine:
                    my_hand.append(entity)
                    visible_cards += 1
                    known_cards += bool(self.catalog.get(entity.card_id))
                else:
                    enemy_hand_size += 1
            elif entity.zone == "PLAY":
                if entity.card_type == "HERO":
                    if mine:
                        self.snapshot.my_hero_hp = entity.health or self.snapshot.my_hero_hp
                        self.snapshot.my_armor = entity.armor
                    else:
                        self.snapshot.enemy_hero_hp = entity.health or self.snapshot.enemy_hero_hp
                        self.snapshot.enemy_armor = entity.armor
                elif entity.card_type in {"MINION", "LOCATION"}:
                    (my_board if mine else enemy_board).append(entity)
                    visible_cards += 1
                    known_cards += bool(self.catalog.get(entity.card_id))
        order = lambda item: (item.zone_position or 99, item.entity_id)
        self.snapshot.my_hand = sorted(my_hand, key=order)
        self.snapshot.my_board = sorted(my_board, key=order)
        self.snapshot.enemy_board = sorted(enemy_board, key=order)
        self.snapshot.enemy_hand_size = enemy_hand_size
        self.snapshot.card_knowledge_coverage = known_cards / visible_cards if visible_cards else 0.0

    def _update_completeness(self) -> None:
        checks = (
            self.snapshot.local_player_id is not None,
            self.snapshot.current_player_id is not None,
            self.snapshot.max_mana > 0 or self.snapshot.turn <= 1,
            bool(self.catalog.source_available),
            self.snapshot.legal_actions_authoritative,
        )
        self.snapshot.state_completeness = sum(checks) / len(checks)

    def _player_id(self, entity_id: int) -> int:
        return self._integer(self.tags.get(entity_id, {}).get("PLAYER_ID")) or entity_id

    def _card_name(self, card_id: str) -> str:
        card = self.catalog.get(card_id)
        return card.name if card else (card_id or "public action")

    @staticmethod
    def _zone_name(value: str) -> str:
        return {
            "0": "INVALID",
            "1": "PLAY",
            "2": "DECK",
            "3": "HAND",
            "4": "GRAVEYARD",
            "5": "REMOVEDFROMGAME",
            "6": "SETASIDE",
            "7": "SECRET",
        }.get(value, value.upper())

    @staticmethod
    def _card_type_name(value: str) -> str:
        return {
            "0": "INVALID",
            "1": "GAME",
            "2": "PLAYER",
            "3": "HERO",
            "4": "MINION",
            "5": "SPELL",
            "6": "ENCHANTMENT",
            "7": "WEAPON",
            "8": "ITEM",
            "9": "TOKEN",
            "10": "HERO_POWER",
            "39": "LOCATION",
        }.get(value, value.upper())

    @staticmethod
    def _integer(value: str | None) -> int | None:
        try:
            return int(value) if value is not None else None
        except ValueError:
            return None
