"""Convert authoritative client options into explainable, ranked action candidates."""

from __future__ import annotations

from dataclasses import replace

from live.card_knowledge import CardKnowledge, StandardCardCatalog, effect_profile
from live.types import ActionCandidate, ClientOption, LiveSnapshot, PublicEntity


class LiveActionEngine:
    def __init__(self, catalog: StandardCardCatalog):
        self.catalog = catalog

    def generate(
        self,
        options: list[ClientOption],
        entities: dict[int, PublicEntity],
        snapshot: LiveSnapshot,
    ) -> list[ActionCandidate]:
        candidates: list[ActionCandidate] = []
        for option in options:
            if not _allowed(option.error):
                continue
            if option.option_type.upper() == "END_TURN":
                candidates.append(
                    ActionCandidate(
                        kind="end_turn",
                        label="结束回合",
                        option_index=option.index,
                        authoritative=True,
                    )
                )
                continue

            source = entities.get(option.source_entity_id or -1)
            card = self.catalog.get(option.card_id or (source.card_id if source else ""))
            targets = [target for target in option.targets if _allowed(target.error)]
            if targets:
                for target in targets:
                    target_entity = entities.get(target.entity_id)
                    candidates.append(
                        self._candidate(
                            option,
                            source,
                            target_entity,
                            card,
                            snapshot,
                            target_index=target.index,
                        )
                    )
            else:
                candidates.append(self._candidate(option, source, None, card, snapshot))

        non_end = sum(candidate.kind != "end_turn" for candidate in candidates)
        return [
            replace(candidate, score=-50.0 if candidate.kind == "end_turn" and non_end else candidate.score)
            for candidate in candidates
        ]

    def _candidate(
        self,
        option: ClientOption,
        source: PublicEntity | None,
        target: PublicEntity | None,
        card: CardKnowledge | None,
        snapshot: LiveSnapshot,
        *,
        target_index: int | None = None,
    ) -> ActionCandidate:
        kind = _kind(option.option_type, source, target, snapshot.local_player_id)
        source_name = _entity_name(source, card)
        target_key, target_name = _target(target, snapshot.local_player_id)
        label = _label(kind, source_name, target_name)
        profile = effect_profile(card)
        damage = source.attack if source and kind in {"attack", "trade", "hero_attack"} else profile.damage
        candidate = ActionCandidate(
            kind=kind,
            label=label,
            source=source_name,
            target=target_key,
            mana_cost=(source.cost if source else (card.cost if card else 0)),
            damage=damage,
            source_entity_id=source.entity_id if source else option.source_entity_id,
            target_entity_id=target.entity_id if target else None,
            option_index=option.index,
            suboption_index=option.suboption_index,
            target_index=target_index,
            card_id=card.card_id if card else (source.card_id if source else option.card_id),
            mechanics_coverage=profile.coverage,
            authoritative=True,
        )
        score, reason = self._score(candidate, source, target, card, snapshot)
        return replace(candidate, score=score, reason=reason)

    def _score(
        self,
        candidate: ActionCandidate,
        source: PublicEntity | None,
        target: PublicEntity | None,
        card: CardKnowledge | None,
        snapshot: LiveSnapshot,
    ) -> tuple[float, str]:
        profile = effect_profile(card)
        score = 0.0
        reasons: list[str] = []
        enemy_effective_hp = snapshot.enemy_hero_hp + snapshot.enemy_armor

        if candidate.kind in {"attack", "hero_attack"} and candidate.target == "enemy_hero":
            score = candidate.damage * 7.0
            reasons.append(f"推进 {candidate.damage} 点可见伤害")
            if candidate.damage >= enemy_effective_hp:
                score += 1000
                reasons.append("构成直接斩杀")
        elif candidate.kind == "trade" and source and target:
            target_value = _board_value(target)
            source_value = _board_value(source)
            score = target_value
            if source.attack >= target.health:
                score += 22
                reasons.append("可以消灭目标")
            if target.attack >= source.health and not source.divine_shield:
                score -= source_value * 0.7
                reasons.append("攻击者可能同时阵亡")
            else:
                score += 8
                reasons.append("攻击后预计能保留攻击者")
        elif candidate.kind == "play_card":
            score += max(2.0, candidate.mana_cost * 1.8)
            if card and card.card_type == "MINION":
                score += card.attack * 2 + card.health - card.cost * 0.7
                score += _mechanic_value(card.mechanics)
                reasons.append("按身材、费用和关键词评估节奏")
            score += profile.draw * 7 + profile.summon * 8 + profile.armor * 2.5
            if profile.draw:
                reasons.append(f"预计补充 {profile.draw} 张资源")
            if profile.discover:
                score += 9
                reasons.append("发现效果提供选择空间")
            if profile.aoe:
                score += max(0, len(snapshot.enemy_board) - len(snapshot.my_board)) * 9
                reasons.append("根据双方场面数量评估群体效果")
            score += self._targeted_effect_score(
                candidate, source, target, profile, snapshot, reasons
            )
        elif candidate.kind == "hero_power":
            score = 8 + profile.damage * 5 + profile.heal * 3 + profile.armor * 2
            reasons.append("使用英雄技能转化剩余法力")
            score += self._targeted_effect_score(
                candidate, source, target, profile, snapshot, reasons
            )
        elif candidate.kind == "trade_card":
            score = 7.0
            reasons.append("将不适合当前回合的可交易牌换成新资源")
        elif candidate.kind in {"location", "minion_power", "power"}:
            score = 10 + profile.damage * 5 + profile.draw * 6 + profile.summon * 7
            reasons.append("这是客户端确认可用的场上能力")
            score += self._targeted_effect_score(
                candidate, source, target, profile, snapshot, reasons
            )
        elif candidate.kind == "end_turn":
            reasons.append("客户端允许结束回合")

        if card and not card.standard:
            score -= 2
        if candidate.mechanics_coverage < 0.5 and candidate.kind not in {
            "attack",
            "trade",
            "hero_attack",
            "end_turn",
        }:
            reasons.append("复杂效果仅作保守估值")
        return score, "；".join(dict.fromkeys(reasons)) or "客户端确认这是合法动作。"

    @staticmethod
    def _targeted_effect_score(
        candidate: ActionCandidate,
        source: PublicEntity | None,
        target: PublicEntity | None,
        profile,
        snapshot: LiveSnapshot,
        reasons: list[str],
    ) -> float:
        if target is None:
            return 0.0
        score = 0.0
        is_enemy = candidate.target in {"enemy_hero", "enemy_board"}
        is_friendly = candidate.target in {"my_hero", "my_board"}
        if profile.damage:
            score += profile.damage * (7 if is_enemy else -8)
            reasons.append(f"识别到 {profile.damage} 点伤害效果")
            if candidate.target == "enemy_hero" and profile.damage >= (
                snapshot.enemy_hero_hp + snapshot.enemy_armor
            ):
                score += 1000
                reasons.append("伤害足以斩杀")
            if candidate.target == "enemy_board" and profile.damage >= target.health:
                score += 20 + _board_value(target)
                reasons.append("伤害足以移除目标")
        if profile.destroy:
            score += (35 + _board_value(target)) if is_enemy else -45
            reasons.append("识别到消灭效果")
        if profile.silence:
            score += (10 + _board_value(target) * 0.4) if is_enemy else -8
            reasons.append("识别到沉默效果")
        if profile.transform:
            score += (28 + _board_value(target) * 0.5) if is_enemy else -25
            reasons.append("识别到变形效果")
        if profile.buff_attack or profile.buff_health:
            value = profile.buff_attack * 3 + profile.buff_health * 2
            score += value if is_friendly else -value
            reasons.append("识别到属性增益")
        if profile.heal:
            missing = max(0, target.max_health - target.health)
            score += min(profile.heal, missing) * 3 if is_friendly else -profile.heal * 3
            reasons.append("根据已损失生命评估治疗")
        return score


