"""Tests for the web API (web_app.py) and the post-game analysis.  Run:  python -m pytest -q"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

flask = pytest.importorskip("flask")

import web_app  # noqa: E402
from game_analysis import analyze_game  # noqa: E402


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(web_app, "GAMES_DIR", str(tmp_path))
    return web_app.app.test_client()


def board(stones=()):
    b = [[None] * 15 for _ in range(15)]
    for r, c, col in stones:
        b[r][c] = col
    return b


def test_index_served(client):
    res = client.get("/")
    assert res.status_code == 200 and b"Gomoku" in res.data


@pytest.mark.parametrize("level", ["Easy", "Medium", "Minimax", "Hard", "Expert"])
def test_ai_move_every_level(client, level):
    res = client.post("/api/ai-move", json={"board": board([(7, 7, "black")]), "color": "white", "level": level})
    data = res.get_json()
    assert res.status_code == 200
    r, c = data["move"]
    assert (r, c) != (7, 7) and 0 <= r < 15 and 0 <= c < 15
    assert data["stats"]["reason"]


def test_ai_move_blocks_four(client):
    b = board([(7, c, "black") for c in range(3, 7)] + [(7, 2, "white")])
    data = client.post("/api/ai-move", json={"board": b, "color": "white", "level": "Hard"}).get_json()
    assert data["move"] == [7, 7]


def test_ai_move_reports_win(client):
    b = board([(7, c, "white") for c in range(3, 7)])
    data = client.post("/api/ai-move", json={"board": b, "color": "white", "level": "Medium"}).get_json()
    assert data["wins"] is True


@pytest.mark.parametrize("payload", [
    {},
    {"board": [[None] * 15] * 14, "color": "black"},
    {"board": board(), "color": "red"},
    {"board": board(), "color": "black", "level": "Impossible"},
    {"board": [["x"] * 15] * 15, "color": "black"},
])
def test_ai_move_rejects_bad_input(client, payload):
    assert client.post("/api/ai-move", json=payload).status_code == 400


def test_hint_returns_up_to_three(client):
    data = client.post("/api/hint", json={"board": board([(7, 7, "black"), (7, 8, "white")]),
                                          "color": "black"}).get_json()
    assert 1 <= len(data["hints"]) <= 3
    assert all("reason" in h for h in data["hints"])


def test_opening_is_balanced(client):
    moves = client.get("/api/opening?stones=2").get_json()["moves"]
    assert [m["player"] for m in moves] == ["black", "white"]
    assert moves[0]["row"] == 7 and moves[0]["col"] == 7


def test_save_writes_csv(client, tmp_path):
    moves = [{"player": "black", "row": 7, "col": 7}, {"player": "white", "row": 7, "col": 8}]
    res = client.post("/api/save", json={"mode": "friend", "winner": "black", "moves": moves})
    assert res.status_code == 200
    files = list(tmp_path.glob("game_web_friend_*.csv"))
    assert len(files) == 1
    assert "board_state" in files[0].read_text()


def test_analysis_finds_missed_win_and_danger():
    moves = []
    for i in range(4):  # black builds four in a row, white plays elsewhere
        moves.append({"player": "black", "row": 7, "col": 3 + i})
        moves.append({"player": "white", "row": 0, "col": i * 2})
    moves.append({"player": "black", "row": 12, "col": 12})  # ignores the winning cell
    a = analyze_game(moves, "black")
    assert a["mistakes"]["missed_win"] == 1
    white = analyze_game(moves, "white")
    assert white["mistakes"]["missed_block"] >= 1
    assert white["dangers"] >= 1


def test_analysis_rewards_block(client):
    seq =[("black", 7, 3), ("white", 0, 0), ("black", 7, 4), ("white", 0, 2), ("black", 7, 5),
           ("white", 7, 6)]  # white blocks the open three
    moves = [{"player": p, "row": r, "col": c} for p, r, c in seq]
    a = client.post("/api/analyze", json={"moves": moves, "perspective": "white"}).get_json()
    assert a["strong_moves"] >= 1
    assert 1 <= a["stars"] <= 3


@pytest.mark.parametrize("size", [9, 11, 13])
def test_ai_move_on_smaller_boards(client, size):
    b = [[None] * size for _ in range(size)]
    b[size // 2][size // 2] = "black"
    for level in ("Blind", "Hard"):
        data = client.post("/api/ai-move", json={"board": b, "color": "white", "level": level}).get_json()
        r, c = data["move"]
        assert 0 <= r < size and 0 <= c < size


def test_board_size_limits(client):
    for n in (5, 21):
        b = [[None] * n for _ in range(n)]
        assert client.post("/api/ai-move", json={"board": b, "color": "black"}).status_code == 400


def test_agents_endpoint_lists_categories(client):
    data = client.get("/api/agents").get_json()
    assert set(data) == {"Easy", "Blind", "Medium", "Minimax", "Hard", "Expert"}
    assert data["Blind"]["search"].startswith("Uninformed")


def test_compare_shows_informed_search_is_cheaper(client):
    b = [[None] * 9 for _ in range(9)]
    b[4][4], b[4][5] = "black", "white"
    data = client.post("/api/compare", json={"board": b, "color": "black"}).get_json()
    nodes = {r["algorithm"]: r["nodes"] for r in data["results"]}
    assert nodes["Alpha-Beta"] < nodes["Minimax"] < nodes["Blind Minimax"]
    assert data["candidate_cells"] < data["empty_cells"]


def test_evaluate_endpoint(client):
    b = [[None] * 9 for _ in range(9)]
    b[4][3] = b[4][4] = b[4][5] = "black"
    data = client.post("/api/evaluate", json={"board": b}).get_json()
    assert data["score"] > 0
    assert any(p["name"] == "open three" and p["count"] > 0 for p in data["patterns"]["black"])


def test_analyze_and_save_with_board_size(client, tmp_path):
    moves = [{"player": "black", "row": 8, "col": 8}, {"player": "white", "row": 0, "col": 0}]
    assert client.post("/api/analyze", json={"moves": moves, "perspective": "black", "size": 9}).status_code == 200
    assert client.post("/api/analyze", json={"moves": moves, "perspective": "black", "size": 7}).status_code == 400
    assert client.post("/api/save", json={"moves": moves, "size": 9, "mode": "level2"}).status_code == 200
