# CircuitPython GC9A01 Test
# 240x240 Round LCD Display Test for Raspberry Pi Pico

import board
import busio
import time
from gc9a01 import GC9A01
import digitalio

# Pin definitions - adjust these to match your wiring
# Using CircuitPython board pin names
SCK_PIN = board.GP18   # SPI Clock
MOSI_PIN = board.GP19  # SPI MOSI
DC_PIN = board.GP6     # Data/Command
CS_PIN = board.GP5     # Chip Select
RST_PIN = board.GP9   # Reset

# Initialize SPI
spi = busio.SPI(SCK_PIN, MOSI=MOSI_PIN)

# Initialize pins
dc = digitalio.DigitalInOut(DC_PIN)
dc.direction = digitalio.Direction.OUTPUT
cs = digitalio.DigitalInOut(CS_PIN)
cs.direction = digitalio.Direction.OUTPUT
rst = digitalio.DigitalInOut(RST_PIN)
rst.direction = digitalio.Direction.OUTPUT

# Create display instance
display = GC9A01(spi, dc, cs, rst, width=240, height=240)

print("GC9A01 Display Initialized!")
print("Running color test...")

# Define some colors (RGB565 format)
BLACK = 0x0000
RED = 0xF800
GREEN = 0x07E0
BLUE = 0x001F
CYAN = 0x07FF
MAGENTA = 0xF81F
YELLOW = 0xFFE0
WHITE = 0xFFFF

# Test 1: Fill screen with colors
colors = [RED, GREEN, BLUE, CYAN, MAGENTA, YELLOW, WHITE, BLACK]
color_names = ["Red", "Green", "Blue", "Cyan", "Magenta", "Yellow", "White", "Black"]

# for color, name in zip(colors, color_names):
#     print(f"Filling screen with {name}...")
#     display.fill(color)
#     time.sleep(1)

# Test 2: Draw rectangles
print("Drawing rectangles...")
display.fill(BLACK)
display.fill_rect(20, 20, 60, 60, RED)
display.fill_rect(80, 20, 60, 60, GREEN)
display.fill_rect(160, 20, 60, 60, BLUE)
display.fill_rect(20, 100, 60, 60, YELLOW)
display.fill_rect(80, 100, 60, 60, CYAN)
display.fill_rect(160, 100, 60, 60, MAGENTA)
time.sleep(2)

# Test 3: Draw pixels
print("Drawing random pixels...")
display.fill(BLACK)
import random
for x in range(240):
    # x = random.randint(0, 239)
    y = random.randint(0, 239)
    color = random.randint(0, 0xFFFF)
    display.pixel(x, y, color)
time.sleep(2)

# # Test 4: Color gradient
# print("Drawing gradient...")
# for y in range(240):
#     color = display.color565(y, 255 - y, 128)
#     display.fill_rect(0, y, 240, 1, color)
# time.sleep(8)

print("Test complete!")
display.fill(BLACK)
