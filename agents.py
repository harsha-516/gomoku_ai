"""
agents.py - The AI agents of the Intelligent Gomoku project.

This module implements the progression of AI techniques described in the
project synopsis, from an uninformed baseline to an informed, optimised
adversarial search:

    RandomAgent     - uninformed: picks any legal move                (Easy)
    RuleBasedAgent  - goal-based agent driven by fixed tactical rules (Medium)
    MinimaxAgent    - full minimax over candidate moves, no pruning
    AlphaBetaAgent  - minimax + alpha-beta pruning + move ordering    (Hard)
    ExpertAgent     - alpha-beta + iterative deepening + transposition
                      table (Zobrist hashing) under a time budget     (Expert)

Every agent follows the same perceive -> decide -> act cycle:
    move = agent.choose_move(state, color)
and records what it did in ``agent.stats`` (nodes explored, leaf
evaluations, cutoffs, depth, time, and a human readable reason), which is
what the benchmark and the GUI display.

The board ``state`` is a 15x15 list of lists holding None / "black" / "white",
the same representation the Tkinter pages use.
"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple

State = List[List[Optional[str]]]
Move = Tuple[int, int]

BOARD_SIZE = 15
CENTER = BOARD_SIZE // 2
MIN_BOARD, MAX_BOARD = 7, 19
WIN_SCORE = 10_000_000

DIRECTIONS = ((0, 1), (1, 0), (1, 1), (1, -1))


def other(color: str) -> str:
    return "white" if color == "black" else "black"


# ============================================================================
# 1. Game rules (shared by every agent, the tests and the benchmark)
# ============================================================================

def empty_board(size: int = BOARD_SIZE) -> State:
    return [[None] * size for _ in range(size)]


def legal_moves(state: State) -> List[Move]:
    n = len(state)
    return [(r, c) for r in range(n) for c in range(n) if state[r][c] is None]


def is_full(state: State) -> bool:
    return all(v is not None for row in state for v in row)


def is_five(state: State, row: int, col: int, color: str) -> bool:
    """True if the stone of ``color`` at (row, col) is part of 5+ in a row."""
    n = len(state)
    for dr, dc in DIRECTIONS:
        count = 1
        for sign in (1, -1):
            r, c = row + sign * dr, col + sign * dc
            while 0 <= r < n and 0 <= c < n and state[r][c] == color:
                count += 1
                r += sign * dr
                c += sign * dc
        if count >= 5:
            return True
    return False


def makes_five(state: State, row: int, col: int, color: str) -> bool:
    """True if playing ``color`` at the empty cell (row, col) wins the game."""
    state[row][col] = color
    win = is_five(state, row, col, color)
    state[row][col] = None
    return win


def winning_line(state: State, row: int, col: int) -> Optional[List[Move]]:
    """Cells of the five-in-a-row through (row, col), or None."""
    color = state[row][col]
    if color is None:
        return None
    n = len(state)
    for dr, dc in DIRECTIONS:
        line = [(row, col)]
        for sign in (1, -1):
            r, c = row + sign * dr, col + sign * dc
            while 0 <= r < n and 0 <= c < n and state[r][c] == color:
                line.append((r, c))
                r += sign * dr
                c += sign * dc
        if len(line) >= 5:
            return sorted(line)
    return None


# ============================================================================
# 2. Candidate move generation
# ============================================================================

def candidate_cells(state: State, radius: int = 2) -> List[Move]:
    """Empty cells within ``radius`` of an existing stone (the centre if empty).

    This is the key branching-factor reduction from the synopsis (section 7.8):
    instead of all 225 cells, only cells near the action are considered.
    """
    n = len(state)
    cells = set()
    any_stone = False
    for r in range(n):
        for c in range(n):
            if state[r][c] is None:
                continue
            any_stone = True
            for dr in range(-radius, radius + 1):
                rr = r + dr
                if not 0 <= rr < n:
                    continue
                for dc in range(-radius, radius + 1):
                    cc = c + dc
                    if 0 <= cc < n and state[rr][cc] is None:
                        cells.add((rr, cc))
    if not any_stone:
        return [(n // 2, n // 2)]
    return sorted(cells)


# ============================================================================
# 3. Heuristic evaluation (pattern based)
# ============================================================================
#
# Each line of the board is turned into a string from one player's point of
# view:  'X' = own stone, '.' = empty, '#' = opponent stone or board edge.
# Patterns are then counted with str.count, which is fast in Python.

FIVE, OPEN_FOUR, FOUR, OPEN_THREE, THREE, TWO = range(6)
CATEGORY_NAMES = ("five", "open four", "four", "open three", "three", "two")

PATTERNS: Tuple[Tuple[int, Tuple[str, ...]], ...] = (
    (1_000_000, ("XXXXX",)),                                        # five
    (100_000, (".XXXX.",)),                                         # open four
    (10_000, ("XXXX.", ".XXXX", "XXX.X", "X.XXX", "XX.XX")),        # four (one way to five)
    (3_000, ("..XXX.", ".XXX..", ".XX.X.", ".X.XX.")),              # open three
    (300, ("XXX..", "..XXX", "XX.X.", ".X.XX", "X.XX.", ".XX.X",
           "XX..X", "X..XX", "X.X.X")),                             # closed three
    (50, ("..XX..", ".X.X.", ".X..X.")),                            # open two
)

_TRANSLATE = {
    "black": str.maketrans({"b": "X", "w": "#"}),
    "white": str.maketrans({"w": "X", "b": "#"}),
}


def line_counts(s: str) -> List[int]:
    return [sum(s.count(p) for p in pats) for _, pats in PATTERNS]


def line_score(s: str) -> int:
    if s.count("X") < 2:
        return 0
    return sum(w * s.count(p) for w, pats in PATTERNS for p in pats)


def _build_lines(n: int) -> List[List[int]]:
    """Flat-index lists of every row, column and diagonal of length >= 5."""
    lines = []
    for i in range(n):
        lines.append([i * n + c for c in range(n)])
        lines.append([r * n + i for r in range(n)])
    for start in range(-(n - 5), n - 4):
        d1 = [r * n + (r + start) for r in range(n) if 0 <= r + start < n]
        d2 = [r * n + (n - 1 - r - start) for r in range(n) if 0 <= n - 1 - r - start < n]
        lines.extend([d1, d2])
    return [ln for ln in lines if len(ln) >= 5]


_LINES: Dict[int, List[List[int]]] = {}


def lines_for(n: int) -> List[List[int]]:
    if n not in _LINES:
        _LINES[n] = _build_lines(n)
    return _LINES[n]


LINES = lines_for(BOARD_SIZE)


def _board_lines(state: State) -> List[str]:
    flat = ["." if v is None else v[0] for row in state for v in row]
    out = []
    for ln in lines_for(len(state)):
        s = "".join(flat[i] for i in ln)
        if "b" in s or "w" in s:
            out.append("#" + s + "#")
    return out


def pattern_counts(state: State, color: str) -> List[int]:
    """How many of each pattern category ``color`` has on the board."""
    tr = _TRANSLATE[color]
    totals = [0] * len(PATTERNS)
    for s in _board_lines(state):
        t = s.translate(tr)
        if t.count("X") < 2:
            continue
        for i, v in enumerate(line_counts(t)):
            totals[i] += v
    return totals


def evaluate(state: State, color: str, to_move: Optional[str] = None) -> int:
    """Static evaluation of ``state`` from ``color``'s point of view.

    Positive means good for ``color``. When ``to_move`` is given, simple
    tactical facts are applied (e.g. the side to move with a four wins).
    """
    lines = _board_lines(state)
    counts = {}
    scores = {}
    for col in ("black", "white"):
        tr = _TRANSLATE[col]
        tot = [0] * len(PATTERNS)
        for s in lines:
            t = s.translate(tr)
            if t.count("X") < 2:
                continue  # a single stone forms no pattern
            for i, v in enumerate(line_counts(t)):
                tot[i] += v
        counts[col] = tot
        scores[col] = sum(PATTERNS[i][0] * tot[i] for i in range(len(PATTERNS)))

    me, opp = counts[color], counts[other(color)]
    if me[FIVE]:
        return WIN_SCORE
    if opp[FIVE]:
        return -WIN_SCORE

    if to_move is not None:
        sign = 1 if to_move == color else -1
        stm, waiting = counts[to_move], counts[other(to_move)]
        if stm[OPEN_FOUR] or stm[FOUR]:
            return sign * (WIN_SCORE // 2)          # completes five next move
        if waiting[OPEN_FOUR]:
            return -sign * (WIN_SCORE // 2)         # cannot block both ends
        if stm[OPEN_THREE] and not waiting[FOUR]:
            return sign * (WIN_SCORE // 4)          # open three -> open four

    return scores[color] - scores[other(color)]


def _segment(state: State, row: int, col: int, dr: int, dc: int, reach: int = 5) -> str:
    n = len(state)
    chars = []
    for k in range(-reach, reach + 1):
        r, c = row + k * dr, col + k * dc
        if 0 <= r < n and 0 <= c < n:
            v = state[r][c]
            chars.append("." if v is None else v[0])
        else:
            chars.append("#")
    return "".join(chars)


def local_threats(state: State, row: int, col: int, color: str) -> List[int]:
    """Pattern categories that playing ``color`` at (row, col) would create."""
    tr = _TRANSLATE[color]
    gained = [0] * len(PATTERNS)
    for dr, dc in DIRECTIONS:
        before = _segment(state, row, col, dr, dc).translate(tr)
        after = before[:5] + "X" + before[6:]
        b, a = line_counts(before), line_counts(after)
        for i in range(len(PATTERNS)):
            gained[i] += max(0, a[i] - b[i])
    return gained


def move_score(state: State, row: int, col: int, color: str) -> int:
    """Local value of a move = attack value + defensive (blocking) value.

    Used for move ordering and by the rule-based agent; it only looks at the
    four lines through the cell, so it is much cheaper than ``evaluate``.
    """
    total = 0
    for col_, weight in ((color, 1.0), (other(color), 0.9)):
        tr = _TRANSLATE[col_]
        for dr, dc in DIRECTIONS:
            before = _segment(state, row, col, dr, dc).translate(tr)
            after = before[:5] + "X" + before[6:]
            total += weight * (line_score(after) - line_score(before))
    # small preference for the centre breaks ties sensibly
    n = len(state)
    total += 3 * (n - abs(row - n // 2) - abs(col - n // 2))
    return int(total)


def generate_moves(state: State, color: str, limit: Optional[int] = None,
                   ordered: bool = True) -> List[Move]:
    """Candidate moves for ``color``, strongest first.

    * an immediate win is returned alone,
    * if the opponent threatens five, only the blocking cells are returned,
    * otherwise candidates are ranked by ``move_score`` and cut to ``limit``.
    With ``ordered=False`` the same set is returned in board order, which is
    used to measure how much move ordering helps alpha-beta.
    """
    cands = candidate_cells(state)
    if not cands:
        return []
    for m in cands:
        if makes_five(state, m[0], m[1], color):
            return [m]
    blocks = [m for m in cands if makes_five(state, m[0], m[1], other(color))]
    if blocks:
        return blocks
    scored = sorted(cands, key=lambda m: move_score(state, m[0], m[1], color), reverse=True)
    if limit:
        scored = scored[:limit]
    if not ordered:
        scored.sort()
    return scored


def describe_move(state: State, row: int, col: int, color: str) -> str:
    """Plain-English reason for a move (state must not contain it yet)."""
    if makes_five(state, row, col, color):
        return "Completes five in a row"
    if makes_five(state, row, col, other(color)):
        return "Blocks opponent's five"
    mine = local_threats(state, row, col, color)
    theirs = local_threats(state, row, col, other(color))
    if mine[OPEN_FOUR]:
        return "Creates an open four (unstoppable)"
    if mine[FOUR] + mine[OPEN_FOUR] >= 2 or (mine[FOUR] and mine[OPEN_THREE]):
        return "Creates a double threat (fork)"
    if theirs[OPEN_FOUR]:
        return "Blocks opponent's open three"
    if mine[OPEN_THREE] >= 2:
        return "Creates a double open three (fork)"
    if mine[FOUR]:
        return "Creates a four (forcing move)"
    if theirs[FOUR] and theirs[OPEN_THREE]:
        return "Prevents an opponent fork"
    if mine[OPEN_THREE]:
        return "Creates an open three"
    if theirs[OPEN_THREE] or theirs[FOUR]:
        return "Restricts opponent's development"
    if mine[TWO] or mine[THREE]:
        return "Builds own shape"
    return "Positional / board control"


# ============================================================================
# 4. Agents
# ============================================================================

@dataclass
class SearchStats:
    """What an agent did while choosing its last move."""
    agent: str = ""
    nodes: int = 0            # game states visited
    evaluations: int = 0      # heuristic evaluations at the leaves
    cutoffs: int = 0          # alpha-beta prunes
    tt_hits: int = 0          # transposition table hits
    depth: int = 0            # search depth reached
    time_ms: float = 0.0
    score: int = 0
    reason: str = ""

    def to_dict(self) -> Dict:
        return asdict(self)

    def summary(self) -> str:
        parts = [self.agent]
        if self.depth:
            parts.append(f"depth {self.depth}")
        if self.nodes:
            parts.append(f"{self.nodes:,} states")
        if self.cutoffs:
            parts.append(f"{self.cutoffs:,} prunes")
        parts.append(f"{self.time_ms:.0f} ms")
        return " | ".join(parts)


class Agent:
    name = "Agent"
    # How the agent fits the AI theory in the synopsis (section 5)
    agent_type = ""      # simple reflex / goal-based / utility-based
    search = ""          # uninformed or informed
    knowledge = ""       # what domain knowledge it uses

    def __init__(self) -> None:
        self.stats = SearchStats(agent=self.name)

    def choose_move(self, state: State, color: str) -> Optional[Move]:
        self.stats = SearchStats(agent=self.name)
        start = time.perf_counter()
        board = [row[:] for row in state]  # never mutate the caller's board
        move = self._choose(board, color)
        self.stats.time_ms = (time.perf_counter() - start) * 1000
        if move is not None and not self.stats.reason:
            self.stats.reason = describe_move(state, move[0], move[1], color)
        return move

    def _choose(self, state: State, color: str) -> Optional[Move]:
        raise NotImplementedError

    def __repr__(self) -> str:
        return self.name


class RandomAgent(Agent):
    """Uninformed baseline: any legal move, with no evaluation at all."""
    name = "Random"
    agent_type = "Simple reflex agent (no goal reasoning)"
    search = "Uninformed - no search at all"
    knowledge = "None: any legal move is equally good"

    def __init__(self, seed: Optional[int] = None) -> None:
        super().__init__()
        self.rng = random.Random(seed)

    def _choose(self, state, color):
        moves = legal_moves(state)
        self.stats.nodes = len(moves)
        self.stats.reason = "Random legal move"
        return self.rng.choice(moves) if moves else None


class RuleBasedAgent(Agent):
    """Goal-based agent following fixed tactical rules in priority order.

    1. Win now           2. Block opponent's five
    3. Make open four    4. Make a fork (double threat)
    5. Block opponent's open three / fork
    6. Otherwise play the cell with the best attack + defence value
    """
    name = "Rule-Based"
    agent_type = "Goal-based agent (condition-action rules)"
    search = "Informed, 1 move ahead (no tree search)"
    knowledge = "Tactical rules: win, block, forks, open threes"

    def __init__(self, seed: Optional[int] = None) -> None:
        super().__init__()
        self.rng = random.Random(seed)

    def _choose(self, state, color):
        opp = other(color)
        cands = candidate_cells(state)
        self.stats.nodes = len(cands)
        if not cands:
            return None

        def first(pred, reason):
            hits = [m for m in cands if pred(m)]
            if hits:
                self.stats.reason = reason
                return max(hits, key=lambda m: move_score(state, m[0], m[1], color))
            return None

        mine = {m: local_threats(state, m[0], m[1], color) for m in cands}
        theirs = {m: local_threats(state, m[0], m[1], opp) for m in cands}
        rules = (
            (lambda m: makes_five(state, m[0], m[1], color), "Rule 1: win immediately"),
            (lambda m: makes_five(state, m[0], m[1], opp), "Rule 2: block opponent's five"),
            (lambda m: mine[m][OPEN_FOUR] > 0, "Rule 3: create an open four"),
            (lambda m: mine[m][FOUR] >= 2 or (mine[m][FOUR] and mine[m][OPEN_THREE]),
             "Rule 4: create a four-three fork"),
            (lambda m: theirs[m][OPEN_FOUR] > 0, "Rule 5: block opponent's open three"),
            (lambda m: mine[m][OPEN_THREE] >= 2, "Rule 4: create a double three"),
            (lambda m: theirs[m][FOUR] and theirs[m][OPEN_THREE], "Rule 5: stop opponent fork"),
        )
        for pred, reason in rules:
            move = first(pred, reason)
            if move is not None:
                return move

        scored = sorted(cands, key=lambda m: move_score(state, m[0], m[1], color), reverse=True)
        best = move_score(state, scored[0][0], scored[0][1], color)
        top = [m for m in scored[:4] if move_score(state, m[0], m[1], color) >= best * 0.9]
        self.stats.reason = "Rule 6: best attack + defence value"
        return self.rng.choice(top)


class MinimaxAgent(Agent):
    """Textbook minimax over the candidate moves - no pruning.

    Explores every branch to ``depth`` plies, so the number of states grows
    as b^d. It is kept to show what alpha-beta saves.
    """
    name = "Minimax"
    agent_type = "Utility-based agent"
    search = "Informed adversarial search (heuristic at the leaves), no pruning"
    knowledge = "Pattern heuristic + candidate move generation"

    def __init__(self, depth: int = 2, max_candidates: int = 10) -> None:
        super().__init__()
        self.depth = depth
        self.max_candidates = max_candidates

    def _moves(self, state, color):
        return generate_moves(state, color, self.max_candidates)

    def _leaf(self, state, to_move):
        self.stats.evaluations += 1
        return evaluate(state, self.me, to_move)

    def _choose(self, state, color):
        self.me = color
        self.stats.depth = self.depth
        best_move, best_val = None, -float("inf")
        for r, c in self._moves(state, color):
            state[r][c] = color
            self.stats.nodes += 1
            if is_five(state, r, c, color):
                val = WIN_SCORE + self.depth
            else:
                val = self._minimax(state, self.depth - 1, False)
            state[r][c] = None
            if val > best_val:
                best_val, best_move = val, (r, c)
        self.stats.score = int(best_val) if best_move else 0
        return best_move

    def _minimax(self, state, depth, maximizing):
        to_move = self.me if maximizing else other(self.me)
        if depth == 0:
            return self._leaf(state, to_move)
        moves = self._moves(state, to_move)
        if not moves:
            return 0  # draw
        values = []
        for r, c in moves:
            state[r][c] = to_move
            self.stats.nodes += 1
            if is_five(state, r, c, to_move):
                v = (WIN_SCORE + depth) * (1 if maximizing else -1)
            else:
                v = self._minimax(state, depth - 1, not maximizing)
            state[r][c] = None
            values.append(v)
        return max(values) if maximizing else min(values)


class BlindMinimaxAgent(Agent):
    """Unguided minimax - the *uninformed* adversarial search of synopsis 5.3.

    It searches every legal move (no candidate generation, no ordering) and
    only knows win / loss / draw: every non-final position is worth 0. So it
    sees an immediate win or a loss one move away, but has no idea which of
    the other moves are good. A node limit keeps it from running forever on
    large boards, which is exactly the point it demonstrates: without domain
    knowledge the state space is too big to search.
    """
    name = "Blind Minimax"
    agent_type = "Goal-based agent (only knows the goal: five in a row)"
    search = "Uninformed adversarial search (win/loss/draw only)"
    knowledge = "None beyond the rules"

    def __init__(self, depth: int = 2, node_limit: int = 300_000, seed: Optional[int] = None) -> None:
        super().__init__()
        self.depth = depth
        self.node_limit = node_limit
        self.rng = random.Random(seed)

    def _choose(self, state, color):
        self.me = color
        self.stats.depth = self.depth
        moves = legal_moves(state)
        if not moves:
            return None
        best_val, best = -float("inf"), []
        for r, c in moves:
            state[r][c] = color
            self.stats.nodes += 1
            if is_five(state, r, c, color):
                val = WIN_SCORE + self.depth
            else:
                val = self._minimax(state, self.depth - 1, False)
            state[r][c] = None
            if val > best_val:
                best_val, best = val, [(r, c)]
            elif val == best_val:
                best.append((r, c))
        self.stats.score = int(best_val)
        if self.stats.nodes >= self.node_limit:
            self.stats.reason = "Ran out of search budget: the board is too big to search blindly"
        elif best_val == 0:
            self.stats.reason = "Sees no win or loss within reach, so every move looks the same"
        # all equally valued moves are indistinguishable to a blind search
        return self.rng.choice(best)

    def _minimax(self, state, depth, maximizing):
        if depth == 0 or self.stats.nodes >= self.node_limit:
            self.stats.evaluations += 1
            return 0  # no heuristic: an unfinished game is worth nothing to either side
        to_move = self.me if maximizing else other(self.me)
        moves = legal_moves(state)
        if not moves:
            return 0
        best = -float("inf") if maximizing else float("inf")
        for r, c in moves:
            state[r][c] = to_move
            self.stats.nodes += 1
            if is_five(state, r, c, to_move):
                v = (WIN_SCORE + depth) * (1 if maximizing else -1)
            else:
                v = self._minimax(state, depth - 1, not maximizing)
            state[r][c] = None
            best = max(best, v) if maximizing else min(best, v)
        return best


class AlphaBetaAgent(MinimaxAgent):
    """Minimax with alpha-beta pruning.

    Returns exactly the same value as ``MinimaxAgent`` at the same depth but
    skips branches that cannot change the decision. With ``ordered=True``
    (default) strong moves are searched first, which makes pruning far more
    effective.
    """
    name = "Alpha-Beta"
    agent_type = "Utility-based agent"
    search = "Informed adversarial search with alpha-beta pruning"
    knowledge = "Pattern heuristic + move ordering + candidate generation"

    def __init__(self, depth: int = 3, max_candidates: int = 12, ordered: bool = True) -> None:
        super().__init__(depth, max_candidates)
        self.ordered = ordered
        if not ordered:
            self.name = "Alpha-Beta (unordered)"

    def _moves(self, state, color):
        return generate_moves(state, color, self.max_candidates, ordered=self.ordered)

    def _choose(self, state, color):
        self.me = color
        self.stats.depth = self.depth
        alpha, beta = -float("inf"), float("inf")
        best_move = None
        for r, c in self._moves(state, color):
            state[r][c] = color
            self.stats.nodes += 1
            if is_five(state, r, c, color):
                val = WIN_SCORE + self.depth
            else:
                val = self._alphabeta(state, self.depth - 1, alpha, beta, False)
            state[r][c] = None
            if val > alpha or best_move is None:
                alpha, best_move = max(alpha, val), (r, c)
        self.stats.score = int(alpha) if best_move else 0
        return best_move

    def _alphabeta(self, state, depth, alpha, beta, maximizing):
        to_move = self.me if maximizing else other(self.me)
        if depth == 0:
            return self._leaf(state, to_move)
        moves = self._moves(state, to_move)
        if not moves:
            return 0
        value = -float("inf") if maximizing else float("inf")
        for r, c in moves:
            state[r][c] = to_move
            self.stats.nodes += 1
            if is_five(state, r, c, to_move):
                v = (WIN_SCORE + depth) * (1 if maximizing else -1)
            else:
                v = self._alphabeta(state, depth - 1, alpha, beta, not maximizing)
            state[r][c] = None
            if maximizing:
                value = max(value, v)
                alpha = max(alpha, value)
            else:
                value = min(value, v)
                beta = min(beta, value)
            if alpha >= beta:
                self.stats.cutoffs += 1
                break
        return value


class _Timeout(Exception):
    pass


_EXACT, _LOWER, _UPPER = 0, 1, 2


class ExpertAgent(Agent):
    """Advanced agent: negamax alpha-beta with iterative deepening and a
    Zobrist-hashed transposition table, under a per-move time budget.

    * Iterative deepening searches depth 1, 2, 3 ... until time runs out, so
      a good move is always ready and the best move of the previous
      iteration is searched first (great move ordering).
    * The transposition table remembers positions already evaluated, since
      in Gomoku the same position is reached by many move orders.
    """
    name = "Expert"
    agent_type = "Utility-based agent"
    search = "Informed: iterative deepening alpha-beta + transposition table"
    knowledge = "Pattern heuristic + memory of evaluated positions"

    def __init__(self, max_depth: int = 8, time_limit: float = 2.0, max_candidates: int = 10,
                 seed: int = 2024) -> None:
        super().__init__()
        self.max_depth = max_depth
        self.time_limit = time_limit
        self.max_candidates = max_candidates
        rng = random.Random(seed)
        self.zobrist = {
            (r, c, col): rng.getrandbits(64)
            for r in range(MAX_BOARD) for c in range(MAX_BOARD) for col in ("black", "white")
        }
        self.table: Dict[int, Tuple[int, int, int, Optional[Move]]] = {}

    def _hash(self, state):
        h = len(state)  # boards of different sizes never share a hash
        for r in range(len(state)):
            for c in range(len(state)):
                if state[r][c] is not None:
                    h ^= self.zobrist[(r, c, state[r][c])]
        return h

    def _choose(self, state, color):
        self.deadline = time.perf_counter() + self.time_limit
        if len(self.table) > 200_000:
            self.table.clear()
        root_moves = generate_moves(state, color, self.max_candidates)
        if len(root_moves) == 1:
            self.stats.depth = 1
            return root_moves[0]
        h = self._hash(state)
        best_move = root_moves[0] if root_moves else None
        for depth in range(1, self.max_depth + 1):
            try:
                val, move = self._root(state, color, depth, h, root_moves, best_move)
            except _Timeout:
                break
            best_move = move
            self.stats.depth, self.stats.score = depth, val
            if abs(val) >= WIN_SCORE // 2:
                break  # forced result found, deeper search is pointless
        return best_move

    def _root(self, state, color, depth, h, moves, pv):
        if pv in moves:
            moves = [pv] + [m for m in moves if m != pv]
        alpha, beta = -float("inf"), float("inf")
        best_move = moves[0]
        for r, c in moves:
            state[r][c] = color
            self.stats.nodes += 1
            if is_five(state, r, c, color):
                val = WIN_SCORE + depth
            else:
                val = -self._negamax(state, other(color), depth - 1, -beta, -alpha,
                                     h ^ self.zobrist[(r, c, color)])
            state[r][c] = None
            if val > alpha:
                alpha, best_move = val, (r, c)
        return int(alpha), best_move

    def _negamax(self, state, color, depth, alpha, beta, h):
        if self.stats.nodes & 255 == 0 and time.perf_counter() > self.deadline:
            raise _Timeout
        alpha0 = alpha
        entry = self.table.get(h)
        tt_move = None
        if entry is not None:
            e_depth, e_val, e_flag, tt_move = entry
            if e_depth >= depth:
                self.stats.tt_hits += 1
                if e_flag == _EXACT:
                    return e_val
                if e_flag == _LOWER:
                    alpha = max(alpha, e_val)
                elif e_flag == _UPPER:
                    beta = min(beta, e_val)
                if alpha >= beta:
                    return e_val
        if depth == 0:
            self.stats.evaluations += 1
            return evaluate(state, color, color)
        moves = generate_moves(state, color, self.max_candidates)
        if not moves:
            return 0
        if tt_move in moves:
            moves.remove(tt_move)
            moves.insert(0, tt_move)
        best, best_move = -float("inf"), moves[0]
        for r, c in moves:
            state[r][c] = color
            self.stats.nodes += 1
            if is_five(state, r, c, color):
                v = WIN_SCORE + depth
            else:
                v = -self._negamax(state, other(color), depth - 1, -beta, -alpha,
                                   h ^ self.zobrist[(r, c, color)])
            state[r][c] = None
            if v > best:
                best, best_move = v, (r, c)
            alpha = max(alpha, v)
            if alpha >= beta:
                self.stats.cutoffs += 1
                break
        flag = _UPPER if best <= alpha0 else (_LOWER if best >= beta else _EXACT)
        self.table[h] = (depth, int(best), flag, best_move)
        return best


# ============================================================================
# 5. Difficulty presets used by the GUI and the benchmark
# ============================================================================

DIFFICULTIES = {
    "Easy": "Random AI - uninformed baseline",
    "Medium": "Rule-Based AI - tactical rules, 1-ply",
    "Hard": "Minimax + Alpha-Beta, depth 3",
    "Expert": "Iterative deepening + transposition table",
}


def make_agent(name: str) -> Agent:
    """Create an agent from a difficulty or algorithm name."""
    key = name.split()[0].strip().lower()
    factories = {
        "easy": RandomAgent,
        "random": RandomAgent,
        "medium": RuleBasedAgent,
        "rule-based": RuleBasedAgent,
        "minimax": lambda: MinimaxAgent(depth=2, max_candidates=10),
        "blind": lambda: BlindMinimaxAgent(depth=2),
        "hard": lambda: AlphaBetaAgent(depth=3, max_candidates=12),
        "alpha-beta": lambda: AlphaBetaAgent(depth=3, max_candidates=12),
        "expert": lambda: ExpertAgent(max_depth=8, time_limit=2.0),
    }
    if key not in factories:
        raise ValueError(f"Unknown agent '{name}'. Choose from: {', '.join(factories)}")
    return factories[key]()
