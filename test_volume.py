import sounddevice as sd
import numpy as np
import time

print("Testing microphone volume for 10 seconds...")
print("Speak normally and watch the RMS values\n")

def callback(indata, frames, time_info, status):
    rms = float(np.sqrt(np.mean(indata.astype(np.float32) ** 2)))
    bars = int(rms * 500)
    bar = "█" * min(bars, 40)
    print(f"RMS: {rms:.4f}  |  {bar}")

with sd.InputStream(device=22, channels=1,
                    samplerate=48000, callback=callback,
                    blocksize=4096):
    time.sleep(10)

print("\nDone! Look at the RMS values above.")
print("Your VAD threshold is currently 0.025")
print("RMS needs to be ABOVE 0.025 to trigger transcription")