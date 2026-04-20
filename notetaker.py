"""
=============================================================
MilJoy — AI Call Assistant
notetaker.py — Smart Notetaker + Email Delivery
=============================================================

PURPOSE:
    Automatically generates a call summary and sends it
    to the user's email after every call.

    Features:
    - AI-generated call summary using Groq
    - Full transcript saved to Documents/MilJoy Notes/
    - Summary saved to Documents/MilJoy Notes/
    - Email sent to user's Gmail with summary + transcript attachment
    - Sender credentials loaded from encrypted file (security.py)

NOTES FOR DEBUGGING:
    - If email fails: run python security.py to set up credentials
    - If summary fails: check Groq API key
    - Files saved to: Documents/MilJoy Notes/
    - Console prints every step of the process
=============================================================
"""

import os
import sys
import smtplib
import threading
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from groq import Groq

# Add current folder to path so security.py is always found
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


# =============================================================
# CONFIGURATION
# =============================================================

NOTES_FOLDER  = os.path.join(
    os.path.expanduser("~"), "Documents", "MilJoy Notes"
)
SUMMARY_MODEL = "llama-3.1-8b-instant"
MIN_WORDS     = 30


# =============================================================
# CALL SUMMARIZER
# =============================================================

class CallSummarizer:
    """Generates AI-powered call summaries using Groq."""

    def __init__(self, api_key):
        self.client = None
        try:
            self.client = Groq(api_key=api_key)
            print("[NOTETAKER] Groq summarizer ready")
        except Exception as e:
            print(f"[ERROR] Summarizer init failed: {e}")

    def generate_summary(self, transcript, call_purpose="General", user_name=""):
        """Generates structured call summary from transcript."""
        if not self.client:
            return None

        if len(transcript.split()) < MIN_WORDS:
            print("[NOTETAKER] Transcript too short — skipping summary")
            return None

        try:
            print(f"[NOTETAKER] Generating summary...")

            prompt = f"""You are MilJoy's call summarizer. Analyze this transcript and generate a clear summary.

Call Type: {call_purpose}
{f'User: {user_name}' if user_name else ''}

TRANSCRIPT:
{transcript}

Generate a summary with these exact sections:

📋 CALL SUMMARY
Date: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}
Call Type: {call_purpose}

🎯 KEY POINTS DISCUSSED
• [Main topics discussed]

💬 WHAT THEY SAID
• [Key things the other person said]

🗣️ WHAT YOU SAID
• [Key things the user said]

✅ ACTION ITEMS
• [Follow-ups, tasks, or next steps]

📊 OVERALL ASSESSMENT
[2-3 sentences about how the call went]

Keep each section concise and professional."""

            resp = self.client.chat.completions.create(
                model=SUMMARY_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a professional call analyst. "
                            "Generate clear, actionable call summaries. "
                            "Be concise and specific."
                        )
                    },
                    {"role": "user", "content": prompt}
                ],
                max_tokens=600,
                temperature=0.3
            )

            summary = resp.choices[0].message.content.strip()
            print("[✓] Summary generated")
            return summary

        except Exception as e:
            print(f"[ERROR] Summary failed: {e}")
            return None


# =============================================================
# FILE SAVER
# =============================================================

class FileSaver:
    """Saves transcripts and summaries to Documents/MilJoy Notes/"""

    def __init__(self):
        os.makedirs(NOTES_FOLDER, exist_ok=True)
        print(f"[NOTETAKER] Notes folder ready: {NOTES_FOLDER}")

    def save_transcript(self, transcript, call_purpose="General"):
        """Saves full transcript. Returns file path."""
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filepath  = os.path.join(
            NOTES_FOLDER, f"MilJoy_Transcript_{timestamp}.txt"
        )
        try:
            content = (
                f"MilJoy — Call Transcript\n"
                f"{'='*50}\n"
                f"Date: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}\n"
                f"Call Type: {call_purpose}\n"
                f"{'='*50}\n\n"
                f"{transcript}\n"
            )
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"[✓] Transcript saved: {os.path.basename(filepath)}")
            return filepath
        except Exception as e:
            print(f"[ERROR] Transcript save failed: {e}")
            return None

    def save_summary(self, summary, call_purpose="General"):
        """Saves AI summary. Returns file path."""
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filepath  = os.path.join(
            NOTES_FOLDER, f"MilJoy_Summary_{timestamp}.txt"
        )
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(summary)
            print(f"[✓] Summary saved: {os.path.basename(filepath)}")
            return filepath
        except Exception as e:
            print(f"[ERROR] Summary save failed: {e}")
            return None


# =============================================================
# EMAIL SENDER
# =============================================================

