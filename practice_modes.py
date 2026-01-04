# Practice Modes

import asyncio
import urandom
import utime
import time
from config import SELECTION_NOTES, CHORD_MIDI_NOTES, OPEN_STRING_NOTES, Colors, NOTE_NAMES
from metronome import Metronome
from chord_detector import ChordDetector


class PracticeMode:
    """Base class for practice modes"""
    
    def __init__(self, display_manager, ble_manager, chord_detector, menu_system, chord_display=None):
        self.display = display_manager
        self.ble = ble_manager
        self.detector = chord_detector
        self.menu = menu_system
        self.chord_display = chord_display
        self.new_chord_list_uploaded = False
        self.last_fret_positions = None  # For live fretboard display optimization
    
    async def run(self):
        """Run the practice mode - override in subclasses"""
        raise NotImplementedError
    
    @staticmethod
    def get_notes_from_pressed_frets(pressed_frets):
        """Map pressed frets to their corresponding MIDI notes.
        
        Args:
            pressed_frets: List of 6 integers representing fret positions for each string
                          (0 = open string/muted, >0 = fret number)
        
        Returns:
            List of 6 MIDI note values corresponding to the pressed frets.
            Notes are calculated as: OPEN_STRING_NOTE + fret_number
            0 is used for muted/unreleased strings.
        
        Example:
            pressed_frets = [0, 2, 2, 1, 0, 0]  # C major chord shape
            notes = get_notes_from_pressed_frets(pressed_frets)
            # Returns: [64, 61, 57, 51, 45, 40] or similar depending on position
        """
        notes = []
        for string_num, fret_num in enumerate(pressed_frets):
            if fret_num == 0:
                # Open string or not pressed
                notes.append(OPEN_STRING_NOTES[string_num])
            else:
                # Calculate MIDI note = open string note + fret number
                midi_note = OPEN_STRING_NOTES[string_num] + fret_num
                notes.append(midi_note)
        return notes
    
    @staticmethod
    def get_note_names_from_pressed_frets(pressed_frets):
        """Map pressed frets to their corresponding note names.
        
        Args:
            pressed_frets: List of 6 integers representing fret positions for each string
        
        Returns:
            List of 6 note name strings (e.g., ['E', 'B', 'G', 'D', 'A', 'E'])
        
        Example:
            pressed_frets = [0, 0, 0, 0, 0, 0]  # Open strings
            names = get_note_names_from_pressed_frets(pressed_frets)
            # Returns: ['E', 'B', 'G', 'D', 'A', 'E']
        """
        midi_notes = PracticeMode.get_notes_from_pressed_frets(pressed_frets)
        note_names = []
        for midi_note in midi_notes:
            # Convert MIDI note to note name
            note_index = midi_note % 12
            note_name = NOTE_NAMES[note_index]
            note_names.append(note_name)
        return note_names


