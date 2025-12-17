# Display Manager for Guitar Trainer

from config import Colors
from scaled_font import ScaledFont

try:
    import LibreBodoni48 as large_font
    HAS_FONT = True
except ImportError:
    print("Warning: LibreBodoni48 font not found, using scaled bitmap font")
    HAS_FONT = False
    large_font = None

class DisplayManager:
    """Manages all TFT display operations"""
    
    def __init__(self, tft):
        self.tft = tft
        # Set large font for the entire display if available
        if HAS_FONT and large_font:
            self.tft.set_font(large_font)
            print("Large font initialized")
        else:
            print("Using default font")
        Colors.initialize(tft)
        print(f"Colors initialized: WHITE={Colors.WHITE}, BLACK={Colors.BLACK}")
    
    def clear(self):
        """Clear the display"""
        self.tft.fill(Colors.BLACK)
    
    def show(self):
        """Update the display"""
        self.tft.show()
    
    def text(self, text, x, y, color=None):
        """Draw text on display - uses large font set at init"""
        if color is None:
            color = Colors.WHITE
        self.tft.text(text, x, y, color)
    
    def draw_large_text(self, text, x, y, color):
        """Draw large text using the font or scaled bitmap font as fallback"""
        if color is None:
            color = Colors.WHITE
        
        # Try to use draw_text if available (requires LibreBodoni48)
        if hasattr(self.tft, 'draw_text') and HAS_FONT:
            try:
                self.tft.draw_text(text, x, y, color)
                return
            except Exception:
                pass
        
        # Use scaled bitmap font for large readable text
        ScaledFont.draw_text(self.tft, text, x, y, color)
    
    def fill_rect(self, x, y, width, height, color):
        """Draw filled rectangle"""
        if color is None:
            color = Colors.WHITE
        self.tft.fill_rect(x, y, width, height, color)
    
    def rect(self, x, y, width, height, color):
        """Draw rectangle outline"""
        if color is None:
            color = Colors.WHITE
        self.tft.rect(x, y, width, height, color)
    
    def vline(self, x, y, length, color):
        """Draw vertical line"""
        if color is None:
            color = Colors.WHITE
        self.tft.vline(x, y, length, color)
    
    def line(self, x1, y1, x2, y2, color):
        """Draw line"""
        if color is None:
            color = Colors.WHITE
        self.tft.line(x1, y1, x2, y2, color)
    
    def pixel(self, x, y, color):
        """Set a single pixel"""
        if color is None:
            color = Colors.WHITE
        self.tft.pixel(x, y, color)
    
    def show_message(self, title, message, color=None):
        """Show a centered message"""
        if color is None:
            color = Colors.WHITE
        self.clear()
        self.text(title, 70, 100, Colors.YELLOW)
        self.text(message, 50, 120, color)
        self.show()
    
    def show_error(self, message):
        """Show an error message"""
        self.show_message("Error!", message, Colors.RED)
    
    def show_success(self, message):
        """Show a success message"""
        self.show_message("Success!", message, Colors.GREEN)
