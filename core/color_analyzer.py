"""
VoxMind Color Analyzer
=======================
Analyzes colors in UI elements to understand semantic meaning.

Color Semantics:
- RED    = Error, danger, critical, stop, delete
- GREEN  = Success, ok, go, confirm, positive
- YELLOW = Warning, caution, attention
- BLUE   = Link, info, primary action
- GRAY   = Disabled, inactive, secondary
- WHITE  = Background, clean
- BLACK  = Text, foreground

This enables:
- "Click the red error message"
- "Find the green checkmark"
- "The blue link on the left"
"""

import logging
from dataclasses import dataclass
from typing import Optional, List, Tuple, Dict, Any
from enum import Enum
import colorsys

logger = logging.getLogger(__name__)


# === Check Dependencies ===

try:
    from PIL import Image, ImageGrab, ImageStat
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False


# === Color Enums ===

class ColorName(Enum):
    """Named colors for natural language."""
    RED = "red"
    GREEN = "green"
    BLUE = "blue"
    YELLOW = "yellow"
    ORANGE = "orange"
    PURPLE = "purple"
    PINK = "pink"
    CYAN = "cyan"
    BROWN = "brown"
    BLACK = "black"
    WHITE = "white"
    GRAY = "gray"
    UNKNOWN = "unknown"


class ColorSemantic(Enum):
    """Semantic meanings of colors in UI context."""
    ERROR = "error"           # Red - errors, danger
    WARNING = "warning"       # Yellow/Orange - warnings
    SUCCESS = "success"       # Green - success, confirmation
    INFO = "info"             # Blue - information
    LINK = "link"             # Blue underlined - clickable links
    PRIMARY = "primary"       # Brand primary color
    SECONDARY = "secondary"   # Muted, secondary
    DISABLED = "disabled"     # Gray - inactive
    NEUTRAL = "neutral"       # No special meaning


# === Data Classes ===

@dataclass
class ColorInfo:
    """Information about a color."""
    rgb: Tuple[int, int, int]
    name: ColorName
    semantic: ColorSemantic
    hex: str
    confidence: float = 1.0
    
    @property
    def r(self) -> int:
        return self.rgb[0]
    
    @property
    def g(self) -> int:
        return self.rgb[1]
    
    @property
    def b(self) -> int:
        return self.rgb[2]
    
    @property
    def hsv(self) -> Tuple[float, float, float]:
        """Get HSV values (0-1 range)."""
        return colorsys.rgb_to_hsv(self.r/255, self.g/255, self.b/255)


@dataclass
class ColorPalette:
    """Color palette extracted from an image/element."""
    dominant: ColorInfo
    colors: List[ColorInfo]
    background: Optional[ColorInfo] = None
    foreground: Optional[ColorInfo] = None


# === Color Analyzer ===

