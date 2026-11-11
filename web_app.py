"""
web_app.py - Browser interface for Intelligent Gomoku.

The browser only draws the board and handles clicks; every AI decision is
made in Python by the agents in agents.py, through a small JSON API:

    POST /api/ai-move   {board, color, level}         -> move + search statistics
    POST /api/hint      {board, color}                -> up to 3 suggested moves
    POST /api/analyze   {moves, perspective}          -> post-game analysis
    POST /api/save      {mode, winner, moves, ...}    -> record the game as CSV
    GET  /api/opening   ?stones=2&size=15             -> random fair opening
    GET  /api/agents                                  -> what kind of agent each AI is
    POST /api/compare   {board, color}                -> run the search algorithms side by side
    POST /api/evaluate  {board}                       -> heuristic patterns and score

Boards may be any square size from 7x7 to 19x19 (15x15 is standard).

Run:  python web_app.py     then open http://127.0.0.1:8050
(set the PORT environment variable to use another port)
"""

from __future__ import annotations

import csv
import os
import random
from datetime import datetime

from flask import Flask, jsonify, request, send_from_directory

from agents import (
    BOARD_SIZE, CATEGORY_NAMES, MAX_BOARD, MIN_BOARD, PATTERNS, WIN_SCORE, AlphaBetaAgent,
    BlindMinimaxAgent, ExpertAgent, MinimaxAgent, RandomAgent, RuleBasedAgent, candidate_cells,
    describe_move, evaluate, generate_moves, is_five, legal_moves, make_agent, pattern_counts,
)
from game_analysis import analyze_game

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WEB_DIR = os.path.join(BASE_DIR, "web")
GAMES_DIR = os.path.join(BASE_DIR, "games", "web")
LEVELS = {"Easy", "Blind", "Medium", "Minimax", "Hard", "Expert"}

app = Flask(__name__, static_folder=WEB_DIR, static_url_path="")


class BadRequest(Exception):
    pass


@app.errorhandler(BadRequest)
def _bad_request(err):
    return jsonify({"error": str(err)}), 400


def _board(data):
    board = data.get("board")
    if (not isinstance(board, list) or not MIN_BOARD <= len(board) <= MAX_BOARD
            or any(not isinstance(row, list) or len(row) != len(board) for row in board)):
        raise BadRequest(f"board must be a square list between {MIN_BOARD}x{MIN_BOARD} and {MAX_BOARD}x{MAX_BOARD}")
    if any(v not in (None, "black", "white") for row in board for v in row):
        raise BadRequest("board cells must be null, 'black' or 'white'")
    return board


def _color(data, key="color"):
    color = data.get(key)
    if color not in ("black", "white"):
        raise BadRequest(f"{key} must be 'black' or 'white'")
    return color


def _size(data):
    size = data.get("size", BOARD_SIZE)
    if not isinstance(size, int) or not MIN_BOARD <= size <= MAX_BOARD:
        raise BadRequest(f"size must be between {MIN_BOARD} and {MAX_BOARD}")
    return size


def _moves(data):
    moves = data.get("moves")
    size = _size(data)
    if not isinstance(moves, list):
        raise BadRequest("moves must be a list")
    for m in moves:
        if (not isinstance(m, dict) or m.get("player") not in ("black", "white")
                or not all(isinstance(m.get(k), int) and 0 <= m[k] < size for k in ("row", "col"))):
            raise BadRequest("each move needs player, row and col")
    return moves


@app.get("/")
def index():
    return send_from_directory(WEB_DIR, "index.html")


@app.post("/api/ai-move")
def ai_move():
    data = request.get_json(silent=True) or {}
    board, color = _board(data), _color(data)
    level = data.get("level", "Medium")
    if level not in LEVELS:
        raise BadRequest(f"level must be one of {sorted(LEVELS)}")
    agent = make_agent(level)
    move = agent.choose_move(board, color)
    if move is None:
        return jsonify({"move": None, "stats": agent.stats.to_dict()})
    board[move[0]][move[1]] = color
    return jsonify({
        "move": list(move),
        "wins": is_five(board, move[0], move[1], color),
        "stats": agent.stats.to_dict(),
    })


@app.post("/api/hint")
def hint():
    data = request.get_json(silent=True) or {}
    board, color = _board(data), _color(data)
    best = AlphaBetaAgent(depth=2, max_candidates=10).choose_move(board, color)
    ranked = [best] if best else []
    ranked += [m for m in generate_moves(board, color, limit=6) if m != best]
    hints = [{"row": r, "col": c, "reason": describe_move(board, r, c, color)} for r, c in ranked[:3]]
    return jsonify({"hints": hints})


@app.post("/api/analyze")
def analyze():
    data = request.get_json(silent=True) or {}
    try:
        return jsonify(analyze_game(_moves(data), _color(data, "perspective"), _size(data)))
    except ValueError as e:
        raise BadRequest(str(e))


