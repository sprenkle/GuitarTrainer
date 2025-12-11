# Chord Display Module

from config import OPEN_STRING_NOTES, Colors, CHORD_MIDI_NOTES

class ChordDisplay:
    """Handles chord visualization on the display"""
    
    def __init__(self, display_manager):
        self.display = display_manager
    
    def display_target_chord(self, chord_name):
        """Display the target chord to play with fretboard diagram"""
        self.display.clear()
        
        # Show large chord name
        self.display.draw_large_text(chord_name, 70, 10, Colors.YELLOW)
        
        # Draw the fretboard diagram
        self._draw_chord_fretboard(chord_name, Colors.ORANGE)
        
        # Instructions at bottom
        self.display.text("22nd fret = menu", 50, 210, Colors.ORANGE)
        self.display.show()
    
    def display_correct_chord(self, chord_name):
        """Display when correct chord is played"""
        self.display.clear()
        self.display.draw_large_text(chord_name, 70, 50, Colors.GREEN)
        self.display.text("Correct!", 85, 110, Colors.GREEN)
        self.display.show()
    
    def display_wrong_chord(self, played_chord, target_chord):
        """Display when wrong chord is played"""
        self.display.clear()
        self.display.text("Wrong!", 90, 50, Colors.RED)
        self.display.draw_large_text(target_chord, 70, 80, Colors.YELLOW)
        self.display.text("Try again", 80, 130, Colors.WHITE)
        self.display.show()
    
    def _draw_chord_fretboard(self, chord_name, highlight_color, string_colors=None):
        """Draw a fretboard diagram showing finger positions for a chord
        
        Args:
            chord_name: Name of the chord (e.g., 'C', 'G', 'Am')
            highlight_color: Color to highlight the positions
            string_colors: Optional list of 6 colors for each string (for hit/miss indication)
        """
        # Get chord shape from CHORD_MIDI_NOTES
        chord_notes = CHORD_MIDI_NOTES.get(chord_name, [])
        if not chord_notes:
            return
        
        # Generate chord shape (fret positions for each string)
        chord_shape = self._get_chord_shape(chord_name, chord_notes)
        
        # Fretboard area
        start_x = 30
        start_y = 50
        string_spacing = 16
        fret_width = 40
        
        # Draw 6 strings (horizontal lines)
        for i in range(6):
            y = start_y + (i * string_spacing)
            string_index = i
            string_color = string_colors[string_index] if string_colors else Colors.WHITE
            self.display.line(start_x, y, start_x + 160, y, string_color)
        
        # Draw 4 frets (vertical lines)
        for i in range(1, 5):
            x = start_x + (i * fret_width)
            self.display.line(x, start_y, x, start_y + (string_spacing * 5), Colors.WHITE)
        
        # Draw fret numbers (1-4)
        for i in range(1, 5):
            x = start_x + (i * fret_width) - (fret_width // 2) - 4
            y = start_y + string_spacing * 5 + 8
            self.display.text(str(i), x, y, Colors.WHITE)
        
        # Draw finger positions for each string
        for string_num, fret_num in chord_shape:
            string_y = start_y + ((string_num - 1) * string_spacing)
            
            if fret_num < 0:
                # Muted string - draw X
                self.display.text("X", start_x - 18, string_y - 4, Colors.RED)
            elif fret_num == 0:
                # Open string - draw O
                self.display.text("O", start_x - 18, string_y - 4, highlight_color)
            else:
                # Fretted note - draw filled square on fretboard
                fret_x = start_x + (fret_num * fret_width) - (fret_width // 2)
                self.display.fill_rect(fret_x - 5, string_y - 5, 11, 11, highlight_color)
                self.display.fill_rect(fret_x - 3, string_y - 3, 7, 7, highlight_color)
    
    def _get_chord_shape(self, chord_name, chord_notes):
        """Generate chord fingering from MIDI notes
        
        Returns list of (string_num, fret_num) tuples
        """
        shape = []
        
        # For each string (1 to 6), find the best fret position
        for string_num in range(1, 7):
            open_note = OPEN_STRING_NOTES[string_num - 1]
            found_fret = None
            
            # Try each note in the chord and find the lowest fret position
            for note in chord_notes:
                fret = note - open_note
                if 0 <= fret <= 4:  # Only first 4 frets
                    if found_fret is None or fret < found_fret:
                        found_fret = fret
            
            if found_fret is not None:
                shape.append((string_num, found_fret))
            else:
                # Mute this string
                shape.append((string_num, -1))
        
        return shape
        """Display when wrong chord is played"""
        self.display.clear()
        self.display.text("Wrong!", 90, 80, Colors.RED)
        self.display.text(f"Target: {target_chord}", 60, 110, Colors.YELLOW)
        if played_chord:
            self.display.text(f"Played: {played_chord}", 60, 130, Colors.ORANGE)
        self.display.show()
    
    def update_live_display(self, target_chord, played_notes, progress):
        """Update display with live chord detection progress"""
        self.display.clear()
        
        # Title
        self.display.text("Playing:", 80, 10, Colors.WHITE)
        
        # Target chord
        self.display.draw_large_text(target_chord, 70, 50, Colors.YELLOW)
        
        # Progress bar
        bar_width = int(progress * 100)
        self.display.fill_rect(40, 150, bar_width, 20, Colors.GREEN)
        self.display.rect(40, 150, 100, 20, Colors.WHITE)
        
        # Played notes info
        played_count = len(played_notes)
        self.display.text(f"Notes: {played_count}/6", 70, 180, Colors.WHITE)
        
        self.display.text("22nd fret = menu", 50, 200, Colors.ORANGE)
        self.display.show()
    
    def draw_fretboard(self, target_chord):
        """Draw fretboard visualization"""
        self.display.clear()
        
        # Title
        self.display.text(target_chord, 100, 10, Colors.YELLOW)
        
        # Simple fretboard visualization
        # 6 strings, 4 frets
        start_x = 50
        start_y = 50
        string_spacing = 20
        fret_spacing = 30
        
        # Draw strings
        for string_idx in range(6):
            y = start_y + (string_idx * string_spacing)
            self.display.line(start_x, y, start_x + (4 * fret_spacing), y, Colors.WHITE)
        
        # Draw frets
        for fret_idx in range(5):
            x = start_x + (fret_idx * fret_spacing)
            self.display.line(x, start_y, x, start_y + (5 * string_spacing), Colors.WHITE)
        
        # Mark notes for this chord
        expected_notes = CHORD_MIDI_NOTES.get(target_chord, [])
        for string_idx, note in enumerate(expected_notes):
            if note is not None:
                open_note = OPEN_STRING_NOTES[string_idx]
                fret = note - open_note
                if 0 <= fret <= 4:
                    x = start_x + (fret * fret_spacing) + fret_spacing // 2
                    y = start_y + (string_idx * string_spacing)
                    self.display.fill_rect(x - 5, y - 5, 10, 10, Colors.GREEN)
        
        self.display.text("Press 22nd fret to play", 30, 190, Colors.ORANGE)
        self.display.show()
    
    def draw_metronome_display(self, metronome_pattern, pattern_index, bpm, metronome_state):
        """Draw the metronome display with beat indicator"""
        self.display.clear()
        
        # Show BPM at top
        self.display.text(f"{bpm} BPM", 90, 10, Colors.YELLOW)
        
        # Two-square display
        square_size = 70
        spacing = 30
        start_x = 35
        y_pos = 90
        
        # LEFT SQUARE - Next beat
        next_index = (pattern_index + 1) % len(metronome_pattern)
        next_chord_name = metronome_pattern[next_index][0]
        next_strum = metronome_pattern[next_index][1]
        
        left_x = start_x
        
        # Draw chord name above left square
        chord_x_offset = -10 if len(next_chord_name) > 2 else 0
        self.display.draw_large_text(next_chord_name, left_x + 10 + chord_x_offset, y_pos - 55, Colors.YELLOW)
        
        # Draw outlined square for next beat
        if next_strum == 'D':
            left_square_color = Colors.GREEN
        elif next_strum == 'U':
            left_square_color = Colors.BLUE
        else:
            left_square_color = Colors.ORANGE
        
        self.display.rect(left_x, y_pos, square_size, square_size, left_square_color)
        self.display.rect(left_x + 1, y_pos + 1, square_size - 2, square_size - 2, left_square_color)
        
        # RIGHT SQUARE - Current beat
        current_index = pattern_index
        current_chord_name = metronome_pattern[current_index][0]
        current_strum = metronome_pattern[current_index][1]
        
        right_x = left_x + square_size + spacing
        
        # Draw chord name above right square
        chord_x_offset = -10 if len(current_chord_name) > 2 else 0
        self.display.draw_large_text(current_chord_name, right_x + 10 + chord_x_offset, y_pos - 55, Colors.GREEN)
        
        # Get base color for current beat
        if current_strum == 'D':
            base_color = Colors.GREEN
        elif current_strum == 'U':
            base_color = Colors.BLUE
        else:
            base_color = Colors.ORANGE
        
        # Draw filled square for current beat
        self.display.fill_rect(right_x, y_pos, square_size, square_size, base_color)
        
        # Draw smaller inner square that blinks with metronome
        inner_size = 30
        inner_offset = (square_size - inner_size) // 2
        inner_x = right_x + inner_offset
        inner_y = y_pos + inner_offset
        
        # Inner square color: white or black based on metronome beat
        inner_color = Colors.WHITE if metronome_state['beat_white'] else Colors.BLACK
        self.display.fill_rect(inner_x, inner_y, inner_size, inner_size, inner_color)
        
        # Instructions at bottom
        self.display.text("Strum to advance", 50, 200, Colors.ORANGE)
        
        self.display.show()
