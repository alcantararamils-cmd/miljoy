"""
=============================================================
MilJoy — AI Call Assistant
ai.py — Groq AI Integration (Section 6 Update)
=============================================================

PURPOSE:
    Connects to Groq API and generates suggested responses.

    Section 6 additions:
    - Pre-call suggestion: generates opening greeting + intro
      based on call purpose before conversation starts
    - Call purpose awareness: AI uses the purpose to give
      more relevant suggestions throughout the call
    - Smarter system prompt that includes call purpose context

NOTES FOR DEBUGGING:
    - If suggestions stop: check Groq rate limits
    - GROQ_MODEL: change to llama-3.3-70b-versatile for smarter responses
    - DEBOUNCE_SECONDS: lower for faster suggestions, higher to reduce API calls
    - Console prints every suggestion generated
=============================================================
"""

import threading
import time
from groq import Groq


# =============================================================
# CONFIGURATION
# =============================================================

GROQ_MODEL       = "llama-3.1-8b-instant"   # Already fastest model
                                              # Smarter: "llama-3.3-70b-versatile"
MAX_TOKENS       = 150                        # Max suggestion length (~2-3 sentences)
DEBOUNCE_SECONDS = 3                          # Seconds of silence after THEM stops
                                              # before generating suggestion
                                              # Raise if THEM gets interrupted too early
                                              # Lower if suggestions feel too slow
WORDS_PER_MINUTE = 150                        # Average reading speed
                                              # Increase if you read faster, decrease if slower
MIN_DISPLAY_SECONDS = 4                       # Minimum time a suggestion stays on screen
MIN_WORDS        = 10                         # Minimum transcript words before suggesting


# =============================================================
# CALL PURPOSES
# Used to build context-aware prompts
# =============================================================

CALL_PURPOSES = {
    "Sales": {
        "label": "💼 Sales Call",
        "description": "Selling a product or service to a prospect",
        "opening": (
            "Generate a warm, confident opening greeting and introduction "
            "for a sales call. Include: a friendly greeting, your name, "
            "your company/role, and a smooth transition into the call purpose. "
            "Keep it under 3 sentences."
        ),
        "context": (
            "You are assisting someone on a sales call. "
            "Focus on building rapport, understanding needs, "
            "handling objections confidently, and moving toward a close. "
            "Suggestions should be persuasive but not pushy."
        )
    },
    "Interview": {
        "label": "🎯 Job Interview",
        "description": "Interviewing for a job position",
        "opening": (
            "Generate a confident, professional opening for a job interview. "
            "Include: a warm greeting, expressing enthusiasm for the opportunity, "
            "and readiness to discuss your background. "
            "Keep it under 3 sentences."
        ),
        "context": (
            "You are assisting someone in a job interview. "
            "Focus on highlighting strengths confidently, "
            "giving structured STAR-method answers, "
            "and showing genuine enthusiasm for the role. "
            "Suggestions should sound natural and confident."
        )
    },
    "Meeting": {
        "label": "📋 Business Meeting",
        "description": "Internal or client business meeting",
        "opening": (
            "Generate a professional opening for a business meeting. "
            "Include: a greeting, briefly setting the agenda or purpose, "
            "and inviting participation. "
            "Keep it under 3 sentences."
        ),
        "context": (
            "You are assisting someone in a business meeting. "
            "Focus on clear communication, staying on topic, "
            "summarizing key points, and driving toward decisions. "
            "Suggestions should be professional and concise."
        )
    },
    "Cold Call": {
        "label": "📞 Cold Call",
        "description": "Reaching out to someone who isn't expecting the call",
        "opening": (
            "Generate a confident, non-intrusive cold call opening. "
            "Include: quick greeting, who you are, why you're calling, "
            "and a soft permission ask to continue. "
            "Keep it under 3 sentences."
        ),
        "context": (
            "You are assisting someone on a cold call. "
            "Focus on quickly establishing credibility, "
            "getting past the gatekeeping instinct, "
            "and creating enough curiosity to continue the conversation. "
            "Suggestions should be respectful of their time."
        )
    },
    "Custom": {
        "label": "✏️ Custom",
        "description": "Other type of call",
        "opening": (
            "Generate a warm, professional opening greeting and introduction "
            "for a call. Keep it under 3 sentences."
        ),
        "context": (
            "You are assisting someone on a call. "
            "Provide natural, helpful suggested responses "
            "based on the conversation context."
        )
    }
}


