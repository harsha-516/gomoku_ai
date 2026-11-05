import tkinter as tk
from tkinter import font as tkfont

class GomokuHomePage:
    def __init__(self, root, single_player_callback, pvp_callback, how_to_play_callback):
        self.root = root
        self.single_player_callback = single_player_callback
        self.pvp_callback = pvp_callback
        self.how_to_play_callback = how_to_play_callback
        
        # Main container
        self.main_container = tk.Frame(root, bg="#f0f4f8")
        self.main_container.pack(fill=tk.BOTH, expand=True)
        
        self.create_header()
        self.create_main_content()
        self.create_info_cards()
        
    def create_header(self):
        # Header frame with gradient-like effect
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
            ("Home", None),
            ("Single Player", self.single_player_callback),
            ("Player Vs Player", self.pvp_callback),
            ("How To Play", self.how_to_play_callback)
        ]
        for btn_text, cmd in nav_buttons:
            btn = tk.Button(nav_frame, text=btn_text, 
                          font=("Arial", 12, "bold"),
                          bg="#e3f2fd", fg="#1a1a1a",
                          relief=tk.FLAT, cursor="hand2",
                          padx=20, pady=10,
                          borderwidth=0,
                          command=cmd)
            btn.pack(side=tk.LEFT, padx=10)
            if btn_text == "Home":
                btn.config(font=("Arial", 12, "bold underline"))
            else:
                btn.bind("<Enter>", lambda e, b=btn: b.config(fg="#4a90e2"))
                btn.bind("<Leave>", lambda e, b=btn: b.config(fg="#1a1a1a"))
    
    def create_main_content(self):
        # Main content frame
        main_frame = tk.Frame(self.main_container, bg="#f0f4f8")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=40, pady=30)
        
        # Left side - Text and buttons
        left_frame = tk.Frame(main_frame, bg="#f0f4f8")
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Title
        title = tk.Label(left_frame, text="Play Gomuku", 
                        font=("Arial", 48, "bold"),
                        bg="#f0f4f8", fg="#1a1a1a")
        title.pack(anchor=tk.W, pady=(40, 20))
        
        # Subtitle
        subtitle = tk.Label(left_frame, 
                          text="The board is set. The challenge awaits. Are you ready?",
                          font=("Arial", 16),
                          bg="#f0f4f8", fg="#4a4a4a")
        subtitle.pack(anchor=tk.W, pady=(0, 40))
        
        # Buttons frame
        buttons_frame = tk.Frame(left_frame, bg="#f0f4f8")
        buttons_frame.pack(anchor=tk.W)
        
        # Single Player button
        single_btn = tk.Button(buttons_frame, text="👤 Single Player",
                              font=("Arial", 14, "bold"),
                              bg="#42a5f5", fg="white",
                              relief=tk.FLAT, cursor="hand2",
                              padx=30, pady=15,
                              borderwidth=0,
                              command=self.single_player_callback)
        single_btn.pack(side=tk.LEFT, padx=(0, 20))
        single_btn.bind("<Enter>", lambda e: single_btn.config(bg="#1e88e5"))
        single_btn.bind("<Leave>", lambda e: single_btn.config(bg="#42a5f5"))
        
        # Player vs Player button
        pvp_btn = tk.Button(buttons_frame, text="👥 Player Vs Player",
                           font=("Arial", 14, "bold"),
                           bg="#455a64", fg="white",
                           relief=tk.FLAT, cursor="hand2",
                           padx=30, pady=15,
                           borderwidth=0,
                           command=self.pvp_callback)
        pvp_btn.pack(side=tk.LEFT)
        pvp_btn.bind("<Enter>", lambda e: pvp_btn.config(bg="#37474f"))
        pvp_btn.bind("<Leave>", lambda e: pvp_btn.config(bg="#455a64"))
        
        # Right side - Board image
        right_frame = tk.Frame(main_frame, bg="#f0f4f8")
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, padx=(40, 0))
        
        # Create board canvas
        board_canvas = tk.Canvas(right_frame, width=500, height=350,
                                bg="#f0f4f8", highlightthickness=0)
        board_canvas.pack(pady=20)
        
        # Draw gomoku board
        self.draw_board(board_canvas)
    
    def draw_board(self, canvas):
        # Create board background
        canvas.create_rectangle(10, 10, 490, 340, fill="#d4a574", outline="")
        
        # Draw grid lines
        for i in range(10):
            x = 40 + i * 45
            canvas.create_line(x, 30, x, 320, fill="#8b6f47", width=1)
            
        for i in range(8):
            y = 30 + i * 40
            canvas.create_line(40, y, 445, y, fill="#8b6f47", width=1)
        
        # Draw stones (example pattern)
        stones = [
            (140, 150, "white"), (185, 150, "black"), (230, 150, "white"),
            (275, 150, "black"), (140, 190, "white"), (185, 190, "white"),
            (230, 190, "black"), (275, 190, "black"), (320, 190, "black"),
            (140, 230, "black"), (185, 230, "white"), (230, 230, "white"),
            (275, 230, "black"), (320, 150, "white"), (365, 150, "black"),
            (320, 230, "white"),
        ]
        
        for x, y, color in stones:
            fill = "white" if color == "white" else "#1a1a1a"
            outline = "#d0d0d0" if color == "white" else "#000000"
            canvas.create_oval(x-15, y-15, x+15, y+15, 
                             fill=fill, outline=outline, width=2)
    
    def create_info_cards(self):
        # Cards container
        cards_frame = tk.Frame(self.main_container, bg="#f0f4f8")
        cards_frame.pack(fill=tk.X, padx=40, pady=(0, 40))
        
        # Center the cards
        center_frame = tk.Frame(cards_frame, bg="#f0f4f8")
        center_frame.pack(anchor=tk.CENTER)
        
        # Single Player card
        single_card = tk.Frame(center_frame, bg="white", relief=tk.FLAT,
                              borderwidth=0, highlightthickness=1,
                              highlightbackground="#e0e0e0")
        single_card.pack(side=tk.LEFT, padx=20, ipadx=40, ipady=30)
        
        single_icon = tk.Label(single_card, text="👤", font=("Arial", 40),
                              bg="white", fg="#42a5f5")
        single_icon.pack(pady=(10, 10))
        
        single_title = tk.Label(single_card, text="Single Player",
                               font=("Arial", 18, "bold"),
                               bg="white", fg="#1a1a1a")
        single_title.pack()
        
        single_desc = tk.Label(single_card, 
                              text="Challenge yourself against our AI with\nmultiple difficulty levels",
                              font=("Arial", 11),
                              bg="white", fg="#757575",
                              justify=tk.CENTER)
        single_desc.pack(pady=(10, 10))
        
        # Player vs Player card
        pvp_card = tk.Frame(center_frame, bg="white", relief=tk.FLAT,
                           borderwidth=0, highlightthickness=1,
                           highlightbackground="#e0e0e0")
        pvp_card.pack(side=tk.LEFT, padx=20, ipadx=40, ipady=30)
        
        pvp_icon = tk.Label(pvp_card, text="👥", font=("Arial", 40),
                           bg="white", fg="#42a5f5")
        pvp_icon.pack(pady=(10, 10))
        
        pvp_title = tk.Label(pvp_card, text="Player Vs Player",
                            font=("Arial", 18, "bold"),
                            bg="white", fg="#1a1a1a")
        pvp_title.pack()
        
        pvp_desc = tk.Label(pvp_card, 
                           text="Challenge in between your friends",
                           font=("Arial", 11),
                           bg="white", fg="#757575",
                           justify=tk.CENTER)
        pvp_desc.pack(pady=(10, 10))
    
    def destroy(self):
        self.main_container.destroy()


class GomokuApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Gomoku")
        self.root.geometry("1400x800")
        self.root.configure(bg="#f0f4f8")
        
        self.show_home_page()
    
    def show_home_page(self):
        self.home_page = GomokuHomePage(self.root, self.open_single_player, self.open_player_vs_player, self.open_how_to_play)
    
    def open_single_player(self):
        # Destroy current home page if present
        if hasattr(self, 'home_page') and self.home_page:
            try:
                self.home_page.destroy()
            except Exception:
                pass
            self.home_page = None
        import single_player
        single_player.GomokuGamePage(
            self.root,
            self.back_to_home,
            self.open_single_player,
            self.open_player_vs_player,
            self.open_how_to_play,
        )
    
    def open_player_vs_player(self):
        if hasattr(self, 'home_page') and self.home_page:
            try:
                self.home_page.destroy()
            except Exception:
                pass
            self.home_page = None
        import player_vs_player
        player_vs_player.GomokuPvPPage(
            self.root,
            self.back_to_home,
            self.open_single_player,
            self.open_player_vs_player,
            self.open_how_to_play,
        )
    
    def open_how_to_play(self):
        if hasattr(self, 'home_page') and self.home_page:
            try:
                self.home_page.destroy()
            except Exception:
                pass
            self.home_page = None
        import how_to_play
        how_to_play.HowToPlayPage(
            self.root,
            self.back_to_home,
            self.open_single_player,
            self.open_player_vs_player,
            self.open_how_to_play,
        )
    
    def back_to_home(self):
        self.show_home_page()


if __name__ == "__main__":
    root = tk.Tk()
    app = GomokuApp(root)
    root.mainloop()