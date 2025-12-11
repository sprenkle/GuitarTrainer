# MIDI Message Parser

class MIDIParser:
    """Parses MIDI messages"""
    
    @staticmethod
    def parse_midi_message(data):
        """Parse MIDI message data"""
        if not data or len(data) < 2:
            return None
        
        byte0 = data[0]
        byte1 = data[1]
        
        # Check message type (upper nibble of byte0)
        status = byte0 & 0xF0
        
        if status == 0x90:  # Note On
            note = byte1
            velocity = data[2] if len(data) > 2 else 0
            if velocity > 0:
                return ('note_on', note, velocity)
        elif status == 0x80:  # Note Off
            note = byte1
            return ('note_off', note)
        
        return None
