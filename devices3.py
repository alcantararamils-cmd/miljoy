import sounddevice as sd

# Test which sample rates work for indexes 22 and 23
test_rates = [8000, 16000, 22050, 44100, 48000, 96000]

for device_index in [22, 23]:
    device = sd.query_devices(device_index)
    print(f"\nDevice [{device_index}]: {device['name']}")
    print(f"Default sample rate: {device['default_samplerate']}")
    print(f"Max input channels: {device['max_input_channels']}")
    
    for rate in test_rates:
        try:
            sd.check_input_settings(
                device=device_index,
                channels=1,
                samplerate=rate
            )
            print(f"  ✓ {rate}Hz supported")
        except Exception as e:
            print(f"  ✗ {rate}Hz — {e}")