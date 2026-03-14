# Quick Start Guide

Get up and running with Stealth Interview Assistant in 5 minutes.

## Prerequisites Check

Before starting, verify you have:
- ✅ Windows 10 or Windows 11
- ✅ Python 3.8 or higher installed
- ✅ Working microphone
- ✅ Audio playing through speakers/headphones

## Step-by-Step Setup

### 1. Install Dependencies

Open Command Prompt or PowerShell in the project directory and run:

```bash
pip install -r requirements.txt
```

Wait for all packages to install (this may take a few minutes).

### 2. Test Audio Devices

Verify your audio devices are detected:

```bash
python main.py devices
```

You should see a list of devices. Look for:
- Your microphone in the input devices
- A "Loopback" device for system audio

### 3. Run Monitor Mode (Recommended First Test)

Test audio capture without the GUI:

```bash
python main.py monitor
```

**What to do**:
1. Speak into your microphone - you should see `[MIC]` lines appearing
2. Play some audio (music, video) - you should see `[SPK]` lines appearing
3. Press `Ctrl+C` to stop

**Expected output**:
```
[MIC] 🎤 Sample #1 | Size: 2048 bytes | [Transcribing...]
[SPK] 🔊 Sample #1 | Size: 4096 bytes | [Transcribing...]
[MIC] 🎤 Sample #2 | Size: 2048 bytes | [Transcribing...]
```

If you see both `[MIC]` and `[SPK]` lines, audio capture is working!

### 4. Launch the GUI

Run the full application:

```bash
python main.py
```

A dark overlay window will appear with:
- 🎤 Green indicator when microphone is active
- 🔊 Green indicator when system audio is active
- Live transcript area showing captured audio samples

### 5. Test Screen Capture Exclusion

To verify the stealth feature is working:

1. Keep the overlay window open
2. Start a screen recording or take a screenshot
3. Check the recording/screenshot - the overlay should appear as a black rectangle or be invisible

Or test with Zoom/Teams:
1. Start a test meeting
2. Share your screen
3. The overlay should be invisible to other participants

## Common Usage Scenarios

### During an Interview

1. **Before the interview starts**:
   ```bash
   python main.py
   ```

2. **Position the overlay** on a secondary monitor or in a corner

3. **Join your interview** (Zoom, Teams, etc.)

4. **The overlay will show**:
   - Your questions/voice in `[MIC]` lines
   - Interviewer's responses in `[SPK]` lines

5. **After the interview**, close the overlay window

### Testing Without GUI

For quick audio testing:

```bash
python main.py monitor
```

Speak and play audio to verify capture. Press `Ctrl+C` when done.

## Troubleshooting

### Problem: No `[MIC]` lines appearing

**Solutions**:
- Check microphone is plugged in
- Verify microphone permissions in Windows Settings → Privacy → Microphone
- Try speaking louder or closer to the mic
- Run `python main.py devices` to verify microphone is detected

### Problem: No `[SPK]` lines appearing

**Solutions**:
- Ensure audio is actually playing (test with music or YouTube)
- Check volume is not muted
- Verify WASAPI loopback device exists: `python main.py devices`
- Try using speakers instead of headphones (or vice versa)

### Problem: Overlay is visible in screen share

**Solutions**:
- Verify you're on Windows 10/11 (feature not available on older Windows)
- Restart the application
- Some capture software may bypass the exclusion (rare)

### Problem: "ModuleNotFoundError"

**Solution**:
```bash
pip install -r requirements.txt
```

Make sure all dependencies are installed.

### Problem: Application crashes immediately

**Solutions**:
1. Check Python version: `python --version` (must be 3.8+)
2. Reinstall dependencies: `pip install -r requirements.txt --force-reinstall`
3. Try monitor mode first: `python main.py monitor`
4. Check for error messages and see README.md troubleshooting section

## Next Steps

Once everything is working:

1. **Customize the overlay**:
   - Edit `stealth_overlay.py` to change size, transparency, or colors
   - Modify window position in `__init__` method

2. **Add transcription**:
   - Integrate Whisper, Google Speech-to-Text, or Azure Speech
   - Replace placeholder text with actual transcriptions

3. **Add AI assistance**:
   - Send transcripts to GPT-4, Claude, or other LLMs
   - Get real-time suggestions and answers

4. **Record sessions**:
   - Use the `save_to_wav` method in `audio_capture.py`
   - Save both channels for later review

## Tips for Best Results

1. **Audio Quality**:
   - Use a good quality microphone
   - Minimize background noise
   - Test before important meetings

2. **Positioning**:
   - Place overlay on secondary monitor if available
   - Keep it visible but not distracting
   - Ensure you can read it comfortably

3. **Performance**:
   - Close unnecessary applications
   - Monitor CPU usage during calls
   - Use wired internet connection when possible

4. **Testing**:
   - Always test before real interviews
   - Verify audio capture with `monitor` mode
   - Check screen share invisibility

## Support

If you encounter issues:
1. Check the troubleshooting section above
2. Review README.md for detailed documentation
3. Verify system requirements
4. Test with `monitor` mode to isolate GUI vs audio issues

## Safety Reminder

⚠️ **Important**:
- Know your local recording laws
- Obtain consent when required
- Follow platform terms of service
- Use ethically and responsibly
