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
        risk = "建议仅基于当前可见信息，不假定对手手牌。"
        return Recommendation(True, action.label, reason, alternative, confidence, risk)
