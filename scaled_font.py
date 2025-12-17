"""
Simple scaled bitmap font for readable chord display
Renders text at a large, readable size without external font files
"""

class ScaledFont:
    """Renders text using scaled bitmap font (approximately 20+ pixels tall)"""
    
    # Simple 5x7 character patterns
    CHAR_MAP = {
        'A': [0b01110, 0b10001, 0b11111, 0b10001, 0b10001],
        'B': [0b11110, 0b10001, 0b11110, 0b10001, 0b11110],
        'C': [0b01110, 0b10000, 0b10000, 0b10000, 0b01110],
        'D': [0b11110, 0b10001, 0b10001, 0b10001, 0b11110],
        'E': [0b11111, 0b10000, 0b11100, 0b10000, 0b11111],
        'F': [0b11111, 0b10000, 0b11100, 0b10000, 0b10000],
        'G': [0b01110, 0b10000, 0b10011, 0b10001, 0b01110],
        'M': [0b10001, 0b11011, 0b10101, 0b10001, 0b10001],
        'N': [0b10001, 0b11001, 0b10101, 0b10011, 0b10001],
        'O': [0b01110, 0b10001, 0b10001, 0b10001, 0b01110],
        '0': [0b01110, 0b10001, 0b10001, 0b10001, 0b01110],
        '1': [0b00100, 0b01100, 0b00100, 0b00100, 0b01110],
        '2': [0b01110, 0b10001, 0b00010, 0b00100, 0b11111],
        '3': [0b11110, 0b00001, 0b00110, 0b10001, 0b01110],
        '4': [0b10010, 0b10010, 0b11111, 0b00010, 0b00010],
        '5': [0b11111, 0b10000, 0b11110, 0b00001, 0b11110],
        '6': [0b01110, 0b10000, 0b11110, 0b10001, 0b01110],
        '7': [0b11111, 0b00001, 0b00010, 0b00100, 0b01000],
        '8': [0b01110, 0b10001, 0b01110, 0b10001, 0b01110],
        '9': [0b01110, 0b10001, 0b01111, 0b00001, 0b01110],
        ' ': [0b00000, 0b00000, 0b00000, 0b00000, 0b00000],
        '.': [0b00000, 0b00000, 0b00000, 0b00000, 0b01110],
        ',': [0b00000, 0b00000, 0b00000, 0b00100, 0b01000],
        ':': [0b00000, 0b01110, 0b00000, 0b01110, 0b00000],
        '-': [0b00000, 0b00000, 0b11111, 0b00000, 0b00000],
        '!': [0b00100, 0b00100, 0b00100, 0b00000, 0b00100],
        '/': [0b00001, 0b00010, 0b00100, 0b01000, 0b10000],
        '#': [0b01010, 0b11111, 0b01010, 0b11111, 0b01010],
    }
    
    # Scale factor - controls size of each pixel
    SCALE = 6
    
    @staticmethod
    def draw_text(tft, text, x, y, color):
        """Draw text at large size"""
        current_x = x
        for char in text:
            char_upper = char.upper()
            if char_upper not in ScaledFont.CHAR_MAP:
                char_upper = ' '
            
            pattern = ScaledFont.CHAR_MAP[char_upper]
            scale = ScaledFont.SCALE
            
            # Draw each row of the character
            for row_idx, row_bits in enumerate(pattern):
                for col_idx in range(5):
                    # Check if this pixel should be drawn
                    if row_bits & (1 << (4 - col_idx)):
                        # Draw scaled pixel
                        tft.fill_rect(
                            current_x + col_idx * scale,
                            y + row_idx * scale,
                            scale,
                            scale,
                            color
                        )
            
            # Move to next character position
            current_x += 5 * scale + scale  # 5 pixels wide + 1 pixel spacing
