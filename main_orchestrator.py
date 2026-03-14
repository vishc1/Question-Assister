#!/usr/bin/env python3
"""
Main Orchestrator
Links Stealth UI, Audio Capture, RAG Index, and Real-time Processing
Complete async implementation with proper error handling
"""

import asyncio
import time
import threading
import queue
from typing import Optional, List, Dict
from collections import deque
from datetime import datetime

from deepgram import (
    DeepgramClient,
    DeepgramClientOptions,
    LiveTranscriptionEvents,
    LiveOptions,
)

from stealth_overlay import StealthOverlay
from audio_capture import DualChannelAudioCapture
from rag_pipeline import RAGPipeline
from response_generator import ResponseGenerator
from config import Config


class TranscriptionBuffer:
    """
    Manages transcription buffer with silence detection
    Determines when interviewer has finished asking a question
    """

    def __init__(self, silence_threshold: float = 1.5):
        """
        Args:
            silence_threshold: Seconds of silence before query is complete
        """
        self.silence_threshold = silence_threshold
        self.buffer = deque(maxlen=50)  # Store recent transcripts
        self.accumulated_text = ""
        self.last_update_time = None
        self.is_speaking = False

    def add_transcript(self, text: str, is_final: bool = False):
        """
        Add transcript to buffer

        Args:
            text: Transcribed text
            is_final: Whether this is a final transcript
        """
        if not text.strip():
            return

        current_time = time.time()

        # Add to buffer
        self.buffer.append({
            "text": text,
            "is_final": is_final,
            "timestamp": current_time
        })

        # Update accumulated text for final transcripts
        if is_final:
            self.accumulated_text += " " + text.strip()
            self.is_speaking = True
            self.last_update_time = current_time

    def check_silence(self) -> Optional[str]:
        """
        Check if silence threshold has been reached

        Returns:
            Complete query if silence detected, None otherwise
        """
        if not self.is_speaking or not self.last_update_time:
            return None

        current_time = time.time()
        silence_duration = current_time - self.last_update_time

        if silence_duration >= self.silence_threshold:
            # Silence detected, return accumulated query
            query = self.accumulated_text.strip()

            # Reset buffer
            self.reset()

            # Validate query length
            if len(query) >= Config.MIN_QUERY_LENGTH:
                return query

        return None

    def reset(self):
        """Reset buffer state"""
        self.accumulated_text = ""
        self.is_speaking = False
        self.last_update_time = None

    def get_recent_transcripts(self, count: int = 5) -> List[str]:
        """Get recent transcripts for display"""
        recent = list(self.buffer)[-count:]
        return [t["text"] for t in recent if t["is_final"]]


