import sounddevice as sd

# Test all CABLE Output indexes specifically
cable_indexes = [1, 10, 24, 25]

for idx in cable_indexes:
    device = sd.query_devices(idx)
    print(f"\nTrying [{idx}]: {device['name']}")
    print(f"  Inputs: {device['max_input_channels']}")
    print(f"  Default rate: {device['default_samplerate']}")
    
    for rate in [44100, 48000]:
        for ch in [1, 2]:
            try:
                with sd.InputStream(
                    device=idx,
                    channels=ch,
                    samplerate=rate
                ):
                    print(f"  ✓ {rate}Hz {ch}ch works!")
                    break
            except Exception as e:
                print(f"  ✗ {rate}Hz {ch}ch — {e}")