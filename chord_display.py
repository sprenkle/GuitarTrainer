# Chord Display Module

from config import OPEN_STRING_NOTES, Colors, CHORD_MIDI_NOTES

class ChordDisplay:
    """Handles chord visualization on the display"""
    
    def __init__(self, display_manager):
        self.display = display_manager
        self.tft = display_manager.tft
        self.current_chord_index = 0
        self.chord_sequence = []
        self.sequence_mode = True
    
    def display_target_chord(self, chord_name, progress_text=None):
        """Display the current target chord to play with fretboard diagram"""
        # Clear screen
        self.tft.fill(Colors.BLACK)
        
        # Show progress if provided
        if progress_text:
            self.display.text(progress_text, 90, 5, Colors.WHITE)
        
        # Draw LARGE chord name
        x_pos = 70 if len(chord_name) > 1 else 90
        self.display.draw_large_text(chord_name, x_pos, 30, Colors.ORANGE)
        
        # Draw chord diagram with all white strings (neutral state)
        white_strings = [Colors.WHITE] * 6
        self._draw_chord_fretboard(chord_name, Colors.ORANGE, white_strings)
        
        self.tft.show()
    
    def display_correct_chord(self, chord_name, progress_text=None):
        """Display success feedback"""
        self.tft.fill(Colors.BLACK)
        
        # Show progress if provided
        if progress_text:
            self.display.text(progress_text, 90, 5, Colors.WHITE)
        
        # Large success message
        x_pos = 70 if len(chord_name) > 1 else 90
        self.display.draw_large_text(chord_name, x_pos, 40, Colors.GREEN)
        
        # Show "Correct!" label
        self.display.text("Correct!", 85, 110, Colors.GREEN)
        
        # Draw chord diagram in green
        self._draw_chord_fretboard(chord_name, Colors.GREEN)
        
        self.tft.show()
    
    def display_wrong_chord(self, played_chord, played_notes, target_chord, strum_direction=None, progress_text=None):
        """Display when wrong chord is played - show target in orange, played with color based on direction
        
        Args:
            played_chord: The chord name that was played (or "???" if unknown)
            played_notes: Set of MIDI notes that were played
            target_chord: The chord name that should have been played
            strum_direction: 'D' for down (white), 'U' for up (blue), None for red
            progress_text: Optional progress text to display
        """
        print(f"display_wrong_chord called: played={played_chord}, notes={played_notes}, target={target_chord}, direction={strum_direction}")
        
        # Clear the screen
        self.tft.fill(Colors.BLACK)
        
        # Show progress if provided
        if progress_text:
            self.display.text(progress_text, 90, 5, Colors.WHITE)
        
        # Show target chord name
        x_pos = 70 if len(target_chord) > 1 else 90
        self.display.draw_large_text(target_chord, x_pos, 30, Colors.ORANGE)
        
        # Get expected non-open notes for target chord
        expected_notes = set(CHORD_MIDI_NOTES.get(target_chord, []))
        non_open_expected = set()
        for note in expected_notes:
            is_open = note in OPEN_STRING_NOTES
            if not is_open:
                non_open_expected.add(note)
        
        # Determine string colors based on whether each string was struck
        string_colors = []
        
        # For each string (1-6), check if ANY note from that string was played
        for string_num in range(1, 7):
            open_note = OPEN_STRING_NOTES[string_num - 1]
            string_was_struck = False
            
            # Check if any note within frets 0-24 on this string was played
            for fret in range(25):
                note = open_note + fret
                if note in played_notes:
                    string_was_struck = True
                    break
            
            if string_was_struck:
                string_colors.append(Colors.GREEN)  # String was struck
            else:
                string_colors.append(Colors.RED)    # String was NOT struck
        
        # Create note color mapping - white if correct, red if wrong
        note_colors = {}
        for note in played_notes:
            if note in non_open_expected:
                note_colors[note] = Colors.WHITE  # Correct note for chord
            else:
                note_colors[note] = Colors.RED    # Wrong note for chord
        
        # Draw target chord with color-coded strings
        self._draw_chord_fretboard(target_chord, Colors.ORANGE, string_colors)
        
        # Overlay played notes with correct coloring (white for correct, red for wrong)
        print(f"Drawing played notes overlay with {len(played_notes)} notes, note_colors: {note_colors}")
        self._draw_played_notes_overlay(played_notes, strum_direction, note_colors)
        
        # Draw X on strings where notes were missed
        self._draw_missed_notes(target_chord, played_notes)
        
        self.tft.show()
    
    def display_playing_chord(self, chord_name, played_notes, strum_direction=None, progress_text=None):
        """Display target chord with real-time played notes overlay during strum"""
        self.tft.fill(Colors.BLACK)
        
        # Show progress if provided
        if progress_text:
            self.display.text(progress_text, 90, 5, Colors.WHITE)
        
        # Draw LARGE chord name
        x_pos = 70 if len(chord_name) > 1 else 90
        self.display.draw_large_text(chord_name, x_pos, 30, Colors.ORANGE)
        
        # Draw chord diagram
        self._draw_chord_fretboard(chord_name, Colors.ORANGE)
        
        # Overlay played notes with strum direction color
        self._draw_played_notes_overlay(played_notes, strum_direction)
        
        self.tft.show()
    
    def _draw_chord_fretboard(self, chord_name, highlight_color, string_colors=None):
        """Draw a fretboard diagram showing all finger positions for a chord
        
        Args:
            chord_name: Name of the chord (e.g., 'C', 'G', 'Am')
            highlight_color: Color to highlight the positions
            string_colors: Optional list of 6 colors for each string (for hit/miss indication)
        """
        chord_shape = self._get_chord_shape(chord_name)
        if not chord_shape:
            return
        
        # Fretboard area
        start_x = 30
        start_y = 100
        string_spacing = 16
        fret_width = 40
        
        # Draw 6 strings (horizontal lines) - thicker, with optional color coding
        for i in range(6):
            y = start_y + (i * string_spacing)
            string_index = i
            string_color = string_colors[string_index] if string_colors else Colors.WHITE
            # Draw thicker lines
            self.tft.hline(start_x, y, 160, string_color)
            self.tft.hline(start_x, y+1, 160, string_color)
        
        # Draw nut line at the start (thicker)
        self.tft.vline(start_x, start_y, string_spacing * 5, Colors.WHITE)
        self.tft.vline(start_x+1, start_y, string_spacing * 5, Colors.WHITE)
        
        # Draw 4 frets (vertical lines) - thicker
        for i in range(1, 5):
            x = start_x + (i * fret_width)
            # Draw thicker lines
            self.tft.vline(x, start_y, string_spacing * 5, Colors.WHITE)
            self.tft.vline(x+1, start_y, string_spacing * 5, Colors.WHITE)
        
        # Draw fret numbers (1-4)
        for i in range(1, 5):
            x = start_x + (i * fret_width) - (fret_width // 2) - 4
            y = start_y + string_spacing * 5 + 8
            self.tft.text(str(i), x, y, Colors.WHITE)
        
        # Draw finger positions for each string
        for string_num, fret_num in chord_shape:
            string_y = start_y + ((string_num - 1) * string_spacing)
            
            if fret_num < 0:
                # Muted string - draw X
                self.tft.text("X", start_x - 18, string_y - 4, Colors.RED)
            elif fret_num == 0:
                # Open string - draw O
                self.tft.text("O", start_x - 18, string_y - 4, highlight_color)
            else:
                # Fretted note - draw filled square on fretboard
                fret_x = start_x + (fret_num * fret_width) - (fret_width // 2)
                self.tft.fill_rect(fret_x - 5, string_y - 5, 11, 11, highlight_color)
                self.tft.fill_rect(fret_x - 3, string_y - 3, 7, 7, highlight_color)
    
    def _draw_fret_positions(self, fret_positions, target_chord=None):
        """Draw the actual fret positions being played by the user
        
        Args:
            fret_positions: List of 6 fret values (0=open, None=not played)
            target_chord: Optional chord name to validate against
        """
        print(f"draw_fret_positions called with: {fret_positions}")
        
        if not fret_positions or all(f is None for f in fret_positions):
            print("No fret positions to draw")
            return
        
        start_x = 30
        start_y = 100
        string_spacing = 16
        fret_width = 40
        
        # Get expected chord if provided
        expected_chord_frets = None
        if target_chord:
            expected_notes = CHORD_MIDI_NOTES.get(target_chord, [])
            expected_chord_frets = []
            for string_num in range(1, 7):
                open_note = OPEN_STRING_NOTES[string_num - 1]
                expected_note = expected_notes[string_num - 1] if string_num - 1 < len(expected_notes) else None
                if expected_note is not None:
                    fret = expected_note - open_note
                    expected_chord_frets.append(fret if fret >= 0 else None)
                else:
                    expected_chord_frets.append(None)
        
        # Draw each played fret position
        for string_num in range(1, 7):
            fret_num = fret_positions[string_num - 1]
            
            if fret_num is None:
                continue  # String not played
            
            string_y = start_y + ((string_num - 1) * string_spacing)
            
            # Determine color: green if matches expected, red if wrong
            if expected_chord_frets and expected_chord_frets[string_num - 1] is not None:
                if fret_num == expected_chord_frets[string_num - 1]:
                    marker_color = Colors.GREEN  # Correct fret
                else:
                    marker_color = Colors.RED    # Wrong fret
            else:
                marker_color = Colors.YELLOW    # No expected chord to compare
            
            if fret_num == 0:
                # Open string - draw O
                self.tft.text("O", start_x - 18, string_y - 4, marker_color)
            else:
                # Fretted note - draw filled square on fretboard
                if fret_num <= 4:
                    fret_x = start_x + (fret_num * fret_width) - (fret_width // 2)
                else:
                    # For frets beyond 4, show at fret 4 position
                    fret_x = start_x + (4 * fret_width) - (fret_width // 2)
                
                self.tft.fill_rect(fret_x - 5, string_y - 5, 11, 11, marker_color)
    
    def _draw_played_notes_overlay(self, played_notes, strum_direction=None, note_colors=None):
        """Draw colored dots over the fretboard showing where user played
        
        Args:
            played_notes: Set of MIDI notes that were played
            strum_direction: 'D' for down (white), 'U' for up (blue), None for red
            note_colors: Optional dict mapping note -> color. If provided, overrides strum_direction
        """
        print(f"draw_played_notes_overlay called with notes: {played_notes}, direction: {strum_direction}, note_colors: {note_colors}")
        
        if not played_notes:
            print("No notes to draw")
            return
        
        start_x = 30
        start_y = 100
        string_spacing = 16
        fret_width = 40
        
        # Determine color based on strum direction (used if note_colors not provided)
        if strum_direction == 'D':
            default_note_color = Colors.WHITE  # Down strum = white
        elif strum_direction == 'U':
            default_note_color = Colors.BLUE   # Up strum = blue
        else:
            default_note_color = Colors.RED    # No direction = red (error)
        
        # For each played note, find the best string to show it on (lowest fret position)
        for note in played_notes:
            # Get color for this note from note_colors dict if available
            if note_colors and note in note_colors:
                note_color = note_colors[note]
            else:
                note_color = default_note_color
            
            best_string = None
            best_fret = None
            
            # Check all strings to find where this note appears
            for string_num in range(1, 7):
                open_note = OPEN_STRING_NOTES[string_num - 1]
                if note >= open_note:
                    fret_num = note - open_note
                    if 0 <= fret_num <= 24:  # Show all frets up to 24
                        if best_fret is None or fret_num < best_fret:
                            best_string = string_num
                            best_fret = fret_num
            
            # Draw the marker on the best string
            if best_string is not None and best_fret is not None:
                string_y = start_y + ((best_string - 1) * string_spacing)
                
                if best_fret == 0:
                    # Open string - draw O
                    self.tft.text("O", start_x - 18, string_y - 4, note_color)
                else:
                    # Fretted note - draw marker at appropriate position
                    # Frets 1-4 are shown on display, frets 5+ are indicated differently
                    if best_fret <= 4:
                        fret_x = start_x + (best_fret * fret_width) - (fret_width // 2)
                    else:
                        # For frets beyond 4, show marker at fret 4 position to indicate higher fret
                        fret_x = start_x + (4 * fret_width) - (fret_width // 2)
                    self.tft.fill_rect(fret_x - 3, string_y - 3, 6, 6, note_color)
    
    def _draw_missed_notes(self, target_chord, played_notes):
        """Draw X on strings where notes were missed (expected but not played)"""
        # Get expected non-open notes for target chord
        expected_notes = set(CHORD_MIDI_NOTES.get(target_chord, []))
        non_open_expected = set()
        for note in expected_notes:
            is_open = note in OPEN_STRING_NOTES
            if not is_open:
                non_open_expected.add(note)
        
        # Find missed notes
        missed_notes = non_open_expected - played_notes
        
        if not missed_notes:
            print("No missed notes")
            return
        
        start_x = 30
        start_y = 100
        string_spacing = 16
        fret_width = 40
        
        # For each missed note, find its string and draw an X
        for note in missed_notes:
            # Find which string this note should be on
            best_string = None
            best_fret = None
            
            for string_num in range(1, 7):
                open_note = OPEN_STRING_NOTES[string_num - 1]
                if note >= open_note:
                    fret_num = note - open_note
                    if 0 <= fret_num <= 24:
                        if best_fret is None or fret_num < best_fret:
                            best_string = string_num
                            best_fret = fret_num
            
            # Draw X on this string at the expected fret position
            if best_string is not None and best_fret is not None:
                string_y = start_y + ((best_string - 1) * string_spacing)
                
                if best_fret <= 4:
                    fret_x = start_x + (best_fret * fret_width) - (fret_width // 2)
                else:
                    fret_x = start_x + (4 * fret_width) - (fret_width // 2)
                
                # Draw X in red
                self.tft.text("X", fret_x - 4, string_y - 4, Colors.RED)
                print(f"Drew missed X on string {best_string} fret {best_fret}")
    
    def _get_chord_shape(self, chord_name):
        """Generate chord fingering from MIDI notes
        
        Returns list of (string_num, fret_num) tuples
        """
        chord_notes = CHORD_MIDI_NOTES.get(chord_name, [])
        shape = []
        
        # For each string (1 to 6), find the best fret position
        for string_num in range(1, 7):
            open_note = OPEN_STRING_NOTES[string_num - 1]
            found_fret = None
            
            # Try each note in the chord and find the lowest fret position
            for note in chord_notes:
                fret = note - open_note
                if 0 <= fret <= 4:
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
