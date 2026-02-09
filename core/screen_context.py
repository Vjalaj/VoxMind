"""
VoxMind Screen Context Module
==============================
Share your screen with Vox for contextual understanding.

Features:
- Screen capture (full screen, window, region)
- OCR text extraction
- UI element detection
- Semantic analysis of screen content
- Context-aware command suggestions

Inspired by:
- Google Assistant Screen Context
- Microsoft Copilot Vision
- Apple Intelligence Screen Awareness
"""

import threading
import logging
import re
import io
import warnings
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

# Suppress PyTorch/EasyOCR GPU warnings (runs fine on CPU)
warnings.filterwarnings("ignore", message=".*pin_memory.*")
warnings.filterwarnings("ignore", message=".*accelerator.*")

logger = logging.getLogger(__name__)

# ============================================================================
# LAZY IMPORTS
# ============================================================================

_PIL_AVAILABLE = False
_PYTESSERACT_AVAILABLE = False
_PYAUTOGUI_AVAILABLE = False

def _ensure_pil():
    global _PIL_AVAILABLE
    try:
        from PIL import Image, ImageGrab, ImageFilter, ImageEnhance
        _PIL_AVAILABLE = True
        return True
    except ImportError:
        logger.warning("PIL not installed. Install with: pip install Pillow")
        return False

def _ensure_tesseract():
    global _PYTESSERACT_AVAILABLE
    try:
        import pytesseract
        _PYTESSERACT_AVAILABLE = True
        return True
    except ImportError:
        logger.warning("pytesseract not installed. Install with: pip install pytesseract")
        return False

