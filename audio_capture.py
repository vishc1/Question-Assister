import pyaudiowpatch as pyaudio
import threading
import queue
import time
import wave


class DualChannelAudioCapture:
    """
    Captures audio from two separate sources simultaneously:
    - Channel A: Physical microphone (user's voice)
    - Channel B: System audio output (interviewer's voice via loopback)
    """

    def __init__(self, sample_rate=16000, chunk_size=1024):
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size

        self.audio = pyaudio.PyAudio()

        # Audio queues for each channel
        self.mic_queue = queue.Queue()
        self.speaker_queue = queue.Queue()

        # Device info
        self.mic_device_index = None
        self.speaker_device_index = None

        # Streams
        self.mic_stream = None
        self.speaker_stream = None

        # Control flags
        self.is_capturing = False
        self.threads = []

        # Callbacks
        self.on_mic_data = None
        self.on_speaker_data = None

    def list_devices(self):
        """List all available audio devices"""
        print("\n=== Available Audio Devices ===\n")

        for i in range(self.audio.get_device_count()):
            info = self.audio.get_device_info_by_index(i)
            print(f"Device {i}: {info['name']}")
            print(f"  Max Input Channels: {info['maxInputChannels']}")
            print(f"  Max Output Channels: {info['maxOutputChannels']}")
            print(f"  Default Sample Rate: {info['defaultSampleRate']}")
            print()

    def find_devices(self):
        """Automatically find the microphone and loopback devices"""
        # Find default microphone
        try:
            default_mic = self.audio.get_default_input_device_info()
            self.mic_device_index = default_mic['index']
            print(f"✓ Found microphone: {default_mic['name']}")
        except Exception as e:
            print(f"⚠ Error finding microphone: {e}")

        # Find WASAPI loopback device (system audio)
        try:
            # Look for loopback device
            wasapi_info = self.audio.get_loopback_device_info_generator()
            for loopback in wasapi_info:
                if loopback['name'].find('Loopback') != -1 or loopback.get('isLoopbackDevice', False):
                    self.speaker_device_index = loopback['index']
                    print(f"✓ Found loopback device: {loopback['name']}")
                    break

            # If not found by name, try to find default speakers and use loopback
            if self.speaker_device_index is None:
                try:
                    default_speakers = self.audio.get_default_wasapi_loopback()
                    self.speaker_device_index = default_speakers['index']
                    print(f"✓ Found default loopback: {default_speakers['name']}")
                except:
                    pass

        except Exception as e:
            print(f"⚠ Error finding loopback device: {e}")

        return self.mic_device_index is not None and self.speaker_device_index is not None

    def _mic_callback(self, in_data, frame_count, time_info, status):
        """Callback for microphone audio data"""
        if status:
            print(f"Mic status: {status}")

        self.mic_queue.put(in_data)

        if self.on_mic_data:
            self.on_mic_data(in_data)

        return (in_data, pyaudio.paContinue)

    def _speaker_callback(self, in_data, frame_count, time_info, status):
        """Callback for system audio (loopback) data"""
        if status:
            print(f"Speaker status: {status}")

        self.speaker_queue.put(in_data)

        if self.on_speaker_data:
            self.on_speaker_data(in_data)

        return (in_data, pyaudio.paContinue)

    def start_capture(self):
        """Start capturing audio from both channels"""
        if not self.find_devices():
            print("❌ Could not find required audio devices")
            return False

        self.is_capturing = True

        try:
            # Open microphone stream
            if self.mic_device_index is not None:
                mic_info = self.audio.get_device_info_by_index(self.mic_device_index)
                print(f"\n▶ Opening microphone stream: {mic_info['name']}")

                self.mic_stream = self.audio.open(
                    format=pyaudio.paInt16,
                    channels=1,
                    rate=self.sample_rate,
                    input=True,
                    input_device_index=self.mic_device_index,
                    frames_per_buffer=self.chunk_size,
                    stream_callback=self._mic_callback
                )
                self.mic_stream.start_stream()
                print("✓ Microphone stream active")

            # Open loopback stream (system audio)
            if self.speaker_device_index is not None:
                speaker_info = self.audio.get_device_info_by_index(self.speaker_device_index)
                print(f"\n▶ Opening loopback stream: {speaker_info['name']}")

                # Get the optimal channel count for loopback
                channels = min(2, int(speaker_info['maxInputChannels']))

                self.speaker_stream = self.audio.open(
                    format=pyaudio.paInt16,
                    channels=channels,
                    rate=int(speaker_info['defaultSampleRate']),
                    input=True,
                    input_device_index=self.speaker_device_index,
                    frames_per_buffer=self.chunk_size,
                    stream_callback=self._speaker_callback
                )
                self.speaker_stream.start_stream()
                print("✓ Loopback stream active")

            print("\n✓ Dual-channel audio capture started successfully\n")
            return True

        except Exception as e:
            print(f"❌ Error starting audio capture: {e}")
            self.stop_capture()
            return False

    def stop_capture(self):
        """Stop capturing audio from both channels"""
        self.is_capturing = False

        if self.mic_stream:
            try:
                self.mic_stream.stop_stream()
                self.mic_stream.close()
            except:
                pass

        if self.speaker_stream:
            try:
                self.speaker_stream.stop_stream()
                self.speaker_stream.close()
            except:
                pass

        print("✓ Audio capture stopped")

    def get_mic_data(self, timeout=0.1):
        """Get the latest microphone audio data from queue"""
        try:
            return self.mic_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def get_speaker_data(self, timeout=0.1):
        """Get the latest speaker audio data from queue"""
        try:
            return self.speaker_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def monitor_mode(self, duration=None):
        """
        Monitor mode: Print live transcription placeholders to verify audio capture
        """
        if not self.is_capturing:
            if not self.start_capture():
                return

        print("\n" + "="*60)
        print("MONITOR MODE - Live Audio Capture Verification")
        print("="*60)
        print("\nListening for audio from both channels...")
        print("Press Ctrl+C to stop\n")

        start_time = time.time()
        mic_samples = 0
        speaker_samples = 0

        try:
            while True:
                if duration and (time.time() - start_time) > duration:
                    break

                # Check microphone data
                mic_data = self.get_mic_data(timeout=0.1)
                if mic_data:
                    mic_samples += 1
                    # Simulate transcription placeholder
                    print(f"[MIC] 🎤 Sample #{mic_samples} | Size: {len(mic_data)} bytes | [Transcribing...]")

                # Check speaker data
                speaker_data = self.get_speaker_data(timeout=0.1)
                if speaker_data:
                    speaker_samples += 1
                    # Simulate transcription placeholder
                    print(f"[SPK] 🔊 Sample #{speaker_samples} | Size: {len(speaker_data)} bytes | [Transcribing...]")

                time.sleep(0.05)

        except KeyboardInterrupt:
            print("\n\n✓ Monitor mode stopped by user")

        finally:
            print(f"\n--- Statistics ---")
            print(f"Microphone samples captured: {mic_samples}")
            print(f"Speaker samples captured: {speaker_samples}")
            print(f"Duration: {time.time() - start_time:.2f} seconds")

    def save_to_wav(self, filename, audio_data, channels=1):
        """Save captured audio data to WAV file"""
        try:
            wf = wave.open(filename, 'wb')
            wf.setnchannels(channels)
            wf.setsampwidth(self.audio.get_sample_size(pyaudio.paInt16))
            wf.setframerate(self.sample_rate)
            wf.writeframes(b''.join(audio_data))
            wf.close()
            print(f"✓ Saved audio to {filename}")
        except Exception as e:
            print(f"❌ Error saving audio: {e}")

    def cleanup(self):
        """Clean up resources"""
        self.stop_capture()
        self.audio.terminate()
