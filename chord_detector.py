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
            for fret in range(5):
                midi_note = open_note + fret
                string_map[midi_note] = string_num
        return string_map
    
    def add_note(self, note):
        """Add a note to the current chord"""
        string_n = self.string_number_map.get(note)
        if string_n is None:
            return None
        
        # Reverse array: string 6 at index 0, string 1 at index 5
        string_num = 6 - string_n
        
        # Store note on the string, replacing if it's higher (higher fret)
        current_note = self.played_notes[string_num]
        if current_note is None or note > current_note:
            self.played_notes[string_num] = note
            return string_num
        
        return string_num
    
    def reset(self):
        """Reset the played notes"""
        self.played_notes = [None] * 6
    
    def get_played_notes(self):
        """Get set of currently played notes"""
        return set(n for n in self.played_notes if n is not None)
    
    def detect_chord(self, target_chord):
        """Check if played notes match target chord"""
        expected_notes = set(CHORD_MIDI_NOTES.get(target_chord, []))
        played_notes = self.get_played_notes()
        
        if not expected_notes:
            return False, None, None, None
        
        matching = played_notes.intersection(expected_notes)
        missing = expected_notes - played_notes
        extra = played_notes - expected_notes
        
        is_correct = played_notes.issuperset(expected_notes)
        
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