@app.get("/api/opening")
def opening():
    """A random, roughly balanced opening: stones alternate near the centre."""
    stones = max(0, min(6, request.args.get("stones", default=2, type=int)))
    size = request.args.get("size", default=BOARD_SIZE, type=int)
    if not MIN_BOARD <= size <= MAX_BOARD:
        raise BadRequest(f"size must be between {MIN_BOARD} and {MAX_BOARD}")
    rng = random.Random()
    c = size // 2
    cells = [(c + dr, c + dc) for dr in range(-2, 3) for dc in range(-2, 3)]
    rng.shuffle(cells)
    picked = [(c, c)] + [x for x in cells if x != (c, c)][: stones - 1] if stones else []
    return jsonify({"moves": [{"player": "black" if i % 2 == 0 else "white", "row": r, "col": col}
                              for i, (r, col) in enumerate(picked)]})


@app.post("/api/save")
def save():
    data = request.get_json(silent=True) or {}
    moves = _moves(data)
    size = _size(data)
    mode = "".join(ch for ch in str(data.get("mode", "web")) if ch.isalnum() or ch == "_")[:20] or "web"
    os.makedirs(GAMES_DIR, exist_ok=True)
    path = os.path.join(GAMES_DIR, f"game_web_{mode}_{datetime.now():%Y%m%d_%H%M%S_%f}.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["mode", "winner", "started_at", "black", "white", "board_size"])
        w.writerow([mode, data.get("winner", ""), data.get("started_at", ""),
                    data.get("black", ""), data.get("white", ""), size])
        w.writerow([])
        fields = ["move_no", "player", "row", "col", "elapsed_ms", "ai_engine", "ai_nodes", "ai_depth",
                  "ai_time_ms", "ai_reason", "board_state"]
        w.writerow(fields)
        board = ["."] * (size * size)
        for i, m in enumerate(moves, start=1):
            board[m["row"] * size + m["col"]] = m["player"][0]
            w.writerow([i, m["player"], m["row"], m["col"], m.get("elapsed_ms", ""), m.get("ai_engine", ""),
                        m.get("ai_nodes", ""), m.get("ai_depth", ""), m.get("ai_time_ms", ""),
                        m.get("ai_reason", ""), "".join(board)])
    return jsonify({"saved": os.path.basename(path)})


AGENT_CLASSES = {
    "Easy": RandomAgent, "Blind": BlindMinimaxAgent, "Medium": RuleBasedAgent,
    "Minimax": MinimaxAgent, "Hard": AlphaBetaAgent, "Expert": ExpertAgent,
}


@app.get("/api/agents")
def agents_info():
    """How each AI fits the theory: agent type, search strategy, knowledge used."""
    return jsonify({level: {"algorithm": cls.name, "agent_type": cls.agent_type, "search": cls.search,
                            "knowledge": cls.knowledge}
                    for level, cls in AGENT_CLASSES.items()})


@app.post("/api/compare")
def compare():
    """Run uninformed and informed search on the same position, depth 2."""
    data = request.get_json(silent=True) or {}
    board, color = _board(data), _color(data)
    runs = [
        ("Blind Minimax", "Uninformed", BlindMinimaxAgent(depth=2, node_limit=400_000, seed=1)),
        ("Minimax", "Informed", MinimaxAgent(depth=2, max_candidates=10)),
        ("Alpha-Beta (no ordering)", "Informed", AlphaBetaAgent(depth=2, max_candidates=10, ordered=False)),
        ("Alpha-Beta", "Informed", AlphaBetaAgent(depth=2, max_candidates=10)),
    ]
    out = []
    for name, kind, agent in runs:
        move = agent.choose_move(board, color)
        out.append({"algorithm": name, "kind": kind, "nodes": agent.stats.nodes,
                    "time_ms": round(agent.stats.time_ms, 1), "move": list(move) if move else None,
                    "reason": agent.stats.reason})
    n = len(board)
    return jsonify({"size": n, "empty_cells": len(legal_moves(board)),
                    "candidate_cells": len(candidate_cells(board)), "results": out})


@app.post("/api/evaluate")
def evaluate_position():
    """The heuristic function, opened up: patterns found and the resulting score."""
    data = request.get_json(silent=True) or {}
    board = _board(data)
    patterns = {}
    for color in ("black", "white"):
        counts = pattern_counts(board, color)
        patterns[color] = [{"name": CATEGORY_NAMES[i], "count": counts[i], "weight": PATTERNS[i][0],
                            "points": counts[i] * PATTERNS[i][0]} for i in range(len(PATTERNS))]
    score = evaluate(board, "black")
    return jsonify({"score": score, "win_score": WIN_SCORE, "patterns": patterns,
                    "black_points": sum(p["points"] for p in patterns["black"]),
                    "white_points": sum(p["points"] for p in patterns["white"])})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8050))
    print(f"Intelligent Gomoku is running - open http://127.0.0.1:{port} in your browser")
    app.run(host="127.0.0.1", port=port, debug=False, threaded=True)
