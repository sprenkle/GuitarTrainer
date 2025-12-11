# Main Entry Point - Refactored Modular Version

import asyncio
from machine import SPI, Pin
from gc9a01_spi_fb import GC9A01_SPI_FB
from guitar_trainer_app import GuitarTrainerApp

async def main():
    """Initialize display and start the application"""
    
    # Initialize SPI
    spi = SPI(0, baudrate=40_000_000, sck=Pin(18), mosi=Pin(19))
    
    # Initialize display
    tft = GC9A01_SPI_FB(
        spi=spi,
        cs_pin=5,
        dc_pin=6,
        rst_pin=9,
        blk_pin=None
    )
    
    # Set rotation
    tft.set_rotation(0)
    
    # Create and run app
    app = GuitarTrainerApp(tft)
    
    try:
        await app.run()
    except KeyboardInterrupt:
        print("Application interrupted")
    finally:
        await app.cleanup()
        print("Application stopped")

if __name__ == "__main__":
    asyncio.run(main())
