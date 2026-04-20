"""
=============================================================
MilJoy — AI Call Assistant
onboarding.py — Setup Wizard (Section 9 Update)
=============================================================

PURPOSE:
    First-launch onboarding wizard.
    Section 9 update: collects user email for call summaries
    and sender Gmail credentials for email delivery.

NOTES FOR DEBUGGING:
    - To reset: delete settings.json from app folder
    - Sender email/password: app owner's Gmail + app password
    - User email: where call summaries are sent
=============================================================
"""

import tkinter as tk
import json
import os
import threading
import sounddevice as sd


# =============================================================
# SETTINGS MANAGER
# =============================================================

SETTINGS_FILE = "settings.json"

DEFAULT_SETTINGS = {
    "onboarding_complete":  False,
    "ai_provider":          "groq",
    "groq_api_key":         "",
    "persona":              "a confident and professional communicator",
    "persona_role":         "General",
    "persona_context":      "",
    "mic_device_index":     22,
    "loopback_device_index": 1,
    "user_name":            "",
    "user_email":           "",       # [NEW] User's Gmail for receiving summaries
    "sender_email":         "",       # [NEW] App owner's Gmail for sending
    "sender_password":      "",       # [NEW] App owner's Gmail app password
}


class SettingsManager:
    @staticmethod
    def load():
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r") as f:
                    settings = json.load(f)
                print(f"[SETTINGS] Loaded from {SETTINGS_FILE}")
                merged = DEFAULT_SETTINGS.copy()
                merged.update(settings)
                return merged
            except Exception as e:
                print(f"[ERROR] Could not load settings: {e}")
                return DEFAULT_SETTINGS.copy()
        print("[SETTINGS] No settings file — first launch")
        return DEFAULT_SETTINGS.copy()

    @staticmethod
    def save(settings):
        try:
            with open(SETTINGS_FILE, "w") as f:
                json.dump(settings, f, indent=2)
            print(f"[SETTINGS] Saved to {SETTINGS_FILE}")
            return True
        except Exception as e:
            print(f"[ERROR] Could not save: {e}")
            return False

    @staticmethod
    def is_onboarding_complete():
        s = SettingsManager.load()
        return s.get("onboarding_complete", False) and bool(s.get("groq_api_key", ""))

    @staticmethod
    def reset():
        if os.path.exists(SETTINGS_FILE):
            os.remove(SETTINGS_FILE)
            print("[SETTINGS] Reset complete")


# =============================================================
# COLOR PALETTE
# =============================================================

class C:
    BG_DARK      = "#0d1117"
    BG_CARD      = "#161b22"
    BG_INPUT     = "#1c2333"
    BLUE_PRIMARY = "#1e6fbf"
    GREEN        = "#57cc99"
    YELLOW       = "#f7b731"
    RED          = "#ff6b6b"
    TEXT_PRIMARY = "#e6edf3"
    TEXT_MUTED   = "#8b949e"
    BORDER       = "#30363d"


# =============================================================
# ONBOARDING WINDOW
# =============================================================

