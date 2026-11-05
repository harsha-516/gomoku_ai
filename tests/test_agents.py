"""Unit tests for game rules, heuristic and AI agents.  Run:  python -m pytest -q"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents import (  # noqa: E402
    AlphaBetaAgent, ExpertAgent, MinimaxAgent, RandomAgent, RuleBasedAgent,
    candidate_cells, empty_board, evaluate, generate_moves, is_five, is_full,
    legal_moves, make_agent, winning_line,
)

ALL_AGENTS = [
    lambda: RuleBasedAgent(seed=1),
    lambda: MinimaxAgent(depth=2),
    lambda: AlphaBetaAgent(depth=3),
    lambda: ExpertAgent(time_limit=1.0),
]


def board(stones):
    s = empty_board()
    for r, c, col in stones:
        s[r][c] = col
    return s


# ---------------- rules ----------------

@pytest.mark.parametrize("cells", [
    [(7, c) for c in range(3, 8)],              # horizontal
    [(r, 4) for r in range(5, 10)],             # vertical
    [(i, i) for i in range(2, 7)],              # diagonal
    [(i, 10 - i) for i in range(3, 8)],         # anti-diagonal
    [(14, c) for c in range(10, 15)],           # touching the edge
])
def test_five_detected_in_every_direction(cells):
    s = board([(r, c, "black") for r, c in cells])
    assert all(is_five(s, r, c, "black") for r, c in cells)
    assert winning_line(s, *cells[0]) == sorted(cells)


def test_four_is_not_a_win():
    s = board([(7, c, "black") for c in range(3, 7)])
    assert not is_five(s, 7, 3, "black")


def test_blocked_five_of_other_colour_not_counted():
    s = board([(7, 3, "black"), (7, 4, "black"), (7, 5, "white"), (7, 6, "black"), (7, 7, "black")])
    assert not any(is_five(s, 7, c, "black") for c in (3, 4, 6, 7))


def test_draw_detection_full_board():
    s = empty_board()
    for r in range(15):
        for c in range(15):
            s[r][c] = "black" if ((r // 2) + c) % 2 == 0 else "white"
    assert is_full(s)
    assert legal_moves(s) == []


def test_candidate_generation_reduces_branching():
    s = board([(7, 7, "black")])
    cands = candidate_cells(s)
    assert len(cands) == 24  # 5x5 square around the stone, minus itself
    assert len(legal_moves(s)) == 224
    assert candidate_cells(empty_board()) == [(7, 7)]


# ---------------- heuristic ----------------

def test_evaluation_prefers_stronger_shapes():
    two = board([(7, 7, "black"), (7, 8, "black")])
    three = board([(7, 7, "black"), (7, 8, "black"), (7, 9, "black")])
    assert evaluate(three, "black") > evaluate(two, "black") > 0


def test_evaluation_is_symmetric():
    s = board([(7, 7, "black"), (7, 8, "black"), (8, 8, "white")])
    assert evaluate(s, "black") == -evaluate(s, "white")


def test_open_three_beats_closed_three():
    open3 = board([(7, 6, "black"), (7, 7, "black"), (7, 8, "black")])
    closed3 = board([(7, 6, "black"), (7, 7, "black"), (7, 8, "black"), (7, 5, "white")])
    assert evaluate(open3, "black") > evaluate(closed3, "black")


# ---------------- agents ----------------

@pytest.mark.parametrize("factory", ALL_AGENTS)
def test_agent_takes_immediate_win(factory):
    s = board([(7, c, "black") for c in range(3, 7)] + [(8, 3, "white"), (8, 4, "white"), (9, 9, "white")])
    assert factory().choose_move(s, "black") in [(7, 2), (7, 7)]


@pytest.mark.parametrize("factory", ALL_AGENTS)
def test_agent_blocks_opponent_four(factory):
    s = board([(7, 3, "white"), (7, 4, "white"), (7, 5, "white"), (7, 6, "white"), (7, 2, "black"),
               (9, 9, "black")])
    assert factory().choose_move(s, "black") == (7, 7)


@pytest.mark.parametrize("factory", ALL_AGENTS)
def test_agent_blocks_open_three(factory):
    s = board([(7, 6, "white"), (7, 7, "white"), (7, 8, "white"), (8, 7, "black"), (6, 8, "black")])
    assert factory().choose_move(s, "black") in [(7, 5), (7, 9), (7, 4), (7, 10)]


def test_random_agent_plays_legal_moves():
    s = board([(7, 7, "black")])
    agent = RandomAgent(seed=3)
    for _ in range(20):
        r, c = agent.choose_move(s, "white")
        assert s[r][c] is None


def test_agent_does_not_modify_callers_board():
    s = board([(7, 7, "black"), (7, 8, "white")])
    snapshot = [row[:] for row in s]
    AlphaBetaAgent(depth=2).choose_move(s, "black")
    assert s == snapshot


@pytest.mark.parametrize("depth", [1, 2, 3])
def test_alpha_beta_matches_minimax(depth):
    """Alpha-beta must return the same value and move as minimax, with fewer states."""
    s = board([(7, 7, "black"), (7, 8, "white"), (8, 8, "black"), (6, 6, "white"), (8, 7, "black"),
               (9, 6, "white")])
    mm, ab = MinimaxAgent(depth=depth, max_candidates=8), AlphaBetaAgent(depth=depth, max_candidates=8)
    abu = AlphaBetaAgent(depth=depth, max_candidates=8, ordered=False)
    m1, m2, m3 = mm.choose_move(s, "black"), ab.choose_move(s, "black"), abu.choose_move(s, "black")
    assert mm.stats.score == ab.stats.score == abu.stats.score
    assert m1 == m2
    assert ab.stats.nodes <= mm.stats.nodes
    assert abu.stats.nodes <= mm.stats.nodes


def test_generate_moves_forced_block():
    s = board([(7, c, "white") for c in range(3, 7)] + [(7, 2, "black")])
    assert generate_moves(s, "black") == [(7, 7)]


def test_stats_are_recorded():
    agent = AlphaBetaAgent(depth=2)
    agent.choose_move(board([(7, 7, "black")]), "white")
    assert agent.stats.nodes > 0 and agent.stats.depth == 2 and agent.stats.reason


def test_make_agent_by_difficulty():
    assert isinstance(make_agent("Easy"), RandomAgent)
    assert isinstance(make_agent("Medium (Rule-Based)"), RuleBasedAgent)
    assert isinstance(make_agent("Hard"), AlphaBetaAgent)
    assert isinstance(make_agent("Expert"), ExpertAgent)
    with pytest.raises(ValueError):
        make_agent("Impossible")