class MainOrchestrator:
    """
    Main orchestrator linking all components:
    - Stealth UI
    - Audio Capture
    - Real-time Transcription (Deepgram)
    - RAG Pipeline
    - Response Generation (GPT-4o-mini)
    """

    def __init__(self):
        """Initialize the orchestrator"""
        # Components
        self.overlay: Optional[StealthOverlay] = None
        self.audio_capture: Optional[DualChannelAudioCapture] = None
        self.rag: Optional[RAGPipeline] = None
        self.response_generator: Optional[ResponseGenerator] = None

        # Deepgram
        self.deepgram_client: Optional[DeepgramClient] = None
        self.deepgram_connection = None

        # Buffer for transcription
        self.buffer = TranscriptionBuffer(silence_threshold=Config.SILENCE_THRESHOLD)

        # State
        self.is_running = False
        self.is_online = True
        self.last_error = None

        # Async loop and threads
        self.event_loop = None
        self.transcription_task = None
        self.silence_monitor_task = None
        self.audio_thread = None

        # Audio queue for async processing
        self.audio_queue = asyncio.Queue() if asyncio._get_running_loop() is None else None

        # Statistics
        self.stats = {
            "start_time": None,
            "transcripts_received": 0,
            "queries_detected": 0,
            "contexts_retrieved": 0,
            "responses_generated": 0,
            "errors": 0
        }

    def initialize(self) -> bool:
        """
        Initialize all components

        Returns:
            True if successful
        """
        try:
            print("\n" + "="*70)
            print(" "*20 + "INITIALIZING ORCHESTRATOR")
            print("="*70 + "\n")

            # Validate configuration
            if not self._validate_config():
                return False

            # Initialize Stealth Overlay
            print("Initializing Stealth Overlay...")
            self.overlay = StealthOverlay(width=500, height=700)
            self.overlay.update_status("Initializing...")
            print("✓ Overlay initialized")

            # Initialize Audio Capture
            print("\nInitializing Audio Capture...")
            self.audio_capture = DualChannelAudioCapture()

            if not self.audio_capture.find_devices():
                print("✗ Failed to find audio devices")
                return False

            print("✓ Audio capture initialized")

            # Initialize Deepgram
            print("\nInitializing Deepgram Client...")
            config = DeepgramClientOptions(
                options={"keepalive": "true"}
            )
            self.deepgram_client = DeepgramClient(
                Config.DEEPGRAM_API_KEY,
                config
            )
            print("✓ Deepgram client initialized")

            # Initialize RAG Pipeline
            print("\nInitializing RAG Pipeline...")
            self.rag = RAGPipeline()

            if not self.rag.load_vector_store():
                print("⚠ Warning: RAG vector store not found")
                print("  Context retrieval will be limited")
                print("  Run 'python rag_pipeline.py build' to enable full RAG")
                self.rag = None
            else:
                print("✓ RAG pipeline loaded")

            # Initialize Response Generator
            print("\nInitializing Response Generator...")
            self.response_generator = ResponseGenerator()
            print("✓ Response generator initialized")

            print("\n" + "="*70)
            print("✓ ALL COMPONENTS INITIALIZED")
            print("="*70 + "\n")

            return True

        except Exception as e:
            print(f"\n✗ Initialization error: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _validate_config(self) -> bool:
        """Validate configuration"""
        issues = []

        if not Config.OPENAI_API_KEY:
            issues.append("OPENAI_API_KEY not set")

        if not Config.DEEPGRAM_API_KEY:
            issues.append("DEEPGRAM_API_KEY not set")

        if issues:
            print("\n✗ Configuration issues:")
            for issue in issues:
                print(f"  - {issue}")
            print("\nPlease set API keys in .env file")
            return False

        return True

    def start(self):
        """Start the orchestrator (blocking)"""
        if self.is_running:
            print("⚠ Orchestrator already running")
            return

        # Show welcome message
        self._show_welcome()

        # Start components in background thread
        start_thread = threading.Thread(
            target=self._start_background_systems,
            daemon=True
        )
        start_thread.start()

        # Run overlay (blocking)
        try:
            self.overlay.run()
        except KeyboardInterrupt:
            pass
        finally:
            self.stop()

    def _show_welcome(self):
        """Show welcome message in overlay"""
        welcome = f"""╔══════════════════════════════════════════╗
║      LIVE INTERVIEW ASSISTANT v2.0       ║
╚══════════════════════════════════════════╝

🎯 Status: Initializing...

Components:
  • Stealth Overlay        [✓]
  • Audio Capture          [...]
  • Deepgram Transcription [...]
  • RAG Context Retrieval  [...]
  • GPT-4o-mini Responses  [...]

⏱️  Starting background systems...
"""
        self.overlay.add_transcript("system", welcome)

    def _start_background_systems(self):
        """Start all background systems"""
        time.sleep(1)  # Let GUI initialize

        try:
            # Create new event loop for this thread
            self.event_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.event_loop)

            # Create audio queue
            self.audio_queue = asyncio.Queue()

            # Start audio capture
            self.overlay.update_status("Starting audio capture...")
            if not self.audio_capture.start_capture():
                self._show_error("Failed to start audio capture")
                return

            self.overlay.add_transcript("system", "\n✓ Audio capture started")

            # Start audio forwarding thread
            self.audio_thread = threading.Thread(
                target=self._audio_forwarding_loop,
                daemon=True
            )
            self.audio_thread.start()

            # Run async tasks
            self.is_running = True
            self.stats["start_time"] = time.time()

            self.event_loop.run_until_complete(self._run_async_tasks())

        except Exception as e:
            print(f"✗ Error in background systems: {e}")
            import traceback
            traceback.print_exc()
            self._show_error(f"Background system error: {e}")

    async def _run_async_tasks(self):
        """Run async tasks"""
        try:
            # Create tasks
            self.transcription_task = asyncio.create_task(
                self._transcription_loop()
            )

            self.silence_monitor_task = asyncio.create_task(
                self._silence_monitor_loop()
            )

            # Update overlay
            self.overlay.update_status("Active - Listening")
            self.overlay.update_speaker_status(True)
            self.overlay.add_transcript(
                "system",
                "\n✓ Real-time transcription active\n"
                "✓ Silence detection enabled\n"
                "✓ Ready for interview!\n" + "="*40 + "\n"
            )

            # Wait for tasks
            await asyncio.gather(
                self.transcription_task,
                self.silence_monitor_task
            )

        except Exception as e:
            print(f"✗ Error in async tasks: {e}")
            import traceback
            traceback.print_exc()

    async def _transcription_loop(self):
        """
        Main transcription loop using Deepgram WebSocket
        Streams audio and receives transcriptions
        """
        try:
            # Configure Deepgram options
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
            self.deepgram_connection = self.deepgram_client.listen.asynclive.v("1")

            # Set up event handlers
            self.deepgram_connection.on(
                LiveTranscriptionEvents.Transcript,
                self._on_transcript
            )

            self.deepgram_connection.on(
                LiveTranscriptionEvents.Error,
                self._on_deepgram_error
            )

            # Start connection
            if not await self.deepgram_connection.start(options):
                self._show_error("Failed to start Deepgram connection")
                return

            self.overlay.add_transcript("system", "✓ Deepgram connected\n")

            # Stream audio to Deepgram
            while self.is_running:
                try:
                    # Get audio from queue
                    audio_data = await asyncio.wait_for(
                        self.audio_queue.get(),
                        timeout=0.1
                    )

                    # Send to Deepgram
                    await self.deepgram_connection.send(audio_data)

                except asyncio.TimeoutError:
                    # No audio data, continue
                    await asyncio.sleep(0.01)

                except Exception as e:
                    print(f"Error streaming audio: {e}")
                    break

            # Close connection
            await self.deepgram_connection.finish()

        except Exception as e:
            print(f"✗ Transcription loop error: {e}")
            import traceback
            traceback.print_exc()
            self._show_error(f"Transcription error: {e}")

    def _on_transcript(self, result, **kwargs):
        """
        Handle transcript from Deepgram

        Args:
            result: Deepgram transcript result
        """
        try:
            sentence = result.channel.alternatives[0].transcript

            if not sentence:
                return

            is_final = result.is_final

            # Update statistics
            self.stats["transcripts_received"] += 1

            # Add to buffer
            self.buffer.add_transcript(sentence, is_final)

            # Show in overlay (only final transcripts to avoid clutter)
            if is_final:
                self.overlay.add_transcript("speaker", f"[INTERVIEWER] {sentence}")

        except Exception as e:
            print(f"Error processing transcript: {e}")
            self.stats["errors"] += 1

    def _on_deepgram_error(self, error, **kwargs):
        """Handle Deepgram errors"""
        print(f"✗ Deepgram error: {error}")
        self.stats["errors"] += 1
        self._show_error(f"Transcription error: {error}")

    async def _silence_monitor_loop(self):
        """
        Monitor for silence and process complete queries
        Runs continuously checking buffer
        """
        try:
            while self.is_running:
                # Check for silence
                query = self.buffer.check_silence()

                if query:
                    # Query detected!
                    self.stats["queries_detected"] += 1

                    # Show in overlay
                    self.overlay.add_transcript(
                        "system",
                        f"\n{'='*40}\n🔍 QUESTION DETECTED\n{'='*40}"
                    )

                    self.overlay.add_transcript("speaker", f"Q: {query}\n")

                    # Process query in background
                    asyncio.create_task(self._process_query(query))

                # Sleep briefly
                await asyncio.sleep(0.1)

        except Exception as e:
            print(f"✗ Silence monitor error: {e}")
            import traceback
            traceback.print_exc()

    async def _process_query(self, query: str):
        """
        Process a complete query:
        1. Retrieve context from RAG
        2. Generate response with GPT-4o-mini
        3. Display in overlay

        Args:
            query: The complete question from interviewer
        """
        try:
            # Update status
            self.overlay.update_status("Retrieving context...")

            # Step 1: Get relevant context from RAG
            context = await self._retrieve_context(query)

            # Step 2: Generate response
            self.overlay.update_status("Generating response...")

            response = await self._generate_response(query, context)

            # Step 3: Display response
            if response:
                self._display_response(response)
            else:
                self._show_error("Failed to generate response")

            # Reset status
            self.overlay.update_status("Active - Listening")

        except Exception as e:
            print(f"✗ Query processing error: {e}")
            import traceback
            traceback.print_exc()
            self._show_error(f"Processing error: {e}")

    async def _retrieve_context(self, query: str) -> List[Dict]:
        """
        Retrieve context from RAG pipeline

        Args:
            query: The question to search for

        Returns:
            List of relevant context snippets
        """
        try:
            if not self.rag:
                self.overlay.add_transcript(
                    "system",
                    "⚠️  RAG not available, generating without context\n"
                )
                return []

            # Run in executor to avoid blocking
            loop = asyncio.get_event_loop()
            context = await loop.run_in_executor(
                None,
                self.rag.get_personal_context,
                query,
                Config.TOP_K_RESULTS,
                True
            )

            if context:
                self.stats["contexts_retrieved"] += 1

                # Show context snippets
                self.overlay.add_transcript(
                    "system",
                    f"📚 Retrieved {len(context)} relevant items:\n"
                )

                for i, item in enumerate(context[:3], 1):  # Show top 3
                    snippet = item['content'][:120] + "..." if len(item['content']) > 120 else item['content']
                    source = item['metadata'].get('file_name', 'Unknown')
                    self.overlay.add_transcript(
                        "context",
                        f"[{i}] {source}: {snippet}\n"
                    )

                self.overlay.add_transcript("system", "")

            else:
                self.overlay.add_transcript(
                    "system",
                    "⚠️  No relevant context found\n"
                )

            return context or []

        except Exception as e:
            print(f"✗ Context retrieval error: {e}")
            self.stats["errors"] += 1
            return []

    async def _generate_response(self, query: str, context: List[Dict]) -> Optional[List[str]]:
        """
        Generate response using GPT-4o-mini

        Args:
            query: The question
            context: Retrieved context from RAG

        Returns:
            List of bullet point suggestions
        """
        try:
            # Run in executor to avoid blocking
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                self.response_generator.generate_response,
                query,
                context
            )

            if response:
                self.stats["responses_generated"] += 1

            return response

        except Exception as e:
            print(f"✗ Response generation error: {e}")
            self.stats["errors"] += 1
            self._show_error(f"GPT error: {e}")
            return None

    def _display_response(self, responses: List[str]):
        """
        Display response suggestions in overlay

        Args:
            responses: List of bullet points
        """
        self.overlay.add_transcript(
            "system",
            f"\n{'='*40}\n💡 SUGGESTED RESPONSES\n{'='*40}\n"
        )

        for i, response in enumerate(responses, 1):
            self.overlay.add_transcript("mic", f"{i}. {response}\n")

        self.overlay.add_transcript("system", "="*40 + "\n\n")

    def _show_error(self, error_msg: str):
        """
        Show error in overlay

        Args:
            error_msg: Error message
        """
        self.last_error = error_msg
        self.stats["errors"] += 1

        # Check if offline
        if "connection" in error_msg.lower() or "network" in error_msg.lower():
            self.is_online = False
            self.overlay.update_status("⚠️ Offline")
            self.overlay.add_transcript("system", f"\n⚠️ OFFLINE: {error_msg}\n")
        else:
            self.overlay.add_transcript("system", f"\n❌ Error: {error_msg}\n")

    def _audio_forwarding_loop(self):
        """
        Forward audio from capture to async queue
        Runs in separate thread
        """
        print("✓ Audio forwarding started")

        while self.is_running:
            try:
                # Get speaker audio (system audio/interviewer)
                audio_data = self.audio_capture.get_speaker_data(timeout=0.1)

                if audio_data and self.audio_queue:
                    # Put in async queue (thread-safe)
                    asyncio.run_coroutine_threadsafe(
                        self.audio_queue.put(audio_data),
                        self.event_loop
                    )

            except Exception as e:
                print(f"Audio forwarding error: {e}")
                time.sleep(0.1)

        print("✓ Audio forwarding stopped")

    def stop(self):
        """Stop the orchestrator"""
        if not self.is_running:
            return

        print("\n🧹 Stopping orchestrator...")

        self.is_running = False

        # Stop audio capture
        if self.audio_capture:
            self.audio_capture.stop_capture()

        # Cancel async tasks
        if self.transcription_task:
            self.transcription_task.cancel()

        if self.silence_monitor_task:
            self.silence_monitor_task.cancel()

        # Stop event loop
        if self.event_loop and self.event_loop.is_running():
            self.event_loop.stop()

        # Show statistics
        self._print_statistics()

        print("✓ Orchestrator stopped")

    def _print_statistics(self):
        """Print session statistics"""
        print("\n" + "="*60)
        print("Session Statistics")
        print("="*60)

        if self.stats["start_time"]:
            duration = time.time() - self.stats["start_time"]
            print(f"Duration: {duration:.1f} seconds")

        print(f"\nTranscripts received: {self.stats['transcripts_received']}")
        print(f"Queries detected: {self.stats['queries_detected']}")
        print(f"Contexts retrieved: {self.stats['contexts_retrieved']}")
        print(f"Responses generated: {self.stats['responses_generated']}")
        print(f"Errors: {self.stats['errors']}")

        print("="*60 + "\n")


def main():
    """Main entry point"""
    print("\n" + "="*70)
    print(" "*15 + "MAIN ORCHESTRATOR - LIVE ASSISTANT")
    print("="*70)

    # Create orchestrator
    orchestrator = MainOrchestrator()

    # Initialize
    if not orchestrator.initialize():
        print("\n✗ Initialization failed")
        input("\nPress Enter to exit...")
        return

    # Start (blocking)
    try:
        print("\nStarting orchestrator...\n")
        orchestrator.start()

    except KeyboardInterrupt:
        print("\n\n✓ Stopped by user")

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()

    finally:
        orchestrator.stop()


if __name__ == "__main__":
    main()
