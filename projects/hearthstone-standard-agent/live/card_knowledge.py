"""Current Standard card knowledge loaded from validated HearthstoneJSON snapshots."""

from __future__ import annotations

import gzip
import html
import json
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SNAPSHOT = ROOT / "data" / "knowledge" / "cards.collectible.zhCN.json.gz"
DEFAULT_STANDARD_CONFIG = ROOT / "data" / "standard_sets.json"


@dataclass(frozen=True, slots=True)
class CardKnowledge:
    card_id: str
    dbf_id: int = 0
    name: str = "Unknown card"
    text: str = ""
    card_type: str = ""
    card_class: str = ""
    set_id: str = ""
    cost: int = 0
    attack: int = 0
    health: int = 0
    durability: int = 0
    mechanics: tuple[str, ...] = ()
    collectible: bool = False
    standard: bool = False


@dataclass(frozen=True, slots=True)
class EffectProfile:
    damage: int = 0
    heal: int = 0
    draw: int = 0
    summon: int = 0
    armor: int = 0
    buff_attack: int = 0
    buff_health: int = 0
    destroy: bool = False
    silence: bool = False
    transform: bool = False
    discover: bool = False
    aoe: bool = False
    friendly_effect: bool = False
    enemy_effect: bool = False
    recognized_features: tuple[str, ...] = ()
    coverage: float = 0.0


@dataclass(slots=True)
class StandardCardCatalog:
    cards: dict[str, CardKnowledge] = field(default_factory=dict)
    active_set_ids: frozenset[str] = frozenset()
    source_available: bool = False
    snapshot_path: Path = DEFAULT_SNAPSHOT

    @classmethod
    def load(
        cls,
        snapshot_path: Path | None = None,
        standard_config_path: Path | None = None,
    ) -> "StandardCardCatalog":
        snapshot_path = snapshot_path or DEFAULT_SNAPSHOT
        standard_config_path = standard_config_path or DEFAULT_STANDARD_CONFIG
        active_sets: frozenset[str] = frozenset()
        if standard_config_path.is_file():
            config = json.loads(standard_config_path.read_text(encoding="utf-8"))
            active_sets = frozenset(str(value) for value in config.get("active_set_ids", []))
        if not snapshot_path.is_file():
            return cls(active_set_ids=active_sets, snapshot_path=snapshot_path)

        with gzip.open(snapshot_path, "rt", encoding="utf-8") as handle:
            payload = json.load(handle)
        cards: dict[str, CardKnowledge] = {}
        for item in payload:
            card_id = str(item.get("id") or "")
            if not card_id:
                continue
            set_id = str(item.get("set") or "")
            cards[card_id] = CardKnowledge(
                card_id=card_id,
                dbf_id=_integer(item.get("dbfId")),
                name=str(item.get("name") or card_id),
                text=clean_card_text(str(item.get("text") or "")),
                card_type=str(item.get("type") or ""),
                card_class=str(item.get("cardClass") or ""),
                set_id=set_id,
                cost=_integer(item.get("cost")),
                attack=_integer(item.get("attack")),
                health=_integer(item.get("health")),
                durability=_integer(item.get("durability")),
                mechanics=tuple(str(value) for value in item.get("mechanics", [])),
                collectible=bool(item.get("collectible", False)),
                standard=set_id in active_sets,
            )
        return cls(
            cards=cards,
            active_set_ids=active_sets,
            source_available=True,
            snapshot_path=snapshot_path,
        )

    def get(self, card_id: str) -> CardKnowledge | None:
        return self.cards.get(card_id)

    @property
    def standard_cards(self) -> tuple[CardKnowledge, ...]:
        return tuple(card for card in self.cards.values() if card.standard)

    @property
    def standard_card_count(self) -> int:
        return sum(card.standard for card in self.cards.values())

    @property
    def standard_set_counts(self) -> dict[str, int]:
        return dict(
            sorted(Counter(card.set_id for card in self.cards.values() if card.standard).items())
        )

    def coverage_summary(self) -> str:
        if not self.source_available:
            return "卡牌知识快照缺失"
        return f"标准卡牌知识 {self.standard_card_count} 张 / {len(self.active_set_ids)} 个系列"


def clean_card_text(value: str) -> str:
    value = html.unescape(value.replace("\n", " "))
    value = re.sub(r"<[^>]+>", "", value)
    value = value.replace("$", "").replace("#", "")
    return re.sub(r"\s+", " ", value).strip()


def effect_profile(card: CardKnowledge | None) -> EffectProfile:
    if card is None:
        return EffectProfile()
    text = card.text.lower()
    features: list[str] = []

    damage = _first_number(
        text,
        r"造成\s*(\d+)\s*点伤害",
        r"deal\s+(\d+)\s+damage",
    )
    if damage:
        features.append("damage")
    heal = _first_number(
        text,
        r"恢复\s*(\d+)\s*点生命",
        r"restore\s+(\d+)\s+health",
    )
    if heal:
        features.append("heal")
    draw = _first_number(text, r"抽(?:取)?\s*(\d+)\s*张牌", r"draw\s+(\d+)\s+cards?")
    if not draw and ("抽一张牌" in text or "draw a card" in text):
        draw = 1
    if draw:
        features.append("draw")
    summon = _first_number(text, r"召唤\s*(\d+)\s*个", r"summon\s+(\d+)")
    if not summon and ("召唤一个" in text or "summon a" in text):
        summon = 1
    if summon:
        features.append("summon")
    armor = _first_number(text, r"获得\s*(\d+)\s*点护甲", r"gain\s+(\d+)\s+armor")
    if armor:
        features.append("armor")
    buff_attack, buff_health = _buff_numbers(text)
    if buff_attack or buff_health:
        features.append("buff")

    destroy = any(value in text for value in ("消灭一个", "消灭该", "destroy a", "destroy it"))
    silence = "沉默" in text or "silence" in text
    transform = "变形成为" in text or "transform" in text
    discover = "发现" in text or "discover" in text
    aoe = any(value in text for value in ("所有随从", "所有敌人", "all minions", "all enemies"))
    friendly = any(value in text for value in ("友方", "friendly", "你的英雄", "your hero"))
    enemy = any(value in text for value in ("敌方", "enemy", "一个敌人", "an enemy"))
    for enabled, label in (
        (destroy, "destroy"),
        (silence, "silence"),
        (transform, "transform"),
        (discover, "discover"),
        (aoe, "aoe"),
    ):
        if enabled:
            features.append(label)
    for mechanic in card.mechanics:
        features.append(mechanic.lower())

    has_text = bool(text)
    coverage = 1.0 if not has_text else min(1.0, 0.35 + 0.13 * len(set(features)))
    if card.card_type == "MINION":
        coverage = max(coverage, 0.65)
    return EffectProfile(
        damage=damage,
        heal=heal,
        draw=draw,
        summon=summon,
        armor=armor,
        buff_attack=buff_attack,
        buff_health=buff_health,
        destroy=destroy,
        silence=silence,
        transform=transform,
        discover=discover,
        aoe=aoe,
        friendly_effect=friendly,
        enemy_effect=enemy,
        recognized_features=tuple(dict.fromkeys(features)),
        coverage=coverage,
    )


def _first_number(text: str, *patterns: str) -> int:
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return int(match.group(1))
    return 0


def _buff_numbers(text: str) -> tuple[int, int]:
    match = re.search(r"\+(\d+)\s*/\s*\+(\d+)", text)
    if match:
        return int(match.group(1)), int(match.group(2))
    match = re.search(r"\+(\d+)\s*攻击力", text)
    return (int(match.group(1)), 0) if match else (0, 0)


def _integer(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0
