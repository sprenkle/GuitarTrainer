# Guitar Chord Trainer - Display chords from Aeroband guitar on GC9A01 display
import asyncio
import aioble
import bluetooth
import network
import urandom
import sys
import select
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
# All 6 strings represented (String order: E4=64, B=59, G=55, D=50, A=45, E2=40)
# CHORD_MIDI_NOTES = {
#     'C': [64, 60, 55, 52, 48, 40],    # E4, C4, G3, E3, C3, E2 (strings 1-6: play, fret3, open, fret1, fret3, open)
#     'G': [43, 47, 50, 55, 59, 67],    # G4, B3, G3, D3, B2, G2 (strings 1-6: fret3, open, open, open, fret2, fret3)
#     'D': [66, 62, 57, 50, 45, 40],    # F#4, D4, A3, D3, A2, E2 (strings 1-6: fret2, fret3, fret2, open, open, open)
#     'A': [64, 60, 57, 52, 49, 45],    # E4, C#4, A3, E3, C#3, A2 (strings 1-6: open, fret2, open, fret2, fret4, open)
#     'E': [64, 59, 56, 52, 47, 44],    # E4, B3, G#3, E3, B2, G#2 (strings 1-6: open, open, fret1, fret2, fret2, fret4)
#     'F': [65, 60, 57, 53, 48, 45],    # F4, C4, A3, F3, C3, A2 (strings 1-6: fret1, fret1, fret2, fret3, fret3, open)
#     'Am': [64, 60, 57, 50, 45, 40],   # E4, C4, A3, E3, C3, A2 (strings 1-6: open, fret1, open, fret2, fret3, open)
#     'Em': [64, 59, 55, 52, 47, 40],   # E4, B3, G3, E3, B2, E2 (strings 1-6: open, open, open, fret2, fret2, open)
#     'Dm': [64, 62, 57, 53, 50, 40],   # E4, D4, A3, F3, D3, E2 (strings 1-6: open, fret3, open, fret3, open, open)
#     'Bdim': [59, 56, 53, 50, 47, 40], # B3, G#3, F3, D3, B2, E2 (strings 1-6: open, fret1, fret3, open, fret2, open)
# }

CHORD_MIDI_NOTES = {
    'A':   [64, 61, 57, 52, 45, 40],   # E4, C#4, A3, E3, A2, E2
    'Am':  [64, 60, 57, 52, 45, 40],   # E4, C4, A3, E3, A2, E2
    'A7':  [64, 59, 57, 52, 45, 40],   # E4, B3, A3, E3, A2, E2

    'B':   [64, 59, 56, 52, 47, 40],   # E4, B3, G#3, E3, B2, E2
    'Bm':  [64, 59, 55, 52, 47, 40],   # E4, B3, G3, E3, B2, E2
    'B7':  [64, 59, 56, 52, 47, 40],   # E4, B3, G#3, E3, B2, E2

    'C':   [64, 60, 55, 52, 48, 40],   # E4, C4, G3, E3, C3, E2
    'Cm':  [64, 60, 55, 52, 48, 40],   # E4, C4, G3, E3, C3, E2
    'C7':  [64, 60, 55, 53, 48, 40],   # E4, C4, G3, F3, C3, E2

    'D':   [66, 62, 57, 50, 45, 40],   # F#4, D4, A3, D3, A2, E2
    'Dm':  [65, 62, 57, 50, 45, 40],   # F4, D4, A3, D3, A2, E2
    'D7':  [64, 62, 57, 50, 45, 40],   # E4, D4, A3, D3, A2, E2

    'E':   [64, 59, 56, 52, 47, 40],   # E4, B3, G#3, E3, B2, E2
    'Em':  [64, 59, 55, 52, 47, 40],   # E4, B3, G3, E3, B2, E2
    'E7':  [64, 59, 55, 52, 47, 40],   # E4, B3, G3, E3, B2, E2

    'F':   [64, 59, 57, 53, 48, 41],   # F4, C4, A3, F3, C3, F2
    'Fm':  [64, 60, 56, 53, 48, 41],   # E4, C4, G#3, F3, C3, F2
    'F7':  [64, 60, 57, 53, 48, 41],   # E4, C4, A3, F3, C3, F2

    'G':   [67, 59, 55, 50, 47, 43],   # G4, B3, G3, D3, B2, G2
    'Gm':  [67, 59, 55, 50, 47, 43],   # G4, B3, G3, D3, B2, G2
    'G7':  [65, 59, 55, 50, 47, 43],   # F4, B3, G3, D3, B2, G2
    'D6/9':  [64, 59, 55, 50, 47, 42], 
}

# Practice options for menu
# Format: (name, [mode, chord1, chord2, ...])
# Mode: 'R' = Randomize after each completion, 'S' = Sequential (no randomization)
PRACTICE_OPTIONS = [
    ('Simple 3', ['R', 'C', 'G', 'D']),
    ('Classic 4', ['R', 'C', 'G', 'Am', 'Em']),
    ('All Basic', ['R', 'C', 'G', 'D', 'A', 'E', 'Am', 'Em', 'Dm']),
    ('Horse With NN', ['S', 'Em', 'D6/9']),
    ('Metronome', []),  # Empty list signals metronome mode
    ('Strum Practice', ['STRUM']),  # Special marker for strum-based metronome
]

# Menu selection notes (22nd fret)
# String 1 (high E): 64 + 22 = 86
# String 2 (B): 59 + 22 = 81
# String 3 (G): 55 + 22 = 77
# String 4 (D): 50 + 22 = 72
# String 5 (A): 45 + 22 = 67
# String 6 (low E): 40 + 22 = 62
SELECTION_NOTES = [86, 81, 77, 72, 67, 62]

# BPM options for metronome
BPM_OPTIONS = [60, 80, 100, 120, 140, 160]

