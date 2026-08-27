"""Paired-seed tournament evaluation."""

from __future__ import annotations

from dataclasses import dataclass

from agents.base import Agent
from env.hearthstone_env import HearthstoneEnv
from training.self_play import play_game


@dataclass(slots=True)
class TournamentResult:
    games: int
    wins_a: int
    wins_b: int
    draws: int
    average_turns: float

    @property
    def win_rate_a(self) -> float:
        return self.wins_a / self.games if self.games else 0.0


def evaluate(
    env: HearthstoneEnv,
    agent_a: Agent,
    agent_b: Agent,
    *,
    games: int = 100,
    seed: int = 0,
) -> TournamentResult:
    wins = [0, 0]
    draws = 0
    turns = 0
    for index in range(games):
        result = play_game(env, (agent_a, agent_b), seed=seed + index)
        turns += result.turns
        if result.winner is None:
            draws += 1
        else:
            wins[result.winner] += 1
    return TournamentResult(games, wins[0], wins[1], draws, turns / games if games else 0.0)
