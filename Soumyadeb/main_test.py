from audio.audio_handler import (
    start_recording,
    stop_recording,
    play_audio,
    save_audio,
    audio_level
)

input("Press ENTER to start recording...")
start_recording()

input("Press ENTER to stop recording...")
audio = stop_recording()

print("Audio Level:", audio_level(audio))
play_audio(audio)
save_audio("test.wav", audio)