def _allowed(error: str) -> bool:
    return not error or error.upper() in {"NONE", "0"}


def _kind(
    option_type: str,
    source: PublicEntity | None,
    target: PublicEntity | None,
    local_player_id: int | None,
) -> str:
    normalized_type = option_type.upper()
    if "TRADE" in normalized_type:
        return "trade_card"
    if source is None:
        return "power"
    if normalized_type == "ATTACK":
        if source.card_type == "HERO":
            return "hero_attack"
        if source.card_type == "MINION" and target is not None:
            target_is_enemy = target.controller is not None and target.controller != local_player_id
            return "trade" if target.card_type == "MINION" and target_is_enemy else "attack"
        return "attack"
    if source.zone == "HAND":
        return "play_card"
    if source.card_type == "HERO_POWER":
        return "hero_power"
    if source.card_type == "LOCATION":
        return "location"
    if source.card_type == "HERO":
        return "power"
    if source.card_type == "MINION":
        return "minion_power"
    return "power"


def _target(
    target: PublicEntity | None, local_player_id: int | None
) -> tuple[str, str]:
    if target is None:
        return "", ""
    mine = local_player_id is not None and target.controller == local_player_id
    if target.card_type == "HERO":
        return ("my_hero", "己方英雄") if mine else ("enemy_hero", "对方英雄")
    return ("my_board", target.name) if mine else ("enemy_board", target.name)


def _entity_name(entity: PublicEntity | None, card: CardKnowledge | None) -> str:
    if entity and entity.name and entity.name != "Unknown card":
        return entity.name
    if card:
        return card.name
    return f"实体 {entity.entity_id}" if entity else "未知动作"


def _label(kind: str, source_name: str, target_name: str) -> str:
    if kind == "play_card":
        return f"打出 {source_name}" + (f" → {target_name}" if target_name else "")
    if kind in {"attack", "trade", "hero_attack"}:
        return f"{source_name} 攻击 {target_name or '目标'}"
    if kind == "hero_power":
        return f"使用英雄技能" + (f" → {target_name}" if target_name else "")
    if kind == "location":
        return f"使用地标 {source_name}" + (f" → {target_name}" if target_name else "")
    if kind == "trade_card":
        return f"交易 {source_name}"
    return f"使用 {source_name}" + (f" → {target_name}" if target_name else "")


def _board_value(entity: PublicEntity) -> float:
    value = entity.attack * 2 + entity.health
    value += 4 if entity.taunt else 0
    value += 5 if entity.divine_shield else 0
    value += 4 if entity.poisonous else 0
    value += 3 if entity.lifesteal else 0
    return float(value)


def _mechanic_value(mechanics: tuple[str, ...]) -> float:
    weights = {
        "TAUNT": 3,
        "DIVINE_SHIELD": 5,
        "RUSH": 4,
        "CHARGE": 7,
        "LIFESTEAL": 3,
        "POISONOUS": 4,
        "REBORN": 5,
        "BATTLECRY": 2,
        "DEATHRATTLE": 2,
        "TITAN": 8,
        "COLOSSAL": 7,
    }
    return float(sum(weights.get(value, 0) for value in mechanics))
