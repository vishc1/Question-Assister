# Stealth Interview Assistant

A Python desktop application designed for interview assistance with two main components:

1. **Stealth Overlay Window**: A semi-transparent, frameless window that's always on top but completely invisible to screen capture software (Zoom, Teams, Google Meet)
2. **Dual-Channel Audio Capture**: Simultaneous capture of microphone input and system audio output using WASAPI loopback

## Features

- 🎯 **Screen Capture Exclusion**: Uses Windows API (`WDA_EXCLUDEFROMCAPTURE`) to hide the overlay from screen sharing
- 🎤 **Microphone Capture**: Records your voice (Channel A)
- 🔊 **System Audio Capture**: Records interviewer's voice via WASAPI loopback (Channel B)
- 📊 **Live Monitor Mode**: Console output showing real-time audio capture from both channels
- 🎨 **Modern UI**: Dark theme overlay with audio status indicators
- 🔄 **Dual-Stream Processing**: Separate queues for independent audio stream handling

## System Requirements

- **Operating System**: Windows 10/11 (required for WDA_EXCLUDEFROMCAPTURE)
- **Python**: 3.8 or higher
- **Audio**: Working microphone and system audio output

## Installation

1. **Clone or download this repository**

2. **Install Python dependencies**:
```bash
pip install -r requirements.txt
```

The main dependencies are:
- `customtkinter` - Modern UI framework
- `pyaudiowpatch` - Extended PyAudio with WASAPI loopback support
- `pywin32` - Windows API access
- `comtypes` - COM interface support

## Usage

### 1. GUI Mode (Default)

Run the application with the stealth overlay window:

```bash
python main.py
```

This will:
- Open a semi-transparent overlay window
- Start capturing audio from both microphone and system audio
- Display live transcription placeholders in the overlay
- Show visual indicators for active audio streams

The overlay window:
- Can be dragged around the screen
- Stays on top of all other windows
- Is invisible to screen capture software
- Shows real-time audio capture status

### 2. Monitor Mode (Console Only)

Test audio capture without the GUI:

```bash
python main.py monitor
```

This will:
- Print live transcription placeholders to the console
- Show sample counts and data sizes from both channels
- Verify that both audio streams are working correctly
- Display statistics when stopped (Ctrl+C)

Example output:
```
[MIC] 🎤 Sample #1 | Size: 2048 bytes | [Transcribing...]
[SPK] 🔊 Sample #1 | Size: 4096 bytes | [Transcribing...]
[MIC] 🎤 Sample #2 | Size: 2048 bytes | [Transcribing...]
[SPK] 🔊 Sample #2 | Size: 4096 bytes | [Transcribing...]
```

### 3. List Audio Devices

Check available audio devices on your system:

```bash
python main.py devices
```

This will display all audio input/output devices with their properties.

### 4. Help

Display usage information:

```bash
python main.py help
```

## How It Works

### Stealth Overlay

The overlay window uses multiple Windows API techniques to remain invisible to screen capture:

1. **`SetWindowDisplayAffinity(WDA_EXCLUDEFROMCAPTURE)`**: Primary method to exclude window from capture
2. **`DwmSetWindowAttribute`**: Additional Desktop Window Manager settings
3. **Frameless & Transparent**: Custom window styling for minimal visibility
4. **Always on Top**: Stays visible above all applications

The window is visible on your physical screen but appears as a black rectangle or is completely invisible to anyone viewing your screen through Zoom, Teams, Google Meet, or any other screen sharing software.

### Dual-Channel Audio Capture

Uses PyAudioWPatch (PyAudio with WASAPI support) to capture two separate audio streams:

**Channel A - Microphone**:
- Captures from default input device
- Records your voice
- Mono audio stream
- 16kHz sample rate

**Channel B - System Audio (Loopback)**:
- Uses WASAPI loopback device
- Captures all system audio output
- Records interviewer's voice from the meeting
- Stereo audio stream
- Native sample rate (typically 44.1kHz or 48kHz)

Both streams are captured simultaneously in separate threads with independent queues, allowing for real-time processing without blocking.

## Architecture

```
main.py
├── StealthAssistant (Main Controller)
│   ├── Initializes components
│   ├── Manages threads
│   └── Coordinates GUI and audio
│
stealth_overlay.py
├── StealthOverlay (GUI Component)
│   ├── CustomTkinter window
│   ├── Windows API integration
│   ├── Status indicators
│   └── Transcript display
│
audio_capture.py
└── DualChannelAudioCapture (Audio Component)
    ├── PyAudioWPatch integration
    ├── Device detection
    ├── Dual stream management
    └── Monitor mode
```

## Important Notes

### Privacy & Ethics

This tool is designed for personal use in situations where you have the right to record. Be aware of:
- Recording laws in your jurisdiction
- Terms of service of the platform you're using
- Consent requirements for recording conversations

### Limitations

- **Windows Only**: The screen capture exclusion feature requires Windows 10/11
- **WASAPI Required**: System audio capture needs WASAPI loopback support
- **Not 100% Guaranteed**: Some screen capture methods might still detect the window
- **Performance**: Running during video calls may impact system performance

### Troubleshooting

**Overlay is visible in screen share**:
- Ensure you're running Windows 10/11
- Try restarting the application
- Check if your screen sharing software uses non-standard capture methods

**No audio captured from speakers**:
- Verify system audio is playing
- Check that WASAPI loopback device is available
- Run `python main.py devices` to list available devices
- Ensure no other application is exclusively using the audio device

**No audio captured from microphone**:
- Check microphone permissions in Windows Settings
- Verify microphone is working in other applications
- Select correct device if multiple microphones are available

**Application crashes on startup**:
- Verify all dependencies are installed: `pip install -r requirements.txt`
- Check Python version (3.8+ required)
- Run in monitor mode first to test audio capture: `python main.py monitor`

## Development

### Project Structure

```
Question Assister/
├── main.py                 # Application entry point
├── stealth_overlay.py      # GUI overlay component
├── audio_capture.py        # Audio capture component
├── requirements.txt        # Python dependencies
└── README.md              # This file
```

### Extending the Application

The modular design allows easy extension:

1. **Add Transcription**: Integrate speech-to-text APIs (Whisper, Google Cloud, Azure)
2. **Add LLM Integration**: Send transcripts to GPT/Claude for real-time assistance
3. **Add Recording**: Save audio streams to WAV files
4. **Add Hotkeys**: Global keyboard shortcuts for controls
5. **Add Configuration**: User settings for audio devices, window position, etc.

### Code Structure

**StealthOverlay** (`stealth_overlay.py`):
- `__init__`: Initialize window and UI
- `_configure_window`: Set window properties
- `_apply_stealth_settings`: Apply Windows API exclusion
- `_create_ui`: Build interface elements
- `update_status`: Update status messages
- `add_transcript`: Add text to transcript box

**DualChannelAudioCapture** (`audio_capture.py`):
- `find_devices`: Auto-detect audio devices
- `start_capture`: Begin dual-stream capture
- `stop_capture`: Stop all streams
- `monitor_mode`: Console monitoring
- `get_mic_data/get_speaker_data`: Retrieve audio from queues

## License

This project is provided as-is for educational purposes. Use responsibly and ethically.

## Disclaimer

This software is intended for personal use only. Users are responsible for:
- Complying with local recording laws
- Obtaining necessary consent for recordings
- Following platform terms of service
- Using the software ethically and legally

The developers assume no liability for misuse of this software.
