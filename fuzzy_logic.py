"""
fuzzy_logic.py - Fuzzy inference for player skill and adaptive difficulty.

A player's performance is never simply "good" or "bad": 72 % accuracy is a bit
"medium" and a bit "high" at the same time. Fuzzy logic handles exactly this
kind of vague, overlapping category. We use a Mamdani fuzzy inference system:

  1. Fuzzification  - crisp inputs -> degrees of membership in fuzzy sets
  2. Rule evaluation - IF-THEN rules, AND = min, OR = max
  3. Aggregation     - each output set is clipped by its rule strength, then
                       all clipped sets are combined with max
  4. Defuzzification - centroid (centre of gravity) of the combined shape

Inputs (from the AI's grading of the player's recent games):
  accuracy  0..100  move accuracy                    low / medium / high
  mistakes  0..10   serious mistakes per 10 moves    few / some / many
  results   0..1    share of recent games won         losing / even / winning

Outputs:
  skill     0..100  how skilled the player is        beginner / intermediate / advanced
  adjust    -1..+1  how to change the difficulty     easier / same / harder

The output drives "Smart Match" (the next opponent is picked for the player)
and the skill assessment shown after every game.
"""

from __future__ import annotations

from typing import Callable, Dict, List, Tuple

MF = Callable[[float], float]


def tri(a: float, b: float, c: float) -> MF:
    """Triangular membership function peaking at b."""
    def f(x: float) -> float:
        if x <= a or x >= c:
            return 1.0 if x == b else 0.0
        return (x - a) / (b - a) if x < b else (c - x) / (c - b)
    return f


def trap(a: float, b: float, c: float, d: float) -> MF:
    """Trapezoidal membership function, flat (= 1) between b and c."""
    def f(x: float) -> float:
        if x < a or x > d:
            return 0.0
        if b <= x <= c:
            return 1.0
        if x < b:
            return (x - a) / (b - a) if b > a else 1.0
        return (d - x) / (d - c) if d > c else 1.0
    return f


class FuzzyVariable:
    def __init__(self, name: str, lo: float, hi: float, sets: Dict[str, Tuple[str, Tuple[float, ...]]]):
        self.name, self.lo, self.hi = name, lo, hi
        self.shapes = sets
        self.sets: Dict[str, MF] = {k: (tri if kind == "tri" else trap)(*pts) for k, (kind, pts) in sets.items()}

    def fuzzify(self, x: float) -> Dict[str, float]:
        x = max(self.lo, min(self.hi, x))
        return {k: round(f(x), 4) for k, f in self.sets.items()}

    def describe(self) -> Dict:
        return {"name": self.name, "min": self.lo, "max": self.hi,
                "sets": {k: {"shape": kind, "points": list(pts)} for k, (kind, pts) in self.shapes.items()}}


ACCURACY = FuzzyVariable("accuracy", 0, 100, {
    "low": ("trap", (0, 0, 35, 55)),
    "medium": ("tri", (40, 62, 82)),
    "high": ("trap", (68, 85, 100, 100)),
})
MISTAKES = FuzzyVariable("mistakes", 0, 10, {
    "few": ("trap", (0, 0, 0.5, 1.5)),
    "some": ("tri", (0.5, 2, 3.5)),
    "many": ("trap", (2.5, 4, 10, 10)),
})
RESULTS = FuzzyVariable("results", 0, 1, {
    "losing": ("trap", (0, 0, 0.2, 0.45)),
    "even": ("tri", (0.25, 0.5, 0.75)),
    "winning": ("trap", (0.55, 0.8, 1, 1)),
})
SKILL = FuzzyVariable("skill", 0, 100, {
    "beginner": ("trap", (0, 0, 20, 40)),
    "intermediate": ("tri", (25, 50, 75)),
    "advanced": ("trap", (60, 80, 100, 100)),
})
ADJUST = FuzzyVariable("adjust", -1, 1, {
    "easier": ("trap", (-1, -1, -0.6, -0.1)),
    "same": ("tri", (-0.4, 0, 0.4)),
    "harder": ("trap", (0.1, 0.6, 1, 1)),
})

