"""
Real-time Transcription Module
Uses Deepgram SDK for live speech-to-text transcription
Includes silence detection and query extraction
"""

import asyncio
import time
import threading
from collections import deque
from typing import Callable, Optional, List
import queue

from deepgram import (
    DeepgramClient,
    DeepgramClientOptions,
    LiveTranscriptionEvents,
    LiveOptions,
)

from config import Config


class SilenceDetector:
    """
    Detects silence periods in transcription stream
    Triggers callback when silence threshold is reached
    """

    def __init__(self, silence_threshold: float = 1.5, min_query_length: int = 10):
        """
        Args:
            silence_threshold: Seconds of silence before triggering (default 1.5)
            min_query_length: Minimum characters for valid query (default 10)
        """
        self.silence_threshold = silence_threshold
        self.min_query_length = min_query_length

        self.last_speech_time = None
        self.current_transcript = ""
        self.is_speaking = False

        self.on_silence_detected = None  # Callback function

    def update(self, transcript: str, is_final: bool = False):
        """
        Update with new transcript text

        Args:
            transcript: New transcript text
            is_final: Whether this is a final transcript
        """
        current_time = time.time()

        if transcript.strip():
            # Speech detected
            self.last_speech_time = current_time
            self.is_speaking = True

            # Accumulate transcript
            if is_final:
                self.current_transcript += " " + transcript.strip()
        else:
            # No speech in this update
            if self.is_speaking and self.last_speech_time:
                silence_duration = current_time - self.last_speech_time

                if silence_duration >= self.silence_threshold:
                    # Silence threshold reached
                    self._trigger_silence()

    def _trigger_silence(self):
        """Trigger silence detection callback"""
        if not self.current_transcript.strip():
            return

        # Check minimum length
        if len(self.current_transcript.strip()) < self.min_query_length:
            self.reset()
            return

        # Call callback with accumulated transcript
        if self.on_silence_detected:
            query = self.current_transcript.strip()
            self.on_silence_detected(query)

        # Reset for next query
        self.reset()

    def reset(self):
        """Reset detector state"""
        self.current_transcript = ""
        self.is_speaking = False
        self.last_speech_time = None

    def force_trigger(self):
        """Force trigger silence detection (for manual triggering)"""
        if self.current_transcript.strip():
            self._trigger_silence()


