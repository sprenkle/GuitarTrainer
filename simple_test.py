# Simple GC9A01 Test - Just colored rectangles
import machine
import time
from gc9a01 import GC9A01

# Pin definitions
SCK_PIN = 18
MOSI_PIN = 19
DC_PIN = 6
CS_PIN = 5
RST_PIN = 9

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

# Create display
display = GC9A01(spi, dc, cs, rst, width=240, height=240)

# Colors
BLACK = 0x0000
RED = 0xF800
GREEN = 0x07E0
BLUE = 0x001F
WHITE = 0xFFFF

print("Testing display...")

# Test 1: Full screen colors
print("1. Filling screen RED")
display.fill(RED)
time.sleep(1)

print("2. Filling screen GREEN")
display.fill(GREEN)
time.sleep(1)

print("3. Filling screen BLUE")
display.fill(BLUE)
time.sleep(1)

# Test 2: Simple rectangles
print("4. Drawing rectangles")
display.fill(BLACK)
display.fill_rect(50, 50, 50, 50, RED)
time.sleep(0.5)
display.fill_rect(140, 50, 50, 50, GREEN)
time.sleep(0.5)
display.fill_rect(50, 140, 50, 50, BLUE)
time.sleep(0.5)
display.fill_rect(140, 140, 50, 50, WHITE)
time.sleep(2)

# Test 3: Large centered box
print("5. Drawing large centered box")
display.fill(BLACK)
display.fill_rect(60, 60, 120, 120, WHITE)
time.sleep(2)

print("Test complete!")
display.fill(BLACK)
