"""
tutor.py - The AI as a teacher: move coaching, puzzles, problem formulation
and a fairness experiment.

Everything here exists to help a *human* understand and improve:

* coach_move()       judges one move the moment it is played and explains why
                     (with a better move when there was one)
* make_puzzle()      the AI generates a new tactics puzzle by playing games
                     against itself until a teachable moment appears
* check_answer()     marks a puzzle answer and explains the right idea
* formulate()        the game as a state-space search problem, filled in with
                     the real numbers of a given board
* fairness_check()   measures the first-move bias with robot self-play
"""

from __future__ import annotations

import math
import random
from typing import Dict, List, Optional

from agents import (
    FOUR, OPEN_FOUR, OPEN_THREE, RandomAgent, RuleBasedAgent, candidate_cells, describe_move, empty_board,
    is_five, is_full, legal_moves, local_threats, makes_five, move_score, other,
)
from game_analysis import move_quality


def _cell(r: int, c: int) -> str:
    return f"{chr(65 + c)}{r + 1}"


# --------------------------------------------------------------------------- answers for each lesson type

PUZZLE_KINDS = {
    "win": "Find the move that makes five in a row and wins.",
    "block": "Your opponent has four in a row. Find the move that blocks it.",
    "open_three": "Your opponent has an open three. Block it before it becomes an open four.",
    "open_four": "Make an open four: four in a row with both ends empty, so it cannot be stopped.",
    "fork": "Make a double threat (a fork): two threats at once, so only one can be blocked.",
}


def answers(state, color: str, kind: str) -> List[List[int]]:
    """All correct moves for a puzzle of the given kind."""
    opp = other(color)
    cands = candidate_cells(state)
    if kind == "win":
        good = [m for m in cands if makes_five(state, m[0], m[1], color)]
    elif kind == "block":
        good = [m for m in cands if makes_five(state, m[0], m[1], opp)]
    elif kind == "open_three":
        good = [m for m in cands if local_threats(state, m[0], m[1], opp)[OPEN_FOUR]]
    elif kind == "open_four":
        good = [m for m in cands if local_threats(state, m[0], m[1], color)[OPEN_FOUR]]
    elif kind == "fork":
        good = []
        for m in cands:
            t = local_threats(state, m[0], m[1], color)
            if t[OPEN_FOUR] or t[FOUR] + t[OPEN_FOUR] >= 2 or (t[FOUR] and t[OPEN_THREE]) or t[OPEN_THREE] >= 2:
                good.append(m)
    else:
        raise ValueError(f"unknown puzzle kind '{kind}'")
    return [list(m) for m in good]


def _is_puzzle(state, color: str, kind: str) -> bool:
    """True if this position is a clean puzzle of ``kind``: the lesson's idea is
    the best thing to do, and no more urgent idea (a win, a block) is hiding."""
    if kind == "win":
        return bool(answers(state, color, "win"))
    if answers(state, color, "win"):
        return False
    if kind == "block":
        return bool(answers(state, color, "block"))
    if answers(state, color, "block"):
        return False
    if kind == "open_four":
        return bool(answers(state, color, "open_four"))
    if kind == "open_three":
        # if you can make an open four yourself you would win instead of defending
        return bool(answers(state, color, "open_three")) and not answers(state, color, "open_four")
    if kind == "fork":
        return (not answers(state, color, "open_four") and not answers(state, color, "open_three")
                and 1 <= len(answers(state, color, "fork")) <= 4)
    return False


def make_puzzle(kind: str, size: int = 9, seed: Optional[int] = None, tries: int = 300) -> Dict:
    """Let two robots play from a random opening until a position of ``kind`` appears."""
    if kind not in PUZZLE_KINDS:
        raise ValueError(f"unknown puzzle kind '{kind}'")
    rng = random.Random(seed)
    for _ in range(tries):
        state = empty_board(size)
        c = size // 2
        players = {"black": RuleBasedAgent(seed=rng.randrange(10 ** 6)), "white": RuleBasedAgent(seed=rng.randrange(10 ** 6))}
        noise = RandomAgent(seed=rng.randrange(10 ** 6))
        state[c][c] = "black"
        color = "white"
        for ply in range(size * size):
            if is_full(state):
                break
            if ply > 2 and _is_puzzle(state, color, kind):
                good = answers(state, color, kind)
                if 1 <= len(good) <= 6:
                    return {"kind": kind, "task": PUZZLE_KINDS[kind], "size": size, "color": color,
                            "board": state, "answers": good}
            # a little randomness so every puzzle is different
            agent = noise if rng.random() < 0.15 else players[color]
            near = candidate_cells(state)
            m = rng.choice(near) if agent is noise else agent.choose_move(state, color)
            state[m[0]][m[1]] = color
            if is_five(state, m[0], m[1], color):
                break
            color = other(color)
    raise RuntimeError("could not generate a puzzle, try again")


def check_answer(state, color: str, kind: str, move) -> Dict:
    good = answers(state, color, kind)
    r, c = move
    ok = [r, c] in good
    reason = describe_move(state, r, c, color) if state[r][c] is None else "That square is taken"
    return {"correct": ok, "answers": good, "your_move": _cell(r, c), "explanation": reason,
            "solution": [_cell(*m) for m in good],
            "message": (f"Correct! {reason}." if ok else
                        f"Not quite. Your move {_cell(r, c)}: {reason.lower()}. The answer{'s are' if len(good) > 1 else ' is'} "
                        f"{', '.join(_cell(*m) for m in good)}: {PUZZLE_KINDS[kind].split('. ')[0].lower()}.")}


