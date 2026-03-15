"""
Web Overlay — Browser-based UI via SSE.
Drop-in replacement for StealthOverlay; displays in Chrome.
"""

import time
import threading
import webbrowser


class WebOverlay:

    def __init__(self, **kwargs):
        pass

    def _broadcast(self, event_type, data):
        from upload_server import broadcast_event
        broadcast_event(event_type, data)

    def update_status(self, message):
        self._broadcast("status", message)

    def update_mic_status(self, active=False):
        self._broadcast("mic", active)

    def update_speaker_status(self, active=False):
        pass

    def show_question(self, text):
        self._broadcast("question", text)

    def show_answer_bullet(self, text):
        self._broadcast("answer", text)

    def show_live(self, text):
        self._broadcast("live", text)

    def add_transcript(self, source, text):
        """Backward-compatible fallback."""
        t = text.strip()
        if not t:
            return
        if "⏳ [live]" in t:
            self._broadcast("live", t.replace("⏳ [live]", "").strip())
        elif source == "mic" and t.startswith("•"):
            self._broadcast("answer", t[1:].strip())
        elif source == "system" and not t.startswith("─") and not t.startswith("=") and len(t) > 3:
            self._broadcast("system", t)

    def run(self):
        def _open():
            time.sleep(2.0)
            try:
                b = webbrowser.get("google-chrome")
                b.open("http://localhost:5001")
            except Exception:
                webbrowser.open_new_tab("http://localhost:5001")

        threading.Thread(target=_open, daemon=True).start()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
