"""
player_db.py - Player profiles, ratings and game history (SQLite).

Every human who plays the computer gets a profile and a rating, in the same
way chess players do (the Elo system):

* each robot has a fixed strength rating (Pip 600 ... Draco 1750),
* a new player starts at 1000,
* after a game the rating moves towards what the result says about the
  player: beating a stronger robot gains more than beating a weaker one,
* the AI's judgement of the game (accuracy, see game_analysis.py) adds a
  small bonus or penalty, so playing well is rewarded even in a loss,
* fairness: moving first (Black) is a real advantage in Gomoku, so when the
  player has White the robot is treated as FIRST_MOVE_ADVANTAGE points
  stronger (and weaker when the robot has White). Nobody gains or loses
  rating just because of the colour they were given.

Everything is stored in one SQLite file, data/gomoku.db, with two tables:
players and games.
"""

from __future__ import annotations

import json
import os
import sqlite3
import threading
from datetime import datetime
from typing import Dict, List, Optional

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "data", "gomoku.db")

START_RATING = 1000
FIRST_MOVE_ADVANTAGE = 100   # rating points the first player (Black) is worth
ROBOT_RATINGS = {"Easy": 600, "Blind": 700, "Medium": 1100, "Minimax": 1250, "Hard": 1500, "Expert": 1750}
ROBOT_NAMES = {"Easy": "Pip the Chick", "Blind": "Batty", "Medium": "Foxy", "Minimax": "Turtle Max",
               "Hard": "Professor Owl", "Expert": "Draco"}
TITLES = ((1800, "Grandmaster", "🐉"), (1600, "Master", "👑"), (1400, "Expert", "🏅"), (1200, "Skilled", "⭐"),
          (1000, "Learner", "📘"), (800, "Beginner", "🌱"), (0, "Pebble", "🪨"))

_lock = threading.Lock()

SCHEMA = """
CREATE TABLE IF NOT EXISTS players (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL UNIQUE COLLATE NOCASE,
    avatar      TEXT NOT NULL DEFAULT '🙂',
    rating      REAL NOT NULL DEFAULT 1000,
    created_at  TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS games (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    player_id       INTEGER NOT NULL REFERENCES players(id),
    played_at       TEXT NOT NULL,
    mode            TEXT NOT NULL,
    opponent        TEXT NOT NULL,
    opponent_rating INTEGER NOT NULL,
    board_size      INTEGER NOT NULL,
    human_color     TEXT NOT NULL,
    result          TEXT NOT NULL,          -- win / loss / draw
    moves           INTEGER NOT NULL,
    accuracy        REAL NOT NULL,
    grade           TEXT NOT NULL,
    mistakes        INTEGER NOT NULL,
    strong_moves    INTEGER NOT NULL,
    rating_before   REAL NOT NULL,
    rating_after    REAL NOT NULL,
    duration_s      INTEGER NOT NULL DEFAULT 0,
    move_list       TEXT NOT NULL,          -- JSON list of {player,row,col}
    mistake_types   TEXT NOT NULL DEFAULT '{}'  -- JSON {missed_win, missed_block, missed_defence, weak_move}
);
CREATE INDEX IF NOT EXISTS games_by_player ON games(player_id, played_at);
"""


def connect(path: Optional[str] = None) -> sqlite3.Connection:
    path = path or DB_PATH
    os.makedirs(os.path.dirname(path), exist_ok=True)
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    cols = {r["name"] for r in con.execute("PRAGMA table_info(games)")}
    if "mistake_types" not in cols:  # databases created by an older version
        con.execute("ALTER TABLE games ADD COLUMN mistake_types TEXT NOT NULL DEFAULT '{}'")
        con.commit()
    return con


def title_for(rating: float) -> Dict:
    for limit, name, icon in TITLES:
        if rating >= limit:
            return {"title": name, "icon": icon}
    return {"title": TITLES[-1][1], "icon": TITLES[-1][2]}