def _ensure_pyautogui():
    global _PYAUTOGUI_AVAILABLE
    try:
        import pyautogui
        _PYAUTOGUI_AVAILABLE = True
        return True
    except ImportError:
        logger.warning("pyautogui not installed")
        return False


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class ScreenRegion:
    """Represents a region of the screen."""
    x: int
    y: int
    width: int
    height: int
    
    @property
    def center(self) -> Tuple[int, int]:
        return (self.x + self.width // 2, self.y + self.height // 2)
    
    @property
    def bounds(self) -> Tuple[int, int, int, int]:
        return (self.x, self.y, self.x + self.width, self.y + self.height)


@dataclass
class TextBlock:
    """A block of text found on screen."""
    text: str
    region: ScreenRegion
    confidence: float = 0.0
    
    def __str__(self):
        return self.text


@dataclass
class UIElement:
    """A detected UI element."""
    element_type: str  # button, input, link, menu, etc.
    text: str
    region: ScreenRegion
    confidence: float = 0.0


@dataclass
class ScreenContext:
    """Complete analysis of screen content."""
    timestamp: datetime = field(default_factory=datetime.now)
    
    # Raw data
    screenshot_path: Optional[str] = None
    
    # Extracted content
    all_text: str = ""
    text_blocks: List[TextBlock] = field(default_factory=list)
    ui_elements: List[UIElement] = field(default_factory=list)
    
    # Semantic analysis
    detected_app: Optional[str] = None
    page_title: Optional[str] = None
    main_content: str = ""
    
    # Contextual info
    urls: List[str] = field(default_factory=list)
    emails: List[str] = field(default_factory=list)
    phone_numbers: List[str] = field(default_factory=list)
    dates: List[str] = field(default_factory=list)
    prices: List[str] = field(default_factory=list)
    
    # Keywords and topics
    keywords: List[str] = field(default_factory=list)
    suggested_actions: List[str] = field(default_factory=list)


# ============================================================================
# SCREEN CAPTURE
# ============================================================================

class ScreenCapture:
    """Handles screen capture operations."""
    
    def __init__(self):
        self._lock = threading.Lock()
        self._last_capture = None
        self._cache_dir = Path("cache/screenshots")
        self._cache_dir.mkdir(parents=True, exist_ok=True)
    
    def capture_full_screen(self) -> Optional[Any]:
        """Capture the entire screen."""
        if not _ensure_pil():
            return None
        
        try:
            from PIL import ImageGrab
            with self._lock:
                screenshot = ImageGrab.grab()
                self._last_capture = screenshot
                return screenshot
        except Exception as e:
            logger.error(f"Failed to capture screen: {e}")
            return None
    
    def capture_region(self, region: ScreenRegion) -> Optional[Any]:
        """Capture a specific region of the screen."""
        if not _ensure_pil():
            return None
        
        try:
            from PIL import ImageGrab
            with self._lock:
                screenshot = ImageGrab.grab(bbox=region.bounds)
                return screenshot
        except Exception as e:
            logger.error(f"Failed to capture region: {e}")
            return None
    
    def capture_active_window(self) -> Optional[Any]:
        """Capture the currently active window."""
        if not _ensure_pyautogui():
            return self.capture_full_screen()
        
        try:
            import pyautogui
            import pygetwindow as gw
            
            active = gw.getActiveWindow()
            if active:
                region = ScreenRegion(
                    x=active.left,
                    y=active.top,
                    width=active.width,
                    height=active.height
                )
                return self.capture_region(region)
            return self.capture_full_screen()
        except Exception as e:
            logger.error(f"Failed to capture active window: {e}")
            return self.capture_full_screen()
    
    def save_screenshot(self, image, filename: Optional[str] = None) -> str:
        """Save a screenshot to disk."""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"screenshot_{timestamp}.png"
        
        path = self._cache_dir / filename
        image.save(path)
        return str(path)
    
    def get_last_capture(self):
        """Get the most recent screenshot."""
        return self._last_capture


# ============================================================================
# OCR TEXT EXTRACTION
# ============================================================================

class TextExtractor:
    """Extract text from images using OCR (multiple backends supported)."""
    
    def __init__(self):
        self._tesseract_cmd = None
        self._easyocr_reader = None
        self._ocr_backend = None  # 'tesseract', 'easyocr', or None
        self._check_ocr_backends()
    
    def _check_ocr_backends(self):
        """Check available OCR backends in order of preference."""
        # Try Tesseract first (faster, more accurate for clear text)
        if self._check_tesseract():
            self._ocr_backend = 'tesseract'
            logger.info("Using Tesseract OCR backend")
            return
        
        # Try EasyOCR as fallback (works without system install)
        if self._check_easyocr():
            self._ocr_backend = 'easyocr'
            logger.info("Using EasyOCR backend")
            return
        
        logger.warning("No OCR backend available. Screen reading disabled.")
    
    def _check_tesseract(self) -> bool:
        """Check if Tesseract is available."""
        if not _ensure_tesseract():
            return False
        
        import pytesseract
        
        # Common Tesseract paths on Windows
        possible_paths = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            r"C:\Users\{}\AppData\Local\Tesseract-OCR\tesseract.exe",
        ]
        
        import os
        for path in possible_paths:
            expanded = path.format(os.environ.get('USERNAME', ''))
            if os.path.exists(expanded):
                pytesseract.pytesseract.tesseract_cmd = expanded
                self._tesseract_cmd = expanded
                return True
        
        # Try system PATH
        try:
            pytesseract.get_tesseract_version()
            self._tesseract_cmd = "tesseract"
            return True
        except (pytesseract.TesseractNotFoundError, OSError) as e:
            logger.debug(f"Tesseract not found in PATH: {e}")
            return False
    
    def _check_easyocr(self) -> bool:
        """Check if EasyOCR is available."""
        try:
            import easyocr
            # Don't initialize reader yet - it's slow
            return True
        except ImportError:
            return False
    
    def _get_easyocr_reader(self):
        """Lazy-load EasyOCR reader."""
        if self._easyocr_reader is None:
            import easyocr
            # Use English only for faster loading
            self._easyocr_reader = easyocr.Reader(['en'], gpu=False, verbose=False)
        return self._easyocr_reader
    
    @property
    def available(self) -> bool:
        """Check if any OCR backend is available."""
        return self._ocr_backend is not None
    
    def extract_text(self, image) -> str:
        """Extract all text from an image."""
        if not self.available:
            return ""
        
        try:
            if self._ocr_backend == 'tesseract':
                return self._extract_text_tesseract(image)
            elif self._ocr_backend == 'easyocr':
                return self._extract_text_easyocr(image)
            return ""
        except Exception as e:
            logger.error(f"OCR failed: {e}")
            return ""
    
    def _extract_text_tesseract(self, image) -> str:
        """Extract text using Tesseract."""
        import pytesseract
        processed = self._preprocess_image(image)
        text = pytesseract.image_to_string(processed, lang='eng')
        return text.strip()
    
    def _extract_text_easyocr(self, image) -> str:
        """Extract text using EasyOCR."""
        import numpy as np
        reader = self._get_easyocr_reader()
        # Convert PIL image to numpy array
        img_array = np.array(image)
        results = reader.readtext(img_array, detail=0)
        return '\n'.join(results)
    
    def extract_text_with_positions(self, image) -> List[TextBlock]:
        """Extract text with bounding box positions."""
        if not self.available:
            return []
        
        try:
            if self._ocr_backend == 'tesseract':
                return self._extract_positions_tesseract(image)
            elif self._ocr_backend == 'easyocr':
                return self._extract_positions_easyocr(image)
            return []
        except Exception as e:
            logger.error(f"OCR with positions failed: {e}")
            return []
    
    def _extract_positions_tesseract(self, image) -> List[TextBlock]:
        """Extract text positions using Tesseract."""
        import pytesseract
        
        data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
        
        blocks = []
        n_boxes = len(data['text'])
        
        for i in range(n_boxes):
            text = data['text'][i].strip()
            conf = float(data['conf'][i])
            
            if text and conf > 30:
                region = ScreenRegion(
                    x=data['left'][i],
                    y=data['top'][i],
                    width=data['width'][i],
                    height=data['height'][i]
                )
                blocks.append(TextBlock(text=text, region=region, confidence=conf))
        
        return blocks
    
    def _extract_positions_easyocr(self, image) -> List[TextBlock]:
        """Extract text positions using EasyOCR."""
        import numpy as np
        reader = self._get_easyocr_reader()
        img_array = np.array(image)
        results = reader.readtext(img_array)
        
        blocks = []
        for bbox, text, conf in results:
            # bbox is [[x1,y1], [x2,y1], [x2,y2], [x1,y2]]
            x1, y1 = int(bbox[0][0]), int(bbox[0][1])
            x2, y2 = int(bbox[2][0]), int(bbox[2][1])
            region = ScreenRegion(
                x=x1, y=y1,
                width=x2 - x1,
                height=y2 - y1
            )
            blocks.append(TextBlock(text=text, region=region, confidence=conf))
        
        return blocks
    
    def _preprocess_image(self, image):
        """Preprocess image for better OCR accuracy."""
        from PIL import Image, ImageEnhance, ImageFilter
        
        # Convert to grayscale
        if image.mode != 'L':
            image = image.convert('L')
        
        # Increase contrast
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(1.5)
        
        # Sharpen
        image = image.filter(ImageFilter.SHARPEN)
        
        return image


