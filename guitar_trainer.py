# Guitar Trainer - Display notes from Aeroband guitar on GC9A01 display
import asyncio
import aioble
import bluetooth
import network
from gc9a01_spi_fb import GC9A01_SPI_FB
from machine import SPI, Pin
from micropython import const

# Import large fonts
import LibreBodoni48 as large_font

# BLE MIDI Service and Characteristic UUIDs
_MIDI_SERVICE_UUID = bluetooth.UUID("03B80E5A-EDE8-4B33-A751-6CE34EC4C700")
_MIDI_CHAR_UUID = bluetooth.UUID("7772E5DB-3868-4112-A1A9-F2669D106BF3")

# Note names
NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

# Chord definitions - Format: {chord_name: [(string, fret), ...]}
# String 1 = high E, String 6 = low E
# X or negative fret means don't play that string
CHORD_SHAPES = {
    'C': [(6, -1), (5, 3), (4, 2), (3, 0), (2, 1), (1, 0)],      # X32010
    'G': [(6, 3), (5, 2), (4, 0), (3, 0), (2, 0), (1, 3)],       # 320003
    'D': [(6, -1), (5, -1), (4, 0), (3, 2), (2, 3), (1, 2)],     # XX0232
    'A': [(6, -1), (5, 0), (4, 2), (3, 2), (2, 2), (1, 0)],      # X02220
    'E': [(6, 0), (5, 2), (4, 2), (3, 1), (2, 0), (1, 0)],       # 022100
    'Am': [(6, -1), (5, 0), (4, 2), (3, 2), (2, 1), (1, 0)],     # X02210
    'Em': [(6, 0), (5, 2), (4, 2), (3, 0), (2, 0), (1, 0)],      # 022000
    'Dm': [(6, -1), (5, -1), (4, 0), (3, 2), (2, 3), (1, 1)],    # XX0231
}

# MIDI notes that make up each chord (for detection)
# Using root position triads
CHORD_MIDI_NOTES = {
    'C': [48, 52, 55],    # C3, E3, G3
    'G': [43, 47, 50, 55, 59, 67],  # G2, B2, D3, G3, B3, G4
    'D': [50, 54, 57, 62],  # D3, F#3, A3, D4
    'A': [45, 49, 52, 57],  # A2, C#3, E3, A3
    'E': [40, 44, 47, 52, 56, 64],  # E2, G#2, B2, E3, G#3, E4
    'Am': [45, 48, 52, 57], # A2, C3, E3, A3
    'Em': [40, 43, 47, 52, 55, 64], # E2, G2, B2, E3, G3, E4
    'Dm': [50, 53, 57, 62], # D3, F3, A3, D4
}

