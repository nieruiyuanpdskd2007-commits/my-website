"""A deterministic, testable Hearthstone-like V0.1 simulator.

It models the rules needed for the first learning loop: mulligan, mana, hidden
hands, minions, targeted spells, weapons, hero powers, combat, fatigue and game
termination.  It intentionally does not pretend to implement every live card.
"""

from __future__ import annotations

import copy
import random
from dataclasses import dataclass, field
from typing import Any, Iterable

from env.action_space import Action, ActionKind, END_TURN
from env.card_db import CardDatabase, CardDef, Deck


class IllegalAction(ValueError):
    pass


@dataclass(slots=True)
class CardInstance:
    entity_id: int
    card_id: str


@dataclass(slots=True)
class MinionState:
    entity_id: int
    card_id: str
    attack: int
    health: int
    max_health: int
    attacks_remaining: int = 0
    summoned_turn: int = 0


@dataclass(slots=True)
class WeaponState:
    card_id: str
    attack: int
    durability: int


@dataclass(slots=True)
class HeroState:
    hero_class: str
    health: int = 30
    armor: int = 0
    hero_power_used: bool = False
    attacked_this_turn: bool = False


@dataclass(slots=True)
class PlayerState:
    name: str
    deck_name: str
    hero: HeroState
    deck: list[str]
    hand: list[CardInstance] = field(default_factory=list)
    board: list[MinionState] = field(default_factory=list)
    weapon: WeaponState | None = None
    mana: int = 0
    max_mana: int = 0
    fatigue: int = 0


