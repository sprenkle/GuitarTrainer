# Minimal display test
import asyncio
from machine import SPI, Pin
from gc9a01_spi_fb import GC9A01_SPI_FB
import LibreBodoni48 as large_font

async def test_display():
    """Test display directly"""
    print("Initializing SPI...")
    spi = SPI(0, baudrate=40_000_000, sck=Pin(18), mosi=Pin(19))
    
    print("Initializing display...")
    tft = GC9A01_SPI_FB(
        spi=spi,
        cs_pin=5,
        dc_pin=6,
        rst_pin=9,
        blk_pin=None
    )
    
    print("Setting rotation...")
    tft.set_rotation(0)
    
    print("Setting font...")
    tft.set_font(large_font)
    
    print("Clearing display...")
    BLACK = tft.color565(0, 0, 0)
    YELLOW = tft.color565(255, 255, 0)
    WHITE = tft.color565(255, 255, 255)
    tft.fill(BLACK)
    
    print("Drawing text...")
    tft.draw_text("Test Display", 80, 100, YELLOW)
    tft.draw_text("Menu Test", 100, 120, WHITE)
    
    print("Calling show()...")
    tft.show()
    
    print("Done! Check display for text.")
    await asyncio.sleep(10)

if __name__ == "__main__":
    asyncio.run(test_display())