def midi_note_to_name(note):
    """Convert MIDI note number to note name with octave"""
    octave = (note // 12) - 1
    note_name = NOTE_NAMES[note % 12]
    return f"{note_name}{octave}"

def get_chord_shape(chord_name):
    """Get chord fingering positions"""
    return CHORD_SHAPES.get(chord_name, None)

def get_chord_notes(chord_name):
    """Get MIDI notes for a chord"""
    return CHORD_MIDI_NOTES.get(chord_name, [])

class GuitarTrainer:
    """Display guitar chords on GC9A01 display"""
    
    def __init__(self, chord_sequence=None):
        """
        Initialize Guitar Trainer
        
        Args:
            chord_sequence: List of chord names to practice (e.g., ['C', 'G', 'D', 'Am'])
                          If None, displays all chords as played
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
        
        # Clear screen
        self.tft.fill(self.COLOR_BLACK)
        self.tft.text("Chord Trainer", 60, 100, self.COLOR_WHITE)
        self.tft.text("Waiting...", 80, 120, self.COLOR_GREEN)
        self.tft.show()
        
        print("Display ready!")
        if self.sequence_mode:
            print(f"Practice sequence loaded: {len(self.chord_sequence)} chords")
        
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
        
        # Clear screen
        self.tft.fill(self.COLOR_BLACK)
        self.tft.text("Chord Trainer", 60, 100, self.COLOR_WHITE)
        self.tft.text("Waiting...", 80, 120, self.COLOR_GREEN)
        self.tft.show()
        
        print("Display ready!")
        if self.sequence_mode:
            print(f"Practice sequence loaded: {len(self.chord_sequence)} chords")
    
    def draw_large_text(self, text, x, y, color, scale=10):
        """Draw text using the large font"""
        # Use draw_text instead of text for custom font
        self.tft.draw_text(text, x, y, color)
    
    def draw_fretboard(self, string_num, fret_num, highlight_color):
        """Draw a simplified fretboard diagram showing finger position
        
        Args:
            string_num: Guitar string (1=high E, 6=low E)
            fret_num: Fret number (0=open)
            highlight_color: Color to highlight the position
        """
        # Fretboard area at bottom of screen
        start_x = 20
        start_y = 160
        string_spacing = 10
        fret_width = 30
        
        # Draw 6 strings (horizontal lines)
        for i in range(6):
            y = start_y + (i * string_spacing)
            self.tft.hline(start_x, y, 200, self.COLOR_WHITE)
        
        # Draw 5 frets (vertical lines)
        for i in range(1, 6):
            x = start_x + (i * fret_width)
            self.tft.vline(x, start_y, string_spacing * 5, self.COLOR_WHITE)
        
        # Draw fret numbers
        for i in range(5):
            x = start_x + (i * fret_width) + fret_width // 2 - 4
            y = start_y + string_spacing * 5 + 5
            self.tft.text(str(fret_num + i) if fret_num + i > 0 else "0", x, y, self.COLOR_WHITE)
        
        # Highlight the finger position
        if fret_num == 0:
            # Open string - small filled square to the left of fretboard
            string_y = start_y + ((string_num - 1) * string_spacing)
            self.tft.fill_rect(start_x - 12, string_y - 3, 6, 6, highlight_color)
        else:
            # Calculate position on fretboard
            # Center the display around the target fret
            display_fret = fret_num
            if fret_num > 2:
                display_fret = 2  # Show fret in middle position
            
            string_y = start_y + ((string_num - 1) * string_spacing)
            fret_x = start_x + (display_fret * fret_width) - (fret_width // 2)
            self.tft.fill_rect(fret_x - 4, string_y - 4, 8, 8, highlight_color)
    
    def display_target_note(self):
        """Display the current target note to play"""
        if not self.sequence_mode or self.current_sequence_index >= len(self.note_sequence):
            return
        
        target_note = self.note_sequence[self.current_sequence_index]
        note_name = midi_note_to_name(target_note)
        
        # Clear screen
        self.tft.fill(self.COLOR_BLACK)
        
        # Show progress (use regular text method)
        progress_text = f"{self.current_sequence_index + 1}/{len(self.note_sequence)}"
        self.tft.text(progress_text, 90, 10, self.COLOR_WHITE)
        
        # Draw LARGE note name with custom font (centered)
        x_pos = 90 if len(note_name) == 2 else 80
        self.draw_large_text(note_name, x_pos, 40, self.COLOR_ORANGE)
        
        # Show fingering information
        fingering = get_guitar_fingering(target_note)
        if fingering:
            string_num, fret_num = fingering
            fing_text = f"String {string_num}, Fret {fret_num}"
            self.tft.text(fing_text, 50, 110, self.COLOR_WHITE)
            # Draw fretboard diagram
            self.draw_fretboard(string_num, fret_num, self.COLOR_ORANGE)
        
        self.tft.show()
        print(f"Target note: {note_name} (MIDI: {target_note})")
        if fingering:
            print(f"  -> String {fingering[0]}, Fret {fingering[1]}")
    
    def display_correct_note(self, note=None):
        """Display success feedback"""
        if not self.sequence_mode:
            return
        
        # Use the passed note, or get from current index
        if note is None:
            if self.current_sequence_index < len(self.note_sequence):
                note = self.note_sequence[self.current_sequence_index]
            else:
                return
        
        note_name = midi_note_to_name(note)
        
        self.tft.fill(self.COLOR_BLACK)
        
        # Large success message
        x_pos = 90 if len(note_name) == 2 else 80
        self.draw_large_text(note_name, x_pos, 40, self.COLOR_GREEN)
        
        # Show fingering in green
        fingering = get_guitar_fingering(note)
        if fingering:
            string_num, fret_num = fingering
            fing_text = f"String {string_num}, Fret {fret_num}"
            self.tft.text(fing_text, 50, 110, self.COLOR_GREEN)
            self.draw_fretboard(string_num, fret_num, self.COLOR_GREEN)
        
        # Show progress
        progress_text = f"{self.current_sequence_index + 1}/{len(self.note_sequence)}"
        self.tft.text(progress_text, 90, 10, self.COLOR_WHITE)
        
        self.tft.show()
    
    def display_wrong_note(self, played_note):
        """Display when wrong note is played"""
        note_name = midi_note_to_name(played_note)
        
        self.tft.fill(self.COLOR_BLACK)
        
        # Show what they played (large font in red)
        x_pos = 95 if len(note_name) == 2 else 85
        self.draw_large_text(note_name, x_pos, 40, self.COLOR_RED)
        
        # Show fingering for what was played
        fingering = get_guitar_fingering(played_note)
        if fingering:
            string_num, fret_num = fingering
            fing_text = f"String {string_num}, Fret {fret_num}"
            self.tft.text(fing_text, 50, 110, self.COLOR_RED)
            self.draw_fretboard(string_num, fret_num, self.COLOR_RED)
        
        self.tft.show()
    
    def display_sequence_complete(self):
        """Display when sequence is complete"""
        self.tft.fill(self.COLOR_BLACK)
        
        self.draw_large_text("DONE", 70, 100, self.COLOR_GREEN)
        self.tft.text("Great job!", 75, 180, self.COLOR_YELLOW)
        
        self.tft.show()
    
    def display_note(self, note, velocity):
        """Display the note on screen (free play mode)"""
        note_name = midi_note_to_name(note)
        self.current_note = note
        self.current_note_name = note_name
        
        # Clear screen
        self.tft.fill(self.COLOR_BLACK)
        
        # Draw LARGE note name with custom font
        x_pos = 90 if len(note_name) == 2 else 80
        self.draw_large_text(note_name, x_pos, 90, self.COLOR_GREEN)
        
        # Draw velocity bar
        bar_width = int((velocity / 127) * 200)
        self.tft.fill_rect(20, 160, bar_width, 20, self.COLOR_YELLOW)
        self.tft.rect(20, 160, 200, 20, self.COLOR_WHITE)
        
        # Show velocity number
        self.tft.text(f"Vel: {velocity}", 90, 190, self.COLOR_WHITE)
        
        # Show MIDI note number
        self.tft.text(f"MIDI: {note}", 85, 210, self.COLOR_WHITE)
        
        self.tft.show()
        print(f"Displayed: {note_name} (velocity: {velocity})")
    
    def clear_note(self):
        """Clear the note display"""
        self.tft.fill(self.COLOR_BLACK)
        self.tft.text("Ready...", 85, 120, self.COLOR_BLUE)
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
        # Initialize WiFi for BLE
        print("Initializing Bluetooth...")
        wlan = network.WLAN(network.STA_IF)
        wlan.active(True)
        await asyncio.sleep(1)
        
        self.tft.fill(self.COLOR_BLACK)
        self.tft.text("Scanning for", 70, 100, self.COLOR_WHITE)
        self.tft.text("Aeroband...", 75, 120, self.COLOR_YELLOW)
        self.tft.show()
        
        print("Scanning for Aeroband guitar...")
        
        async with aioble.scan(timeout_ms, interval_us=30000, window_us=30000, active=True) as scanner:
            async for result in scanner:
                # Look for MIDI service or Aeroband name
                if _MIDI_SERVICE_UUID in result.services():
                    print(f"Found MIDI device: {result.name()} [{result.device}]")
                    
                    try:
                        self.tft.fill(self.COLOR_BLACK)
                        self.tft.text("Connecting...", 70, 120, self.COLOR_GREEN)
                        self.tft.show()
                        
                        print("Connecting...")
                        self.connection = await result.device.connect()
                        print("Connected!")
                        
                        # Get MIDI service
                        midi_service = await self.connection.service(_MIDI_SERVICE_UUID)
                        self.midi_characteristic = await midi_service.characteristic(_MIDI_CHAR_UUID)
                        
                        self.connected = True
                        
                        self.tft.fill(self.COLOR_BLACK)
                        self.tft.text("Connected!", 75, 100, self.COLOR_GREEN)
                        self.tft.text("Play guitar!", 70, 120, self.COLOR_YELLOW)
                        self.tft.show()
                        
                        await asyncio.sleep(2)
                        self.clear_note()
                        
                        return True
                        
                    except Exception as e:
                        print(f"Connection failed: {e}")
                        self.tft.fill(self.COLOR_BLACK)
                        self.tft.text("Failed!", 90, 120, self.COLOR_RED)
                        self.tft.show()
                        return False
                
                # Check for Aeroband in name
                name = result.name()
                if name and ("aeroband" in name.lower() or "pocketdrum" in name.lower()):
                    print(f"Found possible Aeroband: {name}")
                    try:
                        self.tft.fill(self.COLOR_BLACK)
                        self.tft.text("Connecting...", 70, 120, self.COLOR_GREEN)
                        self.tft.show()
                        
                        self.connection = await result.device.connect()
                        midi_service = await self.connection.service(_MIDI_SERVICE_UUID)
                        self.midi_characteristic = await midi_service.characteristic(_MIDI_CHAR_UUID)
                        
                        self.connected = True
                        
                        self.tft.fill(self.COLOR_BLACK)
                        self.tft.text("Connected!", 75, 100, self.COLOR_GREEN)
                        self.tft.text("Play guitar!", 70, 120, self.COLOR_YELLOW)
                        self.tft.show()
                        
                        await asyncio.sleep(2)
                        self.clear_note()
                        
                        return True
                        
                    except Exception as e:
                        print(f"Connection failed: {e}")
        
        self.tft.fill(self.COLOR_BLACK)
        self.tft.text("Not found!", 75, 120, self.COLOR_RED)
        self.tft.show()
        print("Aeroband not found")
        return False
    
    async def handle_midi(self):
        """Listen for MIDI messages and display notes"""
        if not self.connected or not self.midi_characteristic:
            print("Not connected")
            return
        
        print("Listening for notes...")
        
        # If in sequence mode, show first target note
        if self.sequence_mode:
            self.display_target_note()
        
        try:
            while self.connected:
                # Wait for MIDI data
                data = await self.midi_characteristic.notified()
                
                # Parse message
                msg = self.parse_midi_message(data)
                
                if msg:
                    if msg[0] == 'note_on':
                        note = msg[1]
                        velocity = msg[2]
                        print(f"Note ON: {note} (velocity: {velocity})")
                        
                        if self.sequence_mode:
                            # Check if correct note in sequence
                            if self.current_sequence_index < len(self.note_sequence):
                                target_note = self.note_sequence[self.current_sequence_index]
                                
                                if note == target_note:
                                    # Correct note!
                                    print("Correct note!")
                                    self.display_correct_note(note)
                                    await asyncio.sleep_ms(800)
                                    
                                    # Move to next note
                                    self.current_sequence_index += 1
                                    
                                    if self.current_sequence_index >= len(self.note_sequence):
                                        # Sequence complete!
                                        print("Sequence complete!")
                                        self.display_sequence_complete()
                                        await asyncio.sleep(2)
                                        
                                        # Restart sequence
                                        self.current_sequence_index = 0
                                        self.display_target_note()
                                    else:
                                        # Show next target
                                        self.display_target_note()
                                else:
                                    # Wrong note
                                    print(f"Wrong note! Expected {target_note}, got {note}")
                                    self.display_wrong_note(note)
                                    await asyncio.sleep_ms(1000)
                                    # Show target again
                                    self.display_target_note()
                        else:
                            # Free play mode - just display the note
                            self.display_note(note, velocity)
                        
                    elif msg[0] == 'note_off':
                        note = msg[1]
                        print(f"Note OFF: {note}")
                        # In free play mode, clear after note off
                        if not self.sequence_mode:
                            await asyncio.sleep_ms(100)
                            self.clear_note()
                
                await asyncio.sleep_ms(10)
                
        except Exception as e:
            print(f"MIDI handler error: {e}")
            self.connected = False
            self.tft.fill(self.COLOR_BLACK)
            self.tft.text("Disconnected", 70, 120, self.COLOR_RED)
            self.tft.show()
    
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
    # Beginner-friendly practice sequences using only first 4 frets
    
    # Simple open strings
    open_strings = [40, 45, 50, 55, 64]  # E A D G E (open strings)
    
    # Low E string (frets 0-4)
    low_e_scale = [40, 41, 42, 43, 44]  # E F F# G G# on 6th string
    
    # Simple melody on high strings (frets 0-4)
    simple_melody = [64, 65, 66, 67, 68]  # E F F# G G# on 1st string
    
    # Mix of open strings and first fret
    beginner_mix = [40, 45, 50, 55, 60, 64]  # E A D G C E
    
    walk = [45, 49, 50, 52]  # A C C# D C# C A

    # Choose your practice sequence:
    practice_notes = walk
    
    # For free play mode (displays any note you play), pass None or empty list:
    # trainer = GuitarTrainer()
    
    # For practice mode with sequence:
    trainer = GuitarTrainer(note_sequence=practice_notes)
    
    await trainer.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Stopped by user")