def clean_name(name) -> str:
    name = " ".join(str(name or "").split())[:20]
    if not name:
        raise ValueError("name is required")
    return name


def expected_score(player: float, opponent: float) -> float:
    """Elo: probability-like expected score of the player against the opponent."""
    return 1 / (1 + 10 ** ((opponent - player) / 400))


def colour_adjusted(opponent: float, human_color: str) -> float:
    """The robot's effective strength once the first-move advantage is counted."""
    return opponent + (FIRST_MOVE_ADVANTAGE if human_color == "white" else -FIRST_MOVE_ADVANTAGE) / 2


def rating_change(player: float, opponent: float, result: str, accuracy: float, games_played: int,
                  human_color: str = "") -> float:
    """Elo update plus a small bonus for playing accurately.

    K is larger for a player's first games so a new rating settles quickly.
    With ``human_color`` the robot's rating is corrected for who moved first.
    """
    if human_color:
        opponent = colour_adjusted(opponent, human_color)
    actual = {"win": 1.0, "draw": 0.5, "loss": 0.0}[result]
    k = 48 if games_played < 10 else 32
    elo = k * (actual - expected_score(player, opponent))
    bonus = (accuracy - 60) / 10          # -6 ... +4 points
    return round(elo + bonus, 1)


def get_or_create_player(con: sqlite3.Connection, name: str, avatar: Optional[str] = None) -> sqlite3.Row:
    name = clean_name(name)
    row = con.execute("SELECT * FROM players WHERE name = ?", (name,)).fetchone()
    if row is None:
        con.execute("INSERT INTO players (name, avatar, rating, created_at) VALUES (?, ?, ?, ?)",
                    (name, (avatar or "🙂")[:4], START_RATING, datetime.now().isoformat(timespec="seconds")))
        con.commit()
        row = con.execute("SELECT * FROM players WHERE name = ?", (name,)).fetchone()
    elif avatar and avatar[:4] != row["avatar"]:
        con.execute("UPDATE players SET avatar = ? WHERE id = ?", (avatar[:4], row["id"]))
        con.commit()
        row = con.execute("SELECT * FROM players WHERE id = ?", (row["id"],)).fetchone()
    return row


