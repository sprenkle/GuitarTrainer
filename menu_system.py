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
        data = None
        connection_timeout_ms = 0
        connection_check_interval_ms = 100  # Check connection every 100ms
        
        try:
            while self.ble.connected:
                self._display_menu(page, items_per_page) 
                
                # Get next MIDI message from queue (non-blocking)
                data = await self.ble.wait_for_queued_midi()

                # Debug: show all note messages
                if data:
                    command = data[0]
                    string_num = data[1] 
                    fret_num = data[2]
                    note = data[3]
                    fret_pressed = data[4] 
                    print(f"[MENU] MIDI MESSAGE: Command: {hex(command)}, String: {string_num}, Fret: {fret_num}, Note: {note}, Fret Pressed: {fret_pressed}" )
                    connection_timeout_ms = 0  # Reset timeout on data received
                    if command == 0x90:  # Note On
                        print(f"[MENU] Got Note On: {note}")
                        
                        # Navigation controls
                        if note == 86:  # String 1, 22nd fret - Next page
                            print("[MENU] Next page")
                            if (page + 1) * items_per_page < len(PRACTICE_OPTIONS):
                                page += 1
                            continue
                        elif note == 81:  # String 2, 22nd fret - Previous page
                            print("[MENU] Previous page")
                            if page > 0:
                                page -= 1
                            continue
                        
                        # Check if it's a 22nd fret selection (strings 3-6 = indices 2-5)
                        if fret_num == 22:
                            if string_num >= 2:
                                selected_index = page * items_per_page + (string_num - 2)
                                print(f"[MENU] Selected index: {selected_index}")
                                if selected_index < len(PRACTICE_OPTIONS):
                                    selected_chords = list(PRACTICE_OPTIONS[selected_index][1])
                                    print(f"[MENU] Selected: {PRACTICE_OPTIONS[selected_index][0]}")
                                    
                                    # Flash selection
                                    self.display.clear()
                                    self.display.text("Selected:", 70, 100, Colors.YELLOW)
                                    self.display.text(PRACTICE_OPTIONS[selected_index][0], 50, 120, Colors.GREEN)
                                    self.display.show()
                                    await asyncio.sleep(0.5)
                                    
                                    return selected_chords
                    elif command == 0x80:  # Note Off
                        print(f"[MENU] Got Note Off: {note}")
                        pass  # Ignore note off
                else:
                    # No messages in queue, sleep briefly and track timeout
                    connection_timeout_ms += connection_check_interval_ms
                    await asyncio.sleep_ms(connection_check_interval_ms)
                    
                    # Every 1 second, explicitly check if connection is still alive
                    if connection_timeout_ms >= 1000:
                        if not self.ble.connected:
                            print("[MENU] Connection lost, exiting menu")
                            break
                        connection_timeout_ms = 0
                        
        except Exception as e:
            print(f"[MENU] Error in show_menu_and_wait_for_selection: {type(e).__name__}: {e}")
        
        # Return None to signal menu was exited (connection lost)
        print("[MENU] Menu exited, returning None")
        return None
    
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
        connection_timeout_ms = 0
        connection_check_interval_ms = 100
        
        while self.ble.connected:
            # Get next MIDI message from queue (non-blocking)
            data = await self.ble.wait_for_queued_midi()
            if data:
                print(f"[BPM MENU] Received MIDI data: {' '.join(f'{b:02x}' for b in data)}")
                msg = self._parse_midi(data)
                if msg and msg[0] == 'note_on':
                    note = msg[1]
                    print(f"[BPM MENU] Note received: {note}")
                    
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
                connection_timeout_ms = 0
            else:
                # No messages in queue, sleep briefly
                connection_timeout_ms += connection_check_interval_ms
                await asyncio.sleep_ms(connection_check_interval_ms)
                
                # Every 1 second, check connection status
                if connection_timeout_ms >= 1000:
                    if not self.ble.connected:
                        print("[BPM MENU] Connection lost, exiting menu")
                        return None
                    connection_timeout_ms = 0
        
        # Connection was lost
        print("[BPM MENU] BLE disconnected, exiting menu")
        return None
    
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
        if not data or len(data) < 3:
            return None
        
        midi_status = data[0]
        
        # Note On: 0x90-0x9F
        if 0x90 <= midi_status <= 0x9F:
            if len(data) >= 3:
                string_number = data[1]
                note = data[2]
                if note > 0:
                    return ('note_on', string_number, note)
                else:
                    return ('note_off', string_number)
        
        # Note Off: 0x80-0x8F
        elif 0x80 <= midi_status <= 0x8F:
            if len(data) >= 2:
                note = data[1]
                return ('note_off', note)
        
        return None
