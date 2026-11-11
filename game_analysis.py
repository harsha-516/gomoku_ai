"""
game_analysis.py - Post-game analysis built on the agents engine.

Replays a finished game move by move and, for the chosen player, finds the
events listed in section 7.11 of the synopsis:

    missed_win        - a five was available but another move was played
    missed_block      - the opponent threatened five and it was not blocked
    missed_defence    - the opponent could make an open four (open three) and it was ignored
    weak_move         - a move far weaker than the best available (poor strategic decision)
    strong_move       - wins, blocks, forks, open fours, blocked open threes
    danger            - dangerous patterns the opponent built (open threes, fours, forks)

It also aggregates the most common mistake into a coaching tip.
"""

from __future__ import annotations

from collections import Counter
from typing import Dict, List

from agents import (
    FOUR, OPEN_FOUR, OPEN_THREE, candidate_cells, describe_move, empty_board, local_threats,
    makes_five, move_score, other,
)

STRONG_REASONS = {
    "Completes five in a row",
    "Blocks opponent's five",
    "Creates an open four (unstoppable)",
    "Creates a double threat (fork)",
    "Blocks opponent's open three",
    "Creates a double open three (fork)",
    "Prevents an opponent fork",
}

TIPS = {
    "missed_win": "Before every move, look for a line of four you can finish. Winning comes first!",
    "missed_block": "Always check if your opponent has four in a row. If yes, block it straight away.",
    "missed_defence": "An open three (three in a row with empty space on both sides) is dangerous. "
                      "Block one end before it becomes an open four.",
    "weak_move": "Play close to the action. Moves that join your stones or cut your opponent's lines are strongest.",
}


def _cell(r: int, c: int) -> str:
    return f"{chr(65 + c)}{r + 1}"


def analyze_game(moves: List[Dict], perspective: str, size: int = 15) -> Dict:
    """Analyse ``moves`` (dicts with player, row, col) for ``perspective``."""
    state = empty_board(size)
    events: List[Dict] = []
    opp = other(perspective)

    for i, m in enumerate(moves, start=1):
        mover, r, c = m["player"], int(m["row"]), int(m["col"])
        if state[r][c] is not None:
            raise ValueError(f"move {i} plays on an occupied cell {_cell(r, c)}")

        if mover == perspective:
            cands = candidate_cells(state)
            wins = [x for x in cands if makes_five(state, x[0], x[1], mover)]
            fives = [x for x in cands if makes_five(state, x[0], x[1], opp)]
            open3_blocks = [x for x in cands if local_threats(state, x[0], x[1], opp)[OPEN_FOUR]]
            mine = local_threats(state, r, c, mover)
            played_win = (r, c) in wins
            reason = describe_move(state, r, c, mover)

            if wins and not played_win:
                events.append({"move_no": i, "type": "missed_win", "cell": _cell(r, c),
                               "better": _cell(*wins[0]),
                               "text": f"You could have won at {_cell(*wins[0])}."})
            elif fives and (r, c) not in fives and not played_win:
                events.append({"move_no": i, "type": "missed_block", "cell": _cell(r, c),
                               "better": _cell(*fives[0]),
                               "text": f"Your opponent had four in a row. Block at {_cell(*fives[0])}."})
            elif (open3_blocks and (r, c) not in open3_blocks and not played_win
                  and not (mine[FOUR] or mine[OPEN_FOUR])):
                events.append({"move_no": i, "type": "missed_defence", "cell": _cell(r, c),
                               "better": _cell(*open3_blocks[0]),
                               "text": f"Your opponent's open three needed blocking, e.g. at {_cell(*open3_blocks[0])}."})
            elif reason in STRONG_REASONS:
                events.append({"move_no": i, "type": "strong_move", "cell": _cell(r, c),
                               "text": f"{reason}."})
            elif len(cands) > 3:
                scores = {x: move_score(state, x[0], x[1], mover) for x in cands}
                best = max(scores, key=scores.get)
                if scores[best] >= 1000 and scores.get((r, c), 0) < 0.3 * scores[best]:
                    events.append({"move_no": i, "type": "weak_move", "cell": _cell(r, c),
                                   "better": _cell(*best),
                                   "text": f"{_cell(*best)} was a much stronger spot."})
        else:
            theirs = local_threats(state, r, c, mover)
            if not makes_five(state, r, c, mover):
                if theirs[OPEN_FOUR] or theirs[FOUR] >= 2 or (theirs[FOUR] and theirs[OPEN_THREE]):
                    text = "Your opponent made a double threat or an open four."
                elif theirs[FOUR]:
                    text = "Your opponent made four in a row."
                elif theirs[OPEN_THREE]:
                    text = "Your opponent made an open three."
                else:
                    text = ""
                if text:
                    events.append({"move_no": i, "type": "danger", "cell": _cell(r, c), "text": text})

        state[r][c] = mover

    counts = Counter(e["type"] for e in events)
    mistakes = {k: counts.get(k, 0) for k in ("missed_win", "missed_block", "missed_defence", "weak_move")}
    total_mistakes = sum(mistakes.values())
    my_moves = sum(1 for m in moves if m["player"] == perspective)
    worst = max(mistakes, key=mistakes.get) if total_mistakes else None
    stars = 3 if total_mistakes == 0 else (2 if total_mistakes <= max(1, my_moves // 8) else 1)
    return {
        "perspective": perspective,
        "moves": len(moves),
        "your_moves": my_moves,
        "strong_moves": counts.get("strong_move", 0),
        "dangers": counts.get("danger", 0),
        "mistakes": mistakes,
        "total_mistakes": total_mistakes,
        "stars": stars,
        "tip": TIPS[worst] if worst else "Fantastic game. No big mistakes found!",
        "events": events,
    }
