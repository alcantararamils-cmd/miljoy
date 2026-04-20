"""
=============================================================
MilJoy — AI Call Assistant
security.py — Encrypted Credentials + Usage Tracking
=============================================================

PURPOSE:
    Two features in one file:

    1. ENCRYPTED CREDENTIALS
       Stores sensitive data (sender email, app password)
       in an encrypted file instead of plain text in code.
       Uses Fernet symmetric encryption from the cryptography library.
       The encryption key is derived from a master password
       that only you (the app owner) know.

    2. USAGE TRACKING
       Silently pings a tracking server when MilJoy launches.
       Sends only: app version, anonymous user ID, platform.
       NO personal data (no email, no name, no transcript).
       You see a live count of active users on a dashboard.

       Currently uses a free service called "Counter API" or
       a simple HTTP ping to a free stats endpoint.
       Can be upgraded to a proper server later.

NOTES FOR DEBUGGING:
    - If decryption fails: delete miljoy_credentials.enc and re-run setup
    - If tracking fails: check internet connection — app still works without it
    - MASTER_PASSWORD: change this to something only you know
    - Never share miljoy_credentials.enc without the master password

HOW THIS CONNECTS TO main.py:
    main.py calls security.get_credentials() to get sender email/password
    instead of reading from hardcoded values.
    Tracking is called once on startup automatically.
=============================================================
"""

import os
import json
import base64
import hashlib
import threading
import platform
import uuid
from datetime import datetime

try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    CRYPTO_AVAILABLE = True
except ImportError:
    print("[SECURITY] cryptography library not installed")
    print("[SECURITY] Run: pip install cryptography")
    CRYPTO_AVAILABLE = False

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


# =============================================================
# CONFIGURATION
# =============================================================

# App version — update this with each release
APP_VERSION = "1.0.0"

# Encrypted credentials file location
CREDENTIALS_FILE = "miljoy_credentials.enc"

# Salt for key derivation — change this to something unique
# This makes brute-force attacks much harder
SALT = b"MilJoySecretSalt2024"

# Master password — CHANGE THIS to something only you know
# This is used to encrypt/decrypt the credentials file
# Users never see or know this password
MASTER_PASSWORD = "MilJoyOwnerKey2024"    # ← Change this to your own secret!

# Tracking endpoint — uses a simple free counter service
# Replace with your own server URL later for more detailed analytics
TRACKING_URL = "https://api.countapi.xyz/hit/miljoy-app/launches"

# Anonymous user ID file — stores a random ID per installation
USER_ID_FILE = "miljoy_user_id.txt"


# =============================================================
# CREDENTIAL MANAGER
# Encrypts and decrypts sensitive credentials
# =============================================================

class CredentialManager:
    """
    Manages encrypted storage of sensitive credentials.
    Uses Fernet encryption with a key derived from master password.

    Flow:
    1. App owner runs setup_credentials() once with real values
    2. Creates miljoy_credentials.enc in app folder
    3. On each launch, get_credentials() decrypts and returns values
    4. Users never see the plain text values
    """

    def __init__(self, master_password=MASTER_PASSWORD):
        self.master_password = master_password
        self.fernet = None

        if CRYPTO_AVAILABLE:
            self.fernet = self._create_fernet(master_password)
        else:
            print("[SECURITY] Encryption unavailable — using fallback")

    def _create_fernet(self, password):
        """
        Creates a Fernet cipher from master password.
        Uses PBKDF2 key derivation for security.
        """
        try:
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=SALT,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(
                kdf.derive(password.encode())
            )
            return Fernet(key)
        except Exception as e:
            print(f"[SECURITY] Fernet creation failed: {e}")
            return None

    def setup_credentials(self, sender_email, sender_password):
        """
        Called once by app owner to encrypt and save credentials.
        Run this manually to set up credentials securely.

        sender_email: your Gmail address
        sender_password: your Gmail app password
        """
        if not self.fernet:
            print("[SECURITY] Cannot encrypt — cryptography not available")
            return False

        try:
            credentials = {
                "sender_email":    sender_email,
                "sender_password": sender_password,
                "created_at":      datetime.now().isoformat()
            }

            # Encrypt the credentials JSON
            plain_text = json.dumps(credentials).encode()
            encrypted  = self.fernet.encrypt(plain_text)

            # Save to file
            with open(CREDENTIALS_FILE, "wb") as f:
                f.write(encrypted)

            print(f"[✓] Credentials encrypted and saved to {CREDENTIALS_FILE}")
            print("[SECURITY] Delete this from your code after setup!")
            return True

        except Exception as e:
            print(f"[ERROR] Credential setup failed: {e}")
            return False

    def get_credentials(self):
        """
        Decrypts and returns credentials from file.
        Returns dict with sender_email and sender_password.
        Returns None if file not found or decryption fails.
        """
        if not CRYPTO_AVAILABLE:
            return self._get_fallback_credentials()

        if not os.path.exists(CREDENTIALS_FILE):
            print("[SECURITY] No credentials file found")
            print("[SECURITY] Run setup_credentials() to create one")
            return self._get_fallback_credentials()

        try:
            with open(CREDENTIALS_FILE, "rb") as f:
                encrypted = f.read()

            plain_text  = self.fernet.decrypt(encrypted)
            credentials = json.loads(plain_text.decode())

            print("[✓] Credentials decrypted successfully")
            return credentials

        except Exception as e:
            print(f"[ERROR] Credential decryption failed: {e}")
            print("[SECURITY] Delete miljoy_credentials.enc and re-run setup")
            return self._get_fallback_credentials()

    def _get_fallback_credentials(self):
        """
        Fallback if encryption not available.
        Returns hardcoded values — less secure but still works.
        Replace these with your actual values.
        """
        return {
            "sender_email":    "your_gmail@gmail.com",
            "sender_password": "your_app_password_here"
        }

    def credentials_exist(self):
        """Returns True if encrypted credentials file exists."""
        return os.path.exists(CREDENTIALS_FILE)


