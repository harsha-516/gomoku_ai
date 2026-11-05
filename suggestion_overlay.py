import tkinter as tk
from typing import List, Optional, Tuple, Callable
from gomoku_ai import candidate_moves, try_move_is_win, evaluate, suggest_moves

Move = Tuple[int, int]


def compute_suggestions(state: List[List[Optional[str]]], player_color: str, top_k: int = 5, difficulty: str = "Medium") -> List[Tuple[int, int, int, str]]:
    # Delegate to gomoku_ai.suggest_moves (supports Easy/Medium/Hard)
    return suggest_moves(state, player_color, difficulty=difficulty, top_k=top_k, max_candidates=12)


class SuggestionOverlay:
    def __init__(self, canvas: tk.Canvas, cell_size: int = 32, margin: int = 15, use_toplevel: bool = True, show_markers: bool = True):
        self.canvas = canvas
        self.cell_size = cell_size
        self.margin = margin
        self.use_toplevel = use_toplevel
        self.show_markers = show_markers
        # Canvas-mode state
        self.items: List[int] = []
        self.markers: List[int] = []
        # Toplevel-mode state
        self.window: Optional[tk.Toplevel] = None
        self.on_select: Optional[Callable[[int, int], None]] = None

    def show(self, suggestions: List[Tuple[int, int, int, str]], on_select: Optional[Callable[[int, int], None]] = None, anchor: str = "bottom_left"):
        self.hide()
        self.on_select = on_select
        if self.use_toplevel:
            self._show_toplevel(suggestions)
        else:
            self._show_on_canvas(suggestions, anchor)

    def _show_toplevel(self, suggestions: List[Tuple[int, int, int, str]]):
        root = self.canvas.winfo_toplevel()
        win = tk.Toplevel(root)
        win.overrideredirect(True)
        win.attributes("-topmost", True)
        bg = "#6b7280"  # gray-500
        fg = "white"
        frame = tk.Frame(win, bg=bg, bd=1, relief=tk.FLAT)
        frame.pack(fill=tk.BOTH, expand=True)
        title = tk.Label(frame, text="Suggestions", font=("Arial", 12, "bold"), bg=bg, fg=fg)
        title.pack(anchor="w", padx=10, pady=(8, 4))
        for idx, (r, c, s, kind) in enumerate(suggestions[:8]):
            if kind == 'win':
                label = f"{idx+1}. ({r},{c}) ⭐ WIN - Score: {s}"
            elif kind == 'block':
                label = f"{idx+1}. ({r},{c}) 🛡️ BLOCK - Score: {s}"
            elif kind == 'search':
                label = f"{idx+1}. ({r},{c}) 🎯 Strategic - Score: {s}"
            else:
                label = f"{idx+1}. ({r},{c}) 💡 Tactical - Score: {s}"
            btn = tk.Button(frame, text=label, anchor="w", font=("Arial", 10), bg=bg, fg=fg, activebackground="#4b5563", activeforeground="white", relief=tk.FLAT, bd=0, padx=10)
            btn.pack(fill=tk.X, pady=2)
            btn.bind("<Button-1>", lambda e, rr=r, cc=c: self._select(rr, cc))
        # Size and position bottom-left of the root window
        frame.update_idletasks()
        width = max(220, frame.winfo_reqwidth() + 12)
        height = frame.winfo_reqheight() + 8
        # Determine absolute pos for bottom-left
        root.update_idletasks()
        rx = root.winfo_x()
        ry = root.winfo_y()
        rw = root.winfo_width()
        rh = root.winfo_height()
        x = rx + 8
        y = ry + rh - height - 8
        win.geometry(f"{width}x{height}+{x}+{y}")
        self.window = win
        # Optional: draw markers on the board for each suggestion
        if self.show_markers:
            for r, c, _s, kind in suggestions[:8]:
                mx = self.margin + c * self.cell_size
                my = self.margin + r * self.cell_size
                # Color code: green for wins, red for blocks (defense)
                if kind == 'win':
                    color = "#2ecc71"  # green
                elif kind == 'block':
                    color = "#e74c3c"  # red
                else:
                    color = "#2ecc71"  # green for strategic moves
                m = self.canvas.create_oval(mx-9, my-9, mx+9, my+9, outline=color, width=2)
                self.markers.append(m)
                self.canvas.tag_bind(m, "<Button-1>", lambda e, rr=r, cc=c: self._select(rr, cc))

    def _show_on_canvas(self, suggestions: List[Tuple[int, int, int, str]], anchor: str):
        w = int(self.canvas["width"]) if str(self.canvas["width"]).isdigit() else 510
        h = int(self.canvas["height"]) if str(self.canvas["height"]).isdigit() else 510
        box_w = 230
        box_h = 40 + 24 * max(1, len(suggestions))
        if anchor == "bottom_left":
            x0, y0 = 10, h - box_h - 10
        elif anchor == "top_left":
            x0, y0 = 10, 10
        elif anchor == "bottom_right":
            x0, y0 = w - box_w - 10, h - box_h - 10
        else:
            x0, y0 = w - box_w - 10, 10
        x1, y1 = x0 + box_w, y0 + box_h
        bg = self.canvas.create_rectangle(x0, y0, x1, y1, fill="#6b7280", outline="#4b5563")
        self.items.append(bg)
        title = self.canvas.create_text(x0 + 10, y0 + 16, text="Suggestions", anchor="w", font=("Arial", 12, "bold"), fill="white")
        self.items.append(title)
        close_bg = self.canvas.create_rectangle(x1 - 24, y0 + 4, x1 - 4, y0 + 24, fill="#4b5563", outline="#374151")
        close_tx = self.canvas.create_text(x1 - 14, y0 + 14, text="x", font=("Arial", 10), fill="white")
        self.items += [close_bg, close_tx]
        self.canvas.tag_bind(close_bg, "<Button-1>", lambda e: self.hide())
        self.canvas.tag_bind(close_tx, "<Button-1>", lambda e: self.hide())
        for idx, (r, c, s, kind) in enumerate(suggestions[:8]):
            if kind == 'win':
                label = f"{idx+1}. ({r},{c}) ⭐ WIN - {s}"
            elif kind == 'block':
                label = f"{idx+1}. ({r},{c}) 🛡️ BLOCK - {s}"
            elif kind == 'search':
                label = f"{idx+1}. ({r},{c}) 🎯 Strategic - {s}"
            else:
                label = f"{idx+1}. ({r},{c}) 💡 Tactical - {s}"
            ty = y0 + 36 + idx * 22
            t = self.canvas.create_text(x0 + 12, ty, text=label, anchor="w", font=("Arial", 10), fill="white")
            self.items.append(t)
            self.canvas.tag_bind(t, "<Button-1>", lambda e, rr=r, cc=c: self._select(rr, cc))
        # Do not draw markers when we are asked not to place on board

    def _select(self, r: int, c: int):
        self.hide()
        if self.on_select:
            self.on_select(r, c)

    def hide(self):
        # Close toplevel if present
        if self.window is not None:
            try:
                self.window.destroy()
            except Exception:
                pass
            self.window = None
        # Clear canvas items if any
        for i in self.items:
            self.canvas.delete(i)
        for m in self.markers:
            self.canvas.delete(m)
        self.items.clear()
        self.markers.clear()
        self.on_select = None

    def is_visible(self) -> bool:
        return (self.window is not None) or (len(self.items) > 0) or (len(self.markers) > 0)
