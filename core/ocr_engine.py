"""
VoxMind OCR Engine
===================
Optical Character Recognition for extracting text from screen elements.

Features:
- Multiple OCR backends (EasyOCR, Tesseract, Windows OCR)
- Region-based OCR for specific elements
- Text confidence scoring
- Language detection
- Caching for performance

This enables:
- Reading text from unlabeled UI elements
- Understanding button labels from images
- Extracting text from screenshots
"""

import logging
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Tuple, Any
from enum import Enum
import time
import io

logger = logging.getLogger(__name__)


# === Check Available Backends ===

try:
    import easyocr  # type: ignore
    HAS_EASYOCR = True
except ImportError:
    HAS_EASYOCR = False

try:
    import pytesseract  # type: ignore
    from PIL import Image
    HAS_TESSERACT = True
except ImportError:
    HAS_TESSERACT = False

try:
    from PIL import ImageGrab
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


# === Data Classes ===

class OCRBackend(Enum):
    """Available OCR backends."""
    EASYOCR = "easyocr"
    TESSERACT = "tesseract"
    WINDOWS = "windows"
    NONE = "none"


@dataclass
class OCRResult:
    """Result from OCR extraction."""
    text: str
    confidence: float  # 0.0 to 1.0
    bbox: Tuple[int, int, int, int] = (0, 0, 0, 0)  # x, y, width, height
    language: str = "en"


@dataclass
class OCRRegion:
    """A region to perform OCR on."""
    x: int
    y: int
    width: int
    height: int
    
    @property
    def bbox(self) -> Tuple[int, int, int, int]:
        return (self.x, self.y, self.x + self.width, self.y + self.height)


# === OCR Engine ===