# =============================================================
# PERSONA MANAGER
# =============================================================

class PersonaManager:
    """
    Manages user persona and call purpose.
    Both are used to build the AI system prompt.
    """

    def __init__(self):
        self.persona = "a confident and professional communicator"
        self.context = ""
        self.call_purpose = "Custom"        # Default call purpose
        self.call_custom_note = ""          # Optional custom note about the call
        print(f"[PERSONA] Initialized with default persona")

    def set_persona(self, persona, context=""):
        self.persona = persona
        self.context = context
        print(f"[PERSONA] Updated: {persona}")

    def set_call_purpose(self, purpose, custom_note=""):
        """
        Sets the call purpose for this session.
        purpose: key from CALL_PURPOSES dict
        custom_note: optional extra detail about the specific call
        """
        if purpose not in CALL_PURPOSES:
            purpose = "Custom"
        self.call_purpose = purpose
        self.call_custom_note = custom_note
        print(f"[PERSONA] Call purpose set: {purpose}")
        if custom_note:
            print(f"[PERSONA] Call note: {custom_note}")

    def get_system_prompt(self):
        """
        Builds the full system prompt including persona + call purpose.
        Sent with every AI suggestion request.
        """
        purpose_data = CALL_PURPOSES.get(self.call_purpose, CALL_PURPOSES["Custom"])

        prompt = f"""You are a real-time conversation assistant for MilJoy.

The user is {self.persona}.
Call type: {purpose_data['label']} — {purpose_data['description']}
{purpose_data['context']}

Your job is to suggest what the user should say next based on the live transcript.

Rules:
- Keep suggestions SHORT and natural (1-3 sentences max)
- Sound like a real human, not a robot
- Match the tone of the conversation
- Give ONE clear suggestion — not multiple options
- Do NOT include labels like "Suggested response:" — just write it directly
- Do NOT explain your reasoning — just write what they should say
- React specifically to what was just said
- NEVER explain what you're doing or why
- NEVER say things like "Here's a suggestion:" or "You could say:"
- NEVER add any preamble — output ONLY the words the user should speak
- If you add any explanation, label, or commentary you have failed"""

        if self.context:
            prompt += f"\n\nUser context: {self.context}"

        if self.call_custom_note:
            prompt += f"\nCall details: {self.call_custom_note}"

        return prompt

    def get_opening_prompt(self):
        """
        Returns the prompt used to generate the pre-call opening suggestion.
        Called when user sets call purpose before starting.
        """
        purpose_data = CALL_PURPOSES.get(self.call_purpose, CALL_PURPOSES["Custom"])

        prompt = purpose_data["opening"]

        if self.persona and self.persona != "a confident and professional communicator":
            prompt += f" The user is {self.persona}."

        if self.call_custom_note:
            prompt += f" Additional context: {self.call_custom_note}"

        return prompt


# =============================================================
# GROQ AI CLIENT
# =============================================================

