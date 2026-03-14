#!/usr/bin/env python3
"""
Live Interview Assistant
Complete real-time interview assistance with:
- Stealth overlay window
- Deepgram live transcription
- RAG-powered context retrieval
- GPT-4o-mini response generation
"""

import sys
import threading
import time
from datetime import datetime

from stealth_overlay import StealthOverlay
from realtime_processor import RealtimeProcessor
from config import Config


class LiveInterviewAssistant:
    """
    Complete live interview assistant application
    Integrates all components with the stealth overlay
    """

    def __init__(self):
        """Initialize the live interview assistant"""
        self.overlay = None
        self.processor = None
        self.running = False

    def run(self):
        """Run the complete application"""
        print("\n" + "="*70)
        print(" "*15 + "LIVE INTERVIEW ASSISTANT")
        print("="*70)

        # Validate configuration
        if not self._validate_config():
            return

        # Initialize overlay
        print("\nInitializing stealth overlay...")
        self.overlay = StealthOverlay(width=500, height=700)
        self.overlay.update_status("Initializing...")

        # Show welcome message
        self._show_welcome_message()

        # Initialize processor in background
        init_thread = threading.Thread(target=self._initialize_processor, daemon=True)
        init_thread.start()

        # Run overlay (blocking)
        try:
            self.overlay.run()
        except KeyboardInterrupt:
            pass
        finally:
            self.cleanup()

    def _validate_config(self) -> bool:
        """Validate that required API keys are set"""
        print("\nValidating configuration...")

        issues = []

        if not Config.OPENAI_API_KEY:
            issues.append("OPENAI_API_KEY not set")

        if not Config.DEEPGRAM_API_KEY:
            issues.append("DEEPGRAM_API_KEY not set")

        if issues:
            print("\n✗ Configuration issues found:")
            for issue in issues:
                print(f"  - {issue}")

            print("\nPlease set the required API keys in .env file")
            print("Example:")
            print("  OPENAI_API_KEY=sk-...")
            print("  DEEPGRAM_API_KEY=...")

            input("\nPress Enter to exit...")
            return False

        print("✓ Configuration valid")
        return True

    def _show_welcome_message(self):
        """Show welcome message in overlay"""
        welcome = """╔════════════════════════════════════════╗
║   LIVE INTERVIEW ASSISTANT READY    ║
╚════════════════════════════════════════╝

🎯 Features:
  • Real-time transcription (Deepgram)
  • Silence detection (1.5s threshold)
  • Context retrieval (RAG)
  • Response suggestions (GPT-4o-mini)

📊 Status: Initializing...

⏱️  Waiting for interviewer to speak...
"""
        self.overlay.add_transcript("system", welcome)

    def _initialize_processor(self):
        """Initialize the real-time processor"""
        time.sleep(1)  # Let GUI initialize

        self.overlay.update_status("Initializing processor...")

        # Create processor
        self.processor = RealtimeProcessor()

        # Set up callbacks
        self.processor.on_transcript_update = self._handle_transcript
        self.processor.on_query_detected = self._handle_query
        self.processor.on_context_retrieved = self._handle_context
        self.processor.on_response_generated = self._handle_response
        self.processor.on_error = self._handle_error
        self.processor.on_status_change = self._handle_status

        # Initialize
        if not self.processor.initialize():
            self.overlay.update_status("Initialization failed")
            self.overlay.add_transcript("system", "\n❌ Failed to initialize processor")
            return

        # Start
        if not self.processor.start():
            self.overlay.update_status("Failed to start")
            self.overlay.add_transcript("system", "\n❌ Failed to start processor")
            return

        # Success
        self.running = True
        self.overlay.update_status("Active - Listening")
        self.overlay.update_speaker_status(True)

        self.overlay.add_transcript(
            "system",
            "\n✅ System ready! Start your interview.\n" + "="*40 + "\n"
        )

    def _handle_transcript(self, text: str, is_final: bool):
        """Handle transcript update"""
        if not text.strip():
            return

        # Show interim transcripts in lighter color
        prefix = "[INTERVIEWER]" if is_final else "[...]"

        # Only show final transcripts to avoid clutter
        if is_final:
            self.overlay.add_transcript("speaker", f"{prefix} {text}")

    def _handle_query(self, query: str):
        """Handle query detection"""
        self.overlay.add_transcript(
            "system",
            f"\n{'='*40}\n🔍 QUESTION DETECTED\n{'='*40}"
        )

        self.overlay.add_transcript("speaker", f"Q: {query}\n")

        self.overlay.update_status("Processing question...")

    def _handle_context(self, query: str, context: list):
        """Handle context retrieval"""
        if not context:
            self.overlay.add_transcript("system", "⚠️  No relevant context found\n")
            return

        self.overlay.add_transcript(
            "system",
            f"📚 Retrieved {len(context)} relevant items from your history:\n"
        )

        # Show context snippets
        for i, item in enumerate(context[:3], 1):  # Show top 3
            content = item['content'][:150] + "..." if len(item['content']) > 150 else item['content']
            source = item['metadata'].get('file_name', 'Unknown')

            self.overlay.add_transcript(
                "context",
                f"[{i}] {source}: {content}\n"
            )

        self.overlay.add_transcript("system", "")

    def _handle_response(self, query: str, responses: list):
        """Handle response generation"""
        if not responses:
            self.overlay.add_transcript("system", "❌ Failed to generate responses\n")
            return

        # Display suggestions prominently
        self.overlay.add_transcript(
            "system",
            f"\n{'='*40}\n💡 SUGGESTED RESPONSES\n{'='*40}\n"
        )

        for i, response in enumerate(responses, 1):
            self.overlay.add_transcript("mic", f"{i}. {response}\n")

        self.overlay.add_transcript("system", "="*40 + "\n\n")

        self.overlay.update_status("Ready - Listening")

    def _handle_error(self, error: str):
        """Handle errors"""
        self.overlay.add_transcript("system", f"❌ Error: {error}\n")

    def _handle_status(self, status: str):
        """Handle status updates"""
        # Update overlay status
        self.overlay.update_status(status)

    def cleanup(self):
        """Cleanup on exit"""
        print("\n🧹 Cleaning up...")

        self.running = False

        if self.processor:
            self.processor.stop()

            # Show statistics
            print("\nSession Statistics:")
            stats = self.processor.get_stats()

            if stats.get('start_time'):
                uptime = time.time() - stats['start_time']
                print(f"  Session duration: {uptime:.1f} seconds")

            print(f"  Queries processed: {stats.get('queries', 0)}")
            print(f"  Responses generated: {stats.get('responses_generated', 0)}")
            print(f"  Errors: {stats.get('errors', 0)}")

        print("✓ Cleanup complete")


