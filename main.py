#!/usr/bin/env python3
"""
Stealth Interview Assistant
A desktop application with:
1. Stealth overlay window (invisible to screen capture)
2. Dual-channel audio capture (microphone + system audio)
3. Monitor mode for verifying audio capture
"""

import sys
import threading
import time
from stealth_overlay import StealthOverlay
from audio_capture import DualChannelAudioCapture


class StealthAssistant:
    """Main application controller"""

    def __init__(self, gui_mode=True):
        self.gui_mode = gui_mode
        self.overlay = None
        self.audio_capture = None
        self.running = False

    def run_with_gui(self):
        """Run application with GUI overlay"""
        print("\n" + "="*60)
        print("Stealth Interview Assistant - GUI Mode")
        print("="*60 + "\n")

        # Initialize audio capture
        self.audio_capture = DualChannelAudioCapture()

        # Initialize overlay
        self.overlay = StealthOverlay()
        self.overlay.update_status("Initializing audio capture...")

        # Start audio capture in separate thread
        audio_thread = threading.Thread(target=self._start_audio_capture, daemon=True)
        audio_thread.start()

        # Start GUI monitoring in separate thread
        monitor_thread = threading.Thread(target=self._monitor_audio, daemon=True)
        monitor_thread.start()

        # Run the overlay (blocking)
        try:
            self.overlay.run()
        except KeyboardInterrupt:
            pass
        finally:
            self.cleanup()

    def _start_audio_capture(self):
        """Initialize and start audio capture"""
        time.sleep(1)  # Wait for GUI to initialize

        if self.audio_capture.start_capture():
            if self.overlay:
                self.overlay.update_status("Audio capture active")
                self.overlay.update_mic_status(True)
                self.overlay.update_speaker_status(True)
        else:
            if self.overlay:
                self.overlay.update_status("Audio capture failed")

        self.running = True

    def _monitor_audio(self):
        """Monitor audio streams and update GUI"""
        sample_count = {"mic": 0, "speaker": 0}

        while True:
            if not self.running or not self.audio_capture:
                time.sleep(0.1)
                continue

            # Check microphone data
            mic_data = self.audio_capture.get_mic_data(timeout=0.1)
            if mic_data:
                sample_count["mic"] += 1
                if self.overlay and sample_count["mic"] % 10 == 0:  # Update every 10 samples
                    text = f"Sample #{sample_count['mic']} ({len(mic_data)} bytes) [Transcribing...]"
                    self.overlay.add_transcript("mic", text)
                    self.overlay.update_mic_status(True)

            # Check speaker data
            speaker_data = self.audio_capture.get_speaker_data(timeout=0.1)
            if speaker_data:
                sample_count["speaker"] += 1
                if self.overlay and sample_count["speaker"] % 10 == 0:  # Update every 10 samples
                    text = f"Sample #{sample_count['speaker']} ({len(speaker_data)} bytes) [Transcribing...]"
                    self.overlay.add_transcript("speaker", text)
                    self.overlay.update_speaker_status(True)

            time.sleep(0.05)

    def run_monitor_mode(self, duration=None):
        """Run in console monitor mode (no GUI)"""
        print("\n" + "="*60)
        print("Stealth Interview Assistant - Monitor Mode")
        print("="*60 + "\n")

        self.audio_capture = DualChannelAudioCapture()
        self.audio_capture.monitor_mode(duration=duration)
        self.cleanup()

    def cleanup(self):
        """Clean up resources"""
        print("\n🧹 Cleaning up...")
        self.running = False

        if self.audio_capture:
            self.audio_capture.cleanup()

        print("✓ Cleanup complete")


def print_usage():
    """Print usage information"""
    print("\n" + "="*60)
    print("Stealth Interview Assistant")
    print("="*60 + "\n")
    print("Usage:")
    print("  python main.py              - Run with GUI overlay")
    print("  python main.py monitor      - Run monitor mode (console only)")
    print("  python main.py devices      - List available audio devices")
    print("  python main.py help         - Show this help message")
    print("\nFeatures:")
    print("  ✓ Stealth overlay (invisible to screen capture)")
    print("  ✓ Dual-channel audio capture (mic + system audio)")
    print("  ✓ Live monitoring and transcription placeholders")
    print("\nRequirements:")
    print("  - Windows 10/11")
    print("  - Python 3.8+")
    print("  - See requirements.txt for dependencies")
    print()


def main():
    """Main entry point"""
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()

        if command == "help":
            print_usage()
            return

        elif command == "devices":
            print("\nListing audio devices...\n")
            audio = DualChannelAudioCapture()
            audio.list_devices()
            audio.cleanup()
            return

        elif command == "monitor":
            app = StealthAssistant(gui_mode=False)
            try:
                app.run_monitor_mode()
            except KeyboardInterrupt:
                print("\n\n✓ Stopped by user")
            return

        else:
            print(f"\n❌ Unknown command: {command}")
            print_usage()
            return

    # Default: run with GUI
    app = StealthAssistant(gui_mode=True)
    try:
        app.run_with_gui()
    except KeyboardInterrupt:
        print("\n\n✓ Stopped by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
