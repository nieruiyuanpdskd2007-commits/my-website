"""Public-information contracts for the desktop Live Advisor."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any


class GameMode(StrEnum):
    PRACTICE = "practice"
    FRIENDLY = "friendly"
    REPLAY = "replay"
    LADDER = "ladder"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class ModePolicy:
    mode: GameMode
    live_recommendations: bool
    public_tracking: bool = True
    post_game_review: bool = True
    input_automation: bool = False
    process_injection: bool = False
    hidden_information: bool = False

    @classmethod
    def for_mode(cls, mode: GameMode) -> "ModePolicy":
        return cls(
            mode=mode,
            live_recommendations=mode in {GameMode.PRACTICE, GameMode.FRIENDLY, GameMode.REPLAY},
        )


@dataclass(frozen=True, slots=True)
class PublicEntity:
    entity_id: int
    card_id: str = ""
    name: str = "Unknown card"
    card_type: str = ""
    card_text: str = ""
    mechanics: tuple[str, ...] = ()
    controller: int | None = None
    zone: str = ""
    zone_position: int = 0
    attack: int = 0
    health: int = 0
    max_health: int = 0
    armor: int = 0
    durability: int = 0
    cost: int = 0
    can_attack: bool = False
    taunt: bool = False
    divine_shield: bool = False
    poisonous: bool = False
    lifesteal: bool = False
    stealth: bool = False
    frozen: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ActionCandidate:
    kind: str
    label: str
    source: str = ""
    target: str = ""
    mana_cost: int = 0
    damage: int = 0
    score: float = 0.0
    reason: str = ""
    source_entity_id: int | None = None
    target_entity_id: int | None = None
    option_index: int | None = None
    suboption_index: int | None = None
    target_index: int | None = None
    card_id: str = ""
    mechanics_coverage: float = 0.0
    authoritative: bool = False

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ActionCandidate":
        return cls(**payload)


@dataclass(frozen=True, slots=True)
class OptionTarget:
    index: int
    entity_id: int
    error: str = "NONE"


@dataclass(slots=True)
class ClientOption:
    index: int
    option_type: str
    source_entity_id: int | None = None
    card_id: str = ""
    error: str = "NONE"
    suboption_index: int | None = None
    targets: list[OptionTarget] = field(default_factory=list)


@dataclass(slots=True)
class LiveSnapshot:
    mode: GameMode
    turn: int = 0
    local_player_id: int | None = None
    current_player_id: int | None = None
    mana: int = 0
    max_mana: int = 0
    my_hero_hp: int = 30
    my_armor: int = 0
    enemy_hero_hp: int = 30
    enemy_armor: int = 0
    my_hand: list[PublicEntity] = field(default_factory=list)
    my_board: list[PublicEntity] = field(default_factory=list)
    enemy_board: list[PublicEntity] = field(default_factory=list)
    enemy_hand_size: int = 0
    history: list[str] = field(default_factory=list)
    legal_actions: list[ActionCandidate] = field(default_factory=list)
    legal_actions_authoritative: bool = False
    state_completeness: float = 0.0
    card_knowledge_coverage: float = 0.0
    standard_card_count: int = 0
    knowledge_status: str = "卡牌知识未加载"
    game_over: bool = False
    winner: str = ""

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "LiveSnapshot":
        value = dict(payload)
        value["mode"] = GameMode(value.get("mode", GameMode.UNKNOWN))
        for key in ("my_hand", "my_board", "enemy_board"):
            value[key] = [PublicEntity(**item) for item in value.get(key, [])]
        value["legal_actions"] = [
            ActionCandidate.from_dict(item) for item in value.get("legal_actions", [])
        ]
        return cls(**value)

    @property
    def is_my_turn(self) -> bool:
        return (
            self.local_player_id is not None
            and self.current_player_id is not None
            and self.local_player_id == self.current_player_id
        )

    def public_dict(self) -> dict[str, Any]:
        """Serialize without any opponent hand identities."""
        return {
            "mode": self.mode.value,
            "turn": self.turn,
            "local_player_id": self.local_player_id,
            "current_player_id": self.current_player_id,
            "mana": self.mana,
            "max_mana": self.max_mana,
            "my_hero_hp": self.my_hero_hp,
            "my_armor": self.my_armor,
            "enemy_hero_hp": self.enemy_hero_hp,
            "enemy_armor": self.enemy_armor,
            "my_hand": [entity.to_dict() for entity in self.my_hand],
            "my_board": [entity.to_dict() for entity in self.my_board],
            "enemy_board": [entity.to_dict() for entity in self.enemy_board],
            "enemy_hand_size": self.enemy_hand_size,
            "history": list(self.history),
            "legal_actions": [asdict(action) for action in self.legal_actions],
            "legal_actions_authoritative": self.legal_actions_authoritative,
            "state_completeness": self.state_completeness,
            "card_knowledge_coverage": self.card_knowledge_coverage,
            "standard_card_count": self.standard_card_count,
            "knowledge_status": self.knowledge_status,
            "game_over": self.game_over,
            "winner": self.winner,
        }


@dataclass(frozen=True, slots=True)
class Recommendation:
    enabled: bool
    primary: str
    reason: str
    alternative: str = ""
    confidence: float = 0.0
    risk: str = ""
    sequence: tuple[str, ...] = ()

    def render(self) -> str:
        if not self.enabled:
            return self.primary
        lines = [f"推荐：{self.primary}", f"理由：{self.reason}"]
        if self.alternative:
            lines.append(f"备选：{self.alternative}")
        if self.sequence:
            lines.append("建议顺序：" + " → ".join(self.sequence))
        if self.risk:
            lines.append(f"注意：{self.risk}")
        lines.append(f"置信度：{self.confidence:.0%}")
        return "\n".join(lines)
