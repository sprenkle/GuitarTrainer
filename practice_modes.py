# Practice Modes

import asyncio
import urandom
import utime
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
        strum_start_time = 0
        strum_timeout_ms = 750
        last_string = 0
        up = False
        timeout_task = None
        time_last_chord = 0
        
        # Display the first target chord
        target_chord = self.chord_sequence[self.current_chord_index]
        print(f"=== DISPLAY CHORD: {target_chord} ===")
        
        self.display.clear()
        
        # Display the chord name large
        self.display.draw_large_text(target_chord, 70, 30, Colors.YELLOW)
        
        # Display fret info for this chord
        from config import OPEN_STRING_NOTES
        chord_notes = CHORD_MIDI_NOTES.get(target_chord, [])
        
        # Display each string's fret position
        y = 90
        self.display.text("Frets:", 60, y, Colors.WHITE)
        y += 18
        
        for string_num in range(1, 7):
            open_note = OPEN_STRING_NOTES[string_num - 1]
            fret = None
            
            # Find which fret on this string
            for f in range(6):
                if open_note + f in chord_notes:
                    fret = f
                    break
            
            if fret is not None:
                text = f"S{string_num}:{fret}"
                self.display.text(text, 50, y, Colors.GREEN)
                y += 16
        
        self.display.text("Strum & hold", 50, y + 10, Colors.WHITE)
        self.display.text("22nd=back", 70, 220, Colors.ORANGE)
        
        self.display.show()
        print(f"Displayed: {target_chord} with frets")
        
        async def timeout_handler():
            """Handle timeout - reset strum if no completion"""
            await asyncio.sleep_ms(strum_timeout_ms)
            nonlocal started, notes_hit, timeout_task
            started = False
            notes_hit = False
            self.detector.reset()
            timeout_task = None
        
        try:
            while self.ble.connected:
                print("Waiting for MIDI...")
                # Check for new chord list upload
                if self.new_chord_list_uploaded:
                    self.new_chord_list_uploaded = False
                    return 'menu'
                
                # Wait for MIDI data
                try:
                    data = await self.ble.wait_for_midi(0.5)
                    if data:
                        print(f"Got MIDI: {data}")
                except asyncio.TimeoutError:
                    pass
                
                if not data:
                    continue
                
                print(f"Parsing MIDI: {data}")
                msg = self._parse_midi(data)
                print(f"Parsed: {msg}")
                
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
                        continue
                    
                    if note == last_note:
                        continue
                    
                    last_note = note
                    
                    # Start strum detection
                    if not started:
                        if string_num == 5 or string_num == 0:
                            print(f'Strum started on string {string_num}')
                            started = True
                            strum_start_time = utime.ticks_ms()
                            up = (string_num == 0)
                            
                            if timeout_task is not None:
                                timeout_task.cancel()
                            timeout_task = asyncio.create_task(timeout_handler())
                    
                    # Check if strum completed
                    if up and string_num == 5:
                        print(f'Strum completed (up)')
                        started = False
                        notes_hit = True
                        if timeout_task is not None:
                            timeout_task.cancel()
                            timeout_task = None
                    elif not up and string_num == 0:
                        print(f'Strum completed (down)')
                        started = False
                        notes_hit = True
                        if timeout_task is not None:
                            timeout_task.cancel()
                            timeout_task = None
                    
                    last_string = string_num
                    
                    if not notes_hit:
                        continue
                    
                    # Process completed chord
                    await self._process_chord_detection()
                    
                    # Reset for next chord
                    self.detector.reset()
                    started = False
                    notes_hit = False
                    last_note = None
                
                await asyncio.sleep_ms(10)
        
        except Exception as e:
            print(f"Error in practice mode: {e}")
            import sys
            sys.print_exception(e)
        
        return 'menu'
    
    async def _process_chord_detection(self):
        """Process chord detection result"""
        target_chord = self.chord_sequence[self.current_chord_index]
        is_correct, matching, missing, extra = self.detector.detect_chord(target_chord)
        
        played_notes = self.detector.get_played_notes()
        print(f">>> Target: {target_chord}, Played: {played_notes}, Correct: {is_correct}")
        if not is_correct:
            print(f"    Missing: {missing}, Extra: {extra}")
        
        if is_correct:
            print(f">>> SUCCESS! {target_chord} Correct!")
            self.display.show_success(f"{target_chord} Correct!")
            await asyncio.sleep(0.5)
            
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
        
        # Display next chord
        next_chord = self.chord_sequence[self.current_chord_index]
        self.display.clear()
        self.display.draw_large_text(next_chord, 70, 30, Colors.YELLOW)
        
        # Display fret positions again
        from config import OPEN_STRING_NOTES
        chord_notes = CHORD_MIDI_NOTES.get(next_chord, [])
        y = 90
        self.display.text("Frets:", 60, y, Colors.WHITE)
        y += 18
        
        for string_num in range(1, 7):
            open_note = OPEN_STRING_NOTES[string_num - 1]
            fret = None
            
            for f in range(6):
                if open_note + f in chord_notes:
                    fret = f
                    break
            
            if fret is not None:
                text = f"S{string_num}:{fret}"
                self.display.text(text, 50, y, Colors.GREEN)
                y += 16
        
        self.display.text("Strum & hold", 50, y + 10, Colors.WHITE)
        self.display.text("22nd=back", 70, 220, Colors.ORANGE)
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
