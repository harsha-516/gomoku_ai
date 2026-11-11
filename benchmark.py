"""
benchmark.py - Experimental comparison of the Gomoku AI agents.

Runs the two experiments from the project synopsis and writes the results
to results/ (CSV + PNG charts):

  1. Search efficiency - on the same test positions, compare Minimax,
     Alpha-Beta without move ordering and Alpha-Beta with move ordering at
     depths 1..3: game states explored, time, and whether they agree on the
     minimax value (they must - pruning never changes the answer).

  2. Tournament - every agent plays every other agent (colours alternate,
     each game starts from a random two-stone opening) and we record wins,
     game length, time per move and states explored per move. Every move
     is also logged with the board state and AI decision info, which is the
     dataset for future machine-learning work.

Usage:
    python benchmark.py                 # full run (several minutes)
    python benchmark.py --quick         # small run for a demo
    python benchmark.py --games 6 --skip-efficiency
"""

from __future__ import annotations

import argparse
import csv
import itertools
import os
import random
import time
from datetime import datetime
from typing import Dict, List

from agents import (
    AlphaBetaAgent, BlindMinimaxAgent, ExpertAgent, MinimaxAgent, RandomAgent, RuleBasedAgent,
    empty_board, is_five, is_full, other,
)

RESULTS_DIR = "results"

# Categorical palette (fixed order) from the project's chart style guide.
COLORS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300"]
INK, MUTED, GRID, SURFACE = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"


def board_to_string(state) -> str:
    """225-char snapshot: '.' empty, 'b' black, 'w' white (row-major)."""
    return "".join("." if v is None else v[0] for row in state for v in row)


def tournament_agents(expert_time: float):
    return [
        ("Random", lambda: RandomAgent()),
        ("Rule-Based", lambda: RuleBasedAgent()),
        ("Minimax d2", lambda: MinimaxAgent(depth=2, max_candidates=10)),
        ("Alpha-Beta d3", lambda: AlphaBetaAgent(depth=3, max_candidates=12)),
        ("Expert", lambda: ExpertAgent(time_limit=expert_time)),
    ]


# ----------------------------------------------------------------------------
# Experiment 1: search efficiency
# ----------------------------------------------------------------------------

def make_test_positions(n: int, seed: int = 7) -> List:
    """Realistic mid-game positions: rule-based self-play from random openings."""
    rng = random.Random(seed)
    positions = []
    while len(positions) < n:
        state = empty_board()
        state[7][7] = "black"
        r, c = 7 + rng.choice([-1, 0, 1]), 7 + rng.choice([-1, 1])
        state[r][c] = "white"
        color = "black"
        players = RuleBasedAgent(seed=rng.randrange(10**6))
        target = rng.randint(6, 14)
        ok = True
        for _ in range(target):
            m = players.choose_move(state, color)
            state[m[0]][m[1]] = color
            if is_five(state, m[0], m[1], color):
                ok = False
                break
            color = other(color)
        if ok:
            positions.append((state, color))
    return positions


def run_efficiency(n_positions: int, max_depth: int) -> List[Dict]:
    print(f"\n=== Experiment 1: search efficiency ({n_positions} positions, depth 1-{max_depth}) ===")
    positions = make_test_positions(n_positions)
    rows = []
    for depth in range(1, max_depth + 1):
        algos = [
            ("Minimax", MinimaxAgent(depth=depth, max_candidates=10)),
            ("Alpha-Beta (unordered)", AlphaBetaAgent(depth=depth, max_candidates=10, ordered=False)),
            ("Alpha-Beta (ordered)", AlphaBetaAgent(depth=depth, max_candidates=10)),
        ]
        for pid, (state, color) in enumerate(positions):
            scores = []
            for name, agent in algos:
                move = agent.choose_move(state, color)
                s = agent.stats
                scores.append(s.score)
                rows.append({
                    "position": pid, "depth": depth, "algorithm": name,
                    "nodes": s.nodes, "evaluations": s.evaluations, "cutoffs": s.cutoffs,
                    "time_ms": round(s.time_ms, 2), "score": s.score,
                    "move": f"{move[0]},{move[1]}",
                })
            agree = len(set(scores)) == 1
            for row in rows[-3:]:
                row["same_value_as_minimax"] = int(agree)
        summary = {name: [r for r in rows if r["depth"] == depth and r["algorithm"] == name]
                   for name, _ in algos}
        line = " | ".join(f"{name}: {sum(r['nodes'] for r in rs) / len(rs):,.0f} states"
                          for name, rs in summary.items())
        print(f"depth {depth}: {line}")
    agree_all = all(r["same_value_as_minimax"] for r in rows)
    print("All algorithms returned the same minimax value:", "YES" if agree_all else "NO")
    return rows


