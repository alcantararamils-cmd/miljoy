# 🎙 MilJoy — AI Call Assistant

> Your real-time AI co-pilot for every call. Suggests what to say next based on the live conversation — completely invisible to screen share.

![MilJoy Banner](assets/banner.png)

---

## ✨ Features

- 🤖 **Real-time AI suggestions** — generates natural responses based on what the other person says
- 🎤 **Live transcription** — transcribes both sides of the call separately (YOU and THEM)
- 👻 **Invisible to screen share** — only you can see it
- 📋 **Pre-call setup** — set call purpose and generate an opening greeting before you start
- 📜 **Spiel panel** — paste your script with built-in teleprompter mode
- ⏸ **Pause suggestions** — freeze the suggestion while you finish reading
- ⌨️ **Ctrl+Space hotkey** — get a new suggestion instantly anytime
- 📝 **Auto call notes** — generates AI summary + saves transcript after every call
- 📧 **Email delivery** — sends call summary to your Gmail automatically
- 💾 **One-time setup** — settings saved forever, no re-entering API keys

---

## 🖥️ Requirements

- Windows 10 or 11
- Python 3.10 or higher
- Microphone
- [VB-Audio Virtual Cable](https://vb-audio.com/Cable/) (free) — for capturing the other person's voice
- [Groq API key](https://console.groq.com) (free)
- Gmail account (for receiving call summaries)

---

## 🚀 Installation

### Step 1 — Clone the repository
```bash
git clone https://github.com/yourusername/miljoy.git
cd miljoy
```

### Step 2 — Install Python dependencies
```bash
pip install -r requirements.txt
```

### Step 3 — Install VB-Audio Virtual Cable
1. Download from [vb-audio.com/Cable](https://vb-audio.com/Cable/)
2. Run installer as Administrator
3. Restart your computer
4. Set **CABLE Input** as your default playback device in Windows Sound Settings
5. Enable **Listen to this device** on CABLE Output (Recording tab → CABLE Output → Properties → Listen)

### Step 4 — Set up encrypted credentials (app owners only)
Open `security.py` and fill in your Gmail and app password in `owner_setup()`, then run:
```bash
python security.py
```
This creates `miljoy_credentials.enc`. After running, remove your plain text credentials from the file.

> 💡 **Gmail App Password**: Go to myaccount.google.com → Security → App Passwords → Create one for MilJoy

### Step 5 — Run MilJoy
```bash
python main.py
```

The setup wizard will guide you through the rest on first launch.

---

## 📁 File Structure

```
miljoy/
├── main.py              # Main floating window
├── audio.py             # Audio capture + transcription
├── ai.py                # Groq AI integration
├── onboarding.py        # Setup wizard
├── notetaker.py         # Call summary + email
├── security.py          # Encrypted credentials + usage tracking
├── spiel.py             # Spiel panel + teleprompter
├── requirements.txt     # Python dependencies
├── .gitignore           # Git ignore rules
└── README.md            # This file
```

---

## 🎯 How to Use

### Before the call:
1. Open MilJoy — `python main.py`
2. Click **📜** to open your Spiel panel and paste your script
3. Select your **call purpose** (Sales, Interview, Meeting, etc.)
4. Click **✨ Generate Opening** to get a suggested greeting
5. Click **▶ Start Listening**

### During the call:
- AI suggestions appear automatically when the other person finishes speaking
- **Ctrl+Space** — get a new suggestion instantly
- **⏸ Pause** — freeze current suggestion while you read
- Hover over suggestion box — auto-pauses
- **YOU** (green) and **THEM** (blue) transcripts shown separately

### After the call:
- Click **■ Stop Listening**
- MilJoy automatically generates a call summary
- Summary + full transcript saved to `Documents/MilJoy Notes/`
- Email sent to your Gmail with summary attached

---

## ⚙️ Settings

Click **⚙** in the title bar to access settings:
- View current configuration
- Re-detect audio devices
- Reset setup (runs onboarding again)

---

## 🔧 Troubleshooting

| Problem | Solution |
|---|---|
| No transcription appearing | Check mic volume in Windows Sound Settings — raise to 80-100 |
| THEM not transcribing | Make sure CABLE Input is set as default playback device |
| Choppy audio | Increase VB-Audio buffer — open VB-Audio control panel, set latency to 7168 |
| Screen hide not working | Run VS Code or terminal as Administrator |
| Email not sending | Re-run `python security.py` — check app password has no spaces |
| Wrong devices detected | Settings → Re-detect Audio Devices |
| Reset everything | Delete `settings.json` and restart |

---

## 📊 Usage Statistics

MilJoy tracks anonymous launch counts (no personal data ever). View total launches at:
```
https://api.countapi.xyz/get/miljoy-app/launches
```

---

## 🔒 Security & Privacy

- All transcription happens **locally** on your machine (Whisper runs offline)
- Only AI suggestion requests are sent to Groq's servers (transcript snippets only)
- Your Gmail credentials are stored in an **encrypted file** (`miljoy_credentials.enc`)
- Call summaries are stored locally in `Documents/MilJoy Notes/`
- No data is sold or shared with third parties

---

## 🗺️ Roadmap

- [ ] Gemini AI support (Google login)
- [ ] ChatGPT support
- [ ] Speaker diarization (identify multiple speakers)
- [ ] Mobile companion app
- [ ] Windows installer (.exe)
- [ ] Custom AI personas per call type
- [ ] Call history dashboard

---

## 📄 License

MIT License — free to use, modify, and distribute.

---

## 🙏 Credits

Built with:
- [faster-whisper](https://github.com/guillaumekln/faster-whisper) — local speech transcription
- [Groq](https://groq.com) — ultra-fast AI inference
- [VB-Audio](https://vb-audio.com) — virtual audio cable

---

*Made with ❤️ by Mil*
