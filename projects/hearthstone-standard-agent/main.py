"""Run complete V0.1 games from the command line."""

from __future__ import annotations

import argparse
from pathlib import Path

from agents import MCTSAgent, RandomAgent, RuleAgent
from agents.meta_rule_agent import MetaRuleAgent
from env.card_db import CardDatabase
from env.hearthstone_env import HearthstoneEnv
from env.meta_stats import BoxMetaStats
from training.replay_buffer import ReplayBuffer
from training.self_play import play_game


ROOT = Path(__file__).resolve().parent


def make_agent(
    kind: str,
    *,
    seed: int,
    label: str,
    simulations: int,
    meta_stats: BoxMetaStats | None,
    deck_id: str,
):
    if kind == "random":
        return RandomAgent(seed=seed, name=f"{label}-Random")
    if kind == "rule":
        return RuleAgent(seed=seed, name=f"{label}-Rule")
    if kind == "mcts":
        return MCTSAgent(simulations=simulations, seed=seed, name=f"{label}-MCTS")
    if kind == "meta-rule":
        if meta_stats is None:
            raise SystemExit("--agent meta-rule requires --meta-stats CSV/JSON")
        return MetaRuleAgent(meta_stats, deck_id, seed=seed, name=f"{label}-MetaRule")
    raise ValueError(kind)


def main() -> None:
    parser = argparse.ArgumentParser(description="Hearthstone Standard Agent V0.1")
    choices = ("random", "rule", "mcts", "meta-rule")
    parser.add_argument("--agent-a", choices=choices, default="rule")
    parser.add_argument("--agent-b", choices=choices, default="random")
    parser.add_argument("--games", type=int, default=1)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--max-turns", type=int, default=80)
    parser.add_argument("--mcts-simulations", type=int, default=24)
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--replay", type=Path, help="save all state/action/outcome samples as JSONL")
    parser.add_argument("--meta-stats", type=Path, help="user-exported 炉石盒子/meta CSV or JSON")
    parser.add_argument("--deck-id-a", default="demo_mage")
    parser.add_argument("--deck-id-b", default="demo_warrior")
    args = parser.parse_args()

    if args.games < 1:
        parser.error("--games must be at least 1")
    db = CardDatabase.load()
    mage = db.load_deck("data/decks/mage.json")
    warrior = db.load_deck("data/decks/warrior.json")
    env = HearthstoneEnv(db, mage, warrior, max_turns=args.max_turns)
    stats = BoxMetaStats.load(args.meta_stats) if args.meta_stats else None
    agent_a = make_agent(
        args.agent_a,
        seed=args.seed + 101,
        label="Mage",
        simulations=args.mcts_simulations,
        meta_stats=stats,
        deck_id=args.deck_id_a,
    )
    agent_b = make_agent(
        args.agent_b,
        seed=args.seed + 202,
        label="Warrior",
        simulations=args.mcts_simulations,
        meta_stats=stats,
        deck_id=args.deck_id_b,
    )

    buffer = ReplayBuffer()
    wins = [0, 0]
    draws = 0
    total_turns = 0
    for game_index in range(args.games):
        print(f"Game {game_index + 1}: {mage.name} vs {warrior.name}")
        result = play_game(
            env,
            (agent_a, agent_b),
            seed=args.seed + game_index,
            verbose=args.verbose,
        )
        total_turns += result.turns
        buffer.extend(result.samples)
        if result.winner is None:
            draws += 1
            print(f"Winner: Draw (turns={result.turns}, actions={result.actions})")
        else:
            wins[result.winner] += 1
            winner_agent = (agent_a, agent_b)[result.winner]
            winner_class = (mage, warrior)[result.winner].hero_class
            print(
                f"Winner: Player {result.winner + 1} {winner_class} / {winner_agent.name} "
                f"(turns={result.turns}, actions={result.actions})"
            )
    print(
        f"Summary: games={args.games}, Mage={wins[0]}, Warrior={wins[1]}, draws={draws}, "
        f"average_turns={total_turns / args.games:.1f}"
    )
    if args.replay:
        buffer.save_jsonl(args.replay)
        print(f"Replay saved: {args.replay.resolve()}")


if __name__ == "__main__":
    main()
