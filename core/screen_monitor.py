"""
VoxMind Screen Monitor - Continuous Screen Watching
Provides real-time visual awareness through continuous screen capture and analysis.
"""

import threading
import time
from dataclasses import dataclass, field
from typing import Optional, Callable, List, Dict, Any
from datetime import datetime
from collections import deque
import io

try:
    from PIL import Image, ImageChops, ImageDraw, ImageFont
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

# Import screen context for OCR and analysis
try:
    from core.screen_context import get_screen_engine, ScreenContext
    HAS_SCREEN_CONTEXT = True
except ImportError:
    HAS_SCREEN_CONTEXT = False


@dataclass
class ScreenFrame:
    """A single captured screen frame with metadata"""
    timestamp: datetime
    image: Any  # PIL Image
    width: int
    height: int
    text: str = ""
    change_percent: float = 0.0
    keywords: List[str] = field(default_factory=list)
    active_app: str = ""


@dataclass
class ScreenEvent:
    """Detected screen change event"""
    timestamp: datetime
    event_type: str  # 'app_change', 'content_change', 'popup', 'notification'
    description: str
    region: Optional[tuple] = None  # (x, y, width, height)
    before_text: str = ""
    after_text: str = ""


class ScreenMonitor:
    """
    Continuous screen monitoring with change detection.
    Allows VoxMind to "watch" the screen and react to changes.
    """
    
    def __init__(self, 
                 capture_interval: float = 1.0,
                 analysis_interval: float = 3.0,
                 history_size: int = 30,
                 change_threshold: float = 5.0):
        """
        Initialize screen monitor.
        
        Args:
            capture_interval: Seconds between screen captures
            analysis_interval: Seconds between full OCR analysis
            history_size: Number of frames to keep in history
            change_threshold: Percentage of pixels that must change to trigger event
        """
        self.capture_interval = capture_interval
        self.analysis_interval = analysis_interval
        self.history_size = history_size
        self.change_threshold = change_threshold
        
        # Frame history
        self.frames: deque = deque(maxlen=history_size)
        self.events: deque = deque(maxlen=100)
        
        # State
        self._running = False
        self._paused = False
        self._thread: Optional[threading.Thread] = None
        self._last_analysis_time = 0
        self._last_app = ""
        
        # Callbacks
        self._on_change_callbacks: List[Callable] = []
        self._on_app_change_callbacks: List[Callable] = []
        self._on_text_detected_callbacks: List[Callable] = []
        
        # Screen engine
        self._engine = None
        
    @property
    def engine(self):
        """Lazy load screen engine"""
        if self._engine is None and HAS_SCREEN_CONTEXT:
            self._engine = get_screen_engine()
        return self._engine
    
    def start(self):
        """Start continuous screen monitoring"""
        if self._running:
            return
        
        self._running = True
        self._paused = False
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        print("[ScreenMonitor] Started continuous monitoring")
    
    def stop(self):
        """Stop screen monitoring"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
            self._thread = None
        print("[ScreenMonitor] Stopped")
    
    def pause(self):
        """Pause monitoring (keeps thread alive)"""
        self._paused = True
        print("[ScreenMonitor] Paused")
    
    def resume(self):
        """Resume monitoring"""
        self._paused = False
        print("[ScreenMonitor] Resumed")
    
    @property
    def is_running(self) -> bool:
        return self._running and not self._paused
    
    def _monitor_loop(self):
        """Main monitoring loop"""
        while self._running:
            if self._paused:
                time.sleep(0.1)
                continue
            
            try:
                self._capture_frame()
            except Exception as e:
                print(f"[ScreenMonitor] Error: {e}")
            
            time.sleep(self.capture_interval)
    
    def _capture_frame(self):
        """Capture a single frame and analyze changes"""
        if not self.engine:
            return
        
        # Capture screen
        image = self.engine.capture.capture_full_screen()
        if image is None:
            return
        
        now = datetime.now()
        current_time = time.time()
        
        # Create frame
        frame = ScreenFrame(
            timestamp=now,
            image=image,
            width=image.width,
            height=image.height
        )
        
        # Calculate change from previous frame
        if self.frames:
            prev_frame = self.frames[-1]
            frame.change_percent = self._calculate_change(prev_frame.image, image)
            
            # Detect significant changes
            if frame.change_percent > self.change_threshold:
                self._detect_change_type(prev_frame, frame)
        
        # Periodic full analysis (OCR is slow)
        if current_time - self._last_analysis_time >= self.analysis_interval:
            self._analyze_frame(frame)
            self._last_analysis_time = current_time
        
        # Add to history
        self.frames.append(frame)
    
    def _calculate_change(self, img1: Image.Image, img2: Image.Image) -> float:
        """Calculate percentage of pixels that changed between frames"""
        try:
            # Resize for faster comparison
            size = (192, 120)
            img1_small = img1.resize(size).convert('L')
            img2_small = img2.resize(size).convert('L')
            
            # Calculate difference
            diff = ImageChops.difference(img1_small, img2_small)
            
            # Count changed pixels (threshold of 30 to ignore minor variations)
            pixels = list(diff.getdata())
            changed = sum(1 for p in pixels if p > 30)
            total = len(pixels)
            
            return (changed / total) * 100
        except Exception:
            return 0.0
    
    def _detect_change_type(self, prev_frame: ScreenFrame, curr_frame: ScreenFrame):
        """Detect what type of change occurred"""
        # Check for app change
        if curr_frame.active_app and curr_frame.active_app != prev_frame.active_app:
            event = ScreenEvent(
                timestamp=curr_frame.timestamp,
                event_type='app_change',
                description=f"Switched to {curr_frame.active_app}",
                before_text=prev_frame.active_app,
                after_text=curr_frame.active_app
            )
            self.events.append(event)
            self._trigger_app_change_callbacks(event)
        
        # Large change might be a popup or dialog
        if curr_frame.change_percent > 30:
            event = ScreenEvent(
                timestamp=curr_frame.timestamp,
                event_type='popup',
                description=f"Major screen change detected ({curr_frame.change_percent:.1f}%)"
            )
            self.events.append(event)
        
        # Trigger change callbacks
        self._trigger_change_callbacks(curr_frame)
    
    def _analyze_frame(self, frame: ScreenFrame):
        """Perform full OCR analysis on frame"""
        if not self.engine:
            return
        
        try:
            # Get screen context
            context = self.engine.capture_and_analyze()
            
            frame.text = context.all_text
            frame.keywords = context.keywords
            frame.active_app = context.detected_app or ""
            
            # Check for app change
            if frame.active_app and frame.active_app != self._last_app:
                self._last_app = frame.active_app
            
            # Trigger text callbacks if new text detected
            if frame.text:
                self._trigger_text_callbacks(frame)
                
        except Exception as e:
            print(f"[ScreenMonitor] Analysis error: {e}")
    
    # Callback registration
    def on_change(self, callback: Callable[[ScreenFrame], None]):
        """Register callback for screen changes"""
        self._on_change_callbacks.append(callback)
    
    def on_app_change(self, callback: Callable[[ScreenEvent], None]):
        """Register callback for app switches"""
        self._on_app_change_callbacks.append(callback)
    
    def on_text_detected(self, callback: Callable[[ScreenFrame], None]):
        """Register callback when new text is detected"""
        self._on_text_detected_callbacks.append(callback)
    
    def _trigger_change_callbacks(self, frame: ScreenFrame):
        for cb in self._on_change_callbacks:
            try:
                cb(frame)
            except Exception as e:
                print(f"[ScreenMonitor] Callback error: {e}")
    
    def _trigger_app_change_callbacks(self, event: ScreenEvent):
        for cb in self._on_app_change_callbacks:
            try:
                cb(event)
            except Exception as e:
                print(f"[ScreenMonitor] Callback error: {e}")
    
    def _trigger_text_callbacks(self, frame: ScreenFrame):
        for cb in self._on_text_detected_callbacks:
            try:
                cb(frame)
            except Exception as e:
                print(f"[ScreenMonitor] Callback error: {e}")
    
    # Query methods
    def get_current_context(self) -> Optional[str]:
        """Get description of current screen state"""
        if not self.frames:
            return None
        
        frame = self.frames[-1]
        parts = []
        
        if frame.active_app:
            parts.append(f"Currently in: {frame.active_app}")
        if frame.keywords:
            parts.append(f"Topics: {', '.join(frame.keywords[:5])}")
        if frame.change_percent > 10:
            parts.append(f"Screen is actively changing ({frame.change_percent:.0f}%)")
        
        return " | ".join(parts) if parts else "Screen is idle"
    
    def get_recent_events(self, count: int = 5) -> List[ScreenEvent]:
        """Get recent screen events"""
        return list(self.events)[-count:]
    
    def get_activity_summary(self, seconds: int = 60) -> str:
        """Get summary of recent screen activity"""
        cutoff = datetime.now().timestamp() - seconds
        recent_frames = [f for f in self.frames if f.timestamp.timestamp() > cutoff]
        
        if not recent_frames:
            return "No recent activity captured."
        
        # Analyze activity
        avg_change = sum(f.change_percent for f in recent_frames) / len(recent_frames)
        apps = set(f.active_app for f in recent_frames if f.active_app)
        all_keywords = []
        for f in recent_frames:
            all_keywords.extend(f.keywords)
        
        # Count keyword frequency
        keyword_counts = {}
        for kw in all_keywords:
            keyword_counts[kw] = keyword_counts.get(kw, 0) + 1
        top_keywords = sorted(keyword_counts.items(), key=lambda x: -x[1])[:5]
        
        parts = []
        parts.append(f"Captured {len(recent_frames)} frames over {seconds}s")
        parts.append(f"Average change: {avg_change:.1f}%")
        
        if apps:
            parts.append(f"Apps used: {', '.join(apps)}")
        if top_keywords:
            kw_str = ', '.join(f"{k}" for k, v in top_keywords)
            parts.append(f"Main topics: {kw_str}")
        
        return " | ".join(parts)
    
    def is_screen_idle(self, seconds: int = 5) -> bool:
        """Check if screen has been idle (no changes) for given seconds"""
        if not self.frames:
            return True
        
        cutoff = datetime.now().timestamp() - seconds
        recent = [f for f in self.frames if f.timestamp.timestamp() > cutoff]
        
        if not recent:
            return True
        
        return all(f.change_percent < 2 for f in recent)
    
    def wait_for_change(self, timeout: float = 30.0) -> bool:
        """Wait until screen changes (for automation)"""
        start = time.time()
        initial_frames = len(self.frames)
        
        while time.time() - start < timeout:
            if len(self.frames) > initial_frames:
                latest = self.frames[-1]
                if latest.change_percent > self.change_threshold:
                    return True
            time.sleep(0.1)
        
        return False
    
    def wait_for_text(self, text: str, timeout: float = 30.0) -> bool:
        """Wait until specific text appears on screen"""
        text_lower = text.lower()
        start = time.time()
        
        while time.time() - start < timeout:
            if self.frames:
                latest = self.frames[-1]
                if text_lower in latest.text.lower():
                    return True
            time.sleep(0.5)
        
        return False


# Singleton instance
_monitor: Optional[ScreenMonitor] = None

def get_screen_monitor() -> ScreenMonitor:
    """Get singleton ScreenMonitor instance"""
    global _monitor
    if _monitor is None:
        _monitor = ScreenMonitor()
    return _monitor


def start_monitoring():
    """Start screen monitoring"""
    get_screen_monitor().start()


def stop_monitoring():
    """Stop screen monitoring"""
    get_screen_monitor().stop()


if __name__ == "__main__":
    import time
    
    print("=" * 60)
    print("VoxMind Screen Monitor Demo")
    print("=" * 60)
    
    monitor = get_screen_monitor()
    
    # Register callbacks
    def on_change(frame):
        if frame.change_percent > 10:
            print(f"  [CHANGE] {frame.change_percent:.1f}% change detected")
    
    def on_app_change(event):
        print(f"  [APP] {event.description}")
    
    monitor.on_change(on_change)
    monitor.on_app_change(on_app_change)
    
    print("\nStarting monitoring for 15 seconds...")
    print("Try switching windows or scrolling to see change detection.\n")
    
    monitor.start()
    
    for i in range(15):
        time.sleep(1)
        context = monitor.get_current_context()
        if context and i % 3 == 0:
            print(f"[{i}s] {context}")
    
    print("\n" + "-" * 40)
    print("Activity Summary:")
    print(monitor.get_activity_summary(15))
    
    print("\nRecent Events:")
    for event in monitor.get_recent_events(5):
        print(f"  - {event.event_type}: {event.description}")
    
    monitor.stop()
    print("\n" + "=" * 60)
    print("Demo complete!")
