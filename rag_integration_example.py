#!/usr/bin/env python3
"""
RAG Integration Example
Shows how to integrate the RAG pipeline with the interview assistant
"""

import threading
import time
from pathlib import Path

from rag_pipeline import RAGPipeline
from stealth_overlay import StealthOverlay
from audio_capture import DualChannelAudioCapture


class InterviewAssistantWithRAG:
    """
    Enhanced interview assistant with RAG-powered context retrieval
    """

    def __init__(self):
        self.overlay = None
        self.audio_capture = None
        self.rag = None
        self.running = False

        # Simulated transcription buffer
        self.speaker_buffer = []
        self.mic_buffer = []

    def initialize_rag(self):
        """Initialize RAG pipeline"""
        print("\n" + "="*60)
        print("Initializing RAG Pipeline")
        print("="*60 + "\n")

        try:
            self.rag = RAGPipeline()

            # Try to load existing index
            if self.rag.load_vector_store():
                print("✓ RAG pipeline loaded successfully")
                return True
            else:
                print("\n⚠ No vector store found")
                print("\nTo enable RAG features:")
                print("  1. Add documents to the 'identity/' directory")
                print("  2. Run: python rag_pipeline.py build")
                print("  3. Restart the application")
                print("\nContinuing without RAG features...\n")
                self.rag = None
                return False

        except Exception as e:
            print(f"✗ Error initializing RAG: {e}")
            print("Continuing without RAG features...\n")
            self.rag = None
            return False

    def detect_question(self, text: str) -> bool:
        """
        Simple heuristic to detect if text is a question

        In a real implementation, you would use:
        - Speech-to-text with punctuation
        - NLP models for question detection
        - Rising intonation detection from audio
        """
        question_words = [
            'what', 'when', 'where', 'who', 'why', 'how',
            'can you', 'could you', 'would you', 'tell me',
            'describe', 'explain', 'walk me through'
        ]

        text_lower = text.lower()

        # Check for question marks
        if '?' in text:
            return True

        # Check for question words
        for word in question_words:
            if word in text_lower:
                return True

        return False

    def get_context_for_question(self, question: str):
        """
        Get relevant personal context for a question

        Args:
            question: The transcribed question from the interviewer
        """
        if not self.rag:
            return None

        try:
            # Get relevant context
            results = self.rag.get_personal_context(
                query=question,
                top_k=5,
                include_metadata=True
            )

            return results

        except Exception as e:
            print(f"Error retrieving context: {e}")
            return None

    def display_context_in_overlay(self, question: str, results: list):
        """Display retrieved context in the overlay"""
        if not self.overlay or not results:
            return

        # Add separator
        self.overlay.add_transcript("system", "\n" + "="*40)
        self.overlay.add_transcript("system", f"📚 RELEVANT CONTEXT FOR:")
        self.overlay.add_transcript("system", f"Q: {question[:100]}...")
        self.overlay.add_transcript("system", "="*40 + "\n")

        # Add context results
        for i, result in enumerate(results, 1):
            # Format score
            score = result['similarity_score']
            score_indicator = "🔥" if score < 0.5 else "✓" if score < 1.0 else "~"

            # Extract metadata
            source = result['metadata'].get('file_name', 'Unknown')
            content = result['content']

            # Display in overlay
            self.overlay.add_transcript(
                "context",
                f"\n[{i}] {score_indicator} From: {source}\n{content}\n"
            )

        self.overlay.add_transcript("system", "="*40 + "\n")

    def simulate_transcription(self):
        """
        Simulate transcription for demo purposes

        In real implementation, replace with actual speech-to-text:
        - OpenAI Whisper
        - Google Cloud Speech-to-Text
        - Azure Speech Services
        - AssemblyAI
        """
        demo_questions = [
            "Tell me about your experience with Python.",
            "Can you describe a challenging project you worked on?",
            "What are your strengths in software development?",
            "How do you handle technical disagreements in a team?",
            "Walk me through a recent machine learning project."
        ]

        time.sleep(5)  # Wait for initialization

        for i, question in enumerate(demo_questions):
            if not self.running:
                break

            # Simulate question detection
            print(f"\n[DEMO] Simulating interviewer question #{i+1}")
            self.overlay.add_transcript("speaker", question)

            # Detect if it's a question (would use actual detection in prod)
            if self.detect_question(question):
                print(f"[DEMO] Question detected, retrieving context...")

                # Get relevant context
                results = self.get_context_for_question(question)

                if results:
                    print(f"[DEMO] Found {len(results)} relevant contexts")
                    self.display_context_in_overlay(question, results)
                else:
                    print(f"[DEMO] No context found")

            # Wait before next question
            time.sleep(15)

    def run_demo(self):
        """Run demo with simulated questions"""
        print("\n" + "="*60)
        print("Interview Assistant with RAG - DEMO MODE")
        print("="*60 + "\n")

        # Initialize RAG
        rag_available = self.initialize_rag()

        if not rag_available:
            print("⚠ RAG not available, demo will run without context retrieval")
            input("\nPress Enter to continue or Ctrl+C to exit...")

        # Initialize overlay
        print("\nInitializing overlay window...")
        self.overlay = StealthOverlay()
        self.overlay.update_status("Demo Mode - RAG Integration")

        # Start simulation thread
        self.running = True
        sim_thread = threading.Thread(target=self.simulate_transcription, daemon=True)
        sim_thread.start()

        # Show instructions
        if rag_available:
            self.overlay.add_transcript(
                "system",
                "Demo Mode: RAG-Powered Interview Assistant\n"
                "Simulated questions will appear every 15 seconds.\n"
                "Context will be automatically retrieved and displayed.\n"
            )
        else:
            self.overlay.add_transcript(
                "system",
                "Demo Mode: Interview Assistant (RAG Disabled)\n"
                "To enable RAG:\n"
                "1. Add documents to identity/\n"
                "2. Run: python rag_pipeline.py build\n"
                "3. Restart this demo\n"
            )

        # Run overlay (blocking)
        try:
            self.overlay.run()
        except KeyboardInterrupt:
            pass
        finally:
            self.running = False
            print("\n✓ Demo stopped")

    def run_with_real_audio(self):
        """
        Run with real audio capture

        This is a template for integrating with actual audio
        You would need to add real speech-to-text here
        """
        print("\n" + "="*60)
        print("Interview Assistant with RAG - LIVE MODE")
        print("="*60 + "\n")

        # Initialize components
        rag_available = self.initialize_rag()

        print("\nInitializing audio capture...")
        self.audio_capture = DualChannelAudioCapture()

        print("\nInitializing overlay...")
        self.overlay = StealthOverlay()
        self.overlay.update_status("Live Mode - Ready")

        # Start audio capture
        audio_thread = threading.Thread(target=self._start_audio, daemon=True)
        audio_thread.start()

        # Note to user
        msg = "Live Mode: Real-time audio capture\n"
        if rag_available:
            msg += "RAG context retrieval enabled ✓\n"
        else:
            msg += "RAG not available (run: python rag_pipeline.py build)\n"

        msg += "\nNote: Add speech-to-text integration for transcription\n"
        msg += "See rag_integration_example.py for implementation details\n"

        self.overlay.add_transcript("system", msg)

        # Run overlay (blocking)
        try:
            self.overlay.run()
        except KeyboardInterrupt:
            pass
        finally:
            self.running = False
            if self.audio_capture:
                self.audio_capture.stop_capture()
            print("\n✓ Application stopped")

    def _start_audio(self):
        """Start audio capture in background"""
        time.sleep(1)

        if self.audio_capture.start_capture():
            if self.overlay:
                self.overlay.update_status("Audio capture active")
                self.overlay.update_mic_status(True)
                self.overlay.update_speaker_status(True)

                # Show placeholder message
                self.overlay.add_transcript(
                    "system",
                    "\nAudio capture active. Add speech-to-text to transcribe audio.\n"
                )
        else:
            if self.overlay:
                self.overlay.update_status("Audio capture failed")

        self.running = True


def main():
    """Main entry point"""
    import sys

    print("\nRAG Integration Example")
    print("\nOptions:")
    print("  1. demo  - Run demo with simulated questions (recommended)")
    print("  2. live  - Run with real audio capture (requires STT integration)")
    print()

    if len(sys.argv) > 1:
        mode = sys.argv[1].lower()
    else:
        mode = input("Select mode (demo/live) [demo]: ").strip().lower() or "demo"

    app = InterviewAssistantWithRAG()

    try:
        if mode == "demo":
            app.run_demo()
        elif mode == "live":
            app.run_with_real_audio()
        else:
            print(f"Unknown mode: {mode}")
            print("Use 'demo' or 'live'")

    except KeyboardInterrupt:
        print("\n\n✓ Stopped by user")
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
