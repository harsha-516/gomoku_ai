# AI algorithms for Gomoku (logic-only, no UI dependencies)

from typing import List, Optional, Tuple

State = List[List[Optional[str]]]

BOARD_SIZE = 15
CENTER = 7

# ------------ Helpers -------------

def get_empty_cells(state: State) -> list[tuple[int, int]]:
    return [
        (r, c)
        for r in range(BOARD_SIZE)
        for c in range(BOARD_SIZE)
        if state[r][c] is None
    ]


def neighbors_exist(state: State, r: int, c: int, dist: int = 2) -> bool:
    for dr in range(-dist, dist + 1):
        for dc in range(-dist, dist + 1):
            if dr == 0 and dc == 0:
                continue
            rr, cc = r + dr, c + dc
            if 0 <= rr < BOARD_SIZE and 0 <= cc < BOARD_SIZE and state[rr][cc] is not None:
                return True
    return False


def candidate_moves(state: State) -> list[tuple[int, int]]:
    empties = get_empty_cells(state)
    any_stone = any(state[r][c] is not None for r in range(BOARD_SIZE) for c in range(BOARD_SIZE))
    if not any_stone:
        return [(CENTER, CENTER)]
    cand = [(r, c) for (r, c) in empties if neighbors_exist(state, r, c, dist=2)]
    return cand if cand else empties


def is_win_at(state: State, row: int, col: int, color: str) -> bool:
    directions = [(0, 1), (1, 0), (1, 1), (1, -1)]
    for dx, dy in directions:
        cnt = 1
        r, c = row + dx, col + dy
        while 0 <= r < BOARD_SIZE and 0 <= c < BOARD_SIZE and state[r][c] == color:
            cnt += 1
            r += dx
            c += dy
        r, c = row - dx, col - dy
        while 0 <= r < BOARD_SIZE and 0 <= c < BOARD_SIZE and state[r][c] == color:
            cnt += 1
            r -= dx
            c -= dy
        if cnt >= 5:
            return True
    return False


def try_move_is_win(state: State, r: int, c: int, color: str) -> bool:
    state[r][c] = color
    win = is_win_at(state, r, c, color)
    state[r][c] = None
    return win


def count_threat_level(state: State, row: int, col: int, color: str) -> int:
    """
    Count the threat level if a stone is placed at (row, col).
    Returns the maximum consecutive stones + 1 (for the new stone) in any direction.
    """
    if state[row][col] is not None:
        return 0
    
    directions = [(0, 1), (1, 0), (1, 1), (1, -1)]
    max_count = 0
    
    for dx, dy in directions:
        cnt = 1  # Count the stone we're placing
        # Count forward
        r, c = row + dx, col + dy
        while 0 <= r < BOARD_SIZE and 0 <= c < BOARD_SIZE and state[r][c] == color:
            cnt += 1
            r += dx
            c += dy
        # Count backward
        r, c = row - dx, col - dy
        while 0 <= r < BOARD_SIZE and 0 <= c < BOARD_SIZE and state[r][c] == color:
            cnt += 1
            r -= dx
            c -= dy
        
        max_count = max(max_count, cnt)
    
    return max_count


def is_open_threat(state: State, row: int, col: int, color: str, min_count: int = 3) -> bool:
    """
    Check if placing a stone at (row, col) creates an open threat (min_count in a row with at least one open end).
    An open threat is dangerous because it can lead to a win.
    """
    if state[row][col] is not None:
        return False
    
    directions = [(0, 1), (1, 0), (1, 1), (1, -1)]
    
    for dx, dy in directions:
        cnt = 1  # Count the stone we're placing
        left_open = False
        right_open = False
        
        # Count forward and check if end is open
        r, c = row + dx, col + dy
        while 0 <= r < BOARD_SIZE and 0 <= c < BOARD_SIZE and state[r][c] == color:
            cnt += 1
            r += dx
            c += dy
        # Check if forward end is open (empty space)
        if 0 <= r < BOARD_SIZE and 0 <= c < BOARD_SIZE and state[r][c] is None:
            right_open = True
        
        # Count backward and check if end is open
        r, c = row - dx, col - dy
        while 0 <= r < BOARD_SIZE and 0 <= c < BOARD_SIZE and state[r][c] == color:
            cnt += 1
            r -= dx
            c -= dy
        # Check if backward end is open (empty space)
        if 0 <= r < BOARD_SIZE and 0 <= c < BOARD_SIZE and state[r][c] is None:
            left_open = True
        
        # If we have min_count or more with at least one open end, it's a threat
        if cnt >= min_count and (left_open or right_open):
            return True
    
    return False

