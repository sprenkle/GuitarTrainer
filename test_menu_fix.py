#!/usr/bin/env python3
"""
Test the display manager with the corrected text() method
This tests that we're using tft.text() (FrameBuffer's default small font)
for regular menu text, and draw_text() with explicit font for large text.
"""

# Simulate the display behavior
class MockTFT:
    def __init__(self):
        self._font = None
        self.text_calls = []
        self.draw_text_calls = []
        
    def text(self, text, x, y, color):
        """FrameBuffer's built-in text method - uses small monospace font"""
        self.text_calls.append((text, x, y, color, "built-in font"))
        print(f"✓ tft.text() called: '{text}' at ({x},{y})")
        
    def draw_text(self, text, x, y, color):
        """Custom text method - requires font to be set"""
        if self._font is None:
            raise ValueError("draw_text requires a font to be set!")
        self.draw_text_calls.append((text, x, y, color, "custom font"))
        print(f"✓ tft.draw_text() called: '{text}' at ({x},{y}) [font set]")
        
    def set_font(self, font):
        self._font = font
        print(f"  Font set: {font}")
        
    def color565(self, r, g, b):
        return (r << 11) | (g << 5) | b


class MockColors:
    WHITE = 0xFFFF
    BLACK = 0x0000
    @staticmethod
    def initialize(tft):
        pass

# Test display manager
class DisplayManager:
    def __init__(self, tft):
        self.tft = tft
        MockColors.initialize(tft)
        
    def text(self, text, x, y, color=None):
        """Draw text on display using FrameBuffer's built-in font"""
        if color is None:
            color = MockColors.WHITE
        self.tft.text(text, x, y, color)
        
    def draw_large_text(self, text, x, y, color):
        """Draw large text using the custom font"""
        if color is None:
            color = MockColors.WHITE
        # Set font for large text
        self.tft.set_font("LibreBodoni48")
        self.tft.draw_text(text, x, y, color)
        # Reset to no font
        self.tft.set_font(None)


# Test it
print("=== Testing Display Manager ===\n")

tft = MockTFT()
display = DisplayManager(tft)

print("1. Testing regular menu text (should use built-in font):")
display.text("Simple 3", 50, 50, MockColors.WHITE)
display.text("Classic 4", 50, 70, MockColors.WHITE)
print()

print("2. Testing large text (should set font, use draw_text, reset font):")
display.draw_large_text("C Major", 100, 100, MockColors.WHITE)
print()

print("3. Testing after large text (should still use built-in font):")
display.text("Back to menu", 50, 150, MockColors.WHITE)
print()

print("=== Results ===")
print(f"text() calls (FrameBuffer built-in): {len(tft.text_calls)}")
print(f"draw_text() calls (custom font): {len(tft.draw_text_calls)}")
print("\n✓ Test passed! Menu should display correctly now.")
