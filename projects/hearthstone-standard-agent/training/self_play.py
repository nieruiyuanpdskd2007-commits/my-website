"""Complete-game runner and self-play data collection."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from agents.base import Agent
from env.hearthstone_env import HearthstoneEnv
from training.replay_buffer import ReplaySample


@dataclass(slots=True)
class GameResult:
    winner: int | None
    turns: int
    actions: int
    samples: list[ReplaySample]


def play_game(
    env: HearthstoneEnv,
    agents: tuple[Agent, Agent],
    *,
    seed: int = 0,
    verbose: bool = False,
    log: Callable[[str], None] = print,
) -> GameResult:
    observations = env.reset(seed=seed)
    for player in (0, 1):
        env.mulligan(player, agents[player].choose_mulligan(observations[player]))
    env.start()
    engine = env.engine
    assert engine is not None
    trajectory: list[tuple[dict, dict, int]] = []
    action_count = 0
    last_turn = 0
    while not engine.terminal:
        player = engine.current_player
        observation = engine.observation(player)
        legal = engine.legal_actions()
        action = agents[player].choose_action(observation, legal, engine)
        if verbose and engine.turn != last_turn:
            log(
                f"Turn {engine.turn}: P{player + 1} {engine.players[player].hero.hero_class} "
                f"({engine.players[player].mana}/{engine.players[player].max_mana} mana)"
            )
            last_turn = engine.turn
        if verbose:
            log(f"  {agents[player].name}: {engine.describe_action(action, player)}")
        trajectory.append((observation, action.to_dict(), player))
        env.step(action)
        action_count += 1
        if action_count > 5_000:
            raise RuntimeError("Game exceeded action safety limit")

    samples = [
        ReplaySample(
            observation=observation,
            action=action,
            player=player,
            outcome=0.0 if engine.winner is None else (1.0 if engine.winner == player else -1.0),
        )
        for observation, action, player in trajectory
    ]
    return GameResult(engine.winner, engine.turn, action_count, samples)
