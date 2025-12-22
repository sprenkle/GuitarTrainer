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
        
        print(f"MENU: Starting menu, options: {len(PRACTICE_OPTIONS)}")
        
        page = 0
        items_per_page = 4
        
        while True:
            self._display_menu(page, items_per_page)
            
            # Get next MIDI message from queue (non-blocking)
            data = self.ble.wait_for_queued_midi()
            
            if data:
                msg = self._parse_midi(data)
                
                # Debug: show all note messages
                if msg:
                    if msg[0] == 'note_on':
                        note = msg[1]
                        velocity = msg[2]
                        print(f"Got Note On: {note}")
                        
                        # Navigation controls
                        if note == 86:  # String 1, 22nd fret - Next page
                            print("Next page")
                            if (page + 1) * items_per_page < len(PRACTICE_OPTIONS):
                                page += 1
                            continue
                        elif note == 81:  # String 2, 22nd fret - Previous page
                            print("Previous page")
                            if page > 0:
                                page -= 1
                            continue
                        
                        # Check if it's a 22nd fret selection (strings 3-6 = indices 2-5)
                        if note in SELECTION_NOTES:
                            string_num = SELECTION_NOTES.index(note)
                            # Only select if it's strings 3-6 (indices 2-5)
                            if string_num >= 2:
                                selected_index = page * items_per_page + (string_num - 2)
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
                    elif msg[0] == 'note_off':
                        pass  # Ignore note off
            else:
                # No messages in queue, sleep briefly
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
            # Get next MIDI message from queue (non-blocking)
            data = self.ble.wait_for_queued_midi()
            
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
            else:
                # No messages in queue, sleep briefly
                await asyncio.sleep_ms(50)
    
    def _display_menu(self, page, items_per_page=4):
        """Display the current menu page"""
        self.display.clear()
        
        self.display.text("Select Practice:", 50, 10, Colors.YELLOW)
        
        start_index = page * items_per_page
        end_index = min(start_index + items_per_page, len(PRACTICE_OPTIONS))
        
        y_pos = 40
        for i in range(start_index, end_index):
            local_index = i - start_index
            name = PRACTICE_OPTIONS[i][0]
            marker = f"{local_index + 1}"
            self.display.text(f"{marker}. {name}", 40, y_pos, Colors.WHITE)
            y_pos += 25
        
        # Show navigation controls
        total_pages = (len(PRACTICE_OPTIONS) + items_per_page - 1) // items_per_page
        nav_y = 155
        self.display.text("S1=NEXT  S2=PREV", 40, nav_y, Colors.ORANGE)
        if total_pages > 1:
            page_text = f"Page {page + 1}/{total_pages}"
            self.display.text(page_text, 70, nav_y + 18, Colors.YELLOW)
        
        self.display.show()
    
    @staticmethod
    def _parse_midi(data):
        """Parse MIDI message
        
        Expects individual MIDI messages (2-3 bytes) without BLE header/timestamp:
        - Note On: [0x90-0x9F, note, velocity]
        - Note Off: [0x80-0x8F, note] or [0x90-0x9F, note, 0x00]
        """
        if not data or len(data) < 2:
            return None
        
        midi_status = data[0]
        
        # Note On: 0x90-0x9F
        if 0x90 <= midi_status <= 0x9F:
            if len(data) >= 3:
                note = data[1]
                velocity = data[2]
                if velocity > 0:
                    return ('note_on', note, velocity)
                else:
                    return ('note_off', note)
        
        # Note Off: 0x80-0x8F
        elif 0x80 <= midi_status <= 0x8F:
            if len(data) >= 2:
                note = data[1]
                return ('note_off', note)
        
        return None