class EmailSender:
    """Sends call summary and transcript via Gmail."""

    def __init__(self, sender_email, sender_password):
        self.sender_email    = sender_email
        self.sender_password = sender_password

    def send_summary(self, recipient_email, summary,
                     transcript_path, call_purpose="General",
                     user_name=""):
        """Sends summary email with transcript attachment."""
        if not self.sender_email or not self.sender_password:
            print("[EMAIL] No sender credentials — skipping email")
            return False

        if not recipient_email:
            print("[EMAIL] No recipient — skipping")
            return False

        try:
            print(f"[EMAIL] Sending to {recipient_email}...")

            msg            = MIMEMultipart()
            msg['From']    = f"MilJoy AI Assistant <{self.sender_email}>"
            msg['To']      = recipient_email
            msg['Subject'] = (
                f"🎙 MilJoy — {call_purpose} Call Summary | "
                f"{datetime.now().strftime('%b %d, %Y')}"
            )

            greeting = f"Hi {user_name}," if user_name else "Hi there,"
            body = f"""{greeting}

Here's your MilJoy call summary from today's {call_purpose.lower()} call.

{summary}

---
📁 Full transcript is attached to this email.

💡 Tip: Use Ctrl+Space during your next call for instant suggestions.

Best,
MilJoy AI Assistant
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
This summary was automatically generated by MilJoy.
Your AI co-pilot for every call.
"""
            msg.attach(MIMEText(body, 'plain'))

            # Attach transcript
            if transcript_path and os.path.exists(transcript_path):
                with open(transcript_path, "rb") as f:
                    att = MIMEBase('application', 'octet-stream')
                    att.set_payload(f.read())
                    encoders.encode_base64(att)
                    att.add_header(
                        'Content-Disposition',
                        f'attachment; filename="{os.path.basename(transcript_path)}"'
                    )
                    msg.attach(att)
                print("[EMAIL] Transcript attached")

            # Send via Gmail SMTP
            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
                server.login(self.sender_email, self.sender_password)
                server.sendmail(
                    self.sender_email,
                    recipient_email,
                    msg.as_string()
                )

            print(f"[✓] Email sent to {recipient_email}")
            return True

        except smtplib.SMTPAuthenticationError:
            print("[ERROR] Gmail authentication failed")
            print("[!] Run python security.py to reset credentials")
            return False
        except Exception as e:
            print(f"[ERROR] Email failed: {e}")
            return False


# =============================================================
# NOTETAKER — main coordinator
# =============================================================

class NoteTaker:
    """
    Main notetaker coordinator.
    Called when user clicks Stop Listening.
    Loads sender credentials from encrypted file via security.py.
    """

    def __init__(self, settings):
        self.settings = settings

        # Initialize summarizer
        self.summarizer = CallSummarizer(
            api_key=settings.get("groq_api_key", "")
        )

        # Initialize file saver
        self.file_saver = FileSaver()

        # Load encrypted sender credentials
        # Credentials are stored in miljoy_credentials.enc
        # Run python security.py once to create this file
        credentials = {"sender_email": "", "sender_password": ""}
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location(
                "security",
                os.path.join(os.path.dirname(os.path.abspath(__file__)), "security.py")
            )
            security_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(security_module)
            cred_manager = security_module.CredentialManager()
            credentials  = cred_manager.get_credentials()
            print("[NOTETAKER] Credentials loaded from encrypted file")
        except Exception as e:
            print(f"[NOTETAKER] Could not load credentials: {e}")
            print("[NOTETAKER] Run: python security.py to set up credentials")

        self.email_sender = EmailSender(
            sender_email=credentials.get("sender_email", ""),
            sender_password=credentials.get("sender_password", "")
        )

        print("[NOTETAKER] NoteTaker ready")

    def on_call_ended(self, transcript_history, call_purpose="General",
                      on_complete=None):
        """
        Called when user clicks Stop Listening.
        Runs in background so UI stays responsive.
        """
        if not transcript_history or not transcript_history.strip():
            print("[NOTETAKER] No transcript — skipping")
            if on_complete:
                on_complete("No transcript to save.")
            return

        print("[NOTETAKER] Processing call notes...")
        threading.Thread(
            target=self._process,
            args=[transcript_history, call_purpose, on_complete],
            daemon=True
        ).start()

    def _process(self, transcript, call_purpose, on_complete):
        """Background: save transcript, generate summary, send email."""
        user_name  = self.settings.get("user_name", "")
        user_email = self.settings.get("user_email", "")
        results    = {
            "transcript_saved":  False,
            "summary_generated": False,
            "email_sent":        False
        }

        # Step 1 — Save transcript
        transcript_path = self.file_saver.save_transcript(transcript, call_purpose)
        if transcript_path:
            results["transcript_saved"] = True

        # Step 2 — Generate summary
        summary = self.summarizer.generate_summary(
            transcript, call_purpose, user_name
        )

        if summary:
            results["summary_generated"] = True
            self.file_saver.save_summary(summary, call_purpose)

            # Step 3 — Send email
            sent = self.email_sender.send_summary(
                recipient_email=user_email,
                summary=summary,
                transcript_path=transcript_path,
                call_purpose=call_purpose,
                user_name=user_name
            )
            results["email_sent"] = sent

        # Build status message
        parts = []
        if results["transcript_saved"]:
            parts.append("transcript saved")
        if results["summary_generated"]:
            parts.append("summary generated")
        if results["email_sent"]:
            parts.append(f"email sent to {user_email}")
        elif user_email and not results["email_sent"]:
            parts.append("email failed — check credentials")

        status = "Notes: " + " • ".join(parts) if parts else "Notes processing failed"
        print(f"[NOTETAKER] Done — {status}")

        if on_complete:
            on_complete(status)