# (description, antecedent function, output variable, output set)
# antecedents get the fuzzified inputs: a = accuracy, m = mistakes, r = results
RULES: List[Tuple[str, Callable[[Dict, Dict, Dict], float], str, str]] = [
    ("IF accuracy is high AND mistakes are few THEN skill is advanced",
     lambda a, m, r: min(a["high"], m["few"]), "skill", "advanced"),
    ("IF accuracy is high AND mistakes are some THEN skill is intermediate",
     lambda a, m, r: min(a["high"], m["some"]), "skill", "intermediate"),
    ("IF accuracy is medium THEN skill is intermediate",
     lambda a, m, r: a["medium"], "skill", "intermediate"),
    ("IF accuracy is low OR mistakes are many THEN skill is beginner",
     lambda a, m, r: max(a["low"], m["many"]), "skill", "beginner"),
    ("IF results are winning AND accuracy is high THEN make it harder",
     lambda a, m, r: min(r["winning"], a["high"]), "adjust", "harder"),
    ("IF results are winning AND accuracy is medium THEN make it harder",
     lambda a, m, r: min(r["winning"], a["medium"]), "adjust", "harder"),
    ("IF results are even THEN keep the same level",
     lambda a, m, r: r["even"], "adjust", "same"),
    ("IF results are winning AND mistakes are many THEN keep the same level",
     lambda a, m, r: min(r["winning"], m["many"]), "adjust", "same"),
    ("IF results are losing AND accuracy is high THEN keep the same level",
     lambda a, m, r: min(r["losing"], a["high"]), "adjust", "same"),
    ("IF results are losing AND mistakes are many THEN make it easier",
     lambda a, m, r: min(r["losing"], m["many"]), "adjust", "easier"),
    ("IF results are losing AND accuracy is low THEN make it easier",
     lambda a, m, r: min(r["losing"], a["low"]), "adjust", "easier"),
    ("IF results are losing AND accuracy is medium THEN make it easier",
     lambda a, m, r: min(r["losing"], a["medium"]), "adjust", "easier"),
]

OUTPUTS = {"skill": SKILL, "adjust": ADJUST}
LADDER = ["Easy", "Blind", "Medium", "Minimax", "Hard", "Expert"]   # weakest -> strongest robot


def _centroid(var: FuzzyVariable, clip: Dict[str, float], samples: int = 201):
    """Clip each output set by its rule strength, combine with max, return centroid and curve."""
    xs = [var.lo + (var.hi - var.lo) * i / (samples - 1) for i in range(samples)]
    ys = [max((min(clip.get(k, 0.0), f(x)) for k, f in var.sets.items()), default=0.0) for x in xs]
    area = sum(ys)
    crisp = sum(x * y for x, y in zip(xs, ys)) / area if area else (var.lo + var.hi) / 2
    return crisp, xs, ys


def infer(accuracy: float, mistakes: float, results: float) -> Dict:
    """Run the whole fuzzy inference and return every intermediate step."""
    a, m, r = ACCURACY.fuzzify(accuracy), MISTAKES.fuzzify(mistakes), RESULTS.fuzzify(results)
    fired, clip = [], {"skill": {}, "adjust": {}}
    for text, ante, out, label in RULES:
        strength = round(ante(a, m, r), 4)
        fired.append({"rule": text, "strength": strength, "output": out, "set": label})
        clip[out][label] = max(clip[out].get(label, 0.0), strength)
    result = {"inputs": {"accuracy": accuracy, "mistakes": mistakes, "results": results},
              "memberships": {"accuracy": a, "mistakes": m, "results": r}, "rules": fired}
    for out, var in OUTPUTS.items():
        crisp, xs, ys = _centroid(var, clip[out])
        result[out] = round(crisp, 2)
        result[out + "_label"] = max(var.fuzzify(crisp).items(), key=lambda kv: kv[1])[0]
        result[out + "_curve"] = [[round(x, 3), round(y, 4)] for x, y in zip(xs[::4], ys[::4])]
    return result


def recommend(current_level: str, adjust: float) -> str:
    """Next robot on the ladder after a fuzzy difficulty adjustment."""
    i = LADDER.index(current_level) if current_level in LADDER else 2
    step = 1 if adjust > 0.3 else -1 if adjust < -0.3 else 0
    return LADDER[max(0, min(len(LADDER) - 1, i + step))]


def level_for_skill(skill: float) -> str:
    """A starting robot for a player of the given fuzzy skill (used when there is no history)."""
    return LADDER[min(len(LADDER) - 1, int(skill / (100 / len(LADDER))))]


def variables() -> Dict:
    return {v.name: v.describe() for v in (ACCURACY, MISTAKES, RESULTS, SKILL, ADJUST)}