class ColorAnalyzer:
    """
    Analyzes colors and their semantic meanings.
    
    Usage:
        analyzer = ColorAnalyzer()
        
        # Analyze a color value
        info = analyzer.analyze_rgb(255, 0, 0)
        print(info.name)      # ColorName.RED
        print(info.semantic)  # ColorSemantic.ERROR
        
        # Analyze from screen region
        palette = analyzer.analyze_region(100, 100, 50, 20)
        print(palette.dominant.name)
        
        # Check semantic meaning
        if analyzer.is_error_color(rgb):
            print("This is an error indicator")
    """
    
    # Color name ranges in HSV
    # Hue: 0-360 degrees, Saturation: 0-1, Value: 0-1
    COLOR_RANGES = {
        ColorName.RED: [(0, 20), (340, 360)],      # Red wraps around
        ColorName.ORANGE: [(20, 45)],
        ColorName.YELLOW: [(45, 70)],
        ColorName.GREEN: [(70, 165)],
        ColorName.CYAN: [(165, 200)],
        ColorName.BLUE: [(200, 260)],
        ColorName.PURPLE: [(260, 290)],
        ColorName.PINK: [(290, 340)],
    }
    
    # Semantic color mappings
    SEMANTIC_COLORS = {
        ColorSemantic.ERROR: [ColorName.RED],
        ColorSemantic.WARNING: [ColorName.YELLOW, ColorName.ORANGE],
        ColorSemantic.SUCCESS: [ColorName.GREEN],
        ColorSemantic.INFO: [ColorName.BLUE, ColorName.CYAN],
        ColorSemantic.LINK: [ColorName.BLUE],
        ColorSemantic.DISABLED: [ColorName.GRAY],
    }
    
    def __init__(self):
        pass
    
    def analyze_rgb(self, r: int, g: int, b: int) -> ColorInfo:
        """
        Analyze an RGB color value.
        
        Args:
            r, g, b: RGB values (0-255)
        
        Returns:
            ColorInfo with name and semantic meaning
        """
        rgb = (r, g, b)
        
        # Convert to HSV
        h, s, v = colorsys.rgb_to_hsv(r/255, g/255, b/255)
        hue_deg = h * 360
        
        # Determine color name
        name = self._get_color_name(hue_deg, s, v)
        
        # Determine semantic meaning
        semantic = self._get_semantic(name, s, v)
        
        # Generate hex
        hex_color = f"#{r:02x}{g:02x}{b:02x}"
        
        return ColorInfo(
            rgb=rgb,
            name=name,
            semantic=semantic,
            hex=hex_color,
        )
    
    def _get_color_name(self, hue: float, saturation: float, value: float) -> ColorName:
        """Determine color name from HSV values."""
        
        # Check for achromatic colors first (low saturation or value)
        if value < 0.15:
            return ColorName.BLACK
        if value > 0.85 and saturation < 0.15:
            return ColorName.WHITE
        if saturation < 0.15:
            return ColorName.GRAY
        
        # Check chromatic colors by hue
        for color_name, ranges in self.COLOR_RANGES.items():
            for hue_range in ranges:
                if hue_range[0] <= hue <= hue_range[1]:
                    return color_name
        
        return ColorName.UNKNOWN
    
    def _get_semantic(self, name: ColorName, saturation: float, value: float) -> ColorSemantic:
        """Determine semantic meaning from color name."""
        
        # Check if desaturated (disabled/inactive)
        if saturation < 0.3 and name not in [ColorName.BLACK, ColorName.WHITE, ColorName.GRAY]:
            return ColorSemantic.DISABLED
        
        # Map color to semantic
        for semantic, colors in self.SEMANTIC_COLORS.items():
            if name in colors:
                return semantic
        
        return ColorSemantic.NEUTRAL
    
    def analyze_hex(self, hex_color: str) -> ColorInfo:
        """Analyze a hex color string."""
        hex_color = hex_color.lstrip('#')
        
        if len(hex_color) == 3:
            hex_color = ''.join(c*2 for c in hex_color)
        
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        
        return self.analyze_rgb(r, g, b)
    
    def analyze_region(
        self, 
        x: int, 
        y: int, 
        width: int, 
        height: int
    ) -> Optional[ColorPalette]:
        """
        Analyze colors in a screen region.
        
        Args:
            x, y: Top-left corner
            width, height: Region size
        
        Returns:
            ColorPalette with dominant and all colors
        """
        if not HAS_PIL:
            return None
        
        try:
            # Capture region
            bbox = (x, y, x + width, y + height)
            image = ImageGrab.grab(bbox)
            
            return self.analyze_image(image)
            
        except Exception as e:
            logger.error(f"Region color analysis failed: {e}")
            return None
    
    def analyze_image(self, image: Any) -> Optional[ColorPalette]:
        """
        Analyze colors in an image.
        
        Args:
            image: PIL Image
        
        Returns:
            ColorPalette with color information
        """
        if not HAS_PIL:
            return None
        
        try:
            # Get average color
            img_small = image.resize((50, 50))  # Downscale for speed
            
            # Get dominant color via averaging
            stat = ImageStat.Stat(img_small)
            r, g, b = [int(x) for x in stat.mean[:3]]
            dominant = self.analyze_rgb(r, g, b)
            
            # Get color palette via quantization
            colors = []
            quantized = img_small.quantize(colors=8)
            palette = quantized.getpalette()
            
            if palette:
                for i in range(0, min(24, len(palette)), 3):
                    cr, cg, cb = palette[i], palette[i+1], palette[i+2]
                    colors.append(self.analyze_rgb(cr, cg, cb))
            
            # Guess background/foreground
            # Usually corners are background
            corners = [
                image.getpixel((0, 0)),
                image.getpixel((image.width-1, 0)),
                image.getpixel((0, image.height-1)),
                image.getpixel((image.width-1, image.height-1)),
            ]
            
            # Average corner colors for background
            avg_corner = tuple(sum(c[i] for c in corners) // 4 for i in range(3))
            background = self.analyze_rgb(*avg_corner[:3])
            
            # Foreground is usually contrasting with background
            center = image.getpixel((image.width//2, image.height//2))
            foreground = self.analyze_rgb(*center[:3])
            
            return ColorPalette(
                dominant=dominant,
                colors=colors,
                background=background,
                foreground=foreground,
            )
            
        except Exception as e:
            logger.error(f"Image color analysis failed: {e}")
            return None
    
    def is_error_color(self, rgb: Tuple[int, int, int]) -> bool:
        """Check if color indicates an error."""
        info = self.analyze_rgb(*rgb)
        return info.semantic == ColorSemantic.ERROR
    
    def is_warning_color(self, rgb: Tuple[int, int, int]) -> bool:
        """Check if color indicates a warning."""
        info = self.analyze_rgb(*rgb)
        return info.semantic == ColorSemantic.WARNING
    
    def is_success_color(self, rgb: Tuple[int, int, int]) -> bool:
        """Check if color indicates success."""
        info = self.analyze_rgb(*rgb)
        return info.semantic == ColorSemantic.SUCCESS
    
    def is_link_color(self, rgb: Tuple[int, int, int]) -> bool:
        """Check if color indicates a link."""
        info = self.analyze_rgb(*rgb)
        return info.name == ColorName.BLUE
    
    def is_disabled_color(self, rgb: Tuple[int, int, int]) -> bool:
        """Check if color indicates disabled state."""
        info = self.analyze_rgb(*rgb)
        return info.semantic == ColorSemantic.DISABLED or info.name == ColorName.GRAY
    
    def get_contrast_ratio(
        self, 
        color1: Tuple[int, int, int], 
        color2: Tuple[int, int, int]
    ) -> float:
        """
        Calculate contrast ratio between two colors.
        
        Returns:
            Contrast ratio (1 to 21)
        """
        def luminance(rgb):
            r, g, b = [x/255 for x in rgb]
            r = r/12.92 if r <= 0.03928 else ((r+0.055)/1.055)**2.4
            g = g/12.92 if g <= 0.03928 else ((g+0.055)/1.055)**2.4
            b = b/12.92 if b <= 0.03928 else ((b+0.055)/1.055)**2.4
            return 0.2126*r + 0.7152*g + 0.0722*b
        
        l1 = luminance(color1)
        l2 = luminance(color2)
        
        if l1 > l2:
            return (l1 + 0.05) / (l2 + 0.05)
        return (l2 + 0.05) / (l1 + 0.05)
    
    def is_high_contrast(
        self, 
        color1: Tuple[int, int, int], 
        color2: Tuple[int, int, int]
    ) -> bool:
        """Check if two colors have good contrast (WCAG AA standard)."""
        return self.get_contrast_ratio(color1, color2) >= 4.5
    
    def color_matches_query(self, rgb: Tuple[int, int, int], query: str) -> bool:
        """
        Check if a color matches a natural language query.
        
        Args:
            rgb: Color to check
            query: Natural language like "red", "error", "blue link"
        
        Returns:
            True if color matches
        """
        query_lower = query.lower()
        info = self.analyze_rgb(*rgb)
        
        # Check color name
        if info.name.value in query_lower:
            return True
        
        # Check semantic
        if info.semantic.value in query_lower:
            return True
        
        # Check aliases
        semantic_aliases = {
            "error": ColorSemantic.ERROR,
            "danger": ColorSemantic.ERROR,
            "critical": ColorSemantic.ERROR,
            "warning": ColorSemantic.WARNING,
            "caution": ColorSemantic.WARNING,
            "alert": ColorSemantic.WARNING,
            "success": ColorSemantic.SUCCESS,
            "ok": ColorSemantic.SUCCESS,
            "good": ColorSemantic.SUCCESS,
            "link": ColorSemantic.LINK,
            "disabled": ColorSemantic.DISABLED,
            "inactive": ColorSemantic.DISABLED,
        }
        
        for alias, semantic in semantic_aliases.items():
            if alias in query_lower and info.semantic == semantic:
                return True
        
        return False


# === Singleton ===

_color_analyzer: Optional[ColorAnalyzer] = None


def get_color_analyzer() -> ColorAnalyzer:
    """Get the global color analyzer instance."""
    global _color_analyzer
    if _color_analyzer is None:
        _color_analyzer = ColorAnalyzer()
    return _color_analyzer


# === Demo ===

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("VoxMind Color Analyzer")
    print("=" * 40)
    print(f"PIL available: {HAS_PIL}")
    print()
    
    analyzer = get_color_analyzer()
    
    # Test colors
    test_colors = [
        (255, 0, 0),      # Pure red
        (0, 255, 0),      # Pure green  
        (0, 0, 255),      # Pure blue
        (255, 165, 0),    # Orange
        (255, 255, 0),    # Yellow
        (128, 128, 128),  # Gray
        (200, 50, 50),    # Dark red (error)
        (50, 150, 50),    # Dark green (success)
        (100, 100, 200),  # Light blue (link)
    ]
    
    print("Color Analysis:")
    for rgb in test_colors:
        info = analyzer.analyze_rgb(*rgb)
        print(f"  RGB{rgb} -> {info.name.value:8} | {info.semantic.value:10} | {info.hex}")
    
    print()
    print("Semantic Checks:")
    print(f"  Red is error: {analyzer.is_error_color((255, 0, 0))}")
    print(f"  Green is success: {analyzer.is_success_color((0, 255, 0))}")
    print(f"  Blue is link: {analyzer.is_link_color((0, 0, 255))}")
    print(f"  Gray is disabled: {analyzer.is_disabled_color((128, 128, 128))}")
    
    print()
    print("Contrast Ratios:")
    print(f"  Black/White: {analyzer.get_contrast_ratio((0,0,0), (255,255,255)):.2f}")
    print(f"  Red/Green: {analyzer.get_contrast_ratio((255,0,0), (0,255,0)):.2f}")
