import tkinter as tk
import csv
import os
import threading
from datetime import datetime

from agents import DIFFICULTIES, make_agent, is_five, is_full, winning_line

CELL = 32
MARGIN = 15
AGENT_CHOICES = ["Easy", "Medium", "Minimax", "Hard", "Expert"]
AGENT_LABELS = {
    "Easy": "Random",
    "Medium": "Rule-Based",
    "Minimax": "Minimax (no pruning)",
    "Hard": "Alpha-Beta",
    "Expert": "Expert (ID + TT)",
}


class AIvsAIPage:
    """Watch two AI agents play each other, with live search statistics."""

    def __init__(self, root, back_callback, open_single_cb, open_pvp_cb, open_how_cb):
        self.root = root
        self.back_callback = back_callback
        self.open_single_cb = open_single_cb
        self.open_pvp_cb = open_pvp_cb
        self.open_how_cb = open_how_cb

        self.state = [[None] * 15 for _ in range(15)]
        self.stones = []
        self.move_log = []
        self.running = False
        self.thinking = False
        self.game_over = False
        self.current = "black"
        self.agents = {}
        self.totals = {}
        self.started_at = None

        self.main_container = tk.Frame(root, bg="#f0f4f8")
        self.main_container.pack(fill=tk.BOTH, expand=True)
        self.create_header()
        self.create_controls()
        self.create_body()

    # ------------------------------------------------------------------ layout
    def create_header(self):
        header = tk.Frame(self.main_container, bg="#e3f2fd", height=100)
        header.pack(fill=tk.X, padx=20, pady=(20, 0))
        header.pack_propagate(False)
        logo_frame = tk.Frame(header, bg="#e3f2fd")
        logo_frame.pack(side=tk.LEFT, padx=20, pady=10)
        logo_canvas = tk.Canvas(logo_frame, width=60, height=60, bg="#e3f2fd", highlightthickness=0)
        logo_canvas.pack(side=tk.LEFT)
        logo_canvas.create_oval(5, 5, 55, 55, fill="#4a90e2", outline="")
        logo_canvas.create_text(30, 30, text="⚡", font=("Arial", 24), fill="white")
        tk.Label(logo_frame, text="Gomuku", font=("Arial", 32, "bold"), bg="#e3f2fd",
                 fg="#1a1a1a").pack(side=tk.LEFT, padx=15)
        nav_frame = tk.Frame(header, bg="#e3f2fd")
        nav_frame.pack(side=tk.RIGHT, padx=20, pady=10)
        nav_buttons = [
            ("Home", self.go_home),
            ("Single Player", lambda: self._teardown_and(self.open_single_cb)),
            ("Player Vs Player", lambda: self._teardown_and(self.open_pvp_cb)),
            ("AI Vs AI", None),
            ("How To Play", lambda: self._teardown_and(self.open_how_cb)),
        ]
        for text, cmd in nav_buttons:
            btn = tk.Button(nav_frame, text=text, font=("Arial", 12, "bold"), bg="#e3f2fd", fg="#1a1a1a",
                            relief=tk.FLAT, cursor="hand2", padx=10, pady=10, borderwidth=0, command=cmd)
            btn.pack(side=tk.LEFT, padx=4)
            if cmd is None:
                btn.config(font=("Arial", 12, "bold underline"))
            else:
                btn.bind("<Enter>", lambda e, b=btn: b.config(fg="#4a90e2"))
                btn.bind("<Leave>", lambda e, b=btn: b.config(fg="#1a1a1a"))

    def create_controls(self):
        bar = tk.Frame(self.main_container, bg="#f0f4f8")
        bar.pack(pady=(16, 0))
        self.black_var = tk.StringVar(value="Medium")
        self.white_var = tk.StringVar(value="Hard")
        for label, var in (("Black:", self.black_var), ("White:", self.white_var)):
            tk.Label(bar, text=label, font=("Arial", 12, "bold"), bg="#f0f4f8",
                     fg="#2c3e50").pack(side=tk.LEFT, padx=(12, 4))
            menu = tk.OptionMenu(bar, var, *AGENT_CHOICES)
            menu.config(font=("Arial", 11), bg="white", width=8)
            menu.pack(side=tk.LEFT)
        tk.Label(bar, text="Delay (ms):", font=("Arial", 12, "bold"), bg="#f0f4f8",
                 fg="#2c3e50").pack(side=tk.LEFT, padx=(16, 4))
        self.delay_var = tk.IntVar(value=300)
        tk.Scale(bar, from_=0, to=1500, resolution=100, orient=tk.HORIZONTAL, variable=self.delay_var,
                 length=140, bg="#f0f4f8", highlightthickness=0).pack(side=tk.LEFT)
        for text, cmd, color in (("Start", self.start, "#42a5f5"), ("Pause", self.pause, "#78909c"),
                                 ("Reset", self.reset, "#455a64")):
            tk.Button(bar, text=text, command=cmd, font=("Arial", 11, "bold"), bg=color, fg="white",
                      relief=tk.FLAT, cursor="hand2", padx=18, pady=6, borderwidth=0).pack(side=tk.LEFT, padx=4)

    def create_body(self):
        body = tk.Frame(self.main_container, bg="#f0f4f8")
        body.pack(pady=16)
        board_frame = tk.Frame(body, bg="#c9b18f", highlightthickness=2, highlightbackground="#a89070")
        board_frame.pack(side=tk.LEFT, padx=(0, 20))
        self.canvas = tk.Canvas(board_frame, width=478, height=478, bg="#d4a574", highlightthickness=0)
        self.canvas.pack(padx=5, pady=5)
        end = MARGIN + 14 * CELL
        for i in range(15):
            x = MARGIN + i * CELL
            self.canvas.create_line(x, MARGIN, x, end, fill="#8b6f47")
            self.canvas.create_line(MARGIN, x, end, x, fill="#8b6f47")
        for i, j in [(3, 3), (3, 11), (7, 7), (11, 3), (11, 11)]:
            x, y = MARGIN + j * CELL, MARGIN + i * CELL
            self.canvas.create_oval(x - 3, y - 3, x + 3, y + 3, fill="#8b6f47", outline="")

        panel = tk.Frame(body, bg="white", highlightthickness=1, highlightbackground="#e0e0e0")
        panel.pack(side=tk.LEFT, fill=tk.Y)
        self.status = tk.Label(panel, text="Choose two agents and press Start", font=("Arial", 13, "bold"),
                               bg="white", fg="#2c3e50", wraplength=320, justify=tk.LEFT)
        self.status.pack(anchor="w", padx=16, pady=(16, 8))
        self.side_labels = {}
        for color in ("black", "white"):
            box = tk.Frame(panel, bg="#f7f9fb", highlightthickness=1, highlightbackground="#e0e0e0")
            box.pack(fill=tk.X, padx=16, pady=6)
            lbl = tk.Label(box, text="", font=("Arial", 10), bg="#f7f9fb", fg="#4a4a4a",
                           justify=tk.LEFT, anchor="w", wraplength=320)
            lbl.pack(fill=tk.X, padx=10, pady=8)
            self.side_labels[color] = lbl
        tk.Label(panel, text="Move log", font=("Arial", 11, "bold"), bg="white",
                 fg="#2c3e50").pack(anchor="w", padx=16, pady=(8, 2))
        self.log_box = tk.Listbox(panel, width=52, height=12, font=("Consolas", 9), borderwidth=0,
                                  highlightthickness=1, highlightbackground="#e0e0e0")
        self.log_box.pack(padx=16, pady=(0, 16))
        self._refresh_side_labels()

    # ------------------------------------------------------------------ game loop
    def start(self):
        if self.game_over:
            self.reset()
        if not self.agents:
            self.agents = {"black": make_agent(self.black_var.get()), "white": make_agent(self.white_var.get())}
            self.totals = {c: {"moves": 0, "nodes": 0, "ms": 0.0, "last": ""} for c in ("black", "white")}
            self.started_at = datetime.now()
        self.running = True
        self.status.config(text=f"{AGENT_LABELS[self.black_var.get()]} (Black) vs "
                                f"{AGENT_LABELS[self.white_var.get()]} (White)")
        self._step()

    def pause(self):
        self.running = False

    def reset(self):
        self.running = False
        self.game_over = False
        self.agents = {}
        self.totals = {}
        self.move_log = []
        self.current = "black"
        self.state = [[None] * 15 for _ in range(15)]
        self.canvas.delete("stone")
        self.log_box.delete(0, tk.END)
        self.status.config(text="Choose two agents and press Start")
        self._refresh_side_labels()

    def _step(self):
        if not self.running or self.thinking or self.game_over:
            return
        color = self.current
        agent = self.agents[color]
        board = [row[:] for row in self.state]
        self.thinking = True
        generation = id(self.agents)

        result = {}

        def worker():
            result["move"] = agent.choose_move(board, color)

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

        def poll():
            # Tk is not thread-safe, so the main thread polls for the worker's result
            if thread.is_alive():
                self.root.after(20, poll)
            else:
                self._apply(result.get("move"), color, agent.stats, generation)

        poll()

    def _apply(self, move, color, stats, generation):
        self.thinking = False
        if generation != id(self.agents) or not self.main_container.winfo_exists():
            return  # game was reset while the agent was thinking
        if move is None:
            self._finish("Draw")
            return
        r, c = move
        self.state[r][c] = color
        self._draw_stone(r, c, color, len(self.move_log) + 1)
        t = self.totals[color]
        t["moves"] += 1
        t["nodes"] += stats.nodes
        t["ms"] += stats.time_ms
        t["last"] = stats.reason
        self.move_log.append({"move_no": len(self.move_log) + 1, "player": color, "agent": stats.agent,
                              "row": r, "col": c, "nodes": stats.nodes, "depth": stats.depth,
                              "time_ms": round(stats.time_ms, 1), "reason": stats.reason})
        self.log_box.insert(tk.END, f"{len(self.move_log):>3}. {color[0].upper()} {chr(65 + c)}{r + 1:<3} "
                                    f"{stats.nodes:>6} st {stats.time_ms:>6.0f}ms  {stats.reason}")
        self.log_box.see(tk.END)
        self._refresh_side_labels()

        if is_five(self.state, r, c, color):
            for rr, cc in winning_line(self.state, r, c):
                x, y = MARGIN + cc * CELL, MARGIN + rr * CELL
                self.canvas.create_oval(x - 15, y - 15, x + 15, y + 15, outline="#e34948", width=3, tags="stone")
            self._finish(color)
            return
        if is_full(self.state):
            self._finish("Draw")
            return
        self.current = "white" if color == "black" else "black"
        self.root.after(self.delay_var.get(), self._step)

    def _finish(self, winner):
        self.running = False
        self.game_over = True
        if winner == "Draw":
            text = f"Draw after {len(self.move_log)} moves"
        else:
            name = AGENT_LABELS[(self.black_var if winner == "black" else self.white_var).get()]
            text = f"{name} ({winner.title()}) wins in {len(self.move_log)} moves"
        path = self._export_csv(winner)
        self.status.config(text=text + (f"\nSaved to {path}" if path else ""))

    def _draw_stone(self, r, c, color, number):
        x, y = MARGIN + c * CELL, MARGIN + r * CELL
        fill, outline, ink = ("#1a1a1a", "#000000", "white") if color == "black" else ("white", "#d0d0d0", "#1a1a1a")
        self.canvas.create_oval(x - 12, y - 12, x + 12, y + 12, fill=fill, outline=outline, width=2, tags="stone")
        self.canvas.create_text(x, y, text=str(number), fill=ink, font=("Arial", 7), tags="stone")

    def _refresh_side_labels(self):
        for color in ("black", "white"):
            var = self.black_var if color == "black" else self.white_var
            name = AGENT_LABELS[var.get()]
            t = self.totals.get(color)
            if not t or not t["moves"]:
                text = f"{color.title()}: {name}\n{DIFFICULTIES.get(var.get(), 'Plain minimax, depth 2')}"
            else:
                text = (f"{color.title()}: {name}\n"
                        f"Moves: {t['moves']}   States/move: {t['nodes'] / t['moves']:,.0f}   "
                        f"Avg time: {t['ms'] / t['moves']:,.0f} ms\nLast: {t['last']}")
            self.side_labels[color].config(text=text)

    def _export_csv(self, winner):
        try:
            folder = os.path.join("games", "ai_vs_ai")
            os.makedirs(folder, exist_ok=True)
            path = os.path.join(folder, f"game_aivsai_{datetime.now():%Y%m%d_%H%M%S}.csv")
            with open(path, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["mode", "winner", "started_at", "black_agent", "white_agent"])
                w.writerow(["ai_vs_ai", winner, self.started_at.isoformat() if self.started_at else "",
                            AGENT_LABELS[self.black_var.get()], AGENT_LABELS[self.white_var.get()]])
                w.writerow([])
                fields = ["move_no", "player", "agent", "row", "col", "nodes", "depth", "time_ms", "reason"]
                w.writerow(fields)
                for m in self.move_log:
                    w.writerow([m[k] for k in fields])
            return path
        except OSError:
            return ""

    # ------------------------------------------------------------------ navigation
    def _teardown_and(self, action):
        self.running = False
        try:
            self.main_container.destroy()
        except Exception:
            pass
        action()

    def go_home(self):
        self._teardown_and(self.back_callback)

    def destroy(self):
        self.running = False
        self.main_container.destroy()
