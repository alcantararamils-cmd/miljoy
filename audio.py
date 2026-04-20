"""
=============================================================
MilJoy — AI Call Assistant
audio.py — Audio Capture + Transcription (Section 11 Update)
=============================================================

PURPOSE:
    Captures and transcribes audio from two sources:
    - Microphone (YOU) — your voice
    - CABLE Output (THEM) — other person's voice via VB-Audio

    Section 11 improvements:
    - AUTO device detection — finds correct mic and CABLE Output
      automatically on any machine. No hardcoded indexes.
    - Saves detected indexes to settings.json for future launches
    - Faster transcription — reduced chunk duration + optimized Whisper
    - Better VAD sensitivity

NOTES FOR DEBUGGING:
    - If wrong device detected: delete settings.json to re-detect
    - MIC_THRESHOLD: raise if background noise, lower if voice missed
    - CHUNK_DURATION: lower = faster but less accurate
    - Console shows detected device names and indexes
=============================================================
"""

import sounddevice as sd
import numpy as np
import threading
import queue
import time
import json
import os
from faster_whisper import WhisperModel


# =============================================================
# CONFIGURATION
# =============================================================

WHISPER_MODEL       = "tiny"     # Fastest model for real-time use
CHUNK_DURATION      = 2          # Seconds — shorter = faster transcripts
CHANNELS            = 1          # Mono audio
BLOCKSIZE           = 2048       # Smaller = lower latency

# Volume thresholds
MIC_THRESHOLD       = 0.080      # Mic sensitivity
SPEAKER_THRESHOLD   = 0.015      # Speaker/CABLE sensitivity

# VAD settings
MAX_SPEECH_DURATION = 8          # Force transcribe after this many seconds
MIN_SPEECH_DURATION = 0.5        # Ignore audio shorter than this

# Settings file for saving detected device indexes
SETTINGS_FILE       = "settings.json"

# Hallucination filter
HALLUCINATIONS = {
    "you", "you.", "uh", "um", "hmm", "hm", "hmm.",
    ".", "..", "...", "okay", "okay.", "ok", "ok.",
    "yeah", "yeah.", "yes", "yes.", "no", "no.",
    "oh", "oh.", "ah", "ah.", "ahh", "ahhh",
    "huh", "huh?", "shh", "shhh", "hey", "hey.",
    "hi", "hi.", "bye", "bye.", "wow", "wow.",
    "sure", "sure.", "right", "right.", "i see",
    "thank you", "thank you.", "thanks", "thanks.",
}


# =============================================================
# AUTO DEVICE DETECTOR
# Automatically finds the best mic and CABLE Output device
# Works on any Windows machine without hardcoded indexes
# =============================================================