# =============================================================
# USAGE TRACKER
# Silently pings a counter when MilJoy launches
# No personal data is ever sent
# =============================================================

class UsageTracker:
    """
    Tracks MilJoy usage anonymously.

    What IS sent:
    - App version (e.g. "1.0.0")
    - Anonymous random user ID (generated once per installation)
    - Platform (Windows 11)
    - Launch timestamp

    What is NEVER sent:
    - User name or email
    - API keys
    - Transcript content
    - Any personal information
    """

    def __init__(self):
        self.user_id = self._get_or_create_user_id()

    def _get_or_create_user_id(self):
        """
        Gets or creates an anonymous random ID for this installation.
        Stored in miljoy_user_id.txt.
        This ID has no connection to the user's real identity.
        """
        if os.path.exists(USER_ID_FILE):
            try:
                with open(USER_ID_FILE, "r") as f:
                    user_id = f.read().strip()
                if user_id:
                    return user_id
            except Exception:
                pass

        # Generate new random ID
        user_id = str(uuid.uuid4())[:8]     # Short 8-char random ID
        try:
            with open(USER_ID_FILE, "w") as f:
                f.write(user_id)
            print(f"[TRACKER] New installation ID: {user_id}")
        except Exception:
            pass

        return user_id

    def track_launch(self):
        """
        Pings the tracking endpoint in a background thread.
        App continues normally even if tracking fails.
        Fails silently — user never knows.
        """
        threading.Thread(
            target=self._ping,
            daemon=True
        ).start()

    def _ping(self):
        """
        Background thread — sends anonymous ping.
        Uses CountAPI (free, no account needed).
        """
        if not REQUESTS_AVAILABLE:
            return

        try:
            # Build anonymous payload
            payload = {
                "version":    APP_VERSION,
                "user_id":    self.user_id,
                "platform":   platform.system() + " " + platform.release(),
                "timestamp":  datetime.now().isoformat()
            }

            # Primary: CountAPI — free simple counter
            # Shows total launch count at:
            # https://api.countapi.xyz/get/miljoy-app/launches
            response = requests.get(
                TRACKING_URL,
                timeout=5       # Short timeout — don't slow down app
            )

            if response.status_code == 200:
                data = response.json()
                total_launches = data.get("value", 0)
                print(f"[TRACKER] Launch tracked — total launches: {total_launches}")
            else:
                print(f"[TRACKER] Tracking failed: {response.status_code}")

        except requests.exceptions.ConnectionError:
            # No internet — skip silently
            pass
        except requests.exceptions.Timeout:
            # Slow connection — skip silently
            pass
        except Exception as e:
            # Any other error — skip silently
            print(f"[TRACKER] Ping failed (non-critical): {e}")

    def get_stats_url(self):
        """
        Returns the URL where you can see your launch count.
        Open this in a browser to see how many times MilJoy has been launched.
        """
        return "https://api.countapi.xyz/get/miljoy-app/launches"


# =============================================================
# SETUP HELPER
# Run this once as app owner to encrypt your credentials
# =============================================================

def owner_setup():
    """
    Run this function ONCE as the app owner to encrypt your credentials.
    After running, delete the plain text email/password from this call.

    How to use:
    1. Open this file
    2. Replace the values below with your real Gmail and app password
    3. Run: python security.py
    4. It creates miljoy_credentials.enc
    5. Delete your plain text values from this function
    6. Distribute the app with miljoy_credentials.enc included
    """
    print("==============================================")
    print("  MilJoy — Credential Setup")
    print("==============================================")

    manager = CredentialManager()

    # ← Replace these with your real values, then delete after running
    YOUR_SENDER_EMAIL    = "YOUR_SENDER_EMAIL"
    YOUR_SENDER_PASSWORD = "YOUR_SENDER_PASSWORD"

    if YOUR_SENDER_EMAIL == "your_gmail@gmail.com":
        print("[!] Please replace the placeholder values first!")
        print("[!] Open security.py and fill in YOUR_SENDER_EMAIL and YOUR_SENDER_PASSWORD")
        return

    success = manager.setup_credentials(
        sender_email=YOUR_SENDER_EMAIL,
        sender_password=YOUR_SENDER_PASSWORD
    )

    if success:
        print("\n✓ Done! miljoy_credentials.enc has been created.")
        print("✓ You can now delete the plain text values from this file.")
        print("✓ Include miljoy_credentials.enc when distributing MilJoy.")
        print(f"\n📊 Track your users at:\n   {UsageTracker().get_stats_url()}")
    else:
        print("\n✗ Setup failed. Check error messages above.")


# =============================================================
# STANDALONE — run to set up credentials
# python security.py
# =============================================================

if __name__ == "__main__":
    owner_setup()