# ----------------------------------------------------------------------------
# Experiment 2: tournament
# ----------------------------------------------------------------------------

def play_game(black, white, seed: int, game_id: int, move_rows: List[Dict]) -> Dict:
    rng = random.Random(seed)
    state = empty_board()
    # random two-stone opening so repeated games between deterministic agents differ
    state[7][7] = "black"
    wr, wc = 7 + rng.choice([-1, 0, 1]), 7 + rng.choice([-1, 1])
    state[wr][wc] = "white"
    agents = {"black": black, "white": white}
    stats = {"black": [], "white": []}
    color, winner, move_no = "black", "Draw", 2
    started = time.perf_counter()
    while True:
        if is_full(state):
            break
        agent = agents[color]
        move = agent.choose_move(state, color)
        if move is None:
            break
        s = agent.stats
        stats[color].append(s)
        state[move[0]][move[1]] = color
        move_no += 1
        move_rows.append({
            "game_id": game_id, "move_no": move_no, "player": color, "agent": agent.name,
            "row": move[0], "col": move[1], "nodes": s.nodes, "evaluations": s.evaluations,
            "depth": s.depth, "time_ms": round(s.time_ms, 2), "score": s.score,
            "reason": s.reason, "board_after": board_to_string(state),
        })
        if is_five(state, move[0], move[1], color):
            winner = color
            break
        color = other(color)

    def avg(xs):
        return round(sum(xs) / len(xs), 2) if xs else 0

    return {
        "game_id": game_id, "black": black.label, "white": white.label,
        "winner": winner,
        "winner_agent": {"black": black.label, "white": white.label}.get(winner, "Draw"),
        "moves": move_no, "duration_s": round(time.perf_counter() - started, 2),
        "black_avg_ms": avg([s.time_ms for s in stats["black"]]),
        "white_avg_ms": avg([s.time_ms for s in stats["white"]]),
        "black_avg_nodes": avg([s.nodes for s in stats["black"]]),
        "white_avg_nodes": avg([s.nodes for s in stats["white"]]),
    }


# ----------------------------------------------------------------------------
# Experiment 3: state space vs board size (uninformed vs informed search)
# ----------------------------------------------------------------------------

def run_state_space(sizes=(7, 9, 11, 13, 15)) -> List[Dict]:
    """Same small opening on boards of different sizes, depth-2 search.

    Blind (uninformed) minimax must consider every empty cell, so the states it
    explores grow with the board (about n^2 x n^2). Informed search only looks
    near the stones, so its cost stays almost flat.
    """
    print("\n=== Experiment 3: states explored vs board size (depth 2) ===")
    rows = []
    for n in sizes:
        state = empty_board(n)
        c = n // 2
        state[c][c], state[c][c + 1], state[c + 1][c] = "black", "white", "black"
        for name, agent in (("Blind Minimax (uninformed)", BlindMinimaxAgent(depth=2, node_limit=10**7, seed=1)),
                            ("Minimax (informed)", MinimaxAgent(depth=2, max_candidates=10)),
                            ("Alpha-Beta (informed)", AlphaBetaAgent(depth=2, max_candidates=10))):
            agent.choose_move(state, "white")
            rows.append({"board": f"{n}x{n}", "cells": n * n, "algorithm": name, "nodes": agent.stats.nodes,
                         "time_ms": round(agent.stats.time_ms, 1)})
        print(f"  {n:>2}x{n:<2}: " + " | ".join(f"{r['algorithm']}: {r['nodes']:,}" for r in rows[-3:]))
    return rows


def run_tournament(games_per_pair: int, expert_time: float):
    roster = tournament_agents(expert_time)
    print(f"\n=== Experiment 2: round-robin tournament ({games_per_pair} games per pairing) ===")
    games, moves = [], []
    gid = 0
    for (na, fa), (nb, fb) in itertools.combinations(roster, 2):
        for g in range(games_per_pair):
            a, b = fa(), fb()
            a.label, b.label = na, nb
            black, white = (a, b) if g % 2 == 0 else (b, a)
            gid += 1
            res = play_game(black, white, seed=1000 + gid, game_id=gid, move_rows=moves)
            games.append(res)
            print(f"  game {gid:3d}: {res['black']:>13} (B) vs {res['white']:<13} (W) -> "
                  f"{res['winner_agent']:<13} in {res['moves']} moves ({res['duration_s']}s)")
    return roster, games, moves


