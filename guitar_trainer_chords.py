# Guitar Chord Trainer - Display chords from Aeroband guitar on GC9A01 display
import asyncio
import aioble
import bluetooth
import network
from gc9a01_spi_fb import GC9A01_SPI_FB
from machine import SPI, Pin
from micropython import const
import utime

# Import large fonts
import LibreBodoni48 as large_font

# BLE MIDI Service and Characteristic UUIDs
_MIDI_SERVICE_UUID = bluetooth.UUID("03B80E5A-EDE8-4B33-A751-6CE34EC4C700")
_MIDI_CHAR_UUID = bluetooth.UUID("7772E5DB-3868-4112-A1A9-F2669D106BF3")

# Note names
NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

# Chord definitions - Format: {chord_name: [(string, fret), ...]}
# String 1 = high E, String 6 = low E
# Negative fret means don't play that string (muted)
CHORD_SHAPES = {
    'C': [(6, -1), (5, 3), (4, 2), (3, 0), (2, 1), (1, 0)],      # X32010
    'G': [(6, 3), (5, 2), (4, 0), (3, 0), (2, 0), (1, 3)],       # 320003
    'D': [(6, -1), (5, -1), (4, 0), (3, 2), (2, 3), (1, 2)],     # XX0232
    'A': [(6, -1), (5, 0), (4, 2), (3, 2), (2, 2), (1, 0)],      # X02220
    'E': [(6, 0), (5, 2), (4, 2), (3, 1), (2, 0), (1, 0)],       # 022100
    'F': [(6, 1), (5, 3), (4, 3), (3, 2), (2, 1), (1, 1)],       # 133211 (barre chord - simplified)
    'Am': [(6, -1), (5, 0), (4, 2), (3, 2), (2, 1), (1, 0)],     # X02210
    'Em': [(6, 0), (5, 2), (4, 2), (3, 0), (2, 0), (1, 0)],      # 022000
    'Dm': [(6, -1), (5, -1), (4, 0), (3, 2), (2, 3), (1, 1)],    # XX0231
    'Bdim': [(6, -1), (5, 2), (4, 3), (3, 4), (2, 3), (1, -1)],  # X23430 (simplified)
}

# MIDI notes that make up each chord (for detection)
# Using root position triads - we'll check if any of these notes are played
CHORD_MIDI_NOTES = {
    'C': [48, 52, 55, 60, 64],    # C3, E3, G3, C4, E4
    'G': [43, 47, 50, 55, 59, 67],  # G2, B2, D3, G3, B3, G4
    'D': [50, 54, 57, 62, 66],  # D3, F#3, A3, D4, F#4
    'A': [45, 49, 52, 57, 64],  # A2, C#3, E3, A3, E4
    'E': [40, 44, 47, 52, 56, 64],  # E2, G#2, B2, E3, G#3, E4
    'F': [41, 45, 48, 53, 57, 65],  # F2, A2, C3, F3, A3, F4
    'Am': [45, 48, 52, 57, 60], # A2, C3, E3, A3, C4
    'Em': [40, 43, 47, 52, 55, 64], # E2, G2, B2, E3, G3, E4
    'Dm': [50, 53, 57, 62, 65], # D3, F3, A3, D4, F4
    'Bdim': [47, 50, 53, 59],   # B2, D3, F3, B3 (B diminished: B-D-F)
}

def get_chord_shape(chord_name):
    """Get chord fingering positions"""
    return CHORD_SHAPES.get(chord_name, None)

def detect_chord(played_notes):
    """Detect which chord is being played based on notes"""
    if not played_notes:
        return None
    
    # Check each chord to see if enough notes match
    best_match = None
    best_score = 0
    
    for chord_name, chord_notes in CHORD_MIDI_NOTES.items():
        # Count how many of the chord's notes are being played
        matches = len(played_notes.intersection(set(chord_notes)))
        
        # Need at least 2 notes to match (for simpler chords) or 3 for complex ones
        min_notes = 2 if len(chord_notes) <= 4 else 3
        
        if matches >= min_notes and matches > best_score:
            best_score = matches
            best_match = chord_name
    
    return best_match

