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

# Standard tuning: String 1 (high E) = MIDI 64, String 2 (B) = 59, String 3 (G) = 55, 
# String 4 (D) = 50, String 5 (A) = 45, String 6 (low E) = 40
OPEN_STRING_NOTES = [64, 59, 55, 50, 45, 40]  # Strings 1-6

# MIDI notes that make up each chord (for detection)
# These are the notes you want to hear when the chord is played
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

# Map each MIDI note to string number (1-6) for frets 0-4
# If a note appears on multiple strings, store the lowest fret position (highest string number)
STRING_NUMBER = {}
for string_num in range(6, 0, -1):  # Strings 6-1 (low to high) so higher strings overwrite
    open_note = OPEN_STRING_NOTES[string_num - 1]
    for fret in range(5):  # Frets 0-4
        midi_note = open_note + fret
        # This will keep overwriting with higher strings (lower string numbers)
        # So we end up with the highest pitch string for each note
        STRING_NUMBER[midi_note] = string_num


def midi_to_fret_position(midi_note, string_num):
    """Calculate fret position for a MIDI note on a given string (1-6)"""
    open_note = OPEN_STRING_NOTES[string_num - 1]
    fret = midi_note - open_note
    if 0 <= fret <= 4:  # Only first 4 frets
        return fret
    return None

def generate_chord_shape(chord_name):
    """Generate chord fingering from MIDI notes
    
    Attempts to find the best fingering on the fretboard (first 4 frets only)
    """
    if chord_name not in CHORD_MIDI_NOTES:
        return None
    
    midi_notes = CHORD_MIDI_NOTES[chord_name]
    shape = []
    
    # For each string (6 to 1), find if any chord note can be played on it
    for string_num in range(6, 0, -1):
        found_fret = None
        
        # Try each note in the chord
        for note in midi_notes:
            fret = midi_to_fret_position(note, string_num)
            if fret is not None:
                found_fret = fret
                break  # Use first matching note
        
        if found_fret is not None:
            shape.append((string_num, found_fret))
        else:
            # Mute this string
            shape.append((string_num, -1))
    
    return shape

