from __future__ import annotations

from typing import List, Optional, Tuple, Dict, Any

from suggestion_overlay import compute_suggestions

State = List[List[Optional[str]]]
MoveLogEntry = Dict[str, Any]


def _clone_empty_state(board_size: int = 15) -> State:
    return [[None for _ in range(board_size)] for _ in range(board_size)]


def _apply_move(state: State, row: int, col: int, color: str) -> None:
    state[row][col] = color


def _is_edge_move(row: int, col: int, board_size: int = 15, margin: int = 1) -> bool:
    return row < margin or col < margin or row >= board_size - margin or col >= board_size - margin


def _infer_move_facts(
    temp_state: State,
    mover: str,
    row: int,
    col: int,
    difficulty: str = "Hard",
) -> Dict[str, Any]:
    """Forward-chaining style: derive facts about a single move.

    Uses compute_suggestions to approximate "best" moves from the current position.
    """
    facts: Dict[str, Any] = {
        "mover": mover,
        "row": row,
        "col": col,
        "missed_win": False,
        "missed_block": False,
        "weak_edge": False,
        "low_value": False,
        "better_moves": [],  # list[(row, col, kind)]
        "played_kind": None,  # win / block / score / None
    }

    try:
        suggestions = compute_suggestions(temp_state, mover, top_k=6, difficulty=difficulty)
    except Exception:
        suggestions = []

    has_win = any(kind == "win" for _r, _c, _s, kind in suggestions)
    has_block = any(kind == "block" for _r, _c, _s, kind in suggestions)

    played_in_suggestions = None
    played_score_rank = None

    # Rule 1 / 2: detect missed wins or blocks; track better options
    for idx, (sr, sc, score, kind) in enumerate(suggestions):
        if sr == row and sc == col:
            played_in_suggestions = kind
            played_score_rank = idx
        if kind in ("win", "block"):
            facts["better_moves"].append((sr, sc, kind))

    if has_win and played_in_suggestions != "win":
        facts["missed_win"] = True

    if has_block and played_in_suggestions not in ("win", "block"):
        facts["missed_block"] = True

    # Rule 3: low-value move (ignored strong candidates and picked a low-ranked score/search move)
    if played_in_suggestions in ("score", "search") and played_score_rank is not None and played_score_rank >= 4:
        facts["low_value"] = True

    # Rule 4: weak edge placement (very close to the border with no tactical tag)
    if _is_edge_move(row, col) and played_in_suggestions is None:
        facts["weak_edge"] = True

    facts["played_kind"] = played_in_suggestions
    return facts


def analyze_game_rule_based(
    move_log: List[MoveLogEntry],
    final_state: Optional[State],
    perspective: str,
    winner: Optional[str],
    mode: str,
) -> Dict[str, Any]:
    """Run a simple forward-chaining expert analysis over the whole game.

    Returns a rich dict, which is then turned into a narrative.
    """
    board_size = 15
    temp_state = _clone_empty_state(board_size)

    mistake_events: List[Dict[str, Any]] = []
    good_events: List[Dict[str, Any]] = []

    for idx, m in enumerate(move_log):
        move_no = idx + 1
        mover = m.get("player") or m.get("player_color") or m.get("color")
        row = m["row"]
        col = m["col"]

        # Snapshot of the board before move: infer facts
        facts = _infer_move_facts(temp_state, mover, row, col)
        facts["move_no"] = move_no

        # Forward chaining: combine primitive facts into higher-level labels
        labels: List[str] = []
        if facts["missed_win"]:
            labels.append("missed_win")
        if facts["missed_block"]:
            labels.append("missed_block")
        if facts["weak_edge"]:
            labels.append("weak_edge")
        if facts["low_value"]:
            labels.append("low_value")
        if facts.get("played_kind") in ("win", "block"):
            labels.append("strong_move")

        facts["labels"] = labels

        # Separate good / bad events from the perspective player
        if mover == perspective:
            if any(lbl in ("missed_win", "missed_block", "weak_edge", "low_value") for lbl in labels):
                mistake_events.append(facts)
            elif "strong_move" in labels:
                good_events.append(facts)

        _apply_move(temp_state, row, col, mover)

    return {
        "mode": mode,
        "winner": winner,
        "perspective": perspective,
        "total_moves": len(move_log),
        "mistake_events": mistake_events,
        "good_events": good_events,
    }


