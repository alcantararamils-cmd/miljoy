"""
=============================================================
MilJoy — AI Call Assistant
spiel.py — Spiel Panel + Teleprompter
=============================================================

PURPOSE:
    Floating panel for pasting scripts and talking points.
    Includes teleprompter auto-scroll mode.
    Hidden from screen share.
=============================================================
"""

import tkinter as tk
import ctypes


# =============================================================
# CONFIGURATION
# =============================================================

SPEED_SLOW   = 1
SPEED_MEDIUM = 2
SPEED_FAST   = 4
SCROLL_INTERVAL = 60    # milliseconds between scroll steps

PANEL_WIDTH  = 500
PANEL_HEIGHT = 520


# =============================================================
# COLOR PALETTE
# =============================================================

class C:
    BG_DARK      = "#0d1117"
    BG_CARD      = "#161b22"
    BG_INPUT     = "#1c2333"
    BLUE_PRIMARY = "#1e6fbf"
    BLUE_LIGHT   = "#4a90d9"
    GREEN        = "#57cc99"
    YELLOW       = "#f7b731"
    RED          = "#ff6b6b"
    TEXT_PRIMARY = "#e6edf3"
    TEXT_MUTED   = "#8b949e"


# =============================================================
# DRAG MANAGER
# =============================================================

class DragManager:
    def __init__(self, widget, root):
        self.root = root
        self._x = self._y = 0
        widget.bind("<ButtonPress-1>", self._start)
        widget.bind("<B1-Motion>", self._drag)

    def _start(self, e):
        self._x, self._y = e.x, e.y

    def _drag(self, e):
        self.root.geometry(
            f"+{self.root.winfo_x() + e.x - self._x}"
            f"+{self.root.winfo_y() + e.y - self._y}"
        )


# =============================================================
# SPIEL PANEL
# =============================================================