# ------------ Heuristic evaluation -------------

def evaluate(state: State, perspective_color: str) -> int:
    opp = "white" if perspective_color == "black" else "black"
    return score_color(state, perspective_color) - score_color(state, opp)


def score_color(state: State, color: str) -> int:
    lines: list[list[Optional[str]]] = []
    n = BOARD_SIZE
    # rows and cols
    for r in range(n):
        lines.append([state[r][c] for c in range(n)])
    for c in range(n):
        lines.append([state[r][c] for r in range(n)])
    # diagonals
    for d in range(-(n - 5), (n - 4)):
        diag1 = []
        diag2 = []
        for r in range(n):
            c1 = r + d
            c2 = (n - 1) - r - d
            if 0 <= c1 < n:
                diag1.append(state[r][c1])
            if 0 <= c2 < n:
                diag2.append(state[r][c2])
        if len(diag1) >= 5:
            lines.append(diag1)
        if len(diag2) >= 5:
            lines.append(diag2)

    score = 0
    W_FIVE = 100000
    W_OPEN_FOUR = 10000
    W_CLOSED_FOUR = 3000
    W_OPEN_THREE = 1000
    W_CLOSED_THREE = 200
    W_OPEN_TWO = 50

    def seq_score(seq: list[Optional[str]]) -> int:
        s = 0
        n = len(seq)
        stones = [1 if v == color else (0 if v is None else -1) for v in seq]
        for i in range(n - 4):
            window = stones[i : i + 5]
            my_cnt = window.count(1)
            opp_cnt = window.count(-1)
            empty_cnt = window.count(0)
            if opp_cnt == 0:
                if my_cnt == 5:
                    s += W_FIVE
                elif my_cnt == 4 and empty_cnt == 1:
                    left_open = i > 0 and seq[i - 1] is None
                    right_open = i + 5 < n and seq[i + 5] is None
                    s += W_OPEN_FOUR if (left_open or right_open) else W_CLOSED_FOUR
                elif my_cnt == 3 and empty_cnt == 2:
                    left_open = i > 0 and seq[i - 1] is None
                    right_open = i + 5 < n and seq[i + 5] is None
                    s += W_OPEN_THREE if (left_open and right_open) else W_CLOSED_THREE
                elif my_cnt == 2 and empty_cnt == 3:
                    if (i > 0 and seq[i - 1] is None) or (i + 5 < n and seq[i + 5] is None):
                        s += W_OPEN_TWO
        return s

    for ln in lines:
        score += seq_score(ln)
    return score

# ------------ Move ordering and search -------------

def ordered_candidates(state: State, ai_color: str) -> list[tuple[int, int]]:
    wins: list[tuple[int, int]] = []
    blocks: list[tuple[int, int]] = []
    defensive: list[tuple[int, int]] = []  # Blocks against 3-in-a-row threats
    rest: list[tuple[int, int]] = []
    opp = "white" if ai_color == "black" else "black"
    
    for r, c in candidate_moves(state):
        if try_move_is_win(state, r, c, ai_color):
            wins.append((r, c))
        elif try_move_is_win(state, r, c, opp):
            blocks.append((r, c))
        elif is_open_threat(state, r, c, opp, min_count=3):
            # Opponent can create a dangerous 3+ in a row here
            defensive.append((r, c))
        else:
            rest.append((r, c))
    
    return wins + blocks + defensive + rest