class RealtimeTranscription:
    """
    Real-time transcription using Deepgram
    Processes audio stream and provides live transcript
    """

    def __init__(
        self,
        api_key: str = None,
        silence_threshold: float = None,
        min_query_length: int = None
    ):
        """
        Initialize transcription system

        Args:
            api_key: Deepgram API key (defaults to config)
            silence_threshold: Silence detection threshold in seconds
            min_query_length: Minimum query length in characters
        """
        self.api_key = api_key or Config.DEEPGRAM_API_KEY
        self.silence_threshold = silence_threshold or Config.SILENCE_THRESHOLD
        self.min_query_length = min_query_length or Config.MIN_QUERY_LENGTH

        # Deepgram client
        self.deepgram = None
        self.connection = None

        # Silence detector
        self.silence_detector = SilenceDetector(
            silence_threshold=self.silence_threshold,
            min_query_length=self.min_query_length
        )

        # Audio queue for processing
        self.audio_queue = queue.Queue()

        # State
        self.is_transcribing = False
        self.transcription_thread = None

        # Callbacks
        self.on_transcript = None  # Called for each transcript update
        self.on_query_detected = None  # Called when silence detected (full query)
        self.on_error = None  # Called on errors

        # Stats
        self.stats = {
            "transcripts_received": 0,
            "queries_detected": 0,
            "errors": 0
        }

    def initialize(self):
        """Initialize Deepgram client"""
        try:
            config = DeepgramClientOptions(
                options={"keepalive": "true"}
            )
            self.deepgram = DeepgramClient(self.api_key, config)
            print("✓ Deepgram client initialized")
            return True
        except Exception as e:
            print(f"✗ Error initializing Deepgram: {e}")
            if self.on_error:
                self.on_error(f"Initialization error: {e}")
            return False

    async def _start_transcription_async(self):
        """Start async transcription session"""
        try:
            # Configure live transcription options
            options = LiveOptions(
                model="nova-2",
                language="en-US",
                smart_format=True,
                interim_results=True,
                utterance_end_ms="1000",
                vad_events=True,
                punctuate=True,
            )

            # Create connection
            self.connection = self.deepgram.listen.asynclive.v("1")

            # Set up event handlers
            self.connection.on(LiveTranscriptionEvents.Transcript, self._on_message)
            self.connection.on(LiveTranscriptionEvents.Error, self._on_error)
            self.connection.on(LiveTranscriptionEvents.Close, self._on_close)

            # Start connection
            if await self.connection.start(options):
                print("✓ Deepgram connection established")

                # Process audio from queue
                while self.is_transcribing:
                    try:
                        # Get audio data from queue (non-blocking with timeout)
                        audio_data = self.audio_queue.get(timeout=0.1)

                        if audio_data:
                            # Send to Deepgram
                            await self.connection.send(audio_data)

                    except queue.Empty:
                        # No audio data, continue
                        await asyncio.sleep(0.01)
                    except Exception as e:
                        print(f"Error sending audio: {e}")
                        break

                # Close connection
                await self.connection.finish()
            else:
                print("✗ Failed to start Deepgram connection")

        except Exception as e:
            print(f"✗ Transcription error: {e}")
            self.stats["errors"] += 1
            if self.on_error:
                self.on_error(f"Transcription error: {e}")

    def _on_message(self, result, **kwargs):
        """Handle transcript message from Deepgram"""
        try:
            sentence = result.channel.alternatives[0].transcript

            if len(sentence) == 0:
                return

            is_final = result.is_final

            # Update stats
            self.stats["transcripts_received"] += 1

            # Call transcript callback
            if self.on_transcript:
                self.on_transcript(sentence, is_final)

            # Update silence detector
            self.silence_detector.update(sentence, is_final)

        except Exception as e:
            print(f"Error processing message: {e}")
            self.stats["errors"] += 1

    def _on_error(self, error, **kwargs):
        """Handle error from Deepgram"""
        print(f"✗ Deepgram error: {error}")
        self.stats["errors"] += 1
        if self.on_error:
            self.on_error(str(error))

    def _on_close(self, **kwargs):
        """Handle connection close"""
        print("✓ Deepgram connection closed")

    def start_transcription(self):
        """Start transcription in background thread"""
        if self.is_transcribing:
            print("⚠ Transcription already running")
            return False

        if not self.api_key:
            print("✗ Deepgram API key not set")
            return False

        # Initialize if needed
        if not self.deepgram:
            if not self.initialize():
                return False

        # Set up silence detector callback
        self.silence_detector.on_silence_detected = self._handle_query_detected

        # Start transcription in thread
        self.is_transcribing = True

        def run_async():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self._start_transcription_async())
            loop.close()

        self.transcription_thread = threading.Thread(target=run_async, daemon=True)
        self.transcription_thread.start()

        print("✓ Transcription started")
        return True

    def stop_transcription(self):
        """Stop transcription"""
        self.is_transcribing = False

        if self.transcription_thread:
            self.transcription_thread.join(timeout=2)

        print("✓ Transcription stopped")

    def send_audio(self, audio_data: bytes):
        """
        Send audio data for transcription

        Args:
            audio_data: Raw audio bytes
        """
        if self.is_transcribing:
            self.audio_queue.put(audio_data)

    def _handle_query_detected(self, query: str):
        """Handle query detected by silence detector"""
        self.stats["queries_detected"] += 1

        print(f"\n[QUERY DETECTED] {query}")

        if self.on_query_detected:
            self.on_query_detected(query)

    def get_stats(self):
        """Get transcription statistics"""
        return self.stats.copy()

    def print_stats(self):
        """Print statistics"""
        print("\n" + "="*60)
        print("Transcription Statistics")
        print("="*60)
        print(f"Transcripts received: {self.stats['transcripts_received']}")
        print(f"Queries detected: {self.stats['queries_detected']}")
        print(f"Errors: {self.stats['errors']}")
        print("="*60 + "\n")


def test_transcription():
    """Test transcription with simulated audio"""
    import pyaudiowpatch as pyaudio

    print("\n" + "="*60)
    print("Testing Real-time Transcription")
    print("="*60 + "\n")

    # Initialize transcription
    transcription = RealtimeTranscription()

    # Set up callbacks
    def on_transcript(text, is_final):
        status = "[FINAL]" if is_final else "[INTERIM]"
        print(f"{status} {text}")

    def on_query(query):
        print(f"\n🔍 QUERY: {query}\n")

    def on_error(error):
        print(f"❌ ERROR: {error}")

    transcription.on_transcript = on_transcript
    transcription.on_query_detected = on_query
    transcription.on_error = on_error

    # Start transcription
    if not transcription.start_transcription():
        print("✗ Failed to start transcription")
        return

    # Set up audio capture
    audio = pyaudio.PyAudio()

    try:
        # Get default loopback device (system audio)
        loopback_info = audio.get_default_wasapi_loopback()

        print(f"Capturing from: {loopback_info['name']}")
        print("Speak or play audio. Press Ctrl+C to stop.\n")

        # Open audio stream
        stream = audio.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=16000,
            input=True,
            input_device_index=loopback_info['index'],
            frames_per_buffer=1024
        )

        # Capture and send audio
        while True:
            audio_data = stream.read(1024, exception_on_overflow=False)
            transcription.send_audio(audio_data)

    except KeyboardInterrupt:
        print("\n\n✓ Stopped by user")
    except Exception as e:
        print(f"\n✗ Error: {e}")
    finally:
        # Cleanup
        if 'stream' in locals():
            stream.stop_stream()
            stream.close()
        audio.terminate()
        transcription.stop_transcription()
        transcription.print_stats()


if __name__ == "__main__":
    test_transcription()