class SpielPanel:
    """Floating spiel panel with teleprompter mode."""

    def __init__(self, parent_root):
        self.parent_root        = parent_root
        self.is_visible         = False
        self.is_teleprompter    = False
        self.teleprompter_speed = SPEED_MEDIUM
        self._scroll_job        = None
        self._has_placeholder   = False

        self._build_window()
        print("[SPIEL] Panel initialized")

    def _build_window(self):
        self.root = tk.Toplevel(self.parent_root)
        self.root.title("MilJoy Spiel")
        self.root.configure(bg=C.BG_DARK)
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", 0.94)
        self.root.resizable(False, False)

        # Position to right of main window
        main_x = self.parent_root.winfo_x()
        main_y = self.parent_root.winfo_y()
        self.root.geometry(
            f"{PANEL_WIDTH}x{PANEL_HEIGHT}+{main_x + 575}+{main_y}"
        )

        # Build in correct order — bottom elements first
        self._build_status_bar()    # pack to bottom first
        self._build_controls()      # pack to bottom second
        self._build_title_bar()     # pack to top
        self._build_text_area()     # fills remaining space

        # Hide from screen share
        self.root.after(150, self._apply_screen_hide)

        # Start hidden
        self.root.withdraw()

    def _apply_screen_hide(self):
        """Hides from screen capture."""
        try:
            hwnd = ctypes.windll.user32.FindWindowW(None, "MilJoy Spiel")
            if hwnd == 0:
                hwnd = self.root.winfo_id()
            result = ctypes.windll.user32.SetWindowDisplayAffinity(hwnd, 0x11)
            if result:
                print("[✓] Spiel panel hidden from screen capture")
        except Exception as e:
            print(f"[ERROR] Spiel screen hide: {e}")

    def _build_title_bar(self):
        """Top title bar with drag and close."""
        bar = tk.Frame(self.root, bg=C.BLUE_PRIMARY, height=34)
        bar.pack(fill="x", side="top")
        bar.pack_propagate(False)

        left = tk.Frame(bar, bg=C.BLUE_PRIMARY)
        left.pack(side="left", padx=10, fill="y")

        tk.Label(
            left, text="📜  My Spiel",
            bg=C.BLUE_PRIMARY, fg="#ffffff",
            font=("Segoe UI", 10, "bold")
        ).pack(side="left", pady=6)

        tk.Label(
            left, text="  |  hidden from screen share",
            bg=C.BLUE_PRIMARY, fg="#c8deff",
            font=("Segoe UI", 7)
        ).pack(side="left")

        right = tk.Frame(bar, bg=C.BLUE_PRIMARY)
        right.pack(side="right", padx=8, fill="y")

        tk.Button(
            right, text="🗑", bg=C.BLUE_PRIMARY, fg="#c8deff",
            font=("Segoe UI", 11), bd=0, cursor="hand2",
            command=self._clear_text
        ).pack(side="left", padx=2, pady=4)

        tk.Button(
            right, text="✕", bg=C.BLUE_PRIMARY, fg="#ffffff",
            font=("Segoe UI", 11, "bold"), bd=0, cursor="hand2",
            command=self.hide
        ).pack(side="left", padx=2, pady=4)

        DragManager(bar, self.root)

    def _build_controls(self):
        """
        Bottom controls bar — packed to bottom BEFORE text area.
        Contains: Teleprompter button, Speed buttons, Reset button.
        """
        # Outer frame — dark background
        outer = tk.Frame(self.root, bg=C.BG_DARK, pady=4)
        outer.pack(fill="x", side="bottom")

        # Inner frame — card background
        inner = tk.Frame(outer, bg=C.BG_CARD, pady=6, padx=10)
        inner.pack(fill="x", padx=8, pady=(0, 6))

        # Row 1: Teleprompter button + Reset
        row1 = tk.Frame(inner, bg=C.BG_CARD)
        row1.pack(fill="x", pady=(0, 4))

        # Teleprompter toggle button
        self.teleprompter_btn = tk.Button(
            row1,
            text="▶  Start Teleprompter",
            bg=C.GREEN, fg=C.BG_DARK,
            font=("Segoe UI", 9, "bold"),
            bd=0, padx=12, pady=5,
            cursor="hand2",
            command=self._toggle_teleprompter
        )
        self.teleprompter_btn.pack(side="left")

        # Reset scroll button
        tk.Button(
            row1,
            text="⏮ Reset",
            bg=C.BG_DARK, fg=C.TEXT_MUTED,
            font=("Segoe UI", 9),
            bd=0, padx=10, pady=5,
            cursor="hand2",
            command=self._reset_scroll
        ).pack(side="right")

        # Row 2: Speed selector
        row2 = tk.Frame(inner, bg=C.BG_CARD)
        row2.pack(fill="x")

        tk.Label(
            row2, text="Speed:",
            bg=C.BG_CARD, fg=C.TEXT_MUTED,
            font=("Segoe UI", 8)
        ).pack(side="left", padx=(0, 6))

        self.speed_btns = {}
        speeds = [
            ("🐢 Slow",   SPEED_SLOW),
            ("🚶 Medium", SPEED_MEDIUM),
            ("🏃 Fast",   SPEED_FAST),
        ]

        for label, speed in speeds:
            is_default = (speed == SPEED_MEDIUM)
            btn = tk.Button(
                row2,
                text=label,
                bg=C.BLUE_PRIMARY if is_default else C.BG_DARK,
                fg="#ffffff" if is_default else C.TEXT_MUTED,
                font=("Segoe UI", 8),
                bd=0, padx=10, pady=4,
                cursor="hand2",
                command=lambda s=speed, l=label: self._set_speed(s, l)
            )
            btn.pack(side="left", padx=2)
            self.speed_btns[label] = btn

        print("[SPIEL] Controls built")

    def _build_status_bar(self):
        """Status bar — packed to bottom before controls."""
        self.status_bar = tk.Label(
            self.root,
            text="●  Paste your script above — then click ▶ Start Teleprompter",
            bg=C.BG_CARD, fg=C.TEXT_MUTED,
            font=("Segoe UI", 7),
            anchor="w", padx=10
        )
        self.status_bar.pack(fill="x", side="bottom", ipady=4)

    def _build_text_area(self):
        """
        Main text area — fills remaining space after
        title bar, controls, and status bar are packed.
        """
        frame = tk.Frame(self.root, bg=C.BG_DARK, padx=8, pady=6)
        frame.pack(fill="both", expand=True)

        scrollbar = tk.Scrollbar(frame)
        scrollbar.pack(side="right", fill="y")

        self.text_area = tk.Text(
            frame,
            bg=C.BG_INPUT,
            fg=C.TEXT_PRIMARY,
            font=("Segoe UI", 11),
            wrap="word",
            bd=0,
            padx=12,
            pady=10,
            insertbackground=C.TEXT_PRIMARY,
            selectbackground=C.BLUE_PRIMARY,
            yscrollcommand=scrollbar.set,
            relief="flat"
        )
        self.text_area.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.text_area.yview)

        # Placeholder
        self._insert_placeholder()

        self.text_area.bind("<FocusIn>",  self._on_focus_in)
        self.text_area.bind("<FocusOut>", self._on_focus_out)

        print("[SPIEL] Text area built")

    # =============================================================
    # PLACEHOLDER
    # =============================================================

    def _insert_placeholder(self):
        placeholder = (
            "Paste your spiel, script, or talking points here...\n\n"
            "Examples:\n"
            "• Sales pitch introduction\n"
            "• Key benefits to mention\n"
            "• Interview answers\n"
            "• Meeting agenda\n\n"
            "Then click ▶ Start Teleprompter below to auto-scroll."
        )
        self.text_area.config(state="normal")
        self.text_area.delete("1.0", "end")
        self.text_area.insert("1.0", placeholder)
        self.text_area.config(fg=C.TEXT_MUTED)
        self._has_placeholder = True

    def _on_focus_in(self, event):
        if self._has_placeholder:
            self.text_area.delete("1.0", "end")
            self.text_area.config(fg=C.TEXT_PRIMARY)
            self._has_placeholder = False

    def _on_focus_out(self, event):
        if not self.text_area.get("1.0", "end").strip():
            self._insert_placeholder()

    # =============================================================
    # SHOW / HIDE
    # =============================================================

    def show(self):
        self.root.deiconify()
        self.is_visible = True
        # Reposition next to main window
        main_x = self.parent_root.winfo_x()
        main_y = self.parent_root.winfo_y()
        self.root.geometry(f"+{main_x + 575}+{main_y}")
        print("[SPIEL] Shown")

    def hide(self):
        if self.is_teleprompter:
            self._stop_teleprompter()
        self.root.withdraw()
        self.is_visible = False
        print("[SPIEL] Hidden")

    def toggle(self):
        if self.is_visible:
            self.hide()
        else:
            self.show()

    # =============================================================
    # TELEPROMPTER
    # =============================================================

    def _toggle_teleprompter(self):
        if not self.is_teleprompter:
            self._start_teleprompter()
        else:
            self._stop_teleprompter()

    def _start_teleprompter(self):
        if self._has_placeholder:
            self._update_status("Paste your spiel first, then start teleprompter!")
            return

        content = self.text_area.get("1.0", "end").strip()
        if not content:
            self._update_status("Nothing to scroll — paste your spiel first!")
            return

        self.is_teleprompter = True
        self.text_area.config(state="disabled", cursor="arrow")
        self.teleprompter_btn.config(
            text="⏹  Stop Teleprompter",
            bg=C.RED, fg="#ffffff"
        )
        self._update_status("📜 Teleprompter running... click Stop to pause")
        print(f"[SPIEL] Teleprompter started — speed {self.teleprompter_speed}")
        self._scroll_loop()

    def _stop_teleprompter(self):
        self.is_teleprompter = False

        if self._scroll_job:
            self.root.after_cancel(self._scroll_job)
            self._scroll_job = None

        self.text_area.config(state="normal", cursor="xterm")
        self.teleprompter_btn.config(
            text="▶  Start Teleprompter",
            bg=C.GREEN, fg=C.BG_DARK
        )
        self._update_status("Teleprompter stopped")
        print("[SPIEL] Teleprompter stopped")

    def _scroll_loop(self):
        """Recursive scroll — stops at end of text."""
        if not self.is_teleprompter:
            return

        self.text_area.yview_scroll(self.teleprompter_speed, "pixels")

        # Stop if reached bottom
        if self.text_area.yview()[1] >= 1.0:
            self._stop_teleprompter()
            self._update_status("✓ End of spiel reached — click Reset to start over")
            return

        self._scroll_job = self.root.after(SCROLL_INTERVAL, self._scroll_loop)

    def _set_speed(self, speed, label):
        """Sets teleprompter speed and updates button highlights."""
        self.teleprompter_speed = speed
        for lbl, btn in self.speed_btns.items():
            if lbl == label:
                btn.config(bg=C.BLUE_PRIMARY, fg="#ffffff")
            else:
                btn.config(bg=C.BG_DARK, fg=C.TEXT_MUTED)
        print(f"[SPIEL] Speed: {label}")

    def _reset_scroll(self):
        """Scrolls back to top."""
        self.text_area.yview_moveto(0)
        self._update_status("Scroll reset to top — ready to read again")
        print("[SPIEL] Reset to top")

    # =============================================================
    # HELPERS
    # =============================================================

    def _clear_text(self):
        if self.is_teleprompter:
            self._stop_teleprompter()
        self._insert_placeholder()
        print("[SPIEL] Cleared")

    def _update_status(self, message):
        self.status_bar.config(text=f"●  {message}")

    def clear_for_new_session(self):
        """Called when call ends — clears spiel for fresh start."""
        if self.is_teleprompter:
            self._stop_teleprompter()
        self._insert_placeholder()
        print("[SPIEL] Cleared for new session")

    def destroy(self):
        if self.is_teleprompter:
            self._stop_teleprompter()
        try:
            self.root.destroy()
        except Exception:
            pass