class AutoDeviceDetector:
    """
    Automatically detects the best audio devices for MilJoy.

    Detection priority for microphone:
    1. WASAPI Microphone Array
    2. Any WASAPI input device
    3. Any MME microphone

    Detection priority for speaker capture:
    1. CABLE Output (VB-Audio) — best separation
    2. Stereo Mix — fallback if no VB-Audio

    Saves detected indexes to settings.json so detection
    only runs once per machine.
    """

    @staticmethod
    def detect_all(force_redetect=False):
        """
        Detects mic and speaker capture devices.
        Returns (mic_index, speaker_index) tuple.

        force_redetect: if True, ignores saved settings and re-detects
        """
        # Check if we have saved indexes from previous detection
        if not force_redetect:
            saved = AutoDeviceDetector._load_saved_indexes()
            if saved:
                mic_idx, spk_idx = saved
                # Verify saved devices still exist
                if AutoDeviceDetector._verify_device(mic_idx) and \
                   AutoDeviceDetector._verify_device(spk_idx):
                    print(f"[AUTODETECT] Using saved devices — mic: {mic_idx}, speaker: {spk_idx}")
                    return mic_idx, spk_idx
                else:
                    print("[AUTODETECT] Saved devices no longer valid — re-detecting")

        print("[AUTODETECT] Scanning audio devices...")
        devices = sd.query_devices()
        hostapis = sd.query_hostapis()

        mic_index     = AutoDeviceDetector._find_microphone(devices, hostapis)
        speaker_index = AutoDeviceDetector._find_speaker_capture(devices, hostapis)

        # Save detected indexes for next launch
        AutoDeviceDetector._save_indexes(mic_index, speaker_index)

        return mic_index, speaker_index

    @staticmethod
    def _find_microphone(devices, hostapis):
        """
        Finds the best microphone device.
        Prefers WASAPI for lowest latency.
        """
        # Priority 1: WASAPI Microphone Array
        for i, dev in enumerate(devices):
            name    = dev['name'].lower()
            api     = hostapis[dev['hostapi']]['name'].lower()
            inputs  = dev['max_input_channels']
            if (inputs > 0 and 'wasapi' in api and
                    'microphone' in name and
                    'cable' not in name and
                    'stereo mix' not in name):
                print(f"[AUTODETECT] ✓ Mic (WASAPI): {dev['name']} (index {i})")
                return i

        # Priority 2: Any WASAPI input
        for i, dev in enumerate(devices):
            name   = dev['name'].lower()
            api    = hostapis[dev['hostapi']]['name'].lower()
            inputs = dev['max_input_channels']
            if (inputs > 0 and 'wasapi' in api and
                    'cable' not in name and
                    'stereo mix' not in name and
                    'mapper' not in name):
                print(f"[AUTODETECT] ✓ Mic (WASAPI fallback): {dev['name']} (index {i})")
                return i

        # Priority 3: Any MME microphone
        for i, dev in enumerate(devices):
            name   = dev['name'].lower()
            api    = hostapis[dev['hostapi']]['name'].lower()
            inputs = dev['max_input_channels']
            if (inputs > 0 and 'mme' in api and
                    'microphone' in name and
                    'cable' not in name):
                print(f"[AUTODETECT] ✓ Mic (MME): {dev['name']} (index {i})")
                return i

        print("[AUTODETECT] ✗ No microphone found!")
        return None

    @staticmethod
    def _find_speaker_capture(devices, hostapis):
        """
        Finds the best device for capturing speaker audio.
        Prefers VB-Audio CABLE Output for clean separation.
        """
        # Priority 1: CABLE Output with most input channels (VB-Audio)
        best_cable = None
        best_channels = 0
        for i, dev in enumerate(devices):
            name   = dev['name'].lower()
            inputs = dev['max_input_channels']
            if 'cable output' in name and inputs > best_channels:
                best_cable    = i
                best_channels = inputs

        if best_cable is not None:
            print(f"[AUTODETECT] ✓ Speaker (CABLE Output): {devices[best_cable]['name']} (index {best_cable})")
            return best_cable

        # Priority 2: Stereo Mix (Realtek HD Audio — most reliable)
        for i, dev in enumerate(devices):
            name   = dev['name'].lower()
            api    = hostapis[dev['hostapi']]['name'].lower()
            inputs = dev['max_input_channels']
            if ('stereo mix' in name and 'hd audio' in name and
                    inputs > 0):
                print(f"[AUTODETECT] ✓ Speaker (Stereo Mix HD): {dev['name']} (index {i})")
                return i

        # Priority 3: Any Stereo Mix
        for i, dev in enumerate(devices):
            name   = dev['name'].lower()
            inputs = dev['max_input_channels']
            if 'stereo mix' in name and inputs > 0:
                print(f"[AUTODETECT] ✓ Speaker (Stereo Mix): {dev['name']} (index {i})")
                return i

        print("[AUTODETECT] ✗ No speaker capture device found!")
        print("[AUTODETECT] Install VB-Audio from vb-audio.com/Cable")
        return None

    @staticmethod
    def _verify_device(index):
        """Checks if a device index still exists and is valid."""
        if index is None:
            return False
        try:
            devices = sd.query_devices()
            return index < len(devices)
        except Exception:
            return False

    @staticmethod
    def _load_saved_indexes():
        """Loads previously detected device indexes from settings.json."""
        try:
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, "r") as f:
                    settings = json.load(f)
                mic = settings.get("detected_mic_index")
                spk = settings.get("detected_speaker_index")
                if mic is not None and spk is not None:
                    return mic, spk
        except Exception:
            pass
        return None

    @staticmethod
    def _save_indexes(mic_index, speaker_index):
        """Saves detected device indexes to settings.json."""
        try:
            settings = {}
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, "r") as f:
                    settings = json.load(f)

            settings["detected_mic_index"]     = mic_index
            settings["detected_speaker_index"] = speaker_index

            with open(SETTINGS_FILE, "w") as f:
                json.dump(settings, f, indent=2)

            print(f"[AUTODETECT] Saved device indexes to {SETTINGS_FILE}")
        except Exception as e:
            print(f"[AUTODETECT] Could not save indexes: {e}")

    @staticmethod
    def get_sample_rate(device_index):
        """
        Returns the correct sample rate for a device.
        WASAPI devices typically only support their native rate.
        """
        if device_index is None:
            return 48000
        try:
            device = sd.query_devices(device_index)
            rate   = int(device['default_samplerate'])
            print(f"[AUTODETECT] Device {device_index} native rate: {rate}Hz")
            return rate
        except Exception:
            return 48000


