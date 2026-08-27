"""Windows/macOS desktop entry point for the read-only Live Advisor overlay."""

from __future__ import annotations

import argparse
import json
import threading
from pathlib import Path

from live.advisor import LiveAdvisor
from live.card_knowledge import StandardCardCatalog
from live.overlay import ChatOverlay
from live.power_log import LogTailer, PowerLogParser, discover_power_log
from live.recorder import PublicReplayRecorder
from live.tracker import PublicStateTracker
from live.types import GameMode, LiveSnapshot, ModePolicy


def demo_snapshot(mode: GameMode) -> LiveSnapshot:
    catalog = StandardCardCatalog.load()
    return LiveSnapshot.from_dict(
        {
            "mode": mode.value,
            "turn": 7,
            "local_player_id": 1,
            "current_player_id": 1,
            "mana": 7,
            "max_mana": 7,
            "my_hero_hp": 24,
            "enemy_hero_hp": 6,
            "enemy_armor": 0,
            "enemy_hand_size": 5,
            "legal_actions_authoritative": True,
            "state_completeness": 1.0,
            "card_knowledge_coverage": 1.0,
            "standard_card_count": catalog.standard_card_count,
            "knowledge_status": catalog.coverage_summary(),
            "legal_actions": [
                {
                    "kind": "play_card",
                    "label": "打出 Fireball，目标选择对方英雄",
                    "source": "Fireball",
                    "target": "enemy_hero",
                    "mana_cost": 4,
                    "damage": 6,
                    "score": 100,
                    "reason": "造成 6 点伤害。",
                },
                {
                    "kind": "attack",
                    "label": "4/5 随从攻击对方英雄",
                    "target": "enemy_hero",
                    "damage": 4,
                    "score": 60,
                },
            ],
        }
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=[mode.value for mode in GameMode], default="practice")
    parser.add_argument("--log-path", type=Path)
    parser.add_argument("--player-id", type=int)
    parser.add_argument("--snapshot-file", type=Path, help="JSON snapshot for adapter testing")
    parser.add_argument("--demo", action="store_true")
    parser.add_argument("--console", action="store_true")
    parser.add_argument("--record", type=Path, default=Path("data/replays/live-public.jsonl"))
    args = parser.parse_args()

    mode = GameMode(args.mode)
    policy = ModePolicy.for_mode(mode)
    advisor = LiveAdvisor()
    tracker = PublicStateTracker(mode, local_player_id=args.player_id)
    snapshot = tracker.snapshot
    if args.demo:
        snapshot = demo_snapshot(mode)
    elif args.snapshot_file:
        snapshot = LiveSnapshot.from_dict(json.loads(args.snapshot_file.read_text(encoding="utf-8")))
        snapshot.mode = mode

    if args.console:
        print(f"mode={mode.value} live_recommendations={policy.live_recommendations}")
        print(advisor.recommend(snapshot).render())
        return

    status = "建议开启" if policy.live_recommendations else "天梯：仅记牌/复盘"
    overlay = ChatOverlay(
        title="Hearthstone Advisor",
        status=status,
        on_question=lambda question: advisor.answer(
            question, tracker.snapshot if tracker.snapshot.history else snapshot
        ),
    )
    overlay.post("system", f"当前模式：{mode.value}。{status}。不会控制游戏输入。")
    overlay.post("advisor", advisor.recommend(snapshot).render())

    log_path = args.log_path or discover_power_log()
    if log_path:
        stop = threading.Event()
        parser_ = PowerLogParser()
        recorder = PublicReplayRecorder(args.record)

        def consume(line: str) -> None:
            event = parser_.feed(line)
            if event is None:
                return
            recorder.append(event)
            tracker.apply(event)
            if event.kind in {"game_start", "game_end"}:
                overlay.post("system", tracker.snapshot.history[-1])
            elif event.kind == "options_end" and tracker.snapshot.is_my_turn:
                overlay.post("advisor", advisor.recommend(tracker.snapshot).render())

        worker = threading.Thread(
            target=LogTailer(log_path).follow,
            args=(stop, consume),
            name="power-log-reader",
            daemon=True,
        )
        worker.start()
        overlay.root.protocol("WM_DELETE_WINDOW", lambda: (stop.set(), overlay.root.destroy()))
        overlay.post("system", f"已连接只读日志：{log_path}")
    else:
        overlay.post("system", "未发现 Power.log；可使用 --log-path 指定，或先运行 --demo。")
    overlay.run()


if __name__ == "__main__":
    main()