def build_story_summary(analysis: Dict[str, Any]) -> str:
    """Convert analysis facts into a short, coach-style story."""
    mode = analysis.get("mode", "single_player")
    winner = analysis.get("winner") or ""
    perspective = analysis.get("perspective", "black")
    moves = analysis.get("total_moves", 0)
    mistakes = analysis.get("mistake_events", [])
    good = analysis.get("good_events", [])

    missed_wins = sum(1 for e in mistakes if "missed_win" in e["labels"])
    missed_blocks = sum(1 for e in mistakes if "missed_block" in e["labels"])
    weak_edges = sum(1 for e in mistakes if "weak_edge" in e["labels"])
    low_values = sum(1 for e in mistakes if "low_value" in e["labels"])

    paragraphs: List[str] = []

    # 1. Narrative of the match flow
    opener_parts: List[str] = []
    if mode == "single_player":
        opener_parts.append("You played against the computer")
    else:
        opener_parts.append("You played a head-to-head match")

    opener_parts.append(f"as {perspective} in a game that lasted {moves} moves")

    if winner:
        if winner.lower() in ("you", "player", "player 1", "player 2", perspective):
            opener_parts.append("and you finished on top.")
        elif winner.lower() in ("computer", "ai"):
            opener_parts.append("and the computer took the final point.")
        else:
            opener_parts.append(f"and {winner} claimed the win.")
    else:
        opener_parts.append("and the game ended without a clear winner.")

    paragraphs.append(" ".join(opener_parts))

    if good:
        first_good = min(good, key=lambda e: e["move_no"])
        paragraphs.append(
            "You started by placing solid stones. Around move "
            f"{first_good['move_no']}, you found a strong attacking or defensive idea, "
            "showing good awareness of the board."
        )
    else:
        paragraphs.append(
            "The opening phase was cautious, with no immediately powerful attacks, "
            "which is fine while you are still getting comfortable with the board."
        )

    if mistakes:
        first_m = mistakes[0]
        last_m = mistakes[-1]
        paragraphs.append(
            "As the game heated up, a few key moments slipped by. The first big "
            f"chance came around move {first_m['move_no']}, and another important "
            f"turning point was near move {last_m['move_no']}."
        )
    else:
        paragraphs.append(
            "From there, your play stayed fairly consistent with what the AI "
            "considered strong options, with no major missed chances detected."
        )

    # 2. List of major mistakes (high-level, non-technical wording)
    mistake_lines: List[str] = []
    if missed_wins:
        mistake_lines.append(
            f"You missed {missed_wins} clear opportunity(ies) to win in one move."
        )
    if missed_blocks:
        mistake_lines.append(
            f"You overlooked {missed_blocks} critical block(s) where the opponent "
            "was threatening to break through."
        )
    if weak_edges:
        mistake_lines.append(
            f"There were {weak_edges} move(s) placed on the outer edge that "
            "didn't really connect to your main plan."
        )
    if low_values:
        mistake_lines.append(
            f"On about {low_values} move(s), you chose a quiet spot while stronger "
            "options were available nearby."
        )
    if not mistake_lines:
        mistake_lines.append(
            "No major strategic mistakes stood out – nice job keeping your moves "
            "aligned with the AI's ideas."
        )

    # 3. Personalized suggestions
    suggestion_lines: List[str] = []
    if missed_wins or missed_blocks:
        suggestion_lines.append(
            "Before you place a stone in tense positions, pause for a moment and "
            "scan along each line (horizontal, vertical, and diagonal) to see if "
            "either player is one move away from connecting five."
        )
    if weak_edges:
        suggestion_lines.append(
            "Try to build your stones around existing groups instead of drifting "
            "towards the very edge – groups that support each other grow into "
            "dangerous chains much faster."
        )
    if low_values:
        suggestion_lines.append(
            "When you are unsure, look for moves that both extend your own line "
            "and interfere with your opponent's ideas, rather than placing a stone "
            "in an isolated area."
        )
    if not suggestion_lines:
        suggestion_lines.append(
            "To keep improving, keep asking yourself: 'Does this move help a group "
            "I already have, or stop something my opponent wants?' If the answer is "
            "yes to either, you are usually on the right track."
        )

    # Build final text in requested format
    parts: List[str] = []
    parts.append("Match Story:\n" + "\n".join(paragraphs))
    parts.append("\nMajor Moments:\n- " + "\n- ".join(mistake_lines))
    parts.append("\nCoaching Tips:\n- " + "\n- ".join(suggestion_lines))

    return "\n\n".join(parts)


def summarize_gomoku_game(
    move_log: List[MoveLogEntry],
    final_state: Optional[State],
    perspective: str,
    winner: Optional[str],
    mode: str,
) -> str:
    """Public API: return a story-like coaching report for a finished game."""
    analysis = analyze_game_rule_based(
        move_log=move_log,
        final_state=final_state,
        perspective=perspective,
        winner=winner,
        mode=mode,
    )
    return build_story_summary(analysis)
