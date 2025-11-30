# MicroPython GC9A01 Countdown Demo
# Displays a countdown from 10 to 0 on the round display

import machine
import time
from gc9a01 import GC9A01

# Pin definitions - adjust these to match your wiring
SCK_PIN = 18   # SPI Clock
MOSI_PIN = 19  # SPI MOSI
DC_PIN = 6     # Data/Command
CS_PIN = 5     # Chip Select
RST_PIN = 9    # Reset

# Initialize SPI
spi = machine.SPI(0, 
                  baudrate=40000000,
                  polarity=0, 
                  phase=0,
                  sck=machine.Pin(SCK_PIN), 
                  mosi=machine.Pin(MOSI_PIN))

# Initialize pins
dc = machine.Pin(DC_PIN)
cs = machine.Pin(CS_PIN)
rst = machine.Pin(RST_PIN)

# Create display instance
display = GC9A01(spi, dc, cs, rst, width=240, height=240)

# Define colors (RGB565 format)
BLACK = 0x0000
RED = 0xF800
GREEN = 0x07E0
BLUE = 0x001F
CYAN = 0x07FF
YELLOW = 0xFFE0
WHITE = 0xFFFF

print("GC9A01 Countdown Demo Starting...")

# Simple large block-style digit patterns
def draw_digit(digit, x_center, y_center, color):
    """Draw a large digit using simple filled rectangles"""
    
    # Digit patterns as 5x7 grid (scaled up)
    patterns = {
        0: [[1,1,1,1,1],
            [1,0,0,0,1],
            [1,0,0,0,1],
            [1,0,0,0,1],
            [1,0,0,0,1],
            [1,0,0,0,1],
            [1,1,1,1,1]],
        
        1: [[0,0,1,0,0],
            [0,1,1,0,0],
            [0,0,1,0,0],
            [0,0,1,0,0],
            [0,0,1,0,0],
            [0,0,1,0,0],
            [1,1,1,1,1]],
        
        2: [[1,1,1,1,1],
            [0,0,0,0,1],
            [0,0,0,0,1],
            [1,1,1,1,1],
            [1,0,0,0,0],
            [1,0,0,0,0],
            [1,1,1,1,1]],
        
        3: [[1,1,1,1,1],
            [0,0,0,0,1],
            [0,0,0,0,1],
            [1,1,1,1,1],
            [0,0,0,0,1],
            [0,0,0,0,1],
            [1,1,1,1,1]],
        
        4: [[1,0,0,0,1],
            [1,0,0,0,1],
            [1,0,0,0,1],
            [1,1,1,1,1],
            [0,0,0,0,1],
            [0,0,0,0,1],
            [0,0,0,0,1]],
        
        5: [[1,1,1,1,1],
            [1,0,0,0,0],
            [1,0,0,0,0],
            [1,1,1,1,1],
            [0,0,0,0,1],
            [0,0,0,0,1],
            [1,1,1,1,1]],
        
        6: [[1,1,1,1,1],
            [1,0,0,0,0],
            [1,0,0,0,0],
            [1,1,1,1,1],
            [1,0,0,0,1],
            [1,0,0,0,1],
            [1,1,1,1,1]],
        
        7: [[1,1,1,1,1],
            [0,0,0,0,1],
            [0,0,0,0,1],
            [0,0,0,0,1],
            [0,0,0,0,1],
            [0,0,0,0,1],
            [0,0,0,0,1]],
        
        8: [[1,1,1,1,1],
            [1,0,0,0,1],
            [1,0,0,0,1],
            [1,1,1,1,1],
            [1,0,0,0,1],
            [1,0,0,0,1],
            [1,1,1,1,1]],
        
        9: [[1,1,1,1,1],
            [1,0,0,0,1],
            [1,0,0,0,1],
            [1,1,1,1,1],
            [0,0,0,0,1],
            [0,0,0,0,1],
            [1,1,1,1,1]],
        
        10: [[1,0,1,1,1],  # "10" special case
             [1,0,1,0,1],
             [1,0,1,0,1],
             [1,0,1,0,1],
             [1,0,1,0,1],
             [1,0,1,0,1],
             [1,0,1,1,1]]
    }
    
    if digit not in patterns:
        return
    
    pattern = patterns[digit]
    pixel_size = 12  # Size of each "pixel" in the digit
    
    # Calculate dimensions
    width = len(pattern[0]) * pixel_size
    height = len(pattern) * pixel_size
    
    # Calculate top-left position to center the digit
    x_start = x_center - width // 2
    y_start = y_center - height // 2
    
    # Draw the digit
    for row_idx, row in enumerate(pattern):
        for col_idx, pixel in enumerate(row):
            if pixel == 1:
                x = x_start + col_idx * pixel_size
                y = y_start + row_idx * pixel_size
                display.fill_rect(x, y, pixel_size, pixel_size, color)

# Countdown loop
for count in range(10, -1, -1):
    # Clear screen
    display.fill(BLACK)
    
    # Choose color based on count
    if count > 5:
        digit_color = GREEN
    elif count > 2:
        digit_color = YELLOW
    else:
        digit_color = RED
    
    # Draw the digit centered on screen
    print(f"Countdown: {count}")
    draw_digit(count, 120, 120, digit_color)  # Center at (120, 120)
    
    # Wait 1 second
    time.sleep(1)

# Final screen - show "DONE" effect
print("Countdown complete!")
for _ in range(5):
    display.fill(GREEN)
    time.sleep(0.2)
    display.fill(BLACK)
    time.sleep(0.2)

display.fill(BLACK)
print("Demo finished!")
