#!/usr/bin/env python3
"""
Main Orchestrator - macOS Version
Uses OpenAI Whisper for transcription (no Deepgram needed)
"""

import asyncio
import time
import threading
import io
import wave
from collections import deque
from typing import Optional, List, Dict

import pyaudio
import openai

from stealth_overlay import StealthOverlay
from rag_pipeline import RAGPipeline
from response_generator import ResponseGenerator
from config import Config


CHUNK = 1024
RATE = 16000
SILENCE_RMS_THRESHOLD = 100   # audio level to consider as silence
SILENCE_SECONDS = 1.5         # seconds of silence before processing
MIN_SPEECH_SECONDS = 0.5      # minimum audio length to bother transcribing
INTERIM_INTERVAL = 3.0        # seconds between live interim transcriptions


def rms(data: bytes) -> float:
    import struct
    count = len(data) // 2
    if count == 0:
        return 0
    shorts = struct.unpack(f"{count}h", data)
    return (sum(s * s for s in shorts) / count) ** 0.5


class MainOrchestratorMacOS:

    def __init__(self):
        self.overlay: Optional[StealthOverlay] = None
        self.audio: Optional[pyaudio.PyAudio] = None
        self.audio_stream = None
        self.rag: Optional[RAGPipeline] = None
        self.response_generator: Optional[ResponseGenerator] = None
        self.is_running = False

        self.openai_client = None

        # Audio buffering
        self.speech_frames: List[bytes] = []
        self.silence_start: Optional[float] = None
        self.is_speaking = False
        self.last_interim_time: Optional[float] = None
        self.interim_running = False

        self.loop: Optional[asyncio.AbstractEventLoop] = None

        self.stats = {
            "transcripts": 0,
            "queries": 0,
            "responses": 0,
            "errors": 0,
        }

    def initialize(self) -> bool:
        try:
            print("\n" + "=" * 60)
            print("  INITIALIZING (macOS / Whisper mode)")
            print("=" * 60)

            if not Config.OPENAI_API_KEY:
                print("✗ OPENAI_API_KEY not set in .env")
                return False

            self.openai_client = openai.OpenAI(api_key=Config.OPENAI_API_KEY)

            print("Initializing overlay...")
            self.overlay = StealthOverlay(width=500, height=700)
            self.overlay.update_status("Initializing...")
            print("✓ Overlay ready")

            print("Initializing microphone...")
            self.audio = pyaudio.PyAudio()
            print("✓ Audio ready")

            print("Loading RAG pipeline...")
            self.rag = RAGPipeline()
            if not self.rag.load_vector_store():
                print("⚠ RAG not available — run Build Index first")
                self.rag = None
            else:
                print("✓ RAG loaded")

            print("Initializing response generator...")
            self.response_generator = ResponseGenerator()
            print("✓ Response generator ready")

            print("\n✓ INITIALIZATION COMPLETE\n")
            return True

        except Exception as e:
            print(f"✗ Init error: {e}")
            import traceback; traceback.print_exc()
            return False

    def start(self):
        self.overlay.add_transcript("system",
            "╔══════════════════════════════════╗\n"
            "║   Interview Assistant  (Whisper) ║\n"
            "╚══════════════════════════════════╝\n\n"
            "🎤 Speak — pausing triggers analysis\n"
            + "=" * 40 + "\n"
        )

        t = threading.Thread(target=self._run_capture_loop, daemon=True)
        t.start()

        try:
            self.overlay.run()
        except KeyboardInterrupt:
            pass
        finally:
            self.stop()

    def _run_capture_loop(self):
        time.sleep(0.5)
        try:
            device_info = self.audio.get_default_input_device_info()
            print(f"Microphone: {device_info['name']}")

            self.audio_stream = self.audio.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=RATE,
                input=True,
                frames_per_buffer=CHUNK
            )

            self.is_running = True
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)

            self.overlay.update_status("Listening...")
            self.overlay.update_mic_status(True)
            self.overlay.add_transcript("system", "✓ Microphone active\n🎤 Start speaking...\n")

            self.loop.run_until_complete(self._audio_loop())

        except Exception as e:
            print(f"✗ Capture error: {e}")
            import traceback; traceback.print_exc()
            self.overlay.add_transcript("system", f"\n❌ Error: {e}\n")

    async def _audio_loop(self):
        while self.is_running:
            try:
                data = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self.audio_stream.read(CHUNK, exception_on_overflow=False)
                )

                level = rms(data)
                if int(time.time() * 2) % 4 == 0 and level > 10:
                    print(f"RMS: {level:.0f}", end="\r")

                if level > SILENCE_RMS_THRESHOLD:
                    # Speech detected
                    self.speech_frames.append(data)
                    self.silence_start = None
                    if not self.is_speaking:
                        self.is_speaking = True
                        self.last_interim_time = time.time()
                        self.overlay.update_status("🎤 Speaking...")
                    else:
                        # Trigger interim transcription every INTERIM_INTERVAL seconds
                        if (not self.interim_running and
                                self.last_interim_time and
                                time.time() - self.last_interim_time >= INTERIM_INTERVAL and
                                len(self.speech_frames) > 0):
                            self.last_interim_time = time.time()
                            asyncio.create_task(self._process_interim(self.speech_frames[:]))
                else:
                    # Silence
                    if self.is_speaking:
                        if self.silence_start is None:
                            self.silence_start = time.time()
                        elif time.time() - self.silence_start >= SILENCE_SECONDS:
                            # Enough silence — process
                            frames = self.speech_frames[:]
                            self.speech_frames = []
                            self.silence_start = None
                            self.is_speaking = False
                            self.overlay.update_status("Processing...")

                            duration = len(frames) * CHUNK / RATE
                            if duration >= MIN_SPEECH_SECONDS:
                                asyncio.create_task(self._process_audio(frames))
                            else:
                                self.overlay.update_status("Listening...")

            except Exception as e:
                print(f"Audio loop error: {e}")
                await asyncio.sleep(0.1)

    async def _process_audio(self, frames: List[bytes]):
        try:
            # Convert frames to WAV bytes
            buf = io.BytesIO()
            with wave.open(buf, 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(RATE)
                wf.writeframes(b''.join(frames))
            wav_bytes = buf.getvalue()

            # Transcribe with Whisper
            self.overlay.update_status("Transcribing...")
            loop = asyncio.get_event_loop()

            transcript = await loop.run_in_executor(
                None, self._whisper_transcribe, wav_bytes
            )

            if not transcript or len(transcript.strip()) < Config.MIN_QUERY_LENGTH:
                self.overlay.update_status("Listening...")
                return

            self.stats["transcripts"] += 1
            self.overlay.add_transcript("mic", f"[YOU] {transcript}\n")

            # Get context + generate response
            self.stats["queries"] += 1
            self.overlay.add_transcript("system",
                f"\n{'=' * 38}\n🔍 QUESTION DETECTED\n{'=' * 38}\n"
                f"Q: {transcript}\n"
            )

            context = await loop.run_in_executor(
                None, self._get_context, transcript
            )

            self.overlay.update_status("Generating response...")
            response = await loop.run_in_executor(
                None, self.response_generator.generate_response, transcript, context
            )

            if response:
                self.stats["responses"] += 1
                self.overlay.add_transcript("system",
                    f"\n{'=' * 38}\n💡 SUGGESTED RESPONSES\n{'=' * 38}\n"
                )
                for i, r in enumerate(response, 1):
                    self.overlay.add_transcript("mic", f"{i}. {r}\n")
                self.overlay.add_transcript("system", "=" * 38 + "\n\n")

            self.overlay.update_status("Listening...")

        except Exception as e:
            print(f"✗ Process error: {e}")
            import traceback; traceback.print_exc()
            self.overlay.add_transcript("system", f"\n❌ Error: {e}\n")
            self.overlay.update_status("Listening...")

    async def _process_interim(self, frames: List[bytes]):
        self.interim_running = True
        try:
            buf = io.BytesIO()
            with wave.open(buf, 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(RATE)
                wf.writeframes(b''.join(frames))
            wav_bytes = buf.getvalue()

            loop = asyncio.get_event_loop()
            transcript = await loop.run_in_executor(None, self._whisper_transcribe, wav_bytes)

            if transcript and len(transcript.strip()) >= Config.MIN_QUERY_LENGTH:
                self.overlay.add_transcript("live", f"⏳ [live] {transcript}\n")
        except Exception as e:
            print(f"Interim error: {e}")
        finally:
            self.interim_running = False

    def _whisper_transcribe(self, wav_bytes: bytes) -> str:
        try:
            audio_file = io.BytesIO(wav_bytes)
            audio_file.name = "audio.wav"
            result = self.openai_client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language="en"
            )
            text = result.text.strip()
            print(f"Transcript: {text}")
            return text
        except Exception as e:
            print(f"✗ Whisper error: {e}")
            return ""

    def _get_context(self, query: str) -> List[Dict]:
        if not self.rag:
            return []
        try:
            ctx = self.rag.get_personal_context(query, Config.TOP_K_RESULTS, True)
            if ctx:
                self.overlay.add_transcript("system", f"📚 {len(ctx)} context items found\n")
            return ctx or []
        except Exception as e:
            print(f"✗ Context error: {e}")
            return []

    def stop(self):
        self.is_running = False
        if self.audio_stream:
            try:
                self.audio_stream.stop_stream()
                self.audio_stream.close()
            except:
                pass
        if self.audio:
            try:
                self.audio.terminate()
            except:
                pass
        print(f"\nSession: {self.stats['transcripts']} transcripts, "
              f"{self.stats['queries']} queries, "
              f"{self.stats['responses']} responses")


def main():
    print("\n" + "=" * 60)
    print("  Interview Assistant — macOS (Whisper)")
    print("=" * 60)

    orchestrator = MainOrchestratorMacOS()

    if not orchestrator.initialize():
        print("✗ Init failed")
        return

    try:
        orchestrator.start()
    except KeyboardInterrupt:
        print("\n✓ Stopped")
    finally:
        orchestrator.stop()


if __name__ == "__main__":
    main()