class RegularPracticeMode(PracticeMode):
    """Regular chord practice mode"""

    def __init__(self, display_manager, ble_manager, chord_detector, menu_system, chord_sequence, chord_display=None):
        super().__init__(display_manager, ble_manager, chord_detector, menu_system, chord_display)
        self.chord_sequence = chord_sequence
        self.current_chord_index = 0
        self.target_chord = None  # Current target chord
        self.randomize_mode = None
        self.mode = 'R'  # 'R' for randomize, 'S' for sequence, None for direct
        self.hide_diagram = False  # 'H' for hide diagram until first strike
        self.last_display_update_ms = 0
        self.display_update_interval_ms = 30  # Throttle updates to 30ms (~33 FPS)
        self.collected_strings = [None] * 6
        self.pressed_frets = [0] * 6

    async def run(self):
        """Run regular chord practice"""
        # print("=== PRACTICE MODE STARTING ===")
        if not self.ble.connected or not self.ble.midi_characteristic:
            # print("Not connected")
            return 'menu'
        
        # print("Starting regular chord practice...")
        # print(f"Sequence: {self.chord_sequence}")
        
        self.detector.reset()
        last_note = None
        allStringsDetected = False
        notes_hit = False
        last_string = 0
        up = False
        timeout_task = None
        time_last_chord = 0
        
        # Display the first target chord
        self.target_chord = self.chord_sequence[self.current_chord_index]
        # print(f"=== DISPLAY CHORD: {self.target_chord} ===")
        progress_text = f"{self.current_chord_index + 1}/{len(self.chord_sequence)}"

        if self.hide_diagram:
            # Hide mode: show only chord name, no diagram
            self.display.tft.fill(Colors.BLACK)
            self.display.text(progress_text, 90, 5, Colors.WHITE)
            x_pos = 70 if len(self.target_chord) > 1 else 90
            self.display.draw_large_text(self.target_chord, x_pos, 60, Colors.ORANGE)
            self.display.text("(Ready to play)", 70, 180, Colors.WHITE)
            self.display.tft.show()
        elif self.chord_display:
            self.chord_display.display_target_chord(self.target_chord, progress_text)
        else:
            # Fallback display
            self.display.clear()
            self.display.draw_large_text(self.target_chord, 70, 30, Colors.YELLOW)
            self.display.text(progress_text, 90, 5, Colors.WHITE)
            self.display.show()
        
        async def timeout_handler():
            """Handle timeout - reset strum if no completion"""
            await asyncio.sleep_ms(1000)  # Reset display after 500ms if strum not completed
            nonlocal allStringsDetected, notes_hit, timeout_task
            # print("Strum timeout, resetting...")

            await self._process_chord_detection()
            
            # Reset for next chord
            self.detector.reset()
            allStringsDetected = False
            notes_hit = False
            last_note = None
            self.collected_strings = [None] * 6
            self.pressed_frets = [0] * 6
            started = False
            string_count = 0

        started = False
        string_count = 0

        # # Reset display to show target chord with white strings
            # # time.sleep_ms(500)
            # progress_text = f"{self.current_chord_index + 1}/{len(self.chord_sequence)}"
            # if self.chord_display:
            #     self.chord_display.display_target_chord(target_chord, progress_text)
            
        timeout_task = None
        self.collected_strings = [None] * 6
        started = False
        notes_hit = False
        self.detector.reset()

        try:
            while self.ble.connected:
                # Check for new chord list upload
                if self.new_chord_list_uploaded:
                    self.new_chord_list_uploaded = False
                    return 'menu'
                
                # Get MIDI data from the queue (non-blocking)
                data = await self.ble.wait_for_queued_midi()
                
                if not data:
                    # No messages in queue, sleep briefly to avoid busy-waiting
                    await asyncio.sleep_ms(1)
                    continue
                
                # Process the queued message
                command = data[0]
                string_num = data[1] 
                fret_num = data[2]
                note = data[3]
                fret_pressed = data[4] 

                
                # Handle fret press/release messages
                if command == 0x90 or command == 0xB0:
                    # Fret pressed
                    if fret_pressed > 0:
                        self.pressed_frets[string_num] = fret_num
                    else:
                        self.pressed_frets[string_num] = 0
                    print(f"Fret On: String {string_num} Fret {fret_num}")

                    # if command == 0x90:
                    #     # Note on - add to detector
                    #     self.detector.add_note(note, string_num, fret_num)

                    try:
                        self._show_live_fretboard(self.target_chord, self.detector.get_played_notes(), progress_text, self.pressed_frets)
                    except Exception as e:
                        print(f"Error in _show_live_fretboard: {e}")
                        import sys
                        sys.print_exception(e)
                
                if command == 0x80:
                    # Fret released
                    self.pressed_frets[string_num] = 0
                    print(f"Fret Off: String {string_num} Fret {fret_num}")
                    try:
                        self._show_live_fretboard(self.target_chord, self.detector.get_played_notes(), progress_text, self.pressed_frets)
                    except Exception as e:
                        print(f"Error in _show_live_fretboard: {e}")
                        import sys
                        sys.print_exception(e)
                
                elif command == 0x90:  # Note on String struck
                    # Cancel existing timeout before creating new one
                    if timeout_task is not None:  
                        timeout_task.cancel()

                    self.detector.add_note(note, string_num, fret_num)
                    
                    print(f"Check It Note On: Note {note} String {string_num} Fret {fret_num}")

                    # Check for navigation triggers on 22nd fret
                    if note == 86:  # String 1, 22nd fret - Menu
                        # print(f"Menu trigger detected")
                        return 'menu'

                    if not started:
                        if (string_num == 5 or string_num == 0):
                            started = True
                            # print("Strum started")
                        else:
                            self._show_live_fretboard(self.target_chord, self.detector.get_played_notes(), progress_text, self.pressed_frets)

                    
                    self.collected_strings[string_num] = note
                    print(f"Collected strings: {self.collected_strings}")
                    try:
                        self._show_live_fretboard(self.target_chord, self.detector.get_played_notes(), progress_text, self.pressed_frets)
                    except Exception as e:
                        print(f"Error in _show_live_fretboard: {e}")
                        import sys
                        sys.print_exception(e)

                    timeout_task = asyncio.create_task(timeout_handler())

                    # Check if we've collected all 6 strings
                    if any(x is None for x in self.collected_strings):
                        continue  # Exit the note processing loop

                    print(f"Strings collected so far: {self.collected_strings}")

                    if timeout_task is not None:
                        timeout_task.cancel()

                    started = False
                    string_count = 0        
                    # print("All strings were struck!")
                    # print("Strum detected, processing chord.........................................")
                    # Process completed chord (handles display, reset, and index increment)
                    await self._process_chord_detection()
                    
                    # Update progress text for next chord
                    progress_text = f"{self.current_chord_index + 1}/{len(self.chord_sequence)}"
                    
                    # Reset strum detection state for next chord
                    allStringsDetected = False
                    notes_hit = False
                    last_note = None
                    print("Resetting detector and collected strings for next chord")
                    self.collected_strings = [None] * 6
                
                # Handle note off to clear pressed frets
                # elif msg and msg[0] == 'note_off':
                #     note = msg[1]
                    
                #     # Calculate string and fret from MIDI note
                #     from config import OPEN_STRING_NOTES
                #     string_num = None
                    
                #     # Try to find which string this note belongs to
                #     for string_idx, open_note in enumerate(OPEN_STRING_NOTES):
                #         if note >= open_note:
                #             potential_fret = note - open_note
                #             if 0 <= potential_fret <= 24:  # Valid fret range
                #                 string_num = string_idx
                #                 break
                    
                #     print(f"Note Off: Note {note} String {string_num}")
                    
                #     # Clear the pressed fret for this string
                #     if string_num is not None:
                #         self.pressed_frets[string_num] = 0
                #         print(f"Cleared pressed_frets[{string_num}]")
                #         try:
                #             self._show_live_fretboard(self.target_chord, self.detector.get_played_notes(), progress_text, self.pressed_frets)
                #         except Exception as e:
                #             print(f"Error in _show_live_fretboard: {e}")
                #             import sys
                #             sys.print_exception(e)
                
                await asyncio.sleep_ms(1)
        
        except Exception as e:
            # print(f"Error in practice mode: {e}")
            import sys
            sys.print_exception(e)
        
        return 'menu'


    def _display_chord(self, played_note):
        # print(f"Displaying chord for played note: {played_note}")
        """Display the fretboard with a single string highlighted in green
        
        Args:
            played_note: The MIDI note that was played
        """
        if not self.chord_display:
            return
        
        from config import OPEN_STRING_NOTES
        
        target_chord = self.chord_sequence[self.current_chord_index]
        progress_text = f"{self.current_chord_index + 1}/{len(self.chord_sequence)}"
        
        # Determine which string the note is on
        string_colors = [Colors.WHITE] * 6  # Default all strings to white
        
        for string_num in range(1, 7):
            open_note = OPEN_STRING_NOTES[string_num - 1]
            # Check if this note is within 0-24 frets on this string
            for fret in range(25):
                if open_note + fret == played_note:
                    string_colors[string_num - 1] = Colors.GREEN  # Highlight struck string
                    break
        
        # Draw the fretboard
        self.display.tft.fill(Colors.BLACK)
        self.display.text(progress_text, 90, 5, Colors.WHITE)
        
        x_pos = 70 if len(target_chord) > 1 else 90
        self.display.draw_large_text(target_chord, x_pos, 30, Colors.ORANGE)
        
        self.chord_display._draw_chord_fretboard(target_chord, Colors.ORANGE, string_colors)
        self.chord_display._draw_played_notes_overlay({played_note}, None)
        
        self.display.tft.show()





    def _show_live_fretboard(self, target_chord, played_notes, progress_text, pressed_frets):
        """Display the fretboard in real-time with fret positions shown
        
        Shows the actual fret positions being played on each string.
        Frets are colored green if correct for the chord, red if wrong.
        Displays white dots at the frets indicated by pressed_frets (0 = open string, erased).
        
        Args:
            target_chord: The target chord name
            played_notes: Notes detected by the chord detector
            progress_text: Progress text to display
            pressed_frets: List of 6 fret positions (0 = open/erase, >0 = fret number)
        """
        # print(f"Showing live fretboard for chord: {target_chord}, played_notes={played_notes}")
        if not self.chord_display:
            return
        #print("Updating the display with live fretboard")
        
        # Get fret positions for all strings
        fret_positions = self.detector.get_fret_positions()
        #print(f"Fret positions: {fret_positions}")
        
        # Determine which strings have been struck using detector's string mapping
        # detector.played_notes[i] has the note for string (i+1), or None if not struck
        string_colors = []
        for string_num in range(1, 7):
            # Detector reverses indexing: string 6 at index 0, string 1 at index 5
            detector_index = 6 - string_num
            # Check if this string has a note in the detector
            if self.detector.played_notes[detector_index] is not None:
                # print(f"String {string_num} was hit")
                string_colors.append(Colors.GREEN)  # String was hit
            else:
                # print(f"String {string_num} was NOT hit")
                string_colors.append(Colors.WHITE)  # String not yet hit
        
        # Only redraw the full fretboard when needed - use optimized drawing
        self.display.tft.fill(Colors.BLACK)
        
        # Show progress
        self.display.text(progress_text, 90, 5, Colors.WHITE)
        
        # Show chord name
        x_pos = 70 if len(target_chord) > 1 else 90
        self.display.draw_large_text(target_chord, x_pos, 30, Colors.ORANGE)
        
        # Draw the fretboard with color-coded strings
        self.chord_display._draw_chord_fretboard(target_chord, Colors.ORANGE, string_colors)
        
        # Overlay the actual fret positions being played
        if any(f is not None for f in fret_positions):
            self.chord_display._draw_fret_positions(fret_positions, target_chord)
        
        # Draw white dots at the pressed frets (non-zero values in pressed_frets)
        if any(f > 0 for f in pressed_frets):
            self.chord_display._draw_fret_positions(pressed_frets, target_chord)
        
        self.display.tft.show()
    
    async def _process_chord_detection(self):
        """Process chord detection result"""
        # print("-----------------------------------------------------------------------------")
        
        # Get played notes BEFORE resetting
        
        is_correct, matching, missing, extra = self.detector.detect_chord(self.collected_strings, self.target_chord)
        
        # print(f">>> Target: {self.target_chord}, Played: {self.collected_strings}, Correct: {is_correct}")
        # if not is_correct:
        #     pass
        #     # print(f"    Missing: {missing}, Extra: {extra}")
        
        progress_text = f"{self.current_chord_index + 1}/{len(self.chord_sequence)}"
        
        if is_correct:
            # print(f">>> SUCCESS! {self.target_chord} Correct!")
            if self.chord_display:
                self.chord_display.display_correct_chord(self.target_chord, progress_text)
            else:
                self.display.show_success(f"{self.target_chord} Correct!")
            await asyncio.sleep(0.125)  # Wait 1/8 second before clearing
            self.display.tft.fill(Colors.BLACK)  # Clear screen
            self.display.tft.show()
            
            self.current_chord_index += 1
            
            if self.current_chord_index >= len(self.chord_sequence):
                if self.mode == 'R':
                    # print(">>> Sequence complete! Randomizing...")
                    shuffled = list(self.chord_sequence)
                    n = len(shuffled)
                    for i in range(n - 1, 0, -1):
                        j = urandom.getrandbits(16) % (i + 1)
                        shuffled[i], shuffled[j] = shuffled[j], shuffled[i]
                    self.chord_sequence = shuffled
                    self.current_chord_index = 0
                else:
                    # print(">>> All chords completed!")
                    return 'menu'
        else:
            # print(f"Wrong! Expected {self.target_chord}")
            if self.chord_display:
                self.chord_display.display_wrong_chord("???", self.detector.played_notes, self.target_chord, None, progress_text)
                await asyncio.sleep(1.0)  # Show wrong result for 1 second before moving on
        
        # Reset detector BEFORE displaying next chord
        self.detector.reset()
        
        # Display next chord with fresh detector state
        self.target_chord = self.chord_sequence[self.current_chord_index]
        progress_text = f"{self.current_chord_index + 1}/{len(self.chord_sequence)}"
        if self.hide_diagram:
            # Hide mode: show only chord name, no diagram
            self.display.tft.fill(Colors.BLACK)
            self.display.text(progress_text, 90, 5, Colors.WHITE)
            x_pos = 70 if len(self.target_chord) > 1 else 90
            self.display.draw_large_text(self.target_chord, x_pos, 60, Colors.ORANGE)
            self.display.text("(Ready to play)", 70, 180, Colors.WHITE)
            self.display.tft.show()
        elif self.chord_display:
            self.chord_display.display_target_chord(self.target_chord, progress_text)
        else:
            self.display.clear()
            self.display.draw_large_text(self.target_chord, 70, 30, Colors.YELLOW)
            self.display.text(progress_text, 90, 5, Colors.WHITE)
            self.display.show()
    
    def _parse_midi(self, data):
        """Parse MIDI message
        
        Expects individual MIDI messages (2-3 bytes) without BLE header/timestamp:
        - Note On: [0x90-0x9F, note, velocity]
        - Note Off: [0x80-0x8F, note]
        - Program Change: [0xB0-0xBF, controller, value] (fret press/release info)
        """
        print(data)
        if not data or len(data) < 2:
            return None
        
        midi_status = data[0]
        
        # Note On: 0x90-0x9F
        if 0x90 <= midi_status <= 0x9F:
            if len(data) >= 3:
                note = data[1]
                velocity = data[2]
                string_num = midi_status & 0x0F
                if velocity > 0:
                    print(f"Parsed MIDI Note On: Note {note} Velocity {velocity} String {string_num}")
                    return ('note_on', note, velocity, string_num, self.last_fret_positions)
                else:
                    return ('note_off', note)
        
        # Note Off: 0x80-0x8F
        elif 0x80 <= midi_status <= 0x8F:
            if len(data) >= 2:
                note = data[1]
                string_num = midi_status & 0x0F
                print(f"Parsed MIDI Note Off: Note {note} String {string_num}")
                return ('note_off', note)
        
        # Control Change / Program Change for fret info: 0xB0-0xBF
        elif 0xB0 <= midi_status <= 0xBF:
            if len(data) >= 3:
                string_num = midi_status & 0x0F
                controller = data[1]
                value = data[2]
                self.last_fret_positions = value
                print(f"Parsed MIDI Control: String {string_num} Controller {controller} Value {value}")
                # Return 'fret_on' when pressed (value > 0), 'fret_off' when released (value=0)
                if value > 0:
                    return ('fret_on', string_num, value, True)
                else:
                    return ('fret_off', string_num, value, False)
        
        return None

class MetronomePracticeMode(PracticeMode):
    """Metronome practice mode"""
    
    def __init__(self, display_manager, ble_manager, chord_detector, menu_system, bpm, chord_display=None, pattern=None):
        super().__init__(display_manager, ble_manager, chord_detector, menu_system, chord_display)
        self.bpm = bpm
        self.pattern = pattern or self._default_pattern()
        self.metronome = Metronome(bpm)
    
    def _default_pattern(self):
        """Default metronome pattern"""
        return [
            ['Em', 'D'],
            ['Em', 'D'],
            ['Em', 'U'],
            ['Em', 'U'],
            ['Em', 'D'],
            ['Em', 'U'],
            ['D6/9', 'D'],
            ['D6/9', 'D'],
            ['D6/9', 'U'],
            ['D6/9', 'U'],
            ['D6/9', 'D'],
            ['D6/9', 'U'],
        ]
    
    async def run(self):
        """Run metronome practice"""
        # print("Starting metronome practice...")
        await self.metronome.start()
        
        pattern_index = 0
        last_strum_time = 0
        strum_cooldown_ms = 100
        last_string_num = 0
        
        # TODO: Implement full metronome practice logic
        
        await self.metronome.stop()
        return 'menu'