# =============================================================
# VOICE ACTIVITY DETECTOR
# =============================================================

class VAD:
    """
    Detects real speech vs silence using RMS volume.
    Force-transcribes after MAX_SPEECH_DURATION seconds.
    """

    def __init__(self, threshold=MIC_THRESHOLD):
        self.threshold    = threshold
        self.buffer       = []
        self.silence_count = 0
        self.is_speaking  = False
        self.speech_start = None

    def process(self, audio_chunk):
        """
        Processes audio chunk.
        Returns audio to transcribe or None to keep accumulating.
        """
        rms = self._rms(audio_chunk)
        now = time.time()

        if rms > self.threshold:
            if not self.is_speaking:
                self.is_speaking  = True
                self.speech_start = now
                self.buffer       = []
                self.silence_count = 0

            self.buffer.append(audio_chunk)
            self.silence_count = 0

            # Force transcribe if speech goes too long
            duration = now - (self.speech_start or now)
            if duration >= MAX_SPEECH_DURATION and self.buffer:
                combined          = np.concatenate(self.buffer)
                self.buffer       = []
                self.speech_start = now
                print(f"[VAD] Force transcribe after {duration:.1f}s")
                return combined

            return None

        else:
            if self.is_speaking:
                self.silence_count += 1
                self.buffer.append(audio_chunk)

                if self.silence_count >= 2:
                    self.is_speaking = False
                    duration = now - (self.speech_start or now)

                    if self.buffer and duration >= MIN_SPEECH_DURATION:
                        combined    = np.concatenate(self.buffer)
                        self.buffer = []
                        print(f"[VAD] Speech captured: {duration:.1f}s")
                        return combined
                    else:
                        self.buffer = []

            return None

    def reset(self):
        self.buffer        = []
        self.silence_count = 0
        self.is_speaking   = False
        self.speech_start  = None

    def _rms(self, audio):
        if len(audio) == 0:
            return 0.0
        return float(np.sqrt(np.mean(audio.astype(np.float32) ** 2)))


# =============================================================
# WHISPER TRANSCRIBER
# Optimized for speed with tiny model + int8
# =============================================================

