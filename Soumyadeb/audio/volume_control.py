"""Windows Volume Control using pycaw (Python Core Audio Windows).

This module provides native Windows volume control without external tools like nircmd.
"""
import logging

logger = logging.getLogger(__name__)

# Try to import pycaw for native volume control
PYCAW_AVAILABLE = False
_speakers = None
_volume = None

try:
    from pycaw.pycaw import AudioUtilities
    _speakers = AudioUtilities.GetSpeakers()
    _volume = _speakers.EndpointVolume
    PYCAW_AVAILABLE = True
    logger.info("pycaw volume control initialized")
except ImportError:
    logger.warning("pycaw not installed. Install with: pip install pycaw")
except Exception as e:
    logger.warning(f"pycaw initialization failed: {e}")


def _get_volume():
    """Get the volume endpoint, refreshing if needed."""
    global _speakers, _volume
    if _volume is None and PYCAW_AVAILABLE:
        try:
            from pycaw.pycaw import AudioUtilities
            _speakers = AudioUtilities.GetSpeakers()
            _volume = _speakers.EndpointVolume
        except Exception as e:
            logger.error(f"Failed to get volume endpoint: {e}")
    return _volume


def get_volume() -> int:
    """Get current system volume as percentage (0-100)."""
    vol = _get_volume()
    if vol:
        try:
            return int(vol.GetMasterVolumeLevelScalar() * 100)
        except Exception as e:
            logger.error(f"Failed to get volume: {e}")
    return -1


def set_volume(level: int) -> bool:
    """Set system volume to a percentage (0-100)."""
    level = max(0, min(100, level))  # Clamp to 0-100
    vol = _get_volume()
    if vol:
        try:
            vol.SetMasterVolumeLevelScalar(level / 100.0, None)
            return True
        except Exception as e:
            logger.error(f"Failed to set volume: {e}")
    return False


def is_muted() -> bool:
    """Check if system is muted."""
    vol = _get_volume()
    if vol:
        try:
            return bool(vol.GetMute())
        except Exception as e:
            logger.error(f"Failed to get mute state: {e}")
    return False


def mute(muted: bool = True) -> bool:
    """Mute or unmute system volume."""
    vol = _get_volume()
    if vol:
        try:
            vol.SetMute(1 if muted else 0, None)
            return True
        except Exception as e:
            logger.error(f"Failed to set mute: {e}")
    return False


def change_volume(delta: int) -> bool:
    """Change volume by a delta (positive = louder, negative = quieter)."""
    current = get_volume()
    if current >= 0:
        new_level = max(0, min(100, current + delta))
        return set_volume(new_level)
    return False


# Convenience functions
def volume_up(amount: int = 10) -> str:
    """Increase volume."""
    if change_volume(amount):
        new_vol = get_volume()
        return f"Volume increased to {new_vol}%" if new_vol >= 0 else "Volume increased"
    return "Failed to increase volume"


def volume_down(amount: int = 10) -> str:
    """Decrease volume."""
    if change_volume(-amount):
        new_vol = get_volume()
        return f"Volume decreased to {new_vol}%" if new_vol >= 0 else "Volume decreased"
    return "Failed to decrease volume"


def volume_set(level: int) -> str:
    """Set volume to specific level."""
    if set_volume(level):
        return f"Volume set to {level}%"
    return f"Failed to set volume to {level}%"


def volume_mute() -> str:
    """Mute the volume."""
    if mute(True):
        return "Volume muted"
    return "Failed to mute volume"


def volume_unmute() -> str:
    """Unmute the volume."""
    if mute(False):
        return "Volume unmuted"
    return "Failed to unmute volume"


def volume_toggle_mute() -> str:
    """Toggle mute state."""
    if is_muted():
        return volume_unmute()
    else:
        return volume_mute()


if __name__ == "__main__":
    print(f"pycaw available: {PYCAW_AVAILABLE}")
    print(f"Current volume: {get_volume()}%")
    print(f"Is muted: {is_muted()}")
    print("\nTesting volume control...")
    print(volume_down(10))
    print(f"Volume after decrease: {get_volume()}%")
    print(volume_up(10))
    print(f"Volume after increase: {get_volume()}%")
