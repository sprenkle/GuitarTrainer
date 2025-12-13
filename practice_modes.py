# Practice Modes

import asyncio
import urandom
import utime
import time
from config import SELECTION_NOTES, CHORD_MIDI_NOTES, Colors
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
        self.randomize_mode = None
        self.mode = 'R'  # 'R' for randomize, 'S' for sequence, None for direct
        self.last_display_update_ms = 0
        self.display_update_interval_ms = 30  # Throttle updates to 30ms (~33 FPS)

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
        target_chord = self.chord_sequence[self.current_chord_index]
        print(f"=== DISPLAY CHORD: {target_chord} ===")
        
        progress_text = f"{self.current_chord_index + 1}/{len(self.chord_sequence)}"
        if self.chord_display:
            self.chord_display.display_target_chord(target_chord, progress_text)
        else:
            # Fallback display
            self.display.clear()
            self.display.draw_large_text(target_chord, 70, 30, Colors.YELLOW)
            self.display.text(progress_text, 90, 5, Colors.WHITE)
            self.display.show()
        
        async def timeout_handler():
            """Handle timeout - reset strum if no completion"""
            await asyncio.sleep_ms(20900)  # Reset display after 500ms if strum not completed
            nonlocal started, notes_hit, timeout_task
            print("Strum timeout, resetting...")
            started = False
            notes_hit = False
            self.detector.reset()
            
            # Reset display to show target chord with white strings
            # time.sleep_ms(500)
            progress_text = f"{self.current_chord_index + 1}/{len(self.chord_sequence)}"
            if self.chord_display:
                self.chord_display.display_target_chord(target_chord, progress_text)
            
            timeout_task = None
        collected_strings = [None] * 6
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
                    
                    # Check for menu trigger (86 or 81)
                    if note in [86, 81]:
                        print(f"Menu trigger detected")
                        return 'menu'
                    
                    # Check time difference FIRST before processing
                    if utime.ticks_diff(utime.ticks_ms(), time_last_chord) > 500:
                        print("Time reset")
                        started = False
                        notes_hit = False
                        self.detector.reset()
                        last_note = None
                    
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
                    
                    if collected_strings[string_num - 1] == None or collected_strings[string_num - 1] > collected_strings[string_num - 1]:
                        collected_strings[string_num - 1] = note

                    if all(x is not None for x in collected_strings):
                        print("All strings were struck!")
                        started = True

                    # Start strum detection
                    # if not started:
                    #     if string_num == 6 or string_num == 1:
                    #         print(f'Strum started on string {string_num}')
                    #         started = True
                    #         strum_start_time = utime.ticks_ms()
                    #         up = (string_num == 1)
                    #         self.last_display_update_ms = 0  # Reset display throttle when strum starts
                            
                    if timeout_task is not None:
                        timeout_task.cancel()
                    timeout_task = asyncio.create_task(timeout_handler())
                    self._show_live_fretboard(target_chord, note, self.detector.get_played_notes(), progress_text)
                    #self._display_chord(note)
                    # if self.chord_display:
                    #     print("Updating the display with live fretboard");
                    #     self.display.tft.fill(Colors.BLACK)
                    #     self.display.text(progress_text, 90, 5, Colors.WHITE)
                    #     x_pos = 70 if len(target_chord) > 1 else 90
                    #     self.display.draw_large_text(target_chord, x_pos, 30, Colors.ORANGE)
                    #     self.chord_display._draw_chord_fretboard(target_chord, Colors.ORANGE, string_colors)
                    #     self.chord_display._draw_played_notes_overlay(played_notes, None)
                    #     self.display.tft.show()

                    if not started:
                        continue

                    # Show real-time display of struck strings as they come in (with throttling)
                    # if started:
                        # current_time_ms = utime.ticks_ms()
                        # if True or utime.ticks_diff(current_time_ms, self.last_display_update_ms) >= self.display_update_interval_ms:
                        #     self.last_display_update_ms = current_time_ms
                            
                        #     # Get all notes played so far
                        #     played_notes = self.detector.get_played_notes()
                            
                        #     # Determine which strings were hit
                        #     from config import OPEN_STRING_NOTES
                        #     string_colors = []
                        #     for string_num in range(1, 7):
                        #         open_note = OPEN_STRING_NOTES[string_num - 1]
                        #         string_was_hit = False
                                
                        #         # Check if any note on this string was played
                        #         for fret in range(25):
                        #             note_check = open_note + fret
                        #             if note_check in played_notes:
                        #                 string_was_hit = True
                        #                 break
                                
                        #         if string_was_hit:
                        #             string_colors.append(Colors.GREEN)  # String was hit
                        #         else:
                        #             string_colors.append(Colors.RED)    # String not yet hit
                            
                            # Update display with struck strings
                            # if self.chord_display:
                                # print("Updating the display with live fretboard");
                                # self.display.tft.fill(Colors.BLACK)
                                # self.display.text(progress_text, 90, 5, Colors.WHITE)
                                # x_pos = 70 if len(target_chord) > 1 else 90
                                # self.display.draw_large_text(target_chord, x_pos, 30, Colors.ORANGE)
                                # self.chord_display._draw_chord_fretboard(target_chord, Colors.ORANGE, string_colors)
                                # self.chord_display._draw_played_notes_overlay(played_notes, None)
                                # self.display.tft.show()
                    
                    # Check if strum completed
                    # print(f"Strum check: up={up}, string_num={string_num}, last_string={last_string}")
                    # if up and string_num == 6:
                    #     print(f'Strum completed (up)')
                    #     started = False
                    #     notes_hit = True
                    #     if timeout_task is not None:
                    #         timeout_task.cancel()
                    #         timeout_task = None
                    # elif not up and string_num == 1:
                    #     print(f'Strum completed (down)')
                    #     started = False
                    #     if timeout_task is not None:
                    #         timeout_task.cancel()
                    #         timeout_task = None
                    
                    last_string = string_num
                    
                    # if not notes_hit:
                    #     continue
                    print("Strum detected, processing chord.........................................")
                    # Process completed chord
                    await self._process_chord_detection()
                    
                    # Reset for next chord
                    self.detector.reset()
                    started = False
                    notes_hit = False
                    last_note = None
                    collected_strings = [None] * 6
                
                await asyncio.sleep_ms(10)
        
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





    def _show_live_fretboard(self, target_chord, current_note, played_notes, progress_text):
        """Display the fretboard in real-time with played notes overlaid
        
        Shows the target chord with the current string highlighted in green.
        """
        print(f"Showing live fretboard for chord: {target_chord}, current_note={current_note}")
        if not self.chord_display:
            return
        print("Updating the display with live fretboard")
        
        # Get chord shape
        from config import OPEN_STRING_NOTES
        chord_notes = CHORD_MIDI_NOTES.get(target_chord, [])
        
        # Find which string the current note is on
        current_string = None
        for string_num in range(1, 7):
            open_note = OPEN_STRING_NOTES[string_num - 1]
            # Check if current note is on this string
            for fret in range(25):
                if open_note + fret == current_note:
                    current_string = string_num
                    break
            if current_string:
                break
        
        # Determine string colors - only current string is green
        string_colors = []
        for string_num in range(1, 7):
            if string_num == current_string:
                print(f"String {string_num} is current (green)")
                string_colors.append(Colors.GREEN)  # Current string is green
            else:
                print(f"String {string_num} is not current (white)")
                string_colors.append(Colors.WHITE)  # All others are white
        
        # Only redraw the full fretboard when needed - use optimized drawing
        self.display.tft.fill(Colors.BLACK)
        
        # Show progress
        self.display.text(progress_text, 90, 5, Colors.WHITE)
        
        # Show chord name
        x_pos = 70 if len(target_chord) > 1 else 90
        self.display.draw_large_text(target_chord, x_pos, 30, Colors.ORANGE)
        
        # Draw the fretboard with color-coded strings
        self.chord_display._draw_chord_fretboard(target_chord, Colors.ORANGE, string_colors)
        
        # Overlay the played notes
        if played_notes:
            self.chord_display._draw_played_notes_overlay(played_notes, None)
        
        self.display.tft.show()
    
    async def _process_chord_detection(self):
        """Process chord detection result"""
        print("-----------------------------------------------------------------------------")
        target_chord = self.chord_sequence[self.current_chord_index]
        is_correct, matching, missing, extra = self.detector.detect_chord(target_chord)
        
        played_notes = self.detector.get_played_notes()
        print(f">>> Target: {target_chord}, Played: {played_notes}, Correct: {is_correct}")
        if not is_correct:
            print(f"    Missing: {missing}, Extra: {extra}")
        
        progress_text = f"{self.current_chord_index + 1}/{len(self.chord_sequence)}"
        
        if is_correct:
            print(f">>> SUCCESS! {target_chord} Correct!")
            if self.chord_display:
                self.chord_display.display_correct_chord(target_chord, progress_text)
            else:
                self.display.show_success(f"{target_chord} Correct!")
            await asyncio.sleep(0.125)  # Wait 1/8 second before clearing
            self.display.tft.fill(Colors.BLACK)  # Clear screen
            self.display.tft.show()
            
            self.current_chord_index += 1
            
            if self.current_chord_index >= len(self.chord_sequence):
                if self.randomize_mode == 'R':
                    print(">>> Sequence complete! Randomizing...")
                    shuffled = list(self.chord_sequence)
                    n = len(shuffled)
                    for i in range(n - 1, 0, -1):
                        j = urandom.getrandbits(16) % (i + 1)
                        shuffled[i], shuffled[j] = shuffled[j], shuffled[i]
                    self.chord_sequence = shuffled
                
                self.current_chord_index = 0
        else:
            print(f"Wrong! Expected {target_chord}")
            if self.chord_display:
                played_notes_set = self.detector.get_played_notes()
                self.chord_display.display_wrong_chord("???", played_notes_set, target_chord, None, progress_text)
                await asyncio.sleep(1.0)  # Show wrong result for 1 second before moving on
        
        # Reset detector for next chord
        self.detector.reset()
        
        # Display next chord
        next_chord = self.chord_sequence[self.current_chord_index]
        progress_text = f"{self.current_chord_index + 1}/{len(self.chord_sequence)}"
        if self.chord_display:
            self.chord_display.display_target_chord(next_chord, progress_text)
        else:
            self.display.clear()
            self.display.draw_large_text(next_chord, 70, 30, Colors.YELLOW)
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