class OnboardingWindow:
    """MilJoy setup wizard — shown on first launch only."""

    def __init__(self, on_complete_callback):
        self.on_complete = on_complete_callback
        self.settings = DEFAULT_SETTINGS.copy()
        self.current_step = 0
        self.total_steps = 6          # Added email step
        self.detected_mic = None
        self.detected_loopback = None

        self._build_window()
        self._show_step(0)
        print("[ONBOARDING] MilJoy setup wizard opened")

    def _build_window(self):
        self.root = tk.Tk()
        self.root.title("MilJoy — Setup")
        self.root.configure(bg=C.BG_DARK)
        self.root.resizable(False, False)

        w, h = 520, 680
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        self.root.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")
        self.root.attributes("-topmost", True)

        self._build_header()
        self._build_progress_bar()

        self.content_frame = tk.Frame(self.root, bg=C.BG_DARK)
        self.content_frame.pack(fill="both", expand=True, padx=30, pady=10)

        self._build_nav_buttons()

    def _build_header(self):
        header = tk.Frame(self.root, bg=C.BLUE_PRIMARY, pady=10)
        header.pack(fill="x")

        logo = tk.Frame(header, bg=C.BLUE_PRIMARY)
        logo.pack()

        tk.Label(logo, text="🎙", bg=C.BLUE_PRIMARY,
                 font=("Segoe UI", 18)).pack(side="left", padx=(0, 6))
        tk.Label(logo, text="MilJoy", bg=C.BLUE_PRIMARY, fg="#ffffff",
                 font=("Segoe UI", 18, "bold")).pack(side="left")

        tk.Label(header, text="AI Call Assistant",
                 bg=C.BLUE_PRIMARY, fg="#c8deff",
                 font=("Segoe UI", 9)).pack()

    def _build_progress_bar(self):
        frame = tk.Frame(self.root, bg=C.BG_CARD, pady=10)
        frame.pack(fill="x")

        self.step_label = tk.Label(frame, text="Step 1 of 6",
                                    bg=C.BG_CARD, fg=C.TEXT_MUTED,
                                    font=("Segoe UI", 8))
        self.step_label.pack()

        bar_bg = tk.Frame(frame, bg=C.BORDER, height=3)
        bar_bg.pack(fill="x", padx=30, pady=(6, 0))
        bar_bg.pack_propagate(False)

        self.progress_fill = tk.Frame(bar_bg, bg=C.BLUE_PRIMARY, height=3)
        self.progress_fill.place(x=0, y=0, relheight=1, relwidth=1/6)

    def _build_nav_buttons(self):
        nav = tk.Frame(self.root, bg=C.BG_CARD, pady=12)
        nav.pack(fill="x", side="bottom")

        self.back_btn = tk.Button(nav, text="← Back",
                                   bg=C.BG_CARD, fg=C.TEXT_MUTED,
                                   font=("Segoe UI", 10), bd=0,
                                   padx=20, pady=6, cursor="hand2",
                                   command=self._go_back)
        self.back_btn.pack(side="left", padx=20)

        self.next_btn = tk.Button(nav, text="Next →",
                                   bg=C.BLUE_PRIMARY, fg="#ffffff",
                                   font=("Segoe UI", 10, "bold"), bd=0,
                                   padx=20, pady=6, cursor="hand2",
                                   command=self._go_next)
        self.next_btn.pack(side="right", padx=20)

    def _update_progress(self, step):
        self.step_label.config(text=f"Step {step + 1} of {self.total_steps}")
        self.progress_fill.place(relwidth=(step + 1) / self.total_steps)
        self.back_btn.config(
            state="disabled" if step == 0 else "normal",
            fg=C.BG_CARD if step == 0 else C.TEXT_MUTED
        )
        if step == self.total_steps - 1:
            self.next_btn.config(text="🚀  Launch MilJoy",
                                  bg=C.GREEN, fg="#0d1117")
        else:
            self.next_btn.config(text="Next →",
                                  bg=C.BLUE_PRIMARY, fg="#ffffff")

    def _clear_content(self):
        for w in self.content_frame.winfo_children():
            w.destroy()

    def _show_step(self, step):
        self._clear_content()
        self._update_progress(step)
        self.current_step = step
        steps = [
            self._build_step_welcome,
            self._build_step_vbaudio,
            self._build_step_ai_provider,
            self._build_step_persona,
            self._build_step_email,       # [NEW SECTION 9]
            self._build_step_audio_check
        ]
        steps[step]()
        print(f"[ONBOARDING] Step {step + 1}")

    def _go_next(self):
        if not self._validate_step(self.current_step):
            return
        if self.current_step < self.total_steps - 1:
            self._show_step(self.current_step + 1)
        else:
            self._complete_onboarding()

    def _go_back(self):
        if self.current_step > 0:
            self._show_step(self.current_step - 1)

    def _validate_step(self, step):
        if step == 2:
            key = self.api_key_entry.get().strip()
            if not key.startswith("gsk_"):
                self._show_error("Please enter a valid Groq API key (starts with gsk_)")
                return False
            self.settings["groq_api_key"] = key
            self.settings["ai_provider"] = "groq"

        if step == 3:
            name = self.name_entry.get().strip()
            context = self.context_entry.get("1.0", "end").strip()
            role = self.selected_role.get()
            self.settings["user_name"] = name
            self.settings["persona_role"] = role
            self.settings["persona_context"] = context
            role_personas = {
                "Sales":     "a confident sales professional",
                "Interview": "a job candidate in an interview",
                "Meeting":   "a professional in a business meeting",
                "General":   "a confident and professional communicator",
                "Custom":    f"a professional named {name}" if name else "a professional"
            }
            self.settings["persona"] = role_personas.get(role, role_personas["General"])

        if step == 4:
            # [NEW SECTION 9] Email validation
            user_email = self.user_email_entry.get().strip()
            sender_email = self.sender_email_entry.get().strip()
            sender_password = self.sender_password_entry.get().strip()

            if not user_email or "@" not in user_email:
                self._show_error("Please enter a valid Gmail address")
                return False

            self.settings["user_email"] = user_email
            # Sender credentials are hardcoded in notetaker.py
            # not stored in settings or shown to users

        return True

    def _show_error(self, message):
        for w in self.content_frame.winfo_children():
            if hasattr(w, '_is_error'):
                w.destroy()
        lbl = tk.Label(self.content_frame,
                        text=f"⚠  {message}",
                        bg=C.BG_DARK, fg=C.RED,
                        font=("Segoe UI", 9), wraplength=440)
        lbl._is_error = True
        lbl.pack(pady=(0, 6))

    # =============================================================
    # STEP BUILDERS
    # =============================================================

    def _build_step_welcome(self):
        tk.Label(self.content_frame, text="Welcome to MilJoy! 👋",
                  bg=C.BG_DARK, fg=C.TEXT_PRIMARY,
                  font=("Segoe UI", 20, "bold")).pack(pady=(16, 6))

        tk.Label(self.content_frame,
                  text="Your real-time AI co-pilot for every call.",
                  bg=C.BG_DARK, fg=C.TEXT_MUTED,
                  font=("Segoe UI", 11)).pack(pady=(0, 20))

        features = [
            ("🎤", "Listens to both sides of your conversation"),
            ("🤖", "Generates smart suggested responses instantly"),
            ("👻", "Completely invisible to screen share"),
            ("⌨️", "Press Ctrl+Space anytime for a new suggestion"),
            ("📝", "Sends you a call summary after every call"),
            ("💾", "Remembers your settings — set up once, use forever"),
        ]

        for icon, text in features:
            row = tk.Frame(self.content_frame, bg=C.BG_CARD, pady=8)
            row.pack(fill="x", pady=2)
            tk.Label(row, text=icon, bg=C.BG_CARD,
                      font=("Segoe UI", 13)).pack(side="left", padx=(14, 8))
            tk.Label(row, text=text, bg=C.BG_CARD, fg=C.TEXT_PRIMARY,
                      font=("Segoe UI", 10), anchor="w").pack(side="left")

        tk.Label(self.content_frame,
                  text="This setup takes about 3 minutes.",
                  bg=C.BG_DARK, fg=C.TEXT_MUTED,
                  font=("Segoe UI", 9, "italic")).pack(pady=(14, 0))

    def _build_step_vbaudio(self):
        tk.Label(self.content_frame, text="🔊  Audio Setup",
                  bg=C.BG_DARK, fg=C.TEXT_PRIMARY,
                  font=("Segoe UI", 16, "bold")).pack(pady=(10, 4))

        tk.Label(self.content_frame,
                  text="MilJoy needs VB-Audio Virtual Cable (free)\nto hear both sides of your call.",
                  bg=C.BG_DARK, fg=C.TEXT_MUTED,
                  font=("Segoe UI", 10), justify="center").pack(pady=(0, 12))

        steps = [
            ("1", "Download VB-Audio Virtual Cable",  "vb-audio.com/Cable  —  100% free"),
            ("2", "Run installer as Administrator",    "Right-click → Run as administrator"),
            ("3", "Restart your computer",             "Required after installation"),
            ("4", "Set CABLE Input as default output", "Right-click speaker → Sound Settings → Playback"),
            ("5", "Enable Listen on CABLE Output",     "Recording tab → CABLE Output → Properties → Listen"),
        ]

        for num, title, desc in steps:
            row = tk.Frame(self.content_frame, bg=C.BG_CARD, pady=6)
            row.pack(fill="x", pady=2)
            tk.Label(row, text=num, bg=C.BLUE_PRIMARY, fg="#ffffff",
                      font=("Segoe UI", 9, "bold"), width=2).pack(side="left", padx=(10, 8))
            col = tk.Frame(row, bg=C.BG_CARD)
            col.pack(side="left", fill="x", expand=True)
            tk.Label(col, text=title, bg=C.BG_CARD, fg=C.TEXT_PRIMARY,
                      font=("Segoe UI", 9, "bold"), anchor="w").pack(fill="x")
            tk.Label(col, text=desc, bg=C.BG_CARD, fg=C.TEXT_MUTED,
                      font=("Segoe UI", 8), anchor="w").pack(fill="x")

        self.vbaudio_done = tk.BooleanVar(value=False)
        tk.Checkbutton(self.content_frame,
                        text="I already have VB-Audio installed ✓",
                        variable=self.vbaudio_done,
                        bg=C.BG_DARK, fg=C.GREEN,
                        selectcolor=C.BG_DARK,
                        font=("Segoe UI", 9),
                        activebackground=C.BG_DARK).pack(pady=(10, 0))

    def _build_step_ai_provider(self):
        tk.Label(self.content_frame, text="🤖  Connect Groq AI",
                  bg=C.BG_DARK, fg=C.TEXT_PRIMARY,
                  font=("Segoe UI", 16, "bold")).pack(pady=(10, 4))

        tk.Label(self.content_frame,
                  text="MilJoy uses Groq for ultra-fast AI suggestions.\nGet your free API key at console.groq.com",
                  bg=C.BG_DARK, fg=C.TEXT_MUTED,
                  font=("Segoe UI", 10), justify="center").pack(pady=(0, 16))

        # Steps to get API key
        steps_frame = tk.Frame(self.content_frame, bg=C.BG_CARD, pady=10)
        steps_frame.pack(fill="x", pady=(0, 14))

        for num, text in [
            ("1", "Go to console.groq.com and sign up free"),
            ("2", "Click 'API Keys' in the left menu"),
            ("3", "Click 'Create API Key'"),
            ("4", "Copy and paste it below"),
        ]:
            row = tk.Frame(steps_frame, bg=C.BG_CARD)
            row.pack(fill="x", padx=12, pady=2)
            tk.Label(row, text=f"{num}.", bg=C.BG_CARD, fg=C.BLUE_PRIMARY,
                      font=("Segoe UI", 9, "bold"), width=2).pack(side="left")
            tk.Label(row, text=text, bg=C.BG_CARD, fg=C.TEXT_PRIMARY,
                      font=("Segoe UI", 9), anchor="w").pack(side="left")

        tk.Label(self.content_frame,
                  text="Groq API Key",
                  bg=C.BG_DARK, fg=C.TEXT_MUTED,
                  font=("Segoe UI", 9), anchor="w").pack(fill="x", pady=(8, 4))

        self.api_key_entry = tk.Entry(
            self.content_frame,
            bg=C.BG_INPUT, fg=C.TEXT_PRIMARY,
            font=("Segoe UI", 10), bd=0,
            insertbackground=C.TEXT_PRIMARY,
            show="•"
        )
        self.api_key_entry.pack(fill="x", ipady=8, pady=(0, 4))

        existing = SettingsManager.load().get("groq_api_key", "")
        if existing:
            self.api_key_entry.insert(0, existing)

        self.show_key = tk.BooleanVar(value=False)
        tk.Checkbutton(self.content_frame, text="Show API key",
                        variable=self.show_key,
                        command=lambda: self.api_key_entry.config(
                            show="" if self.show_key.get() else "•"),
                        bg=C.BG_DARK, fg=C.TEXT_MUTED,
                        selectcolor=C.BG_DARK,
                        font=("Segoe UI", 8),
                        activebackground=C.BG_DARK).pack(anchor="w")

    def _build_step_persona(self):
        tk.Label(self.content_frame, text="👤  Your Profile",
                  bg=C.BG_DARK, fg=C.TEXT_PRIMARY,
                  font=("Segoe UI", 16, "bold")).pack(pady=(10, 4))

        tk.Label(self.content_frame,
                  text="Help MilJoy understand who you are\nso suggestions fit your situation perfectly.",
                  bg=C.BG_DARK, fg=C.TEXT_MUTED,
                  font=("Segoe UI", 10), justify="center").pack(pady=(0, 12))

        tk.Label(self.content_frame, text="Your name (optional)",
                  bg=C.BG_DARK, fg=C.TEXT_MUTED,
                  font=("Segoe UI", 9), anchor="w").pack(fill="x")

        self.name_entry = tk.Entry(
            self.content_frame,
            bg=C.BG_INPUT, fg=C.TEXT_PRIMARY,
            font=("Segoe UI", 11), bd=0,
            insertbackground=C.TEXT_PRIMARY
        )
        self.name_entry.pack(fill="x", ipady=8, pady=(4, 12))

        saved_name = SettingsManager.load().get("user_name", "")
        if saved_name:
            self.name_entry.insert(0, saved_name)

        tk.Label(self.content_frame,
                  text="What best describes your use case?",
                  bg=C.BG_DARK, fg=C.TEXT_MUTED,
                  font=("Segoe UI", 9), anchor="w").pack(fill="x")

        self.selected_role = tk.StringVar(value="General")
        roles_frame = tk.Frame(self.content_frame, bg=C.BG_DARK)
        roles_frame.pack(fill="x", pady=(6, 12))

        for i, role in enumerate(["Sales", "Interview", "Meeting", "General", "Custom"]):
            tk.Radiobutton(roles_frame, text=role,
                            variable=self.selected_role, value=role,
                            bg=C.BG_DARK, fg=C.TEXT_PRIMARY,
                            selectcolor=C.BG_DARK,
                            activebackground=C.BG_DARK,
                            font=("Segoe UI", 10)).grid(row=0, column=i, padx=6)

        self.selected_role.set(SettingsManager.load().get("persona_role", "General"))

        tk.Label(self.content_frame,
                  text="Extra context for MilJoy (optional)",
                  bg=C.BG_DARK, fg=C.TEXT_MUTED,
                  font=("Segoe UI", 9), anchor="w").pack(fill="x")

        tk.Label(self.content_frame,
                  text='e.g. "Selling CRM software to small business owners"',
                  bg=C.BG_DARK, fg="#6a7a9a",
                  font=("Segoe UI", 8, "italic"), anchor="w").pack(fill="x", pady=(0, 4))

        self.context_entry = tk.Text(
            self.content_frame,
            bg=C.BG_INPUT, fg=C.TEXT_PRIMARY,
            font=("Segoe UI", 10), bd=0,
            insertbackground=C.TEXT_PRIMARY,
            height=3, wrap="word"
        )
        self.context_entry.pack(fill="x")

        saved_context = SettingsManager.load().get("persona_context", "")
        if saved_context:
            self.context_entry.insert("1.0", saved_context)

    def _build_step_email(self):
        """
        [NEW SECTION 9]
        Collects user email and sender Gmail credentials.
        User email = where summaries are sent.
        Sender credentials = app owner's Gmail for sending.
        """
        tk.Label(self.content_frame, text="📧  Email Setup",
                  bg=C.BG_DARK, fg=C.TEXT_PRIMARY,
                  font=("Segoe UI", 16, "bold")).pack(pady=(10, 4))

        tk.Label(self.content_frame,
                  text="MilJoy will email you a call summary\nafter every call automatically.",
                  bg=C.BG_DARK, fg=C.TEXT_MUTED,
                  font=("Segoe UI", 10), justify="center").pack(pady=(0, 14))

        # User email
        tk.Label(self.content_frame,
                  text="Your Gmail address  —  where summaries will be sent",
                  bg=C.BG_DARK, fg=C.TEXT_MUTED,
                  font=("Segoe UI", 9), anchor="w").pack(fill="x")

        self.user_email_entry = tk.Entry(
            self.content_frame,
            bg=C.BG_INPUT, fg=C.TEXT_PRIMARY,
            font=("Segoe UI", 11), bd=0,
            insertbackground=C.TEXT_PRIMARY
        )
        self.user_email_entry.pack(fill="x", ipady=8, pady=(4, 12))

        saved_email = SettingsManager.load().get("user_email", "")
        if saved_email:
            self.user_email_entry.insert(0, saved_email)

        # Simple note for users
        tk.Label(self.content_frame,
                  text="✓  MilJoy will automatically email your\n"
                       "call summaries to this address after every call.",
                  bg=C.BG_CARD, fg=C.GREEN,
                  font=("Segoe UI", 9), justify="center",
                  pady=10).pack(fill="x", pady=(8, 0))

        # Dummy entries to prevent validation errors
        self.sender_email_entry = tk.Entry(self.content_frame)
        self.sender_password_entry = tk.Entry(self.content_frame)

    def _build_step_audio_check(self):
        tk.Label(self.content_frame, text="🎤  Audio Check",
                  bg=C.BG_DARK, fg=C.TEXT_PRIMARY,
                  font=("Segoe UI", 16, "bold")).pack(pady=(10, 4))

        tk.Label(self.content_frame,
                  text="MilJoy is checking your audio devices...",
                  bg=C.BG_DARK, fg=C.TEXT_MUTED,
                  font=("Segoe UI", 10)).pack(pady=(0, 14))

        # Mic row
        mic_row = tk.Frame(self.content_frame, bg=C.BG_CARD, pady=12)
        mic_row.pack(fill="x", pady=4)
        self.mic_icon = tk.Label(mic_row, text="⟳", bg=C.BG_CARD,
                                  fg=C.YELLOW, font=("Segoe UI", 16))
        self.mic_icon.pack(side="left", padx=14)
        mic_col = tk.Frame(mic_row, bg=C.BG_CARD)
        mic_col.pack(side="left")
        tk.Label(mic_col, text="Microphone", bg=C.BG_CARD,
                  fg=C.TEXT_PRIMARY, font=("Segoe UI", 10, "bold")).pack(anchor="w")
        self.mic_status = tk.Label(mic_col, text="Detecting...",
                                    bg=C.BG_CARD, fg=C.TEXT_MUTED,
                                    font=("Segoe UI", 8))
        self.mic_status.pack(anchor="w")

        # Cable row
        cable_row = tk.Frame(self.content_frame, bg=C.BG_CARD, pady=12)
        cable_row.pack(fill="x", pady=4)
        self.cable_icon = tk.Label(cable_row, text="⟳", bg=C.BG_CARD,
                                    fg=C.YELLOW, font=("Segoe UI", 16))
        self.cable_icon.pack(side="left", padx=14)
        cable_col = tk.Frame(cable_row, bg=C.BG_CARD)
        cable_col.pack(side="left")
        tk.Label(cable_col, text="VB-Audio CABLE Output", bg=C.BG_CARD,
                  fg=C.TEXT_PRIMARY, font=("Segoe UI", 10, "bold")).pack(anchor="w")
        self.cable_status = tk.Label(cable_col, text="Detecting...",
                                      bg=C.BG_CARD, fg=C.TEXT_MUTED,
                                      font=("Segoe UI", 8))
        self.cable_status.pack(anchor="w")

        self.audio_note = tk.Label(self.content_frame, text="",
                                    bg=C.BG_DARK, fg=C.TEXT_MUTED,
                                    font=("Segoe UI", 8, "italic"),
                                    wraplength=440, justify="center")
        self.audio_note.pack(pady=(12, 0))

        self.next_btn.config(state="disabled")
        threading.Thread(target=self._detect_devices, daemon=True).start()

    def _detect_devices(self):
        mic_index = None
        cable_index = None

        for i, device in enumerate(sd.query_devices()):
            name = device['name'].lower()
            inputs = device['max_input_channels']
            if mic_index is None and inputs > 0:
                if 'microphone' in name and 'cable' not in name and 'stereo mix' not in name:
                    mic_index = i
            if 'cable output' in name and inputs > 0:
                cable_index = i

        self.detected_mic = mic_index
        self.detected_loopback = cable_index
        self.root.after(0, self._update_device_ui)

    def _update_device_ui(self):
        devices = sd.query_devices()

        if self.detected_mic is not None:
            self.mic_icon.config(text="✓", fg=C.GREEN)
            self.mic_status.config(text=devices[self.detected_mic]['name'], fg=C.GREEN)
            self.settings["mic_device_index"] = self.detected_mic
        else:
            self.mic_icon.config(text="✕", fg=C.RED)
            self.mic_status.config(text="Not found — check Windows sound settings", fg=C.RED)

        if self.detected_loopback is not None:
            self.cable_icon.config(text="✓", fg=C.GREEN)
            self.cable_status.config(text=devices[self.detected_loopback]['name'], fg=C.GREEN)
            self.settings["loopback_device_index"] = self.detected_loopback
        else:
            self.cable_icon.config(text="✕", fg=C.RED)
            self.cable_status.config(text="Not found — install VB-Audio Virtual Cable", fg=C.RED)

        if self.detected_mic and self.detected_loopback:
            self.audio_note.config(
                text="✓  All devices detected! MilJoy is ready to launch.",
                fg=C.GREEN)
        elif self.detected_mic:
            self.audio_note.config(
                text="VB-Audio not found. Only your voice will be transcribed.",
                fg=C.YELLOW)
        else:
            self.audio_note.config(
                text="Some devices missing. Audio capture may not work correctly.",
                fg=C.YELLOW)

        self.next_btn.config(state="normal")

    def _complete_onboarding(self):
        self.settings["onboarding_complete"] = True
        SettingsManager.save(self.settings)
        self.root.destroy()
        self.on_complete(self.settings)

    def run(self):
        self.root.mainloop()


# =============================================================
# ENTRY POINT
# =============================================================

def check_and_run_onboarding(on_complete_callback):
    if SettingsManager.is_onboarding_complete():
        settings = SettingsManager.load()
        print(f"[MILJOY] Welcome back, {settings.get('user_name', 'there')}!")
        on_complete_callback(settings)
    else:
        print("[MILJOY] First launch — starting setup wizard")
        OnboardingWindow(on_complete_callback).run()


if __name__ == "__main__":
    print("MilJoy — Onboarding Test")
    OnboardingWindow(lambda s: print(f"Done!")).run()