def record_game(con: sqlite3.Connection, name: str, level: str, human_color: str, winner: str,
                moves: List[Dict], size: int, analysis: Dict, duration_s: int = 0,
                mode: str = "quick", avatar: Optional[str] = None) -> Dict:
    """Store a finished human-vs-robot game and update the player's rating."""
    if level not in ROBOT_RATINGS:
        raise ValueError("unknown opponent")
    with _lock:
        player = get_or_create_player(con, name, avatar)
        result = "draw" if winner == "draw" else ("win" if winner == human_color else "loss")
        games_played = con.execute("SELECT COUNT(*) FROM games WHERE player_id = ?", (player["id"],)).fetchone()[0]
        before = player["rating"]
        delta = rating_change(before, ROBOT_RATINGS[level], result, analysis["accuracy"], games_played, human_color)
        after = max(100.0, before + delta)
        con.execute("UPDATE players SET rating = ? WHERE id = ?", (after, player["id"]))
        cur = con.execute(
            """INSERT INTO games (player_id, played_at, mode, opponent, opponent_rating, board_size, human_color,
               result, moves, accuracy, grade, mistakes, strong_moves, rating_before, rating_after, duration_s,
               move_list, mistake_types) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (player["id"], datetime.now().isoformat(timespec="seconds"), mode[:20], level, ROBOT_RATINGS[level],
             size, human_color, result, len(moves), analysis["accuracy"], analysis["grade"],
             analysis["total_mistakes"], analysis["strong_moves"], before, after, int(duration_s),
             json.dumps([{"player": m["player"], "row": m["row"], "col": m["col"]} for m in moves]),
             json.dumps(analysis.get("mistakes", {}))))
        con.commit()
    return {"game_id": cur.lastrowid, "player": player["name"], "result": result,
            "rating_before": round(before), "rating_after": round(after), "rating_change": round(after - before),
            "opponent_rating": ROBOT_RATINGS[level], "colour_adjusted_rating": round(colour_adjusted(ROBOT_RATINGS[level], human_color)),
            **title_for(after)}


def recent_performance(con: sqlite3.Connection, name: str, n: int = 5) -> Optional[Dict]:
    """Averages over the player's last n games: the inputs of the fuzzy system."""
    p = con.execute("SELECT id FROM players WHERE name = ?", (clean_name(name),)).fetchone()
    if p is None:
        return None
    rows = con.execute("SELECT * FROM games WHERE player_id = ? ORDER BY played_at DESC, id DESC LIMIT ?",
                       (p["id"], n)).fetchall()
    if not rows:
        return None
    my_moves = sum(max(1, (r["moves"] + (1 if r["human_color"] == "black" else 0)) // 2) for r in rows)
    return {
        "games": len(rows),
        "accuracy": round(sum(r["accuracy"] for r in rows) / len(rows), 1),
        "mistakes": round(10 * sum(r["mistakes"] for r in rows) / my_moves, 2),
        "results": round(sum({"win": 1, "draw": 0.5, "loss": 0}[r["result"]] for r in rows) / len(rows), 2),
        "last_opponent": rows[0]["opponent"],
    }


def insights(con: sqlite3.Connection, name: str) -> List[Dict]:
    """Plain-language insights the AI draws from all of a player's games."""
    p = con.execute("SELECT id FROM players WHERE name = ?", (clean_name(name),)).fetchone()
    if p is None:
        return []
    rows = con.execute("SELECT * FROM games WHERE player_id = ? ORDER BY played_at, id", (p["id"],)).fetchall()
    if not rows:
        return []
    out = []
    totals: Dict[str, int] = {}
    for r in rows:
        for k, v in json.loads(r["mistake_types"] or "{}").items():
            totals[k] = totals.get(k, 0) + v
    words = {"missed_win": ("finishing your own five", "Before every move, check: can I complete five right now?"),
             "missed_block": ("blocking the opponent's four", "Always look for the opponent's four in a row first."),
             "missed_defence": ("stopping open threes", "Block an open three at one end before it becomes an open four."),
             "weak_move": ("choosing strong squares", "Play next to your own stones or across the opponent's lines.")}
    if any(totals.values()):
        worst = max(totals, key=totals.get)
        out.append({"icon": "🎯", "title": f"Practise {words[worst][0]}",
                    "text": f"This is your most common mistake ({totals[worst]} times). {words[worst][1]}"})
    else:
        out.append({"icon": "🌟", "title": "No serious mistakes so far", "text": "You never missed a win or a block. Keep it up!"})
    if len(rows) >= 4:
        half = len(rows) // 2
        first = sum(r["accuracy"] for r in rows[:half]) / half
        last = sum(r["accuracy"] for r in rows[half:]) / (len(rows) - half)
        trend = last - first
        out.append({"icon": "📈" if trend >= 0 else "📉",
                    "title": "You are improving" if trend >= 2 else "Your accuracy is dropping" if trend <= -2 else "Your accuracy is steady",
                    "text": f"Average accuracy went from {first:.0f}% (first games) to {last:.0f}% (recent games)."})
    for colour in ("black", "white"):
        games = [r for r in rows if r["human_color"] == colour]
        if games:
            wins = sum(r["result"] == "win" for r in games)
            out.append({"icon": "⚫" if colour == "black" else "⚪", "title": f"As {colour}: {wins} win(s) in {len(games)} game(s)",
                        "text": "Black moves first, which is an advantage. Your rating takes this into account, so playing White is never punished."
                        if colour == "white" else "Black moves first. Try White too: it's harder, and wins count for more."})
    beaten = [r["opponent"] for r in rows if r["result"] == "win"]
    if beaten:
        best = max(beaten, key=lambda lv: ROBOT_RATINGS[lv])
        out.append({"icon": "🏆", "title": f"Strongest robot beaten: {ROBOT_NAMES[best]}",
                    "text": f"Rated {ROBOT_RATINGS[best]}. Beat a stronger robot to climb faster."})
    return out


def delete_player(con: sqlite3.Connection, name: str) -> bool:
    """Remove a player and all their games (the player's right to delete their data)."""
    p = con.execute("SELECT id FROM players WHERE name = ?", (clean_name(name),)).fetchone()
    if p is None:
        return False
    with _lock:
        con.execute("DELETE FROM games WHERE player_id = ?", (p["id"],))
        con.execute("DELETE FROM players WHERE id = ?", (p["id"],))
        con.commit()
    return True


def leaderboard(con: sqlite3.Connection, limit: int = 20) -> List[Dict]:
    rows = con.execute(
        """SELECT p.name, p.avatar, p.rating, COUNT(g.id) AS games,
                  SUM(g.result = 'win') AS wins, SUM(g.result = 'draw') AS draws, SUM(g.result = 'loss') AS losses,
                  ROUND(AVG(g.accuracy), 1) AS avg_accuracy, MAX(g.accuracy) AS best_accuracy
           FROM players p LEFT JOIN games g ON g.player_id = p.id
           GROUP BY p.id ORDER BY p.rating DESC, games DESC LIMIT ?""", (limit,)).fetchall()
    return [{"rank": i + 1, "name": r["name"], "avatar": r["avatar"], "rating": round(r["rating"]),
             "games": r["games"], "wins": r["wins"] or 0, "draws": r["draws"] or 0, "losses": r["losses"] or 0,
             "avg_accuracy": r["avg_accuracy"], "best_accuracy": r["best_accuracy"], **title_for(r["rating"])}
            for i, r in enumerate(rows)]


def player_profile(con: sqlite3.Connection, name: str) -> Optional[Dict]:
    p = con.execute("SELECT * FROM players WHERE name = ?", (clean_name(name),)).fetchone()
    if p is None:
        return None
    games = con.execute("SELECT * FROM games WHERE player_id = ? ORDER BY played_at, id", (p["id"],)).fetchall()
    history = [{"id": g["id"], "played_at": g["played_at"], "opponent": g["opponent"],
                "opponent_name": ROBOT_NAMES.get(g["opponent"], g["opponent"]), "board_size": g["board_size"],
                "result": g["result"], "moves": g["moves"], "accuracy": g["accuracy"], "grade": g["grade"],
                "rating_after": round(g["rating_after"]), "rating_change": round(g["rating_after"] - g["rating_before"]),
                "mode": g["mode"]} for g in games]
    vs = {}
    for g in games:
        v = vs.setdefault(g["opponent"], {"opponent": g["opponent"], "name": ROBOT_NAMES.get(g["opponent"], g["opponent"]),
                                          "robot_rating": ROBOT_RATINGS.get(g["opponent"]), "win": 0, "draw": 0, "loss": 0})
        v[g["result"]] += 1
    played = len(games)
    return {
        "name": p["name"], "avatar": p["avatar"], "rating": round(p["rating"]), **title_for(p["rating"]),
        "games": played,
        "wins": sum(g["result"] == "win" for g in games),
        "draws": sum(g["result"] == "draw" for g in games),
        "losses": sum(g["result"] == "loss" for g in games),
        "avg_accuracy": round(sum(g["accuracy"] for g in games) / played, 1) if played else None,
        "best_accuracy": max((g["accuracy"] for g in games), default=None),
        "rating_history": [START_RATING] + [h["rating_after"] for h in history],
        "history": list(reversed(history[-50:])),
        "vs_robots": [vs[k] for k in ROBOT_RATINGS if k in vs],
        "rank": next((r["rank"] for r in leaderboard(con, 10_000) if r["name"].lower() == p["name"].lower()), None),
        "insights": insights(con, p["name"]),
        "recent": recent_performance(con, p["name"]),
    }
