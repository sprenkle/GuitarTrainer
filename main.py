# Auto-start Guitar Chord Trainer on boot
import utime
utime.sleep_ms(500)  # Give system time to stabilize

print("Starting Chord Trainer...")

# Clean up any stale BLE state
try:
    import bluetooth
    bt = bluetooth.BLE()
    bt.active(False)
    print("BLE cleaned up")
except:
    pass

try:
    import network
    wlan = network.WLAN(network.STA_IF)
    wlan.active(False)
    utime.sleep_ms(500)
    print("WLAN deactivated")
except:
    pass

# Wait before starting
utime.sleep_ms(1000)

# Import and run the chord trainer
try:
    exec(open('guitar_trainer_chords.py').read())
except Exception as e:
    print(f"Failed to start: {e}")
    import sys
    sys.print_exception(e)
    # Show error on display
    try:
        from gc9a01_spi_fb import GC9A01_SPI_FB
        from machine import SPI, Pin
        
        spi = SPI(0, baudrate=40_000_000, sck=Pin(18), mosi=Pin(19))
        tft = GC9A01_SPI_FB(spi, 5, 6, 9, None)
        tft.fill(0)
        tft.text("Startup Error!", 60, 100, 0xF800)
        tft.text(str(e)[:20], 40, 120, 0xFFFF)
        tft.show()
    except:
        pass
