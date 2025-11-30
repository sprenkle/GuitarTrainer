# Debug test - single rectangle with detailed output
import machine
import time
import struct
from gc9a01 import GC9A01

# Pin definitions
SCK_PIN = 18
MOSI_PIN = 19
DC_PIN = 6
CS_PIN = 5
RST_PIN = 9

# Initialize SPI
spi = machine.SPI(0, 
                  baudrate=10000000,  # Slower for debugging
                  polarity=0, 
                  phase=0,
                  sck=machine.Pin(SCK_PIN), 
                  mosi=machine.Pin(MOSI_PIN))

dc = machine.Pin(DC_PIN)
cs = machine.Pin(CS_PIN)
rst = machine.Pin(RST_PIN)

display = GC9A01(spi, dc, cs, rst, width=240, height=240)

RED = 0xF800
GREEN = 0x07E0
BLUE = 0x001F
BLACK = 0x0000

print("Filling screen BLACK...")
display.fill(BLACK)
time.sleep(1)

print("\nTest 1: Draw a 100x100 RED square at (70, 70)")
print("This should appear as a centered square, not lines")
display.fill_rect(70, 70, 100, 100, RED)
time.sleep(3)

print("\nTest 2: Draw 4 corner rectangles")
display.fill(BLACK)
time.sleep(0.5)

print("Top-left corner: 40x40 RED at (10, 10)")
display.fill_rect(10, 10, 40, 40, RED)
time.sleep(0.5)

print("Top-right corner: 40x40 GREEN at (190, 10)")
display.fill_rect(190, 10, 40, 40, GREEN)
time.sleep(0.5)

print("Bottom-left corner: 40x40 BLUE at (10, 190)")
display.fill_rect(10, 190, 40, 40, BLUE)
time.sleep(0.5)

print("Bottom-right corner: 40x40 RED at (190, 190)")
display.fill_rect(190, 190, 40, 40, RED)
time.sleep(3)

print("\nIf you see vertical lines instead of squares,")
print("the issue is likely with:")
print("1. MADCTL setting (memory access control)")
print("2. Column/Row address order")
print("3. Display orientation")

print("\nTrying different MADCTL value...")
display.write_cmd(0x36)  # MADCTL
display.write_data(0x00)  # Try different rotation
time.sleep(1)

display.fill(BLACK)
time.sleep(0.5)
display.fill_rect(70, 70, 100, 100, GREEN)
time.sleep(2)

print("Did that fix it? If not, there may be a hardware issue.")