# ============================================================================
# SEMANTIC ANALYZER
# ============================================================================

class SemanticAnalyzer:
    """Analyze screen content for semantic understanding."""
    
    # Regex patterns for common entities
    URL_PATTERN = re.compile(
        r'https?://[^\s<>"{}|\\^`\[\]]+|www\.[^\s<>"{}|\\^`\[\]]+'
    )
    EMAIL_PATTERN = re.compile(
        r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    )
    PHONE_PATTERN = re.compile(
        r'(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'
    )
    PRICE_PATTERN = re.compile(
        r'\$[\d,]+(?:\.\d{2})?|\d+(?:,\d{3})*(?:\.\d{2})?\s*(?:USD|EUR|GBP|INR|₹|€|£)'
    )
    DATE_PATTERN = re.compile(
        r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|'
        r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s*\d{4}',
        re.I
    )
    
    # App detection patterns
    APP_PATTERNS = {
        'browser': [
            r'chrome', r'firefox', r'edge', r'safari', r'opera', r'brave',
            r'https?://', r'www\.', r'\.com', r'\.org', r'\.net'
        ],
        'code_editor': [
            r'visual studio', r'vscode', r'vs code', r'pycharm', r'intellij',
            r'sublime', r'atom', r'notepad\+\+', r'def\s+\w+\(', r'class\s+\w+:',
            r'function\s+\w+\(', r'import\s+\w+'
        ],
        'email': [
            r'inbox', r'compose', r'reply', r'forward', r'@gmail', r'@outlook',
            r'@yahoo', r'subject:', r'from:', r'to:'
        ],
        'document': [
            r'word', r'document', r'page \d+ of \d+', r'paragraph',
            r'font', r'heading', r'\.docx?', r'\.pdf'
        ],
        'spreadsheet': [
            r'excel', r'sheet', r'cell', r'row', r'column', r'formula',
            r'\.xlsx?', r'sum\(', r'average\('
        ],
        'chat': [
            r'message', r'chat', r'send', r'typing', r'online', r'slack',
            r'teams', r'discord', r'whatsapp', r'telegram'
        ],
        'terminal': [
            r'\$\s', r'>\s', r'c:\\', r'/home/', r'pip install', r'npm',
            r'git\s', r'python', r'node', r'powershell', r'bash'
        ],
        'media': [
            r'play', r'pause', r'volume', r'spotify', r'youtube', r'netflix',
            r'video', r'audio', r'\d{1,2}:\d{2}'
        ],
    }
    
    # Action suggestions based on content
    ACTION_TRIGGERS = {
        'url': ["open this link", "go to this website", "search for more"],
        'email': ["compose email", "reply to this", "forward email"],
        'phone': ["call this number", "send a text"],
        'price': ["compare prices", "add to cart", "find cheaper"],
        'code': ["run this code", "debug", "explain this code"],
        'error': ["fix this error", "search for solution", "stack overflow"],
        'form': ["fill this form", "submit", "clear form"],
    }
    
    def analyze(self, text: str, text_blocks: List[TextBlock] = None) -> ScreenContext:
        """Perform semantic analysis on screen content."""
        context = ScreenContext()
        context.all_text = text
        context.text_blocks = text_blocks or []
        
        # Extract entities
        context.urls = self.URL_PATTERN.findall(text)
        context.emails = self.EMAIL_PATTERN.findall(text)
        context.phone_numbers = self.PHONE_PATTERN.findall(text)
        context.prices = self.PRICE_PATTERN.findall(text)
        context.dates = self.DATE_PATTERN.findall(text)
        
        # Detect application context
        context.detected_app = self._detect_app(text)
        
        # Extract page title (usually first prominent text)
        context.page_title = self._extract_title(text, text_blocks)
        
        # Extract keywords
        context.keywords = self._extract_keywords(text)
        
        # Generate action suggestions
        context.suggested_actions = self._suggest_actions(context)
        
        # Extract main content
        context.main_content = self._extract_main_content(text)
        
        return context
    
    def _detect_app(self, text: str) -> Optional[str]:
        """Detect what application is being used."""
        text_lower = text.lower()
        
        scores = {}
        for app, patterns in self.APP_PATTERNS.items():
            score = sum(1 for p in patterns if re.search(p, text_lower))
            if score > 0:
                scores[app] = score
        
        if scores:
            return max(scores, key=scores.get)
        return None
    
    def _extract_title(self, text: str, blocks: List[TextBlock]) -> Optional[str]:
        """Extract the page/window title."""
        # First line is often the title
        lines = text.strip().split('\n')
        if lines:
            first_line = lines[0].strip()
            if 5 < len(first_line) < 100:
                return first_line
        
        # Or use the largest text block
        if blocks:
            largest = max(blocks, key=lambda b: b.region.height, default=None)
            if largest and len(largest.text) < 100:
                return largest.text
        
        return None
    
    def _extract_keywords(self, text: str, max_keywords: int = 10) -> List[str]:
        """Extract important keywords from text."""
        # Simple keyword extraction based on word frequency
        # Filter out common words
        stopwords = {
            'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
            'should', 'may', 'might', 'must', 'shall', 'can', 'need', 'dare',
            'ought', 'used', 'to', 'of', 'in', 'for', 'on', 'with', 'at', 'by',
            'from', 'as', 'into', 'through', 'during', 'before', 'after', 'above',
            'below', 'between', 'under', 'again', 'further', 'then', 'once', 'here',
            'there', 'when', 'where', 'why', 'how', 'all', 'each', 'few', 'more',
            'most', 'other', 'some', 'such', 'no', 'nor', 'not', 'only', 'own',
            'same', 'so', 'than', 'too', 'very', 'just', 'and', 'but', 'if', 'or',
            'because', 'until', 'while', 'this', 'that', 'these', 'those', 'it',
        }
        
        # Tokenize and count
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
        word_counts = {}
        for word in words:
            if word not in stopwords:
                word_counts[word] = word_counts.get(word, 0) + 1
        
        # Sort by frequency
        sorted_words = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)
        return [word for word, count in sorted_words[:max_keywords]]
    
    def _suggest_actions(self, context: ScreenContext) -> List[str]:
        """Suggest actions based on screen content."""
        suggestions = []
        
        if context.urls:
            suggestions.extend(self.ACTION_TRIGGERS['url'])
        if context.emails:
            suggestions.extend(self.ACTION_TRIGGERS['email'])
        if context.phone_numbers:
            suggestions.extend(self.ACTION_TRIGGERS['phone'])
        if context.prices:
            suggestions.extend(self.ACTION_TRIGGERS['price'])
        
        # Check for code/error content
        text_lower = context.all_text.lower()
        if any(kw in text_lower for kw in ['error', 'exception', 'failed', 'traceback']):
            suggestions.extend(self.ACTION_TRIGGERS['error'])
        if context.detected_app == 'code_editor':
            suggestions.extend(self.ACTION_TRIGGERS['code'])
        
        return list(set(suggestions))[:5]  # Limit to 5 unique suggestions
    
    def _extract_main_content(self, text: str, max_length: int = 500) -> str:
        """Extract the main content, filtering noise."""
        lines = text.split('\n')
        
        # Filter out very short lines (likely UI elements)
        content_lines = [
            line.strip() for line in lines
            if len(line.strip()) > 20
        ]
        
        main_content = '\n'.join(content_lines)
        if len(main_content) > max_length:
            main_content = main_content[:max_length] + "..."
        
        return main_content


