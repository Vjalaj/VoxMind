"""
VoxMind Cross-Platform Abstraction Layer
==========================================
Provides unified APIs that work across Windows, macOS, and Linux.

Usage:
    from core.platform import get_platform
    
    platform = get_platform()
    platform.window.focus("Chrome")
    platform.audio.set_volume(50)
    platform.system.lock()
"""

import sys
import logging
from typing import TYPE_CHECKING

logger = logging.getLogger(__name__)

# Platform detection
PLATFORM = sys.platform
IS_WINDOWS = PLATFORM == 'win32'
IS_MACOS = PLATFORM == 'darwin'
IS_LINUX = PLATFORM.startswith('linux')

# Platform names for display
PLATFORM_NAME = {
    'win32': 'Windows',
    'darwin': 'macOS',
    'linux': 'Linux',
}.get(PLATFORM, PLATFORM)


def get_platform_module():
    """Get the platform-specific implementation module."""
    if IS_WINDOWS:
        from core.platform import windows as platform_impl
    elif IS_MACOS:
        from core.platform import macos as platform_impl
    elif IS_LINUX:
        from core.platform import linux as platform_impl
    else:
        from core.platform import base as platform_impl
        logger.warning(f"Unknown platform {PLATFORM}, using base implementation")
    return platform_impl


# Lazy-loaded platform instance
_platform_instance = None

def get_platform():
    """Get the platform abstraction instance."""
    global _platform_instance
    if _platform_instance is None:
        module = get_platform_module()
        _platform_instance = module.Platform()
    return _platform_instance


# Export platform info
__all__ = [
    'PLATFORM', 'IS_WINDOWS', 'IS_MACOS', 'IS_LINUX', 'PLATFORM_NAME',
    'get_platform', 'get_platform_module',
]
