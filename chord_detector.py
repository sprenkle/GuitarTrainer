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
    
    def add_note(self, note, string_num, fret_num=None):
        """Add a note to the current chord"""
        # print(f"add_note: note={note}, string_n={string_n}  {self.played_notes[4]}")

        if string_num is None:
            print(f"Note {note} not in string map")
            return None
  
        # Reverse array: string 6 at index 0, string 1 at index 5

        self.played_notes[5-string_num] = note # type: ignore
        # print(f"Added note {note} to string {string_num + 1}")
        return string_num
    
    def reset(self):
        """Reset the played notes"""
        self.played_notes = [None] * 6
    
    def get_played_notes(self):
        """Get set of currently played notes"""
        return set(n for n in self.played_notes if n is not None)
    
    def detect_chord(self, played_chords, target_chord):
        print(f"detect_chord: target_chord={target_chord}  played_chords={played_chords}")
        """Check if played notes match target chord (non-open strings only)"""
        chord_notes = CHORD_MIDI_NOTES.get(target_chord, [])
        expected_notes = set(chord_notes)
        
        # Convert played_chords list to set, filtering out None values
        played_notes = set(note for note in played_chords if note is not None)

        # Filter out muted strings (40 = low E string mute in config) from expected notes
        # But include ALL notes that are actually in the chord definition
        non_open_expected = set()
        for i, note in enumerate(chord_notes):
            # Check if this note is actually in the chord definition
            print(f"Check chord_notes: target_chord={target_chord}, string={i}, note={note}")
            if note is not None:
                non_open_expected.add(note)
        
        print(f"after finding expected detect_chord({target_chord}): expected={expected_notes}, non_open={non_open_expected}, played={played_notes}")
        
        if not non_open_expected:
            return False, None, None, None
        
        for i in range(6):
            note = self.played_notes[i]
            print(f"  string {6 - i}: note={note}")

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
