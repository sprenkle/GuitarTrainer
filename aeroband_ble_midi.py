# The MIT License (MIT)
# Aeroband Guitar BLE MIDI Receiver for Raspberry Pi Pico W
# Receives MIDI data via Bluetooth Low Energy and plays tones through I2S

import asyncio
import aioble
import bluetooth
import struct
import math
import network
from machine import I2S, Pin
from micropython import const

# BLE MIDI Service and Characteristic UUIDs
_MIDI_SERVICE_UUID = bluetooth.UUID("03B80E5A-EDE8-4B33-A751-6CE34EC4C700")
_MIDI_CHAR_UUID = bluetooth.UUID("7772E5DB-3868-4112-A1A9-F2669D106BF3")

# MIDI Note to Frequency conversion (A4 = 440Hz)
def midi_note_to_frequency(note):
    """Convert MIDI note number to frequency in Hz"""
    return 440.0 * pow(2.0, (note - 69) / 12.0)

class AerobandBLEMIDI:
    """
    Class to handle BLE MIDI connection from Aeroband guitar
    and trigger callbacks when notes are played
    """
    
    def __init__(self, note_callback=None):
        """
        Initialize the BLE MIDI receiver
        
        Args:
            note_callback: Function to call when a note event occurs.
                          Signature: callback(event_type, note, velocity=None)
                          event_type: 'note_on' or 'note_off'
                          note: MIDI note number (0-127)
                          velocity: Note velocity (0-127) for note_on events
        """
        self.connected = False
        self.connection = None
        self.midi_characteristic = None
        self.note_callback = note_callback
        
        # Current playing state
        self.current_note = None
        
        print("Aeroband BLE MIDI initialized")

    
    def parse_midi_message(self, data):
        """
        Parse BLE MIDI message and extract MIDI commands
        
        BLE MIDI format: [header, timestamp, midi_status, ...midi_data]
        """
        if len(data) < 3:
            return None
        
        # Skip BLE MIDI header and timestamp (first 2 bytes)
        midi_status = data[2]
        
        # Note On: 0x90-0x9F
        if 0x90 <= midi_status <= 0x9F:
            if len(data) >= 5:
                note = data[3]
                velocity = data[4]
                if velocity > 0:
                    return ('note_on', note, velocity)
                else:
                    return ('note_off', note)
        
        # Note Off: 0x80-0x8F
        elif 0x80 <= midi_status <= 0x8F:
            if len(data) >= 4:
                note = data[3]
                return ('note_off', note)
        
        return None
    
    async def scan_and_connect(self, timeout_ms=30000):
        """
        Scan for Aeroband guitar and connect via BLE
        
        Args:
            timeout_ms: Scan timeout in milliseconds
        """
        # Initialize WiFi to activate CYW43 chip (needed for Bluetooth)
        print("Initializing CYW43 chip...")
        wlan = network.WLAN(network.STA_IF)
        wlan.active(True)
        await asyncio.sleep(1)  # Give chip time to initialize
        
        print("Scanning for Aeroband guitar...")
        
        async with aioble.scan(timeout_ms, interval_us=30000, window_us=30000, active=True) as scanner:
            async for result in scanner:
                # Look for device with MIDI service or Aeroband in name
                if _MIDI_SERVICE_UUID in result.services():
                    print(f"Found MIDI device: {result.name()} [{result.device}]")
                    
                    try:
                        print("Connecting...")
                        self.connection = await result.device.connect()
                        print("Connected!")
                        
                        # Discover MIDI service
                        print("Discovering services...")
                        midi_service = await self.connection.service(_MIDI_SERVICE_UUID)
                        
                        if midi_service is None:
                            print("MIDI service not found")
                            await self.connection.disconnect()
                            continue
                        
                        print("Getting MIDI characteristic...")
                        self.midi_characteristic = await midi_service.characteristic(_MIDI_CHAR_UUID)
                        
                        if self.midi_characteristic is None:
                            print("MIDI characteristic not found")
                            await self.connection.disconnect()
                            continue
                        
                        self.connected = True
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
                
                # Also check for "Aeroband" or "PocketDrum" in device name
                name = result.name()
                if name and ("aeroband" in name.lower() or "pocketdrum" in name.lower()):
                    print(f"Found possible Aeroband: {name} [{result.device}]")
                    try:
                        print("Connecting...")
                        self.connection = await result.device.connect()
                        print("Connected!")
                        
                        # Try to find MIDI service
                        print("Discovering services...")
                        midi_service = await self.connection.service(_MIDI_SERVICE_UUID)
                        
                        if midi_service is None:
                            print("MIDI service not found")
                            await self.connection.disconnect()
                            continue
                        
                        print("Getting MIDI characteristic...")
                        self.midi_characteristic = await midi_service.characteristic(_MIDI_CHAR_UUID)
                        
                        if self.midi_characteristic is None:
                            print("MIDI characteristic not found")
                            await self.connection.disconnect()
                            continue
                        
                        self.connected = True
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
        
        print("Aeroband guitar not found")
        return False
    
    async def handle_midi(self):
        """Handle incoming MIDI messages and play corresponding tones"""
        if not self.connected or not self.midi_characteristic:
            print("Not connected to Aeroband")
            return
        
        print("Listening for MIDI messages...")
        
        try:
            while self.connected:
                # Wait for MIDI data
                data = await self.midi_characteristic.notified()
                
                # Parse MIDI message
                msg = self.parse_midi_message(data)
                
                if msg:
                    if msg[0] == 'note_on':
                        note = msg[1]
                        velocity = msg[2]
                        frequency = midi_note_to_frequency(note)
                        print(f"Note ON: {note} (velocity: {velocity}, freq: {frequency:.1f}Hz)")
                        
                        self.current_note = note
                        
                        # Call the callback if provided
                        if self.note_callback:
                            self.note_callback('note_on', note, velocity)
                        
                    elif msg[0] == 'note_off':
                        note = msg[1]
                        print(f"Note OFF: {note}")
                        
                        if note == self.current_note:
                            self.current_note = None
                        
                        # Call the callback if provided
                        if self.note_callback:
                            self.note_callback('note_off', note)
                
                await asyncio.sleep_ms(10)
                
        except Exception as e:
            print(f"MIDI handler error: {e}")
            self.connected = False
    

    
    async def run(self):
        """Main run loop - connect and handle MIDI"""
        # Connect to Aeroband
        if not await self.scan_and_connect():
            print("Failed to connect to Aeroband guitar")
            return
        
        print("Starting MIDI handler...")
        
        # Run MIDI handler
        try:
            await self.handle_midi()
        except Exception as e:
            print(f"Error in main loop: {e}")
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Clean up resources"""
        print("Cleaning up...")
        if self.connection:
            try:
                asyncio.run(self.connection.disconnect())
            except:
                pass
        print("Done")


# Example usage
def my_note_callback(event_type, note, velocity=None):
    """Example callback function that gets called when notes are played"""
    if event_type == 'note_on':
        print(f"Callback: Note struck! Note={note}, Velocity={velocity}")
        # Add your custom code here
    elif event_type == 'note_off':
        print(f"Callback: Note released! Note={note}")
        # Add your custom code here

async def main():
    # Create instance with your callback function
    aeroband = AerobandBLEMIDI(note_callback=my_note_callback)
    await aeroband.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Stopped by user")