def standings(roster, games) -> List[Dict]:
    table = []
    for name, _ in roster:
        played = [g for g in games if name in (g["black"], g["white"])]
        wins = sum(1 for g in played if g["winner_agent"] == name)
        draws = sum(1 for g in played if g["winner_agent"] == "Draw")
        ms, nodes = [], []
        for g in played:
            side = "black" if g["black"] == name else "white"
            ms.append(g[f"{side}_avg_ms"])
            nodes.append(g[f"{side}_avg_nodes"])
        table.append({
            "agent": name, "played": len(played), "wins": wins, "draws": draws,
            "losses": len(played) - wins - draws,
            "win_rate": round(wins / len(played), 3) if played else 0,
            "avg_ms_per_move": round(sum(ms) / len(ms), 1) if ms else 0,
            "avg_states_per_move": round(sum(nodes) / len(nodes), 1) if nodes else 0,
        })
    table.sort(key=lambda r: r["win_rate"], reverse=True)
    return table


# ----------------------------------------------------------------------------
# Output
# ----------------------------------------------------------------------------

def write_csv(path: str, rows: List[Dict]) -> None:
    if not rows:
        return
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print("  wrote", path)


def _style(ax, title, xlabel, ylabel):
    ax.set_title(title, loc="left", fontsize=12, color=INK, pad=12, fontweight="bold")
    ax.set_xlabel(xlabel, color=MUTED)
    ax.set_ylabel(ylabel, color=MUTED)
    ax.set_facecolor(SURFACE)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(GRID)
    ax.tick_params(colors=MUTED)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def make_charts(eff_rows, roster, games, table) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("  matplotlib not installed - skipping charts")
        return

    if eff_rows:
        fig, ax = plt.subplots(figsize=(8, 5), facecolor=SURFACE)
        algos = list(dict.fromkeys(r["algorithm"] for r in eff_rows))
        depths = sorted({r["depth"] for r in eff_rows})
        for i, name in enumerate(algos):
            ys = [sum(r["nodes"] for r in eff_rows if r["depth"] == d and r["algorithm"] == name)
                  / max(1, len([r for r in eff_rows if r["depth"] == d and r["algorithm"] == name]))
                  for d in depths]
            ax.plot(depths, ys, color=COLORS[i], linewidth=2, marker="o", markersize=8, label=name)
            ax.annotate(f"{ys[-1]:,.0f}", (depths[-1], ys[-1]), xytext=(8, 0),
                        textcoords="offset points", va="center", color=INK, fontsize=9)
        ax.set_yscale("log")
        ax.set_xticks(depths)
        _style(ax, "Game states explored per move (log scale)", "Search depth (plies)", "States explored")
        ax.legend(frameon=False, labelcolor=INK)
        fig.tight_layout()
        fig.savefig(os.path.join(RESULTS_DIR, "search_efficiency.png"), dpi=150)
        plt.close(fig)

    if table:
        names = [n for n, _ in roster]
        idx = {n: i for i, n in enumerate(names)}

        # win-rate bar chart, each agent keeps its own colour
        fig, ax = plt.subplots(figsize=(8, 5), facecolor=SURFACE)
        order = [r["agent"] for r in table]
        vals = [r["win_rate"] * 100 for r in table]
        bars = ax.bar(order, vals, color=[COLORS[idx[n]] for n in order], width=0.6,
                      edgecolor=SURFACE, linewidth=2)
        for b, v in zip(bars, vals):
            ax.text(b.get_x() + b.get_width() / 2, v + 1.5, f"{v:.0f}%", ha="center", color=INK, fontsize=10)
        ax.set_ylim(0, 110)
        _style(ax, "Tournament win rate by agent", "", "Win rate (%)")
        fig.tight_layout()
        fig.savefig(os.path.join(RESULTS_DIR, "win_rates.png"), dpi=150)
        plt.close(fig)

        # head-to-head matrix: row agent's score vs column agent
        n = len(names)
        mat = [[float("nan")] * n for _ in range(n)]
        for a in names:
            for b in names:
                if a == b:
                    continue
                gs = [g for g in games if {g["black"], g["white"]} == {a, b}]
                if gs:
                    pts = sum(1 if g["winner_agent"] == a else 0.5 if g["winner_agent"] == "Draw" else 0
                              for g in gs)
                    mat[idx[a]][idx[b]] = pts / len(gs) * 100
        fig, ax = plt.subplots(figsize=(7.5, 6), facecolor=SURFACE)
        im = ax.imshow(mat, cmap="Blues", vmin=0, vmax=100)
        ax.set_xticks(range(n), names, rotation=30, ha="right", color=MUTED)
        ax.set_yticks(range(n), names, color=MUTED)
        for i in range(n):
            for j in range(n):
                if i != j and mat[i][j] == mat[i][j]:
                    v = mat[i][j]
                    ax.text(j, i, f"{v:.0f}%", ha="center", va="center",
                            color="white" if v > 60 else INK, fontsize=10)
        ax.set_title("Head-to-head score (row agent vs column agent)", loc="left",
                     fontsize=12, color=INK, pad=12, fontweight="bold")
        for s in ax.spines.values():
            s.set_visible(False)
        fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04, label="Score %")
        fig.tight_layout()
        fig.savefig(os.path.join(RESULTS_DIR, "head_to_head.png"), dpi=150)
        plt.close(fig)

        # strength vs cost: average time per move
        fig, ax = plt.subplots(figsize=(8, 5), facecolor=SURFACE)
        vals = [max(r["avg_ms_per_move"], 0.01) for r in table]
        bars = ax.bar(order, vals, color=[COLORS[idx[nm]] for nm in order], width=0.6,
                      edgecolor=SURFACE, linewidth=2)
        for b, v in zip(bars, vals):
            ax.text(b.get_x() + b.get_width() / 2, v * 1.15, f"{v:,.0f} ms" if v >= 1 else "<1 ms",
                    ha="center", color=INK, fontsize=10)
        ax.set_yscale("log")
        _style(ax, "Average thinking time per move (log scale)", "", "Milliseconds")
        fig.tight_layout()
        fig.savefig(os.path.join(RESULTS_DIR, "time_per_move.png"), dpi=150)
        plt.close(fig)
    print("  charts saved to", RESULTS_DIR + "/")


