"""Tests for fuzzy logic, the AI tutor, fairness and privacy features.  Run:  python -m pytest -q"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import fuzzy_logic  # noqa: E402
import player_db  # noqa: E402
import tutor  # noqa: E402
from agents import empty_board  # noqa: E402
from game_analysis import analyze_game  # noqa: E402


# ---------------- fuzzy logic ----------------

def test_membership_functions():
    f = fuzzy_logic.tri(0, 5, 10)
    assert f(5) == 1 and f(0) == 0 and f(2.5) == 0.5
    g = fuzzy_logic.trap(0, 2, 4, 6)
    assert g(3) == 1 and g(1) == 0.5 and g(7) == 0


def test_overlapping_sets():
    m = fuzzy_logic.ACCURACY.fuzzify(75)
    assert 0 < m["medium"] < 1 and 0 < m["high"] < 1 and m["low"] == 0


@pytest.mark.parametrize("acc, mis, res, skill, adjust", [
    (92, 0.2, 0.9, "advanced", "harder"),
    (30, 5, 0.1, "beginner", "easier"),
    (62, 2, 0.5, "intermediate", "same"),
])
def test_inference_outcomes(acc, mis, res, skill, adjust):
    out = fuzzy_logic.infer(acc, mis, res)
    assert out["skill_label"] == skill and out["adjust_label"] == adjust
    assert 0 <= out["skill"] <= 100 and -1 <= out["adjust"] <= 1
    assert any(r["strength"] > 0 for r in out["rules"])


def test_skill_grows_with_accuracy():
    skills = [fuzzy_logic.infer(a, 1, 0.5)["skill"] for a in (20, 50, 80, 95)]
    assert skills == sorted(skills)


def test_recommendation_moves_along_the_ladder():
    assert fuzzy_logic.recommend("Medium", 0.7) == "Minimax"
    assert fuzzy_logic.recommend("Medium", -0.7) == "Blind"
    assert fuzzy_logic.recommend("Medium", 0.0) == "Medium"
    assert fuzzy_logic.recommend("Expert", 0.9) == "Expert"
    assert fuzzy_logic.recommend("Easy", -0.9) == "Easy"


# ---------------- AI tutor ----------------

@pytest.mark.parametrize("kind", list(tutor.PUZZLE_KINDS))
def test_generated_puzzles_are_solvable(kind):
    p = tutor.make_puzzle(kind, 9, seed=3)
    assert p["answers"] and p["kind"] == kind
    good = tutor.check_answer(p["board"], p["color"], kind, p["answers"][0])
    assert good["correct"]


def test_wrong_answer_is_explained():
    p = tutor.make_puzzle("block", 9, seed=3)
    empty = next([r, c] for r in range(9) for c in range(9) if p["board"][r][c] is None and [r, c] not in p["answers"])
    res = tutor.check_answer(p["board"], p["color"], "block", empty)
    assert not res["correct"] and res["solution"]


def test_coach_spots_a_missed_block_and_a_good_move():
    b = empty_board(9)
    for c in range(1, 5):
        b[4][c] = "white"
    b[4][0] = "black"
    bad = tutor.coach_move(b, "black", [0, 8])
    assert bad["verdict"] == "mistake" and bad["better"] == [4, 5]
    good = tutor.coach_move(b, "black", [4, 5])
    assert good["verdict"] in ("great", "good")


def test_formulation_has_every_component():
    b = empty_board(15)
    b[7][7] = "black"
    f = tutor.formulate(b, "white")
    names = {c["name"] for c in f["components"]}
    assert {"State", "Initial state", "Actions", "Transition model", "Goal (terminal) test", "Utility"} <= names
    assert f["empty"] == 224 and f["candidates"] == 24 and not f["terminal"]


def test_fairness_check_counts_every_game():
    d = tutor.fairness_check(games=4, size=9)
    assert d["black"] + d["white"] + d["draw"] == 4


# ---------------- fairness + privacy in the rating system ----------------

def test_colour_fair_rating():
    as_black = player_db.rating_change(1000, 1100, "win", 60, 20, "black")
    as_white = player_db.rating_change(1000, 1100, "win", 60, 20, "white")
    assert as_white > as_black  # winning without the first-move advantage is worth more


def test_recent_performance_insights_and_delete(tmp_path):
    con = player_db.connect(str(tmp_path / "p.db"))
    moves = []
    for i in range(5):
        moves.append({"player": "black", "row": 7, "col": 3 + i})
        if i < 4:
            moves.append({"player": "white", "row": 0, "col": i * 2})
    player_db.record_game(con, "Ravi", "Medium", "black", "black", moves, 15, analyze_game(moves, "black"))
    rec = player_db.recent_performance(con, "Ravi")
    assert rec["games"] == 1 and rec["results"] == 1 and rec["last_opponent"] == "Medium"
    assert player_db.insights(con, "Ravi")
    assert player_db.delete_player(con, "ravi")
    assert player_db.player_profile(con, "Ravi") is None
    assert con.execute("SELECT COUNT(*) FROM games").fetchone()[0] == 0


# ---------------- web endpoints ----------------

@pytest.fixture
def client(tmp_path, monkeypatch):
    pytest.importorskip("flask")
    import web_app
    monkeypatch.setattr(web_app, "DB_PATH", str(tmp_path / "web.db"))
    return web_app.app.test_client()


def test_tutor_endpoints(client):
    p = client.get("/api/puzzle?kind=win&seed=3").get_json()
    assert client.post("/api/check", json={"board": p["board"], "color": p["color"], "kind": "win",
                                           "move": p["answers"][0]}).get_json()["correct"]
    assert client.get("/api/puzzle?kind=nonsense").status_code == 400
    c = client.post("/api/coach", json={"board": p["board"], "color": p["color"], "move": p["answers"][0]}).get_json()
    assert c["verdict"] in ("great", "good")


def test_fuzzy_and_smart_match_endpoints(client):
    f = client.post("/api/fuzzy", json={"accuracy": 90, "mistakes": 0.5, "results": 0.9}).get_json()
    assert f["adjust_label"] == "harder" and "variables" in f
    assert client.get("/api/smart-match").get_json()["level"] == "Medium"


def test_delete_endpoint(client):
    client.post("/api/player", json={"name": "Zara"})
    assert client.delete("/api/player?name=Zara").get_json()["deleted"] is True
    assert client.get("/api/scoreboard?player=Zara").get_json()["player"] is None


def test_formulation_endpoint(client):
    b = [[None] * 9 for _ in range(9)]
    assert client.post("/api/formulation", json={"board": b, "color": "black"}).get_json()["empty"] == 81


# ---------------- the AI's visible thinking ----------------

def _four_on_diagonal():
    b = empty_board(9)
    for r, c in [(2, 2), (3, 3), (4, 4), (5, 5)]:
        b[r][c] = "black"
    for r, c in [(6, 6), (8, 4), (8, 7)]:
        b[r][c] = "white"
    return b


def test_blind_thinking_is_not_just_the_top_row():
    from agents import BlindMinimaxAgent
    agent = BlindMinimaxAgent(seed=5)
    assert agent.choose_move(_four_on_diagonal(), "white") == (1, 1)  # blocks the four
    runners_up = agent.stats.considered[1:]
    assert len({m["row"] for m in runners_up}) > 1  # ties are sampled from the whole board


def test_random_agent_has_dice_squares_and_forced_moves_show_one():
    from agents import AlphaBetaAgent, RandomAgent
    r = RandomAgent(seed=1)
    move = r.choose_move(_four_on_diagonal(), "white")
    assert r.stats.considered and (r.stats.considered[0]["row"], r.stats.considered[0]["col"]) == move
    a = AlphaBetaAgent(depth=3)
    a.choose_move(_four_on_diagonal(), "white")
    assert len(a.stats.considered) == 1  # forced block: everything else was pruned
