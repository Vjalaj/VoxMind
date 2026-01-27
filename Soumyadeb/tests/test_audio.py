import numpy as np
from audio.audio_handler import audio_level

def test_silence_audio_level():
    silence = np.zeros(16000)
    assert audio_level(silence) == 0

def test_audio_level_difference():
    noisy = np.random.randn(16000)
    clean = noisy * 0.1
    assert audio_level(clean) < audio_level(noisy)

def test_sample_length():
    audio = np.random.randn(16000)
    assert len(audio) == 16000
