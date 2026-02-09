"""
VoxMind Voice Access Settings
==============================
Inspired by Windows Voice Access and Google Voice Access (Android).

This module provides configurable settings for voice control behavior,
making VoxMind more accessible and customizable.

Features from Windows Voice Access:
- Wake word activation
- Sleep/Wake commands
- Number overlay mode (for clicking by number)
- Grid selection mode
- Dictation vs Command mode

Features from Google Voice Access (Android):
- Verbosity levels (all feedback, errors only, none)
- Require verbs setting (e.g., "Tap Gmail" vs just "Gmail")
- Timeout after no speech
- Physical activation key
- Label contrast settings
- Screen wake behavior

References:
- Windows: https://support.microsoft.com/en-us/topic/voice-access-command-list-dac0f091-87ce-454d-8d57-bef38d3d8563
- Android: https://support.google.com/accessibility/android/answer/6151843
"""

import json
import os
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Optional, List, Dict, Any, Callable
from pathlib import Path


class VoiceAccessMode(Enum):
    """Operating modes for voice control (inspired by Windows Voice Access)."""
    DEFAULT = "default"      # Both commands and dictation
    COMMANDS = "commands"    # Commands only mode
    DICTATION = "dictation"  # Dictation only mode
    SLEEPING = "sleeping"    # Voice access is paused


class VerbosityLevel(Enum):
    """Feedback verbosity levels (inspired by Google Voice Access)."""
    ALL = "all"              # All feedback (confirmations, errors, suggestions)
    ERRORS_ONLY = "errors"   # Only speak on errors
    NONE = "none"            # No audio feedback (visual only)


class ScreenWakeBehavior(Enum):
    """Listening behavior on app start (inspired by Google Voice Access)."""
    ALWAYS_LISTEN = "always"           # Always start listening
    LISTEN_UNLESS_PAUSED = "unless_paused"  # Listen unless user said "stop"
    NEVER_LISTEN = "never"             # Only listen when explicitly activated


class LabelContrast(Enum):
    """Label visibility contrast (inspired by Google Voice Access)."""
    LIGHTEST = "lightest"
    LIGHT = "light"
    MEDIUM = "medium"
    DARK = "dark"


class NumberLabelMode(Enum):
    """Which items get number labels (inspired by Google Voice Access)."""
    ALL_ITEMS = "all"                # All clickable items
    UNLABELED_ONLY = "unlabeled"     # Only items without text labels