def minimax(state: State, depth: int, maximizing: bool, ai_color: str, opp_color: str, alpha: int, beta: int, use_ab: bool, max_candidates: int | None = None) -> int:
    cand = candidate_moves(state)
    if depth == 0 or not cand:
        return evaluate(state, ai_color)

    if maximizing:
        value = -10**9
        oc = ordered_candidates(state, ai_color)
        if max_candidates is not None:
            opp = opp_color
            wins = [m for m in oc if try_move_is_win(state, m[0], m[1], ai_color)]
            blocks = [m for m in oc if m not in wins and try_move_is_win(state, m[0], m[1], opp)]
            defensive = [m for m in oc if m not in wins and m not in blocks and is_open_threat(state, m[0], m[1], opp, min_count=3)]
            rest = [m for m in oc if m not in wins and m not in blocks and m not in defensive]
            remaining_slots = max(0, max_candidates - len(wins) - len(blocks) - len(defensive))
            oc = wins + blocks + defensive + rest[:remaining_slots]
        for r, c in oc:
            state[r][c] = ai_color
            if is_win_at(state, r, c, ai_color):
                evalv = 100000
            else:
                evalv = minimax(state, depth - 1, False, ai_color, opp_color, alpha, beta, use_ab, max_candidates)
            state[r][c] = None
            if evalv > value:
                value = evalv
            if use_ab:
                if value > alpha:
                    alpha = value
                if alpha >= beta:
                    break
        return value
    else:
        value = 10**9
        oc = ordered_candidates(state, opp_color)
        if max_candidates is not None:
            wins = [m for m in oc if try_move_is_win(state, m[0], m[1], opp_color)]
            blocks = [m for m in oc if m not in wins and try_move_is_win(state, m[0], m[1], ai_color)]
            defensive = [m for m in oc if m not in wins and m not in blocks and is_open_threat(state, m[0], m[1], ai_color, min_count=3)]
            rest = [m for m in oc if m not in wins and m not in blocks and m not in defensive]
            remaining_slots = max(0, max_candidates - len(wins) - len(blocks) - len(defensive))
            oc = wins + blocks + defensive + rest[:remaining_slots]
        for r, c in oc:
            state[r][c] = opp_color
            if is_win_at(state, r, c, opp_color):
                evalv = -100000
            else:
                evalv = minimax(state, depth - 1, True, ai_color, opp_color, alpha, beta, use_ab, max_candidates)
            state[r][c] = None
            if evalv < value:
                value = evalv
            if use_ab:
                if value < beta:
                    beta = value
                if alpha >= beta:
                    break
        return value


def ai_search(state: State, ai_color: str, opp_color: str, depth: int = 2, use_alpha_beta: bool = False, max_candidates: int | None = None) -> Optional[Tuple[int, int]]:
    best_move: Optional[Tuple[int, int]] = None
    best_score = -10**9
    alpha = -10**9
    beta = 10**9
    oc = ordered_candidates(state, ai_color)
    
    # Debug: Check for blocks and defensive moves in ordered candidates
    blocks_in_oc = [m for m in oc if try_move_is_win(state, m[0], m[1], opp_color)]
    defensive_in_oc = [m for m in oc if m not in blocks_in_oc and is_open_threat(state, m[0], m[1], opp_color, min_count=3)]
    if blocks_in_oc:
        print(f"[DEBUG] Found {len(blocks_in_oc)} blocking moves: {blocks_in_oc[:3]}")
    if defensive_in_oc:
        print(f"[DEBUG] Found {len(defensive_in_oc)} defensive moves (3+ threats): {defensive_in_oc[:3]}")
    
    # CRITICAL: Never prune wins, blocks, or defensive moves - only limit the "rest" candidates
    if max_candidates is not None:
        wins = [m for m in oc if try_move_is_win(state, m[0], m[1], ai_color)]
        blocks = [m for m in oc if m not in wins and try_move_is_win(state, m[0], m[1], opp_color)]
        defensive = [m for m in oc if m not in wins and m not in blocks and is_open_threat(state, m[0], m[1], opp_color, min_count=3)]
        rest = [m for m in oc if m not in wins and m not in blocks and m not in defensive]
        # Keep all wins, blocks, and defensive moves, but limit rest
        remaining_slots = max(0, max_candidates - len(wins) - len(blocks) - len(defensive))
        oc = wins + blocks + defensive + rest[:remaining_slots]
        print(f"[DEBUG] After pruning: {len(wins)} wins, {len(blocks)} blocks, {len(defensive)} defensive, {len(rest[:remaining_slots])} rest")
    
    for r, c in oc:
        state[r][c] = ai_color
        val = minimax(state, depth - 1, False, ai_color, opp_color, alpha, beta, use_alpha_beta, max_candidates)
        state[r][c] = None
        if val > best_score:
            best_score = val
            best_move = (r, c)
        if use_alpha_beta:
            if best_score > alpha:
                alpha = best_score
            if alpha >= beta:
                break
    
    # Debug: Show selected move
    is_block = best_move and try_move_is_win(state, best_move[0], best_move[1], opp_color)
    print(f"[DEBUG] Selected move: {best_move}, score: {best_score}, is_block: {is_block}")
    
    return best_move


def ai_easy(state: State, ai_color: str, opp_color: str) -> Optional[Tuple[int, int]]:
    # Win if possible
    for r, c in candidate_moves(state):
        if try_move_is_win(state, r, c, ai_color):
            return (r, c)
    # Block opponent immediate win
    for r, c in candidate_moves(state):
        if try_move_is_win(state, r, c, opp_color):
            return (r, c)
    # Random nearby
    import random
    cand = candidate_moves(state)
    return random.choice(cand) if cand else None


