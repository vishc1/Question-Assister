"""
Real-time Processing Loop
Coordinates transcription, RAG retrieval, and response generation
"""

import time
import threading
from typing import Optional, Callable
from collections import deque

from realtime_transcription import RealtimeTranscription
from rag_pipeline import RAGPipeline
from response_generator import ResponseGenerator
from audio_capture import DualChannelAudioCapture
from config import Config


class RealtimeProcessor:
    """
    Coordinates the complete real-time processing pipeline:
    1. Captures system audio (interviewer speech)
    2. Transcribes with Deepgram
    3. Detects silence and extracts queries
    4. Retrieves personal context with RAG
    5. Generates response suggestions with GPT-4o-mini
    """

    def __init__(self):
        """Initialize the real-time processor"""
        # Components
        self.audio_capture = None
        self.transcription = None
        self.rag = None
        self.response_generator = None

        # State
        self.is_running = False
        self.audio_thread = None

        # Transcript buffer
        self.transcript_buffer = deque(maxlen=100)

        # Callbacks
        self.on_transcript_update = None  # (text, is_final) -> None
        self.on_query_detected = None  # (query) -> None
        self.on_context_retrieved = None  # (query, context) -> None
        self.on_response_generated = None  # (query, responses) -> None
        self.on_error = None  # (error_msg) -> None
        self.on_status_change = None  # (status_msg) -> None

        # Statistics
        self.stats = {
            "transcripts": 0,
            "queries": 0,
            "contexts_retrieved": 0,
            "responses_generated": 0,
            "errors": 0,
            "start_time": None
        }

    def initialize(self) -> bool:
        """
        Initialize all components

        Returns:
            True if successful, False otherwise
        """
        try:
            self._update_status("Initializing components...")

            # Initialize audio capture
            self.audio_capture = DualChannelAudioCapture()
            print("✓ Audio capture initialized")

            # Initialize transcription
            self.transcription = RealtimeTranscription()

            # Set up transcription callbacks
            self.transcription.on_transcript = self._handle_transcript
            self.transcription.on_query_detected = self._handle_query
            self.transcription.on_error = self._handle_transcription_error

            if not self.transcription.initialize():
                self._update_status("Failed to initialize transcription")
                return False

            print("✓ Transcription initialized")

            # Initialize RAG pipeline
            self.rag = RAGPipeline()

            if not self.rag.load_vector_store():
                print("⚠ Warning: RAG vector store not found")
                print("  Context retrieval will be disabled")
                print("  Run 'python rag_pipeline.py build' to enable")
                self.rag = None
            else:
                print("✓ RAG pipeline loaded")

            # Initialize response generator
            self.response_generator = ResponseGenerator()
            print("✓ Response generator initialized")

            self._update_status("All components ready")
            return True

        except Exception as e:
            error_msg = f"Initialization error: {e}"
            print(f"✗ {error_msg}")
            self._handle_error(error_msg)
            return False

    def start(self) -> bool:
        """
        Start the real-time processing loop

        Returns:
            True if started successfully
        """
        if self.is_running:
            print("⚠ Processor already running")
            return False

        if not self.transcription or not self.response_generator:
            print("✗ Components not initialized. Call initialize() first")
            return False

        try:
            self._update_status("Starting real-time processing...")

            # Start audio capture
            if not self.audio_capture.find_devices():
                print("✗ Audio devices not found")
                return False

            if not self.audio_capture.start_capture():
                print("✗ Failed to start audio capture")
                return False

            print("✓ Audio capture started")

            # Start transcription
            if not self.transcription.start_transcription():
                print("✗ Failed to start transcription")
                self.audio_capture.stop_capture()
                return False

            print("✓ Transcription started")

            # Start audio forwarding thread
            self.is_running = True
            self.stats["start_time"] = time.time()

            self.audio_thread = threading.Thread(
                target=self._audio_forwarding_loop,
                daemon=True
            )
            self.audio_thread.start()

            self._update_status("Real-time processing active")
            print("\n✓ Real-time processor started successfully")
            return True

        except Exception as e:
            error_msg = f"Start error: {e}"
            print(f"✗ {error_msg}")
            self._handle_error(error_msg)
            return False

    def stop(self):
        """Stop the real-time processing loop"""
        if not self.is_running:
            return

        self._update_status("Stopping...")

        self.is_running = False

        # Stop components
        if self.transcription:
            self.transcription.stop_transcription()

        if self.audio_capture:
            self.audio_capture.stop_capture()

        # Wait for thread
        if self.audio_thread:
            self.audio_thread.join(timeout=2)

        self._update_status("Stopped")
        print("✓ Real-time processor stopped")

    def _audio_forwarding_loop(self):
        """Forward system audio to transcription"""
        print("✓ Audio forwarding loop started")

        while self.is_running:
            try:
                # Get audio from system (speaker/loopback)
                audio_data = self.audio_capture.get_speaker_data(timeout=0.1)

                if audio_data:
                    # Send to transcription
                    self.transcription.send_audio(audio_data)

            except Exception as e:
                print(f"Audio forwarding error: {e}")
                time.sleep(0.1)

        print("✓ Audio forwarding loop stopped")

    def _handle_transcript(self, text: str, is_final: bool):
        """Handle transcript update from Deepgram"""
        self.stats["transcripts"] += 1

        # Add to buffer
        self.transcript_buffer.append({
            "text": text,
            "is_final": is_final,
            "timestamp": time.time()
        })

        # Call callback
        if self.on_transcript_update:
            self.on_transcript_update(text, is_final)

    def _handle_query(self, query: str):
        """Handle query detected by silence detector"""
        self.stats["queries"] += 1

        print(f"\n{'='*60}")
        print(f"QUERY DETECTED: {query}")
        print(f"{'='*60}\n")

        # Call callback
        if self.on_query_detected:
            self.on_query_detected(query)

        # Process query in background thread
        processing_thread = threading.Thread(
            target=self._process_query,
            args=(query,),
            daemon=True
        )
        processing_thread.start()

    def _process_query(self, query: str):
        """Process query through RAG and response generation"""
        try:
            # Step 1: Retrieve context from RAG
            context = None

            if self.rag:
                self._update_status(f"Retrieving context...")

                context = self.rag.get_personal_context(
                    query=query,
                    top_k=Config.TOP_K_RESULTS,
                    include_metadata=True
                )

                if context:
                    self.stats["contexts_retrieved"] += 1
                    print(f"✓ Retrieved {len(context)} context items")

                    # Call callback
                    if self.on_context_retrieved:
                        self.on_context_retrieved(query, context)
                else:
                    print("⚠ No context found")
                    context = []
            else:
                print("⚠ RAG not available, generating response without context")
                context = []

            # Step 2: Generate response suggestions
            self._update_status(f"Generating response suggestions...")

            responses = self.response_generator.generate_response(
                query=query,
                context=context
            )

            if responses:
                self.stats["responses_generated"] += 1
                print(f"✓ Generated {len(responses)} response suggestions")

                # Call callback
                if self.on_response_generated:
                    self.on_response_generated(query, responses)
            else:
                print("✗ Failed to generate responses")
                self._handle_error("Response generation failed")

            self._update_status("Ready")

        except Exception as e:
            error_msg = f"Query processing error: {e}"
            print(f"✗ {error_msg}")
            self._handle_error(error_msg)

    def _handle_transcription_error(self, error: str):
        """Handle transcription errors"""
        self.stats["errors"] += 1
        self._handle_error(f"Transcription error: {error}")

    def _handle_error(self, error_msg: str):
        """Handle errors"""
        if self.on_error:
            self.on_error(error_msg)

    def _update_status(self, status: str):
        """Update status"""
        if self.on_status_change:
            self.on_status_change(status)

    def get_stats(self) -> dict:
        """Get processing statistics"""
        stats = self.stats.copy()

        # Add component stats
        if self.transcription:
            stats["transcription"] = self.transcription.get_stats()

        if self.response_generator:
            stats["response_generator"] = self.response_generator.get_stats()

        # Calculate uptime
        if stats["start_time"]:
            stats["uptime"] = time.time() - stats["start_time"]

        return stats

    def print_stats(self):
        """Print detailed statistics"""
        print("\n" + "="*60)
        print("Real-time Processor Statistics")
        print("="*60)

        if self.stats["start_time"]:
            uptime = time.time() - self.stats["start_time"]
            print(f"Uptime: {uptime:.1f} seconds")

        print(f"\nTranscripts received: {self.stats['transcripts']}")
        print(f"Queries detected: {self.stats['queries']}")
        print(f"Contexts retrieved: {self.stats['contexts_retrieved']}")
        print(f"Responses generated: {self.stats['responses_generated']}")
        print(f"Errors: {self.stats['errors']}")

        # Component stats
        if self.transcription:
            print("\nTranscription:")
            t_stats = self.transcription.get_stats()
            print(f"  Transcripts: {t_stats['transcripts_received']}")
            print(f"  Queries: {t_stats['queries_detected']}")
            print(f"  Errors: {t_stats['errors']}")

        if self.response_generator:
            print("\nResponse Generator:")
            r_stats = self.response_generator.get_stats()
            print(f"  Requests: {r_stats['requests']}")
            print(f"  Successes: {r_stats['successes']}")
            print(f"  Tokens: {r_stats['total_tokens']}")

        print("="*60 + "\n")