class GroqAIClient:
    """Handles all Groq API communication."""

    def __init__(self, api_key, persona_manager):
        self.persona_manager = persona_manager
        self.client = None
        self._init(api_key)

    def _init(self, api_key):
        try:
            self.client = Groq(api_key=api_key)
            print("[✓] Groq client initialized")
            self._test()
        except Exception as e:
            print(f"[ERROR] Groq init failed: {e}")
            self.client = None

    def _test(self):
        """Quick connection test on startup."""
        try:
            print("[GROQ] Testing API connection...")
            resp = self.client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[{"role": "user", "content": "Say 'OK' and nothing else."}],
                max_tokens=5
            )
            result = resp.choices[0].message.content.strip()
            print(f"[✓] Groq API connected successfully — test response: {result}")
        except Exception as e:
            print(f"[ERROR] Groq API test failed: {e}")
            print("[!] Check your API key at https://console.groq.com")

    def generate_suggestion(self, transcript_history):
        """
        Generates a response suggestion based on transcript.
        Returns suggestion text or None if failed.
        """
        if not self.client:
            return None

        words = transcript_history.split()
        if len(words) < MIN_WORDS:
            print(f"[GROQ] Transcript too short ({len(words)} words), skipping")
            return None

        try:
            user_msg = f"""Here is the recent conversation transcript:

{transcript_history}

Based on this conversation, what should I say next?"""

            print(f"[GROQ] Generating suggestion from {len(words)} words of transcript...")

            resp = self.client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[
                    {"role": "system", "content": self.persona_manager.get_system_prompt()},
                    {"role": "user",   "content": user_msg}
                ],
                max_tokens=MAX_TOKENS,
                temperature=0.7
            )

            suggestion = resp.choices[0].message.content.strip()
            print(f"[GROQ] Suggestion generated: {suggestion[:100]}...")
            return suggestion

        except Exception as e:
            print(f"[ERROR] Groq API call failed: {e}")
            return None

    def generate_opening(self):
        """
        [NEW SECTION 6]
        Generates a pre-call opening greeting + introduction.
        Called when user sets call purpose before starting.
        Returns opening text or None if failed.
        """
        if not self.client:
            return None

        try:
            opening_prompt = self.persona_manager.get_opening_prompt()
            print(f"[GROQ] Generating opening for: {self.persona_manager.call_purpose}")

            resp = self.client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are MilJoy, an AI call assistant. "
                            "Generate natural, confident call openings. "
                            "Write in first person as if the user is saying it. "
                            "Keep it concise — under 3 sentences."
                        )
                    },
                    {"role": "user", "content": opening_prompt}
                ],
                max_tokens=120,
                temperature=0.8
            )

            opening = resp.choices[0].message.content.strip()
            print(f"[GROQ] Opening generated: {opening[:80]}...")
            return opening

        except Exception as e:
            print(f"[ERROR] Opening generation failed: {e}")
            return None


# =============================================================
# AI MANAGER — used by main.py
# =============================================================

