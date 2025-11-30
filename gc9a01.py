"""
CircuitPython GC9A01 Driver
240x240 Round LCD Display Driver for Raspberry Pi Pico

VCC → 3.3V (pin 36)
GND → GND (any ground pin, e.g., pin 38)
SCK → GP18 (pin 24) - SPI Clock
MOSI/SDA → GP19 (pin 25) - SPI Data
DC → GP6 (pin 9) - Data/Command
CS → GP5 (pin 7) - Chip Select
RST → GP9 (pin 12) - Reset
BL → 3.3V (or a GPIO if you want PWM backlight control)
"""

import time
import struct# GC9A01 Commands
_SWRESET = const(0x01)
_SLPOUT = const(0x11)
_INVON = const(0x21)
_DISPON = const(0x29)
_CASET = const(0x2A)
_RASET = const(0x2B)
_RAMWR = const(0x2C)
_MADCTL = const(0x36)
_COLMOD = const(0x3A)

# Color modes
COLOR_MODE_65K = const(0x50)
COLOR_MODE_262K = const(0x60)
COLOR_MODE_12BIT = const(0x03)
COLOR_MODE_16BIT = const(0x05)
COLOR_MODE_18BIT = const(0x06)


class GC9A01:
    """GC9A01 240x240 Round LCD Display Driver for CircuitPython"""
    
    def __init__(self, spi, dc, cs, rst=None, width=240, height=240, rotation=0):
        """
        Initialize GC9A01 display driver
        
        Args:
            spi: SPI bus instance
            dc: Data/Command pin
            cs: Chip Select pin
            rst: Reset pin (optional)
            width: Display width (default 240)
            height: Display height (default 240)
            rotation: Display rotation 0-3 (default 0)
        """
        self.spi = spi
        self.dc = dc
        self.cs = cs
        self.rst = rst
        self.width = width
        self.height = height
        self.rotation = rotation
        
        # Pins should already be initialized as DigitalInOut with direction set
        # Just set initial values
        self.dc.value = False
        self.cs.value = True
        if self.rst:
            self.rst.value = True
        
        # Reset and initialize display
        self.reset()
        self.init_display()
        
    def reset(self):
        """Hardware reset the display"""
        if self.rst:
            self.rst.value = True
            time.sleep(0.01)
            self.rst.value = False
            time.sleep(0.01)
            self.rst.value = True
            time.sleep(0.12)
    
    def write_cmd(self, cmd):
        """Write command to display"""
        self.cs.value = False
        self.dc.value = False
        while not self.spi.try_lock():
            pass
        self.spi.write(bytes([cmd]))
        self.spi.unlock()
        self.cs.value = True
    
    def write_data(self, data):
        """Write data to display"""
        self.cs.value = False
        self.dc.value = True
        while not self.spi.try_lock():
            pass
        if isinstance(data, int):
            self.spi.write(bytes([data]))
        else:
            self.spi.write(data)
        self.spi.unlock()
        self.cs.value = True
    
    def init_display(self):
        """Initialize display with command sequence"""
        # Inter Register Enable1
        self.write_cmd(0xFE)
        # Inter Register Enable2
        self.write_cmd(0xEF)
        
        # Display Function Control
        self.write_cmd(0xB6)
        self.write_data(bytes([0x00, 0x00]))
        
        # Memory Access Control
        self.write_cmd(_MADCTL)
        self.write_data(0x48)
        
        # Pixel Format Set - 16 bits/pixel
        self.write_cmd(_COLMOD)
        self.write_data(COLOR_MODE_16BIT)
        
        # Power Control 2
        self.write_cmd(0xC3)
        self.write_data(0x13)
        
        # Power Control 3
        self.write_cmd(0xC4)
        self.write_data(0x13)
        
        # Power Control 4
        self.write_cmd(0xC9)
        self.write_data(0x22)
        
        # Gamma Set 1
        self.write_cmd(0xF0)
        self.write_data(bytes([0x45, 0x09, 0x08, 0x08, 0x26, 0x2a]))
        
        # Gamma Set 2
        self.write_cmd(0xF1)
        self.write_data(bytes([0x43, 0x70, 0x72, 0x36, 0x37, 0x6f]))
        
        # Gamma Set 3
        self.write_cmd(0xF2)
        self.write_data(bytes([0x45, 0x09, 0x08, 0x08, 0x26, 0x2a]))
        
        # Gamma Set 4
        self.write_cmd(0xF3)
        self.write_data(bytes([0x43, 0x70, 0x72, 0x36, 0x37, 0x6f]))
        
        # Display Inversion ON
        self.write_cmd(_INVON)
        
        # Sleep Out
        self.write_cmd(_SLPOUT)
        time.sleep(0.12)
        
        # Display ON
        self.write_cmd(_DISPON)
        time.sleep(0.02)
    
    def set_window(self, x0, y0, x1, y1):
        """Set the display window"""
        # Column Address Set
        self.cs.value = False
        self.dc.value = False
        while not self.spi.try_lock():
            pass
        self.spi.write(bytes([_CASET]))
        self.dc.value = True
        self.spi.write(struct.pack('>HH', x0, x1))
        self.spi.unlock()
        self.cs.value = True
        
        # Row Address Set  
        self.cs.value = False
        self.dc.value = False
        while not self.spi.try_lock():
            pass
        self.spi.write(bytes([_RASET]))
        self.dc.value = True
        self.spi.write(struct.pack('>HH', y0, y1))
        self.spi.unlock()
        self.cs.value = True
        
        # Memory Write - leave CS low, caller will handle data and CS
        self.cs.value = False
        self.dc.value = False
        while not self.spi.try_lock():
            pass
        self.spi.write(bytes([_RAMWR]))
        self.dc.value = True
        # Note: CS stays LOW and SPI stays locked for subsequent data writes
    
    def fill(self, color):
        """Fill entire screen with color (RGB565 format)"""
        self.set_window(0, 0, self.width - 1, self.height - 1)
        # CS is already low from set_window
        
        # Create a buffer with repeated color for efficiency
        color_bytes = struct.pack('>H', color)
        chunk_size = 512
        buffer = color_bytes * chunk_size
        
        total_pixels = self.width * self.height
        full_chunks = total_pixels // chunk_size
        remainder = total_pixels % chunk_size
        
        # Write full chunks (CS already low, DC already high, SPI locked)
        for _ in range(full_chunks):
            self.spi.write(buffer)
        
        # Write remaining pixels
        if remainder > 0:
            self.spi.write(color_bytes * remainder)
        
        self.spi.unlock()
        self.cs.value = True  # Done, raise CS
    
    def pixel(self, x, y, color):
        """Set a single pixel to color (RGB565 format)"""
        if 0 <= x < self.width and 0 <= y < self.height:
            self.set_window(x, y, x, y)
            # CS is already low from set_window, DC is already high, SPI locked
            color_bytes = struct.pack('>H', color)
            self.spi.write(color_bytes)
            self.spi.unlock()
            self.cs.value = True  # Done, raise CS
    
    def fill_rect(self, x, y, w, h, color):
        """Fill a rectangle with color (RGB565 format)"""
        x1 = min(x + w - 1, self.width - 1)
        y1 = min(y + h - 1, self.height - 1)
        
        if x1 < x or y1 < y:
            return
            
        self.set_window(x, y, x1, y1)
        # CS is already low from set_window, DC is already high
        
        # Create a buffer with the color repeated
        pixels = (x1 - x + 1) * (y1 - y + 1)
        color_bytes = struct.pack('>H', color)
        
        # Send data in chunks for better performance
        chunk_size = 256
        buffer = color_bytes * chunk_size
        
        # Write full chunks
        full_chunks = pixels // chunk_size
        for _ in range(full_chunks):
            self.spi.write(buffer)
        
        # Write remaining pixels
        remainder = pixels % chunk_size
        if remainder > 0:
            self.spi.write(color_bytes * remainder)
        
        self.spi.unlock()
        self.cs.value = True  # Done, raise CS
    
    def blit_buffer(self, buffer, x, y, w, h):
        """Write a buffer to display area"""
        self.set_window(x, y, x + w - 1, y + h - 1)
        self.write_data(buffer)
    
    @staticmethod
    def color565(r, g, b):
        """Convert RGB888 to RGB565"""
        return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
