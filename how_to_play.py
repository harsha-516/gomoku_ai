import tkinter as tk
from tkinter import ttk


class HowToPlayPage:
    def __init__(self, root, back_callback, open_single_cb, open_pvp_cb, open_how_cb):
        self.root = root
        self.back_callback = back_callback
        self.open_single_cb = open_single_cb
        self.open_pvp_cb = open_pvp_cb
        self.open_how_cb = open_how_cb
        
        # Main container
        self.main_container = tk.Frame(root, bg="#f0f4f8")
        self.main_container.pack(fill=tk.BOTH, expand=True)
        
        self.create_header()
        self.create_scrollable_content()
        
    def create_header(self):
        header = tk.Frame(self.main_container, bg="#e3f2fd", height=100)
        header.pack(fill=tk.X, padx=20, pady=(20, 0))
        header.pack_propagate(False)
        
        # Logo
        logo_frame = tk.Frame(header, bg="#e3f2fd")
        logo_frame.pack(side=tk.LEFT, padx=20, pady=10)
        
        logo_canvas = tk.Canvas(logo_frame, width=60, height=60, bg="#e3f2fd", highlightthickness=0)
        logo_canvas.pack(side=tk.LEFT)
        logo_canvas.create_oval(5, 5, 55, 55, fill="#4a90e2", outline="")
        logo_canvas.create_text(30, 30, text="⚡", font=("Arial", 24), fill="white")
        
        title_label = tk.Label(logo_frame, text="Gomuku", font=("Arial", 32, "bold"), bg="#e3f2fd", fg="#1a1a1a")
        title_label.pack(side=tk.LEFT, padx=15)
        
        # Navigation
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
            if btn_text == "How To Play":
                underline = 0
            btn = tk.Button(nav_frame, text=btn_text, font=("Arial", 12, "bold"), 
                          bg="#e3f2fd", fg="#1a1a1a", relief=tk.FLAT, 
                          cursor="hand2", padx=20, pady=10, borderwidth=0, command=cmd)
            btn.pack(side=tk.LEFT, padx=10)
            if underline >= 0:
                btn.config(font=("Arial", 12, "bold underline"))
            else:
                btn.bind("<Enter>", lambda e, b=btn: b.config(fg="#4a90e2"))
                btn.bind("<Leave>", lambda e, b=btn: b.config(fg="#1a1a1a"))
        
    def _teardown_and(self, action):
        try:
            self.destroy()
        except Exception:
            pass
        action()

    def _nav_to_single(self):
        self._teardown_and(self.open_single_cb)

    def _nav_to_pvp(self):
        self._teardown_and(self.open_pvp_cb)

    def _nav_to_how(self):
        # Already here, but follow same path for consistency
        self._teardown_and(self.open_how_cb)
    
    def create_scrollable_content(self):
        # Scrollable container
        container = tk.Frame(self.main_container, bg="#f0f4f8")
        container.pack(fill=tk.BOTH, expand=True)
        
        canvas = tk.Canvas(container, bg="#f0f4f8", highlightthickness=0)
        scrollbar = tk.Scrollbar(container, orient=tk.VERTICAL, command=canvas.yview)
        
        scrollable_frame = tk.Frame(canvas, bg="#f0f4f8")
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Content
        self.create_content(scrollable_frame)
        
        # Bind mousewheel
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
    
    def create_content(self, parent):
        # Title
        title = tk.Label(parent, text="How to Play Gomoku", 
                        font=("Arial", 28, "bold"), bg="#f0f4f8", fg="#2c3e50")
        title.pack(pady=(30, 20))
        
        # Content container - now spans full width
        content = tk.Frame(parent, bg="white", relief=tk.FLAT, 
                          highlightthickness=1, highlightbackground="#e0e0e0")
        content.pack(padx=200, pady=20, fill=tk.BOTH, expand=True)
        
        # Game Rules Section
        self.create_section(content, "Game Rules", [
            "Gomoku is played on a 15×15 board.",
            "Black plays first, and players alternate in placing a stone of their color on an empty intersection.",
            "The winner is the first player to form an unbroken chain of five stones horizontally, vertically, or diagonally.",
            "Once placed, stones cannot be moved or removed from the board."
        ])
        
        # Basic Strategy Section
        self.create_section(content, "Basic Strategy", [
            ("Attack and Defense:", "Always look for opportunities to create threats while defending against your opponent's threats."),
            ("Center Control:", "The center of the board offers more opportunities to create winning lines in multiple directions."),
            ("Connected Stones:", "Try to keep your stones connected as much as possible to create multiple threats."),
            ("Watch for Patterns:", "Learn to recognize common patterns like \"open four\" (four in a row with empty spaces at both ends) which are strong threats.")
        ])
        
        # Example Patterns Section
        self.create_patterns_section(content)
        
        # Suggestion Markers Section
        self.create_markers_section(content)
        
        # Difficulty Levels Section
        self.create_difficulty_section(content)
    
    def create_section(self, parent, title, items):
        section = tk.Frame(parent, bg="white")
        section.pack(fill=tk.X, padx=40, pady=20)
        
        # Section title
        title_label = tk.Label(section, text=title, font=("Arial", 18, "bold"), 
                              bg="white", fg="#2c3e50", anchor="w")
        title_label.pack(fill=tk.X, pady=(0, 10))
        
        # Items
        for item in items:
            item_frame = tk.Frame(section, bg="white")
            item_frame.pack(fill=tk.X, pady=3)
            
            bullet = tk.Label(item_frame, text="•", font=("Arial", 12), 
                            bg="white", fg="#e74c3c", width=2, anchor="w")
            bullet.pack(side=tk.LEFT)
            
            if isinstance(item, tuple):
                # Bold title + description
                bold_text, normal_text = item
                text_frame = tk.Frame(item_frame, bg="white")
                text_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
                
                bold_label = tk.Label(text_frame, text=bold_text, font=("Arial", 11, "bold"), 
                                    bg="white", fg="#2c3e50", anchor="w")
                bold_label.pack(side=tk.LEFT)
                
                normal_label = tk.Label(text_frame, text=" " + normal_text, font=("Arial", 11), 
                                       bg="white", fg="#555", anchor="w")
                normal_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
            else:
                # Regular text
                text_label = tk.Label(item_frame, text=item, font=("Arial", 11), 
                                    bg="white", fg="#555", anchor="w", wraplength=800, justify=tk.LEFT)
                text_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
    
    def create_patterns_section(self, parent):
        section = tk.Frame(parent, bg="white")
        section.pack(fill=tk.X, padx=40, pady=20)
        
        # Section title
        title_label = tk.Label(section, text="Example Patterns", font=("Arial", 18, "bold"), 
                              bg="white", fg="#2c3e50", anchor="w")
        title_label.pack(fill=tk.X, pady=(0, 15))
        
        # Patterns container
        patterns_frame = tk.Frame(section, bg="white")
        patterns_frame.pack(fill=tk.X)
        
        # Three pattern examples
        patterns = [
            ("Five in a Row (Win)", [(3, 2), (3, 3), (3, 4), (3, 5), (3, 6)], "black"),
            ("Open Four", [(3, 2), (3, 3), (3, 4), (3, 5)], "black"),
            ("Double Three", [(2, 2), (3, 2), (4, 2), (3, 3), (3, 4), (2, 4), (4, 4)], "black")
        ]
        
        for pattern_name, stones, color in patterns:
            self.create_pattern_board(patterns_frame, pattern_name, stones, color)
    
    def create_pattern_board(self, parent, title, stones, stone_color):
        container = tk.Frame(parent, bg="white")
        container.pack(side=tk.LEFT, padx=15, pady=10)
        
        # Title
        title_label = tk.Label(container, text=title, font=("Arial", 11, "bold"), 
                              bg="white", fg="#2c3e50")
        title_label.pack(pady=(0, 8))
        
        # Board
        board_size = 180
        cell_size = board_size // 7
        
        canvas = tk.Canvas(container, width=board_size, height=board_size, 
                          bg="#d4a574", highlightthickness=2, highlightbackground="#a89070")
        canvas.pack()
        
        # Draw grid
        for i in range(7):
            x = i * cell_size + cell_size // 2
            canvas.create_line(x, cell_size // 2, x, board_size - cell_size // 2, fill="#8b6f47", width=1)
            canvas.create_line(cell_size // 2, x, board_size - cell_size // 2, x, fill="#8b6f47", width=1)
        
        # Draw stones
        for row, col in stones:
            x = col * cell_size + cell_size // 2
            y = row * cell_size + cell_size // 2
            radius = cell_size // 3
            
            fill = "#1a1a1a" if stone_color == "black" else "white"
            outline = "#000000" if stone_color == "black" else "#d0d0d0"
            
            canvas.create_oval(x - radius, y - radius, x + radius, y + radius, 
                             fill=fill, outline=outline, width=2)
        
        # Add white stones for Double Three pattern
        if title == "Double Three":
            white_stones = [(1, 2), (3, 1), (3, 5), (5, 4)]
            for row, col in white_stones:
                x = col * cell_size + cell_size // 2
                y = row * cell_size + cell_size // 2
                radius = cell_size // 3
                canvas.create_oval(x - radius, y - radius, x + radius, y + radius, 
                                 fill="white", outline="#d0d0d0", width=2)
    
    def create_markers_section(self, parent):
        section = tk.Frame(parent, bg="white")
        section.pack(fill=tk.X, padx=40, pady=20)
        
        # Section title
        title_label = tk.Label(section, text="Suggestion Markers", font=("Arial", 18, "bold"), 
                              bg="white", fg="#2c3e50", anchor="w")
        title_label.pack(fill=tk.X, pady=(0, 10))
        
        # Description
        desc = tk.Label(section, text="During gameplay, you can request move suggestions by clicking the 'Suggest' button or pressing 'S'. The AI will analyze the board and show you the best moves with color-coded markers:",
                       font=("Arial", 11), bg="white", fg="#555", anchor="w", 
                       wraplength=800, justify=tk.LEFT)
        desc.pack(fill=tk.X, pady=(0, 15))
        
        # Marker types
        markers = [
            ("🟢 Green Markers:", "Winning moves - positions where you can win immediately, or strong offensive moves that create threats."),
            ("🔴 Red Markers:", "Defensive blocks - critical positions where you must block your opponent from winning on their next turn."),
            ("Auto-Suggestions:", "If you don't make a move for 12 seconds, suggestions will automatically appear to help you.")
        ]
        
        for item in markers:
            item_frame = tk.Frame(section, bg="white")
            item_frame.pack(fill=tk.X, pady=3)
            
            bullet = tk.Label(item_frame, text="•", font=("Arial", 12), 
                            bg="white", fg="#42a5f5", width=2, anchor="w")
            bullet.pack(side=tk.LEFT)
            
            bold_text, normal_text = item
            text_frame = tk.Frame(item_frame, bg="white")
            text_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
            
            bold_label = tk.Label(text_frame, text=bold_text, font=("Arial", 11, "bold"), 
                                bg="white", fg="#2c3e50", anchor="w")
            bold_label.pack(side=tk.LEFT)
            
            normal_label = tk.Label(text_frame, text=" " + normal_text, font=("Arial", 11), 
                                   bg="white", fg="#555", anchor="w", wraplength=700)
            normal_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
    
    def create_difficulty_section(self, parent):
        section = tk.Frame(parent, bg="white")
        section.pack(fill=tk.X, padx=40, pady=20)
        
        # Section title
        title_label = tk.Label(section, text="AI Difficulty Levels", font=("Arial", 18, "bold"), 
                              bg="white", fg="#2c3e50", anchor="w")
        title_label.pack(fill=tk.X, pady=(0, 10))
        
        # Difficulty descriptions
        difficulties = [
            ("Easy:", "The AI uses simple pattern recognition. It will block immediate wins and look for winning moves, but doesn't plan ahead."),
            ("Medium:", "The AI uses one-ply lookahead strategy, evaluating positions after each move and considering opponent responses."),
            ("Hard:", "The AI uses minimax search with alpha-beta pruning, looking 2-3 moves ahead to find optimal strategies.")
        ]
        
        for item in difficulties:
            item_frame = tk.Frame(section, bg="white")
            item_frame.pack(fill=tk.X, pady=3)
            
            bullet = tk.Label(item_frame, text="•", font=("Arial", 12), 
                            bg="white", fg="#e74c3c", width=2, anchor="w")
            bullet.pack(side=tk.LEFT)
            
            bold_text, normal_text = item
            text_frame = tk.Frame(item_frame, bg="white")
            text_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
            
            bold_label = tk.Label(text_frame, text=bold_text, font=("Arial", 11, "bold"), 
                                bg="white", fg="#2c3e50", anchor="w")
            bold_label.pack(side=tk.LEFT)
            
            normal_label = tk.Label(text_frame, text=" " + normal_text, font=("Arial", 11), 
                                   bg="white", fg="#555", anchor="w", wraplength=700)
            normal_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Bottom spacing
        tk.Frame(section, bg="white", height=30).pack()
    
    def go_home(self):
        self.destroy()
        self.back_callback()
    
    def destroy(self):
        self.main_container.destroy()
