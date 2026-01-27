import sounddevice as sd
import soundfile as sf
import numpy as np
import noisereduce as nr
import logging
import os
from queue import Queue

SAMPLE_RATE = 16000
CHANNELS = 1
DTYPE = "float32"

audio_queue = Queue()
stream = None

# Ensure logs directory exists
os.makedirs("logs", exist_ok=True)

logging.basicConfig(
    filename="logs/audio.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

def audio_callback(indata, frames, time, status):
    if status:
        logging.warning(status)
    audio_queue.put(indata.copy())

def start_recording(device=None):
    global stream
    audio_queue.queue.clear()

    stream = sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        dtype=DTYPE,
        callback=audio_callback,
        device=device,
        blocksize=1024
    )
    stream.start()
    print("🎤 Recording started")

def stop_recording():
    stream.stop()
    stream.close()

    frames = []
    while not audio_queue.empty():
        frames.append(audio_queue.get())

    audio = np.concatenate(frames, axis=0).flatten()
    audio = nr.reduce_noise(y=audio, sr=SAMPLE_RATE)

    print("🛑 Recording stopped")
    return audio

def play_audio(audio):
    sd.play(audio, SAMPLE_RATE)
    sd.wait()

def save_audio(filename, audio):
    sf.write(filename, audio, SAMPLE_RATE)

def audio_level(audio):
    rms = np.sqrt(np.mean(audio ** 2))
    return round(rms * 100, 2)