# ------------ Suggestions (ranked list) -------------
def suggest_moves(
    state: State,
    player_color: str,
    difficulty: str = "Medium",
    top_k: int = 6,
    max_candidates: Optional[int] = None,
) -> List[Tuple[int, int, int, str]]:
    """
    Return a ranked list of suggestions: (row, col, score, kind)
    kind in {win, block, search, score}
    - Easy: prioritize wins, then blocks, then heuristic-scored candidates
    - Medium: heuristic one-ply lookahead (place move, evaluate) with blocks prioritized
    - Hard: shallow minimax search per candidate with alpha-beta; blocks prioritized
    """
    opp = "white" if player_color == "black" else "black"

    # Immediate wins and blocks
    wins: List[Tuple[int, int, int, str]] = []
    blocks: List[Tuple[int, int, int, str]] = []
    others: List[Tuple[int, int, int, str]] = []

    # CRITICAL: Check ALL candidates for immediate wins, blocks, and defensive moves first
    # Do not prune before checking threats
    all_cand = candidate_moves(state)
    defensive: List[Tuple[int, int, int, str]] = []
    
    for r, c in all_cand:
        if try_move_is_win(state, r, c, player_color):
            wins.append((r, c, 10**9, "win"))
        elif try_move_is_win(state, r, c, opp):
            blocks.append((r, c, 10**8, "block"))
        elif is_open_threat(state, r, c, opp, min_count=3):
            # Defensive move against 3+ in a row threat
            threat_level = count_threat_level(state, r, c, opp)
            defensive.append((r, c, 10**7 + threat_level * 1000, "defensive"))
    
    # Now get ordered candidates for scoring
    # Keep wins/blocks/defensive separate, only prune "rest" candidates
    cand = ordered_candidates(state, player_color)
    if max_candidates is not None:
        # Extract wins, blocks, and defensive from ordered list
        cand_wins = [m for m in cand if try_move_is_win(state, m[0], m[1], player_color)]
        cand_blocks = [m for m in cand if m not in cand_wins and try_move_is_win(state, m[0], m[1], opp)]
        cand_defensive = [m for m in cand if m not in cand_wins and m not in cand_blocks and is_open_threat(state, m[0], m[1], opp, min_count=3)]
        cand_rest = [m for m in cand if m not in cand_wins and m not in cand_blocks and m not in cand_defensive]
        # Keep all wins/blocks/defensive, limit rest
        remaining_slots = max(0, max_candidates - len(cand_wins) - len(cand_blocks) - len(cand_defensive))
        cand = cand_wins + cand_blocks + cand_defensive + cand_rest[:remaining_slots]

    # If Easy, fill remaining by heuristic after placing the move
    if difficulty == "Easy":
        for r, c in cand:
            if any((r == rr and c == cc) for rr, cc, *_ in wins + blocks + defensive):
                continue
            state[r][c] = player_color
            s = evaluate(state, player_color)
            state[r][c] = None
            others.append((r, c, s, "score"))
        others.sort(key=lambda x: x[2], reverse=True)
        return (wins + blocks + defensive + others)[:top_k]

    # Medium: 1-ply evaluation minus opponent best reply (depth 1 adversarial)
    if difficulty == "Medium":
        for r, c in cand:
            if any((r == rr and c == cc) for rr, cc, *_ in wins + blocks + defensive):
                continue
            state[r][c] = player_color
            # Check if this creates a threat or defends
            my_eval = evaluate(state, player_color)
            # Check opponent's best counter-threat
            opp_best_threat = -10**9
            for r2, c2 in candidate_moves(state)[:10]:
                if try_move_is_win(state, r2, c2, opp):
                    opp_best_threat = 10**8
                    break
                state[r2][c2] = opp
                opp_eval = evaluate(state, opp)
                state[r2][c2] = None
                if opp_eval > opp_best_threat:
                    opp_best_threat = opp_eval
            state[r][c] = None
            # Penalize moves that allow strong opponent replies
            score = my_eval - opp_best_threat
            others.append((r, c, score, "score"))
        others.sort(key=lambda x: x[2], reverse=True)
        return (wins + blocks + defensive + others)[:top_k]

    # Hard: Use minimax per candidate with alpha-beta, shallow depth
    depth = 2
    alpha = -10**9
    beta = 10**9
    for r, c in cand:
        if any((r == rr and c == cc) for rr, cc, *_ in wins + blocks + defensive):
            continue
        state[r][c] = player_color
        if is_win_at(state, r, c, player_color):
            val = 100000
        else:
            val = minimax(state, depth - 1, False, player_color, opp, alpha, beta, True, max_candidates)
        state[r][c] = None
        others.append((r, c, val, "search"))
    others.sort(key=lambda x: x[2], reverse=True)
    return (wins + blocks + defensive + others)[:top_k]