def make_state_space_chart(rows) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return
    fig, ax = plt.subplots(figsize=(8, 5), facecolor=SURFACE)
    algos = list(dict.fromkeys(r["algorithm"] for r in rows))
    for i, name in enumerate(algos):
        pts = [r for r in rows if r["algorithm"] == name]
        xs, ys = [r["cells"] for r in pts], [r["nodes"] for r in pts]
        ax.plot(xs, ys, color=COLORS[i], linewidth=2, marker="o", markersize=8, label=name)
        ax.annotate(f"{ys[-1]:,}", (xs[-1], ys[-1]), xytext=(8, 0), textcoords="offset points",
                    va="center", color=INK, fontsize=9)
    ax.set_yscale("log")
    ax.set_xticks([r["cells"] for r in rows if r["algorithm"] == algos[0]],
                  [r["board"] for r in rows if r["algorithm"] == algos[0]])
    _style(ax, "States explored vs board size (depth 2, log scale)", "Board size", "States explored")
    ax.legend(frameon=False, labelcolor=INK)
    fig.tight_layout()
    fig.savefig(os.path.join(RESULTS_DIR, "state_space.png"), dpi=150)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser(description="Benchmark the Gomoku AI agents")
    ap.add_argument("--games", type=int, default=4, help="games per pairing (default 4)")
    ap.add_argument("--positions", type=int, default=8, help="test positions for experiment 1")
    ap.add_argument("--max-depth", type=int, default=3, help="max depth for experiment 1")
    ap.add_argument("--expert-time", type=float, default=1.0, help="Expert time limit per move (s)")
    ap.add_argument("--quick", action="store_true", help="small, fast run")
    ap.add_argument("--skip-efficiency", action="store_true")
    ap.add_argument("--skip-tournament", action="store_true")
    ap.add_argument("--skip-state-space", action="store_true")
    args = ap.parse_args()
    if args.quick:
        args.games, args.positions, args.max_depth, args.expert_time = 2, 3, 2, 0.5

    os.makedirs(RESULTS_DIR, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    eff_rows, roster, games, table = [], [], [], []

    if not args.skip_efficiency:
        eff_rows = run_efficiency(args.positions, args.max_depth)
        write_csv(os.path.join(RESULTS_DIR, "search_efficiency.csv"), eff_rows)

    space_rows = []
    if not args.skip_state_space:
        space_rows = run_state_space()
        write_csv(os.path.join(RESULTS_DIR, "state_space.csv"), space_rows)

    if not args.skip_tournament:
        roster, games, moves = run_tournament(args.games, args.expert_time)
        table = standings(roster, games)
        write_csv(os.path.join(RESULTS_DIR, "tournament_games.csv"), games)
        write_csv(os.path.join(RESULTS_DIR, "tournament_moves.csv"), moves)
        write_csv(os.path.join(RESULTS_DIR, "standings.csv"), table)
        print("\nStandings:")
        print(f"  {'Agent':<14}{'W':>4}{'D':>4}{'L':>4}{'Win%':>7}{'ms/move':>10}{'states/move':>13}")
        for r in table:
            print(f"  {r['agent']:<14}{r['wins']:>4}{r['draws']:>4}{r['losses']:>4}"
                  f"{r['win_rate'] * 100:>6.0f}%{r['avg_ms_per_move']:>10.1f}{r['avg_states_per_move']:>13.1f}")

    make_charts(eff_rows, roster, games, table)
    if space_rows:
        make_state_space_chart(space_rows)
    print(f"\nDone ({stamp}).")


if __name__ == "__main__":
    main()
