"""
Guitar Trainer - Chord List Upload Tool
Upload custom chord sequences to your Guitar Trainer via USB Serial

Requirements:
    pip install pyserial

Usage:
    python upload_chords.py [chord_file.json]
    
    If no file is specified, uploads example chord lists.
    
Note: The Guitar Trainer will receive uploads at any time during operation.
"""

import serial
import serial.tools.list_ports
import time
import json
import sys
import os

class ChordUploader:
    def __init__(self):
        self.serial = None
        self.port = None
        
    def scan_for_device(self):
        """Scan for the Guitar Trainer device (Pico COM port)"""
        print("Scanning for Raspberry Pi Pico...")
        ports = serial.tools.list_ports.comports()
        
        for port in ports:
            # Look for Pico - usually shows as "USB Serial Device" or contains "Pico"
            if any(keyword in port.description.lower() for keyword in ['pico', 'usb serial', 'com']):
                print(f"Found potential device: {port.device} - {port.description}")
                self.port = port.device
                return True
        
        # If no Pico found, list all ports for user to choose
        if ports:
            print("\nAvailable COM ports:")
            for i, port in enumerate(ports, 1):
                print(f"{i}. {port.device} - {port.description}")
            
            choice = input("\nEnter port number (or port name like COM3): ").strip()
            if choice.isdigit():
                idx = int(choice) - 1
                if 0 <= idx < len(ports):
                    self.port = ports[idx].device
                    return True
            elif choice.upper().startswith('COM'):
                self.port = choice.upper()
                return True
        
        print("No suitable device found")
        return False
    
    def connect(self):
        """Connect to the device"""
        if not self.port:
            print("No port selected. Run scan first.")
            return False
        
        try:
            self.serial = serial.Serial(self.port, 115200, timeout=2)
            time.sleep(0.5)  # Wait for connection to stabilize
            print(f"Connected to {self.port}")
            return True
        except Exception as e:
            print(f"Connection failed: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from device"""
        if self.serial and self.serial.is_open:
            self.serial.close()
            print("Disconnected")
    
    def upload_json_file(self, json_data):
        """Upload entire JSON chord list file to device by writing directly to filesystem"""
        if not self.serial or not self.serial.is_open:
            print("Not connected to device")
            return False
        
        try:
            print(f"Uploading JSON file with {len(json_data)} chord lists...")
            
            # Convert to compact JSON string
            json_str = json.dumps(json_data)
            
            # Enter REPL mode by sending Ctrl+C to interrupt any running program
            print("  Interrupting running program...")
            self.serial.write(b'\x03')  # Ctrl+C
            time.sleep(0.5)
            
            # Send Ctrl+C again to make sure
            self.serial.write(b'\x03')
            time.sleep(0.3)
            
            # Clear buffer
            response = self.serial.read(self.serial.in_waiting).decode('utf-8', errors='ignore')
            print(f"  After interrupt: {response[:100]}")
            
            # Enter raw REPL mode (Ctrl+A)
            print("  Entering raw REPL mode...")
            self.serial.write(b'\x01')  # Ctrl+A
            time.sleep(0.5)
            response = self.serial.read(self.serial.in_waiting).decode('utf-8', errors='ignore')
            print(f"  Raw REPL response: {response[:100]}")
            
            if 'raw REPL' not in response and 'REPL' not in response:
                print("  WARNING: May not be in raw REPL mode!")
            
            # Write Python code to delete old file, save new file, and verify
            code = f"""
import json
import os
# Delete old file if it exists
try:
    os.remove('custom_chords.json')
    print('Deleted old file')
except:
    print('No old file to delete')
# Write new file
data = {repr(json_str)}
with open('custom_chords.json', 'w') as f:
    f.write(data)
print('Wrote new file')
# Verify it was written correctly
with open('custom_chords.json', 'r') as f:
    verify = f.read()
parsed = json.loads(verify)
print('SAVED:' + str(len(parsed)) + ' lists')
for item in parsed:
    print('  - ' + item[0])
"""
            
            print("  Sending code to Pico...")
            # Execute the code
            self.serial.write(code.encode('utf-8'))
            time.sleep(0.2)
            self.serial.write(b'\x04')  # Ctrl+D to execute
            
            print("  Waiting for execution...")
            time.sleep(1.5)  # Give more time for file write
            
            # Read response
            response = self.serial.read(self.serial.in_waiting).decode('utf-8', errors='ignore')
            
            print(f"\n  Full response from Pico:")
            print("  " + "="*50)
            print(response)
            print("  " + "="*50)
            
            if 'SAVED:' in response:
                print("✓ Upload successful! File written to Pico.")
                print("  Performing soft reset...")
                
                # Exit raw REPL mode first (Ctrl+B)
                time.sleep(0.2)
                self.serial.write(b'\x02')  # Ctrl+B to exit raw REPL
                time.sleep(0.2)
                
                # Perform soft reset (Ctrl+D)
                self.serial.write(b'\x04')  # Ctrl+D
                time.sleep(1.5)
                
                # Clear any output
                self.serial.reset_input_buffer()
                
                print("✓ Device reset complete!")
                print("  Your new chord lists should now appear in the menu.")
                return True
            else:
                print(f"Upload may have failed. Response: {response[:200]}")
                
                # Try to recover - exit raw REPL and reset anyway
                print("  Attempting to reset device...")
                time.sleep(0.2)
                self.serial.write(b'\x02')  # Ctrl+B
                time.sleep(0.2)
                self.serial.write(b'\x04')  # Ctrl+D
                time.sleep(1.0)
                return False
            
        except Exception as e:
            print(f"Upload failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def encode_chord_list(self, name, mode, chords):
        """
        Encode chord list as a simple protocol string
        Format: CHORD_LIST|name|mode|chord1,chord2,chord3...
        """
        chord_str = ','.join(chords)
        return f"CHORD_LIST|{name}|{mode}|{chord_str}\n"
    
    def upload_chord_list(self, name, mode, chords):
        """Upload a chord list to the device"""
        if not self.serial or not self.serial.is_open:
            print("Not connected to device")
            return False
        
        try:
            # Clear input buffer before sending
            self.serial.reset_input_buffer()
            
            # Encode the chord list
            data = self.encode_chord_list(name, mode, chords)
            
            print(f"Uploading: {name} (mode={mode}, {len(chords)} chords)")
            print(f"Chords: {', '.join(chords)}")
            
            # Send via serial
            self.serial.write(data.encode('utf-8'))
            self.serial.flush()
            
            # Wait for acknowledgment (give more time for Pico to process)
            time.sleep(0.5)
            
            # Try to read response multiple times
            for attempt in range(3):
                if self.serial.in_waiting > 0:
                    response = self.serial.read(self.serial.in_waiting).decode('utf-8', errors='ignore').strip()
                    if 'OK' in response or 'Added' in response:
                        print("✓ Upload successful!")
                        time.sleep(0.3)
                        return True
                    else:
                        print(f"Response: {response}")
                        return True
                time.sleep(0.3)
            
            print("Upload sent (no confirmation received)")
            time.sleep(0.3)
            return True
            
        except Exception as e:
            print(f"Upload failed: {e}")
            return False
    
    def upload_multiple(self, chord_lists):
        """Upload multiple chord lists"""
        success_count = 0
        
        for name, mode, chords in chord_lists:
            if self.upload_chord_list(name, mode, chords):
                success_count += 1
            time.sleep(0.5)  # Wait between uploads
        
        print(f"\nUploaded {success_count}/{len(chord_lists)} chord lists")
        return success_count

def main():
    """Main upload workflow"""
    uploader = ChordUploader()
    
    # Scan for device
    if not uploader.scan_for_device():
        return
    
    # Connect
    if not uploader.connect():
        return
    
    try:
        print("\n" + "="*50)
        print("Guitar Trainer Chord Upload Tool")
        print("="*50)
        
        # Check if JSON file was provided as argument
        if len(sys.argv) > 1:
            json_file = sys.argv[1]
            if os.path.exists(json_file):
                print(f"\nLoading chord lists from: {json_file}")
                try:
                    with open(json_file, 'r') as f:
                        chord_data = json.load(f)
                    
                    # Validate format
                    if not isinstance(chord_data, list):
                        print("Error: JSON file must contain a list of chord lists")
                        return
                    
                    print(f"Found {len(chord_data)} chord lists in file")
                    for item in chord_data:
                        name = item[0]
                        data = item[1]
                        if data[0] == "M":
                            mode_text = "Metronome"
                            print(f"  - {name} ({mode_text}): {len(data)-1} beats")
                        else:
                            mode = data[0]
                            chords = data[1:]
                            mode_text = "Random" if mode == "R" else "Sequential"
                            print(f"  - {name} ({mode_text}): {', '.join(chords)}")
                    
                    print(f"\nUploading JSON data ({len(json.dumps(chord_data))} bytes)...")
                    
                    # Upload the entire JSON
                    uploader.upload_json_file(chord_data)
                    return
                    
                except json.JSONDecodeError as e:
                    print(f"Error parsing JSON file: {e}")
                    return
                except Exception as e:
                    print(f"Error loading file: {e}")
                    return
            else:
                print(f"Error: File not found: {json_file}")
                return
        
        # No file provided - use example chord lists
        print("\nNo JSON file specified. Using example chord lists.")
        print("Usage: python upload_chords.py [chord_file.json]")
        
        # Example chord lists to upload
        # Format: (name, mode, [chord1, chord2, ...])
        chord_lists = [
            ("Pop Progression", "R", ["C", "G", "Am", "F"]),
            ("Blues in E", "R", ["E7", "A7", "B7"]),
            ("Jazz ii-V-I", "S", ["Dm7", "G7", "Cmaj7"]),
            ("Country Basic", "R", ["G", "C", "D", "Em"]),
        ]
        
        print("\nAvailable chord lists to upload:")
        for i, (name, mode, chords) in enumerate(chord_lists, 1):
            mode_text = "Random" if mode == "R" else "Sequential"
            print(f"{i}. {name} ({mode_text}) - {', '.join(chords)}")
        
        print("\nOptions:")
        print("1-{}: Upload specific list".format(len(chord_lists)))
        print("A: Upload all")
        print("C: Create custom list")
        print("J: Upload as JSON file")
        print("Q: Quit")
        
        choice = input("\nYour choice: ").strip().upper()
        
        if choice == 'Q':
            return
        elif choice == 'J':
            # Upload as JSON file
            json_data = [(name, [mode] + chords) for name, mode, chords in chord_lists]
            uploader.upload_json_file(json_data)
        elif choice == 'A':
            uploader.upload_multiple(chord_lists)
        elif choice == 'C':
            # Custom chord list
            name = input("List name (max 20 chars): ").strip()[:20]
            mode = input("Mode (R=Random, S=Sequential): ").strip().upper()
            if mode not in ['R', 'S']:
                mode = 'R'
            
            chords_input = input("Chords (comma-separated, e.g., C,G,Am,F): ").strip()
            chords = [c.strip() for c in chords_input.split(',') if c.strip()]
            
            if name and chords:
                uploader.upload_chord_list(name, mode, chords)
            else:
                print("Invalid input")
        elif choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(chord_lists):
                name, mode, chords = chord_lists[idx]
                uploader.upload_chord_list(name, mode, chords)
            else:
                print("Invalid selection")
        else:
            print("Invalid choice")
        
    finally:
        uploader.disconnect()

if __name__ == "__main__":
    print("Guitar Trainer - Chord Upload Tool")
    print("Make sure your Guitar Trainer is powered on and in menu mode")
    print()
    
    try:
        main()
    except KeyboardInterrupt:
        print("\nCancelled by user")
    except Exception as e:
        print(f"Error: {e}")