def check_prerequisites():
    """Check that all prerequisites are met"""
    print("\n" + "="*60)
    print("Checking Prerequisites")
    print("="*60 + "\n")

    all_good = True

    # Check Python packages
    packages = [
        "customtkinter",
        "deepgram",
        "openai",
        "langchain",
        "faiss"
    ]

    for package in packages:
        try:
            __import__(package)
            print(f"✓ {package}")
        except ImportError:
            print(f"✗ {package} - NOT INSTALLED")
            all_good = False

    # Check API keys
    print("\nAPI Keys:")
    print(f"  OpenAI: {'✓ Set' if Config.OPENAI_API_KEY else '✗ Not Set'}")
    print(f"  Deepgram: {'✓ Set' if Config.DEEPGRAM_API_KEY else '✗ Not Set'}")

    if not Config.OPENAI_API_KEY or not Config.DEEPGRAM_API_KEY:
        all_good = False

    # Check RAG index
    print("\nRAG Index:")
    from pathlib import Path
    index_path = Config.VECTOR_STORE_PATH / "faiss_index"

    if index_path.exists():
        print(f"  ✓ Found at {index_path}")
    else:
        print(f"  ⚠️  Not found (run 'python rag_pipeline.py build')")
        print(f"     App will work but without context retrieval")

    print("\n" + "="*60)

    if all_good:
        print("✓ All prerequisites met!")
    else:
        print("⚠️  Some prerequisites missing")
        print("\nTo fix:")
        print("  1. Install: pip install -r requirements.txt")
        print("  2. Set API keys in .env file")
        print("  3. Build RAG index: python rag_pipeline.py build")

    print("="*60 + "\n")

    return all_good


def show_usage():
    """Show usage information"""
    print("\n" + "="*60)
    print("Live Interview Assistant")
    print("="*60)
    print("\nUsage:")
    print("  python live_interview_assistant.py        - Run the application")
    print("  python live_interview_assistant.py check  - Check prerequisites")
    print("  python live_interview_assistant.py help   - Show this help")
    print("\nFeatures:")
    print("  • Real-time transcription of interviewer speech")
    print("  • Automatic silence detection (1.5s)")
    print("  • Personal context retrieval from your documents")
    print("  • AI-generated response suggestions")
    print("  • Stealth overlay (invisible to screen capture)")
    print("\nSetup:")
    print("  1. Set API keys in .env:")
    print("     OPENAI_API_KEY=sk-...")
    print("     DEEPGRAM_API_KEY=...")
    print("  2. Add documents to identity/ folder")
    print("  3. Build RAG index: python rag_pipeline.py build")
    print("  4. Run: python live_interview_assistant.py")
    print("\nDuring Interview:")
    print("  • The overlay shows live transcription")
    print("  • When interviewer stops (1.5s silence):")
    print("    - Question is detected")
    print("    - Context is retrieved from your docs")
    print("    - Response suggestions are displayed")
    print("  • Use suggestions to formulate your answer")
    print("\nTips:")
    print("  • Position overlay on second monitor")
    print("  • Test before actual interview")
    print("  • Ensure system audio is being captured")
    print("="*60 + "\n")


def main():
    """Main entry point"""
    # Parse arguments
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()

        if command == "check":
            check_prerequisites()
            return

        elif command == "help":
            show_usage()
            return

        else:
            print(f"Unknown command: {command}")
            show_usage()
            return

    # Run application
    try:
        app = LiveInterviewAssistant()
        app.run()

    except KeyboardInterrupt:
        print("\n\n✓ Stopped by user")

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
