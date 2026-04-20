"""
=============================================================
MilJoy — AI Call Assistant
main.py — Main Floating Window (Section 12 Update)
=============================================================

PURPOSE:
    Main floating window with spiel panel integration.

    Section 12 additions:
    - 📜 Spiel button in title bar toggles spiel panel
    - Spiel panel opens as separate floating window
    - Also hidden from screen share
    - Cleared automatically when app closes

NOTES FOR DEBUGGING:
    - To re-detect devices: Settings → Re-detect Audio Devices
    - Spiel panel position: right of main window
    - Console shows spiel panel events
=============================================================
"""

import tkinter as tk
import ctypes
import threading
import os
from audio import AudioManager
from ai import AIManager, CALL_PURPOSES
from onboarding import check_and_run_onboarding, SettingsManager
from notetaker import NoteTaker
from spiel import SpielPanel          # [NEW SECTION 12]


# =============================================================
# COLOR PALETTE
# =============================================================

class C:
    BG_DARK      = "#0d1117"
    BG_CARD      = "#161b22"
    BG_INPUT     = "#1c2333"
    BLUE_PRIMARY = "#1e6fbf"
    BLUE_LIGHT   = "#4a90d9"
    BLUE_DEEP    = "#0f3460"
    GREEN        = "#57cc99"
    YELLOW       = "#f7b731"
    RED          = "#ff6b6b"
    TEXT_PRIMARY = "#e6edf3"
    TEXT_MUTED   = "#8b949e"
    BORDER       = "#30363d"


# =============================================================
# SCREEN CAPTURE HIDE
# =============================================================

def hide_from_screen_capture(hwnd):
    try:
        result = ctypes.windll.user32.SetWindowDisplayAffinity(hwnd, 0x11)
        if result:
            print("[✓] MilJoy is HIDDEN from screen capture")
        else:
            print("[!] Could not hide — try running as Administrator")
    except Exception as e:
        print(f"[ERROR] Screen hide: {e}")


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
# MILJOY FLOATING WINDOW
# =============================================================