def test_processor():
    """Test the real-time processor"""
    print("\n" + "="*70)
    print(" "*20 + "REAL-TIME PROCESSOR TEST")
    print("="*70)

    # Initialize processor
    processor = RealtimeProcessor()

    # Set up callbacks
    def on_transcript(text, is_final):
        status = "[FINAL]" if is_final else "[INTERIM]"
        print(f"{status} {text}")

    def on_query(query):
        print(f"\n🔍 QUERY: {query}\n")

    def on_context(query, context):
        print(f"📚 Retrieved {len(context)} context items")

    def on_response(query, responses):
        print(f"\n💡 SUGGESTED RESPONSES:")
        for i, resp in enumerate(responses, 1):
            print(f"  {i}. {resp}")
        print()

    def on_error(error):
        print(f"❌ ERROR: {error}")

    def on_status(status):
        print(f"ℹ️  Status: {status}")

    processor.on_transcript_update = on_transcript
    processor.on_query_detected = on_query
    processor.on_context_retrieved = on_context
    processor.on_response_generated = on_response
    processor.on_error = on_error
    processor.on_status_change = on_status

    # Initialize
    if not processor.initialize():
        print("✗ Initialization failed")
        return

    # Start
    if not processor.start():
        print("✗ Failed to start")
        return

    print("\n" + "="*60)
    print("Listening for system audio...")
    print("Play audio or speak through applications")
    print("Press Ctrl+C to stop")
    print("="*60 + "\n")

    try:
        # Run until interrupted
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n\n✓ Stopped by user")

    finally:
        processor.stop()
        processor.print_stats()


if __name__ == "__main__":
    test_processor()
