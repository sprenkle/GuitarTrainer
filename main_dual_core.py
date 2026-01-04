# Main Entry Point - Dual Core Ready Version
# This version uses a SharedMIDIMessageQueue for inter-core communication
# BLE runs on CPU0 (asyncio requirement) but messages go into a thread-safe queue
# Other tasks/threads on CPU1 can safely read from the queue at their own pace

import asyncio
from machine import SPI, Pin
from gc9a01_spi_fb import GC9A01_SPI_FB
from guitar_trainer_app import GuitarTrainerApp
from ble_connection_dual_core import BLEConnectionManagerDualCore, SharedMIDIMessageQueue

async def main():
    """Initialize display and start the application with dual-core BLE"""
    
    # Create shared queue that will be used between CPU0 and CPU1
    shared_midi_queue = SharedMIDIMessageQueue(max_size=256)
    print("[CPU0] Created shared MIDI queue for inter-core communication")
    
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
    
    # Create BLE manager with shared queue
    app_ble = BLEConnectionManagerDualCore(None, shared_queue=shared_midi_queue)
    
    # Create app with dual-core BLE manager
    # Pass the BLE manager to the app so it uses the shared queue
    app = GuitarTrainerApp(tft, ble_manager=app_ble)
    
    # Set the display on the BLE manager after creating the app
    app_ble.display = app.display
    
    print("[CPU0] Application initialized with shared MIDI queue for inter-core communication")
    
    try:
        await app.run()
    except KeyboardInterrupt:
        print("[CPU0] Application interrupted")
    finally:
        await app.cleanup()
        print("[CPU0] Application stopped")

if __name__ == "__main__":
    asyncio.run(main())
