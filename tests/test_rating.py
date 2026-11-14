"""Tests for the AI's game grading, player ratings and the scoreboard.  Run:  python -m pytest -q"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import player_db  # noqa: E402
from agents import AlphaBetaAgent, RandomAgent, empty_board, is_five, make_agent, other  # noqa: E402
from game_analysis import analyze_game, grade_for  # noqa: E402


def play(black, white, n=15):
    s, moves, color = empty_board(n), [], "black"
    agents = {"black": black, "white": white}
    for _ in range(n * n):
        r, c = agents[color].choose_move(s, color)
        s[r][c] = color
        moves.append({"player": color, "row": r, "col": c})
        if is_five(s, r, c, color):
            break
        color = other(color)
    return moves


def five_in_a_row_game():
    moves = []
    for i in range(5):
        moves.append({"player": "black", "row": 7, "col": 3 + i})
        if i < 4:
            moves.append({"player": "white", "row": 0, "col": i * 2})
    return moves


# ---------------- the AI's grade for a game ----------------

def test_strong_play_grades_higher_than_random_play():
    moves = play(AlphaBetaAgent(depth=3), RandomAgent(seed=3))
    strong, weak = analyze_game(moves, "black"), analyze_game(moves, "white")
    assert strong["accuracy"] > 80 and strong["grade"] in ("A", "A+")
    assert weak["accuracy"] < strong["accuracy"]


def test_grade_boundaries():
    assert grade_for(95)[0] == "A+" and grade_for(85)[0] == "A" and grade_for(70)[0] == "B"
    assert grade_for(55)[0] == "C" and grade_for(10)[0] == "D"


def test_stars_never_contradict_grade():
    a = analyze_game(play(AlphaBetaAgent(depth=3), RandomAgent(seed=3)), "white")
    assert a["stars"] <= {"A+": 3, "A": 3, "B": 2, "C": 2}.get(a["grade"], 1)


def test_missed_win_costs_accuracy():
    moves = five_in_a_row_game()[:-1] + [{"player": "black", "row": 12, "col": 12}]
    assert analyze_game(moves, "black")["mistakes"]["missed_win"] == 1
    assert analyze_game(moves, "black")["accuracy"] < analyze_game(five_in_a_row_game(), "black")["accuracy"]


# ---------------- ratings ----------------

def test_beating_a_stronger_robot_gains_more():
    weak = player_db.rating_change(1000, 600, "win", 70, 0)
    strong = player_db.rating_change(1000, 1750, "win", 70, 0)
    assert strong > weak > 0


def test_losing_to_a_much_stronger_robot_costs_little():
    assert -5 < player_db.rating_change(1000, 1750, "loss", 60, 20) < 0
    assert player_db.rating_change(1000, 600, "loss", 60, 20) < -20


def test_accuracy_bonus():
    assert player_db.rating_change(1000, 1100, "loss", 95, 20) > player_db.rating_change(1000, 1100, "loss", 20, 20)


def test_titles():
    assert player_db.title_for(1000)["title"] == "Learner"
    assert player_db.title_for(1850)["title"] == "Grandmaster"
    assert player_db.title_for(500)["title"] == "Pebble"


def test_record_game_and_profile(tmp_path):
    con = player_db.connect(str(tmp_path / "t.db"))
    moves = five_in_a_row_game()
    a = analyze_game(moves, "black")
    r = player_db.record_game(con, "Asha", "Medium", "black", "black", moves, 15, a, avatar="🦄")
    assert r["result"] == "win" and r["rating_after"] > r["rating_before"] == 1000
    player_db.record_game(con, "asha", "Expert", "black", "white", moves[:4], 15, analyze_game(moves[:4], "black"))
    prof = player_db.player_profile(con, "ASHA")  # names are case-insensitive
    assert prof["games"] == 2 and prof["wins"] == 1 and prof["losses"] == 1
    assert prof["rating_history"][0] == 1000 and len(prof["rating_history"]) == 3
    assert {v["opponent"] for v in prof["vs_robots"]} == {"Medium", "Expert"}
    board = player_db.leaderboard(con)
    assert board[0]["name"] == "Asha" and board[0]["rank"] == 1


def test_names_are_cleaned():
    assert player_db.clean_name("  Harsha   A  ") == "Harsha A"
    with pytest.raises(ValueError):
        player_db.clean_name("   ")


# ---------------- the AI shows what it considered ----------------

@pytest.mark.parametrize("level", ["Blind", "Medium", "Minimax", "Hard", "Expert"])
def test_agents_report_the_moves_they_compared(level):
    s = empty_board()
    s[7][7], s[7][8] = "black", "white"
    agent = make_agent(level)
    move = agent.choose_move(s, "black")
    considered = agent.stats.considered
    assert 1 <= len(considered) <= 8
    assert (considered[0]["row"], considered[0]["col"]) == move  # the chosen move is listed first
    assert all(s[m["row"]][m["col"]] is None for m in considered)


# ---------------- web API ----------------

@pytest.fixture
def client(tmp_path, monkeypatch):
    flask = pytest.importorskip("flask")  # noqa: F841
    import web_app
    monkeypatch.setattr(web_app, "DB_PATH", str(tmp_path / "web.db"))
    monkeypatch.setattr(web_app, "GAMES_DIR", str(tmp_path / "games"))
    return web_app.app.test_client()


def test_result_endpoint_grades_and_rates(client):
    payload = {"player": "Kid", "avatar": "🐼", "level": "Hard", "human_color": "black", "winner": "black",
               "moves": five_in_a_row_game(), "size": 15, "duration_s": 42}
    data = client.post("/api/result", json=payload).get_json()
    assert data["analysis"]["grade"] and 0 <= data["analysis"]["accuracy"] <= 100
    assert data["rating"]["rating_change"] > 0
    board = client.get("/api/scoreboard?player=kid").get_json()
    assert board["leaderboard"][0]["name"] == "Kid"
    assert board["player"]["history"][0]["opponent"] == "Hard"
    assert len(board["robots"]) == 6


def test_result_endpoint_rejects_bad_input(client):
    good = {"player": "Kid", "level": "Hard", "human_color": "black", "winner": "black", "moves": five_in_a_row_game()}
    assert client.post("/api/result", json={**good, "level": "God"}).status_code == 400
    assert client.post("/api/result", json={**good, "winner": "red"}).status_code == 400
    assert client.post("/api/result", json={**good, "player": " "}).status_code == 400


def test_player_endpoint(client):
    data = client.post("/api/player", json={"name": "Nina", "avatar": "🐸"}).get_json()
    assert data["name"] == "Nina" and data["rating"] == 1000 and data["games"] == 0
    assert client.get("/api/scoreboard").get_json()["player"] is None
