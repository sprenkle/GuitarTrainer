# Menu System

import asyncio
from config import PRACTICE_OPTIONS, BPM_OPTIONS, SELECTION_NOTES, Colors

class MenuSystem:
    """Handles menu display and selection"""
    
    def __init__(self, display_manager, ble_manager):
        self.display = display_manager
        self.ble = ble_manager
        self.midi_buffer = []
    
    async def show_menu_and_wait_for_selection(self):
        """Show practice menu and wait for selection"""
        
        print(f"MENU: Entering menu selection, BLE connected: {self.ble.connected}")
        print(f"MENU: MIDI characteristic: {self.ble.midi_characteristic}")
        print(f"SELECTION_NOTES: {SELECTION_NOTES}")
        
        while True:
            self._display_menu(0)
            
            # Wait for MIDI note
            try:
                data = await self.ble.wait_for_midi(0.5)
                if data:
                    print(f"MENU DEBUG: Received MIDI data: {data}, length: {len(data)}")
                    msg = self._parse_midi(data)
                    print(f"MENU DEBUG: Parsed message: {msg}")
                    if msg and msg[0] == 'note_on':
                        note = msg[1]
                        print(f"MENU DEBUG: Note On detected - note: {note}")
                        
                        # Check if it's a 22nd fret selection
                        if note in SELECTION_NOTES:
                            selected_index = SELECTION_NOTES.index(note)
                            print(f"MENU DEBUG: Found selection note at index: {selected_index}")
                            if selected_index < len(PRACTICE_OPTIONS):
                                selected_chords = list(PRACTICE_OPTIONS[selected_index][1])
                                print(f"Selected: {PRACTICE_OPTIONS[selected_index][0]}")
                                
                                # Flash selection
                                self.display.clear()
                                self.display.text("Selected:", 70, 100, Colors.YELLOW)
                                self.display.text(PRACTICE_OPTIONS[selected_index][0], 50, 120, Colors.GREEN)
                                self.display.show()
                                await asyncio.sleep(0.5)
                                
                                return selected_chords
                        else:
                            print(f"MENU DEBUG: Note {note} not in SELECTION_NOTES {SELECTION_NOTES}")
                    else:
                        print(f"MENU DEBUG: Not a note_on message or msg is None")
                else:
                    pass  # No data, just timeout - expected
            except asyncio.TimeoutError:
                pass
            except Exception as e:
                print(f"MENU ERROR: {e}")
                import traceback
                traceback.print_exc()
            
            await asyncio.sleep_ms(50)
    
    async def show_bpm_menu(self):
        """Show BPM selection menu"""
        # Display BPM menu
        self.display.clear()
        self.display.text("Select BPM:", 80, 10, Colors.YELLOW)
        self.display.text("Use 22nd fret", 55, 30, Colors.WHITE)
        
        # Show BPM options
        y_pos = 50
        for i, bpm in enumerate(BPM_OPTIONS):
            color = Colors.WHITE
            marker = " "
            self.display.text(f"{marker}{i+1}. {bpm} BPM", 50, y_pos, color)
            y_pos += 20
        
        self.display.text("String 1-6 = opt 1-6", 30, y_pos + 10, Colors.ORANGE)
        self.display.show()
        
        print("BPM menu displayed. Waiting for 22nd fret selection...")
        
        # Wait for selection
        while True:
            try:
                data = await self.ble.wait_for_midi(0.5)
                if data:
                    msg = self._parse_midi(data)
                    if msg and msg[0] == 'note_on':
                        note = msg[1]
                        print(f"BPM Menu - Note received: {note}")
                        
                        # Check if it's a 22nd fret note
                        if note in SELECTION_NOTES:
                            selected_index = SELECTION_NOTES.index(note)
                            if selected_index < len(BPM_OPTIONS):
                                selected_bpm = BPM_OPTIONS[selected_index]
                                print(f"Selected: {selected_bpm} BPM")
                                
                                # Flash selection
                                self.display.clear()
                                self.display.text("Selected:", 80, 100, Colors.GREEN)
                                self.display.text(f"{selected_bpm} BPM", 85, 120, Colors.YELLOW)
                                self.display.show()
                                await asyncio.sleep(0.5)
                                
                                return selected_bpm
            except asyncio.TimeoutError:
                pass
            
            await asyncio.sleep_ms(50)
    
    def _display_menu(self, current_selection):
        """Display the current menu"""
        print("_display_menu called")
        self.display.clear()
        
        # Use hardcoded colors for testing
        WHITE = 0xFFFF
        YELLOW = 0xFFE0
        GREEN = 0x07E0
        ORANGE = 0xFD20
        
        self.display.text("Select Practice:", 50, 10, YELLOW)
        self.display.text("Use 22nd fret", 55, 30, WHITE)
        
        y_pos = 50
        for i, (name, _) in enumerate(PRACTICE_OPTIONS):
            color = GREEN if i == current_selection else WHITE
            marker = ">" if i == current_selection else " "
            self.display.text(f"{marker}{i+1}. {name}", 40, y_pos, color)
            y_pos += 20
        
        self.display.text("String 1-6 = opt 1-6", 30, y_pos + 10, ORANGE)
        print("About to call display.show()")
        self.display.show()
        print("display.show() completed")
    
    @staticmethod
    def _parse_midi(data):
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
