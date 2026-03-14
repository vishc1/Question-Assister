"""
Stealth Overlay - macOS Compatible Version
Uses customtkinter only (no Windows API dependencies)
"""

import time
import customtkinter as ctk


class StealthOverlay:
    """
    A semi-transparent, frameless overlay window that's always on top.
    macOS version: no screen capture exclusion (Windows-only feature).
    """

    def __init__(self, width=500, height=700, transparency=0.92):
        self.width = width
        self.height = height
        self.transparency = transparency

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.root = ctk.CTk()
        self.root.title("Interview Assistant")

        self._configure_window()
        self._create_ui()

    def _configure_window(self):
        # Position top-right of screen
        self.root.update_idletasks()
        screen_w = self.root.winfo_screenwidth()
        x = screen_w - self.width - 20
        self.root.geometry(f"{self.width}x{self.height}+{x}+20")

        self.root.attributes('-alpha', self.transparency)
        self.root.attributes('-topmost', True)
        self.root.resizable(False, False)
        self.root.lift()
        self.root.focus_force()

    def _create_ui(self):
        main_frame = ctk.CTkFrame(self.root, fg_color="#1a1a1a", corner_radius=12)
        main_frame.pack(fill="both", expand=True, padx=4, pady=4)

        # Title bar
        self.title_bar = ctk.CTkFrame(main_frame, height=36, fg_color="#2b2b2b", corner_radius=8)
        self.title_bar.pack(fill="x", padx=6, pady=(6, 4))
        self.title_bar.pack_propagate(False)

        ctk.CTkLabel(
            self.title_bar,
            text="🎯 Interview Assistant",
            font=("Arial", 12, "bold"),
            text_color="#ffffff"
        ).pack(side="left", padx=12)

        ctk.CTkButton(
            self.title_bar,
            text="✕",
            width=28,
            height=24,
            fg_color="#ff4444",
            hover_color="#cc0000",
            corner_radius=6,
            command=self.close
        ).pack(side="right", padx=6, pady=4)

        # Status bar
        status_frame = ctk.CTkFrame(main_frame, fg_color="#2b2b2b", corner_radius=8)
        status_frame.pack(fill="x", padx=6, pady=(0, 4))

        self.status_label = ctk.CTkLabel(
            status_frame,
            text="Status: Initializing...",
            font=("Arial", 11),
            text_color="#aaaaaa"
        )
        self.status_label.pack(pady=8)

        # Mic indicator
        audio_frame = ctk.CTkFrame(main_frame, fg_color="#2b2b2b", corner_radius=8)
        audio_frame.pack(fill="x", padx=6, pady=(0, 4))

        mic_row = ctk.CTkFrame(audio_frame, fg_color="transparent")
        mic_row.pack(fill="x", padx=10, pady=6)

        ctk.CTkLabel(mic_row, text="🎤 Microphone:", font=("Arial", 10)).pack(side="left")

        self.mic_status = ctk.CTkLabel(
            mic_row, text="●", text_color="gray", font=("Arial", 18)
        )
        self.mic_status.pack(side="right")

        # Transcript area
        ctk.CTkLabel(
            main_frame,
            text="Live Output",
            font=("Arial", 11, "bold"),
            text_color="#888888"
        ).pack(pady=(4, 2))

        self.transcript_box = ctk.CTkTextbox(
            main_frame,
            font=("Menlo", 10),
            fg_color="#111111",
            text_color="#e0e0e0",
            corner_radius=8,
            wrap="word"
        )
        self.transcript_box.pack(fill="both", expand=True, padx=6, pady=(0, 6))

        print("✓ Overlay window created (macOS mode)")

    def _enable_dragging(self):
        def start_drag(event):
            self._drag_x = event.x
            self._drag_y = event.y

        def do_drag(event):
            x = self.root.winfo_x() + (event.x - self._drag_x)
            y = self.root.winfo_y() + (event.y - self._drag_y)
            self.root.geometry(f"+{x}+{y}")

        self.title_bar.bind("<Button-1>", start_drag)
        self.title_bar.bind("<B1-Motion>", do_drag)

    def update_status(self, message):
        self.root.after(0, lambda: self.status_label.configure(text=f"Status: {message}"))

    def update_mic_status(self, active=False):
        color = "#00ff00" if active else "gray"
        self.root.after(0, lambda: self.mic_status.configure(text_color=color))

    def update_speaker_status(self, active=False):
        pass

    def add_transcript(self, source, text):
        def _insert():
            self.transcript_box.configure(state="normal")
            self.transcript_box.insert("end", text + "\n")
            self.transcript_box.see("end")
            self.transcript_box.configure(state="disabled")
        self.root.after(0, _insert)

    def close(self):
        try:
            self.root.quit()
        except Exception:
            pass
        import os
        os._exit(0)

    def _keep_alive(self):
        """Prevent macOS beachball by keeping the event loop ticking."""
        self.root.after(50, self._keep_alive)

    def run(self):
        import subprocess
        subprocess.Popen(
            ["osascript", "-e", 'tell application "Python" to activate'],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self._keep_alive()
        self.root.mainloop()
