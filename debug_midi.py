"""
Simple MIDI debug script - connects to Aeroband using ble_connection and displays all MIDI messages
"""

import asyncio
from ble_connection_dual_core import BLEConnectionManagerDualCore


class MockDisplay:
    """Mock display for ble_connection that just prints to console"""
    def clear(self):
        pass
    
    def text(self, text, x, y):
        print(f"[Display] {text}")
    
    def show(self):
        pass


class MIDIDebugger:
    def __init__(self):
        self.display = MockDisplay()
        self.ble = BLEConnectionManagerDualCore(self.display)
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

    def get_note_name(self, midi_note):
        """Get friendly note name from MIDI note number"""
        return self.note_names.get(midi_note, f'Unknown({midi_note})')

    @staticmethod
    def parse_midi_messages(data):
        """
        Parse BLE MIDI notification and extract ALL MIDI commands
        
        BLE MIDI format: [header, timestamp, midi_status, midi_data1, midi_data2, ...]
        A single notification can contain multiple MIDI messages
        Returns a list of parsed messages
        """
        messages = []
        
        if len(data) < 3:
            return messages
        
        # BLE MIDI packet format:
        # Bytes 0-1: BLE MIDI header and timestamp
        # Bytes 2+: MIDI message(s)
        
        i = 2
        while i < len(data):
            midi_status = data[i]
            
            # Note On: 0x90-0x9F
            if 0x90 <= midi_status <= 0x9F:
                if i + 2 < len(data):
                    note = data[i + 1]
                    velocity = data[i + 2]
                    string_num = midi_status & 0x0F
                    if velocity > 0:
                        messages.append(('note_on', string_num, note, velocity))
                    else:
                        messages.append(('note_off', string_num, note))
                    i += 3
                else:
                    break
            
            # Note Off: 0x80-0x8F
            elif 0x80 <= midi_status <= 0x8F:
                if i + 1 < len(data):
                    note = data[i + 1]
                    string_num = midi_status & 0x0F
                    messages.append(('note_off', string_num, note))
                    i += 2
                else:
                    break
            
            # Unknown status byte, skip it
            else:
                i += 1
        
        return messages

    async def run(self):
        """Main debug loop"""
        print("=== MIDI DEBUG MONITOR (using ble_connection) ===\n")
        
        # Connect to Aeroband using BLEConnectionManager
        print("Connecting to Aeroband guitar...")
        if not await self.ble.scan_and_connect():
            print("Failed to connect!")
            return
        
        print("Connected! Listening for MIDI messages...\n")
        message_count = 0
        
        try:
            while self.ble.connected:
                try:
                    # Get MIDI data from the queued messages
                    data = self.ble.wait_for_queued_midi(timeout_ms=100)
                    
                    if data:
                        # Display raw bytes
                        hex_str = ' '.join(f'{b:02x}' for b in data)
                        # print(f"[Notification {data}")
                        
                        # Parse ALL MIDI messages from this notification
                        messages = self.parse_midi_messages(data)
                        
                        if messages:
                            for msg in messages:
                                if msg[0] == 'note_on':
                                    string_num = msg[1]
                                    note = msg[2]
                                    velocity = msg[3]
                                    note_name = self.get_note_name(note)
                                    print(f"  ✓ NOTE ON  - String: {string_num} Note: {note:3d} ({note_name:4s}) Velocity: {velocity:3d}")
                                elif msg[0] == 'note_off':
                                    string_num = msg[1]
                                    note = msg[2]
                                    note_name = self.get_note_name(note)
                                    print(f"  ✗ NOTE OFF - String: {string_num} Note: {note:3d} ({note_name:4s})")
                        else:
                            pass
                            # print("  (No valid MIDI messages found)")
                        
                       
                        message_count += 1
                    else:
                        # Small sleep to prevent busy-waiting when no data
                        await asyncio.sleep_ms(10)
                        
                except Exception as e:
                    print(f"Error: {e}")
                    import sys
                    sys.print_exception(e)
        
        except KeyboardInterrupt:
            print("\nDebug monitor stopped")
        
        finally:
            await self.ble.disconnect()


async def main():
    debugger = MIDIDebugger()
    await debugger.run()


if __name__ == '__main__':
    asyncio.run(main())