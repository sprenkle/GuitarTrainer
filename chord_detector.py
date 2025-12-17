# Chord Detection and Analysis

from config import CHORD_MIDI_NOTES, OPEN_STRING_NOTES

class ChordDetector:
    """Detects and analyzes chords from played notes"""
    
    def __init__(self):
        self.played_notes = [None] * 6  # Array for 6 strings
        self.string_number_map = self._create_string_map()
    
    def _create_string_map(self):
        """Create mapping from MIDI note to string number"""
        string_map = {}
        for string_num in range(6, 0, -1):
            open_note = OPEN_STRING_NOTES[string_num - 1]
            for fret in range(25):  # Extended range to handle higher frets
                midi_note = open_note + fret
                string_map[midi_note] = string_num
        return string_map
    
    def add_note(self, note):
        """Add a note to the current chord"""
        string_n = self.string_number_map.get(note)
        print(f"add_note: note={note}, string_n={string_n}  {self.played_notes[4]}")

        if string_n is None:
            print(f"Note {note} not in string map")
            return None

        special_59 = False
        if note == 59 and self.played_notes[4] is not None and self.played_notes[3] is None:
        #     # Special case for open B string (string 2)
            print(f"Special case: assigning note {note} to string {string_n} -----------------------------------------")
            string_n = 3
            special_59 = True




        # Reverse array: string 6 at index 0, string 1 at index 5
        string_num = 6 - string_n
        # Store note on the string, replacing if it's higher (higher fret)

        current_note = self.played_notes[string_num]


        if current_note is None or note > current_note:
            self.played_notes[string_num] = note
            print(f"Added note {note} to string {string_num + 1}")
            return string_num
        
        return string_num
    
    def reset(self):
        """Reset the played notes"""
        self.played_notes = [None] * 6
    
    def get_played_notes(self):
        """Get set of currently played notes"""
        return set(n for n in self.played_notes if n is not None)
    
    def detect_chord(self, played_chords, target_chord):
        """Check if played notes match target chord (non-open strings only)"""
        expected_notes = set(CHORD_MIDI_NOTES.get(target_chord, []))
        played_notes = self.get_played_notes()
        
        # Filter out open strings (fret 0) from expected notes
        non_open_expected = set()
        for note in expected_notes:
            # Check if this note is NOT an open string
            is_open = note in OPEN_STRING_NOTES
            if not is_open:
                non_open_expected.add(note)
        
        print(f"detect_chord({target_chord}): expected={expected_notes}, non_open={non_open_expected}, played={played_notes}")
        
        if not non_open_expected:
            return False, None, None, None
        
        matching = played_notes.intersection(non_open_expected)
        missing = non_open_expected - played_notes
        extra = played_notes - non_open_expected
        
        is_correct = played_notes.issuperset(non_open_expected)
        
        print(f"  matching={matching}, missing={missing}, extra={extra}, correct={is_correct}")
        
        return is_correct, matching, missing, extra
    
    def midi_to_fret_position(self, midi_note, string_num):
        """Calculate fret position for a MIDI note on a given string"""
        open_note = OPEN_STRING_NOTES[string_num - 1]
        fret = midi_note - open_note
        if 0 <= fret <= 4:
            return fret
        return None
    
    def get_string_from_note(self, note):
        """Get string number from MIDI note"""
        return self.string_number_map.get(note)
    
    def get_fret_positions(self):
        """Get fret positions for all strings (0 = open, None = not played)
        
        Returns:
            List of 6 fret positions, indexed by string (string 1 at index 0, string 6 at index 5)
        """
        fret_positions = [None] * 6
        
        for string_num in range(1, 7):
            # Detector reverses indexing: string 6 at index 0, string 1 at index 5
            detector_index = 6 - string_num
            note = self.played_notes[detector_index]
            
            if note is not None:
                open_note = OPEN_STRING_NOTES[string_num - 1]
                fret = note - open_note
                if fret >= 0:
                    fret_positions[string_num - 1] = fret
        
        return fret_positions
