import tkinter as tk
from tkinter import messagebox
import threading
import csv
import os
import time
from datetime import datetime
from gomoku_ai import ai_easy, ai_search, candidate_moves, get_empty_cells
from suggestion_overlay import SuggestionOverlay, compute_suggestions
from gomoku_coach import summarize_gomoku_game, analyze_game_rule_based
from gomoku_ml_coach import coach_reply, retrain_model_if_needed

class GomokuGamePage:
    def __init__(self, root, back_callback, open_single_cb, open_pvp_cb, open_how_cb):
        self.root = root
        self.back_callback = back_callback
        self.open_single_cb = open_single_cb
        self.open_pvp_cb = open_pvp_cb
        self.open_how_cb = open_how_cb
        self.game_started = False
        self.timer_seconds = 0
        self.timer_running = False
        
        # Game state
        self.board = [[None for _ in range(15)] for _ in range(15)]
        # Parallel logical board to track piece colors (None/"black"/"white")
        self.state = [[None for _ in range(15)] for _ in range(15)]
        self.ai_thinking = False
        self.suggestion_timer_id = None
        self.move_log = []
        self.game_started_at = None
        self.current_player = "black"  # Black always starts in Gomoku
        self.player_color = None
        self.computer_color = None
        
        # Inactivity alert system
        self.inactivity_timer_id = None
        self.last_move_time = None
        self.inactivity_alert_shown = False
        
        # Main container
        self.main_container = tk.Frame(root, bg="#f0f4f8")
        self.main_container.pack(fill=tk.BOTH, expand=True)
        
        self.create_header()
        self.create_scrollable_content()
        self.create_difficulty_selector()
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
        # Header frame
        header = tk.Frame(self.main_container, bg="#e3f2fd", height=100)
        header.pack(fill=tk.X, padx=20, pady=(20, 0))
        header.pack_propagate(False)
        
        # Logo and title frame
        logo_frame = tk.Frame(header, bg="#e3f2fd")
        logo_frame.pack(side=tk.LEFT, padx=20, pady=10)
        
        # Create circular logo
        logo_canvas = tk.Canvas(logo_frame, width=60, height=60, 
                               bg="#e3f2fd", highlightthickness=0)
        logo_canvas.pack(side=tk.LEFT)
        logo_canvas.create_oval(5, 5, 55, 55, fill="#4a90e2", outline="")
        logo_canvas.create_text(30, 30, text="⚡", font=("Arial", 24), fill="white")
        
        # Title
        title_label = tk.Label(logo_frame, text="Gomuku", 
                              font=("Arial", 32, "bold"),
                              bg="#e3f2fd", fg="#1a1a1a")
        title_label.pack(side=tk.LEFT, padx=15)
        
        # Navigation buttons
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
            if btn_text == "Single Player":
                underline = 0
            
            btn = tk.Button(nav_frame, text=btn_text, 
                          font=("Arial", 12, "bold"),
                          bg="#e3f2fd", fg="#1a1a1a",
                          relief=tk.FLAT, cursor="hand2",
                          padx=20, pady=10,
                          borderwidth=0,
                          command=cmd)
            btn.pack(side=tk.LEFT, padx=10)
            
            if underline >= 0:
                btn.config(font=("Arial", 12, "bold underline"))
            else:
                btn.bind("<Enter>", lambda e, b=btn: b.config(fg="#4a90e2"))
                btn.bind("<Leave>", lambda e, b=btn: b.config(fg="#1a1a1a"))
        
    def _teardown_and(self, action):
        # Stop timers and teardown UI before navigation
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
        # Horizontal play area: centered board + side panel on right edge
        self.play_area = tk.Frame(self.content_frame, bg="#f0f4f8")
        self.play_area.pack(pady=30, fill=tk.X)
        
        # Center container grows to keep board centered
        center_container = tk.Frame(self.play_area, bg="#f0f4f8")
        center_container.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Board container inside center container, anchored center
        board_container = tk.Frame(center_container, bg="#f0f4f8")
        board_container.pack(anchor="center")
        
        # Board frame with border
        board_frame = tk.Frame(board_container, bg="#c9b18f", 
                              highlightthickness=2, highlightbackground="#a89070")
        board_frame.pack()
        
        # Canvas for the board
        self.board_canvas = tk.Canvas(board_frame, width=510, height=510,
                                     bg="#d4a574", highlightthickness=0)
        self.board_canvas.pack(padx=5, pady=5)
        
        # Draw grid
        self.draw_grid()
        
        # Start game overlay
        self.create_start_overlay()
        
        # Bind click event
        self.board_canvas.bind("<Button-1>", self.on_board_click)

        # Suggestions overlay helper
        self.suggestion_overlay = SuggestionOverlay(self.board_canvas, cell_size=32, margin=15)

    def create_difficulty_selector(self):
        bar = tk.Frame(self.content_frame, bg="#f0f4f8")
        bar.pack(pady=(20, 0))
        label = tk.Label(bar, text="Difficulty:", font=("Arial", 12, "bold"), bg="#f0f4f8", fg="#2c3e50")
        label.pack(side=tk.LEFT, padx=(0, 10))
        self.difficulty_var = tk.StringVar(value="Medium")
        dropdown = tk.OptionMenu(bar, self.difficulty_var, "Easy", "Medium", "Hard")
        dropdown.config(font=("Arial", 12), bg="white")
        dropdown.pack(side=tk.LEFT)
    
    def draw_grid(self):
        # Draw grid lines
        cell_size = 32
        margin = 15
        
        for i in range(15):
            x = margin + i * cell_size
            self.board_canvas.create_line(x, margin, x, 495 - margin, 
                                         fill="#8b6f47", width=1)
            self.board_canvas.create_line(margin, x, 495 - margin, x, 
                                         fill="#8b6f47", width=1)
        
        # Draw star points
        star_points = [(3, 3), (3, 11), (7, 7), (11, 3), (11, 11)]
        for i, j in star_points:
            x = margin + j * cell_size
            y = margin + i * cell_size
            self.board_canvas.create_oval(x-3, y-3, x+3, y+3, fill="#8b6f47", outline="")
    
    def create_start_overlay(self):
        # White overlay box
        self.overlay = self.board_canvas.create_rectangle(100, 180, 400, 330,
                                                         fill="white", outline="")
        
        # Text
        self.overlay_title = self.board_canvas.create_text(255, 230, 
                                                          text="Ready to Play?",
                                                          font=("Arial", 24, "bold"),
                                                          fill="#2c3e50")
        
        self.overlay_subtitle = self.board_canvas.create_text(240, 260,
                                                             text="Click the button below to start the game",
                                                             font=("Arial", 11),
                                                             fill="#7f8c8d")
        
        # Start button
        self.start_btn_bg = self.board_canvas.create_rectangle(180, 275, 330, 315,
                                                               fill="#42a5f5", outline="")
        self.start_btn_text = self.board_canvas.create_text(255, 295,
                                                            text="Start Game",
                                                            font=("Arial", 14, "bold"),
                                                            fill="white")
        
        # Make button clickable
        self.board_canvas.tag_bind(self.start_btn_bg, "<Button-1>", self.start_game)
        self.board_canvas.tag_bind(self.start_btn_text, "<Button-1>", self.start_game)
        self.board_canvas.tag_bind(self.start_btn_bg, "<Enter>", 
                                  lambda e: self.board_canvas.itemconfig(self.start_btn_bg, fill="#1e88e5"))
        self.board_canvas.tag_bind(self.start_btn_bg, "<Leave>", 
                                  lambda e: self.board_canvas.itemconfig(self.start_btn_bg, fill="#42a5f5"))
        self.board_canvas.config(cursor="arrow")
    
    def start_game(self, event=None):
        # Remove overlay
        self.board_canvas.delete(self.overlay)
        self.board_canvas.delete(self.overlay_title)
        self.board_canvas.delete(self.overlay_subtitle)
        self.board_canvas.delete(self.start_btn_bg)
        self.board_canvas.delete(self.start_btn_text)
        
        self.game_started = True
        self.timer_running = True
        self.start_timer()
        
        # Update click start game text
        self.timer_label.config(text="00:00")
        self.click_start_label.pack_forget()
        
        # Ask the player to choose a color
        self.show_color_overlay()
        self.game_started_at = datetime.now()

    def show_color_overlay(self):
        # Draw an overlay on the board canvas similar to the Start Game card
        self.color_overlay = self.board_canvas.create_rectangle(110, 165, 400, 345,
                                                                fill="white", outline="")
        self.color_title = self.board_canvas.create_text(255, 195,
                                                         text="Choose your color",
                                                         font=("Arial", 20, "bold"),
                                                         fill="#2c3e50")
        # Black button
        self.color_black_bg = self.board_canvas.create_rectangle(155, 230, 255, 270,
                                                                 fill="#1a1a1a", outline="")
        self.color_black_text = self.board_canvas.create_text(205, 250,
                                                              text="Black",
                                                              font=("Arial", 12, "bold"),
                                                              fill="white")
        # White button
        self.color_white_bg = self.board_canvas.create_rectangle(255, 230, 355, 270,
                                                                 fill="#f5f5f5", outline="#e0e0e0")
        self.color_white_text = self.board_canvas.create_text(305, 250,
                                                              text="White",
                                                              font=("Arial", 12, "bold"),
                                                              fill="#2c3e50")
        # Bind events
        self.board_canvas.tag_bind(self.color_black_bg, "<Button-1>", lambda e: self.select_color("black"))
        self.board_canvas.tag_bind(self.color_black_text, "<Button-1>", lambda e: self.select_color("black"))
        self.board_canvas.tag_bind(self.color_white_bg, "<Button-1>", lambda e: self.select_color("white"))
        self.board_canvas.tag_bind(self.color_white_text, "<Button-1>", lambda e: self.select_color("white"))
        # Hover effects
        self.board_canvas.tag_bind(self.color_black_bg, "<Enter>",
                                   lambda e: self.board_canvas.itemconfig(self.color_black_bg, fill="#000000"))
        self.board_canvas.tag_bind(self.color_black_bg, "<Leave>",
                                   lambda e: self.board_canvas.itemconfig(self.color_black_bg, fill="#1a1a1a"))
        self.board_canvas.tag_bind(self.color_white_bg, "<Enter>",
                                   lambda e: self.board_canvas.itemconfig(self.color_white_bg, fill="#ffffff"))
        self.board_canvas.tag_bind(self.color_white_bg, "<Leave>",
                                   lambda e: self.board_canvas.itemconfig(self.color_white_bg, fill="#f5f5f5"))

    def hide_color_overlay(self):
        for item in [
            getattr(self, 'color_overlay', None), getattr(self, 'color_title', None),
            getattr(self, 'color_black_bg', None), getattr(self, 'color_black_text', None),
            getattr(self, 'color_white_bg', None), getattr(self, 'color_white_text', None)
        ]:
            if item:
                self.board_canvas.delete(item)

    def select_color(self, color):
        self.set_colors(color)
        self.hide_color_overlay()
        # If computer is to move first (black when player chose white), trigger AI
        if self.current_player == self.computer_color:
            self.root.after(400, self.computer_move)
        else:
            self._schedule_auto_suggestion()
            # Start inactivity monitoring when it's player's turn
            self._start_inactivity_timer()
    
    def create_player_info(self):
        # Player info container
        # Side panel to the right edge of the play area
        self.info_container = tk.Frame(self.play_area, bg="white",
                                 highlightthickness=1, highlightbackground="#e0e0e0")
        self.info_container.pack(side=tk.RIGHT, padx=(0, 10), pady=5, anchor="n")
        
        # Inner frame
        inner_frame = tk.Frame(self.info_container, bg="white")
        inner_frame.pack(padx=20, pady=20)
        
        # You (Player) section
        you_frame = tk.Frame(inner_frame, bg="white")
        you_frame.pack(side=tk.TOP)
        
        you_icon = tk.Label(you_frame, text="👤", font=("Arial", 24),
                           bg="white", fg="#757575")
        you_icon.pack()
        
        you_label = tk.Label(you_frame, text="You", 
                            font=("Arial", 12, "bold"),
                            bg="white", fg="#2c3e50")
        you_label.pack()
        
        self.player_stone_canvas = tk.Canvas(you_frame, width=30, height=30,
                                            bg="white", highlightthickness=0)
        self.player_stone_canvas.pack(pady=5)
        self.player_stone_canvas.create_oval(3, 3, 27, 27, 
                                            fill="#1a1a1a", outline="#000000", width=2)
        
        # Timer section (center)
        # Stack timer vertically below player info
        timer_frame = tk.Frame(inner_frame, bg="white")
        timer_frame.pack(side=tk.TOP, pady=10)
        
        clock_label = tk.Label(timer_frame, text="🕐", font=("Arial", 24),
                              bg="white")
        clock_label.pack()
        
        self.timer_label = tk.Label(timer_frame, text="00:00",
                                   font=("Arial", 18, "bold"),
                                   bg="white", fg="#2c3e50")
        self.timer_label.pack()
        
        self.click_start_label = tk.Label(timer_frame, text="Click Start Game",
                                         font=("Arial", 10),
                                         bg="white", fg="#42a5f5")
        self.click_start_label.pack()
        
        # Computer section
        # Computer section below timer
        computer_frame = tk.Frame(inner_frame, bg="white")
        computer_frame.pack(side=tk.TOP, pady=(10, 0))
        
        computer_icon = tk.Label(computer_frame, text="🤖", font=("Arial", 24),
                                bg="white", fg="#757575")
        computer_icon.pack()
        
        computer_label = tk.Label(computer_frame, text="Computer",
                                 font=("Arial", 12, "bold"),
                                 bg="white", fg="#2c3e50")
        computer_label.pack()
        
        self.computer_stone_canvas = tk.Canvas(computer_frame, width=30, height=30,
                                              bg="white", highlightthickness=0)
        self.computer_stone_canvas.pack(pady=5)
        self.computer_stone_canvas.create_oval(3, 3, 27, 27,
                                              fill="white", outline="#d0d0d0", width=2)

        # Initialize indicator colors if selection already made
        if self.player_color:
            self.update_indicator_colors()

    def set_colors(self, player_color):
        self.player_color = player_color
        self.computer_color = "white" if player_color == "black" else "black"
        # Black always starts
        self.current_player = "black"
        self.update_indicator_colors()

    def update_indicator_colors(self):
        # Update the small stone previews for player and computer
        def _apply(canvas, color):
            canvas.delete("all")
            fill = "#1a1a1a" if color == "black" else "white"
            outline = "#000000" if color == "black" else "#d0d0d0"
            canvas.create_oval(3, 3, 27, 27, fill=fill, outline=outline, width=2)
        _apply(self.player_stone_canvas, self.player_color or "black")
        _apply(self.computer_stone_canvas, self.computer_color or "white")
    
    def create_control_buttons(self):
        # Control buttons container - vertical layout
        controls_frame = tk.Frame(self.info_container, bg="#f0f4f8")
        controls_frame.pack(pady=(0, 10))
        
        # Restart button
        restart_btn = tk.Button(controls_frame, text="Restart",
                               font=("Arial", 12, "bold"),
                               bg="#455a64", fg="white",
                               relief=tk.FLAT, cursor="hand2",
                               padx=40, pady=10,
                               borderwidth=0,
                               command=self.restart_game)
        restart_btn.pack(pady=5, fill=tk.X)
        restart_btn.bind("<Enter>", lambda e: restart_btn.config(bg="#37474f"))
        restart_btn.bind("<Leave>", lambda e: restart_btn.config(bg="#455a64"))

        # Suggestions button
        sugg_btn = tk.Button(controls_frame, text="Suggest",
                             font=("Arial", 12, "bold"),
                             bg="#42a5f5", fg="white",
                             relief=tk.FLAT, cursor="hand2",
                             padx=40, pady=10,
                             borderwidth=0,
                             command=self.show_suggestions)
        sugg_btn.pack(pady=5, fill=tk.X)
        sugg_btn.bind("<Enter>", lambda e: sugg_btn.config(bg="#1e88e5"))
        sugg_btn.bind("<Leave>", lambda e: sugg_btn.config(bg="#42a5f5"))

        # Hotkey to toggle suggestions
        self.root.bind("<Key-s>", lambda e: self.show_suggestions())
    
    def on_board_click(self, event):
        if not self.game_started:
            return
        # Only accept input when it's the player's turn and color chosen
        if not self.player_color or self.current_player != self.player_color or self.ai_thinking:
            return
        
        # Calculate grid position
        cell_size = 32
        margin = 15
        
        col = round((event.x - margin) / cell_size)
        row = round((event.y - margin) / cell_size)
        
        if 0 <= row < 15 and 0 <= col < 15 and self.board[row][col] is None:
            mover_color = self.current_player
            # Hide suggestions and cancel timer when making a move
            if hasattr(self, 'suggestion_overlay') and self.suggestion_overlay.is_visible():
                self.suggestion_overlay.hide()
            self._cancel_suggestion_timer()
            self._cancel_inactivity_timer()  # Cancel inactivity timer on move
            self.place_stone(row, col, mover_color)
            
            # Check for winner
            if self.check_winner(row, col):
                self.timer_running = False
                winner = "You" if mover_color == self.player_color else "Computer"
                self._finalize_game(winner)
                return
            
            # Switch player
            self.current_player = "white" if self.current_player == "black" else "black"
            
            # Computer move (simple random for now)
            if self.current_player == self.computer_color:
                self.root.after(500, self.computer_move)
            else:
                self._schedule_auto_suggestion()
    
    def place_stone(self, row, col, color):
        cell_size = 32
        margin = 15
        
        x = margin + col * cell_size
        y = margin + row * cell_size
        
        fill = "#1a1a1a" if color == "black" else "white"
        outline = "#000000" if color == "black" else "#d0d0d0"
        
        stone = self.board_canvas.create_oval(x-12, y-12, x+12, y+12,
                                             fill=fill, outline=outline, width=2)
        self.board[row][col] = stone
        self.state[row][col] = color
        try:
            elapsed = self.timer_seconds
        except Exception:
            elapsed = 0
        self.move_log.append({
            "move_no": len(self.move_log) + 1,
            "player": color,
            "row": row,
            "col": col,
            "elapsed_seconds": elapsed,
        })
    
    def computer_move(self):
        # Run AI computation in a background thread to keep UI responsive
        if self.ai_thinking:
            return
        self.ai_thinking = True
        # Ensure suggestions don't pop during AI's turn
        self._cancel_suggestion_timer()
        try:
            self.board_canvas.config(cursor="watch")
        except Exception:
            pass

        difficulty = (self.difficulty_var.get() if hasattr(self, 'difficulty_var') else "Medium").strip()
        ai_color = self.computer_color or "white"
        player_color = self.player_color or ("black" if ai_color == "white" else "white")

        def worker():
            if difficulty == "Easy":
                move = ai_easy(self.state, ai_color, player_color)
            elif difficulty == "Hard":
                move = ai_search(self.state, ai_color, player_color, depth=3, use_alpha_beta=True, max_candidates=12)
            else:  # Medium
                move = ai_search(self.state, ai_color, player_color, depth=2, use_alpha_beta=False, max_candidates=10)

            if move is None:
                import random
                empties = get_empty_cells(self.state)
                move = random.choice(empties) if empties else None

            self.root.after(0, lambda: self._apply_ai_move(move, ai_color))

        threading.Thread(target=worker, daemon=True).start()

    def _apply_ai_move(self, move, ai_color):
        if move is not None:
            row, col = move
            # Check still empty (player may undo quickly)
            if self.state[row][col] is None:
                self.place_stone(row, col, ai_color)
                if self.check_winner(row, col):
                    self.timer_running = False
                    self._finalize_game("Computer")
                    self.ai_thinking = False
                    try:
                        self.board_canvas.config(cursor="arrow")
                    except Exception:
                        pass
                    return
                self.current_player = self.player_color or "black"
                # Schedule auto-suggestion for player's turn
                self._schedule_auto_suggestion()
                # Start inactivity monitoring for player's turn
                self._start_inactivity_timer()
        self.ai_thinking = False
        try:
            self.board_canvas.config(cursor="arrow")
        except Exception:
            pass
    
    def check_winner(self, row, col):
        directions = [(0, 1), (1, 0), (1, 1), (1, -1)]
        color = self.state[row][col]
        for dx, dy in directions:
            count = 1
            # forward
            r, c = row + dx, col + dy
            while 0 <= r < 15 and 0 <= c < 15 and self.state[r][c] == color:
                count += 1
                r += dx
                c += dy
            # backward
            r, c = row - dx, col - dy
            while 0 <= r < 15 and 0 <= c < 15 and self.state[r][c] == color:
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
        # Clear board
        for row in range(15):
            for col in range(15):
                if self.board[row][col] is not None:
                    self.board_canvas.delete(self.board[row][col])
                    self.board[row][col] = None
                self.state[row][col] = None
        # Hide suggestions overlay on restart
        if hasattr(self, 'suggestion_overlay'):
            self.suggestion_overlay.hide()
        self._cancel_suggestion_timer()
        
        self.current_player = "black"
        self.timer_seconds = 0
        self.timer_running = True
        self.game_started = True
        self.ai_thinking = False
        self.timer_label.config(text="00:00")
        # Start timer loop
        self.start_timer()

        # Handle color/turn after restart
        if self.player_color is None:
            # Ask again if color not chosen yet
            self.show_color_overlay()
        else:
            # If computer should start (player chose white), trigger AI
            if self.current_player == (self.computer_color or "white"):
                self.root.after(400, self.computer_move)
        self.move_log = []
        self.game_started_at = datetime.now()
    
    def undo_move(self):
        # Find last move and remove it
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
        fname = f"games/game_single_{ts}.csv"
        try:
            # Pre-compute analysis for the human perspective so we can store labels per move
            perspective = self.player_color or "black"
            analysis = analyze_game_rule_based(
                move_log=self.move_log,
                final_state=self.state,
                perspective=perspective,
                winner=winner,
                mode="single_player",
            )
            events = {}
            for ev in analysis.get("mistake_events", []) + analysis.get("good_events", []):
                events[ev["move_no"]] = ev

            with open(fname, mode="w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["mode", "winner", "started_at"])
                w.writerow(["single_player", winner, (self.game_started_at.isoformat() if self.game_started_at else "")])
                w.writerow([])
                # Add analysis columns to the header
                w.writerow([
                    "move_no",
                    "player",
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
                    player = m["player"]
                    row = m["row"]
                    col = m["col"]
                    tsec = m["elapsed_seconds"]

                    # Default flags
                    good_move = missed_win = missed_block = weak_edge = low_value = risky_move = forced_move = 0

                    # Only evaluate from human perspective moves
                    if player == perspective and idx in events:
                        ev = events[idx]
                        labels = ev.get("labels", [])
                        played_kind = ev.get("played_kind")

                        missed_win = 1 if "missed_win" in labels else 0
                        missed_block = 1 if "missed_block" in labels else 0
                        weak_edge = 1 if "weak_edge" in labels else 0
                        low_value = 1 if "low_value" in labels else 0
                        # Good move if explicitly strong and no negative labels
                        if "strong_move" in labels and not any(
                            lab in ("missed_win", "missed_block", "weak_edge", "low_value") for lab in labels
                        ):
                            good_move = 1
                        # Forced move if it was a blocking move
                        if played_kind == "block":
                            forced_move = 1
                        # Risky move: low-value but not also a missed immediate win/block
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
        # Use the shared rule-based coach to analyze from the human player's perspective
        perspective = self.player_color or "black"
        report = summarize_gomoku_game(
            move_log=self.move_log,
            final_state=self.state,
            perspective=perspective,
            winner=None,
            mode="single_player",
        )
        return report

    def _finalize_game(self, winner: str):
        # Save CSV silently for records
        csv_path = self._export_csv(winner)
        perspective = self.player_color or "black"

        # Get narrative report and detailed analysis (rule-based)
        analysis = analyze_game_rule_based(
            move_log=self.move_log,
            final_state=self.state,
            perspective=perspective,
            winner=winner,
            mode="single_player",
        )
        report = summarize_gomoku_game(
            move_log=self.move_log,
            final_state=self.state,
            perspective=perspective,
            winner=winner,
            mode="single_player",
        )

        # Get ML-based coaching story (if available)
        ml_story = None
        try:
            threading.Thread(target=lambda: retrain_model_if_needed(games_folder="games", min_games=2), daemon=True).start()
            if csv_path:
                ml_story = coach_reply(csv_path, winner=winner)
        except Exception as e:
            print(f"ML coach error: {e}")

        # First, show a simple win/lose popup
        if winner == "You":
            messagebox.showinfo("Game Over", "You won!")
        elif winner == "Computer":
            messagebox.showinfo("Game Over", "Computer won.")
        else:
            messagebox.showinfo("Game Over", f"{winner}.")

        # Map mistakes by move number for quick lookup
        mistakes_by_move = {e["move_no"]: e for e in analysis.get("mistake_events", [])}

        # Build a detailed summary window with story + moves table
        win = tk.Toplevel(self.root)
        win.title("Game Summary")
        win.geometry("1000x700")

        container = tk.Frame(win)
        container.pack(fill=tk.BOTH, expand=True)

        # Create notebook-style tabs (using frames and buttons)
        tab_frame = tk.Frame(container, bg="#e0e0e0", height=40)
        tab_frame.pack(fill=tk.X, padx=0, pady=0)
        tab_frame.pack_propagate(False)

        # Tab buttons
        rule_btn = tk.Button(tab_frame, text="Rule-Based Coach", font=("Arial", 11, "bold"), bg="#42a5f5", fg="white", relief=tk.FLAT, padx=20, pady=8)
        rule_btn.pack(side=tk.LEFT, padx=5, pady=5)

        ml_btn = tk.Button(tab_frame, text="ML Coach", font=("Arial", 11, "bold"), bg="#90caf9", fg="white", relief=tk.FLAT, padx=20, pady=8)
        ml_btn.pack(side=tk.LEFT, padx=5, pady=5)

        # Content frame (will swap between rule-based and ML)
        content_frame = tk.Frame(container)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        def show_rule_based():
            # Clear content frame
            for widget in content_frame.winfo_children():
                widget.destroy()
            
            # Story section
            story_frame = tk.LabelFrame(content_frame, text="Coach Story", padx=10, pady=10)
            story_frame.pack(fill=tk.X, pady=(0, 10))

            story_text = tk.Text(story_frame, wrap=tk.WORD, height=8)
            story_text.pack(fill=tk.X)
            story_text.insert(tk.END, report)
            story_text.config(state=tk.DISABLED)

            # Moves table section
            table_frame = tk.LabelFrame(content_frame, text="Move-by-move overview", padx=10, pady=10)
            table_frame.pack(fill=tk.BOTH, expand=True)

            canvas = tk.Canvas(table_frame)
            scrollbar = tk.Scrollbar(table_frame, orient=tk.VERTICAL, command=canvas.yview)
            inner = tk.Frame(canvas)

            inner.bind(
                "<Configure>",
                lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
            )

            canvas.create_window((0, 0), window=inner, anchor="nw")
            canvas.configure(yscrollcommand=scrollbar.set)

            canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

            # Header row
            headers = ["Move", "Player", "Row", "Col", "Time (s)", "Comment"]
            for c, h in enumerate(headers):
                tk.Label(inner, text=h, font=("Arial", 10, "bold"), borderwidth=1, relief=tk.SOLID, padx=4, pady=2).grid(row=0, column=c, sticky="nsew")

            for c in range(len(headers)):
                inner.grid_columnconfigure(c, weight=1)

            # Rows
            for idx, m in enumerate(self.move_log, start=1):
                mover = m.get("player")
                row = m.get("row")
                col = m.get("col")
                tsec = m.get("elapsed_seconds", 0)

                comment = ""
                if mover == perspective and idx in mistakes_by_move:
                    ev = mistakes_by_move[idx]
                    labels = ev.get("labels", [])
                    kinds = []
                    if "missed_win" in labels:
                        kinds.append("missed a winning move")
                    if "missed_block" in labels:
                        kinds.append("missed a critical block")
                    if "weak_edge" in labels:
                        kinds.append("weak edge move")
                    if "low_value" in labels:
                        kinds.append("low-value move")
                    if kinds:
                        comment = ", ".join(kinds).capitalize()
                    better = [f"({br},{bc})" for br, bc, kind in ev.get("better_moves", [])]
                    if better:
                        comment += f"; better: {', '.join(better)}"
                elif mover == perspective:
                    comment = "Solid move aligned with the AI's plan."

                values = [idx, mover, row, col, tsec, comment]
                for c, val in enumerate(values):
                    tk.Label(inner, text=str(val), font=("Arial", 9), anchor="w", borderwidth=1, relief=tk.SOLID, padx=4, pady=2).grid(row=idx, column=c, sticky="nsew")

        def show_ml_coach():
            # Clear content frame
            for widget in content_frame.winfo_children():
                widget.destroy()
            
            if not ml_story:
                no_ml = tk.Label(content_frame, text="ML Coach not available yet. Play more games to train the model!", font=("Arial", 12), fg="#666")
                no_ml.pack(pady=50)
                return
            
            # ML story section
            ml_frame = tk.LabelFrame(content_frame, text="ML-Based Analysis", padx=10, pady=10)
            ml_frame.pack(fill=tk.BOTH, expand=True)

            ml_text = tk.Text(ml_frame, wrap=tk.WORD, font=("Arial", 10))
            ml_text.pack(fill=tk.BOTH, expand=True)
            ml_text.insert(tk.END, ml_story)
            ml_text.config(state=tk.DISABLED)

        # Set button commands
        rule_btn.config(command=lambda: [show_rule_based(), rule_btn.config(bg="#42a5f5"), ml_btn.config(bg="#90caf9")])
        ml_btn.config(command=lambda: [show_ml_coach(), ml_btn.config(bg="#42a5f5"), rule_btn.config(bg="#90caf9")])

        # Show rule-based by default
        show_rule_based()

        # Close button
        btn = tk.Button(container, text="Close", command=win.destroy, font=("Arial", 11, "bold"))
        btn.pack(pady=(0, 10))
    
    def destroy(self):
        self.main_container.destroy()

    def show_suggestions(self):
        # Toggle: hide if visible
        if hasattr(self, 'suggestion_overlay') and self.suggestion_overlay.is_visible():
            self.suggestion_overlay.hide()
            return
        # Only when game running, player's turn, and not thinking
        if not self.game_started or not self.player_color:
            return
        if self.current_player != self.player_color or self.ai_thinking:
            return
        # Build suggestions using selected difficulty
        diff = (self.difficulty_var.get() if hasattr(self, 'difficulty_var') else "Medium")
        suggestions = compute_suggestions(self.state, self.player_color, top_k=6, difficulty=diff)

        def on_pick(r, c):
            if 0 <= r < 15 and 0 <= c < 15 and self.state[r][c] is None and self.current_player == self.player_color:
                mover_color = self.current_player
                # Hide suggestions and cancel timer
                if hasattr(self, 'suggestion_overlay'):
                    self.suggestion_overlay.hide()
                self._cancel_suggestion_timer()
                self.place_stone(r, c, mover_color)
                if self.check_winner(r, c):
                    self.timer_running = False
                    self._finalize_game("You")
                    return
                self.current_player = "white" if self.current_player == "black" else "black"
                if self.current_player == (self.computer_color or "white"):
                    self.root.after(400, self.computer_move)
                else:
                    self._schedule_auto_suggestion()

        self.suggestion_overlay.show(suggestions, on_select=on_pick, anchor="bottom_left")

    # -------- Suggestion auto-show timer helpers --------
    def _cancel_suggestion_timer(self):
        if getattr(self, 'suggestion_timer_id', None):
            try:
                self.root.after_cancel(self.suggestion_timer_id)
            except Exception:
                pass
            self.suggestion_timer_id = None

    def _schedule_auto_suggestion(self, delay_ms: int = 12000):
        self._cancel_suggestion_timer()
        if not self.game_started or not self.player_color:
            return
        if self.current_player != self.player_color or self.ai_thinking:
            return
        self.suggestion_timer_id = self.root.after(delay_ms, self._auto_show_suggestions)

    def _auto_show_suggestions(self):
        self.suggestion_timer_id = None
        # Still player's turn and no AI thinking
        if self.game_started and self.player_color and self.current_player == self.player_color and not self.ai_thinking:
            if not (hasattr(self, 'suggestion_overlay') and self.suggestion_overlay.is_visible()):
                self.show_suggestions()
    
    # -------- Inactivity alert system --------
    def _start_inactivity_timer(self):
        """Start monitoring player inactivity"""
        print("[INACTIVITY] Starting inactivity timer")  # Debug output
        self.last_move_time = time.time()
        self.inactivity_alert_shown = False
        self._cancel_inactivity_timer()
        self._check_inactivity()
    
    def _cancel_inactivity_timer(self):
        """Cancel inactivity monitoring"""
        if getattr(self, 'inactivity_timer_id', None):
            try:
                self.root.after_cancel(self.inactivity_timer_id)
            except Exception:
                pass
            self.inactivity_timer_id = None
    
    def _reset_inactivity_timer(self):
        """Reset the inactivity timer when player makes a move"""
        self.last_move_time = time.time()
        self.inactivity_alert_shown = False
        if self.game_started and self.current_player == self.player_color:
            self._check_inactivity()
    
    def _check_inactivity(self):
        """Check if player has been inactive for 12 seconds"""
        # Cancel any existing timer
        self._cancel_inactivity_timer()
        
        # Only check during active game and player's turn
        if not self.game_started or not self.player_color:
            return
        if self.current_player != self.player_color or self.ai_thinking:
            return
        
        # Calculate time since last move
        if self.last_move_time is not None:
            elapsed = time.time() - self.last_move_time
            print(f"[INACTIVITY] Elapsed: {elapsed:.1f}s")  # Debug output
            
            if elapsed >= 12 and not self.inactivity_alert_shown:
                # Show alert
                print("[INACTIVITY] Showing alert!")  # Debug output
                self._show_inactivity_alert()
                self.inactivity_alert_shown = True
            else:
                # Schedule next check in 1 second
                self.inactivity_timer_id = self.root.after(1000, self._check_inactivity)
    
    def _show_inactivity_alert(self):
        """Display inactivity alert to the player"""
        # Create a non-blocking alert overlay on the canvas
        try:
            # Flash the board border
            self.board_canvas.config(highlightthickness=3, highlightbackground="#ff6b6b")
            
            # Show message box
            response = messagebox.showwarning(
                "Inactivity Alert",
                "You've been inactive for 12 seconds!\n\nAre you still there?\n\nClick OK to continue playing.",
                parent=self.root
            )
            
            # Reset border
            self.board_canvas.config(highlightthickness=0)
            
            # Reset timer after alert
            self._reset_inactivity_timer()
            
        except Exception as e:
            print(f"Error showing inactivity alert: {e}")