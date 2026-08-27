"""Typed actions used by the simulator and every agent."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class ActionKind(StrEnum):
    PLAY_CARD = "play_card"
    ATTACK = "attack"
    HERO_ATTACK = "hero_attack"
    HERO_POWER = "hero_power"
    END_TURN = "end_turn"


@dataclass(frozen=True, slots=True)
class Action:
    """One fully specified action.

    Target selection is folded into the action.  This keeps search nodes atomic while
    still representing Hearthstone's PlayCard/ChooseTarget interaction.
    """

    kind: ActionKind
    source: int | None = None
    target: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {"kind": self.kind.value, "source": self.source, "target": self.target}

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "Action":
        return cls(
            kind=ActionKind(payload["kind"]),
            source=payload.get("source"),
            target=payload.get("target"),
        )

    def short(self) -> str:
        bits = [self.kind.value]
        if self.source is not None:
            bits.append(f"#{self.source}")
        if self.target is not None:
            bits.append(f"->{self.target}")
        return "".join(bits)


END_TURN = Action(ActionKind.END_TURN)
