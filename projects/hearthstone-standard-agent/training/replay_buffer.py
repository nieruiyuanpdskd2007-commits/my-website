"""Append-only JSONL replay buffer for imitation/self-play samples."""

from __future__ import annotations

import json
import random
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(slots=True)
class ReplaySample:
    observation: dict
    action: dict
    player: int
    outcome: float
    policy: dict[str, float] | None = None


class ReplayBuffer:
    def __init__(self, capacity: int = 100_000):
        self.capacity = capacity
        self.samples: list[ReplaySample] = []

    def extend(self, samples: list[ReplaySample]) -> None:
        self.samples.extend(samples)
        overflow = len(self.samples) - self.capacity
        if overflow > 0:
            del self.samples[:overflow]

    def sample(self, count: int, *, seed: int = 0) -> list[ReplaySample]:
        return random.Random(seed).sample(self.samples, min(count, len(self.samples)))

    def save_jsonl(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as handle:
            for sample in self.samples:
                handle.write(json.dumps(asdict(sample), ensure_ascii=False) + "\n")

    @classmethod
    def load_jsonl(cls, path: str | Path, *, capacity: int = 100_000) -> "ReplayBuffer":
        buffer = cls(capacity)
        with Path(path).open(encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    buffer.samples.append(ReplaySample(**json.loads(line)))
        if len(buffer.samples) > capacity:
            buffer.samples = buffer.samples[-capacity:]
        return buffer
