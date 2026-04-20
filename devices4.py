import sounddevice as sd

# Try opening WASAPI devices with different settings
for idx in [22, 23]:
    device = sd.query_devices(idx)
    print(f"\nTrying device [{idx}]: {device['name']}")
    
    # Try 1: Standard open
    try:
        with sd.InputStream(device=idx, channels=1, samplerate=48000):
            print(f"  ✓ Standard open works!")
    except Exception as e:
        print(f"  ✗ Standard: {e}")
    
    # Try 2: With 2 channels
    try:
        with sd.InputStream(device=idx, channels=2, samplerate=48000):
            print(f"  ✓ 2-channel open works!")
    except Exception as e:
        print(f"  ✗ 2-channel: {e}")

    # Try 3: Using default sample rate
    try:
        rate = int(device['default_samplerate'])
        with sd.InputStream(device=idx, channels=1, samplerate=rate):
            print(f"  ✓ Default rate ({rate}Hz) works!")
    except Exception as e:
        print(f"  ✗ Default rate: {e}")

    # Try 4: No sample rate specified
    try:
        with sd.InputStream(device=idx, channels=1):
            print(f"  ✓ No rate specified works!")
    except Exception as e:
        print(f"  ✗ No rate: {e}")