class OCREngine:
    """
    Multi-backend OCR engine for screen text extraction.
    
    Usage:
        ocr = OCREngine()
        
        # OCR entire screen
        results = ocr.extract_screen()
        
        # OCR specific region
        results = ocr.extract_region(100, 100, 200, 50)
        
        # OCR from image
        results = ocr.extract_from_image(image)
    """
    
    def __init__(self, backend: Optional[OCRBackend] = None, languages: List[str] = None):
        """
        Initialize OCR engine.
        
        Args:
            backend: Preferred backend (auto-detect if None)
            languages: Languages to detect (default: ["en"])
        """
        self.languages = languages or ["en"]
        self.backend = backend or self._detect_backend()
        
        self._easyocr_reader = None
        self._cache: Dict[str, List[OCRResult]] = {}
        self._cache_timeout = 5.0  # seconds
        
        logger.info(f"OCR Engine initialized with backend: {self.backend.value}")
    
    def _detect_backend(self) -> OCRBackend:
        """Auto-detect best available backend."""
        if HAS_EASYOCR:
            return OCRBackend.EASYOCR
        elif HAS_TESSERACT:
            return OCRBackend.TESSERACT
        else:
            logger.warning("No OCR backend available. Install easyocr or pytesseract.")
            return OCRBackend.NONE
    
    def _get_easyocr_reader(self):
        """Lazy-load EasyOCR reader (it's slow to initialize)."""
        if self._easyocr_reader is None and HAS_EASYOCR:
            logger.info("Initializing EasyOCR reader (this may take a moment)...")
            self._easyocr_reader = easyocr.Reader(self.languages, gpu=False)
        return self._easyocr_reader
    
    def extract_screen(self) -> List[OCRResult]:
        """
        Extract all text from the current screen.
        
        Returns:
            List of OCRResult with detected text and positions
        """
        if not HAS_PIL:
            logger.error("PIL not available for screen capture")
            return []
        
        try:
            # Capture screen
            screenshot = ImageGrab.grab()
            return self.extract_from_image(screenshot)
        except Exception as e:
            logger.error(f"Screen OCR failed: {e}")
            return []
    
    def extract_region(
        self, 
        x: int, 
        y: int, 
        width: int, 
        height: int
    ) -> List[OCRResult]:
        """
        Extract text from a specific screen region.
        
        Args:
            x, y: Top-left corner
            width, height: Size of region
        
        Returns:
            List of OCRResult
        """
        if not HAS_PIL:
            return []
        
        try:
            # Capture specific region
            bbox = (x, y, x + width, y + height)
            screenshot = ImageGrab.grab(bbox)
            
            results = self.extract_from_image(screenshot)
            
            # Adjust coordinates to screen position
            for result in results:
                bx, by, bw, bh = result.bbox
                result.bbox = (bx + x, by + y, bw, bh)
            
            return results
            
        except Exception as e:
            logger.error(f"Region OCR failed: {e}")
            return []
    
    def extract_from_image(self, image: Any) -> List[OCRResult]:
        """
        Extract text from an image.
        
        Args:
            image: PIL Image or numpy array
        
        Returns:
            List of OCRResult
        """
        if self.backend == OCRBackend.EASYOCR:
            return self._extract_easyocr(image)
        elif self.backend == OCRBackend.TESSERACT:
            return self._extract_tesseract(image)
        else:
            return []
    
    def _extract_easyocr(self, image: Any) -> List[OCRResult]:
        """Extract using EasyOCR."""
        if not HAS_EASYOCR:
            return []
        
        try:
            reader = self._get_easyocr_reader()
            if reader is None:
                return []
            
            # Convert PIL to array if needed
            import numpy as np
            if hasattr(image, 'convert'):
                image = np.array(image)
            
            # Run OCR
            detections = reader.readtext(image)
            
            results = []
            for detection in detections:
                bbox_pts, text, confidence = detection
                
                # Convert polygon to rectangle
                xs = [p[0] for p in bbox_pts]
                ys = [p[1] for p in bbox_pts]
                x, y = int(min(xs)), int(min(ys))
                w, h = int(max(xs) - x), int(max(ys) - y)
                
                results.append(OCRResult(
                    text=text,
                    confidence=confidence,
                    bbox=(x, y, w, h),
                ))
            
            return results
            
        except Exception as e:
            logger.error(f"EasyOCR extraction failed: {e}")
            return []
    
    def _extract_tesseract(self, image: Any) -> List[OCRResult]:
        """Extract using Tesseract."""
        if not HAS_TESSERACT:
            return []
        
        try:
            # Get detailed output with boxes
            data = pytesseract.image_to_data(
                image, 
                output_type=pytesseract.Output.DICT,
                lang="+".join(self.languages)
            )
            
            results = []
            n_boxes = len(data['text'])
            
            for i in range(n_boxes):
                text = data['text'][i].strip()
                if not text:
                    continue
                
                conf = float(data['conf'][i]) / 100.0  # Tesseract uses 0-100
                if conf < 0:  # -1 means no confidence
                    conf = 0.5
                
                results.append(OCRResult(
                    text=text,
                    confidence=conf,
                    bbox=(
                        data['left'][i],
                        data['top'][i],
                        data['width'][i],
                        data['height'][i]
                    ),
                ))
            
            return results
            
        except Exception as e:
            logger.error(f"Tesseract extraction failed: {e}")
            return []
    
    def extract_text_only(self, image: Any) -> str:
        """
        Simple text extraction without position info.
        
        Returns:
            Combined text string
        """
        results = self.extract_from_image(image)
        return " ".join(r.text for r in results)
    
    def extract_from_element(
        self, 
        element_rect: Tuple[int, int, int, int]
    ) -> str:
        """
        Extract text from a UI element's region.
        
        Args:
            element_rect: (x, y, width, height) of the element
        
        Returns:
            Text found in the element
        """
        x, y, w, h = element_rect
        
        # Add small padding
        padding = 2
        x = max(0, x - padding)
        y = max(0, y - padding)
        w += padding * 2
        h += padding * 2
        
        results = self.extract_region(x, y, w, h)
        
        if results:
            # Return highest confidence result
            results.sort(key=lambda r: r.confidence, reverse=True)
            return results[0].text
        
        return ""
    
    def find_text(self, target: str, threshold: float = 0.7) -> List[OCRResult]:
        """
        Find specific text on screen.
        
        Args:
            target: Text to search for
            threshold: Minimum match ratio (0-1)
        
        Returns:
            List of matches
        """
        all_results = self.extract_screen()
        target_lower = target.lower()
        
        matches = []
        for result in all_results:
            text_lower = result.text.lower()
            
            # Exact match
            if target_lower == text_lower:
                matches.append(result)
                continue
            
            # Partial match
            if target_lower in text_lower:
                matches.append(result)
                continue
            
            # Fuzzy match (simple ratio)
            ratio = self._similarity(target_lower, text_lower)
            if ratio >= threshold:
                matches.append(result)
        
        return matches
    
    def _similarity(self, a: str, b: str) -> float:
        """Simple string similarity ratio."""
        if not a or not b:
            return 0.0
        
        # Count matching characters
        matches = sum(1 for ca, cb in zip(a, b) if ca == cb)
        return matches / max(len(a), len(b))
    
    @property
    def is_available(self) -> bool:
        """Check if OCR is available."""
        return self.backend != OCRBackend.NONE


# === Singleton ===

_ocr_engine: Optional[OCREngine] = None


def get_ocr_engine() -> OCREngine:
    """Get the global OCR engine instance."""
    global _ocr_engine
    if _ocr_engine is None:
        _ocr_engine = OCREngine()
    return _ocr_engine


# === Demo ===

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("VoxMind OCR Engine")
    print("=" * 40)
    print(f"EasyOCR available: {HAS_EASYOCR}")
    print(f"Tesseract available: {HAS_TESSERACT}")
    print(f"PIL available: {HAS_PIL}")
    print()
    
    engine = get_ocr_engine()
    print(f"Using backend: {engine.backend.value}")
    print()
    
    if engine.is_available:
        print("Scanning screen for text...")
        start = time.time()
        results = engine.extract_screen()
        elapsed = time.time() - start
        
        print(f"Found {len(results)} text regions in {elapsed:.2f}s:")
        for i, result in enumerate(results[:10]):
            print(f"  {i+1}. '{result.text}' (conf: {result.confidence:.2f})")
        
        if len(results) > 10:
            print(f"  ... and {len(results) - 10} more")
    else:
        print("No OCR backend available.")
        print("Install with: pip install easyocr")
        print("         or: pip install pytesseract")
