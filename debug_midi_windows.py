"""
Windows MIDI Debug Script - Captures MIDI messages from any connected MIDI device
and displays them in a user-friendly format.

Requires: pip install mido python-rtmidi

NOTE: For Bluetooth MIDI on Windows:
1. Pair the device via Windows Bluetooth Settings
2. Install "Bluetooth MIDI" app from Microsoft Store (for native MIDI support)
3. Or use a third-party tool like "Bluetooth MIDI Connect"
"""

import mido
import time
from typing import Dict, Tuple


class WindowsMIDIDebugger:
    def __init__(self):
        self.note_names = {
            0: 'C-1', 1: 'C#-1', 2: 'D-1', 3: 'D#-1', 4: 'E-1', 5: 'F-1',
            6: 'F#-1', 7: 'G-1', 8: 'G#-1', 9: 'A-1', 10: 'A#-1', 11: 'B-1',
            12: 'C0', 13: 'C#0', 14: 'D0', 15: 'D#0', 16: 'E0', 17: 'F0',
            18: 'F#0', 19: 'G0', 20: 'G#0', 21: 'A0', 22: 'A#0', 23: 'B0',
            24: 'C1', 25: 'C#1', 26: 'D1', 27: 'D#1', 28: 'E1', 29: 'F1',
            30: 'F#1', 31: 'G1', 32: 'G#1', 33: 'A1', 34: 'A#1', 35: 'B1',
            36: 'C2', 37: 'C#2', 38: 'D2', 39: 'D#2', 40: 'E2', 41: 'F2',
            42: 'F#2', 43: 'G2', 44: 'G#2', 45: 'A2', 46: 'A#2', 47: 'B2',
            48: 'C3', 49: 'C#3', 50: 'D3', 51: 'D#3', 52: 'E3', 53: 'F3',
            54: 'F#3', 55: 'G3', 56: 'G#3', 57: 'A3', 58: 'A#3', 59: 'B3',
            60: 'C4', 61: 'C#4', 62: 'D4', 63: 'D#4', 64: 'E4', 65: 'F4',
            66: 'F#4', 67: 'G4', 68: 'G#4', 69: 'A4', 70: 'A#4', 71: 'B4',
            72: 'C5', 73: 'C#5', 74: 'D5', 75: 'D#5', 76: 'E5', 77: 'F5',
            78: 'F#5', 79: 'G5', 80: 'G#5', 81: 'A5', 82: 'A#5', 83: 'B5',
            84: 'C6', 85: 'C#6', 86: 'D6', 87: 'D#6', 88: 'E6', 89: 'F6',
            90: 'F#6', 91: 'G6', 92: 'G#6', 93: 'A6', 94: 'A#6', 95: 'B6',
            96: 'C7',
        }
        self.inport = None
        self.message_count = 0

    def get_note_name(self, midi_note: int) -> str:
        """Get friendly note name from MIDI note number"""
        return self.note_names.get(midi_note, f'Unknown({midi_note})')

    def list_devices(self) -> None:
        """List all available MIDI input devices, highlighting Bluetooth devices"""
        print("Available MIDI Input Devices:")
        print("-" * 60)
        input_names = mido.get_input_names()
        
        if not input_names:
            print("❌ No MIDI input devices found!")
            print("\nPossible solutions:")
            print("  1. Make sure your device is paired via Windows Bluetooth Settings")
            print("  2. Install 'Bluetooth MIDI' from Microsoft Store")
            print("  3. Or use 'Bluetooth MIDI Connect' (third-party tool)")
            print("  4. Try reconnecting the Bluetooth device")
            print("\nChecking MIDI output devices...")
            output_names = mido.get_output_names()
            if output_names:
                print("✓ MIDI output devices found (MIDI system is working):")
                for name in output_names:
                    print(f"    - {name}")
            else:
                print("❌ No MIDI devices of any kind found")
                print("  Check that you have MIDI drivers installed")
            return
        
        bluetooth_keywords = ['bluetooth', 'wireless', 'ble', 'aeroband', 'aerophone']
        
        for idx, name in enumerate(input_names):
            is_bluetooth = any(keyword in name.lower() for keyword in bluetooth_keywords)
            marker = "🔵 [BT]" if is_bluetooth else "    "
            print(f"  [{idx}] {marker} {name}")
        print("-" * 60)

    def select_device(self) -> bool:
        """Select a MIDI input device, with option to auto-connect to Bluetooth"""
        input_names = mido.get_input_names()
        
        if not input_names:
            print("No MIDI input devices found!")
            return False
        
        # Check for Bluetooth MIDI devices
        bluetooth_keywords = ['bluetooth', 'wireless', 'ble', 'aeroband', 'aerophone']
        bluetooth_devices = [(idx, name) for idx, name in enumerate(input_names) 
                            if any(keyword in name.lower() for keyword in bluetooth_keywords)]
        
        # If only one Bluetooth device found, offer to auto-connect
        if len(bluetooth_devices) == 1:
            idx, name = bluetooth_devices[0]
            print(f"\nFound Bluetooth MIDI device: {name}")
            auto_connect = input("Auto-connect to this device? (y/n): ").strip().lower()
            if auto_connect == 'y':
                self.inport = mido.open_input(name)
                print(f"Connected to: {name}")
                return True
        
        self.list_devices()
        
        try:
            device_idx = int(input(f"\nSelect device (0-{len(input_names)-1}): "))
            if 0 <= device_idx < len(input_names):
                device_name = input_names[device_idx]
                self.inport = mido.open_input(device_name)
                print(f"\nConnected to: {device_name}")
                return True
            else:
                print("Invalid selection!")
                return False
        except ValueError:
            print("Invalid input!")
            return False

    def process_message(self, msg: mido.Message) -> None:
        """Process and display a MIDI message"""
        self.message_count += 1
        
        if msg.type == 'note_on':
            note_name = self.get_note_name(msg.note)
            channel = msg.channel + 1
            print(f"  ✓ NOTE ON  - Channel: {channel:2d} Note: {msg.note:3d} ({note_name:4s}) Velocity: {msg.velocity:3d}")
        
        elif msg.type == 'note_off':
            note_name = self.get_note_name(msg.note)
            channel = msg.channel + 1
            print(f"  ✗ NOTE OFF - Channel: {channel:2d} Note: {msg.note:3d} ({note_name:4s})")
        
        elif msg.type == 'control_change':
            channel = msg.channel + 1
            print(f"  ⚙ CONTROL CHANGE - Channel: {channel:2d} Control: {msg.control:3d} Value: {msg.value:3d}")
        
        elif msg.type == 'program_change':
            channel = msg.channel + 1
            print(f"  🎵 PROGRAM CHANGE - Channel: {channel:2d} Program: {msg.program:3d}")
        
        elif msg.type == 'pitch_wheel':
            channel = msg.channel + 1
            print(f"  ⏸ PITCH WHEEL - Channel: {channel:2d} Value: {msg.pitch}")
        
        else:
            # Print other message types as-is
            print(f"  → {msg.type.upper()} - {msg}")

    def run(self) -> None:
        """Main debug loop"""
        print("=== MIDI DEBUG MONITOR (Windows) ===\n")
        
        if not self.select_device():
            return
        
        print("\nListening for MIDI messages... (Press Ctrl+C to stop)\n")
        
        try:
            while True:
                # Poll for messages with a timeout
                msg = self.inport.poll()
                
                if msg:
                    self.process_message(msg)
                else:
                    # Small sleep to prevent busy-waiting
                    time.sleep(0.01)
        
        except KeyboardInterrupt:
            print("\n\nDebug monitor stopped")
        
        finally:
            if self.inport:
                self.inport.close()
                print("MIDI input closed")


def main():
    debugger = WindowsMIDIDebugger()
    debugger.run()


if __name__ == '__main__':
    main()
