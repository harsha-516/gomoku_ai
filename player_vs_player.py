import tkinter as tk
from tkinter import messagebox
import csv
import os
from datetime import datetime
import threading
from suggestion_overlay import SuggestionOverlay, compute_suggestions
from gomoku_coach import summarize_gomoku_game, analyze_game_rule_based
from gomoku_ml_coach import coach_reply, retrain_model_if_needed

class GomokuPvPPage:
    def __init__(self, root, back_callback, open_single_cb, open_pvp_cb, open_how_cb):
        self.root = root
        self.back_callback = back_callback
        self.open_single_cb = open_single_cb
        self.open_pvp_cb = open_pvp_cb
        self.open_how_cb = open_how_cb
        self.game_started = False
        self.timer_seconds = 0
        self.timer_running = False
        self.board = [[None for _ in range(15)] for _ in range(15)]
        # Logical state grid to track colors for suggestions and analysis
        self.state = [[None for _ in range(15)] for _ in range(15)]
        self.current_player = "black"
        self.player1_color = None
        self.player2_color = None
        self.move_log = []
        self.game_started_at = None

        self.main_container = tk.Frame(root, bg="#f0f4f8")
        self.main_container.pack(fill=tk.BOTH, expand=True)

        self.create_header()
        self.create_scrollable_content()
        self.create_game_board()
        self.create_player_info()
        self.create_control_buttons()

    def create_scrollable_content(self):
        container = tk.Frame(self.main_container, bg="#f0f4f8")
        container.pack(fill=tk.BOTH, expand=True)
        self.content_canvas = tk.Canvas(container, bg="#f0f4f8", highlightthickness=0)
        vscroll = tk.Scrollbar(container, orient=tk.VERTICAL, command=self.content_canvas.yview)
        self.content_canvas.configure(yscrollcommand=vscroll.set)
        vscroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.content_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.content_frame = tk.Frame(self.content_canvas, bg="#f0f4f8")
        self.content_window = self.content_canvas.create_window((0, 0), window=self.content_frame, anchor="nw")
        def _on_frame_configure(event):
            self.content_canvas.configure(scrollregion=self.content_canvas.bbox("all"))
        def _on_canvas_configure(event):
            self.content_canvas.itemconfigure(self.content_window, width=event.width)
        self.content_frame.bind("<Configure>", _on_frame_configure)
        self.content_canvas.bind("<Configure>", _on_canvas_configure)

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
        title_label = tk.Label(logo_frame, text="Gomuku", font=("Arial", 32, "bold"), bg="#e3f2fd", fg="#1a1a1a")
        title_label.pack(side=tk.LEFT, padx=15)
        nav_frame = tk.Frame(header, bg="#e3f2fd")
        nav_frame.pack(side=tk.RIGHT, padx=20, pady=10)
        nav_buttons = [
            ("Home", self.go_home),
            ("Single Player", self._nav_to_single),
            ("Player Vs Player", self._nav_to_pvp),
            ("How To Play", self._nav_to_how)
        ]
        for btn_text, cmd in nav_buttons:
            underline = -1
            if btn_text == "Player Vs Player":
                underline = 0
            btn = tk.Button(nav_frame, text=btn_text, font=("Arial", 12, "bold"), bg="#e3f2fd", fg="#1a1a1a", relief=tk.FLAT, cursor="hand2", padx=20, pady=10, borderwidth=0, command=cmd)
            btn.pack(side=tk.LEFT, padx=10)
            if underline >= 0:
                btn.config(font=("Arial", 12, "bold underline"))
            else:
                btn.bind("<Enter>", lambda e, b=btn: b.config(fg="#4a90e2"))
                btn.bind("<Leave>", lambda e, b=btn: b.config(fg="#1a1a1a"))

    def _teardown_and(self, action):
        self.timer_running = False
        try:
            self.main_container.destroy()
        except Exception:
            pass
        action()

    def _nav_to_single(self):
        self._teardown_and(self.open_single_cb)

    def _nav_to_pvp(self):
        self._teardown_and(self.open_pvp_cb)

    def _nav_to_how(self):
        self._teardown_and(self.open_how_cb)

    def create_game_board(self):
        # Horizontal play area: board (left) + side panel (right)
        self.play_area = tk.Frame(self.content_frame, bg="#f0f4f8")
        self.play_area.pack(pady=30, fill=tk.X)
        
        # Center container grows to keep board centered
        center_container = tk.Frame(self.play_area, bg="#f0f4f8")
        center_container.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Board container inside center container, anchored center
        board_container = tk.Frame(center_container, bg="#f0f4f8")
        board_container.pack(anchor="center")
        board_frame = tk.Frame(board_container, bg="#c9b18f", highlightthickness=2, highlightbackground="#a89070")
        board_frame.pack()
        self.board_canvas = tk.Canvas(board_frame, width=510, height=510, bg="#d4a574", highlightthickness=0)
        self.board_canvas.pack(padx=5, pady=5)
        self.draw_grid()
        self.create_start_overlay()
        self.board_canvas.bind("<Button-1>", self.on_board_click)

        # Suggestions overlay helper
        self.suggestion_overlay = SuggestionOverlay(self.board_canvas, cell_size=32, margin=15)

    def draw_grid(self):
        cell_size = 32
        margin = 15
        for i in range(15):
            x = margin + i * cell_size
            self.board_canvas.create_line(x, margin, x, 495 - margin, fill="#8b6f47", width=1)
            self.board_canvas.create_line(margin, x, 495 - margin, x, fill="#8b6f47", width=1)
        star_points = [(3, 3), (3, 11), (7, 7), (11, 3), (11, 11)]
        for i, j in star_points:
            x = margin + j * cell_size
            y = margin + i * cell_size
            self.board_canvas.create_oval(x-3, y-3, x+3, y+3, fill="#8b6f47", outline="")

    def create_start_overlay(self):
        self.overlay = self.board_canvas.create_rectangle(130, 180, 380, 330, fill="white", outline="")
        self.overlay_title = self.board_canvas.create_text(255, 215, text="Ready to Play?", font=("Arial", 24, "bold"), fill="#2c3e50")
        self.overlay_subtitle = self.board_canvas.create_text(255, 250, text="Click the button below to start the game", font=("Arial", 11), fill="#7f8c8d")
        self.start_btn_bg = self.board_canvas.create_rectangle(180, 275, 330, 315, fill="#42a5f5", outline="")
        self.start_btn_text = self.board_canvas.create_text(255, 295, text="Start Game", font=("Arial", 14, "bold"), fill="white")
        self.board_canvas.tag_bind(self.start_btn_bg, "<Button-1>", self.start_game)
        self.board_canvas.tag_bind(self.start_btn_text, "<Button-1>", self.start_game)
        self.board_canvas.tag_bind(self.start_btn_bg, "<Enter>", lambda e: self.board_canvas.itemconfig(self.start_btn_bg, fill="#1e88e5"))
        self.board_canvas.tag_bind(self.start_btn_bg, "<Leave>", lambda e: self.board_canvas.itemconfig(self.start_btn_bg, fill="#42a5f5"))
        self.board_canvas.config(cursor="arrow")

    def start_game(self, event=None):
        self.board_canvas.delete(self.overlay)
        self.board_canvas.delete(self.overlay_title)
        self.board_canvas.delete(self.overlay_subtitle)
        self.board_canvas.delete(self.start_btn_bg)
        self.board_canvas.delete(self.start_btn_text)
        self.game_started = True
        self.timer_running = True
        self.start_timer()
        self.timer_label.config(text="00:00")
        self.click_start_label.pack_forget()
        self.show_color_overlay()
        self.game_started_at = datetime.now()

    def show_color_overlay(self):
        self.color_overlay = self.board_canvas.create_rectangle(110, 165, 400, 345, fill="white", outline="")
        self.color_title = self.board_canvas.create_text(255, 195, text="Player 1: Choose color", font=("Arial", 20, "bold"), fill="#2c3e50")
        self.color_black_bg = self.board_canvas.create_rectangle(155, 230, 255, 270, fill="#1a1a1a", outline="")
        self.color_black_text = self.board_canvas.create_text(205, 250, text="Black", font=("Arial", 12, "bold"), fill="white")
        self.color_white_bg = self.board_canvas.create_rectangle(255, 230, 355, 270, fill="#f5f5f5", outline="#e0e0e0")
        self.color_white_text = self.board_canvas.create_text(305, 250, text="White", font=("Arial", 12, "bold"), fill="#2c3e50")
        self.board_canvas.tag_bind(self.color_black_bg, "<Button-1>", lambda e: self.select_color("black"))
        self.board_canvas.tag_bind(self.color_black_text, "<Button-1>", lambda e: self.select_color("black"))
        self.board_canvas.tag_bind(self.color_white_bg, "<Button-1>", lambda e: self.select_color("white"))
        self.board_canvas.tag_bind(self.color_white_text, "<Button-1>", lambda e: self.select_color("white"))
        self.board_canvas.tag_bind(self.color_black_bg, "<Enter>", lambda e: self.board_canvas.itemconfig(self.color_black_bg, fill="#000000"))
        self.board_canvas.tag_bind(self.color_black_bg, "<Leave>", lambda e: self.board_canvas.itemconfig(self.color_black_bg, fill="#1a1a1a"))
        self.board_canvas.tag_bind(self.color_white_bg, "<Enter>", lambda e: self.board_canvas.itemconfig(self.color_white_bg, fill="#ffffff"))
        self.board_canvas.tag_bind(self.color_white_bg, "<Leave>", lambda e: self.board_canvas.itemconfig(self.color_white_bg, fill="#f5f5f5"))

    def hide_color_overlay(self):
        for item in [getattr(self, 'color_overlay', None), getattr(self, 'color_title', None), getattr(self, 'color_black_bg', None), getattr(self, 'color_black_text', None), getattr(self, 'color_white_bg', None), getattr(self, 'color_white_text', None)]:
            if item:
                self.board_canvas.delete(item)

    def select_color(self, color):
        self.player1_color = color
        self.player2_color = "white" if color == "black" else "black"
        self.current_player = "black"
        self.hide_color_overlay()
        self.update_indicator_colors()

    def create_player_info(self):
        # Side panel to the right of the board
        self.info_container = tk.Frame(self.play_area, bg="white", highlightthickness=1, highlightbackground="#e0e0e0")
        self.info_container.pack(side=tk.RIGHT, padx=(0, 10), pady=5, anchor="n")
        inner_frame = tk.Frame(self.info_container, bg="white")
        inner_frame.pack(padx=20, pady=20)
        # Player 1 (top)
        p1_frame = tk.Frame(inner_frame, bg="white")
        p1_frame.pack(side=tk.TOP)
        p1_icon = tk.Label(p1_frame, text="👤", font=("Arial", 24), bg="white", fg="#757575")
        p1_icon.pack()
        p1_label = tk.Label(p1_frame, text="Player 1", font=("Arial", 12, "bold"), bg="white", fg="#2c3e50")
        p1_label.pack()
        self.p1_stone_canvas = tk.Canvas(p1_frame, width=30, height=30, bg="white", highlightthickness=0)
        self.p1_stone_canvas.pack(pady=5)
        self.p1_stone_canvas.create_oval(3, 3, 27, 27, fill="#1a1a1a", outline="#000000", width=2)
        # Timer (middle)
        timer_frame = tk.Frame(inner_frame, bg="white")
        timer_frame.pack(side=tk.TOP, pady=10)
        clock_label = tk.Label(timer_frame, text="🕐", font=("Arial", 24), bg="white")
        clock_label.pack()
        self.timer_label = tk.Label(timer_frame, text="00:00", font=("Arial", 18, "bold"), bg="white", fg="#2c3e50")
        self.timer_label.pack()
        self.click_start_label = tk.Label(timer_frame, text="Click Start Game", font=("Arial", 10), bg="white", fg="#42a5f5")
        self.click_start_label.pack()
        # Player 2 (bottom)
        p2_frame = tk.Frame(inner_frame, bg="white")
        p2_frame.pack(side=tk.TOP, pady=(10, 0))
        p2_icon = tk.Label(p2_frame, text="👤", font=("Arial", 24), bg="white", fg="#757575")
        p2_icon.pack()
        p2_label = tk.Label(p2_frame, text="Player 2", font=("Arial", 12, "bold"), bg="white", fg="#2c3e50")
        p2_label.pack()
        self.p2_stone_canvas = tk.Canvas(p2_frame, width=30, height=30, bg="white", highlightthickness=0)
        self.p2_stone_canvas.pack(pady=5)
        self.p2_stone_canvas.create_oval(3, 3, 27, 27, fill="white", outline="#d0d0d0", width=2)

    def update_indicator_colors(self):
        def _apply(canvas, color):
            canvas.delete("all")
            fill = "#1a1a1a" if color == "black" else "white"
            outline = "#000000" if color == "black" else "#d0d0d0"
            canvas.create_oval(3, 3, 27, 27, fill=fill, outline=outline, width=2)
        _apply(self.p1_stone_canvas, self.player1_color or "black")
        _apply(self.p2_stone_canvas, self.player2_color or "white")

    def create_control_buttons(self):
        # Controls below the side card - vertical layout
        controls_frame = tk.Frame(self.info_container, bg="#f0f4f8")
        controls_frame.pack(pady=(0, 10))
        restart_btn = tk.Button(controls_frame, text="Restart", font=("Arial", 12, "bold"), bg="#455a64", fg="white", relief=tk.FLAT, cursor="hand2", padx=40, pady=10, borderwidth=0, command=self.restart_game)
        restart_btn.pack(pady=5, fill=tk.X)
        restart_btn.bind("<Enter>", lambda e: restart_btn.config(bg="#37474f"))
        restart_btn.bind("<Leave>", lambda e: restart_btn.config(bg="#455a64"))

        # Suggestions button
        sugg_btn = tk.Button(controls_frame, text="Suggest", font=("Arial", 12, "bold"), bg="#42a5f5", fg="white", relief=tk.FLAT, cursor="hand2", padx=40, pady=10, borderwidth=0, command=self.show_suggestions)
        sugg_btn.pack(pady=5, fill=tk.X)
        sugg_btn.bind("<Enter>", lambda e: sugg_btn.config(bg="#1e88e5"))
        sugg_btn.bind("<Leave>", lambda e: sugg_btn.config(bg="#42a5f5"))

    def on_board_click(self, event):
        if not self.game_started:
            return
        if not self.player1_color:
            return
        cell_size = 32
        margin = 15
        col = round((event.x - margin) / cell_size)
        row = round((event.y - margin) / cell_size)
        if 0 <= row < 15 and 0 <= col < 15 and self.board[row][col] is None:
            mover_color = self.current_player
            self.place_stone(row, col, mover_color)
            if self.check_winner(row, col):
                self.timer_running = False
                winner = "Player 1" if mover_color == self.player1_color else "Player 2"
                messagebox.showinfo("Game Over", f"{winner} won")
                self._finalize_game(winner)
                return
            self.current_player = "white" if self.current_player == "black" else "black"

    def place_stone(self, row, col, color):
        cell_size = 32
        margin = 15
        x = margin + col * cell_size
        y = margin + row * cell_size
        fill = "#1a1a1a" if color == "black" else "white"
        outline = "#000000" if color == "black" else "#d0d0d0"
        stone = self.board_canvas.create_oval(x-12, y-12, x+12, y+12, fill=fill, outline=outline, width=2)
        self.board[row][col] = stone
        self.state[row][col] = color
        elapsed = getattr(self, 'timer_seconds', 0)
        self.move_log.append({
            "move_no": len(self.move_log) + 1,
            "player": color,
            "row": row,
            "col": col,
            "elapsed_seconds": elapsed,
        })

    def check_winner(self, row, col):
        directions = [(0, 1), (1, 0), (1, 1), (1, -1)]
        for dx, dy in directions:
            count = 1
            r, c = row + dx, col + dy
            while 0 <= r < 15 and 0 <= c < 15 and self.board[r][c] is not None:
                count += 1
                r += dx
                c += dy
            r, c = row - dx, col - dy
            while 0 <= r < 15 and 0 <= c < 15 and self.board[r][c] is not None:
                count += 1
                r -= dx
                c -= dy
            if count >= 5:
                return True
        return False

    def start_timer(self):
        if self.timer_running:
            self.timer_seconds += 1
            minutes = self.timer_seconds // 60
            seconds = self.timer_seconds % 60
            self.timer_label.config(text=f"{minutes:02d}:{seconds:02d}")
            self.root.after(1000, self.start_timer)

    def restart_game(self):
        for row in range(15):
            for col in range(15):
                if self.board[row][col] is not None:
                    self.board_canvas.delete(self.board[row][col])
                    self.board[row][col] = None
                self.state[row][col] = None
        self.current_player = "black"
        self.timer_seconds = 0
        self.timer_running = True
        self.game_started = True
        self.timer_label.config(text="00:00")
        # Start timer loop again
        self.start_timer()
        # Ask players for colors again
        self.show_color_overlay()
        # Hide any active suggestions
        if hasattr(self, 'suggestion_overlay'):
            self.suggestion_overlay.hide()
        self.move_log = []
        self.game_started_at = datetime.now()

    def undo_move(self):
        for row in range(14, -1, -1):
            for col in range(14, -1, -1):
                if self.board[row][col] is not None:
                    self.board_canvas.delete(self.board[row][col])
                    self.board[row][col] = None
                    self.state[row][col] = None
                    self.current_player = "white" if self.current_player == "black" else "black"
                    return

    def go_home(self):
        self.timer_running = False
        self.destroy()
        self.back_callback()

    def _export_csv(self, winner: str) -> str:
        try:
            os.makedirs("games", exist_ok=True)
        except Exception:
            pass
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        fname = f"games/game_pvp_{ts}.csv"
        try:
            # Pre-compute analysis for each color perspective
            analysis_black = analyze_game_rule_based(
                move_log=self.move_log,
                final_state=self.state,
                perspective="black",
                winner=winner,
                mode="player_vs_player",
            )
            analysis_white = analyze_game_rule_based(
                move_log=self.move_log,
                final_state=self.state,
                perspective="white",
                winner=winner,
                mode="player_vs_player",
            )

            events_black = {}
            for ev in analysis_black.get("mistake_events", []) + analysis_black.get("good_events", []):
                events_black[ev["move_no"]] = ev

            events_white = {}
            for ev in analysis_white.get("mistake_events", []) + analysis_white.get("good_events", []):
                events_white[ev["move_no"]] = ev

            with open(fname, mode="w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["mode", "winner", "started_at"]) 
                w.writerow(["player_vs_player", winner, (self.game_started_at.isoformat() if self.game_started_at else "")])
                w.writerow([])
                # Extended header with analysis columns
                w.writerow([
                    "move_no",
                    "player_color",
                    "row",
                    "col",
                    "elapsed_seconds",
                    "good_move",
                    "missed_win",
                    "missed_block",
                    "weak_edge",
                    "low_value",
                    "risky_move",
                    "forced_move",
                ])
                for idx, m in enumerate(self.move_log, start=1):
                    player = m["player"]  # 'black' or 'white'
                    row = m["row"]
                    col = m["col"]
                    tsec = m["elapsed_seconds"]

                    good_move = missed_win = missed_block = weak_edge = low_value = risky_move = forced_move = 0

                    # Pick the right perspective map based on mover color
                    if player == "black":
                        ev = events_black.get(idx)
                    else:
                        ev = events_white.get(idx)

                    if ev:
                        labels = ev.get("labels", [])
                        played_kind = ev.get("played_kind")

                        missed_win = 1 if "missed_win" in labels else 0
                        missed_block = 1 if "missed_block" in labels else 0
                        weak_edge = 1 if "weak_edge" in labels else 0
                        low_value = 1 if "low_value" in labels else 0
                        if "strong_move" in labels and not any(
                            lab in ("missed_win", "missed_block", "weak_edge", "low_value") for lab in labels
                        ):
                            good_move = 1
                        if played_kind == "block":
                            forced_move = 1
                        if low_value and not missed_win and not missed_block:
                            risky_move = 1

                    w.writerow([
                        idx,
                        player,
                        row,
                        col,
                        tsec,
                        good_move,
                        missed_win,
                        missed_block,
                        weak_edge,
                        low_value,
                        risky_move,
                        forced_move,
                    ])
        except Exception:
            return ""
        return fname

    def _analyze_game(self):
        # Use the shared rule-based coach for both players
        p1_col = self.player1_color or "black"
        p2_col = self.player2_color or "white"
        analysis_p1 = analyze_game_rule_based(
            move_log=self.move_log,
            final_state=self.state,
            perspective=p1_col,
            winner=None,
            mode="player_vs_player",
        )
        analysis_p2 = analyze_game_rule_based(
            move_log=self.move_log,
            final_state=self.state,
            perspective=p2_col,
            winner=None,
            mode="player_vs_player",
        )
        return analysis_p1, analysis_p2

    def _finalize_game(self, winner: str):
        """Show game summary with both rule-based and ML coaching."""
        csv_path = self._export_csv(winner)
        p1_col = self.player1_color or "black"
        p2_col = self.player2_color or "white"

        # Get rule-based analyses
        analysis_p1 = analyze_game_rule_based(
            move_log=self.move_log,
            final_state=self.state,
            perspective=p1_col,
            winner=winner,
            mode="player_vs_player",
        )
        analysis_p2 = analyze_game_rule_based(
            move_log=self.move_log,
            final_state=self.state,
            perspective=p2_col,
            winner=winner,
            mode="player_vs_player",
        )

        report_p1 = summarize_gomoku_game(
            move_log=self.move_log,
            final_state=self.state,
            perspective=p1_col,
            winner=winner,
            mode="player_vs_player",
        )
        report_p2 = summarize_gomoku_game(
            move_log=self.move_log,
            final_state=self.state,
            perspective=p2_col,
            winner=winner,
            mode="player_vs_player",
        )

        # Get ML-based coaching stories
        ml_story_p1 = None
        ml_story_p2 = None
        try:
            threading.Thread(target=lambda: retrain_model_if_needed(games_folder="games", min_games=2), daemon=True).start()
            if csv_path:
                ml_story_p1 = coach_reply(csv_path, winner=winner)
                ml_story_p2 = coach_reply(csv_path, winner=winner)
        except Exception as e:
            print(f"ML coach error: {e}")

        mistakes_p1 = {e["move_no"]: e for e in analysis_p1.get("mistake_events", [])}
        mistakes_p2 = {e["move_no"]: e for e in analysis_p2.get("mistake_events", [])}

        # Build summary window with tabs
        win = tk.Toplevel(self.root)
        win.title("Game Summary")
        win.geometry("1100x750")

        container = tk.Frame(win)
        container.pack(fill=tk.BOTH, expand=True)

        # Tab frame
        tab_frame = tk.Frame(container, bg="#e0e0e0", height=40)
        tab_frame.pack(fill=tk.X, padx=0, pady=0)
        tab_frame.pack_propagate(False)

        rule_btn = tk.Button(tab_frame, text="Rule-Based Coach", font=("Arial", 11, "bold"), bg="#42a5f5", fg="white", relief=tk.FLAT, padx=20, pady=8)
        rule_btn.pack(side=tk.LEFT, padx=5, pady=5)

        ml_btn = tk.Button(tab_frame, text="ML Coach", font=("Arial", 11, "bold"), bg="#90caf9", fg="white", relief=tk.FLAT, padx=20, pady=8)
        ml_btn.pack(side=tk.LEFT, padx=5, pady=5)

        content_frame = tk.Frame(container)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        def show_rule_based():
            for widget in content_frame.winfo_children():
                widget.destroy()

            # Title
            tk.Label(content_frame, text=f"Game Over - {winner} won", font=("Arial", 14, "bold")).pack(pady=(0, 10))

            # Two story panels
            stories_frame = tk.Frame(content_frame)
            stories_frame.pack(fill=tk.X, pady=(0, 10))

            p1_story = tk.LabelFrame(stories_frame, text=f"Player 1 view (color: {p1_col})", padx=8, pady=8)
            p1_story.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
            txt1 = tk.Text(p1_story, wrap=tk.WORD, height=8)
            txt1.pack(fill=tk.BOTH, expand=True)
            txt1.insert(tk.END, report_p1)
            txt1.config(state=tk.DISABLED)

            p2_story = tk.LabelFrame(stories_frame, text=f"Player 2 view (color: {p2_col})", padx=8, pady=8)
            p2_story.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0))
            txt2 = tk.Text(p2_story, wrap=tk.WORD, height=8)
            txt2.pack(fill=tk.BOTH, expand=True)
            txt2.insert(tk.END, report_p2)
            txt2.config(state=tk.DISABLED)

            # Move table
            table_frame = tk.LabelFrame(content_frame, text="Move-by-move overview", padx=10, pady=10)
            table_frame.pack(fill=tk.BOTH, expand=True)

            canvas = tk.Canvas(table_frame)
            scrollbar = tk.Scrollbar(table_frame, orient=tk.VERTICAL, command=canvas.yview)
            inner = tk.Frame(canvas)

            inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
            canvas.create_window((0, 0), window=inner, anchor="nw")
            canvas.configure(yscrollcommand=scrollbar.set)
            canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

            headers = ["Move", "Player", "Row", "Col", "Time (s)", "Comment (P1)", "Comment (P2)"]
            for c, h in enumerate(headers):
                tk.Label(inner, text=h, font=("Arial", 10, "bold"), borderwidth=1, relief=tk.SOLID, padx=4, pady=2).grid(row=0, column=c, sticky="nsew")

            for c in range(len(headers)):
                inner.grid_columnconfigure(c, weight=1)

            for idx, m in enumerate(self.move_log, start=1):
                mover = m.get("player")
                r = m.get("row")
                c = m.get("col")
                tsec = m.get("elapsed_seconds", 0)

                def _comment(ev_map):
                    ev = ev_map.get(idx)
                    if not ev:
                        return ""
                    labels = ev.get("labels", [])
                    parts = []
                    if "missed_win" in labels:
                        parts.append("missed a winning move")
                    if "missed_block" in labels:
                        parts.append("missed a critical block")
                    if "weak_edge" in labels:
                        parts.append("weak edge move")
                    if "low_value" in labels:
                        parts.append("low-value move")
                    text = ", ".join(parts).capitalize() if parts else ""
                    better = [f"({br},{bc})" for br, bc, kind in ev.get("better_moves", [])]
                    if better:
                        text += f"; better: {', '.join(better)}"
                    return text

                comment_p1 = _comment(mistakes_p1)
                comment_p2 = _comment(mistakes_p2)

                values = [idx, mover, r, c, tsec, comment_p1, comment_p2]
                for col_idx, val in enumerate(values):
                    tk.Label(inner, text=str(val), font=("Arial", 9), anchor="w", borderwidth=1, relief=tk.SOLID, padx=4, pady=2).grid(row=idx, column=col_idx, sticky="nsew")

        def show_ml_coach():
            for widget in content_frame.winfo_children():
                widget.destroy()

            if not ml_story_p1:
                no_ml = tk.Label(content_frame, text="ML Coach not available yet. Play more games to train the model!", font=("Arial", 12), fg="#666")
                no_ml.pack(pady=50)
                return

            # Two ML story panels
            ml_stories = tk.Frame(content_frame)
            ml_stories.pack(fill=tk.BOTH, expand=True)

            ml_p1 = tk.LabelFrame(ml_stories, text=f"ML Analysis - Player 1 ({p1_col})", padx=8, pady=8)
            ml_p1.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
            txt1 = tk.Text(ml_p1, wrap=tk.WORD, font=("Arial", 10))
            txt1.pack(fill=tk.BOTH, expand=True)
            txt1.insert(tk.END, ml_story_p1 or "No data")
            txt1.config(state=tk.DISABLED)

            ml_p2 = tk.LabelFrame(ml_stories, text=f"ML Analysis - Player 2 ({p2_col})", padx=8, pady=8)
            ml_p2.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0))
            txt2 = tk.Text(ml_p2, wrap=tk.WORD, font=("Arial", 10))
            txt2.pack(fill=tk.BOTH, expand=True)
            txt2.insert(tk.END, ml_story_p2 or "No data")
            txt2.config(state=tk.DISABLED)

        rule_btn.config(command=lambda: [show_rule_based(), rule_btn.config(bg="#42a5f5"), ml_btn.config(bg="#90caf9")])
        ml_btn.config(command=lambda: [show_ml_coach(), ml_btn.config(bg="#42a5f5"), rule_btn.config(bg="#90caf9")])

        show_rule_based()

        btn = tk.Button(container, text="Close", command=win.destroy, font=("Arial", 11, "bold"))
        btn.pack(pady=(0, 10))

    def destroy(self):
        self.main_container.destroy()

    def show_suggestions(self):
        # Toggle: hide if visible
        if hasattr(self, 'suggestion_overlay') and self.suggestion_overlay.is_visible():
            self.suggestion_overlay.hide()
            return
        # Only when game running and colors chosen
        if not self.game_started or not self.player1_color:
            return
        # Current mover color
        mover_color = self.current_player
        suggestions = compute_suggestions(self.state, mover_color, top_k=6)

        def on_pick(r, c):
            if 0 <= r < 15 and 0 <= c < 15 and self.state[r][c] is None:
                color = self.current_player
                self.place_stone(r, c, color)
                if self.check_winner(r, c):
                    self.timer_running = False
                    winner = "Player 1" if color == self.player1_color else "Player 2"
                    messagebox.showinfo("Game Over", f"{winner} won!")
                    return
                self.current_player = "white" if self.current_player == "black" else "black"

        self.suggestion_overlay.show(suggestions, on_select=on_pick, anchor="bottom_left")
