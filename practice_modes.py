# Practice Modes

import asyncio
import urandom
import utime
import time
from config import SELECTION_NOTES, CHORD_MIDI_NOTES, OPEN_STRING_NOTES, Colors
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
    
    async def run(self):
        """Run the practice mode - override in subclasses"""
        raise NotImplementedError


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

    async def run(self):
        """Run regular chord practice"""
        print("=== PRACTICE MODE STARTING ===")
        if not self.ble.connected or not self.ble.midi_characteristic:
            print("Not connected")
            return 'menu'
        
        print("Starting regular chord practice...")
        print(f"Sequence: {self.chord_sequence}")
        
        self.detector.reset()
        last_note = None
        started = False
        notes_hit = False
        last_string = 0
        up = False
        timeout_task = None
        time_last_chord = 0
        
        # Display the first target chord
        self.target_chord = self.chord_sequence[self.current_chord_index]
        print(f"=== DISPLAY CHORD: {self.target_chord} ===")
        
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
            nonlocal started, notes_hit, timeout_task
            print("Strum timeout, resetting...")

            await self._process_chord_detection()
            
            # Reset for next chord
            self.detector.reset()
            started = False
            notes_hit = False
            last_note = None
            self.collected_strings = [None] * 6



            # # Reset display to show target chord with white strings
            # # time.sleep_ms(500)
            # progress_text = f"{self.current_chord_index + 1}/{len(self.chord_sequence)}"
            # if self.chord_display:
            #     self.chord_display.display_target_chord(target_chord, progress_text)
            
            
            
            # await asyncio.sleep_ms(500)
            # self.detector.reset()
            # timeout_task = None
            # self.collected_strings = [None] * 6
            # started = False
            # notes_hit = False
            # self.detector.reset()

        try:
            while self.ble.connected:
                # print("Waiting for MIDI...")
                # Check for new chord list upload
                if self.new_chord_list_uploaded:
                    self.new_chord_list_uploaded = False
                    return 'menu'
                
                # Wait for MIDI data
                try:
                    data = await self.ble.wait_for_midi()
                    # if data:
                    #     print(f"Got MIDI: {data}")
                except asyncio.TimeoutError:
                    pass
                
                if not data:
                    continue
                
                # print(f"Parsing MIDI: {data}")
                msg = self._parse_midi(data)
                # print(f"Parsed: {msg}")
                
                if msg and msg[0] == 'note_on':
                    note = msg[1]
                    print(f"Note On: {note}")
                    
                    # Check for navigation triggers on 22nd fret
                    if note == 86:  # String 1, 22nd fret - Menu
                        print(f"Menu trigger detected")
                        return 'menu'
                    elif note == 81:  # String 2, 22nd fret - Skip chord
                        print(f"Skip chord detected")
                        self.current_chord_index += 1
                        if self.current_chord_index >= len(self.chord_sequence):
                            if self.mode == 'R':
                                print(">>> Sequence complete! Randomizing...")
                                shuffled = list(self.chord_sequence)
                                n = len(shuffled)
                                for i in range(n - 1, 0, -1):
                                    j = urandom.getrandbits(16) % (i + 1)
                                    shuffled[i], shuffled[j] = shuffled[j], shuffled[i]
                                self.chord_sequence = shuffled
                                self.current_chord_index = 0
                            else:
                                print(">>> All chords completed!")
                                return 'menu'
                        self.target_chord = self.chord_sequence[self.current_chord_index]
                        self.detector.reset()
                        progress_text = f"{self.current_chord_index + 1}/{len(self.chord_sequence)}"
                        if self.chord_display:
                            self.chord_display.display_target_chord(self.target_chord, progress_text)
                        continue
                    elif note == 77:  # String 3, 22nd fret - Previous chord
                        print(f"Previous chord detected")
                        self.current_chord_index -= 1
                        if self.current_chord_index < 0:
                            self.current_chord_index = len(self.chord_sequence) - 1
                        self.target_chord = self.chord_sequence[self.current_chord_index]
                        self.detector.reset()
                        progress_text = f"{self.current_chord_index + 1}/{len(self.chord_sequence)}"
                        if self.chord_display:
                            self.chord_display.display_target_chord(self.target_chord, progress_text)
                        continue
                    
                    time_last_chord = utime.ticks_ms()
                    
                    # Add note to detector
                    string_num = self.detector.add_note(note)
                    print(f"String: {string_num}")
                    if string_num is None:
                        print("Unknown string, ignoring note")
                        continue
                    
                    # if note == last_note:
                    #     print("Duplicate note, ignoring")
                    #     continue
                    
                    last_note = note
                    
                    if self.collected_strings[string_num - 1] == None or self.collected_strings[string_num - 1] > self.collected_strings[string_num - 1]:
                        self.collected_strings[string_num - 1] = note

                    if all(x is not None for x in self.collected_strings):
                        print("All strings were struck!")
                        started = True

                    if timeout_task is not None:
                        timeout_task.cancel()
                    timeout_task = asyncio.create_task(timeout_handler())
                    try:
                        self._show_live_fretboard(self.target_chord, self.detector.get_played_notes(), progress_text)
                    except Exception as e:
                        print(f"Error in _show_live_fretboard: {e}")
                        import sys
                        sys.print_exception(e)

                    if not started:
                        continue
                    timeout_task.cancel()
                    timeout_task = None
                    last_string = string_num
                    
                    # if not notes_hit:
                    #     continue
                    print("Strum detected, processing chord.........................................")
                    # Process completed chord
                    await self._process_chord_detection()
                    
                    # Update target_chord to the current chord after processing
                    self.target_chord = self.chord_sequence[self.current_chord_index]
                    progress_text = f"{self.current_chord_index + 1}/{len(self.chord_sequence)}"
                    
                    # Reset for next chord
                    self.detector.reset()
                    started = False
                    notes_hit = False
                    last_note = None
                    self.collected_strings = [None] * 6
                
                await asyncio.sleep_ms(1)
        
        except Exception as e:
            print(f"Error in practice mode: {e}")
            import sys
            sys.print_exception(e)
        
        return 'menu'


    def _display_chord(self, played_note):
        print(f"Displaying chord for played note: {played_note}")
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





    def _show_live_fretboard(self, target_chord, played_notes, progress_text):
        """Display the fretboard in real-time with played notes overlaid
        
        Shows all strings that have been struck in green, with all played notes overlaid.
        Uses the detector's played_notes array to determine which strings were actually struck.
        Notes are colored green if correct for the chord, red if not.
        """
        print(f"Showing live fretboard for chord: {target_chord}, played_notes={played_notes}")
        if not self.chord_display:
            return
        print("Updating the display with live fretboard")
        
        # Get chord shape
        chord_notes = CHORD_MIDI_NOTES.get(target_chord, [])
        
        # Get expected non-open notes for this chord
        expected_notes = set(CHORD_MIDI_NOTES.get(target_chord, []))
        non_open_expected = set()
        for note in expected_notes:
            is_open = note in OPEN_STRING_NOTES
            if not is_open:
                non_open_expected.add(note)
        
        # Determine which strings have been struck using detector's string mapping
        # detector.played_notes[i] has the note for string (i+1), or None if not struck
        string_colors = []
        for string_num in range(1, 7):
            # Detector reverses indexing: string 6 at index 0, string 1 at index 5
            detector_index = 6 - string_num
            # Check if this string has a note in the detector
            if self.detector.played_notes[detector_index] is not None:
                print(f"String {string_num} was hit")
                string_colors.append(Colors.GREEN)  # String was hit
            else:
                print(f"String {string_num} was NOT hit")
                string_colors.append(Colors.WHITE)  # String not yet hit
        
        # Create note color mapping - green if correct, red if wrong
        note_colors = {}
        for note in played_notes:
            if note in non_open_expected:
                note_colors[note] = Colors.GREEN  # Correct note for chord
            else:
                note_colors[note] = Colors.RED    # Wrong note for chord
        
        # Only redraw the full fretboard when needed - use optimized drawing
        self.display.tft.fill(Colors.BLACK)
        
        # Show progress
        self.display.text(progress_text, 90, 5, Colors.WHITE)
        
        # Show chord name
        x_pos = 70 if len(target_chord) > 1 else 90
        self.display.draw_large_text(target_chord, x_pos, 30, Colors.ORANGE)
        
        # Draw the fretboard with color-coded strings
        self.chord_display._draw_chord_fretboard(target_chord, Colors.ORANGE, string_colors)
        
        # Overlay the played notes (with correct coloring for now)
        if played_notes:
            self.chord_display._draw_played_notes_overlay(played_notes, None, note_colors)
        
        self.display.tft.show()
    
    async def _process_chord_detection(self):
        """Process chord detection result"""
        print("-----------------------------------------------------------------------------")
        
        # Get played notes BEFORE resetting
        played_notes = self.detector.get_played_notes()
        is_correct, matching, missing, extra = self.detector.detect_chord(self.target_chord)
        
        print(f">>> Target: {self.target_chord}, Played: {played_notes}, Correct: {is_correct}")
        if not is_correct:
            print(f"    Missing: {missing}, Extra: {extra}")
        
        progress_text = f"{self.current_chord_index + 1}/{len(self.chord_sequence)}"
        
        if is_correct:
            print(f">>> SUCCESS! {self.target_chord} Correct!")
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
                    print(">>> Sequence complete! Randomizing...")
                    shuffled = list(self.chord_sequence)
                    n = len(shuffled)
                    for i in range(n - 1, 0, -1):
                        j = urandom.getrandbits(16) % (i + 1)
                        shuffled[i], shuffled[j] = shuffled[j], shuffled[i]
                    self.chord_sequence = shuffled
                    self.current_chord_index = 0
                else:
                    print(">>> All chords completed!")
                    return 'menu'
        else:
            print(f"Wrong! Expected {self.target_chord}")
            if self.chord_display:
                self.chord_display.display_wrong_chord("???", played_notes, self.target_chord, None, progress_text)
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
        """Parse MIDI message"""
        if not data or len(data) < 5:
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
        print("Starting metronome practice...")
        await self.metronome.start()
        
        pattern_index = 0
        last_strum_time = 0
        strum_cooldown_ms = 100
        last_string_num = 0
        
        # TODO: Implement full metronome practice logic
        
        await self.metronome.stop()
        return 'menu'