# Generate chord shapes from MIDI notes
CHORD_SHAPES = {}
for chord_name in CHORD_MIDI_NOTES.keys():
    CHORD_SHAPES[chord_name] = generate_chord_shape(chord_name)

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
        start_y = 100
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
    
    def draw_played_notes_overlay(self, played_notes):
        """Draw red dots over the fretboard showing where user played"""
        print(f"draw_played_notes_overlay called with notes: {played_notes}")
        
        if not played_notes:
            print("No notes to draw")
            return
        
        start_x = 30
        start_y = 100
        string_spacing = 16
        fret_width = 40
        
        # For each played note, find the best string to show it on (lowest fret position within 0-4)
        for note in played_notes:
            best_string = None
            best_fret = None
            
            # Check all strings to find where this note appears in frets 0-4
            for string_num in range(1, 7):  # Strings 1-6
                open_note = OPEN_STRING_NOTES[string_num - 1]
                if note >= open_note:
                    fret_num = note - open_note
                    if 0 <= fret_num <= 4:  # Only within visible frets
                        if best_fret is None or fret_num < best_fret:
                            best_string = string_num
                            best_fret = fret_num
            
            # Draw the red marker on the best string
            if best_string is not None:
                print(f"Drawing note {note} on string {best_string}, fret {best_fret}")
                string_y = start_y + ((best_string - 1) * string_spacing)
                
                if best_fret == 0:
                    # Open string - draw red O
                    self.tft.text("O", start_x - 18, string_y - 4, self.COLOR_RED)
                else:
                    # Fretted note - draw smaller red square (4x4 instead of 10x10)
                    fret_x = start_x + (best_fret * fret_width) - (fret_width // 2)
                    self.tft.fill_rect(fret_x - 2, string_y - 2, 4, 4, self.COLOR_RED)
            else:
                print(f"Note {note} not within frets 0-4 on any string")
    
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
        
        # Draw chord diagram
        self.draw_chord_fretboard(chord_name, self.COLOR_ORANGE)
        
        self.tft.show()
        print(f"Target chord: {chord_name}")
    
    def display_correct_chord(self, chord_name):
        """Display success feedback"""
        self.tft.fill(self.COLOR_BLACK)
        
        # Large success message
        x_pos = 70 if len(chord_name) > 1 else 90
        self.draw_large_text(chord_name, x_pos, 40, self.COLOR_GREEN)
        
        # Show "Correct!" label
        self.tft.text("Correct!", 85, 110, self.COLOR_GREEN)
        
        # Draw chord diagram in green
        self.draw_chord_fretboard(chord_name, self.COLOR_GREEN)
        
        # Show progress
        progress_text = f"{self.current_chord_index + 1}/{len(self.chord_sequence)}"
        self.tft.text(progress_text, 90, 10, self.COLOR_WHITE)
        
        self.tft.show()
    
    def display_wrong_chord(self, played_chord, played_notes, target_chord):
        """Display when wrong chord is played - show target in orange, played in red"""
        print(f"display_wrong_chord called: played={played_chord}, notes={played_notes}, target={target_chord}")
        
        self.tft.fill(self.COLOR_BLACK)
        
        # Show progress
        progress_text = f"{self.current_chord_index + 1}/{len(self.chord_sequence)}"
        self.tft.text(progress_text, 90, 5, self.COLOR_WHITE)
        
        # Show target chord name
        x_pos = 70 if len(target_chord) > 1 else 90
        self.draw_large_text(target_chord, x_pos, 30, self.COLOR_ORANGE)
        
        # Draw target chord in orange
        self.draw_chord_fretboard(target_chord, self.COLOR_ORANGE)
        
        # Overlay played notes in red
        print(f"Drawing played notes overlay with {len(played_notes)} notes")
        self.draw_played_notes_overlay(played_notes)
        
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
        notes_hit = [False, False, False, False, False, False]  # For strings 1-6
        last_note = None
        time_last_chord = 0
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
                        if note == last_note:
                            continue
                        if utime.ticks_diff(utime.ticks_ms(), time_last_chord) > 500:
                            print("Resetting notes_hit due to time difference")
                            notes_hit = [False, False, False, False, False, False]

                        time_last_chord = utime.ticks_ms()
                        last_note = note
                        string_n = STRING_NUMBER.get(note) 
                        string_num = string_n - 1 if string_n else 0
                        notes_hit[string_num] = True
                        print(notes_hit)
                        if not all(notes_hit):
                            continue
                        
                        
                        print("All strings played! -------------------------------------------------------------------")


                        # Check for chord after a short delay to collect all notes
                        #await asyncio.sleep_ms(100)
                        # Detect chord
                        detected_chord = detect_chord(self.played_notes)
                        
                        if detected_chord and detected_chord != self.last_detected_chord:
                            self.last_detected_chord = detected_chord
                            print(f"Detected chord: {detected_chord} {detected_chord.index}")
                            
                            if self.sequence_mode:
                                # Check if correct chord
                                if self.current_chord_index < len(self.chord_sequence):
                                    target_chord = self.chord_sequence[self.current_chord_index]
                                    
                                    if detected_chord == target_chord:
                                        # Correct!
                                        print("Correct chord!")
                                        self.display_correct_chord(detected_chord)
                                        await asyncio.sleep_ms(3000)
                                        
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
                                        # Wrong chord - capture the notes NOW before they change
                                        print(f"Wrong! Expected {target_chord}, got {detected_chord}")
                                        wrong_notes = set(self.played_notes)  # Make a copy
                                        self.display_wrong_chord(detected_chord, wrong_notes, target_chord)
                                        
                                        # Reset last_detected_chord so next chord attempt will be detected
                                        self.last_detected_chord = None
                        
                        notes_hit = [False, False, False, False, False, False]
                    elif msg[0] == 'note_off':
                        note = msg[1]
                        print(f"Note OFF: {note}")
                        self.played_notes.discard(note)
                        
                        # Reset chord detection when all notes released
                        if len(self.played_notes) == 0:
                            self.last_detected_chord = None
                
                # await asyncio.sleep_ms(10)
                
        except Exception as e:
            print(f"MIDI handler error: {e}")
            self.connected = False
    
    async def show_menu_and_wait_for_selection(self):
        """Show practice menu and wait for user to select with 22nd fret note"""
        # Practice options
        practice_options = [
            ('Simple 3', ['C', 'G', 'D']),
            ('Classic 4', ['C', 'G', 'Am', 'Em']),
            ('All Basic', ['C', 'G', 'D', 'A', 'E', 'Am', 'Em', 'Dm']),
            ('Major Chords', ['C', 'D', 'E', 'F', 'G', 'A']),
            ('Minor Chords', ['Am', 'Dm', 'Em']),
            ('Free Play', []),
        ]
        
        # MIDI notes for 22nd fret on each string (high to low)
        # String 1 (high E): 64 + 22 = 86
        # String 2 (B): 59 + 22 = 81
        # String 3 (G): 55 + 22 = 77
        # String 4 (D): 50 + 22 = 72
        # String 5 (A): 45 + 22 = 67
        # String 6 (low E): 40 + 22 = 62
        selection_notes = [86, 81, 77, 72, 67, 62]
        
        current_selection = 0
        
        # Display menu
        self.tft.fill(self.COLOR_BLACK)
        self.tft.text("Select Practice:", 50, 10, self.COLOR_YELLOW)
        self.tft.text("Use 22nd fret", 55, 30, self.COLOR_WHITE)
        
        # Show options
        y_pos = 50
        for i, (name, _) in enumerate(practice_options):
            color = self.COLOR_GREEN if i == current_selection else self.COLOR_WHITE
            marker = ">" if i == current_selection else " "
            self.tft.text(f"{marker}{i+1}. {name}", 30, y_pos, color)
            y_pos += 20
        
        self.tft.text("String 1-6 = opt 1-6", 30, y_pos + 10, self.COLOR_ORANGE)
        self.tft.show()
        
        print("Menu displayed. Waiting for 22nd fret selection...")
        print("Play 22nd fret on:")
        for i, (name, _) in enumerate(practice_options):
            print(f"  String {i+1}: {name}")
        
        # Wait for selection
        while True:
            data = await self.midi_characteristic.notified()
            msg = self.parse_midi_message(data)
            
            if msg and msg[0] == 'note_on':
                note = msg[1]
                print(f"Note received: {note}")
                
                # Check if it's a 22nd fret note
                if note in selection_notes:
                    selected_index = selection_notes.index(note)
                    if selected_index < len(practice_options):
                        print(f"Selected: {practice_options[selected_index][0]}")
                        
                        # Flash selection
                        self.tft.fill(self.COLOR_BLACK)
                        name, chords = practice_options[selected_index]
                        self.tft.text("Selected:", 80, 100, self.COLOR_GREEN)
                        self.tft.text(name, 85, 120, self.COLOR_YELLOW)
                        self.tft.show()
                        #await asyncio.sleep_ms(1000)
                        
                        return chords
            
            #await asyncio.sleep_ms(10)
    
    async def run(self):
        """Main run loop"""
        if not await self.scan_and_connect():
            print("Failed to connect")
            return
        
        # Show menu and wait for selection
        print("Showing practice menu...")
        selected_chords = await self.show_menu_and_wait_for_selection()
        
        # Set the chord sequence
        self.chord_sequence = selected_chords
        self.sequence_mode = len(self.chord_sequence) > 0
        self.current_chord_index = 0
        
        if self.sequence_mode:
            print(f"Starting practice: {len(self.chord_sequence)} chords")
        else:
            print("Starting free play mode")
        
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
    # Start with no preset chord sequence - menu will set it
    trainer = ChordTrainer(chord_sequence=[])
    
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
