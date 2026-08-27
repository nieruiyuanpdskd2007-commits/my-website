"""Start/stop lifecycle for the read-only live log monitor."""

from __future__ import annotations

import threading
from collections.abc import Callable
from pathlib import Path

from live.power_log import LogTailer, PowerLogParser, PowerEvent
from live.recorder import PublicReplayRecorder
from live.tracker import PublicStateTracker
from live.types import GameMode, LiveSnapshot


class LiveController:
    def __init__(
        self,
        *,
        on_status: Callable[[str], None] | None = None,
        on_event: Callable[[PowerEvent, LiveSnapshot], None] | None = None,
    ):
        self.on_status = on_status or (lambda _message: None)
        self.on_event = on_event or (lambda _event, _snapshot: None)
        self.stop_event = threading.Event()
        self.worker: threading.Thread | None = None
        self.tracker = PublicStateTracker(GameMode.UNKNOWN)

    @property
    def running(self) -> bool:
        return self.worker is not None and self.worker.is_alive()

    @property
    def snapshot(self) -> LiveSnapshot:
        return self.tracker.snapshot

    def start(
        self,
        log_path: str | Path,
        *,
        mode: GameMode,
        local_player_id: int | None,
        replay_path: str | Path,
    ) -> None:
        path = Path(log_path)
        if not path.is_file():
            raise FileNotFoundError(path)
        self.stop()
        self.stop_event = threading.Event()
        self.tracker = PublicStateTracker(mode, local_player_id=local_player_id)
        parser = PowerLogParser()
        recorder = PublicReplayRecorder(replay_path)

        def consume(line: str) -> None:
            event = parser.feed(line)
            if event is None:
                return
            recorder.append(event)
            snapshot = self.tracker.apply(event)
            self.on_event(event, snapshot)

        def work() -> None:
            self.on_status("正在监听")
            LogTailer(path).follow(self.stop_event, consume)
            self.on_status("已停止")

        self.worker = threading.Thread(target=work, name="power-log-reader", daemon=True)
        self.worker.start()

    def stop(self) -> None:
        self.stop_event.set()
        worker = self.worker
        if worker and worker.is_alive() and worker is not threading.current_thread():
            worker.join(timeout=1.0)
        self.worker = None