class MilJoyAssistant:
    """
    MilJoy main floating window.
    Section 12: Spiel panel toggle in title bar.
    """

    def __init__(self, settings):
        print("[MILJOY] Starting floating assistant...")
        self.settings = settings

        self.groq_api_key    = settings.get("groq_api_key", "")
        self.mic_index       = settings.get("mic_device_index", None)
        self.loopback_index  = settings.get("loopback_device_index", None)
        self.persona         = settings.get("persona", "a confident and professional communicator")
        self.persona_context = settings.get("persona_context", "")
        self.user_name       = settings.get("user_name", "")
        self.user_email      = settings.get("user_email", "")

        self.audio_manager  = None
        self.ai_manager     = None
        self.notetaker      = None
        self.spiel_panel    = None     # [NEW SECTION 12]
        self.is_listening   = False
        self.call_purpose   = "Custom"
        self.call_note      = ""

        # Pause state
        self.is_paused          = False
        self.pending_suggestion = None

        self._build_window()
        print("[✓] MilJoy window ready")

        self.root.after(100, self._apply_screen_hide)

        # [NEW] Initialize spiel panel after window is ready
        self.root.after(200, self._init_spiel_panel)

        self.root.bind("<Control-space>", self._on_hotkey)

        self.update_status("Loading MilJoy...", color=C.YELLOW)
        threading.Thread(target=self._init_all, daemon=True).start()
        threading.Thread(target=self._track_launch, daemon=True).start()

    # =============================================================
    # WINDOW BUILDER
    # =============================================================

    def _build_window(self):
        self.root = tk.Tk()
        self.root.title("MilJoy")

        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        w, h = 560, 560
        self.root.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")
        self.root.attributes("-topmost", True)
        self.root.overrideredirect(True)
        self.root.attributes("-alpha", 0.94)
        self.root.configure(bg=C.BG_DARK)

        self._build_title_bar()
        self._build_precall_panel()
        self._build_suggestion_area()
        self._build_transcript_area()
        self._build_controls()
        self._build_status_bar()

    def _build_title_bar(self):
        """Title bar with spiel toggle button."""
        bar = tk.Frame(self.root, bg=C.BLUE_PRIMARY, height=36)
        bar.pack(fill="x", side="top")
        bar.pack_propagate(False)

        left = tk.Frame(bar, bg=C.BLUE_PRIMARY)
        left.pack(side="left", padx=10)

        tk.Label(left, text="🎙", bg=C.BLUE_PRIMARY,
                 font=("Segoe UI", 12)).pack(side="left")
        tk.Label(left, text=" MilJoy", bg=C.BLUE_PRIMARY, fg="#ffffff",
                 font=("Segoe UI", 11, "bold")).pack(side="left")

        if self.user_name:
            tk.Label(left, text=f"  |  Hi {self.user_name}!",
                     bg=C.BLUE_PRIMARY, fg="#c8deff",
                     font=("Segoe UI", 8)).pack(side="left")

        right = tk.Frame(bar, bg=C.BLUE_PRIMARY)
        right.pack(side="right", padx=6)

        # Settings button
        tk.Button(right, text="⚙", bg=C.BLUE_PRIMARY, fg="#c8deff",
                  font=("Segoe UI", 11), bd=0, cursor="hand2",
                  command=self._open_settings).pack(side="left", padx=4)

        # [NEW SECTION 12] Spiel toggle button
        self.spiel_btn = tk.Button(
            right,
            text="📜",
            bg=C.BLUE_PRIMARY, fg="#c8deff",
            font=("Segoe UI", 11), bd=0,
            cursor="hand2",
            command=self._toggle_spiel
        )
        self.spiel_btn.pack(side="left", padx=4)

        # Close button
        tk.Button(right, text="✕", bg=C.BLUE_PRIMARY, fg="#ffffff",
                  font=("Segoe UI", 11, "bold"), bd=0, cursor="hand2",
                  command=self._on_close).pack(side="left", padx=4)

        DragManager(bar, self.root)

    def _build_precall_panel(self):
        """Pre-call setup panel."""
        self.precall_frame = tk.Frame(self.root, bg=C.BG_CARD, padx=14, pady=10)
        self.precall_frame.pack(fill="x")

        header = tk.Frame(self.precall_frame, bg=C.BG_CARD)
        header.pack(fill="x", pady=(0, 8))

        tk.Label(header, text="📋  SET CALL PURPOSE",
                 bg=C.BG_CARD, fg=C.YELLOW,
                 font=("Segoe UI", 7, "bold"), anchor="w").pack(side="left")
        tk.Label(header, text="Set before starting",
                 bg=C.BG_CARD, fg=C.TEXT_MUTED,
                 font=("Segoe UI", 7, "italic")).pack(side="right")

        purposes_frame = tk.Frame(self.precall_frame, bg=C.BG_CARD)
        purposes_frame.pack(fill="x", pady=(0, 8))

        self.purpose_btns = {}
        for i, purpose in enumerate(CALL_PURPOSES.keys()):
            btn = tk.Button(
                purposes_frame,
                text=CALL_PURPOSES[purpose]["label"],
                bg=C.BG_DARK, fg=C.TEXT_MUTED,
                font=("Segoe UI", 8), bd=0,
                padx=8, pady=4, cursor="hand2",
                command=lambda p=purpose: self._select_purpose(p)
            )
            btn.grid(row=0, column=i, padx=2, sticky="ew")
            purposes_frame.columnconfigure(i, weight=1)
            self.purpose_btns[purpose] = btn

        note_frame = tk.Frame(self.precall_frame, bg=C.BG_CARD)
        note_frame.pack(fill="x", pady=(0, 8))

        tk.Label(note_frame, text="Call note (optional):",
                 bg=C.BG_CARD, fg=C.TEXT_MUTED,
                 font=("Segoe UI", 8)).pack(side="left", padx=(0, 8))

        self.call_note_entry = tk.Entry(
            note_frame,
            bg=C.BG_INPUT, fg=C.TEXT_MUTED,
            font=("Segoe UI", 9), bd=0,
            insertbackground=C.TEXT_PRIMARY
        )
        self.call_note_entry.pack(side="left", fill="x", expand=True, ipady=4)
        self.call_note_entry.insert(0, "e.g. Calling TechCorp about their CRM needs")
        self.call_note_entry.bind("<FocusIn>",  self._clear_note_placeholder)
        self.call_note_entry.bind("<FocusOut>", self._restore_note_placeholder)

        self.opening_btn = tk.Button(
            self.precall_frame,
            text="✨  Generate Opening",
            bg=C.BLUE_PRIMARY, fg="#ffffff",
            font=("Segoe UI", 9, "bold"),
            bd=0, padx=12, pady=5,
            cursor="hand2",
            command=self._generate_opening,
            state="disabled"
        )
        self.opening_btn.pack(anchor="w")
        self._select_purpose("Custom")

    def _select_purpose(self, purpose):
        self.call_purpose = purpose
        for p, btn in self.purpose_btns.items():
            btn.config(
                bg=C.BLUE_PRIMARY if p == purpose else C.BG_DARK,
                fg="#ffffff" if p == purpose else C.TEXT_MUTED
            )

    def _clear_note_placeholder(self, event):
        if self.call_note_entry.get().startswith("e.g."):
            self.call_note_entry.delete(0, "end")
            self.call_note_entry.config(fg=C.TEXT_PRIMARY)

    def _restore_note_placeholder(self, event):
        if not self.call_note_entry.get().strip():
            self.call_note_entry.insert(0, "e.g. Calling TechCorp about their CRM needs")
            self.call_note_entry.config(fg=C.TEXT_MUTED)

    def _generate_opening(self):
        if not self.ai_manager:
            return
        note = self.call_note_entry.get().strip()
        if note.startswith("e.g."):
            note = ""
        self.ai_manager.set_call_purpose(self.call_purpose, note)
        self._set_suggestion("✨ Generating opening...")
        self.opening_btn.config(state="disabled", text="Generating...")
        self.update_status("Generating opening...", color=C.YELLOW)

        def on_done(opening):
            self.root.after(0, lambda: self._on_opening_ready(opening))

        self.ai_manager.generate_opening(on_complete=on_done)

    def _on_opening_ready(self, opening):
        self._set_suggestion(opening)
        self.opening_btn.config(state="normal", text="✨  Generate Opening")
        self.update_status("Opening ready! Start listening when ready.", color=C.GREEN)

    def _build_suggestion_area(self):
        """AI suggestion display with pause button."""
        frame = tk.Frame(self.root, bg=C.BG_DARK, padx=14, pady=8)
        frame.pack(fill="x")

        header = tk.Frame(frame, bg=C.BG_DARK)
        header.pack(fill="x")

        tk.Label(header, text="💡  SUGGESTED RESPONSE",
                 bg=C.BG_DARK, fg=C.BLUE_LIGHT,
                 font=("Segoe UI", 7, "bold"), anchor="w").pack(side="left")

        self.pause_btn = tk.Button(
            header,
            text="⏸ Pause",
            bg=C.BG_CARD, fg=C.TEXT_MUTED,
            font=("Segoe UI", 7), bd=0,
            padx=6, pady=2,
            cursor="hand2",
            command=self._toggle_pause
        )
        self.pause_btn.pack(side="right", padx=(4, 0))

        self.generating_label = tk.Label(
            header, text="",
            bg=C.BG_DARK, fg=C.YELLOW,
            font=("Segoe UI", 7, "italic")
        )
        self.generating_label.pack(side="right")

        self.suggestion_text = tk.Text(
            frame,
            bg=C.BLUE_DEEP, fg=C.TEXT_PRIMARY,
            font=("Segoe UI", 12),
            wrap="word", bd=0,
            padx=10, pady=8,
            state="disabled", cursor="arrow",
            height=4, relief="flat"
        )
        self.suggestion_text.pack(fill="x", pady=(6, 0))
        self.suggestion_text.bind("<Enter>", self._on_suggestion_hover)
        self.suggestion_text.bind("<Leave>", self._on_suggestion_unhover)

        self._set_suggestion(
            "Set your call purpose above and click\n"
            "✨ Generate Opening to get started!\n\n"
            "📜 Click the scroll icon in the title bar to open your Spiel panel."
        )

    def _build_transcript_area(self):
        frame = tk.Frame(self.root, bg=C.BG_DARK, padx=14, pady=4)
        frame.pack(fill="both", expand=True)

        tk.Label(frame, text="🎤  LIVE TRANSCRIPT",
                 bg=C.BG_DARK, fg=C.GREEN,
                 font=("Segoe UI", 7, "bold"), anchor="w").pack(fill="x")

        scroll_frame = tk.Frame(frame, bg=C.BG_DARK)
        scroll_frame.pack(fill="both", expand=True, pady=(6, 0))

        sb = tk.Scrollbar(scroll_frame)
        sb.pack(side="right", fill="y")

        self.transcript_text = tk.Text(
            scroll_frame,
            bg=C.BG_CARD, fg=C.TEXT_MUTED,
            font=("Segoe UI", 11),
            wrap="word", bd=0,
            padx=10, pady=6,
            state="disabled", cursor="arrow",
            height=4, relief="flat",
            yscrollcommand=sb.set
        )
        self.transcript_text.pack(side="left", fill="both", expand=True)
        sb.config(command=self.transcript_text.yview)

        self.transcript_text.tag_configure("YOU",  foreground=C.GREEN)
        self.transcript_text.tag_configure("THEM", foreground=C.BLUE_LIGHT)
        self.transcript_text.tag_configure("TEXT", foreground=C.TEXT_MUTED)

    def _build_controls(self):
        frame = tk.Frame(self.root, bg=C.BG_CARD, pady=8)
        frame.pack(fill="x", padx=14, pady=(4, 0))

        self.listen_btn = tk.Button(
            frame, text="▶  Start Listening",
            bg=C.GREEN, fg=C.BG_DARK,
            font=("Segoe UI", 9, "bold"),
            bd=0, padx=14, pady=5,
            cursor="hand2", state="disabled",
            command=self._toggle_listening
        )
        self.listen_btn.pack(side="left")

        self.suggest_btn = tk.Button(
            frame, text="💡  Suggest",
            bg=C.BLUE_PRIMARY, fg="#ffffff",
            font=("Segoe UI", 9, "bold"),
            bd=0, padx=12, pady=5,
            cursor="hand2", state="disabled",
            command=self._on_manual_suggest
        )
        self.suggest_btn.pack(side="left", padx=(8, 0))

        tk.Button(
            frame, text="✕ Clear",
            bg=C.BG_DARK, fg=C.TEXT_MUTED,
            font=("Segoe UI", 9),
            bd=0, padx=10, pady=5,
            cursor="hand2",
            command=self._clear_transcript
        ).pack(side="left", padx=(8, 0))

    def _build_status_bar(self):
        self.status_bar = tk.Label(
            self.root,
            text="● Initializing MilJoy...",
            bg=C.BG_CARD, fg=C.GREEN,
            font=("Segoe UI", 7),
            anchor="w", padx=14
        )
        self.status_bar.pack(fill="x", side="bottom", ipady=5)

    # =============================================================
    # SPIEL PANEL
    # =============================================================

    def _init_spiel_panel(self):
        """
        [NEW SECTION 12]
        Initializes the spiel panel after main window is ready.
        """
        try:
            self.spiel_panel = SpielPanel(self.root)
            print("[✓] Spiel panel initialized")
        except Exception as e:
            print(f"[ERROR] Spiel panel init failed: {e}")

    def _toggle_spiel(self):
        """
        [NEW SECTION 12]
        Toggles spiel panel visibility.
        Updates spiel button appearance.
        """
        if self.spiel_panel is None:
            return

        self.spiel_panel.toggle()

        # Update button to show state
        if self.spiel_panel.is_visible:
            self.spiel_btn.config(fg="#ffffff")   # Bright when visible
        else:
            self.spiel_btn.config(fg="#c8deff")   # Dimmed when hidden

    # =============================================================
    # PAUSE SYSTEM
    # =============================================================

    def _toggle_pause(self):
        if not self.is_paused:
            self._pause()
        else:
            self._resume()

    def _pause(self):
        self.is_paused = True
        self.pause_btn.config(text="▶ Resume", bg=C.YELLOW, fg=C.BG_DARK)
        self.suggestion_text.config(bg="#1a3a6e")
        self.update_status("⏸ Paused — suggestion frozen", color=C.YELLOW)
        print("[PAUSE] Paused")

    def _resume(self):
        self.is_paused = False
        self.pause_btn.config(text="⏸ Pause", bg=C.BG_CARD, fg=C.TEXT_MUTED)
        self.suggestion_text.config(bg=C.BLUE_DEEP)
        self.update_status("▶ Resumed", color=C.GREEN)
        print("[PAUSE] Resumed")

        if self.pending_suggestion:
            self._set_suggestion(self.pending_suggestion)
            self.pending_suggestion = None

    def _on_suggestion_hover(self, event):
        if not self.is_paused and self.is_listening:
            self._pause()

    def _on_suggestion_unhover(self, event):
        if self.is_paused and self.is_listening:
            self._resume()

    # =============================================================
    # INITIALIZATION
    # =============================================================

    def _init_all(self):
        try:
            self.audio_manager = AudioManager(
                on_transcript_callback=self._on_transcript,
                mic_index=self.mic_index,
                loopback_index=self.loopback_index
            )

            if self.groq_api_key:
                self.ai_manager = AIManager(
                    api_key=self.groq_api_key,
                    on_suggestion_callback=lambda t: self.root.after(
                        0, lambda: self._on_suggestion(t)
                    )
                )
                self.ai_manager.set_persona(self.persona, self.persona_context)

            self.notetaker = NoteTaker(self.settings)
            self.root.after(0, self._on_ready)

        except Exception as e:
            err = str(e)
            print(f"[ERROR] Init failed: {err}")
            self.root.after(0, lambda: self.update_status(f"Error: {err}", color=C.RED))

    def _on_ready(self):
        self.listen_btn.config(state="normal")
        if self.ai_manager:
            self.opening_btn.config(state="normal")
        self.update_status("Ready  |  📜 Click scroll icon for Spiel panel")
        print("[✓] MilJoy fully ready")

    def _track_launch(self):
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location(
                "security",
                os.path.join(os.path.dirname(os.path.abspath(__file__)), "security.py")
            )
            if spec:
                security = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(security)
                security.UsageTracker().track_launch()
        except Exception:
            pass

    # =============================================================
    # AI METHODS
    # =============================================================

    def _on_suggestion(self, text):
        if self.is_paused:
            self.pending_suggestion = text
            return
        self._set_suggestion(text)
        self.generating_label.config(text="")
        self.update_status("Suggestion ready  |  Ctrl+Space for another", color=C.GREEN)
        if self.ai_manager:
            self.ai_manager.set_current_suggestion(text)

    def _on_hotkey(self, event=None):
        self._trigger_suggestion()

    def _on_manual_suggest(self):
        self._trigger_suggestion()

    def _trigger_suggestion(self):
        if not self.ai_manager:
            self.update_status("No API key", color=C.RED)
            return
        if not self.is_listening:
            self.update_status("Start listening first", color=C.YELLOW)
            return
        transcript = self.audio_manager.get_transcript_history()
        if not transcript:
            self.update_status("No transcript yet", color=C.YELLOW)
            return
        if self.is_paused:
            self._resume()
        self.generating_label.config(text="⟳ Generating...")
        self.update_status("Generating suggestion...", color=C.YELLOW)
        self.ai_manager.trigger_now(transcript)

    # =============================================================
    # AUDIO METHODS
    # =============================================================

    def _toggle_listening(self):
        if not self.is_listening:
            if self.ai_manager:
                note = self.call_note_entry.get().strip()
                if note.startswith("e.g."):
                    note = ""
                self.ai_manager.set_call_purpose(self.call_purpose, note)

            self.audio_manager.start()
            self.is_listening = True
            self.listen_btn.config(text="■  Stop Listening", bg=C.RED, fg="#ffffff")
            self.suggest_btn.config(state="normal")
            self.update_status(
                f"Listening  |  {CALL_PURPOSES[self.call_purpose]['label']}  |  Ctrl+Space",
                color=C.BLUE_LIGHT
            )
            self._collapse_precall_panel()

        else:
            self.audio_manager.stop()
            self.is_listening = False
            self.listen_btn.config(text="▶  Start Listening", bg=C.GREEN, fg=C.BG_DARK)
            self.suggest_btn.config(state="disabled")

            if self.is_paused:
                self._resume()

            # [NEW] Clear spiel for new session
            if self.spiel_panel:
                self.spiel_panel.clear_for_new_session()

            self._on_call_ended()

    def _on_call_ended(self):
        if not self.notetaker:
            self.update_status("Stopped", color=C.TEXT_MUTED)
            self._show_precall_panel()
            return

        transcript = self.audio_manager.get_transcript_history()
        if not transcript:
            self.update_status("Stopped — no transcript", color=C.TEXT_MUTED)
            self._show_precall_panel()
            return

        self.update_status("📝 Processing call notes...", color=C.YELLOW)
        self._set_suggestion("📝 Generating call summary...\nThis will be emailed to you shortly.")

        def on_done(status):
            self.root.after(0, lambda: self.update_status(f"✓ {status}", color=C.GREEN))
            self.root.after(0, self._show_precall_panel)

        self.notetaker.on_call_ended(
            transcript_history=transcript,
            call_purpose=self.call_purpose,
            on_complete=on_done
        )

    def _collapse_precall_panel(self):
        self.precall_frame.pack_forget()

    def _show_precall_panel(self):
        slaves = self.root.pack_slaves()
        if slaves:
            self.precall_frame.pack(fill="x", after=slaves[0])

    def _on_transcript(self, text, speaker):
        self.root.after(0, lambda: self._append_transcript(text, speaker))
        if self.ai_manager:
            transcript = self.audio_manager.get_transcript_history()
            if speaker == "THEM":
                self.root.after(0, lambda: self.generating_label.config(text="⟳ Generating..."))
            self.ai_manager.on_transcript_update(transcript, speaker=speaker)

    def _append_transcript(self, text, speaker):
        self.transcript_text.config(state="normal")
        self.transcript_text.insert("end", f"{speaker}: ", speaker)
        self.transcript_text.insert("end", f"{text}\n", "TEXT")
        self.transcript_text.see("end")
        self.transcript_text.config(state="disabled")

    def _clear_transcript(self):
        self.transcript_text.config(state="normal")
        self.transcript_text.delete("1.0", "end")
        self.transcript_text.config(state="disabled")
        if self.audio_manager:
            self.audio_manager.transcript_history = []
        self._set_suggestion("Transcript cleared.")

    # =============================================================
    # HELPERS
    # =============================================================

    def _apply_screen_hide(self):
        hwnd = ctypes.windll.user32.FindWindowW(None, "MilJoy")
        if hwnd == 0:
            hwnd = self.root.winfo_id()
        hide_from_screen_capture(hwnd)

    def _set_suggestion(self, text):
        self.suggestion_text.config(state="normal")
        self.suggestion_text.delete("1.0", "end")
        self.suggestion_text.insert("1.0", text)
        self.suggestion_text.config(state="disabled")

    def update_status(self, message, color=None):
        color = color or C.GREEN
        print(f"[STATUS] {message}")
        self.status_bar.config(text=f"●  {message}", fg=color)

    def _open_settings(self):
        win = tk.Toplevel(self.root)
        win.title("MilJoy Settings")
        win.configure(bg=C.BG_DARK)
        win.geometry("340x300")
        win.attributes("-topmost", True)

        tk.Label(win, text="🎙 MilJoy Settings",
                 bg=C.BG_DARK, fg=C.TEXT_PRIMARY,
                 font=("Segoe UI", 13, "bold")).pack(pady=(16, 8))

        tk.Label(win,
                 text=f"AI: {self.settings.get('ai_provider','groq').upper()}\n"
                      f"Role: {self.settings.get('persona_role','General')}\n"
                      f"User: {self.settings.get('user_name','—')}\n"
                      f"Email: {self.settings.get('user_email','—')}",
                 bg=C.BG_DARK, fg=C.TEXT_MUTED,
                 font=("Segoe UI", 9), justify="center").pack(pady=(0, 8))

        tk.Label(win, text="📁 Notes: Documents/MilJoy Notes/",
                 bg=C.BG_DARK, fg=C.TEXT_MUTED,
                 font=("Segoe UI", 8)).pack(pady=(0, 8))

        tk.Button(win, text="🔍 Re-detect Audio Devices",
                  bg=C.BLUE_PRIMARY, fg="#ffffff",
                  font=("Segoe UI", 9), bd=0,
                  padx=12, pady=6, cursor="hand2",
                  command=lambda: self._redetect_devices(win)).pack(pady=(0, 8))

        tk.Button(win, text="Reset Setup & Restart",
                  bg=C.RED, fg="#ffffff",
                  font=("Segoe UI", 9), bd=0,
                  padx=12, pady=6, cursor="hand2",
                  command=lambda: self._reset(win)).pack()

    def _redetect_devices(self, win):
        from audio import AutoDeviceDetector
        mic, spk = AutoDeviceDetector.detect_all(force_redetect=True)
        win.destroy()

    def _reset(self, win):
        SettingsManager.reset()
        win.destroy()
        self._on_close()

    def _on_close(self):
        print("[MILJOY] Closing...")

        # Clean up spiel panel
        if self.spiel_panel:
            self.spiel_panel.destroy()

        if self.audio_manager and self.is_listening:
            self.audio_manager.stop()

        self.root.destroy()

    def run(self):
        self.root.mainloop()


# =============================================================
# ENTRY POINT
# =============================================================

def launch_miljoy(settings):
    MilJoyAssistant(settings).run()


if __name__ == "__main__":
    print("==============================================")
    print("  MilJoy — AI Call Assistant")
    print("==============================================")
    check_and_run_onboarding(launch_miljoy)
    print("[MILJOY] Closed.")