class ChordTrainer:
    """Display guitar chords on GC9A01 display"""
    
    def __init__(self, chord_sequence=None):
        """
        Initialize Chord Trainer
        
        Args:
            chord_sequence: List of chord names to practice (e.g., ['C', 'G', 'D', 'Am'])
                          If None, detects and displays any chords played
        """
        # Display setup
        print("Initializing display...")
        self.spi = SPI(0, baudrate=40_000_000, 
                      sck=Pin(18), mosi=Pin(19))
        self.tft = GC9A01_SPI_FB(self.spi, 5, 6, 9, None)
        self.tft.set_rotation(0)
        
        # Set large font
        self.tft.set_font(large_font)
        
        # Colors
        self.COLOR_BLACK = self.tft.color565(0, 0, 0)
        self.COLOR_WHITE = self.tft.color565(255, 255, 255)
        self.COLOR_GREEN = self.tft.color565(0, 255, 0)
        self.COLOR_RED = self.tft.color565(255, 0, 0)
        self.COLOR_BLUE = self.tft.color565(0, 0, 255)
        self.COLOR_YELLOW = self.tft.color565(255, 255, 0)
        self.COLOR_ORANGE = self.tft.color565(255, 165, 0)
        
        # BLE MIDI
        self.connected = False
        self.connection = None
        self.midi_characteristic = None
        
        # Chord sequence for practice
        self.chord_sequence = chord_sequence or []
        self.current_chord_index = 0
        self.sequence_mode = len(self.chord_sequence) > 0
        
        # Track played notes for chord detection
        self.played_notes = set()  # Currently held notes
        self.last_detected_chord = None
        
        # Clear screen
        self.tft.fill(self.COLOR_BLACK)
        self.tft.text("Chord Trainer", 60, 100, self.COLOR_WHITE)
        self.tft.text("Waiting...", 80, 120, self.COLOR_GREEN)
        self.tft.show()
        
        print("Display ready!")
        if self.sequence_mode:
            print(f"Practice sequence loaded: {len(self.chord_sequence)} chords")
    
    def draw_large_text(self, text, x, y, color):
        """Draw text using the large font"""
        self.tft.draw_text(text, x, y, color)
    
    def draw_chord_fretboard(self, chord_name, highlight_color):
        """Draw a fretboard diagram showing all finger positions for a chord
        
        Args:
            chord_name: Name of the chord (e.g., 'C', 'G', 'Am')
            highlight_color: Color to highlight the positions
        """
        chord_shape = get_chord_shape(chord_name)
        if not chord_shape:
            return
        
        # Fretboard area - DOUBLED SIZE
        start_x = 30
        start_y = 130
        string_spacing = 16  # Was 8, now 16
        fret_width = 40      # Was 30, now 40
        
        # Draw 6 strings (horizontal lines) - thicker
        for i in range(6):
            y = start_y + (i * string_spacing)
            # Draw thicker lines
            self.tft.hline(start_x, y, 160, self.COLOR_WHITE)
            self.tft.hline(start_x, y+1, 160, self.COLOR_WHITE)
        
        # Draw 4 frets (vertical lines) - thicker
        for i in range(1, 5):
            x = start_x + (i * fret_width)
            # Draw thicker lines
            self.tft.vline(x, start_y, string_spacing * 5, self.COLOR_WHITE)
            self.tft.vline(x+1, start_y, string_spacing * 5, self.COLOR_WHITE)
        
        # Draw fret numbers - larger spacing
        for i in range(4):
            x = start_x + (i * fret_width) + fret_width // 2 - 4
            y = start_y + string_spacing * 5 + 8
            self.tft.text(str(i) if i > 0 else "0", x, y, self.COLOR_WHITE)
        
        # Draw finger positions for each string - LARGER markers
        for string_num, fret_num in chord_shape:
            string_y = start_y + ((string_num - 1) * string_spacing)
            
            if fret_num < 0:
                # Muted string - draw X to the left (larger)
                self.tft.text("X", start_x - 18, string_y - 4, self.COLOR_RED)
            elif fret_num == 0:
                # Open string - draw O to the left (larger)
                self.tft.text("O", start_x - 18, string_y - 4, highlight_color)
            else:
                # Fretted note - draw LARGER filled square on fretboard
                fret_x = start_x + (fret_num * fret_width) - (fret_width // 2)
                self.tft.fill_rect(fret_x - 5, string_y - 5, 10, 10, highlight_color)
                fret_x = start_x + (fret_num * fret_width) - (fret_width // 2)
                self.tft.fill_rect(fret_x - 3, string_y - 3, 6, 6, highlight_color)
    
    def display_target_chord(self):
        """Display the current target chord to play"""
        if not self.sequence_mode or self.current_chord_index >= len(self.chord_sequence):
            return
        
        chord_name = self.chord_sequence[self.current_chord_index]
        
        # Clear screen
        self.tft.fill(self.COLOR_BLACK)
        
        # Show progress
        progress_text = f"{self.current_chord_index + 1}/{len(self.chord_sequence)}"
        self.tft.text(progress_text, 90, 5, self.COLOR_WHITE)
        
        # Draw LARGE chord name
        x_pos = 70 if len(chord_name) > 1 else 90
        self.draw_large_text(chord_name, x_pos, 30, self.COLOR_ORANGE)
        
        # Show chord label - moved up
        self.tft.text("Play this chord:", 50, 95, self.COLOR_WHITE)
        
        # Draw chord diagram
        self.draw_chord_fretboard(chord_name, self.COLOR_ORANGE)
        
        self.tft.show()
        print(f"Target chord: {chord_name}")
    
    def display_correct_chord(self, chord_name):
        """Display success feedback"""
        self.tft.fill(self.COLOR_BLACK)
        
        # Large success message
        x_pos = 70 if len(chord_name) > 1 else 90
        self.draw_large_text(chord_name, x_pos, 30, self.COLOR_GREEN)
        
        # Show "Correct!" label - moved up
        self.tft.text("Correct!", 85, 95, self.COLOR_GREEN)
        
        # Draw chord diagram in green
        self.draw_chord_fretboard(chord_name, self.COLOR_GREEN)
        
        # Show progress
        progress_text = f"{self.current_chord_index + 1}/{len(self.chord_sequence)}"
        self.tft.text(progress_text, 90, 5, self.COLOR_WHITE)
        
        self.tft.show()
    
    def display_wrong_chord(self, played_chord):
        """Display when wrong chord is played"""
        self.tft.fill(self.COLOR_BLACK)
        
        # Show what they played - moved up
        x_pos = 70 if len(played_chord) > 1 else 90
        self.draw_large_text(played_chord, x_pos, 30, self.COLOR_RED)
        
        self.tft.text("Wrong chord", 70, 95, self.COLOR_RED)
        
        # Show what was played
        self.draw_chord_fretboard(played_chord, self.COLOR_RED)
        
        self.tft.show()
    
    def display_sequence_complete(self):
        """Display when sequence is complete"""
        self.tft.fill(self.COLOR_BLACK)
        
        self.draw_large_text("DONE!", 60, 80, self.COLOR_GREEN)
        self.tft.text("Great job!", 75, 160, self.COLOR_YELLOW)
        
        self.tft.show()
    
    def parse_midi_message(self, data):
        """Parse BLE MIDI message"""
        if len(data) < 3:
            return None
        
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
        """Scan for and connect to Aeroband guitar"""
        print("Initializing Bluetooth...")
        
        # Initialize network for BLE
        try:
            wlan = network.WLAN(network.STA_IF)
            wlan.active(True)
            await asyncio.sleep(2)
            print(f"WLAN active: {wlan.active()}")
            
        except Exception as e:
            print(f"Init failed: {e}")
            self.tft.fill(self.COLOR_BLACK)
            self.tft.text("BLE Init Failed", 60, 80, self.COLOR_RED)
            self.tft.text("Press Ctrl+C", 60, 110, self.COLOR_YELLOW)
            self.tft.text("then Ctrl+D", 60, 130, self.COLOR_YELLOW)
            self.tft.text("to soft reset", 55, 150, self.COLOR_YELLOW)
            self.tft.show()
            return False
        
        self.tft.fill(self.COLOR_BLACK)
        self.tft.text("Scanning for", 70, 100, self.COLOR_WHITE)
        self.tft.text("Aeroband...", 75, 120, self.COLOR_YELLOW)
        self.tft.show()
        
        print("Scanning for Aeroband guitar...")
        
        async with aioble.scan(timeout_ms, interval_us=30000, window_us=30000, active=True) as scanner:
            async for result in scanner:
                print(f"Found device: {result.name()} - {result.device}")
                
                # Look for MIDI service OR Aeroband in name
                has_midi_service = _MIDI_SERVICE_UUID in result.services()
                name = result.name()
                has_aeroband_name = name and ("aeroband" in name.lower() or "pocketdrum" in name.lower() or "midi" in name.lower())
                
                if has_midi_service or has_aeroband_name:
                    print(f"Found MIDI device: {name} [{result.device}]")
                    
                    try:
                        self.tft.fill(self.COLOR_BLACK)
                        self.tft.text("Connecting...", 70, 120, self.COLOR_GREEN)
                        self.tft.show()
                        
                        print("Connecting...")
                        self.connection = await result.device.connect()
                        print("Connected!")
                        
                        # Get MIDI service
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
                        
                        # Show connected status
                        self.tft.fill(self.COLOR_BLACK)
                        self.tft.text("Connected!", 75, 110, self.COLOR_GREEN)
                        self.tft.show()
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
        
        print("Aeroband guitar not found")
        return False
    
    async def handle_midi(self):
        """Handle incoming MIDI messages"""
        if not self.connected or not self.midi_characteristic:
            print("Not connected")
            return
        
        print("Listening for MIDI...")
        
        # Show first target if in sequence mode
        if self.sequence_mode:
            self.display_target_chord()
        
        try:
            while self.connected:
                # Wait for MIDI data
                data = await self.midi_characteristic.notified()
                
                # Parse message
                msg = self.parse_midi_message(data)
                
                if msg:
                    if msg[0] == 'note_on':
                        note = msg[1]
                        print(f"Note ON: {note}")
                        self.played_notes.add(note)
                        
                        # Check for chord after a short delay to collect all notes
                        await asyncio.sleep_ms(100)
                        
                        # Detect chord
                        detected_chord = detect_chord(self.played_notes)
                        
                        if detected_chord and detected_chord != self.last_detected_chord:
                            self.last_detected_chord = detected_chord
                            print(f"Detected chord: {detected_chord}")
                            
                            if self.sequence_mode:
                                # Check if correct chord
                                if self.current_chord_index < len(self.chord_sequence):
                                    target_chord = self.chord_sequence[self.current_chord_index]
                                    
                                    if detected_chord == target_chord:
                                        # Correct!
                                        print("Correct chord!")
                                        self.display_correct_chord(detected_chord)
                                        await asyncio.sleep_ms(1500)
                                        
                                        # Move to next chord
                                        self.current_chord_index += 1
                                        
                                        if self.current_chord_index >= len(self.chord_sequence):
                                            # Sequence complete!
                                            print("Sequence complete!")
                                            self.display_sequence_complete()
                                            await asyncio.sleep(3)
                                            
                                            # Restart
                                            self.current_chord_index = 0
                                            self.display_target_chord()
                                        else:
                                            # Show next target
                                            self.display_target_chord()
                                    else:
                                        # Wrong chord
                                        print(f"Wrong! Expected {target_chord}, got {detected_chord}")
                                        self.display_wrong_chord(detected_chord)
                                        await asyncio.sleep_ms(1000)
                                        self.display_target_chord()
                        
                    elif msg[0] == 'note_off':
                        note = msg[1]
                        print(f"Note OFF: {note}")
                        self.played_notes.discard(note)
                        
                        # Reset chord detection when all notes released
                        if len(self.played_notes) == 0:
                            self.last_detected_chord = None
                
                await asyncio.sleep_ms(10)
                
        except Exception as e:
            print(f"MIDI handler error: {e}")
            self.connected = False
    
    async def run(self):
        """Main run loop"""
        if not await self.scan_and_connect():
            print("Failed to connect")
            return
        
        print("Starting MIDI handler...")
        
        try:
            await self.handle_midi()
        except Exception as e:
            print(f"Error: {e}")
        finally:
            if self.connection:
                try:
                    await self.connection.disconnect()
                except:
                    pass
            print("Done")

# Main
async def main():
    # Beginner chord progressions
    
    # Simple 3-chord progression
    simple_progression = ['C', 'G', 'D']
    
    # Classic 4-chord progression
    classic_progression = ['C', 'G', 'Am', 'Em']
    
    # Full beginner chords
    all_basic_chords = ['C', 'G', 'D', 'A', 'E', 'Am', 'Em', 'Dm']
    
    easy_chords = ['C', 'Dm', 'Em', 'F', 'G', 'Am', 'Bdim']

    # Choose your practice sequence:
    practice_chords = easy_chords
    
    # For free play mode (detects any chord), pass None or empty list:
    # trainer = ChordTrainer()
    
    # For practice mode with sequence:
    trainer = ChordTrainer(chord_sequence=practice_chords)
    
    await trainer.run()

def cleanup_ble():
    """Clean up BLE state before starting"""
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
        print("WLAN deactivated")
    except:
        pass

if __name__ == "__main__":
    # Clean up any previous BLE state
    cleanup_ble()
    
    # Wait for cleanup
    import utime
    utime.sleep_ms(1000)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Stopped by user")
        cleanup_ble()
    except Exception as e:
        print(f"Error: {e}")
        cleanup_ble()