# ============================================================================
# MAIN SCREEN CONTEXT ENGINE
# ============================================================================

class ScreenContextEngine:
    """
    Main engine for screen context understanding.
    
    Usage:
        engine = ScreenContextEngine()
        context = engine.capture_and_analyze()
        print(context.detected_app)
        print(context.keywords)
        print(context.suggested_actions)
    """
    
    def __init__(self):
        self.capture = ScreenCapture()
        self.extractor = TextExtractor()
        self.analyzer = SemanticAnalyzer()
        
        self._last_context: Optional[ScreenContext] = None
        self._context_history: List[ScreenContext] = []
        self._max_history = 10
        self._lock = threading.Lock()
    
    @property
    def ocr_available(self) -> bool:
        """Check if OCR is available."""
        return self.extractor.available
    
    def capture_and_analyze(self, save_screenshot: bool = False) -> ScreenContext:
        """Capture the screen and perform full analysis."""
        with self._lock:
            # Capture screen
            screenshot = self.capture.capture_full_screen()
            if screenshot is None:
                return ScreenContext()
            
            # Save if requested
            screenshot_path = None
            if save_screenshot:
                screenshot_path = self.capture.save_screenshot(screenshot)
            
            # Extract text
            all_text = self.extractor.extract_text(screenshot)
            text_blocks = self.extractor.extract_text_with_positions(screenshot)
            
            # Analyze
            context = self.analyzer.analyze(all_text, text_blocks)
            context.screenshot_path = screenshot_path
            
            # Store in history
            self._last_context = context
            self._context_history.append(context)
            if len(self._context_history) > self._max_history:
                self._context_history.pop(0)
            
            return context
    
    def capture_active_window_and_analyze(self) -> ScreenContext:
        """Capture and analyze only the active window."""
        with self._lock:
            screenshot = self.capture.capture_active_window()
            if screenshot is None:
                return ScreenContext()
            
            all_text = self.extractor.extract_text(screenshot)
            text_blocks = self.extractor.extract_text_with_positions(screenshot)
            
            context = self.analyzer.analyze(all_text, text_blocks)
            self._last_context = context
            
            return context
    
    def get_quick_context(self) -> Dict[str, Any]:
        """Get a quick summary of the current screen context."""
        context = self.capture_and_analyze()
        
        return {
            "app": context.detected_app,
            "title": context.page_title,
            "keywords": context.keywords[:5],
            "has_urls": len(context.urls) > 0,
            "has_emails": len(context.emails) > 0,
            "has_prices": len(context.prices) > 0,
            "suggested_actions": context.suggested_actions,
            "text_preview": context.main_content[:200] if context.main_content else "",
        }
    
    def find_text_on_screen(self, search_text: str) -> List[TextBlock]:
        """Find specific text on screen and return its location."""
        context = self._last_context
        if context is None:
            context = self.capture_and_analyze()
        
        search_lower = search_text.lower()
        matches = []
        
        for block in context.text_blocks:
            if search_lower in block.text.lower():
                matches.append(block)
        
        return matches
    
    def click_on_text(self, text: str) -> bool:
        """Find text on screen and click it."""
        if not _ensure_pyautogui():
            return False
        
        matches = self.find_text_on_screen(text)
        if matches:
            import pyautogui
            best_match = matches[0]
            x, y = best_match.region.center
            pyautogui.click(x, y)
            logger.info(f"Clicked on '{text}' at ({x}, {y})")
            return True
        
        logger.warning(f"Text '{text}' not found on screen")
        return False
    
    def get_last_context(self) -> Optional[ScreenContext]:
        """Get the most recent screen context."""
        return self._last_context
    
    def describe_screen(self) -> str:
        """Get a natural language description of the screen."""
        context = self.capture_and_analyze()
        
        parts = []
        
        if context.detected_app:
            parts.append(f"You appear to be using a {context.detected_app} application.")
        
        if context.page_title:
            parts.append(f"The current page or window is titled: '{context.page_title}'")
        
        if context.keywords:
            parts.append(f"Key topics on screen: {', '.join(context.keywords[:5])}")
        
        if context.urls:
            parts.append(f"I can see {len(context.urls)} link(s) on the screen.")
        
        if context.emails:
            parts.append(f"There are {len(context.emails)} email address(es) visible.")
        
        if context.prices:
            parts.append(f"I can see prices: {', '.join(context.prices[:3])}")
        
        if context.suggested_actions:
            parts.append(f"You might want to: {', '.join(context.suggested_actions[:3])}")
        
        if not parts:
            if context.all_text:
                return f"I can see some content on your screen. Preview: {context.main_content[:150]}..."
            return "I couldn't read the screen content. Is Tesseract OCR installed?"
        
        return " ".join(parts)