CHORD_MIDI_NOTES_FULL = {
    'A':   [64, 61, 57, 52, 45, None],   # E4, C#4, A3, E3, A2
    'Am':  [64, 60, 57, 52, 45, None],   # E4, C4, A3, E3, A2
    'A7':  [64, 59, 57, 52, 45, None],   # E4, B3, A3, E3, A2

    'B':   [64, 59, 56, 52, 47, None],   # E4, B3, G#3, E3, B2
    'Bm':  [64, 59, 55, 52, 47, None],   # E4, B3, G3, E3, B2
    'B7':  [64, 59, 56, 52, 47, None],   # E4, B3, G#3, E3, B2

    'C':   [64, 60, 55, 52, 48, None],   # E4, C4, G3, E3, C3
    'Cm':  [64, 60, 55, 52, 48, None],   # E4, C4, G3, E3, C3
    'C7':  [64, 60, 55, 53, 48, None],   # E4, C4, G3, F3, C3

    'D':   [66, 62, 57, 50, None, None], # F#4, D4, A3, D3
    'Dm':  [65, 62, 57, 50, None, None], # F4, D4, A3, D3
    'D7':  [64, 62, 57, 50, None, None], # E4, D4, A3, D3

    'E':   [64, 59, 56, 52, 47, 40],     # E4, B3, G#3, E3, B2, E2
    'Em':  [64, 59, 55, 52, 47, 40],     # E4, B3, G3, E3, B2, E2
    'E7':  [64, 59, 55, 52, 47, 40],     # E4, B3, G3, E3, B2, E2

    'F':   [65, 60, 57, 53, 48, 41],     # F4, C4, A3, F3, C3, F2
    'Fm':  [64, 60, 56, 53, 48, 41],     # E4, C4, G#3, F3, C3, F2
    'F7':  [64, 60, 57, 53, 48, 41],     # E4, C4, A3, F3, C3, F2

    'G':   [67, 59, 55, 50, 47, 43],     # G4, B3, G3, D3, B2, G2
    'Gm':  [67, 59, 55, 50, 47, 43],     # G4, B3, G3, D3, B2, G2
    'G7':  [65, 59, 55, 50, 47, 43],     # F4, B3, G3, D3, B2, G2
    'D6/9':  [64, 59, 55, 52, 47, 40], # F#4, D4, A3, B4, D3
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
    
    # For each string (6 to 1), find the best fret position (prefer lowest fret)
    for string_num in range(6, 0, -1):
        found_fret = None
        
        # Try each note in the chord and find the lowest fret position
        for note in midi_notes:
            fret = midi_to_fret_position(note, string_num)
            if fret is not None:
                if found_fret is None or fret < found_fret:
                    found_fret = fret
        
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
    if chord_name == 'G':
        print(f"Generated G chord shape: {CHORD_SHAPES[chord_name]}")

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
        self.randomize_mode = 'R'  # Default to randomize
        self.current_chord_index = 0
        self.sequence_mode = len(self.chord_sequence) > 0
        
        # Custom uploaded chord lists (stored in RAM)
        self.custom_chord_lists = []
        
        # USB Serial buffer for receiving chord lists
        self.serial_buffer = ""
        self.serial_task = None  # Background task for serial monitoring
        self.new_chord_list_uploaded = False  # Flag to signal menu refresh
        
        # Track played notes - array of 6 strings, each stores the note played (or None)
        # Will keep the highest note (lowest fret) for each string
        # Index 0-5 for strings 6-1 (thick to thin)
        self.played_notes = [None] * 6  # Position 0=string 6, position 5=string 1
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
    
    def draw_timeout_ring(self, progress_percent):
        """Draw a progress ring around the edge of the display
        
        Args:
            progress_percent: 0.0 to 1.0, how much of the ring to draw
        """
        import math
        
        center_x = 120
        center_y = 120
        radius = 118  # Just inside the 240x240 display
        
        # Calculate how many degrees to draw (0-360)
        degrees = int(progress_percent * 360)
        
        # Draw the ring pixel by pixel
        for angle in range(degrees):
            # Convert angle to radians (start from top, go clockwise)
            rad = math.radians(angle - 90)  # -90 to start at top
            x = int(center_x + radius * math.cos(rad))
            y = int(center_y + radius * math.sin(rad))
            
            # Draw a thicker ring (2 pixels)
            self.tft.pixel(x, y, self.COLOR_YELLOW)
            # Inner ring
            x2 = int(center_x + (radius - 1) * math.cos(rad))
            y2 = int(center_y + (radius - 1) * math.sin(rad))
            self.tft.pixel(x2, y2, self.COLOR_YELLOW)
    
    def update_live_display(self, target_chord, played_notes, strum_progress):
        """Update display in real-time as notes are played
        
        Args:
            target_chord: The chord they should be playing
            played_notes: Set of notes played so far
            strum_progress: 0.0 to 1.0 for timeout ring
        """
        # Clear and redraw
        self.tft.fill(self.COLOR_BLACK)
        
        # Show progress
        progress_text = f"{self.current_chord_index + 1}/{len(self.chord_sequence)}"
        self.tft.text(progress_text, 90, 5, self.COLOR_WHITE)
        
        # Show target chord name
        x_pos = 70 if len(target_chord) > 1 else 90
        self.draw_large_text(target_chord, x_pos, 30, self.COLOR_ORANGE)
        
        # Determine which strings have been struck (green) vs not struck (white)
        string_colors = []
        for string_num in range(1, 7):
            open_note = OPEN_STRING_NOTES[string_num - 1]
            string_was_struck = False
            
            # Check if any note from this string was played
            for fret in range(25):
                note = open_note + fret
                if note in played_notes:
                    string_was_struck = True
                    break
            
            string_colors.append(self.COLOR_GREEN if string_was_struck else self.COLOR_WHITE)
        
        # Draw fretboard with target chord positions and colored strings
        self.draw_chord_fretboard(target_chord, self.COLOR_ORANGE, string_colors)
        
        # Draw red dots for notes played
        self.draw_played_notes_overlay(played_notes)
        
        # Draw timeout ring
        self.draw_timeout_ring(strum_progress)
        
        self.tft.show()
    
    def draw_chord_fretboard(self, chord_name, highlight_color, string_colors=None):
        """Draw a fretboard diagram showing all finger positions for a chord
        
        Args:
            chord_name: Name of the chord (e.g., 'C', 'G', 'Am')
            highlight_color: Color to highlight the positions
            string_colors: Optional list of 6 colors for each string (for hit/miss indication)
        """
        chord_shape = get_chord_shape(chord_name)
        if not chord_shape:
            return
        
        # Fretboard area - DOUBLED SIZE
        start_x = 30
        start_y = 100
        string_spacing = 16  # Was 8, now 16
        fret_width = 40      # Was 30, now 40
        
        # Draw 6 strings (horizontal lines) - thicker, with optional color coding
        # String 1 (high E) at top, String 6 (low E) at bottom - player's view
        for i in range(6):
            y = start_y + (i * string_spacing)
            # String 1 at top (i=0), string 6 at bottom (i=5)
            string_index = i  # Maps i=0->string 1, i=5->string 6
            string_color = string_colors[string_index] if string_colors else self.COLOR_WHITE
            # Draw thicker lines
            self.tft.hline(start_x, y, 160, string_color)
            self.tft.hline(start_x, y+1, 160, string_color)
        
        # Draw 4 frets (vertical lines) - thicker
        for i in range(1, 5):
            x = start_x + (i * fret_width)
            # Draw thicker lines
            self.tft.vline(x, start_y, string_spacing * 5, self.COLOR_WHITE)
            self.tft.vline(x+1, start_y, string_spacing * 5, self.COLOR_WHITE)
        
        # Draw fret numbers - larger spacing (1-4, not 0)
        for i in range(1, 5):
            x = start_x + (i * fret_width) - (fret_width // 2) - 4
            y = start_y + string_spacing * 5 + 8
            self.tft.text(str(i), x, y, self.COLOR_WHITE)
        
        # Draw finger positions for each string - LARGER markers
        # string_num 1=top, 6=bottom (player's view)
        for string_num, fret_num in chord_shape:
            # String 1 at top (y=0), string 6 at bottom (y=5)
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
                self.tft.fill_rect(fret_x - 5, string_y - 5, 11, 11, highlight_color)
                fret_x = start_x + (fret_num * fret_width) - (fret_width // 2)
                self.tft.fill_rect(fret_x - 3, string_y - 3, 7, 7, highlight_color)
    
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
            if best_string is not None and best_fret is not None:
                #print(f"Drawing note {note} on string {best_string}, fret {best_fret}")
                # String 1 at top (y=0), string 6 at bottom (y=5)
                string_y = start_y + ((best_string - 1) * string_spacing)
                
                if best_fret == 0:
                    # Open string - draw red O
                    self.tft.text("O", start_x - 18, string_y - 4, self.COLOR_RED)
                else:
                    # Fretted note - draw smaller red square (6x6)
                    fret_x = start_x + (best_fret * fret_width) - (fret_width // 2)
                    self.tft.fill_rect(fret_x - 3, string_y - 3, 6, 6, self.COLOR_RED)
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
        
        # Clear the screen completely
        self.tft.fill(self.COLOR_BLACK)
        self.tft.show()  # Force clear to display
        
        # Now redraw everything
        self.tft.fill(self.COLOR_BLACK)
        
        # Show progress
        progress_text = f"{self.current_chord_index + 1}/{len(self.chord_sequence)}"
        self.tft.text(progress_text, 90, 5, self.COLOR_WHITE)
        
        # Show target chord name
        x_pos = 70 if len(target_chord) > 1 else 90
        self.draw_large_text(target_chord, x_pos, 30, self.COLOR_ORANGE)
        
        # Determine string colors based on whether each string was struck
        string_colors = []
        
        # For each string (1-6), check if ANY note from that string was played
        for string_num in range(1, 7):
            open_note = OPEN_STRING_NOTES[string_num - 1]
            string_was_struck = False
            
            # Check if any note within frets 0-24 on this string was played
            for fret in range(25):  # Check up to 24 frets
                note = open_note + fret
                if note in played_notes:
                    string_was_struck = True
                    break
            
            if string_was_struck:
                string_colors.append(self.COLOR_GREEN)  # String was struck
            else:
                string_colors.append(self.COLOR_RED)    # String was NOT struck
        
        # Draw target chord with color-coded strings
        self.draw_chord_fretboard(target_chord, self.COLOR_ORANGE, string_colors)
        
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
    
    async def show_bpm_menu(self):
        """Show BPM selection menu and wait for selection"""
        current_selection = 0
        
        # Display BPM menu
        self.tft.fill(self.COLOR_BLACK)
        self.tft.text("Select BPM:", 80, 10, self.COLOR_YELLOW)
        self.tft.text("Use 22nd fret", 55, 30, self.COLOR_WHITE)
        
        # Show BPM options
        y_pos = 50
        for i, bpm in enumerate(BPM_OPTIONS):
            color = self.COLOR_GREEN if i == current_selection else self.COLOR_WHITE
            marker = ">" if i == current_selection else " "
            self.tft.text(f"{marker}{i+1}. {bpm} BPM", 50, y_pos, color)
            y_pos += 20
        
        self.tft.text("String 1-6 = opt 1-6", 30, y_pos + 10, self.COLOR_ORANGE)
        self.tft.show()
        
        print("BPM menu displayed. Waiting for 22nd fret selection...")
        print("Play 22nd fret on:")
        for i, bpm in enumerate(BPM_OPTIONS):
            print(f"  String {i+1}: {bpm} BPM")
        
        # Wait for selection
        while True:
            data = await self.midi_characteristic.notified()
            msg = self.parse_midi_message(data)
            
            if msg and msg[0] == 'note_on':
                note = msg[1]
                print(f"BPM Menu - Note received: {note}")
                
                # Check if it's a 22nd fret note
                if note in SELECTION_NOTES:
                    selected_index = SELECTION_NOTES.index(note)
                    if selected_index < len(BPM_OPTIONS):
                        selected_bpm = BPM_OPTIONS[selected_index]
                        print(f"Selected: {selected_bpm} BPM")
                        
                        # Flash selection
                        self.tft.fill(self.COLOR_BLACK)
                        self.tft.text("Selected:", 80, 100, self.COLOR_GREEN)
                        self.tft.text(f"{selected_bpm} BPM", 85, 120, self.COLOR_YELLOW)
                        self.tft.show()
                        await asyncio.sleep_ms(500)
                        
                        return selected_bpm
    
    async def run_metronome(self, bpm=60):
        """Run visual metronome mode with chord practice
        
        Args:
            bpm: Beats per minute (default 60)
        
        Returns:
            'menu' if returning to menu, 'practice' if switching to practice mode
        """
        beat_interval_ms = int(60000 / bpm)  # Convert BPM to milliseconds
        beat_num = 0
        last_beat_time = utime.ticks_ms()
        
        # Metronome pattern: each entry is [chord, strum_direction]
        # Strum direction: True=Down, False=Up, None=Rest (no strum)
        metronome_pattern = [
            ['Em', True],    # Beat 1: C chord, down strum
            ['Em', True],   # Beat 2: C chord, up strum
            ['Em', False],    # Beat 3: C chord, rest
            ['Em', False],    # Beat 4: C chord, down strum
            ['Em', True],    # Beat 3: C chord, rest
            ['Em', False],    # Beat 4: C chord, down strum
            ['D6/9', True],    # Beat 5: G chord, down strum
            ['D6/9', True],   # Beat 6: G chord, up strum
            ['D6/9', False],    # Beat 7: G chord, rest
            ['D6/9', False],    # Beat 8: G chord, down strum
            ['D6/9', True],   # Beat 9: Am chord, down strum
            ['D6/9', False],   # Beat 9: Am chord, down strum
        ]
        pattern_index = 0
        current_chord = metronome_pattern[pattern_index][0]
        
        print(f"Metronome mode: {bpm} BPM")
        print("Play 22nd fret to switch mode or return to menu")
        
        # Create buffer for MIDI messages
        midi_buffer = []
        running = True
        
        async def midi_listener():
            """Background task to listen for MIDI"""
            while running:
                try:
                    data = await self.midi_characteristic.notified()
                    msg = self.parse_midi_message(data)
                    if msg and msg[0] == 'note_on':
                        midi_buffer.append(msg[1])
                except Exception as e:
                    await asyncio.sleep_ms(10)
        
        # Start MIDI listener in background
        listener_task = asyncio.create_task(midi_listener())
        
        try:
            while self.connected:
                # Check if new chord list was uploaded - return to menu
                if self.new_chord_list_uploaded:
                    print("[Menu] New chord list uploaded, returning to menu...")
                    self.new_chord_list_uploaded = False
                    running = False
                    listener_task.cancel()
                    return 'menu'
                
                # Check for menu selection notes
                if midi_buffer:
                    note = midi_buffer.pop(0)
                    print(f"Metronome - Note received: {note}")
                    
                    # Check if it's a 22nd fret note - return to menu
                    if note in SELECTION_NOTES:
                        print(f"22nd fret detected - returning to menu...")
                        running = False
                        listener_task.cancel()
                        return 'menu'
                
                # Check if time for next beat
                current_time = utime.ticks_ms()
                time_since_beat = utime.ticks_diff(current_time, last_beat_time)
                
                if time_since_beat >= beat_interval_ms:
                    # Time for next beat
                    beat_num_index = beat_num % 4  # 0-3 for pattern index
                    beat_num = (beat_num % 4) + 1  # 1-4 for display
                    last_beat_time = current_time
                    
                    # Move to next pattern entry
                    pattern_index = (pattern_index + 1) % len(metronome_pattern)
                    current_chord = metronome_pattern[pattern_index][0]
                    strum_direction = metronome_pattern[pattern_index][1]
                    
                    # Only redraw full display on beat 1, otherwise just update current beat indicator
                    if beat_num == 1:
                        # Draw full screen
                        self.tft.fill(self.COLOR_BLACK)
                        
                        # Show BPM at top
                        self.tft.text(f"{bpm} BPM", 90, 5, self.COLOR_YELLOW)
                        
                        # Draw beat squares with chords above and directions below
                        y_pos = 110
                        square_size = 35  # Larger squares
                        spacing = 50  # More space between squares
                        start_x = 20  # Start further left
                        
                        # Show next chord (2 beats ahead)
                        next_chord_index = (pattern_index + 2) % len(metronome_pattern)
                        next_chord = metronome_pattern[next_chord_index][0]
                        chord_x_offset = -5 if len(next_chord) > 1 else 5
                        self.draw_large_text(next_chord, 90 + chord_x_offset, 40, self.COLOR_YELLOW)
                        
                        for i in range(1, 5):
                            x_pos = start_x + (i - 1) * spacing
                            
                            # Get strum for this beat position
                            display_index = (pattern_index + i - 1) % len(metronome_pattern)
                            strum_for_beat = metronome_pattern[display_index][1]
                            
                            # Determine square color based on current beat
                            if i == beat_num:
                                # Current beat - always green
                                color = self.COLOR_GREEN
                            else:
                                # Not current beat - always white
                                color = self.COLOR_WHITE
                            
                            # Draw filled square
                            self.tft.fill_rect(x_pos, y_pos, square_size, square_size, color)
                            
                            # Draw beat number inside square in white
                            self.tft.text(str(i), x_pos + 13, y_pos + 13, self.COLOR_WHITE)
                            
                            # Draw strum direction arrow below square - larger
                            strum_dir = strum_for_beat
                            arrow_center_x = x_pos + (square_size // 2)
                            arrow_y = y_pos + square_size + 10
                            arrow_length = 18  # Increased from 12
                            arrow_head_size = 5  # Increased from 3-4
                            
                            if strum_dir is True:
                                # Down arrow - always green - thicker
                                strum_color = self.COLOR_GREEN
                                # Vertical line (thicker)
                                self.tft.vline(arrow_center_x, arrow_y, arrow_length, strum_color)
                                self.tft.vline(arrow_center_x + 1, arrow_y, arrow_length, strum_color)
                                # Arrow head (down)
                                for offset in range(3):
                                    self.tft.line(arrow_center_x, arrow_y + arrow_length, arrow_center_x - arrow_head_size, arrow_y + arrow_length - arrow_head_size + offset, strum_color)
                                    self.tft.line(arrow_center_x, arrow_y + arrow_length, arrow_center_x + arrow_head_size, arrow_y + arrow_length - arrow_head_size + offset, strum_color)
                            elif strum_dir is False:
                                # Up arrow - always blue - thicker
                                strum_color = self.COLOR_BLUE
                                # Vertical line (thicker)
                                self.tft.vline(arrow_center_x, arrow_y, arrow_length, strum_color)
                                self.tft.vline(arrow_center_x + 1, arrow_y, arrow_length, strum_color)
                                # Arrow head (up)
                                for offset in range(3):
                                    self.tft.line(arrow_center_x, arrow_y, arrow_center_x - arrow_head_size, arrow_y + arrow_head_size - offset, strum_color)
                                    self.tft.line(arrow_center_x, arrow_y, arrow_center_x + arrow_head_size, arrow_y + arrow_head_size - offset, strum_color)
                            else:
                                # Rest - X mark - always gray - larger and thicker
                                strum_color = self.tft.color565(100, 100, 100)
                                x_size = 7  # Increased from 4
                                for offset in range(3):
                                    self.tft.line(arrow_center_x - x_size, arrow_y + offset, arrow_center_x + x_size, arrow_y + arrow_length - offset, strum_color)
                                    self.tft.line(arrow_center_x + x_size, arrow_y + offset, arrow_center_x - x_size, arrow_y + arrow_length - offset, strum_color)
                    else:
                        # Just update the square colors for beat indication
                        y_pos = 110
                        square_size = 35
                        spacing = 50
                        start_x = 20
                        
                        # On beat 4, update square 1 with next chord info
                        if beat_num == 4:
                            # Clear and redraw square 1 area including chord above
                            x_pos = start_x
                            
                            # Clear area above square 1 for new chord
                            self.tft.fill_rect(x_pos - 10, y_pos - 70, 55, 65, self.COLOR_BLACK)
                            
                            # Get chord for next beat (beat 1)
                            next_beat_index = (pattern_index + 1) % len(metronome_pattern)
                            next_chord = metronome_pattern[next_beat_index][0]
                            chord_x_offset = -5 if len(next_chord) > 1 else 5
                            self.draw_large_text(next_chord, x_pos + chord_x_offset, y_pos - 50, self.COLOR_ORANGE)
                            
                            # Get strum direction for next beat
                            next_strum = metronome_pattern[next_beat_index][1]
                            
                            # Draw square 1 (white since not current beat)
                            self.tft.fill_rect(x_pos, y_pos, square_size, square_size, self.COLOR_WHITE)
                            self.tft.text("1", x_pos + 13, y_pos + 13, self.COLOR_WHITE)
                            
                            # Draw strum arrow for square 1
                            arrow_center_x = x_pos + (square_size // 2)
                            arrow_y = y_pos + square_size + 10
                            arrow_length = 18
                            arrow_head_size = 5
                            
                            # Clear arrow area first
                            self.tft.fill_rect(x_pos - 5, arrow_y - 2, square_size + 10, arrow_length + 12, self.COLOR_BLACK)
                            
                            if next_strum is True:
                                # Down arrow - green
                                strum_color = self.COLOR_GREEN
                                self.tft.vline(arrow_center_x, arrow_y, arrow_length, strum_color)
                                self.tft.vline(arrow_center_x + 1, arrow_y, arrow_length, strum_color)
                                for offset in range(3):
                                    self.tft.line(arrow_center_x, arrow_y + arrow_length, arrow_center_x - arrow_head_size, arrow_y + arrow_length - arrow_head_size + offset, strum_color)
                                    self.tft.line(arrow_center_x, arrow_y + arrow_length, arrow_center_x + arrow_head_size, arrow_y + arrow_length - arrow_head_size + offset, strum_color)
                            elif next_strum is False:
                                # Up arrow - blue
                                strum_color = self.COLOR_BLUE
                                self.tft.vline(arrow_center_x, arrow_y, arrow_length, strum_color)
                                self.tft.vline(arrow_center_x + 1, arrow_y, arrow_length, strum_color)
                                for offset in range(3):
                                    self.tft.line(arrow_center_x, arrow_y, arrow_center_x - arrow_head_size, arrow_y + arrow_head_size - offset, strum_color)
                                    self.tft.line(arrow_center_x, arrow_y, arrow_center_x + arrow_head_size, arrow_y + arrow_head_size - offset, strum_color)
                            else:
                                # Rest - X mark - gray
                                strum_color = self.tft.color565(100, 100, 100)
                                x_size = 7
                                for offset in range(3):
                                    self.tft.line(arrow_center_x - x_size, arrow_y + offset, arrow_center_x + x_size, arrow_y + arrow_length - offset, strum_color)
                                    self.tft.line(arrow_center_x + x_size, arrow_y + offset, arrow_center_x - x_size, arrow_y + arrow_length - offset, strum_color)
                        
                        for i in range(1, 5):
                            x_pos = start_x + (i - 1) * spacing
                            
                            # Determine square color based on current beat
                            if i == beat_num:
                                color = self.COLOR_GREEN
                            else:
                                color = self.COLOR_WHITE
                            
                            # Draw filled square
                            self.tft.fill_rect(x_pos, y_pos, square_size, square_size, color)
                            
                            # Draw beat number inside square in white
                            self.tft.text(str(i), x_pos + 13, y_pos + 13, self.COLOR_WHITE)
                    
                    self.tft.text("22nd fret string", 55, 190, self.COLOR_ORANGE)
                    self.tft.text("to change mode", 55, 210, self.COLOR_ORANGE)
                    
                    self.tft.show()
                
                # Small sleep to yield to other tasks
                await asyncio.sleep_ms(10)
                
        finally:
            running = False
            listener_task.cancel()
    
    async def run_strum_metronome(self, bpm=60):
        """Run visual metronome mode that advances on strum detection
        
        Args:
            bpm: Target BPM for timing display (default 60)
        
        Returns:
            'menu' if returning to menu, 'practice' if switching to practice mode
        """
        beat_num = 1
        beat_interval_ms = int(60000 / bpm)  # Convert BPM to milliseconds for timing comparison
        last_strum_time = 0
        
        # Metronome pattern: each entry is [chord, strum_direction]
        # Strum direction: True=Down, False=Up, None=Rest (no strum)
        metronome_pattern = [
            ['Em', True],    # Beat 1: Em chord, down strum
            ['Em', True],    # Beat 2: Em chord, down strum
            ['Em', False],   # Beat 3: Em chord, up strum
            ['Em', False],   # Beat 4: Em chord, up strum
            ['Em', True],    # Beat 5: Em chord, down strum
            ['Em', False],   # Beat 6: Em chord, up strum
            ['D6/9', True],  # Beat 7: D6/9 chord, down strum
            ['D6/9', True],  # Beat 8: D6/9 chord, down strum
            ['D6/9', False], # Beat 9: D6/9 chord, up strum
            ['D6/9', False], # Beat 10: D6/9 chord, up strum
            ['D6/9', True],  # Beat 11: D6/9 chord, down strum
            ['D6/9', False], # Beat 12: D6/9 chord, up strum
        ]
        pattern_index = 0
        current_chord = metronome_pattern[pattern_index][0]
        
        print(f"Strum Practice mode: Target {bpm} BPM")
        print("Strum to advance beats")
        print("Play 22nd fret to switch mode or return to menu")
        
        # Initial display
        self.tft.fill(self.COLOR_BLACK)
        self.tft.text("STRUM PRACTICE", 55, 5, self.COLOR_YELLOW)
        
        # Draw beat squares with chords above and directions below
        y_pos = 110
        square_size = 35  # Larger squares
        spacing = 50  # More space between squares
        start_x = 20  # Start further left
        
        # Show next chord (2 beats ahead)
        next_chord_index = (pattern_index + 2) % len(metronome_pattern)
        next_chord = metronome_pattern[next_chord_index][0]
        chord_x_offset = -5 if len(next_chord) > 1 else 5
        self.draw_large_text(next_chord, 90 + chord_x_offset, 40, self.COLOR_YELLOW)
        
        for i in range(1, 5):
            x_pos = start_x + (i - 1) * spacing
            
            # Get strum for this beat position
            display_index = (pattern_index + i - 1) % len(metronome_pattern)
            strum_for_beat = metronome_pattern[display_index][1]
            
            # Determine square color based on current beat
            if i == beat_num:
                # Current beat - always green
                color = self.COLOR_GREEN
            else:
                # Not current beat - always white
                color = self.COLOR_WHITE
            
            # Draw filled square
            self.tft.fill_rect(x_pos, y_pos, square_size, square_size, color)
            
            # Draw beat number inside square in white
            self.tft.text(str(i), x_pos + 13, y_pos + 13, self.COLOR_WHITE)
            
            # Draw strum direction arrow below square - larger
            strum_dir = strum_for_beat
            arrow_center_x = x_pos + (square_size // 2)
            arrow_y = y_pos + square_size + 10
            arrow_length = 18
            arrow_head_size = 5
            
            if strum_dir is True:
                # Down arrow - always green - thicker
                strum_color = self.COLOR_GREEN
                # Vertical line (thicker)
                self.tft.vline(arrow_center_x, arrow_y, arrow_length, strum_color)
                self.tft.vline(arrow_center_x + 1, arrow_y, arrow_length, strum_color)
                # Arrow head (down)
                for offset in range(3):
                    self.tft.line(arrow_center_x, arrow_y + arrow_length, arrow_center_x - arrow_head_size, arrow_y + arrow_length - arrow_head_size + offset, strum_color)
                    self.tft.line(arrow_center_x, arrow_y + arrow_length, arrow_center_x + arrow_head_size, arrow_y + arrow_length - arrow_head_size + offset, strum_color)
            elif strum_dir is False:
                # Up arrow - always blue - thicker
                strum_color = self.COLOR_BLUE
                # Vertical line (thicker)
                self.tft.vline(arrow_center_x, arrow_y, arrow_length, strum_color)
                self.tft.vline(arrow_center_x + 1, arrow_y, arrow_length, strum_color)
                # Arrow head (up)
                for offset in range(3):
                    self.tft.line(arrow_center_x, arrow_y, arrow_center_x - arrow_head_size, arrow_y + arrow_head_size - offset, strum_color)
                    self.tft.line(arrow_center_x, arrow_y, arrow_center_x + arrow_head_size, arrow_y + arrow_head_size - offset, strum_color)
            else:
                # Rest - X mark - always gray - larger and thicker
                strum_color = self.tft.color565(100, 100, 100)
                x_size = 7
                for offset in range(3):
                    self.tft.line(arrow_center_x - x_size, arrow_y + offset, arrow_center_x + x_size, arrow_y + arrow_length - offset, strum_color)
                    self.tft.line(arrow_center_x + x_size, arrow_y + offset, arrow_center_x - x_size, arrow_y + arrow_length - offset, strum_color)
        
        self.tft.text("22nd fret string", 55, 190, self.COLOR_ORANGE)
        self.tft.text("to change mode", 55, 210, self.COLOR_ORANGE)
        
        # Show target BPM
        self.tft.text(f"Target: {bpm} BPM", 70, 170, self.COLOR_YELLOW)
        
        self.tft.show()
        
        # Variables for debouncing strums and timing
        strum_debounce_ms = 200  # Ignore notes within 200ms of last strum
        timing_display_ms = 1500  # Show timing for 1.5 seconds
        
        try:
            while self.connected:
                # Check if new chord list was uploaded - return to menu
                if self.new_chord_list_uploaded:
                    print("[Menu] New chord list uploaded, returning to menu...")
                    self.new_chord_list_uploaded = False
                    return 'menu'
                
                # Wait for MIDI input with timeout to check flag periodically
                try:
                    data = await asyncio.wait_for(self.midi_characteristic.notified(), timeout=0.5)
                except asyncio.TimeoutError:
                    continue  # Timeout, loop back to check flag
                    
                msg = self.parse_midi_message(data)
                
                if msg and msg[0] == 'note_on':
                    note = msg[1]
                    current_time = utime.ticks_ms()
                    print(f"Strum Practice - Note received: {note}")
                    
                    # Check if it's a 22nd fret note - return to menu
                    if note in SELECTION_NOTES:
                        print(f"22nd fret detected - returning to menu...")
                        return 'menu'
                    
                    # Check if enough time has passed since last strum
                        time_since_last = utime.ticks_diff(current_time, last_strum_time)
                        if time_since_last < strum_debounce_ms:
                            print(f"Debouncing - only {time_since_last}ms since last strum")
                            continue
                        
                        # Calculate timing accuracy
                        timing_diff_ms = 0
                        bar_width = 0
                        bar_color = self.COLOR_WHITE
                        bar_x_pos = 120  # Center of bar graph
                        
                        if last_strum_time > 0:  # Not the first beat
                            timing_diff_ms = time_since_last - beat_interval_ms
                            
                            # Calculate bar width and color based on timing
                            # Max bar width = 100 pixels (50 pixels each side from center)
                            # Map timing difference to bar width (max 500ms = full width)
                            max_timing_for_full_bar = 500  # ms
                            bar_width = min(100, int(abs(timing_diff_ms) * 100 / max_timing_for_full_bar))
                            
                            # Determine color based on accuracy
                            if abs(timing_diff_ms) <= 50:  # Within 50ms - excellent
                                bar_color = self.COLOR_GREEN
                            elif abs(timing_diff_ms) <= 100:  # Within 100ms - good
                                bar_color = self.COLOR_YELLOW
                            else:  # More than 100ms off
                                bar_color = self.COLOR_RED
                        
                        # Update last strum time
                        last_strum_time = current_time
                        
                        # Any non-menu note advances the beat
                        beat_num_index = beat_num % 4
                        beat_num = (beat_num % 4) + 1
                        
                        # Move to next pattern entry
                        pattern_index = (pattern_index + 1) % len(metronome_pattern)
                        current_chord = metronome_pattern[pattern_index][0]
                        
                        # Redraw display based on beat
                        if beat_num == 1:
                            # Full redraw
                            self.tft.fill(self.COLOR_BLACK)
                            self.tft.text("STRUM PRACTICE", 55, 5, self.COLOR_YELLOW)
                            
                            # Show next chord (2 beats ahead)
                            next_chord_index = (pattern_index + 2) % len(metronome_pattern)
                            next_chord = metronome_pattern[next_chord_index][0]
                            chord_x_offset = -5 if len(next_chord) > 1 else 5
                            self.draw_large_text(next_chord, 90 + chord_x_offset, 40, self.COLOR_YELLOW)
                            
                            for i in range(1, 5):
                                x_pos = start_x + (i - 1) * spacing
                                
                                # Get strum for this beat position
                                display_index = (pattern_index + i - 1) % len(metronome_pattern)
                                strum_for_beat = metronome_pattern[display_index][1]
                                
                                # Determine square color
                                if i == beat_num:
                                    color = self.COLOR_GREEN
                                else:
                                    color = self.COLOR_WHITE
                                
                                # Draw filled square
                                self.tft.fill_rect(x_pos, y_pos, square_size, square_size, color)
                                self.tft.text(str(i), x_pos + 13, y_pos + 13, self.COLOR_WHITE)
                                
                                # Draw strum arrow
                                strum_dir = strum_for_beat
                                arrow_center_x = x_pos + (square_size // 2)
                                arrow_y = y_pos + square_size + 10
                                arrow_length = 18
                                arrow_head_size = 5
                                
                                if strum_dir is True:
                                    strum_color = self.COLOR_GREEN
                                    self.tft.vline(arrow_center_x, arrow_y, arrow_length, strum_color)
                                    self.tft.vline(arrow_center_x + 1, arrow_y, arrow_length, strum_color)
                                    for offset in range(3):
                                        self.tft.line(arrow_center_x, arrow_y + arrow_length, arrow_center_x - arrow_head_size, arrow_y + arrow_length - arrow_head_size + offset, strum_color)
                                        self.tft.line(arrow_center_x, arrow_y + arrow_length, arrow_center_x + arrow_head_size, arrow_y + arrow_length - arrow_head_size + offset, strum_color)
                                elif strum_dir is False:
                                    strum_color = self.COLOR_BLUE
                                    self.tft.vline(arrow_center_x, arrow_y, arrow_length, strum_color)
                                    self.tft.vline(arrow_center_x + 1, arrow_y, arrow_length, strum_color)
                                    for offset in range(3):
                                        self.tft.line(arrow_center_x, arrow_y, arrow_center_x - arrow_head_size, arrow_y + arrow_head_size - offset, strum_color)
                                        self.tft.line(arrow_center_x, arrow_y, arrow_center_x + arrow_head_size, arrow_y + arrow_head_size - offset, strum_color)
                                else:
                                    strum_color = self.tft.color565(100, 100, 100)
                                    x_size = 7
                                    for offset in range(3):
                                        self.tft.line(arrow_center_x - x_size, arrow_y + offset, arrow_center_x + x_size, arrow_y + arrow_length - offset, strum_color)
                                        self.tft.line(arrow_center_x + x_size, arrow_y + offset, arrow_center_x - x_size, arrow_y + arrow_length - offset, strum_color)
                            
                            self.tft.text("22nd fret string", 55, 190, self.COLOR_ORANGE)
                            self.tft.text("to change mode", 55, 210, self.COLOR_ORANGE)
                            
                            # Show target BPM
                            self.tft.text(f"Target: {bpm} BPM", 70, 170, self.COLOR_YELLOW)
                            
                            # Draw timing bar graph at bottom
                            bar_y = 225
                            bar_height = 10
                            # Draw center line
                            self.tft.vline(bar_x_pos, bar_y, bar_height, self.COLOR_WHITE)
                            # Draw timing bar if available
                            if bar_width > 0:
                                if timing_diff_ms > 0:  # Too slow - bar to the right
                                    self.tft.fill_rect(bar_x_pos, bar_y, bar_width, bar_height, bar_color)
                                else:  # Too fast - bar to the left
                                    self.tft.fill_rect(bar_x_pos - bar_width, bar_y, bar_width, bar_height, bar_color)
                        else:
                            # On beat 4, update square 1 with next chord info
                            if beat_num == 4:
                                # Clear and redraw square 1 area including chord above
                                x_pos = start_x
                                
                                # Clear area above square 1 for new chord
                                self.tft.fill_rect(x_pos - 10, y_pos - 70, 55, 65, self.COLOR_BLACK)
                                
                                # Get chord for next beat (beat 1)
                                next_beat_index = (pattern_index + 1) % len(metronome_pattern)
                                next_chord = metronome_pattern[next_beat_index][0]
                                chord_x_offset = -5 if len(next_chord) > 1 else 5
                                self.draw_large_text(next_chord, x_pos + chord_x_offset, y_pos - 50, self.COLOR_ORANGE)
                                
                                # Get strum direction for next beat
                                next_strum = metronome_pattern[next_beat_index][1]
                                
                                # Draw square 1 (white since not current beat)
                                self.tft.fill_rect(x_pos, y_pos, square_size, square_size, self.COLOR_WHITE)
                                self.tft.text("1", x_pos + 13, y_pos + 13, self.COLOR_WHITE)
                                
                                # Draw strum arrow for square 1
                                arrow_center_x = x_pos + (square_size // 2)
                                arrow_y = y_pos + square_size + 10
                                arrow_length = 18
                                arrow_head_size = 5
                                
                                # Clear arrow area first
                                self.tft.fill_rect(x_pos - 5, arrow_y - 2, square_size + 10, arrow_length + 12, self.COLOR_BLACK)
                                
                                if next_strum is True:
                                    strum_color = self.COLOR_GREEN
                                    self.tft.vline(arrow_center_x, arrow_y, arrow_length, strum_color)
                                    self.tft.vline(arrow_center_x + 1, arrow_y, arrow_length, strum_color)
                                    for offset in range(3):
                                        self.tft.line(arrow_center_x, arrow_y + arrow_length, arrow_center_x - arrow_head_size, arrow_y + arrow_length - arrow_head_size + offset, strum_color)
                                        self.tft.line(arrow_center_x, arrow_y + arrow_length, arrow_center_x + arrow_head_size, arrow_y + arrow_length - arrow_head_size + offset, strum_color)
                                elif next_strum is False:
                                    strum_color = self.COLOR_BLUE
                                    self.tft.vline(arrow_center_x, arrow_y, arrow_length, strum_color)
                                    self.tft.vline(arrow_center_x + 1, arrow_y, arrow_length, strum_color)
                                    for offset in range(3):
                                        self.tft.line(arrow_center_x, arrow_y, arrow_center_x - arrow_head_size, arrow_y + arrow_head_size - offset, strum_color)
                                        self.tft.line(arrow_center_x, arrow_y, arrow_center_x + arrow_head_size, arrow_y + arrow_head_size - offset, strum_color)
                                else:
                                    strum_color = self.tft.color565(100, 100, 100)
                                    x_size = 7
                                    for offset in range(3):
                                        self.tft.line(arrow_center_x - x_size, arrow_y + offset, arrow_center_x + x_size, arrow_y + arrow_length - offset, strum_color)
                                        self.tft.line(arrow_center_x + x_size, arrow_y + offset, arrow_center_x - x_size, arrow_y + arrow_length - offset, strum_color)
                            
                            # Update square colors
                            for i in range(1, 5):
                                x_pos = start_x + (i - 1) * spacing
                                
                                # Determine square color based on current beat
                                if i == beat_num:
                                    color = self.COLOR_GREEN
                                else:
                                    color = self.COLOR_WHITE
                                
                                # Draw filled square
                                self.tft.fill_rect(x_pos, y_pos, square_size, square_size, color)
                                self.tft.text(str(i), x_pos + 13, y_pos + 13, self.COLOR_WHITE)
                            
                            # Clear timing bar area and redraw
                            bar_y = 225
                            bar_height = 10
                            self.tft.fill_rect(0, bar_y, 240, bar_height, self.COLOR_BLACK)
                            # Draw center line
                            self.tft.vline(bar_x_pos, bar_y, bar_height, self.COLOR_WHITE)
                            # Draw timing bar if available
                            if bar_width > 0:
                                if timing_diff_ms > 0:  # Too slow - bar to the right
                                    self.tft.fill_rect(bar_x_pos, bar_y, bar_width, bar_height, bar_color)
                                else:  # Too fast - bar to the left
                                    self.tft.fill_rect(bar_x_pos - bar_width, bar_y, bar_width, bar_height, bar_color)
                        
                        self.tft.show()
                
        except Exception as e:
            print(f"Error in strum metronome: {e}")
            return 'menu'
    
    def parse_midi_message(self, data):
        """Parse BLE MIDI message"""
        if len(data) < 3:
            return None
        
        midi_status = data[2]
        
        # SysEx message (for chord list upload)
        if midi_status == 0xF0:
            return self.parse_sysex_message(data)
        
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
    
    def parse_sysex_message(self, data):
        """Parse SysEx message for chord list upload
        Format: F0 7D [name_len] [name_bytes] [mode] [chord_count] [chord1_len] [chord1_bytes] ... F7
        """
        try:
            # Skip BLE MIDI header (2 bytes)
            idx = 2
            
            # Check for SysEx start and manufacturer ID
            if data[idx] != 0xF0 or data[idx + 1] != 0x7D:
                return None
            
            idx += 2
            
            # Parse name
            name_len = data[idx]
            idx += 1
            name = bytes(data[idx:idx+name_len]).decode('utf-8')
            idx += name_len
            
            # Parse mode
            mode = chr(data[idx])
            idx += 1
            
            # Parse chord count
            chord_count = data[idx]
            idx += 1
            
            # Parse chords
            chords = []
            for _ in range(chord_count):
                chord_len = data[idx]
                idx += 1
                chord = bytes(data[idx:idx+chord_len]).decode('utf-8')
                idx += chord_len
                chords.append(chord)
            
            # Check for SysEx end
            if data[idx] == 0xF7:
                return ('chord_list', name, mode, chords)
            
        except Exception as e:
            print(f"Error parsing SysEx: {e}")
        
        return None
    
    def add_custom_chord_list(self, name, mode, chords):
        """Add a custom chord list to the practice options"""
        # Add to custom lists
        self.custom_chord_lists.append((name, [mode] + chords))
        print(f"Added custom list: {name} ({mode}) - {chords}")
        
        # Show confirmation on screen
        self.tft.fill(self.COLOR_BLACK)
        self.tft.text("Chord List Added!", 50, 100, self.COLOR_GREEN)
        self.tft.text(name, 60, 120, self.COLOR_YELLOW)
        self.tft.text(f"{len(chords)} chords", 80, 140, self.COLOR_WHITE)
        self.tft.show()
    
    def get_all_practice_options(self):
        """Get combined list of built-in and custom chord lists"""
        return PRACTICE_OPTIONS + self.custom_chord_lists
    
    async def serial_monitor_task(self):
        """Background task to continuously monitor serial input"""
        print("[Serial] Monitor task started")
        while True:
            try:
                # Check if data is available (non-blocking)
                rlist, _, _ = select.select([sys.stdin], [], [], 0)
                if rlist:
                    char = sys.stdin.read(1)
                    if char:
                        self.serial_buffer += char
                        
                        # Check if we have a complete message (ends with newline)
                        if '\n' in self.serial_buffer:
                            message = self.serial_buffer.strip()
                            self.serial_buffer = ""
                            
                            print(f"[Serial] Received: {message}")
                            
                            # Parse the message
                            if message.startswith("CHORD_LIST|"):
                                try:
                                    parts = message.split('|')
                                    if len(parts) >= 4:
                                        name = parts[1]
                                        mode = parts[2]
                                        chords = parts[3].split(',')
                                        
                                        # Add the chord list
                                        self.add_custom_chord_list(name, mode, chords)
                                        
                                        # Signal that menu should be refreshed
                                        self.new_chord_list_uploaded = True
                                        
                                        # Send acknowledgment
                                        print(f"OK: Added '{name}' with {len(chords)} chords")
                                except Exception as e:
                                    print(f"[Serial] Error parsing: {e}")
            except Exception as e:
                print(f"[Serial] Error: {e}")
            
            # Small delay to prevent tight loop
            await asyncio.sleep_ms(50)
    
    async def scan_and_connect(self, timeout_ms=30000):
        """Scan for and connect to Aeroband guitar"""
        # Start serial monitor task
        if not self.serial_task:
            self.serial_task = asyncio.create_task(self.serial_monitor_task())
        
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
        notes_hit = False
        last_note = None
        time_last_chord = 0
        strum_start_time = 0  # Track when strum started
        strum_timeout_ms = 750  # 0.75 second timeout
        started = False
        last_string = 0
        up = False
        timeout_task = None  # Track the timeout task
        
        async def timeout_handler():
            """Handle timeout - wait for timeout period then reset"""
            await asyncio.sleep_ms(strum_timeout_ms)
            print("Timeout! Resetting strum...")
            nonlocal started, notes_hit, timeout_task
            started = False
            notes_hit = False
            self.played_notes = [None] * 6
            timeout_task = None
            
            # Redisplay clean target
            if self.sequence_mode:
                target_chord = self.chord_sequence[self.current_chord_index]
                self.update_live_display(target_chord, set(), 0.0)
        
        try:
            while self.connected:
                # Check if new chord list was uploaded - return to menu
                if self.new_chord_list_uploaded:
                    print("[Menu] New chord list uploaded, returning to menu...")
                    self.new_chord_list_uploaded = False
                    return 'menu'
                
                # Wait for MIDI data with timeout to check flag periodically
                try:
                    data = await asyncio.wait_for(self.midi_characteristic.notified(), timeout=0.5)
                except asyncio.TimeoutError:
                    continue  # Timeout, loop back to check flag
                
                # Parse message
                msg = self.parse_midi_message(data)
                
                if msg:
                    if msg[0] == 'note_on':
                        note = msg[1]
                        print(f"Note On: {note}")
                        
                        # Check if it's a 22nd fret note - return to menu (but only if isolated)
                        if note in SELECTION_NOTES:
                            # Wait a short moment to see if more notes come (indicating a chord strum)
                            await asyncio.sleep_ms(100)
                            
                            # Count how many notes are currently active in played_notes
                            active_notes = sum(1 for n in self.played_notes if n is not None)
                            
                            # Only treat as menu trigger if it's a single isolated note
                            if active_notes <= 1:
                                print(f"22nd fret detected on string {SELECTION_NOTES.index(note)+1} - returning to menu...")
                                return 'menu'
                            else:
                                print(f"22nd fret in chord strum ({active_notes} notes), ignoring for menu")
                        
                        # Check time difference FIRST before processing
                        if utime.ticks_diff(utime.ticks_ms(), time_last_chord) > 500:
                            print("Resetting due to time difference")
                            started = False
                            notes_hit = False
                            self.played_notes = [None] * 6
                            last_note = None  # Clear last_note on reset

                        time_last_chord = utime.ticks_ms()
                        
                        string_n = STRING_NUMBER.get(note)
                        if string_n is None:
                            print(f"WARNING: Note {note} not in STRING_NUMBER mapping!")
                        # Reverse array: string 6 at index 0, string 1 at index 5
                        string_num = (6 - string_n) if string_n else 0
                        print(f"Note {note} -> String {string_n}, array index {string_num}")

                        if note == last_note:
                            continue

                        # Store note on the string, replacing if it's lower (higher fret)
                        current_note = self.played_notes[string_num]
                        if current_note is None or note > current_note:
                            self.played_notes[string_num] = note
                            print(f"String {string_num + 1}: set to note {note}")
                        else:
                            print(f"String {string_num + 1}: kept {current_note} (ignoring {note})")

                        print(f"Current strings: {self.played_notes}")

                        last_note = note

                        if not started: 
                            if string_num == 5 or string_num == 0:
                                print('Started strum!')
                                started = True
                                strum_start_time = utime.ticks_ms()  # Start timer
                                if string_num == 5:
                                    up = False       
                                else:
                                    up = True
                                
                                # Cancel any existing timeout task
                                if timeout_task is not None:
                                    timeout_task.cancel()
                                
                                # Start new timeout task
                                timeout_task = asyncio.create_task(timeout_handler())
                        
                        # Update display in real-time as notes are played
                        if started and self.sequence_mode:
                            target_chord = self.chord_sequence[self.current_chord_index]
                            elapsed = utime.ticks_diff(utime.ticks_ms(), strum_start_time)
                            progress = min(1.0, elapsed / strum_timeout_ms)
                            # Convert array to set for display (filter out None values)
                            played_set = set(n for n in self.played_notes if n is not None)
                            self.update_live_display(target_chord, played_set, progress)
                        
                        if not started:
                            continue

                        # Check if we've completed a strum (reached opposite end)
                        if up:
                            if string_num == 5:
                                print("Strum complete (reached string 6)! -------------------------------------------------------------------")
                                started = False
                                up = False
                                notes_hit = True
                                # Cancel timeout since strum completed
                                if timeout_task is not None:
                                    timeout_task.cancel()
                                    timeout_task = None
                        else:
                            if string_num == 0:
                                print("Strum complete (reached string 1)! -------------------------------------------------------------------")
                                started = False
                                up = True
                                notes_hit = True
                                # Cancel timeout since strum completed
                                if timeout_task is not None:
                                    timeout_task.cancel()
                                    timeout_task = None  

                        last_string = string_num
                        
                        # If we haven't completed the strum yet, continue collecting notes
                        if not notes_hit:
                            continue
                        
                        
                        print("All strings played! -------------------------------------------------------------------")

                        # Capture the played notes (convert array to set, filter out None)
                        played_notes_copy = set(n for n in self.played_notes if n is not None)
                        
                        print(f"Played notes: {sorted(played_notes_copy)}")
                        print(f"String array: {self.played_notes}")

                        if True or self.sequence_mode:
                            target_chord = self.chord_sequence[self.current_chord_index]
                            expected_notes = set(CHORD_MIDI_NOTES.get(target_chord, []))
                            print(f"Target chord: {target_chord}, Expected notes: {sorted(expected_notes)}")
                            
                            # Show which notes match
                            matching = played_notes_copy.intersection(expected_notes)
                            missing = expected_notes - played_notes_copy
                            extra = played_notes_copy - expected_notes
                            print(f"Matching notes: {sorted(matching)}")
                            print(f"Missing notes: {sorted(missing)}")
                            print(f"Extra notes: {sorted(extra)}")
                            
                            # Check if notes match exactly (all required notes, no missing, no extra)
                            is_correct = played_notes_copy.issuperset(expected_notes)
                            
                            if is_correct:
                                # Correct!
                                print("Correct chord!")
                                self.display_correct_chord(target_chord)
                                await asyncio.sleep_ms(500)
                                
                                # Move to next chord
                                self.current_chord_index += 1
                                
                                if self.current_chord_index >= len(self.chord_sequence):
                                    # Sequence complete! Check if should randomize
                                    if self.randomize_mode == 'R':
                                        print("Sequence complete! Randomizing and starting over...")
                                        
                                        # Fisher-Yates shuffle algorithm
                                        shuffled = list(self.chord_sequence)
                                        n = len(shuffled)
                                        for i in range(n - 1, 0, -1):
                                            j = urandom.getrandbits(16) % (i + 1)
                                            shuffled[i], shuffled[j] = shuffled[j], shuffled[i]
                                        
                                        self.chord_sequence = shuffled
                                        print(f"New randomized order: {self.chord_sequence}")
                                    else:
                                        print("Sequence complete! Starting over in same order...")
                                    
                                    self.current_chord_index = 0
                                
                                # Show next target (or first target if looping)
                                self.display_target_chord()
                            else:
                                # Wrong - show what was played
                                print(f"Wrong! Not enough matching notes")
                                print(f"About to call display_wrong_chord with notes: {played_notes_copy}")
                                self.display_wrong_chord("???", played_notes_copy, target_chord)
                                print("display_wrong_chord completed")
                                
                                # Wait a moment to show the wrong chord
                                await asyncio.sleep_ms(500)
                                
                                # Clear played notes for next attempt
                                self.played_notes = [None] * 6
                                
                                # Redisplay the target chord for next attempt
                                self.update_live_display(target_chord, set(), 0.0)
                                
                                # Reset last_detected_chord so next chord attempt will be detected
                                self.last_detected_chord = None
                        
                        # ALWAYS reset notes_hit after processing
                        notes_hit = [False, False, False, False, False, False]
                        last_note = None  # Clear last_note for next attempt
                        # Cancel timeout task if still running
                        if timeout_task is not None:
                            timeout_task.cancel()
                            timeout_task = None
                        print("Reset notes_hit for next attempt")
                    
                
                # await asyncio.sleep_ms(10)
                
        except Exception as e:
            print(f"MIDI handler error: {e}")
            self.connected = False
    
    async def show_menu_and_wait_for_selection(self, page=0):
        """Show practice menu and wait for user to select with 22nd fret note
        
        Args:
            page: Current page number (0-indexed)
        """
        current_selection = 0
        
        # Get all options (built-in + custom)
        all_options = self.get_all_practice_options()
        
        # Calculate pagination
        items_per_page = 5  # Show 5 items + "More" option on string 6
        total_pages = (len(all_options) + items_per_page - 1) // items_per_page
        page = page % total_pages if total_pages > 0 else 0  # Wrap around
        start_idx = page * items_per_page
        end_idx = min(start_idx + items_per_page, len(all_options))
        page_options = all_options[start_idx:end_idx]
        has_more_pages = total_pages > 1  # Always show More if multiple pages
        
        # Display menu
        self.tft.fill(self.COLOR_BLACK)
        self.tft.text("Select Practice:", 50, 10, self.COLOR_YELLOW)
        self.tft.text("Use 22nd fret", 55, 30, self.COLOR_WHITE)
        
        # Show page indicator if multiple pages
        if has_more_pages:
            self.tft.text(f"Page {page+1}/{total_pages}", 80, 220, self.COLOR_BLUE)
        
        # Show options (up to 5 items)
        y_pos = 50
        for i, (name, _) in enumerate(page_options):
            color = self.COLOR_GREEN if i == current_selection else self.COLOR_WHITE
            marker = ">" if i == current_selection else " "
            self.tft.text(f"{marker}{i+1}. {name}", 30, y_pos, color)
            y_pos += 20
        
        # Show "More" option on string 6 if there are multiple pages
        if has_more_pages:
            next_page = (page + 1) % total_pages
            self.tft.text(f" 6. More... (page {next_page+1})", 30, y_pos, self.COLOR_ORANGE)
        
        self.tft.text("String 1-5 = options", 30, 185, self.COLOR_WHITE)
        if has_more_pages:
            self.tft.text("String 6 = More", 40, 200, self.COLOR_ORANGE)
        
        self.tft.show()
        
        print(f"Menu page {page+1}/{total_pages} displayed. Waiting for 22nd fret selection...")
        print("Play 22nd fret on:")
        for i, (name, _) in enumerate(page_options):
            print(f"  String {i+1}: {name}")
        if has_more_pages:
            next_page = (page + 1) % total_pages
            print(f"  String 6: More... (go to page {next_page+1})")
        
        # Wait for selection
        while True:
            # Check if new chord list was uploaded - refresh menu
            if self.new_chord_list_uploaded:
                print("[Menu] New chord list uploaded, refreshing menu...")
                self.new_chord_list_uploaded = False
                # Refresh menu to show new list
                return await self.show_menu_and_wait_for_selection()
            
            # Wait for MIDI data with timeout to allow periodic checks
            try:
                data = await asyncio.wait_for(self.midi_characteristic.notified(), timeout=0.5)
            except asyncio.TimeoutError:
                continue  # Timeout, loop back
                
            msg = self.parse_midi_message(data)
            
            if msg:
                # Handle chord list upload
                if msg[0] == 'chord_list':
                    _, name, mode, chords = msg
                    self.add_custom_chord_list(name, mode, chords)
                    await asyncio.sleep_ms(2000)
                    # Refresh menu to show new list
                    return await self.show_menu_and_wait_for_selection()
                
                elif msg[0] == 'note_on':
                    note = msg[1]
                    print(f"Menu - Note received: {note}")
                    
                    # Check if it's a 22nd fret note
                    if note in SELECTION_NOTES:
                        selected_string = SELECTION_NOTES.index(note)
                        
                        # String 6 (index 5) is "More" if there are multiple pages
                        if selected_string == 5 and has_more_pages:
                            print("More selected, showing next page...")
                            return await self.show_menu_and_wait_for_selection(page + 1)
                        
                        # Regular selection
                        selected_index = start_idx + selected_string
                        if selected_string < len(page_options):
                            print(f"Selected: {all_options[selected_index][0]}")
                            
                            # Flash selection
                            self.tft.fill(self.COLOR_BLACK)
                            name, chords = all_options[selected_index]
                            self.tft.text("Selected:", 80, 100, self.COLOR_GREEN)
                            self.tft.text(name, 85, 120, self.COLOR_YELLOW)
                            self.tft.show()
                            await asyncio.sleep_ms(500)
                            
                            return chords
            
            #await asyncio.sleep_ms(10)
    
    async def run(self):
        """Main run loop with menu system"""
        if not await self.scan_and_connect():
            print("Failed to connect")
            return
        
        # Main loop - show menu when needed
        while True:
            # Show menu and wait for selection
            print("Showing practice menu...")
            selected_chords = await self.show_menu_and_wait_for_selection()
            
            # Set the chord sequence - extract mode if present
            if len(selected_chords) > 0 and selected_chords[0] in ['R', 'S']:
                self.randomize_mode = selected_chords[0]
                self.chord_sequence = selected_chords[1:]
            else:
                # Empty or special mode (metronome, strum)
                self.chord_sequence = selected_chords
            
            self.sequence_mode = True  # Always in sequence mode now
            self.current_chord_index = 0
            
            print(f"Starting practice: {len(self.chord_sequence)} chords")
            print("Starting MIDI handler...")
            print("Play 22nd fret on any string to return to menu")
            
            # Run the selected mode
            try:
                # Check if metronome mode
                if len(self.chord_sequence) == 0:
                    print("Metronome mode selected")
                    # Show BPM selection menu
                    selected_bpm = await self.show_bpm_menu()
                    result = await self.run_metronome(bpm=selected_bpm)
                # Check if strum practice mode
                elif self.chord_sequence == ['STRUM']:
                    print("Strum Practice mode selected")
                    # Show BPM selection menu
                    selected_bpm = await self.show_bpm_menu()
                    result = await self.run_strum_metronome(bpm=selected_bpm)
                # Regular chord practice
                else:
                    result = await self.handle_midi()
                
                # Any result returns to menu (outer loop continues)
            except Exception as e:
                print(f"Error: {e}")
        
        # Disconnect when exiting (this code is now unreachable but kept for safety)
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
