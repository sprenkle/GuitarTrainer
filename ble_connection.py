# BLE Connection Manager

import asyncio
import aioble
import network
from config import MIDI_SERVICE_UUID, MIDI_CHAR_UUID

class BLEConnectionManager:
    """Manages BLE connections to MIDI devices"""
    
    def __init__(self, display_manager):
        self.display = display_manager
        self.connection = None
        self.midi_characteristic = None
        self.connected = False
    
    async def scan_and_connect(self, timeout_ms=5000):
        """Scan for and connect to Aeroband guitar"""
        self.display.clear()
        self.display.text("Scanning for", 70, 100)
        self.display.text("Aeroband...", 75, 120)
        self.display.show()
        
        print("Initializing Bluetooth...")
        
        # Disable WLAN to allow BLE to work
        try:
            wlan = network.WLAN(network.STA_IF)
            if wlan.active():
                print("Disabling WLAN for BLE...")
                wlan.active(False)
                await asyncio.sleep(0.5)
        except Exception as e:
            print(f"WLAN disable warning: {e}")
        
        self.display.clear()
        self.display.text("Scanning for", 70, 100)
        self.display.text("Aeroband...", 75, 120)
        self.display.show()
        
        print("Scanning for Aeroband guitar...")
        
        found_count = 0
        try:
            print("Entering scan context...")
            async with aioble.scan(timeout_ms, interval_us=30000, window_us=30000, active=True) as scanner:
                print("Scan started, waiting for devices...")
                async for result in scanner:
                    found_count += 1
                    name = result.name()
                    print(f"Found device #{found_count}: {name}")
                    
                    has_midi_service = MIDI_SERVICE_UUID in result.services()
                    has_aeroband_name = name and ("aeroband" in name.lower() or "pocketdrum" in name.lower() or "midi" in name.lower())
                    
                    if has_midi_service or has_aeroband_name:
                        print(f"Connecting to: {name}")
                        
                        try:
                            self.display.clear()
                            self.display.text("Connecting...", 70, 120)
                            self.display.show()
                            
                            print("Connecting...")
                            self.connection = await result.device.connect()
                            print("Connected!")
                            
                            print("Discovering services...")
                            midi_service = await self.connection.service(MIDI_SERVICE_UUID)
                            
                            if midi_service is None:
                                print("MIDI service not found")
                                await self.connection.disconnect()
                                continue
                            
                            print("Getting MIDI characteristic...")
                            self.midi_characteristic = await midi_service.characteristic(MIDI_CHAR_UUID)
                            
                            if self.midi_characteristic is None:
                                print("MIDI characteristic not found")
                                await self.connection.disconnect()
                                continue
                            
                            # Subscribe to notifications
                            print("Subscribing to MIDI notifications...")
                            try:
                                await self.midi_characteristic.subscribe(notify=True)
                                print("Successfully subscribed to notifications")
                            except Exception as e:
                                print(f"Failed to subscribe: {e}")
                            
                            self.connected = True
                            
                            self.display.clear()
                            self.display.text("Connected!", 75, 110)
                            self.display.show()
                            await asyncio.sleep(1)
                            
                            print("MIDI service ready!")
                            return True
                            
                        except Exception as e:
                            print(f"Connection failed: {e}")
                            if self.connection:
                                try:
                                    await self.connection.disconnect()
                                except:
                                    pass
                            continue
        
        except Exception as e:
            print(f"Scan failed: {e}")
            # Note: traceback module not available in MicroPython
        
        print(f"Scan completed. Found {found_count} devices total")
        print("Aeroband guitar not found")
        return False
    
    async def disconnect(self):
        """Disconnect from device"""
        if self.connection:
            try:
                await self.connection.disconnect()
            except:
                pass
            self.connected = False
            self.midi_characteristic = None
    
    async def wait_for_midi(self, timeout=0.5):
        """Wait for MIDI data with timeout"""
        if not self.midi_characteristic:
            print("DEBUG BLE: midi_characteristic not set!")
            raise RuntimeError("Not connected to MIDI device")
        
        try:
            data = await asyncio.wait_for(self.midi_characteristic.notified(), timeout=timeout)
            #print(f"DEBUG BLE: Received notification: {data}")
            return data
        except asyncio.TimeoutError:
            #print(f"DEBUG BLE: Wait timeout")
            return None
