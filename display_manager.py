# Display Manager for Guitar Trainer

from config import Colors
import LibreBodoni48 as large_font

class DisplayManager:
    """Manages all TFT display operations"""
    
    def __init__(self, tft):
        self.tft = tft
        # Use built-in font by default (don't set a custom font)
        # Large font will be set when needed for special displays
        Colors.initialize(tft)
        print(f"Colors initialized: WHITE={Colors.WHITE}, BLACK={Colors.BLACK}")
    
    def clear(self):
        """Clear the display"""
        print("Calling clear()...")
        try:
            self.tft.fill(Colors.BLACK)
            print("clear() successful")
        except Exception as e:
            print(f"clear() error: {e}")
    
    def show(self):
        """Update the display"""
        print(f"Calling display.show()...")
        try:
            self.tft.show()
            print("show() successful")
        except Exception as e:
            print(f"show() error: {e}")
            import traceback
            traceback.print_exc()
    
    def text(self, text, x, y, color=None):
        """Draw text on display"""
        if color is None:
            color = Colors.WHITE
        if color is None:
            print(f"WARNING: Color is None for text '{text}'")
        else:
            self.tft.text(text, x, y, color)
    
    def draw_large_text(self, text, x, y, color):
        """Draw large text using the font"""
        if color is None:
            color = Colors.WHITE
        # Set font for large text
        self.tft.set_font(large_font)
        self.tft.draw_text(text, x, y, color)
        # Reset to no font (for regular FrameBuffer text)
        self.tft.set_font(None)
    
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
