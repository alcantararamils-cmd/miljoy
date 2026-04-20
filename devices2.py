import sounddevice as sd

hostapis = sd.query_hostapis()
devices = sd.query_devices()

for i, d in enumerate(devices):
    if d['max_input_channels'] > 0:
        api = hostapis[d['hostapi']]['name']
        print(f"[{i}] {d['name']} | API: {api} | inputs: {d['max_input_channels']}")