@dataclass
class VoiceAccessSettings:
    """
    Complete voice access settings for VoxMind.
    
    Combines best features from:
    - Windows Voice Access
    - Google Voice Access (Android)
    """
    
    # === Wake Word & Activation (Both platforms) ===
    wake_word: str = "vox"
    wake_word_enabled: bool = True
    wake_word_alternatives: List[str] = field(default_factory=lambda: [
        "hey vox", "ok vox", "voxmind", "hey voxmind"
    ])
    
    # === Activation Settings (Google Voice Access) ===
    activation_key: Optional[str] = None  # Physical key to toggle (e.g., "F12")
    screen_wake_behavior: ScreenWakeBehavior = ScreenWakeBehavior.LISTEN_UNLESS_PAUSED
    
    # === Operating Mode (Windows Voice Access) ===
    current_mode: VoiceAccessMode = VoiceAccessMode.DEFAULT
    
    # === Command Preferences (Google Voice Access) ===
    require_verbs: bool = False  # If True: "Open Gmail" required, not just "Gmail"
    timeout_after_no_speech_seconds: int = 30  # 0 = never timeout
    cancel_on_touch: bool = False  # Stop listening on mouse/keyboard input
    
    # === Feedback Settings (Google Voice Access) ===
    verbosity: VerbosityLevel = VerbosityLevel.ALL
    play_feedback_sounds: bool = True
    
    # === Voice Settings ===
    voice_rate: int = 180
    voice_volume: float = 0.9
    voice_style: str = "normal"  # normal, calm, lively, emphatic, whisper
    
    # === Visual Settings (Google Voice Access) ===
    show_number_labels: bool = False
    number_label_mode: NumberLabelMode = NumberLabelMode.ALL_ITEMS
    label_contrast: LabelContrast = LabelContrast.MEDIUM
    show_borders: bool = False  # Show borders around interactive elements
    show_grid: bool = False
    grid_size: int = 3  # 3x3, 4x4, etc.
    
    # === Disambiguation (Both platforms) ===
    disambiguation_enabled: bool = True  # Ask "Which one?" when ambiguous
    
    # === Language Settings ===
    language: str = "en-US"
    offline_mode: bool = True  # Use offline speech recognition when possible
    
    # === Advanced Settings ===
    recognize_common_icons: bool = True  # Label common icons (back, menu, etc.)
    active_during_calls: bool = False  # Keep voice access on during calls
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert settings to dictionary for JSON serialization."""
        data = {}
        for key, value in asdict(self).items():
            if isinstance(value, Enum):
                data[key] = value.value
            else:
                data[key] = value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'VoiceAccessSettings':
        """Create settings from dictionary."""
        # Convert enum strings back to enums
        if 'current_mode' in data and isinstance(data['current_mode'], str):
            data['current_mode'] = VoiceAccessMode(data['current_mode'])
        if 'verbosity' in data and isinstance(data['verbosity'], str):
            data['verbosity'] = VerbosityLevel(data['verbosity'])
        if 'screen_wake_behavior' in data and isinstance(data['screen_wake_behavior'], str):
            data['screen_wake_behavior'] = ScreenWakeBehavior(data['screen_wake_behavior'])
        if 'label_contrast' in data and isinstance(data['label_contrast'], str):
            data['label_contrast'] = LabelContrast(data['label_contrast'])
        if 'number_label_mode' in data and isinstance(data['number_label_mode'], str):
            data['number_label_mode'] = NumberLabelMode(data['number_label_mode'])
        
        # Filter out unknown keys
        valid_keys = {f.name for f in cls.__dataclass_fields__.values()}
        filtered_data = {k: v for k, v in data.items() if k in valid_keys}
        
        return cls(**filtered_data)


class VoiceAccessSettingsManager:
    """
    Manages VoxMind voice access settings with persistence.
    """
    
    DEFAULT_CONFIG_PATH = Path(__file__).parent.parent / "voice_access_config.json"
    
    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or self.DEFAULT_CONFIG_PATH
        self._settings: Optional[VoiceAccessSettings] = None
        self._listeners: List[Callable] = []
    
    @property
    def settings(self) -> VoiceAccessSettings:
        """Get current settings, loading from file if needed."""
        if self._settings is None:
            self._settings = self.load()
        return self._settings
    
    def load(self) -> VoiceAccessSettings:
        """Load settings from file."""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    data = json.load(f)
                return VoiceAccessSettings.from_dict(data)
            except Exception as e:
                print(f"[VoiceAccess] Error loading settings: {e}")
        return VoiceAccessSettings()
    
    def save(self) -> bool:
        """Save current settings to file."""
        try:
            with open(self.config_path, 'w') as f:
                json.dump(self.settings.to_dict(), f, indent=2)
            return True
        except Exception as e:
            print(f"[VoiceAccess] Error saving settings: {e}")
            return False
    
    def update(self, **kwargs) -> None:
        """Update settings and notify listeners."""
        for key, value in kwargs.items():
            if hasattr(self.settings, key):
                setattr(self._settings, key, value)
        self.save()
        self._notify_listeners()
    
    def add_listener(self, callback: Callable) -> None:
        """Add a listener for settings changes."""
        self._listeners.append(callback)
    
    def _notify_listeners(self) -> None:
        """Notify all listeners of settings change."""
        for listener in self._listeners:
            try:
                listener(self.settings)
            except Exception as e:
                print(f"[VoiceAccess] Listener error: {e}")
    
    # === Mode Control (Windows Voice Access style) ===
    
    def wake_up(self) -> None:
        """Wake up from sleeping mode."""
        if self.settings.current_mode == VoiceAccessMode.SLEEPING:
            self.update(current_mode=VoiceAccessMode.DEFAULT)
    
    def go_to_sleep(self) -> None:
        """Put voice access to sleep."""
        self.update(current_mode=VoiceAccessMode.SLEEPING)
    
    def switch_to_commands_mode(self) -> None:
        """Switch to commands-only mode."""
        self.update(current_mode=VoiceAccessMode.COMMANDS)
    
    def switch_to_dictation_mode(self) -> None:
        """Switch to dictation-only mode."""
        self.update(current_mode=VoiceAccessMode.DICTATION)
    
    def switch_to_default_mode(self) -> None:
        """Switch to default (command + dictation) mode."""
        self.update(current_mode=VoiceAccessMode.DEFAULT)
    
    # === Quick Toggles ===
    
    def toggle_number_labels(self) -> bool:
        """Toggle number overlay display. Returns new state."""
        new_state = not self.settings.show_number_labels
        self.update(show_number_labels=new_state)
        return new_state
    
    def toggle_grid(self) -> bool:
        """Toggle grid overlay display. Returns new state."""
        new_state = not self.settings.show_grid
        self.update(show_grid=new_state)
        return new_state
    
    def set_verbosity(self, level: VerbosityLevel) -> None:
        """Set feedback verbosity level."""
        self.update(verbosity=level)
    
    def toggle_require_verbs(self) -> bool:
        """Toggle require verbs setting. Returns new state."""
        new_state = not self.settings.require_verbs
        self.update(require_verbs=new_state)
        return new_state


# === Voice Access Commands ===
# These are the voice commands that control voice access itself

VOICE_ACCESS_COMMANDS = {
    # Wake/Sleep (Windows Voice Access)
    "wake_up": [
        "voice access wake up",
        "wake up",
        "unmute",
        "start listening",
        "i'm back"
    ],
    "sleep": [
        "voice access sleep",
        "go to sleep",
        "mute",
        "stop listening",
        "be quiet"
    ],
    
    # Mode Switching (Windows Voice Access)
    "commands_mode": [
        "commands mode",
        "switch to command mode",
        "command only"
    ],
    "dictation_mode": [
        "dictation mode",
        "switch to dictation mode",
        "typing mode"
    ],
    "default_mode": [
        "default mode",
        "switch to default mode",
        "normal mode"
    ],
    
    # Number/Grid Overlays (Both platforms)
    "show_numbers": [
        "show numbers",
        "show numbers everywhere",
        "show labels"
    ],
    "hide_numbers": [
        "hide numbers",
        "cancel",
        "hide labels"
    ],
    "show_grid": [
        "show grid",
        "show grid everywhere"
    ],
    "hide_grid": [
        "hide grid",
        "cancel grid"
    ],
    
    # Help (Both platforms)
    "show_commands": [
        "what can i say",
        "show all commands",
        "show command list",
        "show commands",
        "help"
    ],
    "open_tutorial": [
        "open tutorial",
        "start tutorial",
        "how do i use this"
    ],
    
    # Settings
    "open_settings": [
        "open voice access settings",
        "voice settings",
        "open settings"
    ]
}


def get_command_for_phrase(phrase: str) -> Optional[str]:
    """
    Check if a phrase matches a voice access control command.
    
    Returns command name if matched, None otherwise.
    """
    phrase_lower = phrase.lower().strip()
    
    for command, phrases in VOICE_ACCESS_COMMANDS.items():
        for p in phrases:
            if phrase_lower == p or phrase_lower.startswith(p):
                return command
    
    return None


# Singleton instance
_settings_manager: Optional[VoiceAccessSettingsManager] = None


def get_settings_manager() -> VoiceAccessSettingsManager:
    """Get the global settings manager instance."""
    global _settings_manager
    if _settings_manager is None:
        _settings_manager = VoiceAccessSettingsManager()
    return _settings_manager


def get_settings() -> VoiceAccessSettings:
    """Get current voice access settings."""
    return get_settings_manager().settings