# --------------------------------------------------------------------------- live coaching of one move

def coach_move(state, color: str, move) -> Dict:
    """Judge a move the moment it is played (``state`` is the board *before* the move)."""
    r, c = move
    opp = other(color)
    quality = move_quality(state, r, c, color)
    cands = candidate_cells(state)
    wins = [m for m in cands if makes_five(state, m[0], m[1], color)]
    blocks = [m for m in cands if makes_five(state, m[0], m[1], opp)]
    open3 = [m for m in cands if local_threats(state, m[0], m[1], opp)[OPEN_FOUR]]
    reason = describe_move(state, r, c, color)
    best = max(cands, key=lambda m: move_score(state, m[0], m[1], color)) if cands else (r, c)
    verdict, text, better = "good", reason, None
    if wins and (r, c) not in wins:
        verdict, better = "mistake", wins[0]
        text = f"You could have WON at {_cell(*wins[0])}!"
    elif blocks and (r, c) not in blocks and (r, c) not in wins:
        verdict, better = "mistake", blocks[0]
        text = f"Careful: your opponent has four in a row. You needed to block at {_cell(*blocks[0])}."
    elif open3 and (r, c) not in open3 and not (local_threats(state, r, c, color)[FOUR] or (r, c) in wins):
        verdict, better = "warning", open3[0]
        text = f"Your opponent has an open three. Blocking at {_cell(*open3[0])} would be safer."
    elif quality >= 0.85:
        verdict = "great"
    elif quality < 0.35:
        verdict, better = "warning", best
        text = f"{reason}. A stronger square was {_cell(*best)}."
    return {"verdict": verdict, "quality": round(quality * 100), "text": text, "reason": reason,
            "better": list(better) if better else None, "better_cell": _cell(*better) if better else None}


# --------------------------------------------------------------------------- state-space formulation

def formulate(state, color: str) -> Dict:
    """The game as a search problem, with the real numbers of this board."""
    n = len(state)
    stones = sum(v is not None for row in state for v in row)
    empty = len(legal_moves(state))
    cands = len(candidate_cells(state)) if stones else 1
    over = any(state[r][c] and is_five(state, r, c, state[r][c]) for r in range(n) for c in range(n))
    return {
        "size": n, "stones": stones, "to_move": color, "empty": empty, "candidates": cands,
        "terminal": over or empty == 0,
        "state_space_digits": round(n * n * math.log10(3)),          # 3^(n*n) upper bound
        "tree_depth3_uninformed": empty * max(empty - 1, 0) * max(empty - 2, 0),
        "tree_depth3_informed": cands ** 3,
        "components": [
            {"name": "State", "text": f"A {n}×{n} grid where every cell is empty, black or white, plus whose turn it is. "
                                      f"Now: {stones} stones, {color} to move."},
            {"name": "Initial state", "text": "The empty board with Black to move (or a short random opening in Robot Battle)."},
            {"name": "Actions", "text": f"Place one stone on any empty cell. Here: {empty} legal actions, of which the AI "
                                        f"keeps {cands} candidate cells near existing stones."},
            {"name": "Transition model", "text": "RESULT(state, cell) = the same board with the mover's stone on that cell, and the turn passes to the other player."},
            {"name": "Goal (terminal) test", "text": "Five or more stones of one colour in a row (horizontal, vertical or diagonal), "
                                                     f"or a full board (draw). This board is {'terminal' if over or empty == 0 else 'not terminal'}."},
            {"name": "Utility", "text": "+∞ (win) / −∞ (loss) / 0 (draw) at terminal states. Before that the heuristic function estimates it."},
            {"name": "Path cost", "text": "Not used: only the final result matters, so every move costs the same. Faster wins are preferred slightly."},
            {"name": "Search strategy", "text": "Adversarial search (minimax), because the opponent tries to minimise our result. "
                                                "Alpha-beta pruning and candidate move generation make it fast enough; "
                                                "blind minimax shows why an uninformed search is too slow."},
        ],
    }


# --------------------------------------------------------------------------- fairness experiment

def fairness_check(games: int = 10, size: int = 9, seed: int = 7) -> Dict:
    """The same rule-based robot plays itself: does the colour that moves first win more?

    Then the same openings are replayed with the robots' colours swapped, which
    is how Robot Battle keeps comparisons between robots fair.
    """
    rng = random.Random(seed)
    tally = {"black": 0, "white": 0, "draw": 0}
    for g in range(games):
        state = empty_board(size)
        c = size // 2
        state[c][c] = "black"
        color = "white"
        agents = {"black": RuleBasedAgent(seed=rng.randrange(10 ** 6)), "white": RuleBasedAgent(seed=rng.randrange(10 ** 6))}
        result = "draw"
        while not is_full(state):
            m = agents[color].choose_move(state, color)
            state[m[0]][m[1]] = color
            if is_five(state, m[0], m[1], color):
                result = color
                break
            color = other(color)
        tally[result] += 1
    decided = tally["black"] + tally["white"]
    return {"games": games, "size": size, **tally,
            "black_share": round(tally["black"] / decided, 2) if decided else None,
            "conclusion": ("Black (moving first) wins more often: a first-move bias." if decided and tally["black"] > tally["white"]
                           else "No first-move advantage showed up in this sample.")}