class AIManager:
    """
    Top-level AI coordinator for MilJoy.
    Section 6: Adds pre-call opening generation and call purpose support.

    Usage in main.py:
        ai = AIManager(api_key, on_suggestion_callback)
        ai.set_persona("sales professional", "selling CRM software")
        ai.set_call_purpose("Sales", "calling TechCorp about their CRM needs")
        ai.generate_opening()          # Before call starts
        ai.on_transcript_update(text)  # During call — auto suggestion
        ai.trigger_now(text)           # Manual trigger via Ctrl+Space
    """

    def __init__(self, api_key, on_suggestion_callback):
        print("\n[AI] Initializing AI Manager...")

        self.on_suggestion   = on_suggestion_callback
        self.is_generating           = False
        self.last_transcript         = 0
        self.debounce_timer          = None
        self.current_suggestion      = ""
        self.suggestion_display_time = 0
        self.pending_transcript      = ""    # Stores latest transcript from THEM

        # Initialize persona and Groq client
        self.persona_manager = PersonaManager()
        self.groq = GroqAIClient(
            api_key=api_key,
            persona_manager=self.persona_manager
        )

        print("[✓] AI Manager ready\n")

    def set_persona(self, persona, context=""):
        """Sets user persona."""
        self.persona_manager.set_persona(persona, context)

    def set_call_purpose(self, purpose, custom_note=""):
        """
        [NEW SECTION 6]
        Sets the call purpose for this session.
        Should be called before generate_opening().
        """
        self.persona_manager.set_call_purpose(purpose, custom_note)

    def generate_opening(self, on_complete=None):
        """
        [NEW SECTION 6]
        Generates pre-call opening suggestion in background thread.
        on_complete: optional extra callback when done
        """
        def _generate():
            print("[AI] Generating pre-call opening...")
            opening = self.groq.generate_opening()
            if opening:
                self.on_suggestion(opening)
                if on_complete:
                    on_complete(opening)

        threading.Thread(target=_generate, daemon=True).start()

    def on_transcript_update(self, transcript_history, speaker=None):
        """
        Called when new transcript arrives.
        Only generates suggestions when THEM speaks.

        Key behavior:
        - Every time THEM says something, the debounce timer RESETS
        - Suggestion only generates after THEM has been SILENT
          for DEBOUNCE_SECONDS
        - This means if THEM speaks in 3 parts with pauses,
          we wait until they fully stop before suggesting
        - You get ONE final suggestion based on everything they said
        """
        # Only trigger when THEM speaks
        if speaker == "YOU":
            print("[AI] Skipping — YOU are speaking")
            return

        # THEM is still talking — cancel any pending suggestion
        # and restart the silence timer
        if self.debounce_timer:
            self.debounce_timer.cancel()
            print("[AI] THEM still talking — resetting silence timer")

        self.last_transcript = time.time()
        self.pending_transcript = transcript_history  # Store latest transcript

        # Only start timer if we're not already showing a suggestion
        # that the user hasn't had time to read yet
        wait_time = self._get_wait_time()

        self.debounce_timer = threading.Timer(
            wait_time,
            self._debounced_generate,
            args=[transcript_history]
        )
        self.debounce_timer.start()
        print(f"[AI] Silence timer started — will suggest in {wait_time:.1f}s if THEM stops")

    def set_current_suggestion(self, text):
        """
        Called by main.py whenever a new suggestion is displayed.
        Stores it so we can calculate reading time before replacing.
        """
        self.current_suggestion = text
        self.suggestion_display_time = time.time()
        print(f"[AI] Suggestion display time set — {self._reading_time(text):.1f}s to read")

    def _reading_time(self, text):
        """
        Calculates how many seconds it takes to read a text.
        Based on average reading speed of WORDS_PER_MINUTE.
        """
        word_count = len(text.split())
        seconds = (word_count / WORDS_PER_MINUTE) * 60
        return max(MIN_DISPLAY_SECONDS, seconds)

    def _get_wait_time(self):
        """
        Returns how long to wait before generating next suggestion.
        If current suggestion hasn't been on screen long enough
        to finish reading, waits until reading time is up.
        """
        if not hasattr(self, 'current_suggestion') or not self.current_suggestion:
            return DEBOUNCE_SECONDS

        # How long has current suggestion been displayed
        display_duration = time.time() - getattr(self, 'suggestion_display_time', 0)

        # How long it takes to read current suggestion
        read_time = self._reading_time(self.current_suggestion)

        # Time remaining to finish reading
        remaining = read_time - display_duration

        if remaining > 0:
            # Add debounce on top of remaining reading time
            wait = remaining + DEBOUNCE_SECONDS
            print(f"[AI] Waiting {wait:.1f}s (reading time: {read_time:.1f}s, elapsed: {display_duration:.1f}s)")
            return wait
        else:
            return DEBOUNCE_SECONDS

    def trigger_now(self, transcript_history):
        """Manual trigger — bypasses debounce."""
        print("[AI] Manual trigger")
        if self.debounce_timer:
            self.debounce_timer.cancel()
        self._generate(transcript_history)

    def _debounced_generate(self, transcript_history):
        """Called after debounce timer fires."""
        elapsed = time.time() - self.last_transcript
        if elapsed >= DEBOUNCE_SECONDS - 0.1:
            print(f"[AI] Auto-trigger after {DEBOUNCE_SECONDS}s pause")
            self._generate(transcript_history)

    def _generate(self, transcript_history):
        """Runs AI generation in background thread."""
        if self.is_generating:
            print("[AI] Already generating — skipping")
            return

        threading.Thread(
            target=self._generate_bg,
            args=[transcript_history],
            daemon=True
        ).start()

    def _generate_bg(self, transcript_history):
        """Background thread for AI generation."""
        self.is_generating = True
        try:
            suggestion = self.groq.generate_suggestion(transcript_history)
            if suggestion:
                self.on_suggestion(suggestion)
        except Exception as e:
            print(f"[ERROR] Generation failed: {e}")
        finally:
            self.is_generating = False
