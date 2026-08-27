"""Explainable recommendation policy with a hard ladder safety gate."""

from __future__ import annotations

from live.types import ActionCandidate, LiveSnapshot, ModePolicy, Recommendation


class LiveAdvisor:
    def recommend(self, snapshot: LiveSnapshot) -> Recommendation:
        policy = ModePolicy.for_mode(snapshot.mode)
        if not policy.live_recommendations:
            return Recommendation(
                enabled=False,
                primary="天梯保护模式：本局只显示公开记牌与局面摘要，赛后再提供复盘。",
                reason="",
            )
        if snapshot.game_over:
            winner = snapshot.winner or "未知"
            return Recommendation(False, f"对局已结束（胜者：{winner}），可以开始复盘。", "")
        if not snapshot.is_my_turn:
            return Recommendation(False, "等待对手行动；当前不生成出牌建议。", "")
        if not snapshot.legal_actions:
            return Recommendation(
                True,
                "检查可用攻击与英雄技能；若都不可用则结束回合",
                "尚未收到完整合法动作列表，使用保守提示。",
                confidence=0.25,
                risk="不要依据不完整状态强行操作。",
            )

        enemy_effective_hp = snapshot.enemy_hero_hp + snapshot.enemy_armor
        lethal = [
            action
            for action in snapshot.legal_actions
            if action.target == "enemy_hero" and action.damage >= enemy_effective_hp
        ]
        if lethal:
            best = max(lethal, key=lambda action: (action.damage, action.score))
            return self._format(best, snapshot, "这是当前合法动作中的直接斩杀。", 0.99)

        lethal_sequence = self._visible_lethal_sequence(snapshot, enemy_effective_hp)
        if lethal_sequence:
            first = lethal_sequence[0]
            recommendation = self._format(
                first,
                snapshot,
                f"当前公开合法动作可以组合造成至少 {enemy_effective_hp} 点伤害。",
                0.9,
            )
            return Recommendation(
                enabled=True,
                primary=recommendation.primary,
                reason=recommendation.reason,
                alternative=recommendation.alternative,
                confidence=recommendation.confidence,
                risk=recommendation.risk,
                sequence=tuple(action.label for action in lethal_sequence),
            )

        trades = [action for action in snapshot.legal_actions if action.kind == "trade"]
        if trades:
            best = max(trades, key=lambda action: action.score)
            if best.score >= 60:
                return self._format(
                    best,
                    snapshot,
                    best.reason or "这次交换能改善场面资源差。",
                    0.78,
                )

        plays = [action for action in snapshot.legal_actions if action.kind == "play_card"]
        if plays:
            affordable = [action for action in plays if action.mana_cost <= snapshot.mana]
            if affordable:
                best = max(affordable, key=lambda action: (action.score, action.mana_cost))
                return self._format(
                    best,
                    snapshot,
                    best.reason or "在当前法力内提供最高的节奏评分。",
                    0.68,
                )

        face = [
            action
            for action in snapshot.legal_actions
            if action.kind in {"attack", "hero_attack"} and action.target == "enemy_hero"
        ]
        if face:
            best = max(face, key=lambda action: (action.damage, action.score))
            return self._format(best, snapshot, "没有更高价值交换，推进可见伤害。", 0.62)

        powers = [action for action in snapshot.legal_actions if action.kind == "hero_power"]
        if powers:
            best = max(powers, key=lambda action: action.score)
            return self._format(best, snapshot, best.reason or "利用剩余法力。", 0.52)

        remaining = [
            action for action in snapshot.legal_actions if action.kind != "end_turn"
        ]
        if remaining:
            best = max(remaining, key=lambda action: action.score)
            return self._format(
                best,
                snapshot,
                best.reason or "这是剩余候选中评分最高的客户端合法动作。",
                0.5,
            )

        end = next(
            (action for action in snapshot.legal_actions if action.kind == "end_turn"),
            ActionCandidate("end_turn", "结束回合"),
        )
        return self._format(end, snapshot, "当前没有更高价值的公开合法动作。", 0.45)

    def answer(self, question: str, snapshot: LiveSnapshot) -> str:
        normalized = question.strip().lower()
        policy = ModePolicy.for_mode(snapshot.mode)
        if any(word in normalized for word in ("怎么打", "推荐", "出什么", "斩杀")):
            return self.recommend(snapshot).render()
        if "手牌" in normalized:
            cards = "、".join(card.name for card in snapshot.my_hand) or "暂无已识别手牌"
            return f"你的公开手牌：{cards}。对手仅显示手牌数量 {snapshot.enemy_hand_size}。"
        if "模式" in normalized or "天梯" in normalized:
            state = "开启" if policy.live_recommendations else "关闭"
            return f"当前模式：{snapshot.mode.value}；实时出牌建议：{state}。"
        if "覆盖" in normalized or "卡池" in normalized or "准确" in normalized:
            legal = "客户端 OPTIONS 权威动作" if snapshot.legal_actions_authoritative else "动作列表未完成"
            return (
                f"{snapshot.knowledge_status}；可见卡牌识别率 "
                f"{snapshot.card_knowledge_coverage:.0%}；状态完整度 "
                f"{snapshot.state_completeness:.0%}；{legal}。"
            )
        return (
            f"第 {snapshot.turn} 回合，法力 {snapshot.mana}/{snapshot.max_mana}，"
            f"己方生命 {snapshot.my_hero_hp}，对手有效生命 "
            f"{snapshot.enemy_hero_hp + snapshot.enemy_armor}。"
        )

    @staticmethod
    def _format(
        action: ActionCandidate,
        snapshot: LiveSnapshot,
        reason: str,
        confidence: float,
    ) -> Recommendation:
        alternatives = sorted(
            (candidate for candidate in snapshot.legal_actions if candidate != action),
            key=lambda candidate: candidate.score,
            reverse=True,
        )
        alternative = alternatives[0].label if alternatives else ""
        if snapshot.legal_actions_authoritative:
            confidence *= 0.72 + 0.18 * snapshot.state_completeness + 0.1 * max(
                action.mechanics_coverage, snapshot.card_knowledge_coverage
            )
        else:
            confidence *= 0.55
        risk_parts = ["建议仅基于当前可见信息，不假定对手手牌。"]
        if not snapshot.legal_actions_authoritative:
            risk_parts.append("尚未收到完整 OPTIONS，合法动作可能不完整。")
        if action.mechanics_coverage < 0.5 and action.kind not in {
            "attack",
            "trade",
            "hero_attack",
            "end_turn",
        }:
            risk_parts.append("该卡复杂文本尚未被完全结构化，评分已降置信度。")
        return Recommendation(
            True,
            action.label,
            reason,
            alternative,
            min(0.99, confidence),
            " ".join(risk_parts),
        )

    @staticmethod
    def _visible_lethal_sequence(
        snapshot: LiveSnapshot, enemy_effective_hp: int
    ) -> list[ActionCandidate]:
        by_source: dict[object, ActionCandidate] = {}
        for action in snapshot.legal_actions:
            if action.target != "enemy_hero" or action.damage <= 0:
                continue
            key: object = action.source_entity_id if action.source_entity_id is not None else action.label
            previous = by_source.get(key)
            if previous is None or (action.damage, action.score) > (previous.damage, previous.score):
                by_source[key] = action
        actions = list(by_source.values())
        best: list[ActionCandidate] | None = None
        for mask in range(1, 1 << len(actions)):
            chosen = [action for index, action in enumerate(actions) if mask & (1 << index)]
            mana = sum(
                action.mana_cost
                for action in chosen
                if action.kind in {"play_card", "hero_power"}
            )
            if mana > snapshot.mana or sum(action.damage for action in chosen) < enemy_effective_hp:
                continue
            if best is None or (len(chosen), mana, -sum(a.score for a in chosen)) < (
                len(best),
                sum(a.mana_cost for a in best),
                -sum(a.score for a in best),
            ):
                best = chosen
        if best is None:
            return []
        return sorted(best, key=lambda action: (action.kind == "hero_power", action.mana_cost))