# ============================================================================
# SINGLETON & CONVENIENCE FUNCTIONS
# ============================================================================

_engine: Optional[ScreenContextEngine] = None

def get_screen_engine() -> ScreenContextEngine:
    """Get the singleton ScreenContextEngine instance."""
    global _engine
    if _engine is None:
        _engine = ScreenContextEngine()
    return _engine


def capture_screen_context() -> ScreenContext:
    """Capture and analyze the current screen."""
    return get_screen_engine().capture_and_analyze()


def describe_current_screen() -> str:
    """Get a description of what's on screen."""
    return get_screen_engine().describe_screen()


def find_and_click(text: str) -> bool:
    """Find text on screen and click it."""
    return get_screen_engine().click_on_text(text)


# ============================================================================
# TEST / DEMO
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("VoxMind Screen Context Module")
    print("=" * 60)
    
    engine = get_screen_engine()
    
    print(f"\nOCR Available: {engine.ocr_available}")
    
    if not engine.ocr_available:
        print("\n⚠️  Tesseract OCR is not installed.")
        print("   To enable screen reading, install Tesseract:")
        print("   1. Download from: https://github.com/UB-Mannheim/tesseract/wiki")
        print("   2. Install and add to PATH")
        print("   3. pip install pytesseract")
    else:
        print("\nCapturing screen...")
        context = engine.capture_and_analyze(save_screenshot=True)
        
        print(f"\n[Screen Analysis Results]")
        print(f"  Detected App: {context.detected_app or 'Unknown'}")
        print(f"  Page Title: {context.page_title or 'Unknown'}")
        print(f"  Keywords: {', '.join(context.keywords[:5]) if context.keywords else 'None'}")
        print(f"  URLs Found: {len(context.urls)}")
        print(f"  Emails Found: {len(context.emails)}")
        print(f"  Prices Found: {len(context.prices)}")
        print(f"  Text Blocks: {len(context.text_blocks)}")
        
        if context.suggested_actions:
            print(f"\n[Suggested Actions]")
            for action in context.suggested_actions:
                print(f"  • {action}")
        
        if context.screenshot_path:
            print(f"\n  Screenshot saved: {context.screenshot_path}")
        
        print(f"\n[Screen Description]")
        print(engine.describe_screen())
    
    print("\n" + "=" * 60)
