import sounddevice as sd
import soundfile as sf
import numpy as np
from queue import Queue

# =========================
# Audio Configuration
# =========================
SAMPLE_RATE = 16000       # Good for speech recognition
CHANNELS = 1              # Mono audio
DTYPE = 'float32'

audio_queue = Queue()
recording = False


# =========================
# Audio Callback
# =========================
def _audio_callback(indata, frames, time, status):
    if status:
        print("Audio status:", status)
    audio_queue.put(indata.copy())


# =========================
# Start Recording
# =========================
def start_recording():
    global recording, stream
    recording = True
    audio_queue.queue.clear()

    stream = sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        dtype=DTYPE,
        callback=_audio_callback
    )
    stream.start()
    print("🎤 Recording started...")


# =========================
# Stop Recording
# =========================
def stop_recording():
    global recording
    recording = False
    stream.stop()
    stream.close()

    audio_data = []
    while not audio_queue.empty():
        audio_data.append(audio_queue.get())

    audio_np = np.concatenate(audio_data, axis=0)
    print("🛑 Recording stopped")

    return audio_np


# =========================
# Play Audio
# =========================
def play_audio(audio_data):
    print("🔊 Playing audio...")
    sd.play(audio_data, SAMPLE_RATE)
    sd.wait()


# =========================
# Save Audio (Optional)
# =========================
def save_audio(filename, audio_data):
    sf.write(filename, audio_data, SAMPLE_RATE)
    print(f"💾 Audio saved as {filename}")


# =========================
# Test Script
# =========================
if __name__ == "__main__":
    input("Press ENTER to start recording...")
    start_recording()

    input("Press ENTER to stop recording...")
    audio = stop_recording()

    play_audio(audio)
    save_audio("test.wav", audio)