class GameEngine:
    MAX_BOARD = 7
    MAX_HAND = 10
    HERO_POWER_COST = 2

    def __init__(
        self,
        card_db: CardDatabase,
        deck_a: Deck,
        deck_b: Deck,
        *,
        seed: int = 0,
        max_turns: int = 80,
    ):
        self.card_db = card_db
        self.decks = (deck_a, deck_b)
        self.seed = seed
        self.rng = random.Random(seed)
        self.max_turns = max_turns
        self.players: list[PlayerState] = []
        self.current_player = 0
        self.turn = 0
        self.phase = "new"
        self.terminal = False
        self.winner: int | None = None
        self.history: list[dict[str, Any]] = []
        self._next_entity_id = 1

    def clone(self) -> "GameEngine":
        return copy.deepcopy(self)

    def initialize(self) -> None:
        self.rng = random.Random(self.seed)
        self.players = []
        for index, deck in enumerate(self.decks):
            cards = list(deck.cards)
            self.rng.shuffle(cards)
            self.players.append(
                PlayerState(
                    name=f"Player {index + 1}",
                    deck_name=deck.name,
                    hero=HeroState(deck.hero_class),
                    deck=cards,
                )
            )
        self.current_player = 0
        self.turn = 0
        self.phase = "mulligan"
        self.terminal = False
        self.winner = None
        self.history = []
        self._next_entity_id = 1
        for _ in range(3):
            self._draw(0)
        for _ in range(4):
            self._draw(1)
        self.players[1].hand.append(self._new_card("THE_COIN"))

    def mulligan(self, player: int, entity_ids: Iterable[int]) -> None:
        if self.phase != "mulligan":
            raise RuntimeError("Mulligan is only available before the game starts")
        selected = set(entity_ids)
        state = self.players[player]
        replace = [card for card in state.hand if card.entity_id in selected and card.card_id != "THE_COIN"]
        if len(replace) != len(selected):
            raise ValueError("Mulligan selection contains an invalid card")
        for card in replace:
            state.hand.remove(card)
        returned = [card.card_id for card in replace]
        for _ in returned:
            self._draw(player)
        state.deck.extend(returned)
        self.rng.shuffle(state.deck)

    def start(self) -> None:
        if self.phase != "mulligan":
            raise RuntimeError("Game is not waiting for mulligans")
        self.phase = "playing"
        self.current_player = 0
        self._start_turn(0)

    def legal_actions(self, player: int | None = None) -> list[Action]:
        player = self.current_player if player is None else player
        if self.phase != "playing" or self.terminal or player != self.current_player:
            return []
        me = self.players[player]
        actions: list[Action] = []
        for instance in me.hand:
            card = self.card_db[instance.card_id]
            if card.cost > me.mana:
                continue
            if card.type == "MINION" and len(me.board) >= self.MAX_BOARD:
                continue
            targets = self._card_targets(card, player)
            if card.target != "none" and not targets:
                continue
            if card.target == "none":
                actions.append(Action(ActionKind.PLAY_CARD, instance.entity_id))
            else:
                actions.extend(Action(ActionKind.PLAY_CARD, instance.entity_id, target) for target in targets)

        attack_targets = self._attack_targets(player)
        for minion in me.board:
            if minion.attack > 0 and minion.attacks_remaining > 0:
                actions.extend(Action(ActionKind.ATTACK, minion.entity_id, target) for target in attack_targets)
        if me.weapon and me.weapon.attack > 0 and not me.hero.attacked_this_turn:
            actions.extend(Action(ActionKind.HERO_ATTACK, target=target) for target in attack_targets)

        if me.mana >= self.HERO_POWER_COST and not me.hero.hero_power_used:
            if me.hero.hero_class == "MAGE":
                actions.extend(
                    Action(ActionKind.HERO_POWER, target=target)
                    for target in self._character_targets(player, "any_character")
                )
            elif me.hero.hero_class == "WARRIOR":
                actions.append(Action(ActionKind.HERO_POWER))
        actions.append(END_TURN)
        return actions

    def apply(self, action: Action) -> None:
        if action not in self.legal_actions():
            raise IllegalAction(f"Illegal action for player {self.current_player}: {action}")
        actor = self.current_player
        if action.kind == ActionKind.END_TURN:
            self._record(actor, action, "end turn")
            self.current_player = 1 - actor
            self._start_turn(self.current_player)
            return
        if action.kind == ActionKind.PLAY_CARD:
            self._play_card(actor, action)
        elif action.kind == ActionKind.ATTACK:
            self._minion_attack(actor, action)
        elif action.kind == ActionKind.HERO_ATTACK:
            self._hero_attack(actor, action)
        elif action.kind == ActionKind.HERO_POWER:
            self._hero_power(actor, action)
        self._remove_dead_minions()
        self._check_terminal()

    def observation(self, player: int) -> dict[str, Any]:
        me = self.players[player]
        opponent = self.players[1 - player]
        return {
            "phase": self.phase,
            "turn": self.turn,
            "current_player": self.current_player,
            "player": player,
            "terminal": self.terminal,
            "winner": self.winner if self.terminal else None,
            "me": self._visible_player(me, reveal_hand=True),
            "opponent": self._visible_player(opponent, reveal_hand=False),
            "history": list(self.history[-30:]),
        }

    def describe_action(self, action: Action, actor: int | None = None) -> str:
        actor = self.current_player if actor is None else actor
        if action.kind == ActionKind.PLAY_CARD and action.source is not None:
            instance = self._find_hand_card(actor, action.source)
            name = self.card_db[instance.card_id].name
            return f"play {name}" + (f" -> {action.target}" if action.target else "")
        if action.kind in {ActionKind.ATTACK, ActionKind.HERO_ATTACK}:
            return f"{action.kind.value} -> {action.target}"
        if action.kind == ActionKind.HERO_POWER:
            return "hero power" + (f" -> {action.target}" if action.target else "")
        return "end turn"

    def _new_card(self, card_id: str) -> CardInstance:
        entity = CardInstance(self._next_entity_id, card_id)
        self._next_entity_id += 1
        return entity

    def _draw(self, player: int) -> None:
        state = self.players[player]
        if not state.deck:
            state.fatigue += 1
            self._damage_hero(player, state.fatigue)
            self.history.append({"turn": self.turn, "player": player, "event": f"fatigue {state.fatigue}"})
            self._check_terminal()
            return
        card_id = state.deck.pop()
        if len(state.hand) < self.MAX_HAND:
            state.hand.append(self._new_card(card_id))
        else:
            self.history.append({"turn": self.turn, "player": player, "event": "overdraw"})

    def _start_turn(self, player: int) -> None:
        if self.terminal:
            return
        self.turn += 1
        if self.turn > self.max_turns:
            self._resolve_turn_limit()
            return
        state = self.players[player]
        state.max_mana = min(10, state.max_mana + 1)
        state.mana = state.max_mana
        state.hero.hero_power_used = False
        state.hero.attacked_this_turn = False
        for minion in state.board:
            minion.attacks_remaining = 1
        self._draw(player)
        self._check_terminal()

    def _play_card(self, player: int, action: Action) -> None:
        state = self.players[player]
        instance = self._find_hand_card(player, action.source)
        card = self.card_db[instance.card_id]
        state.hand.remove(instance)
        state.mana -= card.cost
        if card.type == "MINION":
            state.board.append(
                MinionState(
                    entity_id=instance.entity_id,
                    card_id=card.id,
                    attack=card.attack,
                    health=card.health,
                    max_health=card.health,
                    attacks_remaining=1 if "CHARGE" in card.keywords else 0,
                    summoned_turn=self.turn,
                )
            )
        elif card.type == "WEAPON":
            state.weapon = WeaponState(card.id, card.attack, card.durability)
        self._apply_effects(player, card, action.target)
        self._record(player, action, f"played {card.name}")

    def _apply_effects(self, player: int, card: CardDef, target: str | None) -> None:
        effects = card.effects
        if effects.get("damage") and target:
            self._damage_target(target, effects["damage"])
        if effects.get("heal") and target:
            self._heal_target(target, effects["heal"])
        if effects.get("armor"):
            self.players[player].hero.armor += effects["armor"]
        if effects.get("mana_gain"):
            state = self.players[player]
            state.mana = min(10, state.mana + effects["mana_gain"])
        for _ in range(effects.get("draw", 0)):
            self._draw(player)

    def _minion_attack(self, player: int, action: Action) -> None:
        attacker = self._find_minion(player, action.source)
        attacker.attacks_remaining -= 1
        if action.target == self._hero_ref(1 - player):
            self._damage_hero(1 - player, attacker.attack)
        else:
            defender = self._minion_from_ref(action.target)
            attacker.health -= defender.attack
            defender.health -= attacker.attack
        self._record(player, action, "minion attack")

    def _hero_attack(self, player: int, action: Action) -> None:
        state = self.players[player]
        assert state.weapon is not None
        state.hero.attacked_this_turn = True
        attack = state.weapon.attack
        if action.target == self._hero_ref(1 - player):
            self._damage_hero(1 - player, attack)
        else:
            defender = self._minion_from_ref(action.target)
            defender.health -= attack
            self._damage_hero(player, defender.attack)
        state.weapon.durability -= 1
        if state.weapon.durability <= 0:
            state.weapon = None
        self._record(player, action, "hero attack")

    def _hero_power(self, player: int, action: Action) -> None:
        state = self.players[player]
        state.mana -= self.HERO_POWER_COST
        state.hero.hero_power_used = True
        if state.hero.hero_class == "MAGE":
            assert action.target is not None
            self._damage_target(action.target, 1)
        elif state.hero.hero_class == "WARRIOR":
            state.hero.armor += 2
        self._record(player, action, "hero power")

    def _card_targets(self, card: CardDef, player: int) -> list[str]:
        return self._character_targets(player, card.target)

    def _character_targets(self, player: int, rule: str) -> list[str]:
        friendly = [self._hero_ref(player), *(self._minion_ref(m.entity_id) for m in self.players[player].board)]
        enemy = [self._hero_ref(1 - player), *(self._minion_ref(m.entity_id) for m in self.players[1 - player].board)]
        if rule == "none":
            return []
        if rule == "enemy_character":
            return enemy
        if rule == "friendly_character":
            return friendly
        if rule == "any_character":
            return friendly + enemy
        if rule == "enemy_minion":
            return enemy[1:]
        if rule == "friendly_minion":
            return friendly[1:]
        raise ValueError(f"Unknown target rule: {rule}")

    def _attack_targets(self, player: int) -> list[str]:
        opponent = self.players[1 - player]
        taunts = [m for m in opponent.board if "TAUNT" in self.card_db[m.card_id].keywords]
        if taunts:
            return [self._minion_ref(m.entity_id) for m in taunts]
        return [self._hero_ref(1 - player), *(self._minion_ref(m.entity_id) for m in opponent.board)]

    def _damage_target(self, target: str, amount: int) -> None:
        if target.startswith("hero:"):
            self._damage_hero(int(target.split(":", 1)[1]), amount)
        else:
            self._minion_from_ref(target).health -= amount

    def _heal_target(self, target: str, amount: int) -> None:
        if target.startswith("hero:"):
            hero = self.players[int(target.split(":", 1)[1])].hero
            hero.health = min(30, hero.health + amount)
        else:
            minion = self._minion_from_ref(target)
            minion.health = min(minion.max_health, minion.health + amount)

    def _damage_hero(self, player: int, amount: int) -> None:
        hero = self.players[player].hero
        absorbed = min(hero.armor, amount)
        hero.armor -= absorbed
        hero.health -= amount - absorbed

    def _remove_dead_minions(self) -> None:
        for state in self.players:
            state.board[:] = [minion for minion in state.board if minion.health > 0]

    def _check_terminal(self) -> None:
        if not self.players:
            return
        dead = [index for index, state in enumerate(self.players) if state.hero.health <= 0]
        if not dead:
            return
        self.terminal = True
        self.phase = "finished"
        self.winner = None if len(dead) == 2 else 1 - dead[0]

    def _resolve_turn_limit(self) -> None:
        scores = [p.hero.health + p.hero.armor for p in self.players]
        self.terminal = True
        self.phase = "finished"
        self.winner = 0 if scores[0] > scores[1] else 1 if scores[1] > scores[0] else None

    def _record(self, player: int, action: Action, event: str) -> None:
        self.history.append(
            {"turn": self.turn, "player": player, "action": action.to_dict(), "event": event}
        )

    def _find_hand_card(self, player: int, entity_id: int | None) -> CardInstance:
        for card in self.players[player].hand:
            if card.entity_id == entity_id:
                return card
        raise IllegalAction(f"Card entity {entity_id} is not in hand")

    def _find_minion(self, player: int, entity_id: int | None) -> MinionState:
        for minion in self.players[player].board:
            if minion.entity_id == entity_id:
                return minion
        raise IllegalAction(f"Minion entity {entity_id} is not controlled by player {player}")

    def _minion_from_ref(self, target: str | None) -> MinionState:
        if target is None or not target.startswith("minion:"):
            raise IllegalAction(f"Not a minion target: {target}")
        entity_id = int(target.split(":", 1)[1])
        for state in self.players:
            for minion in state.board:
                if minion.entity_id == entity_id:
                    return minion
        raise IllegalAction(f"Unknown minion target: {target}")

    def _visible_player(self, state: PlayerState, *, reveal_hand: bool) -> dict[str, Any]:
        hand = []
        if reveal_hand:
            hand = [self.card_db[c.card_id].public_dict(c.entity_id) for c in state.hand]
        board = []
        for minion in state.board:
            item = self.card_db[minion.card_id].public_dict(minion.entity_id)
            item.update(
                {
                    "current_attack": minion.attack,
                    "current_health": minion.health,
                    "max_health": minion.max_health,
                    "can_attack": minion.attacks_remaining > 0,
                }
            )
            board.append(item)
        return {
            "name": state.name,
            "deck_name": state.deck_name,
            "hero_class": state.hero.hero_class,
            "hero_hp": state.hero.health,
            "armor": state.hero.armor,
            "mana": state.mana,
            "max_mana": state.max_mana,
            "hero_power_used": state.hero.hero_power_used,
            "hand": hand,
            "hand_size": len(state.hand),
            "board": board,
            "deck_size": len(state.deck),
            "fatigue": state.fatigue,
            "weapon": None
            if state.weapon is None
            else {
                "card_id": state.weapon.card_id,
                "attack": state.weapon.attack,
                "durability": state.weapon.durability,
            },
        }

    @staticmethod
    def _hero_ref(player: int) -> str:
        return f"hero:{player}"

    @staticmethod
    def _minion_ref(entity_id: int) -> str:
        return f"minion:{entity_id}"