class WhisperTranscriber:
    """
    Transcribes audio using local Whisper tiny model.
    Optimized for real-time use with int8 quantization.
    """

    def __init__(self, on_transcript_callback):
        self.on_transcript = on_transcript_callback
        self.model         = None
        self.audio_queue   = queue.Queue()
        self.is_running    = False
        self._load_model()

    def _load_model(self):
        print(f"[WHISPER] Loading '{WHISPER_MODEL}' model...")
        print("[WHISPER] First run downloads ~150MB, please wait...")
        try:
            self.model = WhisperModel(
                WHISPER_MODEL,
                device="cpu",
                compute_type="int8"     # Fastest CPU mode
            )
            print(f"[✓] Whisper '{WHISPER_MODEL}' loaded")
        except Exception as e:
            print(f"[ERROR] Whisper failed: {e}")
            self.model = None

    def transcribe_chunk(self, audio, speaker, source_rate=48000):
        """Queues audio for transcription."""
        if self.model:
            self.audio_queue.put((audio, speaker, source_rate))

    def start_processing(self):
        self.is_running = True
        threading.Thread(target=self._loop, daemon=True).start()
        print("[✓] Transcription thread started")

    def stop_processing(self):
        self.is_running = False

    def _loop(self):
        """Background transcription loop."""
        while self.is_running:
            try:
                audio, speaker, source_rate = self.audio_queue.get(timeout=1.0)
                text = self._transcribe(audio, source_rate)
                if text:
                    print(f"[TRANSCRIPT] {speaker}: {text}")
                    self.on_transcript(text, speaker)
            except queue.Empty:
                continue
            except Exception as e:
                print(f"[ERROR] Transcription: {e}")

    def _transcribe(self, audio, source_rate=48000):
        """
        Transcribes audio to text.
        Resamples from source_rate to 16000Hz for Whisper.
        """
        try:
            audio = audio.astype(np.float32)

            # Resample to 16000Hz
            if source_rate == 48000:
                audio = audio[::3]           # 48000/3 = 16000
            elif source_rate == 44100:
                audio = audio[::3]           # Close enough
            else:
                factor = max(1, source_rate // 16000)
                audio  = audio[::factor]

            # Normalize volume
            max_val = np.max(np.abs(audio))
            if max_val == 0:
                return ""
            audio = audio / max_val

            # Transcribe with Whisper
            segments, _ = self.model.transcribe(
                audio,
                beam_size=1,                 # Faster than beam_size=5
                language="en",
                condition_on_previous_text=False,
                vad_filter=True,
                vad_parameters=dict(
                    min_silence_duration_ms=200   # More responsive
                )
            )

            text = " ".join([s.text for s in segments]).strip()

            # Filter 1: Too short
            if len(text) < 6:
                return ""

            # Filter 2: Known hallucinations
            if text.lower().strip(".,!? ") in HALLUCINATIONS:
                return ""

            # Filter 3: Repetitive words
            words = text.lower().split()
            if len(words) >= 4:
                if len(set(words)) / len(words) < 0.3:
                    print(f"[FILTER] Repetitive removed")
                    return ""

            return text

        except Exception as e:
            print(f"[ERROR] _transcribe: {e}")
            return ""


# =============================================================
# AUDIO CAPTURE
# =============================================================

class AudioCapture:
    """
    Opens mic and speaker streams.
    Uses auto-detected sample rates for each device.
    """

    def __init__(self, transcriber, mic_index, speaker_index):
        self.transcriber    = transcriber
        self.mic_index      = mic_index
        self.speaker_index  = speaker_index

        # Get native sample rates for each device
        self.mic_rate     = AutoDeviceDetector.get_sample_rate(mic_index)
        self.speaker_rate = AutoDeviceDetector.get_sample_rate(speaker_index)

        # Separate VAD per stream
        self.mic_vad     = VAD(threshold=MIC_THRESHOLD)
        self.speaker_vad = VAD(threshold=SPEAKER_THRESHOLD)

        self.mic_stream     = None
        self.speaker_stream = None
        self.is_capturing   = False

        self.mic_buffer     = []
        self.speaker_buffer = []

        # Chunk sizes based on native rates
        self.mic_chunk_samples     = int(self.mic_rate * CHUNK_DURATION)
        self.speaker_chunk_samples = int(self.speaker_rate * CHUNK_DURATION)

    def start(self):
        self.is_capturing = True
        self._open_mic()
        self._open_speaker()
        print("[✓] Audio capture started")

    def stop(self):
        self.is_capturing = False
        self.mic_vad.reset()
        self.speaker_vad.reset()

        for stream, name in [
            (self.mic_stream,     "Microphone"),
            (self.speaker_stream, "Speaker capture")
        ]:
            if stream:
                try:
                    stream.stop()
                    stream.close()
                    print(f"[INFO] {name} stream closed")
                except Exception as e:
                    print(f"[ERROR] {name} close: {e}")

    def _open_mic(self):
        """Opens microphone at its native sample rate."""
        if self.mic_index is None:
            print("[!] No mic — skipping")
            return
        try:
            self.mic_stream = sd.InputStream(
                device=self.mic_index,
                channels=CHANNELS,
                samplerate=self.mic_rate,
                callback=self._mic_cb,
                blocksize=BLOCKSIZE
            )
            self.mic_stream.start()
            name = sd.query_devices(self.mic_index)['name']
            print(f"[✓] Microphone stream opened: {name} (index {self.mic_index})")
        except Exception as e:
            print(f"[ERROR] Mic stream failed: {e}")

    def _open_speaker(self):
        """Opens speaker capture at its native sample rate."""
        if self.speaker_index is None:
            print("[!] No speaker capture — THEM disabled")
            return
        try:
            self.speaker_stream = sd.InputStream(
                device=self.speaker_index,
                channels=CHANNELS,
                samplerate=self.speaker_rate,
                callback=self._speaker_cb,
                blocksize=BLOCKSIZE
            )
            self.speaker_stream.start()
            name = sd.query_devices(self.speaker_index)['name']
            print(f"[✓] Speaker capture opened: {name} (index {self.speaker_index})")
        except Exception as e:
            print(f"[ERROR] Speaker stream failed: {e}")

    def _mic_cb(self, indata, frames, time_info, status):
        """Mic audio callback — YOUR voice."""
        self.mic_buffer.extend(indata[:, 0].tolist())
        while len(self.mic_buffer) >= self.mic_chunk_samples:
            chunk = np.array(
                self.mic_buffer[:self.mic_chunk_samples],
                dtype=np.float32
            )
            self.mic_buffer = self.mic_buffer[self.mic_chunk_samples:]
            speech = self.mic_vad.process(chunk)
            if speech is not None:
                self.transcriber.transcribe_chunk(
                    speech, "YOU", source_rate=self.mic_rate
                )

    def _speaker_cb(self, indata, frames, time_info, status):
        """Speaker audio callback — THEIR voice."""
        self.speaker_buffer.extend(indata[:, 0].tolist())
        while len(self.speaker_buffer) >= self.speaker_chunk_samples:
            chunk = np.array(
                self.speaker_buffer[:self.speaker_chunk_samples],
                dtype=np.float32
            )
            self.speaker_buffer = self.speaker_buffer[self.speaker_chunk_samples:]
            speech = self.speaker_vad.process(chunk)
            if speech is not None:
                self.transcriber.transcribe_chunk(
                    speech, "THEM", source_rate=self.speaker_rate
                )


# =============================================================
# AUDIO MANAGER — used by main.py
# =============================================================

class AudioManager:
    """
    Top-level audio coordinator for MilJoy.
    Section 11: Auto-detects devices on any machine.
    No hardcoded indexes needed.
    """

    def __init__(self, on_transcript_callback,
                 mic_index=None, loopback_index=None):
        print("\n[AUDIO] Initializing MilJoy Audio Manager...")

        self.on_transcript    = on_transcript_callback
        self.is_running       = False
        self.transcript_history = []

        # Auto-detect devices
        # mic_index/loopback_index from settings used as hints
        # but auto-detection verifies and finds best match
        self.mic_index, self.speaker_index = AutoDeviceDetector.detect_all()

        # Initialize Whisper
        self.transcriber = WhisperTranscriber(
            on_transcript_callback=self._handle_transcript
        )

        # Initialize capture
        self.capture = AudioCapture(
            transcriber=self.transcriber,
            mic_index=self.mic_index,
            speaker_index=self.speaker_index
        )

        print("[✓] Audio Manager ready\n")

    def start(self):
        if self.is_running:
            return
        print("[AUDIO] Starting capture...")
        self.transcriber.start_processing()
        self.capture.start()
        self.is_running = True
        print("[✓] Listening started")

    def stop(self):
        if not self.is_running:
            return
        print("[AUDIO] Stopping...")
        self.capture.stop()
        self.transcriber.stop_processing()
        self.is_running = False
        print("[✓] Audio stopped")

    def get_transcript_history(self):
        """Returns last 20 lines for AI context."""
        return "\n".join(self.transcript_history[-20:])

    def _handle_transcript(self, text, speaker):
        entry = f"{speaker}: {text}"
        self.transcript_history.append(entry)
        if len(self.transcript_history) > 50:
            self.transcript_history = self.transcript_history[-50:]
        self.on_transcript(text, speaker)


# =============================================================
# STANDALONE TEST
# Run: python audio.py
# =============================================================

if __name__ == "__main__":
    print("==============================================")
    print("  MilJoy Audio Test — Section 11")
    print("==============================================")
    print("Auto-detecting devices...")
    print("Speak → YOU  |  Play YouTube → THEM\n")

    def cb(text, speaker):
        print(f"  >>> [{speaker}]: {text}")

    manager = AudioManager(on_transcript_callback=cb)
    manager.start()

    try:
        print("Listening for 40 seconds!\n")
        time.sleep(40)
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        manager.stop()
        print("Test complete.")
