# Serial Handler for Chord Uploads

import asyncio
import sys

class SerialHandler:
    """Handles serial communication for chord uploads"""
    
    def __init__(self, display_manager):
        self.display = display_manager
        self.new_chord_list_uploaded = False
        self.custom_chord_lists = {}
        self.serial_task = None
    
    async def serial_monitor_task(self):
        """Background task to listen on serial port"""
        try:
            while True:
                try:
                    # Non-blocking read from stdin
                    import select
                    rlist, _, _ = select.select([sys.stdin], [], [], 0)
                    
                    if rlist:
                        char = sys.stdin.read(1)
                        if char:
                            self._process_serial_char(char)
                except:
                    pass
                
                await asyncio.sleep_ms(50)
        except Exception as e:
            print(f"[Serial] Error: {e}")
    
    def _process_serial_char(self, char):
        """Process a character from serial input"""
        # This is a placeholder - implement based on your serial protocol
        pass
    
    def load_custom_chord_lists(self):
        """Load custom chord lists from storage"""
        try:
            import json
            with open('custom_chords.json', 'r') as f:
                self.custom_chord_lists = json.load(f)
                print(f"Loaded {len(self.custom_chord_lists)} custom chord lists")
        except Exception as e:
            print(f"Could not load custom chords: {e}")
            self.custom_chord_lists = {}
    
    def save_custom_chord_lists(self):
        """Save custom chord lists to storage"""
        try:
            import json
            with open('custom_chords.json', 'w') as f:
                json.dump(self.custom_chord_lists, f)
                print(f"Saved {len(self.custom_chord_lists)} custom chord lists")
        except Exception as e:
            print(f"Could not save custom chords: {e}")
    
    def add_custom_chord_list(self, name, mode, chords):
        """Add a custom chord list"""
        self.custom_chord_lists[name] = [mode] + chords
        self.save_custom_chord_lists()
        print(f"Added chord list: {name}")
