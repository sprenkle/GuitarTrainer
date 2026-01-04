# Main Application Class - Orchestrates all components

import asyncio
from display_manager import DisplayManager
from ble_connection_dual_core import BLEConnectionManagerDualCore
from menu_system import MenuSystem
from chord_detector import ChordDetector
from chord_display import ChordDisplay
from serial_handler import SerialHandler
from practice_modes import RegularPracticeMode, MetronomePracticeMode
from config import Colors

class GuitarTrainerApp:
    """Main application class that orchestrates all components"""
    RANDOMIZE = 'R'
    SEQUENCE = 'S'
    METRODOME = 'M'
    HIDDE_DIAGRAM = 'H'

    def __init__(self, tft, ble_manager=None):
        # Initialize managers
        self.display = DisplayManager(tft)
        # Use provided BLE manager or create a new one
        if ble_manager is not None:
            self.ble = ble_manager
        else:
            self.ble = BLEConnectionManagerDualCore(self.display)
        self.menu = MenuSystem(self.display, self.ble)
        self.detector = ChordDetector()
        self.chord_display = ChordDisplay(self.display)
        self.serial = SerialHandler(self.display)
        
        # State
        self.chord_sequence = []
        self.randomize_mode = None
        self.current_chord_index = 0
        self.sequence_mode = True
    
    async def run(self):
        """Main application loop with auto-reconnection"""
        while True:
            # Try to connect - will loop until successful
            if not self.ble.connected:
                if not await self.ble.scan_and_connect():
                    print("Failed to connect, retrying...")
                    await asyncio.sleep(2)
                    continue
            
            # Start serial monitor
            if not self.serial.serial_task:
                self.serial.serial_task = asyncio.create_task(self.serial.serial_monitor_task())
            
            # Main loop - show menu when needed
            while self.ble.connected:
                try:
                    print("Showing practice menu...")
                    selected_chords = await self.menu.show_menu_and_wait_for_selection()
                    print(f"Menu returned: {selected_chords}, type: {type(selected_chords)}")
                    
                    # Check if menu exited due to connection loss
                    if selected_chords is None:
                        print("Menu returned None - connection was likely lost")
                        self.ble.connected = False
                        break
                    
                    # Set the chord sequence
                    if selected_chords and len(selected_chords) > 0 and selected_chords[0] in ['R', 'S', 'M', 'H']:
                        self.randomize_mode = selected_chords[0]
                        self.chord_sequence = selected_chords[1:]
                        print(f"Mode with prefix: mode={self.randomize_mode}, chords={self.chord_sequence}")
                    else:
                        self.randomize_mode = None
                        self.chord_sequence = selected_chords if selected_chords else []
                        print(f"Direct chord list: chords={self.chord_sequence}")
                    
                    self.current_chord_index = 0
                    self.serial.new_chord_list_uploaded = False
                    
                    print(f"Starting practice: {len(self.chord_sequence)} chords")
                    
                    # Run selected mode
                    if len(self.chord_sequence) == 0:
                        print("No chords selected, showing menu again")
                        continue    # Skip the rest of the loop and show menu again 

                    if self.randomize_mode == self.METRODOME:
                        print("Metrodome practice mode selected")
                        mode = MetronomePracticeMode(
                            self.display, self.ble, self.detector, self.menu, self.chord_sequence, self.chord_display
                        )
                        result = await mode.run()
                        print(f"Practice session ended with result: {result}")
                    elif self.randomize_mode == self.HIDDE_DIAGRAM:
                        print("Hide Diagram mode selected")
                        mode = RegularPracticeMode(
                            self.display, self.ble, self.detector, self.menu, self.chord_sequence, self.chord_display
                        )
                        mode.hide_diagram = True
                        result = await mode.run()
                        print(f"Practice session ended with result: {result}")
                    elif self.randomize_mode == self.RANDOMIZE or self.randomize_mode == self.SEQUENCE:
                        print(f"Practice Mode {self.randomize_mode}")
                        mode = RegularPracticeMode(
                            self.display, self.ble, self.detector, self.menu, self.chord_sequence, self.chord_display
                        )
                        mode.mode = self.randomize_mode 
                        result = await mode.run()
                        print(f"Practice session ended with result: {result}")
                    else:
                        print("Regular practice mode selected")
                        mode = RegularPracticeMode(
                            self.display, self.ble, self.detector, self.menu, self.chord_sequence, self.chord_display
                        )
                        if self.randomize_mode:
                            mode.randomize_mode = self.randomize_mode
                        result = await mode.run()
                        
                        print(f"Practice session ended with result: {result}")
                
                except Exception as e:
                    print(f"Error during practice: {e}")
                    import sys
                    sys.print_exception(e)
                    
                    # Check if connection was lost
                    if not self.ble.connected or not self.ble.midi_characteristic:
                        print("Connection lost, returning to scan...")
                        self.ble.connected = False
                        break
            
            # If we exit the inner loop due to disconnection, try to reconnect
            if not self.ble.connected:
                print("Attempting to reconnect...")
                self.display.clear()
                self.display.text("Connection Lost", 60, 100, Colors.RED)
                self.display.text("Reconnecting...", 60, 120, Colors.YELLOW)
                self.display.show()
                await asyncio.sleep(1)
    
    async def cleanup(self):
        """Clean up resources"""
        await self.ble.disconnect()
        if self.serial.serial_task:
            self.serial.serial_task.cancel()
